from telegram.ext import CommandHandler
from telegram_bot.handlers.start_handler import start
from telegram_bot.handlers.help_handler import help_command
from telegram_bot.handlers.stop_handler import stop_command
from telegram_bot.handlers.echo_handler import echo
from telegram_bot.server.server_status import server_status
from telegram_bot.server.server_restart import server_restart
from telegram_bot.toggl.toggl_menu import toggl_menu, toggl_menu_handler
from telegram_bot.ai_tools.gpt_handler import gpt_conversation_handler
from telegram_bot.subs_tool.subs_handler import subs_handler


def register_handlers(app):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("server", server_status))
    app.add_handler(CommandHandler("restart", server_restart))
    app.add_handler(CommandHandler("toggl_menu", toggl_menu))
    app.add_handler(gpt_conversation_handler)

    # Добавляем CallbackQueryHandler для обработки нажатий кнопок
    app.add_handler(toggl_menu_handler)
    app.add_handler(CommandHandler("subs_status", subs_handler))
