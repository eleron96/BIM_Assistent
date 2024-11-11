import asyncio
import logging
import time
from specklepy.api import operations
from specklepy.transports.server import ServerTransport
from specklepy.transports.memory import MemoryTransport
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, ConversationHandler, \
    MessageHandler, filters
from telegram_bot.speckle.speckle_config import client, get_speckle_stream_id
from telegram_bot.speckle.speckle_projects import get_speckle_projects
from telegram_bot.handlers.security_check import is_user_whitelisted

logging.basicConfig(level=logging.INFO)

SELECT_PROJECT = 0


def get_discrepancy_rooms(obj):
    discrepancy_rooms = []

    if getattr(obj, 'category', None) == 'Помещения' and hasattr(obj,
                                                                 "parameters"):
        param_obj = obj.parameters
        area, rounded_area, level_name, room_number = None, None, None, None

        for param in param_obj.__dict__.values():
            if hasattr(param, 'name'):
                name_lower = param.name.lower()
                if name_lower == 'площадь':
                    area = param.value
                elif name_lower == 'speech_площадь округлённая':
                    rounded_area = param.value
                elif name_lower == 'уровень' and not level_name:
                    level_name = param.value
                elif name_lower == 'номер' and not room_number:
                    room_number = param.value

        if area and rounded_area and abs(area - rounded_area) > 0.4:
            discrepancy_rooms.append({
                'id': obj.elementId,
                'name': obj.name,
                'area': area,
                'rounded_area': rounded_area,
                'level_name': level_name,
                'room_number': room_number
            })

    for element in getattr(obj, 'elements', []):
        discrepancy_rooms.extend(get_discrepancy_rooms(element))

    return discrepancy_rooms


def format_discrepancy_rooms(discrepancy_rooms):
    if not discrepancy_rooms:
        return "Расхождений не найдено.\n\n"

    return "Найдены расхождения в помещениях:\n\n" + "\n\n".join([
        f"№: {i + 1}\nID: {room.get('id', 'N/A')}\nНазвание: {room.get('name', 'N/A')}\n"
        f"Площадь: {room.get('area', 'N/A')}\nОкругленная Площадь: {room.get('rounded_area', 'N/A')}\n"
        f"Уровень: {room.get('level_name', 'N/A')}\nНомер комнаты: {room.get('room_number', 'N/A')}"
        for i, room in enumerate(discrepancy_rooms)
    ]) + "\n\n"


async def get_commits_async(branch_name=None, stream_id=None):
    commits = await asyncio.to_thread(
        lambda: client.commit.list(stream_id, limit=100))
    return [commit for commit in commits if
            not branch_name or getattr(commit, 'branchName', '') == branch_name]


async def list_branches_async(stream_id):
    return [branch.name for branch in
            await asyncio.to_thread(lambda: client.branch.list(stream_id))]


def split_message(message, max_bytes=4000):
    chunks, current_chunk = [], ''
    for line in message.split('\n'):
        encoded_line = (line + '\n').encode('utf-8')
        if len(encoded_line) > max_bytes:
            chunks.extend(
                encoded_line[i:i + max_bytes].decode('utf-8', 'ignore') for i in
                range(0, len(encoded_line), max_bytes))
        elif len((current_chunk + line + '\n').encode('utf-8')) <= max_bytes:
            current_chunk += line + '\n'
        else:
            chunks.append(current_chunk)
            current_chunk = line + '\n'
    if current_chunk:
        chunks.append(current_chunk)
    return chunks


async def start_check_area_discrepancy(update: Update,
                                       context: CallbackContext):
    logging.info(
        f"User {update.message.from_user.first_name} initiated check_area_discrepancy command.")
    project_list = [project.name for project in await asyncio.to_thread(
        lambda: get_speckle_projects(client))]

    await update.message.reply_text(
        "Пожалуйста, выберите проект:",
        reply_markup=ReplyKeyboardMarkup(
            [[project] for project in project_list], one_time_keyboard=True)
    )
    return SELECT_PROJECT


