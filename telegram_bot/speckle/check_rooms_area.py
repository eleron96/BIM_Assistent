# telegram_bot/handlers/check_rooms_area.py

import logging
from specklepy.api import operations
from specklepy.transports.server import ServerTransport
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
        other_params = {}
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
                else:
                    other_params[param_value.name] = param_value.value

        if area is not None and rounded_area is not None and abs(area - rounded_area) > 0.4:
            discrepancy_info = {
                'id': obj.elementId,
                'name': obj.name,
                'area': area,
                'rounded_area': rounded_area,
                'level_name': level_name,
                'room_number': room_number
            }
            discrepancy_info.update(other_params)
            discrepancy_rooms.append(discrepancy_info)

    for element in getattr(obj, 'elements', []):
        discrepancy_rooms.extend(extract_check_area_discrepancy(element))

    return discrepancy_rooms

def format_discrepancy_rooms(discrepancy_rooms):
    if discrepancy_rooms:
        message = "Найдены расхождения в помещениях:\n\n"
        for index, room in enumerate(discrepancy_rooms, start=1):
            message += (f"№: {index}\n"
                        f"ID: {room['id']}\n"
                        f"Название: {room['name']}\n"
                        f"Площадь: {room['area']}\n"
                        f"Округленная Площадь: {room['rounded_area']}\n"
                        f"Уровень: {room['level_name']}\n"
                        f"Номер комнаты: {room['room_number']}\n"
                        f"Другие параметры: {room.get('other_params', 'Нет')}\n\n")
        return message
    else:
        return "Проверка завершена. Расхождений не найдено."

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

async def start_check_area_discrepancy(update: Update, context: CallbackContext):
    user = update.message.from_user
    logging.debug(f"User {user.first_name} initiated check_area_discrepancy command.")

    projects = get_speckle_projects(client)
    logging.debug(f"Retrieved projects: {projects}")
    project_list = [project.name for project in projects]

    reply_keyboard = [[project] for project in project_list]
    await update.message.reply_text(
        "Please choose a project:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    logging.debug("Sent project selection message.")

    return SELECT_PROJECT

async def select_project(update: Update, context: CallbackContext):
    selected_project = update.message.text
    logging.debug(f"Selected project: {selected_project}")

    context.user_data['selected_project'] = selected_project
    await update.message.reply_text(f"Selected project: {selected_project}")

    try:
        stream_id = get_speckle_stream_id(selected_project)
        context.user_data['stream_id'] = stream_id
        logging.debug(f"Stream ID: {stream_id}")

        branches = list_branches(stream_id, print_to_console=False)
        discrepancy_reports = []

        logging.debug(f"Starting discrepancy check for project: {selected_project}")

        for branch in branches:
            logging.debug(f"Processing branch: {branch}")
            if branch.lower() == "main":
                continue

            commits = get_commits(branch_name=branch, stream_id=stream_id)
            logging.debug(f"Commits for branch {branch}: {commits}")
            if not commits:
                logging.debug(f"No commits found for branch: {branch}")
                continue

            commits.sort(key=lambda x: getattr(x, 'createdAt', None), reverse=True)
            last_commit = commits[0]
            logging.debug(f"Last commit for branch {branch}: {last_commit}")

            try:
                transport = ServerTransport(client=client, stream_id=stream_id)
                res = operations.receive(last_commit.referencedObject, transport)
                room_section = extract_check_area_discrepancy(res)
                logging.debug(f"Discrepancy rooms for branch {branch}: {room_section}")
                discrepancy_reports.append((branch, getattr(last_commit, 'message', None), room_section))
            except Exception as e:
                logging.error(f"Error processing branch {branch}: {str(e)}")
                discrepancy_reports.append((branch, "Error: " + str(e), None))

        result_message = ""
        for branch, commit_message, rooms in discrepancy_reports:
            result_message += f"Проверка ветки: {branch}\nСообщение коммита: {commit_message}\n\n"
            if rooms:
                result_message += format_discrepancy_rooms(rooms)
            else:
                result_message += "Расхождений не найдено.\n\n"
            result_message += "-" * 40 + "\n"

        await update.message.reply_text(result_message)
        logging.debug("Discrepancy check completed.")
    except Exception as e:
        logging.error(f"Error: {e}")
        await update.message.reply_text(f"An error occurred: {e}")

    return ConversationHandler.END

async def cancel(update: Update, context: CallbackContext):
    await update.message.reply_text('Operation cancelled.')
    logging.debug('Operation cancelled.')
    return ConversationHandler.END

check_area_discrepancy_handler = ConversationHandler(
    entry_points=[CommandHandler('check_rooms_area', start_check_area_discrepancy)],
    states={
        SELECT_PROJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_project)],
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)
