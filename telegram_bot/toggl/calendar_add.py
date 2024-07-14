import aiohttp
import logging
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
from telegram import InputFile
from telegram.ext import CallbackContext
from icalendar import Calendar, Event
import pytz
import io

# Настройка логирования
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
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
            logging.error(
                f"Unexpected content type: {content_type}, URL: {url}, Response: {text}")
            return {"error": f"Unexpected content type: {content_type}"}


async def get_workspace_milestones(session, workspace_id):
    url = f"https://api.plan.toggl.com/api/v5/{workspace_id}/milestones"
    logging.debug(f"Запрос URL: {url}")
    return await fetch(session, url)


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


def create_ics_file(events):
    cal = Calendar()
    for event_name, deadline in events:
        event = Event()
        event.add('summary', event_name)
        event.add('dtstart', deadline)
        event.add('dtend', deadline + timedelta(days=1))
        event.add('dtstamp', datetime.now(pytz.utc))
        event.add('transp', 'TRANSPARENT')
        event.add('X-MICROSOFT-CDO-BUSYSTATUS', 'FREE')
        event.add('X-MICROSOFT-CDO-ALLDAYEVENT', 'TRUE')
        event.add('X-APPLE-TRAVEL-ADVISORY-BEHAVIOR', 'AUTOMATIC')
        event.add('allDay', True)  # Для совместимости с iOS
        cal.add_component(event)
    return cal.to_ical()


async def generate_calendar_link(callback_query, context: CallbackContext):
    logging.debug("Starting generate_calendar_link function")
    milestones = await fetch_milestones()
    logging.debug(f"Fetched milestones: {milestones}")

    events = []

    if isinstance(milestones, list) and len(milestones) > 0:
        for milestone in milestones:
            deadline_str = milestone.get('date', '')
            if deadline_str:
                deadline = datetime.fromisoformat(deadline_str).date()
                now = datetime.now().date()
                if now <= deadline:
                    name = milestone.get('name', 'N/A')
                    project_code, clean_name = extract_code_and_name(name)
                    events.append((clean_name, deadline))

        if events:
            ics_content = create_ics_file(events)
            ics_filename = f"milestones.ics"
            ics_file = io.BytesIO(ics_content)
            ics_file.name = ics_filename
            await context.bot.send_document(
                chat_id=callback_query.message.chat_id, document=ics_file,
                filename=ics_filename)
        else:
            await context.bot.send_message(
                chat_id=callback_query.message.chat_id,
                text="Нет предстоящих вех для добавления в календарь.")
    else:
        logging.error(milestones.get("error", "Неизвестная ошибка"))
        await context.bot.send_message(chat_id=callback_query.message.chat_id,
                                       text="Ошибка получения информации о вехах",
                                       parse_mode="Markdown",
                                       disable_notification=True)
