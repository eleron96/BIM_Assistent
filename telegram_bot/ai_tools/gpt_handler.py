import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import CallbackContext, CommandHandler, MessageHandler, filters, ConversationHandler, ApplicationBuilder, JobQueue
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
        model="gpt-4-turbo",
        messages=messages
    )
    return response.choices[0].message.content.strip()

# Функция для завершения сессии по таймеру
async def timeout(context: CallbackContext):
    job = context.job
    chat_id = job.data['chat_id']

    if chat_id in last_interaction_times:
        elapsed_time = time.time() - last_interaction_times[chat_id]
        logger.info(f"Прошло времени с последнего взаимодействия для чата {chat_id}: {elapsed_time:.2f} секунд")

        if elapsed_time > 300:  # 300 секунд
            logger.info(f"Таймер завершает сессию для чата {chat_id}")
            await cancel(None, context, chat_id)

# Хэндлер для команды /gpt
async def start_gpt(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id

    if chat_id not in chat_histories:
        chat_histories[chat_id] = [{"role": "system", "content": "You are a helpful assistant."}]
    last_interaction_times[chat_id] = time.time()

    # Установка таймера на завершение сессии через 300 секунд
    context.job_queue.run_once(timeout, 300, data={'chat_id': chat_id})

    await context.bot.send_message(chat_id=chat_id, text="Напишите ваш вопрос помощнику.")
    logger.info(f"Таймер установлен для чата {chat_id}")
    return ASKING

# Хэндлер для обработки сообщений пользователя
async def handle_message(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id

    # Проверка, активна ли сессия
    if chat_id not in chat_histories:
        await context.bot.send_message(chat_id=chat_id, text="Сессия была завершена. Начните новую.")
        return ConversationHandler.END

    user_input = update.message.text
    last_interaction_times[chat_id] = time.time()

    # Сброс таймера
    current_jobs = context.job_queue.get_jobs_by_name(f'timeout_{chat_id}')
    for job in current_jobs:
        job.schedule_removal()
    context.job_queue.run_once(timeout, 300, data={'chat_id': chat_id}, name=f'timeout_{chat_id}')

    logger.info(f"Таймер сброшен для чата {chat_id}")

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
async def cancel(update: Update, context: CallbackContext, chat_id=None):
    if update:
        chat_id = update.message.chat_id
    if chat_id is not None:
        chat_histories.pop(chat_id, None)
        last_interaction_times.pop(chat_id, None)
        await context.bot.send_message(chat_id=chat_id, text="Сессия завершена.")
        logger.info(f"Сессия завершена для чата {chat_id}")
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
