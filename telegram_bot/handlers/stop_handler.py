from telegram import Update
from telegram.ext import ContextTypes

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Бот остановлен.')
    await context.application.stop()
