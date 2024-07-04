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
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

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


async def fetch(session, url):
    async with session.get(url, headers=headers) as response:
        content_type = response.headers.get('Content-Type', '')
        if 'application/json' in content_type:
            return await response.json()
        else:
            text = await response.text()
            logging.error(f"Unexpected content type: {content_type}, URL: {url}, Response: {text}")
            return {"error": f"Unexpected content type: {content_type}"}

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
    cutoff_date = datetime.now() - timedelta(days=30)
    for task in tasks:
        created_at = datetime.fromisoformat(task['created_at'].replace('Z', '+00:00'))
        if created_at >= cutoff_date:
            recent_tasks.append(task)
    return recent_tasks

async def get_users_info(session, workspace_id):
    workspace_members = await get_workspace_members(session, workspace_id)
    if "error" not in workspace_members:
        return create_members_dict(workspace_members)
    else:
        logging.error(workspace_members["error"])
        return None, None, None

async def stat_by_projects(update: Update, context: CallbackContext):
    async with aiohttp.ClientSession() as session:
        members_by_id, members_by_membership_id, members_by_name = await get_users_info(session, workspace_id)

        if members_by_id and members_by_membership_id and members_by_name:
            all_tasks = await get_all_tasks(session, workspace_id)

            if "error" not in all_tasks:
                recent_tasks = filter_tasks_by_date(all_tasks)

                project_task_count = {}
                project_task_done_count = {}
                project_task_blocked_count = {}

                tasks = []
                for task in recent_tasks:
                    task_id = task['id']

                    tasks.append(get_task_detail(session, workspace_id, task_id))

                responses = await asyncio.gather(*tasks)

                for task_detail in responses:
                    if "error" not in task_detail:
                        project_name = task_detail.get("project", {}).get("name", "Unknown")
                        plan_status = task_detail.get("plan_status", {}).get("name")

                        if project_name not in project_task_count:
                            project_task_count[project_name] = 0
                            project_task_done_count[project_name] = 0
                            project_task_blocked_count[project_name] = 0

                        project_task_count[project_name] += 1
                        if plan_status == "Done":
                            project_task_done_count[project_name] += 1
                        elif plan_status == "Blocked":
                            project_task_blocked_count[project_name] += 1


                # Сортировка проектов по убыванию общего количества задач, с "Unknown" в конце
                sorted_projects = sorted(project_task_count.items(), key=lambda item: (item[0] == "Unknown", -item[1]))

                # Список символов для нумерации проектов
                numbering_symbols = ['0️⃣', '1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣']

                def get_numbering_symbol(index):
                    if index < 10:
                        return numbering_symbols[index]
                    else:
                        tens = index // 10
                        ones = index % 10
                        return numbering_symbols[tens] + numbering_symbols[ones]

                # Весовые коэффициенты
                weight_done = 0.8
                weight_blocked = 1
                weight_remaining = 1.2

                report_lines = []
                for index, (project_name, task_count) in enumerate(sorted_projects):
                    task_done_count = project_task_done_count[project_name]
                    task_blocked_count = project_task_blocked_count[project_name]

                    if task_count > 0:
                        percent_done = task_done_count / task_count
                        percent_blocked = task_blocked_count / task_count
                        percent_remaining = 1 - percent_done - percent_blocked
                    else:
                        percent_done = 0
                        percent_blocked = 0
                        percent_remaining = 1

                    # Применяем весовые коэффициенты
                    adjusted_percent_done = percent_done * weight_done
                    adjusted_percent_blocked = percent_blocked * weight_blocked
                    adjusted_percent_remaining = percent_remaining * weight_remaining

                    total_adjusted_percent = adjusted_percent_done + adjusted_percent_blocked + adjusted_percent_remaining

                    # Нормализуем проценты для шкалы из 10 символов
                    num_symbols = 10
                    num_done = round((adjusted_percent_done / total_adjusted_percent) * num_symbols)
                    num_blocked = round((adjusted_percent_blocked / total_adjusted_percent) * num_symbols)
                    num_remaining = num_symbols - num_done - num_blocked

                    task_symbols = '🟩' * num_done + '🟥' * num_blocked + '🟨' * num_remaining

                    # Получение символа для текущего индекса
                    num_symbol = get_numbering_symbol(index + 1)

                    report_lines.append(f"{num_symbol} {project_name}")
                    report_lines.append(f"├{task_symbols}")
                    report_lines.append(f"├✅Done - {task_done_count}")
                    report_lines.append(f"├🛑Blocked - {task_blocked_count}")
                    report_lines.append(f"├🚧To-do - {task_count - task_done_count - task_blocked_count}")
                    report_lines.append(f"└🗂Total - {task_count}\n")

                report_text = "\n".join(report_lines)
                await update.message.reply_text(f"```\n{report_text}\n```", parse_mode="Markdown")
        else:
            await update.message.reply_text("Ошибка получения информации о пользователях", parse_mode="Markdown")