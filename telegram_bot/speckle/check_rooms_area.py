import asyncio
import logging
import time
from specklepy.api import operations
from specklepy.transports.server import ServerTransport
from specklepy.transports.memory import MemoryTransport
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, ConversationHandler, MessageHandler, filters
from telegram_bot.speckle.speckle_config import client, get_speckle_stream_id
from telegram_bot.speckle.speckle_projects import get_speckle_projects

logging.basicConfig(level=logging.DEBUG)

SELECT_PROJECT = 0

def extract_check_area_discrepancy(obj):
    discrepancy_rooms = []

    if getattr(obj, 'category', None) == 'Помещения' and hasattr(obj, "parameters"):
        param_obj = obj.parameters
        area = None
        rounded_area = None
        level_name = None
        room_number = None

        for param_name, param_value in param_obj.__dict__.items():
            if hasattr(param_value, 'name'):
                normalized_param_name = param_value.name.lower()
                if normalized_param_name == 'площадь':
                    area = param_value.value
                elif normalized_param_name == 'speech_площадь округлённая':
                    rounded_area = param_value.value
                elif normalized_param_name == 'уровень' and level_name is None:
                    level_name = param_value.value
                elif normalized_param_name == 'номер' and room_number is None:
                    room_number = param_value.value

        if area is not None and rounded_area is not None and abs(area - rounded_area) > 0.4:
            discrepancy_info = {
                'id': obj.elementId,
                'name': obj.name,
                'area': area,
                'rounded_area': rounded_area,
                'level_name': level_name,
                'room_number': room_number
            }
            discrepancy_rooms.append(discrepancy_info)

    for element in getattr(obj, 'elements', []):
        discrepancy_rooms.extend(extract_check_area_discrepancy(element))

    return discrepancy_rooms

def format_discrepancy_rooms(discrepancy_rooms):
    if discrepancy_rooms:
        message = "Найдены расхождения в помещениях:\n\n"
        for index, room in enumerate(discrepancy_rooms, start=1):
            message += (f"№: {index}\n"
                        f"ID: {room.get('id', 'N/A')}\n"
                        f"Название: {room.get('name', 'N/A')}\n"
                        f"Площадь: {room.get('area', 'N/A')}\n"
                        f"Округленная Площадь: {room.get('rounded_area', 'N/A')}\n"
                        f"Уровень: {room.get('level_name', 'N/A')}\n"
                        f"Номер комнаты: {room.get('room_number', 'N/A')}\n\n")
        return message
    else:
        return "Расхождений не найдено.\n\n"

def get_commits(branch_name=None, stream_id=None):
    limit = 100
    commits = client.commit.list(stream_id, limit=limit)

    if branch_name:
        commits = [commit for commit in commits if getattr(commit, 'branchName', '') == branch_name]

    return commits

def list_branches(stream_id, print_to_console=True):
    branches = client.branch.list(stream_id)
    if print_to_console:
        for idx, branch in enumerate(branches):
            logging.info(f"[{idx + 1}] {branch.name}")
    return [branch.name for branch in branches]

def split_message(message, max_bytes=4096):
    """Разбивает сообщение на части, не превышающие max_bytes байт."""
    chunks = []
    current_chunk = ''
    for line in message.split('\n'):
        encoded_line = (line + '\n').encode('utf-8')
        if len(encoded_line) > max_bytes:
            # Разбиваем слишком длинную строку
            for i in range(0, len(encoded_line), max_bytes):
                part = encoded_line[i:i+max_bytes].decode('utf-8', errors='ignore')
                chunks.append(part)
        elif len((current_chunk + line + '\n').encode('utf-8')) <= max_bytes:
            current_chunk += line + '\n'
        else:
            chunks.append(current_chunk)
            current_chunk = line + '\n'
    if current_chunk:
        chunks.append(current_chunk)
    return chunks

