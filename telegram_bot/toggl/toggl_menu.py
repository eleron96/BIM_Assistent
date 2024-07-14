import logging
import coloredlogs
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CallbackQueryHandler, CommandHandler

from telegram_bot.toggl.stat_by_user import stat_by_user
from telegram_bot.toggl.stat_by_projects import stat_by_projects
from telegram_bot.toggl.deadline_info import deadline_info
from telegram_bot.toggl.calendar_add import generate_calendar_link

# Настройка логирования
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)
coloredlogs.install(level='DEBUG', fmt=LOG_FORMAT)

logger = logging.getLogger(__name__)

function_names = {
    'stat_by_user': 'Stat by User',
    'stat_by_projects': 'Stat by Projects',
    'deadline_info': 'Deadline Info',
    'add_to_calendar': 'Add to Calendar',
    'back': 'Back'
}

async def toggl_menu(update: Update, context: CallbackContext, edit_message=False, from_info=False) -> None:
    keyboard = [
        [
            InlineKeyboardButton("Stat by User", callback_data='stat_by_user'),
            InlineKeyboardButton("Stat by Projects", callback_data='stat_by_projects')
        ],
        [
            InlineKeyboardButton("Deadline Info", callback_data='deadline_info')
        ],
        [
            InlineKeyboardButton("Exit", callback_data='exit_menu')
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        logger.info("Displaying menu to the user.")
        await update.message.reply_text('Please choose:', reply_markup=reply_markup, disable_notification=True)
    elif update.callback_query and update.callback_query.message:
        if edit_message:
            logger.info("Editing existing message to display menu.")
            await update.callback_query.edit_message_text('Please choose:', reply_markup=reply_markup)
        else:
            logger.info("Displaying menu to the user.")
            await update.callback_query.message.reply_text('Please choose:', reply_markup=reply_markup, disable_notification=True)
    else:
        logger.error("No valid message or callback_query in toggl_menu")







async def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    try:
        await query.answer()
        logger.debug(f"Callback query answered: {query.data}")
    except Exception as e:
        logger.error(f"Failed to answer callback query: {e}")
        return

    try:
        if query.data == 'back_from_info':
            logger.info("User chose to go back from info. Returning to menu.")
            await query.delete_message()
            await toggl_menu(update, context, edit_message=False, from_info=False)
            return
        elif query.data == 'exit_menu':
            logger.info("User chose to exit menu and delete message.")
            await query.delete_message()
            return

        await query.delete_message()

        if query.data == 'stat_by_user':
            logger.debug("Calling stat_by_user function")
            await stat_by_user(query, context)
        elif query.data == 'stat_by_projects':
            logger.debug("Calling stat_by_projects function")
            await stat_by_projects(query, context)
        elif query.data == 'deadline_info':
            logger.debug("Calling deadline_info function")
            await deadline_info(query, context)
        elif query.data == 'add_to_calendar':
            logger.debug("Calling generate_calendar_link function")
            await generate_calendar_link(query, context)
    except Exception as e:
        logger.error(f"Error handling button callback: {e}")








toggl_menu_handler = CallbackQueryHandler(button)

def register_handlers(app):
    app.add_handler(CommandHandler("toggl_menu", toggl_menu))
    app.add_handler(toggl_menu_handler)
