import os
import logging
import requests
from telegram import Update
from telegram.ext import CallbackContext
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()


async def restart_server():
    try:
        logger.debug(
            "Попытка выполнить команду перезагрузки через Timeweb Cloud API")
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + os.getenv('TIMEWEB_CLOUD_TOKEN', ''),
        }
        response = requests.post(
            'https://api.timeweb.cloud/api/v1/servers/3109085/reboot',
            headers=headers)

        if response.status_code == 200:
            logger.debug("Команда перезагрузки выполнена успешно")
        else:
            logger.error(
                f"Ошибка при выполнении команды перезагрузки: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Ошибка при выполнении команды перезагрузки: {e}")


async def server_restart(update: Update, context: CallbackContext):
    # Определяем имя пользователя, под которым работает скрипт
    user_name = os.popen("whoami").read().strip()
    logger.debug(f"Скрипт выполняется под пользователем: {user_name}")

    user = update.message.from_user
    await update.message.reply_text(
        f"🔄 Перезагрузка сервера, {user.first_name}...\n"
        f"Скрипт выполняется под пользователем: {user_name}"
    )

    # Перезагружаем сервер
    await restart_server()