async def start_check_area_discrepancy(update: Update, context: CallbackContext):
    user = update.message.from_user
    logging.debug(f"User {user.first_name} initiated check_area_discrepancy command.")

    projects = get_speckle_projects(client)
    logging.debug(f"Retrieved projects: {projects}")
    project_list = [project.name for project in projects]

    reply_keyboard = [[project] for project in project_list]
    await update.message.reply_text(
        "Пожалуйста, выберите проект:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    logging.debug("Sent project selection message.")

    return SELECT_PROJECT

async def process_branch(branch, stream_id, semaphore, timing_info):
    start_time = time.perf_counter()
    async with semaphore:
        branch_info = {}
        branch_info['branch'] = branch
        branch_start_time = time.perf_counter()
        logging.debug(f"Processing branch: {branch}")
        if branch.lower() == "main":
            branch_info['status'] = 'Skipped main branch'
            return branch_info

        # Получаем коммиты для ветки
        commits_start_time = time.perf_counter()
        commits = await asyncio.to_thread(get_commits, branch_name=branch, stream_id=stream_id)
        commits_end_time = time.perf_counter()
        branch_info['commits_fetch_time'] = commits_end_time - commits_start_time
        logging.debug(f"Commits for branch {branch}: {commits}")

        if not commits:
            logging.debug(f"No commits found for branch: {branch}")
            branch_info['status'] = 'No commits found'
            return branch_info

        # Получаем последний коммит
        sort_start_time = time.perf_counter()
        commits.sort(key=lambda x: getattr(x, 'createdAt', None), reverse=True)
        sort_end_time = time.perf_counter()
        branch_info['commits_sort_time'] = sort_end_time - sort_start_time

        last_commit = commits[0]
        branch_info['commit_message'] = getattr(last_commit, 'message', None)
        logging.debug(f"Last commit for branch {branch}: {last_commit}")

        try:
            receive_start_time = time.perf_counter()
            transport = ServerTransport(client=client, stream_id=stream_id)
            memory_transport = MemoryTransport()
            res = await asyncio.to_thread(operations.receive, last_commit.referencedObject, transport, memory_transport)
            receive_end_time = time.perf_counter()
            branch_info['receive_time'] = receive_end_time - receive_start_time

            process_start_time = time.perf_counter()
            room_section = extract_check_area_discrepancy(res)
            process_end_time = time.perf_counter()
            branch_info['processing_time'] = process_end_time - process_start_time

            logging.debug(f"Discrepancy rooms for branch {branch}: {room_section}")
            branch_info['rooms'] = room_section
            branch_info['status'] = 'Success'
        except Exception as e:
            logging.error(f"Error processing branch {branch}: {str(e)}")
            branch_info['error'] = str(e)
            branch_info['status'] = 'Error'

        branch_end_time = time.perf_counter()
        branch_info['total_branch_time'] = branch_end_time - branch_start_time
        timing_info[branch] = branch_info
        return branch_info

async def select_project(update: Update, context: CallbackContext):
    selected_project = update.message.text
    logging.debug(f"Selected project: {selected_project}")

    context.user_data['selected_project'] = selected_project
    await update.message.reply_text(f"Выбран проект: {selected_project}")

    try:
        total_start_time = time.perf_counter()

        stream_id = get_speckle_stream_id(selected_project)
        context.user_data['stream_id'] = stream_id
        logging.debug(f"Stream ID: {stream_id}")

        branches = list_branches(stream_id, print_to_console=False)

        logging.debug(f"Starting discrepancy check for project: {selected_project}")

        semaphore = asyncio.Semaphore(3)

        tasks = []
        timing_info = {}

        for branch in branches:
            tasks.append(process_branch(branch, stream_id, semaphore, timing_info))

        results = await asyncio.gather(*tasks)

        total_end_time = time.perf_counter()
        total_time = total_end_time - total_start_time

        discrepancy_reports = [result for result in results if result]

        result_message = ""
        for report in discrepancy_reports:
            branch = report.get('branch', 'Unknown')
            commit_message = report.get('commit_message', 'No commit message')
            status = report.get('status', 'Unknown status')
            error = report.get('error', None)
            rooms = report.get('rooms', None)

            result_message += f"Проверка ветки: {branch}\nСообщение коммита: {commit_message}\n\n"
            if status == 'Success':
                if rooms:
                    result_message += format_discrepancy_rooms(rooms)
                else:
                    result_message += "Расхождений не найдено.\n\n"
            elif status == 'Error':
                result_message += f"Ошибка: {error}\n\n"
            else:
                result_message += f"Статус: {status}\n\n"

            result_message += "-" * 40 + "\n"

        messages = split_message(result_message)
        for idx, msg in enumerate(messages):
            msg_length = len(msg.encode('utf-8'))
            logging.debug(f"Отправка сообщения {idx+1}/{len(messages)} с длиной {msg_length} байт")
            try:
                await update.message.reply_text(msg)
            except Exception as e:
                logging.error(f"Ошибка при отправке сообщения: {e}")
                await update.message.reply_text(f"Произошла ошибка при отправке сообщения: {e}")
        logging.debug("Discrepancy check completed.")
    except Exception as e:
        logging.error(f"Error: {e}")
        await update.message.reply_text(f"Произошла ошибка: {e}")

    return ConversationHandler.END

async def cancel(update: Update, context: CallbackContext):
    await update.message.reply_text('Операция отменена.')
    logging.debug('Operation cancelled.')
    return ConversationHandler.END

check_area_discrepancy_handler = ConversationHandler(
    entry_points=[CommandHandler('check_rooms_area', start_check_area_discrepancy)],
    states={
        SELECT_PROJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_project)],
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)
