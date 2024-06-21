# bot.py
from telegram.ext import ApplicationBuilder
from telegram_bot.config import TOKEN
from telegram_bot.handlers import register_handlers

def main() -> None:
    app = ApplicationBuilder().token(TOKEN).build()

    app.bot.delete_webhook(drop_pending_updates=True)

    register_handlers(app)

    app.run_polling()

if __name__ == '__main__':
    main()
