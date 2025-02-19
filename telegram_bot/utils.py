import logging
from telegram.ext import ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)


# Вспомогательные функции
async def delete_webhook(context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.delete_webhook(drop_pending_updates=True)
