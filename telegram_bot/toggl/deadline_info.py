import aiohttp
import logging
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import CallbackContext

# Настройка логирования
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levellevel)s - %(message)s',
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

async def get_workspace_milestones(session, workspace_id):
    url = f"https://api.plan.toggl.com/api/v5/{workspace_id}/milestones"
    logging.debug(f"Запрос URL: {url}")
    return await fetch(session, url)

def format_date(date_str):
    try:
        date_obj = datetime.fromisoformat(date_str)
        return date_obj.strftime('%d %b %y')
    except ValueError:
        return date_str

def extract_code_and_name(name):
    if '[' in name and ']' in name:
        code_start = name.find('[') + 1
        code_end = name.find(']')
        code = name[code_start:code_end]
        clean_name = name[code_end + 1:].strip()
        return code, clean_name
    return '', name

async def fetch_milestones():
    async with aiohttp.ClientSession() as session:
        milestones = await get_workspace_milestones(session, workspace_id)
        return milestones

async def deadline_info(update: Update, context: CallbackContext):
    milestones = await fetch_milestones()

    if isinstance(milestones, list):
        # Разделение на прошедшие и предстоящие milestones
        past_milestones = []
        upcoming_milestones = []
        now = datetime.now().date()
        next_month = now + timedelta(days=30)

        for milestone in milestones:
            deadline_str = milestone.get('date', '')
            if deadline_str:
                deadline = datetime.fromisoformat(deadline_str).date()
                if deadline < now:
                    past_milestones.append(milestone)
                elif now <= deadline <= next_month:
                    upcoming_milestones.append(milestone)

        # Сортировка milestones по дате
        past_milestones.sort(key=lambda x: datetime.fromisoformat(x.get('date')).date())
        upcoming_milestones.sort(key=lambda x: datetime.fromisoformat(x.get('date')).date())

        # Формирование текста отчета
        report_lines = ["Completed milestones:"]
        for milestone in past_milestones:
            deadline = format_date(milestone.get('date', 'N/A'))
            name = milestone.get('name', 'N/A')
            milestone_id = milestone.get('id', 'N/A')
            project_code, clean_name = extract_code_and_name(name)
            report_lines.append(f"{deadline:<8}|{clean_name[:21]:<21}|{project_code[:10]:<7}")

        report_lines.append("\nUpcoming milestones:")
        for milestone in upcoming_milestones:
            deadline = format_date(milestone.get('date', 'N/A'))
            name = milestone.get('name', 'N/A')
            milestone_id = milestone.get('id', 'N/A')
            project_code, clean_name = extract_code_and_name(name)
            report_lines.append(f"{deadline:<8}|{clean_name[:21]:<21}|{project_code[:10]:<7}")

        report_text = "\n".join(report_lines)
        await update.message.reply_text(f"```\n{report_text}\n```", parse_mode="Markdown", disable_notification=True)
    else:
        logging.error(milestones.get("error", "Неизвестная ошибка"))
        await update.message.reply_text("Ошибка получения информации о вехах", parse_mode="Markdown", disable_notification=True)
