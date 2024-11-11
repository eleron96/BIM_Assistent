import asyncio

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, \
    CallbackQueryHandler, MessageHandler, CommandHandler, filters
from datetime import datetime
import logging

from telegram_bot.handlers import echo
from telegram_bot.speckle.speckle_projects import get_speckle_projects
from telegram_bot.speckle.speckle_models import get_project_models_and_commits
from telegram_bot.utils import speckle_client, HOST

SELECTING_PROJECT, SHOWING_MODELS, MAIN_MENU = range(3)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def show_projects(update: Update,
                        context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        projects = await asyncio.to_thread(
            lambda: get_speckle_projects(speckle_client))
        buttons = [
            [InlineKeyboardButton(project.name, callback_data=project.id)] for
            project in projects]
        reply_markup = InlineKeyboardMarkup(buttons)

        await update.message.reply_text(
            text="Проекты:",
            reply_markup=reply_markup,
            disable_notification=True,
            reply_to_message_id=update.message.message_id
        )
        return SELECTING_PROJECT
    except Exception as e:
        logger.error(f"Error in show_projects: {e}")
        await update.message.reply_text(text="Ошибка при получении проектов.")
        return ConversationHandler.END


async def project_selected(update: Update,
                           context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    project_id = query.data

    try:
        models = await asyncio.to_thread(
            lambda: get_project_models_and_commits(speckle_client, project_id))
        messages = []

        for model in models:
            last_commit_id = model['latest_commit_id']
            if last_commit_id:
                last_commit_date = datetime.strptime(
                    model['latest_commit_message'], "%d.%m.%y").strftime(
                    "%d %B %Y")
                commit_message = (
                    f"*Имя модели* - {model['name']}\n"
                    f"*Дата последнего коммита* - {last_commit_date}"
                )
                commit_button = InlineKeyboardButton(
                    "Ссылка на последний коммит",
                    url=f"{HOST}streams/{project_id}/commits/{last_commit_id}"
                )
            else:
                commit_message = f"❗️В модели *{model['name']}*, коммитов нет"
                commit_button = None

            messages.append({"text": commit_message, "button": commit_button})

        for message in messages:
            reply_markup = InlineKeyboardMarkup([[message["button"]]]) if \
            message["button"] else None
            await query.message.reply_text(text=message["text"],
                                           parse_mode='Markdown',
                                           reply_markup=reply_markup)

        return SHOWING_MODELS
    except Exception as e:
        logger.error(f"Error in project_selected: {e}")
        await query.message.reply_text(
            text="Ошибка при обработке выбора проекта.")
        return ConversationHandler.END


async def exit_command(update: Update,
                       context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        'Вы вернулись к начальному состоянию. Введите команду.')
    return ConversationHandler.END


conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("/projects"), show_projects)],
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
