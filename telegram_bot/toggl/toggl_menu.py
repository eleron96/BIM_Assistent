import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CallbackQueryHandler, CommandHandler

from telegram_bot.toggl.stat_by_user import stat_by_user
from telegram_bot.toggl.stat_by_projects import stat_by_projects

# Настройка логирования
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Маппинг для названий функций
function_names = {
    'stat_by_user': 'Stat by User',
    'stat_by_projects': 'Stat by Projects',
    'back': 'Back'
}

async def toggl_menu(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [
            InlineKeyboardButton("Stat by User", callback_data='stat_by_user'),
            InlineKeyboardButton("Stat by Projects", callback_data='stat_by_projects')
        ],
        [
            InlineKeyboardButton("Back", callback_data='back')
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text('Please choose:', reply_markup=reply_markup, disable_notification=True)
    elif update.callback_query and update.callback_query.message:
        await update.callback_query.message.reply_text('Please choose:', reply_markup=reply_markup, disable_notification=True)
    else:
        logging.error("No valid message or callback_query in toggl_menu")

async def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    try:
        await query.answer()
    except Exception as e:
        logging.error(f"Failed to answer callback query: {e}")
        return

    try:
        if query.data == 'back':
            # Удаление сообщения и возврат к меню без вывода выбора пользователя
            await query.delete_message()
            return

        # Удаление текущего сообщения с меню
        await query.delete_message()

        # Получение читабельного названия функции из маппинга
        readable_name = function_names.get(query.data, query.data)

        # Отправка сообщения с информацией о выбранной статистике
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Selected option: {readable_name}", disable_notification=True)

        # Вызов соответствующей функции для вывода статистики
        if query.data == 'stat_by_user':
            await stat_by_user(query, context)
        elif query.data == 'stat_by_projects':
            await stat_by_projects(query, context)
    except Exception as e:
        logging.error(f"Error handling button callback: {e}")

toggl_menu_handler = CallbackQueryHandler(button)

def register_handlers(app):
    app.add_handler(CommandHandler("toggl_menu", toggl_menu))
    app.add_handler(toggl_menu_handler)
