import logging
from specklepy.api.client import SpeckleClient
from telegram.ext import ContextTypes
from telegram_bot.config import HOST, SPECKLE_TOKEN

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# Настройка клиента Speckle
speckle_client = SpeckleClient(host=HOST)
speckle_client.authenticate_with_token(SPECKLE_TOKEN)

# Вспомогательные функции
async def delete_webhook(context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.delete_webhook(drop_pending_updates=True)
