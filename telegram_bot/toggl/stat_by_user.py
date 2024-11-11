import aiohttp
import asyncio
import logging
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import CallbackContext

# Настройка логирования
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Загрузка переменных окружения из файла .env
load_dotenv()

# Получение токена доступа из переменной окружения
access_token = os.getenv('ACCESS_TOKEN')

if not access_token:
    logging.error("ACCESS_TOKEN не найден в .env файле")
    exit(1)

# Идентификатор рабочего пространства
workspace_id = 880544

# Заголовки запроса
headers = {
    "Authorization": f"Bearer {access_token}"
}


async def fetch(session, url, retries=3):
    for attempt in range(retries):
        async with session.get(url, headers=headers) as response:
            content_type = response.headers.get('Content-Type', '')
            if response.status == 429:
                retry_after = int(response.headers.get('Retry-After', 1))
                logging.warning(
                    f"Rate limit exceeded. Retrying in {retry_after} seconds...")
                await asyncio.sleep(retry_after)
                continue
            if 'application/json' in content_type:
                return await response.json()
            else:
                text = await response.text()
                logging.error(
                    f"Unexpected content type: {content_type}, URL: {url}, Response: {text}")
                return {"error": f"Unexpected content type: {content_type}"}
    return {"error": "Exceeded maximum retries"}


async def get_workspace_members(session, workspace_id):
    url = f"https://api.plan.toggl.com/api/v5/{workspace_id}/members"
    logging.debug(f"Запрос URL: {url}")
    return await fetch(session, url)


async def get_all_tasks(session, workspace_id):
    url = f"https://api.plan.toggl.com/api/v5/{workspace_id}/tasks"
    logging.debug(f"Запрос URL: {url}")
    return await fetch(session, url)


async def get_task_detail(session, workspace_id, task_id):
    url = f"https://api.plan.toggl.com/api/v5/{workspace_id}/tasks/{task_id}"
    logging.debug(f"Запрос URL: {url}")
    return await fetch(session, url)


def create_members_dict(workspace_members):
    members_by_id = {}
    members_by_membership_id = {}
    members_by_name = {}

    for member in workspace_members:
        user_id = member['id']
        membership_id = member['membership_id']
        name = member['name']

        members_by_id[user_id] = member
        members_by_membership_id[membership_id] = member
        members_by_name[name] = member

    return members_by_id, members_by_membership_id, members_by_name


def filter_tasks_by_date(tasks, days=30):
    recent_tasks = []
    cutoff_date = datetime.now() - timedelta(days=days)
    for task in tasks:
        created_at = datetime.fromisoformat(
            task['created_at'].replace('Z', '+00:00'))
        start_date = datetime.fromisoformat(
            task['start_date'].replace('Z', '+00:00')) if task.get(
            'start_date') else None
        end_date = datetime.fromisoformat(
            task['end_date'].replace('Z', '+00:00')) if task.get(
            'end_date') else None

        if created_at >= cutoff_date or (
                start_date and start_date >= cutoff_date) or (
                end_date and end_date >= cutoff_date):
            recent_tasks.append(task)
    return recent_tasks


async def get_users_info(session, workspace_id):
    workspace_members = await get_workspace_members(session, workspace_id)
    if "error" not in workspace_members:
        return create_members_dict(workspace_members)
    else:
        logging.error(workspace_members["error"])
        return None, None, None


async def generate_stat_by_user():
    async with aiohttp.ClientSession() as session:
        members_by_id, members_by_membership_id, members_by_name = await get_users_info(
            session, workspace_id)

        if members_by_id and members_by_membership_id and members_by_name:
            all_tasks = await get_all_tasks(session, workspace_id)

            if "error" not in all_tasks:
                recent_tasks = filter_tasks_by_date(all_tasks)

                user_task_count = {member_id: 0 for member_id in
                                   members_by_id.keys()}
                user_task_done_count = {member_id: 0 for member_id in
                                        members_by_id.keys()}
                user_inprogress_tasks = {member_id: [] for member_id in
                                         members_by_id.keys()}

                task_weights = {'Done': 0.8, 'In progress': 1.1}

                tasks = []
                for task in recent_tasks:
                    task_id = task['id']

                    tasks.append(
                        get_task_detail(session, workspace_id, task_id))

                responses = await asyncio.gather(*tasks)

                for task_detail in responses:
                    if "error" not in task_detail:
                        workspace_members_ids = task_detail.get(
                            "workspace_members", [])
                        plan_status = task_detail.get("plan_status", {}).get(
                            "name")

                        for membership_id in workspace_members_ids:
                            if membership_id in members_by_membership_id:
                                user_id = \
                                members_by_membership_id[membership_id]['id']
                                user_task_count[user_id] += 1
                                if plan_status == "Done":
                                    user_task_done_count[user_id] += 1
                                elif plan_status == "In progress":
                                    user_inprogress_tasks[user_id].append(
                                        task_detail['id'])

                # Логи списка задач "In progress" по пользователям
                for user_id, inprogress_tasks in user_inprogress_tasks.items():
                    user_name = members_by_id[user_id]['name']
                    logging.debug(
                        f"User {user_name} (ID: {user_id}) has the following In progress tasks: {inprogress_tasks}")

                # Формирование результата
                table_data = []
                for user_id, task_count in user_task_count.items():
                    user_name = members_by_id[user_id]['name']
                    task_done_count = user_task_done_count[user_id]
                    task_inprogress_count = len(user_inprogress_tasks[user_id])

                    # Расчет веса
                    done_weight = task_done_count * task_weights['Done']
                    inprogress_weight = task_inprogress_count * task_weights[
                        'In progress']
                    total_weight = done_weight + inprogress_weight

                    if total_weight > 0:
                        done_percentage = done_weight / total_weight
                    else:
                        done_percentage = 0

                    num_done = int(done_percentage * 5)
                    num_inprogress = 5 - num_done
                    task_symbols = '🟩' * num_done + '🟨' * num_inprogress

                    table_data.append([
                        user_id,
                        user_name,
                        task_symbols,
                        task_done_count,
                        task_inprogress_count,
                        task_count
                    ])

                return table_data
            else:
                return all_tasks["error"]
        else:
            return "Ошибка получения информации о пользователях"


def format_table_data(data):
    # Форматирование заголовка таблицы
    header = f"{'Name':<7} |{'Tasks':<12}|{'✅':<2}|{'🚧':<2}|{'🗂️':<2}"
    table_text = header + "\n" + '-' * len(header) + "\n"

    name_map = {
        'Нико Гамсахурдия': 'Нико Г.',
        'Крутов Алексей': 'Леша К.',
        'Анастасия Димитриева': 'Настя Д.',
        'r.iusov@speech.su': 'Роман Ю.',
        'd.vasilev': 'Дима В.',
        'Дмитрий Константинов': 'Дима К.',
        'Лилия Щедрина': 'Лиля Щ.',
        'g.novak': 'Гоша Н.',
        'Денисов Иван': 'Иван Д.',
        'Света':'Света П.'
    }

    for row in data:
        user_id, original_name, tasks, done, remaining, total = row
        display_name = name_map.get(original_name, original_name)
        table_text += f"{display_name:<8}|{tasks:<6}|{done:<3}|{remaining:<3}|{total:<3}\n"

    return table_text


async def stat_by_user(update: Update, context: CallbackContext):
    table_data = await generate_stat_by_user()
    if isinstance(table_data, str):
        await update.message.reply_text(table_data)
    else:
        table_text = format_table_data(table_data)
        await update.message.reply_text(f"```\n{table_text}\n```",
                                        parse_mode="Markdown")
