from telegram import Update
from telegram.ext import ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    welcome_message = (
        "👋 Привет!\n\n"
        "Я ваш BIM Ассистент. Я здесь, чтобы помочь вам управлять вашими проектами и задачами. "
        "Вот что я умею:\n\n"
        "🔍 Отправьте /check_rooms_area, чтобы проверить расхождения в площадях помещений.\n"
        "⚙️ Отправьте /server для получения статуса сервера.\n"
        "🔄 Отправьте /restart для перезагрузки сервера.\n"
        "🕒 Отправьте /toggl_menu, чтобы открыть меню Toggl.\n\n"
        "Просто отправьте мне любое сообщение, и я отвечу тем же! 😊"
    )
    await update.message.reply_text(welcome_message)
