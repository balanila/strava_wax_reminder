from __future__ import annotations

import logging

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from app.config import Config
from app.i18n import LANGUAGE_LABELS, SUPPORTED_LANGUAGES, get_texts, language_from_label
from app.service import ChainWaxService, render_status
from app.state import State
from app.strava import StravaUnavailable

logger = logging.getLogger(__name__)


def build_application(config: Config, service: ChainWaxService) -> Application:
    app = Application.builder().token(config.telegram_bot_token).build()
    app.bot_data["config"] = config
    app.bot_data["service"] = service
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("wax", wax_command))
    app.add_handler(CommandHandler("interval", interval_command))
    app.add_handler(CommandHandler("check", check_command))
    app.add_handler(CommandHandler("language", language_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_button_handler))
    return app


async def send_alert(application: Application, chat_id: int, text: str) -> None:
    try:
        await application.bot.send_message(chat_id=chat_id, text=text)
    except Exception:
        logger.exception("Telegram alert send failed")


def _authorized(update: Update, config: Config) -> bool:
    chat = update.effective_chat
    return chat is not None and chat.id == config.telegram_chat_id


async def _reject_if_unauthorized(update: Update, config: Config) -> bool:
    if _authorized(update, config):
        return False
    if update.effective_message:
        await update.effective_message.reply_text("Unauthorized")
    return True


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config: Config = context.application.bot_data["config"]
    if await _reject_if_unauthorized(update, config):
        return
    state = _service(context).state_store.load()
    await update.effective_message.reply_text(
        get_texts(state.language).choose_language,
        reply_markup=language_keyboard(),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config: Config = context.application.bot_data["config"]
    if await _reject_if_unauthorized(update, config):
        return
    state = _service(context).state_store.load()
    await update.effective_message.reply_text(
        get_texts(state.language).help,
        reply_markup=main_keyboard(state),
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config: Config = context.application.bot_data["config"]
    if await _reject_if_unauthorized(update, config):
        return
    state = _service(context).state_store.load()
    await update.effective_message.reply_text(render_status(state), reply_markup=main_keyboard(state))


async def wax_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config: Config = context.application.bot_data["config"]
    if await _reject_if_unauthorized(update, config):
        return
    service = _service(context)
    state = service.state_store.load()
    texts = get_texts(state.language)

    if context.args:
        try:
            wax_km = float(context.args[0].replace(",", "."))
        except ValueError:
            await update.effective_message.reply_text(texts.wax_number_hint, reply_markup=main_keyboard(state))
            return
        state = service.set_wax(wax_km)
        texts = get_texts(state.language)
        await update.effective_message.reply_text(
            f"{texts.wax_mileage_saved}: {format_km_for_bot(state.last_wax_km)} {texts.km}\n"
            f"{texts.next_wax}: {format_km_for_bot(state.last_wax_km + state.interval_km)} {texts.km}",
            reply_markup=main_keyboard(state),
        )
        return

    await save_current_wax(update, service)


async def interval_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config: Config = context.application.bot_data["config"]
    if await _reject_if_unauthorized(update, config):
        return
    if not context.args:
        state = _service(context).state_store.load()
        await update.effective_message.reply_text(
            get_texts(state.language).interval_hint,
            reply_markup=main_keyboard(state),
        )
        return
    try:
        interval_km = float(context.args[0].replace(",", "."))
    except ValueError:
        state = _service(context).state_store.load()
        await update.effective_message.reply_text(
            get_texts(state.language).interval_number_error,
            reply_markup=main_keyboard(state),
        )
        return

    service = _service(context)
    try:
        state = service.set_interval(interval_km)
    except ValueError:
        state = service.state_store.load()
        await update.effective_message.reply_text(
            get_texts(state.language).interval_range_error,
            reply_markup=main_keyboard(state),
        )
        return

    texts = get_texts(state.language)
    next_wax = None if state.last_wax_km is None else state.last_wax_km + state.interval_km
    text = f"{texts.interval_saved}: {format_km_for_bot(state.interval_km)} {texts.km}"
    if next_wax is not None:
        text += f"\n{texts.next_wax}: {format_km_for_bot(next_wax)} {texts.km}"
    await update.effective_message.reply_text(text, reply_markup=main_keyboard(state))


async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config: Config = context.application.bot_data["config"]
    if await _reject_if_unauthorized(update, config):
        return
    service = _service(context)
    state = service.state_store.load()
    try:
        state = await service.update_mileage()
    except StravaUnavailable:
        await update.effective_message.reply_text(
            get_texts(state.language).strava_unavailable_check,
            reply_markup=main_keyboard(state),
        )
        return
    await update.effective_message.reply_text(render_status(state), reply_markup=main_keyboard(state))


async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config: Config = context.application.bot_data["config"]
    if await _reject_if_unauthorized(update, config):
        return
    state = _service(context).state_store.load()
    await update.effective_message.reply_text(
        get_texts(state.language).choose_language,
        reply_markup=language_keyboard(),
    )


async def text_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config: Config = context.application.bot_data["config"]
    if await _reject_if_unauthorized(update, config):
        return
    message = update.effective_message
    if message is None or message.text is None:
        return

    service = _service(context)
    text = message.text.strip()
    language = language_from_label(text)
    if language is not None:
        state = service.set_language(language)
        await message.reply_text(get_texts(state.language).language_saved, reply_markup=main_keyboard(state))
        return

    state = service.state_store.load()
    texts = get_texts(state.language)
    action = _button_labels().get(text)
    if action == "status":
        await message.reply_text(render_status(state), reply_markup=main_keyboard(state))
    elif action == "check":
        await check_command(update, context)
    elif action == "wax":
        await save_current_wax(update, service)
    elif action == "language":
        await message.reply_text(texts.choose_language, reply_markup=language_keyboard())
    elif action == "help":
        await message.reply_text(texts.help, reply_markup=main_keyboard(state))


async def save_current_wax(update: Update, service: ChainWaxService) -> None:
    state = service.state_store.load()
    texts = get_texts(state.language)
    try:
        state = await service.update_mileage()
    except StravaUnavailable:
        await update.effective_message.reply_text(texts.strava_unavailable_wax, reply_markup=main_keyboard(state))
        return
    current = state.logical_total_km
    if current is None:
        await update.effective_message.reply_text(texts.current_mileage_missing, reply_markup=main_keyboard(state))
        return
    state = service.set_wax(current)
    texts = get_texts(state.language)
    await update.effective_message.reply_text(
        f"{texts.wax_saved}\n\n"
        f"{texts.mileage}: {format_km_for_bot(state.last_wax_km)} {texts.km}\n"
        f"{texts.next_wax}: {format_km_for_bot(state.last_wax_km + state.interval_km)} {texts.km}",
        reply_markup=main_keyboard(state),
    )


def _service(context: ContextTypes.DEFAULT_TYPE) -> ChainWaxService:
    return context.application.bot_data["service"]


def language_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[LANGUAGE_LABELS["en"], LANGUAGE_LABELS["ro"], LANGUAGE_LABELS["ru"]]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def main_keyboard(state: State) -> ReplyKeyboardMarkup:
    texts = get_texts(state.language)
    return ReplyKeyboardMarkup(
        [
            [texts.status_button, texts.check_button],
            [texts.wax_button, texts.language_button],
            [texts.help_button],
        ],
        resize_keyboard=True,
    )


def _button_labels() -> dict[str, str]:
    labels: dict[str, str] = {}
    for language in SUPPORTED_LANGUAGES:
        texts = get_texts(language)
        labels[texts.status_button] = "status"
        labels[texts.check_button] = "check"
        labels[texts.wax_button] = "wax"
        labels[texts.language_button] = "language"
        labels[texts.help_button] = "help"
    return labels


def format_km_for_bot(value: float) -> str:
    rounded = round(value, 1)
    if rounded.is_integer():
        return f"{int(rounded):,}".replace(",", " ")
    return f"{rounded:,.1f}".replace(",", " ")
