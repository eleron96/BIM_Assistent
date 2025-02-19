import aiohttp
from telegram import Update
from telegram.ext import CallbackContext
from telegram.ext import CommandHandler
from telegram_bot.handlers.security_check import is_user_whitelisted


# Функции для получения данных с API

async def get_linkedin_latest(profile_id: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"http://194.35.119.49:8090/linkedin/latest?profile_id={profile_id}") as resp:
            data = await resp.json()
            print(f"LinkedIn latest data: {data}")  # Логируем ответ от API
            return data

async def get_youtube_latest(channel_id: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"http://194.35.119.49:8090/youtube/latest?channel_id={channel_id}") as resp:
            data = await resp.json()
            print(f"YouTube latest data: {data}")  # Логируем ответ от API
            return data

async def get_medium_latest(username: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"http://194.35.119.49:8090/medium/latest?username={username}") as resp:
            data = await resp.json()
            print(f"Medium latest data: {data}")  # Логируем ответ от API
            return data

async def get_statistics_linkedin(profile_id: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"http://194.35.119.49:8090/linkedin/statistics?profile_id={profile_id}") as resp:
            return await resp.json()

async def get_statistics_youtube(channel_id: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"http://194.35.119.49:8090/youtube/statistics?channel_id={channel_id}") as resp:
            return await resp.json()

async def get_statistics_medium(username: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"http://194.35.119.49:8090/medium/statistics?username={username}") as resp:
            return await resp.json()


# Функция для получения данных по подписчикам и форматирования ответа
async def get_followers_data():
    profile_id = "gamsakhurdiya"  # LinkedIn
    channel_id = "UCRhID0powzDpE4D2KuVKGHg"  # YouTube
    username = "Eleron"  # Medium

    # Запрашиваем данные с API
    linkedin_data = await get_linkedin_latest(profile_id)
    linkedin_stats = await get_statistics_linkedin(profile_id)

    youtube_data = await get_youtube_latest(channel_id)
    youtube_stats = await get_statistics_youtube(channel_id)

    medium_data = await get_medium_latest(username)
    medium_stats = await get_statistics_medium(username)

    # Получаем количество подписчиков с правильным парсингом
    linkedin_followers = linkedin_data.get('latest_data', {}).get('count', 'N/A')
    youtube_followers = youtube_data.get('latest_data', {}).get('count', 'N/A')
    medium_followers = medium_data.get('latest_data', {}).get('count', 'N/A')

    # Форматируем данные для ответа
    response = f"""
*📊 Подписчики по платформам:*

**LinkedIn**:
- **Подписчиков**: {linkedin_followers}
- **Изменения за день**: {linkedin_stats.get('statistics', {}).get('24h', 'N/A')}%

**YouTube**:
- **Подписчиков**: {youtube_followers}
- **Изменения за месяц**: {youtube_stats.get('statistics', {}).get('month', 'N/A')}%

**Medium**:
- **Подписчиков**: {medium_followers}
- **Изменения за месяц**: {medium_stats.get('statistics', {}).get('month', 'N/A')}%
"""
    return response



# Хендлер для команды /subs_status
async def subs_handler(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not is_user_whitelisted(user_id):
        await update.message.reply_text('Отказано в доступе.')
        return

    # Получаем данные
    response = await get_followers_data()

    # Отправляем ответ
    await update.message.reply_text(response, parse_mode="Markdown")
