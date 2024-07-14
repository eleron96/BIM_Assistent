import logging
import coloredlogs
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CallbackQueryHandler, CommandHandler

from telegram_bot.toggl.stat_by_user import stat_by_user
from telegram_bot.toggl.stat_by_projects import stat_by_projects
from telegram_bot.toggl.deadline_info import deadline_info  # Импортируем функцию

# Настройка логирования
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)
coloredlogs.install(level='DEBUG', fmt=LOG_FORMAT)

# Получение логгера
logger = logging.getLogger(__name__)

# Маппинг для названий функций
function_names = {
    'stat_by_user': 'Stat by User',
    'stat_by_projects': 'Stat by Projects',
    'deadline_info': 'Deadline Info',  # Добавляем новую функцию
    'back': 'Back'
}

async def toggl_menu(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [
            InlineKeyboardButton("Stat by User", callback_data='stat_by_user'),
            InlineKeyboardButton("Stat by Projects", callback_data='stat_by_projects')
        ],
        [
            InlineKeyboardButton("Deadline Info", callback_data='deadline_info')  # Новая кнопка в отдельной строке
        ],
        [
            InlineKeyboardButton("Back", callback_data='back')
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        logger.info("Displaying menu to the user.")
        await update.message.reply_text('Please choose:', reply_markup=reply_markup, disable_notification=True)
    elif update.callback_query and update.callback_query.message:
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
        if query.data == 'back':
            # Удаление сообщения и возврат к меню без вывода выбора пользователя
            logger.info("User chose to go back. Deleting message and returning to menu.")
            await query.delete_message()
            return

        # Удаление текущего сообщения с меню
        logger.info(f"User selected option: {query.data}. Deleting menu message.")
        await query.delete_message()

        # Получение читабельного названия функции из маппинга
        readable_name = function_names.get(query.data, query.data)

        # Отправка сообщения с информацией о выбранной статистике
        logger.info(f"Sending selected option message: {readable_name}")
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Selected option: {readable_name}", disable_notification=True)

        # Вызов соответствующей функции для вывода статистики
        if query.data == 'stat_by_user':
            logger.debug("Calling stat_by_user function")
            await stat_by_user(query, context)
        elif query.data == 'stat_by_projects':
            logger.debug("Calling stat_by_projects function")
            await stat_by_projects(query, context)
        elif query.data == 'deadline_info':  # Обработка новой кнопки
            logger.debug("Calling deadline_info function")
            await deadline_info(query, context)
    except Exception as e:
        logger.error(f"Error handling button callback: {e}")

toggl_menu_handler = CallbackQueryHandler(button)

def register_handlers(app):
    app.add_handler(CommandHandler("toggl_menu", toggl_menu))
    app.add_handler(toggl_menu_handler)
