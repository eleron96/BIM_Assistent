import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes,
    CallbackQueryHandler, ConversationHandler
)
from dotenv import load_dotenv
import os
from telegram_bot.speckle_projects import get_speckle_projects
from telegram_bot.speckle_models import get_project_models_and_commits
from datetime import datetime

# Загрузка токена из файла .env
load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')
HOST = os.getenv('HOST')

# Включаем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# Определяем состояния для ConversationHandler
SELECTING_PROJECT, SHOWING_MODELS, MAIN_MENU = range(3)


# Определяем функцию для обработки команд /start и /help
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        'Привет! Отправь мне сообщение, и я верну его тебе!')


async def help_command(update: Update,
                       context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        'Просто отправь мне любое сообщение, и я отвечу тем же.')


async def stop_command(update: Update,
                       context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Бот остановлен.')
    # Остановка бота
    await context.application.stop()


async def exit_command(update: Update,
                       context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        'Вы вернулись к начальному состоянию. Введите команду.')
    return MAIN_MENU


# Функция для обработки запроса "покажи проекты"
async def show_projects(update: Update,
                        context: ContextTypes.DEFAULT_TYPE) -> int:
    projects = get_speckle_projects()
    buttons = [
        [InlineKeyboardButton(f"{project.name}", callback_data=project.id)]
        for project in projects
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(
        text="Проекты:",
        reply_markup=reply_markup
    )
    return SELECTING_PROJECT


# Функция для обработки выбора проекта
async def project_selected(update: Update,
                           context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    project_id = query.data

    # Получение моделей и последних коммитов проекта
    models = get_project_models_and_commits(project_id)
    messages = []
    for model in models:
        last_commit_message = model['latest_commit_message']
        last_commit_id = model['latest_commit_id']
        if last_commit_id:
            last_commit_date = datetime.strptime(last_commit_message,
                                                 "%d.%m.%y").strftime(
                "%d %B %Y")
            commit_message = f"Информация о модели {model['name']}, дата последнего коммита: {last_commit_date}"
            commit_button = InlineKeyboardButton("Ссылка на последний коммит",
                                                 url=f"{HOST}streams/{project_id}/commits/{last_commit_id}")
        else:
            commit_message = f"Информация о модели {model['name']}, коммитов нет"
            commit_button = None

        message = {
            "text": commit_message,
            "button": commit_button
        }
        messages.append(message)

    for message in messages:
        if message["button"]:
            reply_markup = InlineKeyboardMarkup([[message["button"]]])
            await query.message.reply_text(text=message["text"],
                                           reply_markup=reply_markup)
        else:
            await query.message.reply_text(text=message["text"])

    return SHOWING_MODELS


# Функция для обработки текстовых сообщений
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        text=update.message.text,
        reply_to_message_id=update.message.message_id
    )


async def delete_webhook(context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.delete_webhook(drop_pending_updates=True)


def main() -> None:
    # Создаем приложение и передаем ему токен вашего бота.
    app = ApplicationBuilder().token(TOKEN).build()

    # Удаляем вебхук перед началом polling
    app.bot.delete_webhook(drop_pending_updates=True)

    # Определяем ConversationHandler для обработки выбора проекта и показа моделей
    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("/projects"), show_projects)],
        states={
            MAIN_MENU: [
                MessageHandler(filters.Regex("/projects"), show_projects),
            ],
            SELECTING_PROJECT: [
                CallbackQueryHandler(project_selected),
                CommandHandler("exit", exit_command)
            ],
            SHOWING_MODELS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, echo),
                CommandHandler("exit", exit_command)
            ],
        },
        fallbacks=[CommandHandler("exit", exit_command)],
        allow_reentry=True
    )

    # Регистрируем обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("stop", stop_command))
    app.add_handler(conv_handler)

    # Обработчик остальных текстовых сообщений
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Запуск бота
    app.run_polling()


if __name__ == '__main__':
    main()
