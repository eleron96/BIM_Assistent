from telegram.ext import CommandHandler, MessageHandler, filters
from telegram_bot.handlers.start_handler import start
from telegram_bot.handlers.help_handler import help_command
from telegram_bot.handlers.stop_handler import stop_command
from telegram_bot.handlers.echo_handler import echo
from telegram_bot.handlers.server_status import server_status
from telegram_bot.handlers.server_restart import server_restart
from telegram_bot.handlers.projects_handler import conv_handler

def register_handlers(app):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("stop", stop_command))
    app.add_handler(CommandHandler("server", server_status))
    app.add_handler(CommandHandler("restart", server_restart))
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
