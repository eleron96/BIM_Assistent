import os
import logging
import re
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import CallbackContext, CommandHandler, MessageHandler, filters, ConversationHandler
from openai import OpenAI
import time

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Загрузка API ключа
load_dotenv(dotenv_path='.env')
api_key = os.getenv('openai_api_key')

# Создание клиента OpenAI
client = OpenAI(api_key=api_key)

# Словарь для хранения истории сообщений по чатам
chat_histories = {}
last_interaction_times = {}

# Определение состояния для диалога
ASKING = 1

# Функция для получения ответа от ChatGPT с учетом истории
def fetch_chatgpt_response(messages):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )
    return response.choices[0].message.content.strip()

# Функция для завершения сессии по таймеру
async def check_inactivity(context: CallbackContext):
    for chat_id, last_interaction in list(last_interaction_times.items()):
        if time.time() - last_interaction > 300:  # 5 минут бездействия
            await context.bot.send_message(chat_id=chat_id, text="Время ожидания истекло. Сессия завершена.")
            chat_histories.pop(chat_id, None)
            last_interaction_times.pop(chat_id, None)

# Хэндлер для команды /gpt
async def start_gpt(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id

    if chat_id not in chat_histories:
        chat_histories[chat_id] = [{"role": "system", "content": "You are a helpful assistant."}]
    last_interaction_times[chat_id] = time.time()

    await context.bot.send_message(chat_id=chat_id, text="Напишите ваш вопрос помощнику.")
    return ASKING

# Хэндлер для обработки сообщений пользователя
async def handle_message(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    user_input = update.message.text

    if chat_id not in chat_histories:
        chat_histories[chat_id] = [{"role": "system", "content": "You are a helpful assistant."}]
    last_interaction_times[chat_id] = time.time()

    # Проверка на команду завершения сессии
    if user_input.lower() == 'пока':
        return await cancel(update, context)

    # Добавление вопроса пользователя в историю
    chat_histories[chat_id].append({"role": "user", "content": user_input})

    # Получение ответа от ChatGPT
    response = fetch_chatgpt_response(chat_histories[chat_id])

    # Отправка ответа пользователю
    await context.bot.send_message(chat_id=chat_id, text=response, parse_mode='Markdown')

    # Добавление ответа ChatGPT в историю
    chat_histories[chat_id].append({"role": "assistant", "content": response})

    # Логирование истории сообщений
    log_message_history(chat_id)

    return ASKING

# Хэндлер для команды выхода
async def cancel(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    chat_histories.pop(chat_id, None)
    last_interaction_times.pop(chat_id, None)
    await context.bot.send_message(chat_id=chat_id, text="Сессия завершена.")
    return ConversationHandler.END

def log_message_history(chat_id):
    logger.info(f"История сообщений для чата {chat_id}:")
    for message in chat_histories[chat_id]:
        logger.info(f"{message['role']}: {message['content']}")

# Создание обработчика диалога
gpt_conversation_handler = ConversationHandler(
    entry_points=[CommandHandler('gpt', start_gpt)],
    states={
        ASKING: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)]
    },
    fallbacks=[CommandHandler('cancel', cancel)],
    allow_reentry=True
)

# Добавление задачи для проверки бездействия
def add_inactivity_job(job_queue):
    job_queue.run_repeating(check_inactivity, interval=60, first=60)