async def process_branch(branch, stream_id, semaphore, timing_info):
    async with semaphore:
        branch_info = {'branch': branch}
        branch_start_time = time.perf_counter()

        commits = await get_commits_async(branch_name=branch,
                                          stream_id=stream_id)
        branch_info[
            'commits_fetch_time'] = time.perf_counter() - branch_start_time

        if not commits:
            branch_info['status'] = 'No commits found'
            return branch_info

        last_commit = max(commits, key=lambda x: getattr(x, 'createdAt', None))
        branch_info['commit_message'] = getattr(last_commit, 'message', None)

        try:
            transport = ServerTransport(client=client, stream_id=stream_id)
            memory_transport = MemoryTransport()

            start_time = time.perf_counter()
            res = await asyncio.to_thread(operations.receive,
                                          last_commit.referencedObject,
                                          transport, memory_transport)
            branch_info['receive_time'] = time.perf_counter() - start_time

            start_time = time.perf_counter()
            branch_info['rooms'] = get_discrepancy_rooms(res)
            branch_info['processing_time'] = time.perf_counter() - start_time
            branch_info['status'] = 'Success'
        except Exception as e:
            branch_info['error'] = str(e)
            branch_info['status'] = 'Error'

        branch_info[
            'total_branch_time'] = time.perf_counter() - branch_start_time
        timing_info[branch] = branch_info
        return branch_info


async def select_project(update: Update, context: CallbackContext):
    if not is_user_whitelisted(update.effective_user.id):
        await update.message.reply_text('Отказано в доступе.')
        return

    selected_project = update.message.text
    context.user_data['selected_project'] = selected_project
    await update.message.reply_text(f"Выбран проект: {selected_project}")

    try:
        stream_id = get_speckle_stream_id(selected_project)

        # Получаем список веток, исключая 'main'
        branches = [branch for branch in await list_branches_async(stream_id) if
                    branch.lower() != "main"]

        semaphore = asyncio.Semaphore(3)
        timing_info = {}

        # Инициализируем сообщение о прогрессе
        progress_message = await update.message.reply_text(
            "Процент выполнения: 0% \n🔄 Инициализация")
        total_branches = len(branches)

        async def update_progress(progress, completed_actions, current_action):
            """Обновление сообщения прогресса с указанием текущего действия и завершенных операций."""
            completed_text = "\n".join(
                f"✅ {action}" for action in completed_actions)
            try:
                await progress_message.edit_text(
                    f"Процент выполнения: {progress}%\n{completed_text}\n\n🔄 {current_action}"
                )
                if progress == 100:
                    await progress_message.delete()  # Удаление сообщения при 100%
            except Exception as e:
                logging.error(f"Ошибка при обновлении сообщения прогресса: {e}")

        tasks = []
        completed_branches = 0
        completed_actions = []

        for branch in branches:
            task = process_branch(branch, stream_id, semaphore, timing_info)
            tasks.append(task)

            async def track_progress(task, branch_name):
                nonlocal completed_branches
                nonlocal completed_actions
                # Обновляем текущий этап до завершения работы
                await update_progress(
                    (completed_branches / total_branches) * 100,
                    completed_actions, f"🔄 Обработка ветки: {branch_name}")

                # Дожидаемся завершения задачи и добавляем галочку только после завершения
                result = await task
                completed_branches += 1
                completed_actions.append(f"Обработка ветки: {branch_name}")

                # Обновляем прогресс с новым завершенным этапом
                progress_percent = (completed_branches / total_branches) * 100
                next_action = "Завершение всех операций" if completed_branches == total_branches else "Обработка следующей ветки"
                await update_progress(int(progress_percent), completed_actions,
                                      next_action)
                return result

            tasks[-1] = track_progress(tasks[-1], branch)

        results = await asyncio.gather(*tasks)

        # Формируем и отправляем результат
        result_message = "\n".join(
            f"Проверка ветки: {report.get('branch', 'Unknown')}\n"
            f"Сообщение коммита: {report.get('commit_message', 'No commit message')}\n"
            f"{format_discrepancy_rooms(report['rooms']) if report['status'] == 'Success' else 'Статус: ' + report.get('status', 'Unknown status')}\n"
            + "-" * 40
            for report in results if report
        )

        for msg in split_message(result_message):
            await update.message.reply_text(msg)

    except Exception as e:
        logging.error(f"Error: {e}")
        await update.message.reply_text(f"Произошла ошибка: {e}")

    return ConversationHandler.END


async def cancel(update: Update, context: CallbackContext):
    await update.message.reply_text('Операция отменена.')
    return ConversationHandler.END


check_area_discrepancy_handler = ConversationHandler(
    entry_points=[
        CommandHandler('check_rooms_area', start_check_area_discrepancy)],
    states={SELECT_PROJECT: [
        MessageHandler(filters.TEXT & ~filters.COMMAND, select_project)]},
    fallbacks=[CommandHandler('cancel', cancel)]
)
