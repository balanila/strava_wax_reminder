from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from app.config import Config
from app.service import ChainWaxService, render_status
from app.strava import StravaUnavailable

logger = logging.getLogger(__name__)


HELP_TEXT = """Доступные команды:
/status - текущий статус цепи
/wax - записать текущий пробег Strava как проварку
/wax <пробег> - записать пробег проварки вручную
/interval <км> - изменить интервал обслуживания
/check - проверить Strava сейчас
/help - показать команды"""


def build_application(config: Config, service: ChainWaxService) -> Application:
    app = Application.builder().token(config.telegram_bot_token).build()
    app.bot_data["config"] = config
    app.bot_data["service"] = service
    app.add_handler(CommandHandler("start", help_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("wax", wax_command))
    app.add_handler(CommandHandler("interval", interval_command))
    app.add_handler(CommandHandler("check", check_command))
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


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config: Config = context.application.bot_data["config"]
    if await _reject_if_unauthorized(update, config):
        return
    await update.effective_message.reply_text(HELP_TEXT)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config: Config = context.application.bot_data["config"]
    if await _reject_if_unauthorized(update, config):
        return
    service: ChainWaxService = context.application.bot_data["service"]
    await update.effective_message.reply_text(render_status(service.state_store.load()))


async def wax_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config: Config = context.application.bot_data["config"]
    if await _reject_if_unauthorized(update, config):
        return
    service: ChainWaxService = context.application.bot_data["service"]

    if context.args:
        try:
            wax_km = float(context.args[0].replace(",", "."))
        except ValueError:
            await update.effective_message.reply_text("Укажи пробег числом: /wax 12910")
            return
        state = service.set_wax(wax_km)
        await update.effective_message.reply_text(
            f"✅ Пробег проварки сохранён: {format_km_for_bot(state.last_wax_km)} км\n"
            f"Следующая проварка: {format_km_for_bot(state.last_wax_km + state.interval_km)} км"
        )
        return

    try:
        state = await service.update_mileage()
    except StravaUnavailable:
        await update.effective_message.reply_text("Strava временно недоступна. Проварку не сохранил.")
        return
    current = state.logical_total_km
    if current is None:
        await update.effective_message.reply_text("Текущий пробег ещё не получен.")
        return
    state = service.set_wax(current)
    await update.effective_message.reply_text(
        "✅ Проварка цепи сохранена.\n\n"
        f"Пробег: {format_km_for_bot(state.last_wax_km)} км\n"
        f"Следующая проварка: {format_km_for_bot(state.last_wax_km + state.interval_km)} км"
    )


async def interval_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config: Config = context.application.bot_data["config"]
    if await _reject_if_unauthorized(update, config):
        return
    if not context.args:
        await update.effective_message.reply_text("Укажи интервал: /interval 450")
        return
    try:
        interval_km = float(context.args[0].replace(",", "."))
    except ValueError:
        await update.effective_message.reply_text("Интервал должен быть числом.")
        return

    service: ChainWaxService = context.application.bot_data["service"]
    try:
        state = service.set_interval(interval_km)
    except ValueError:
        await update.effective_message.reply_text("Интервал должен быть в диапазоне 50-5000 км.")
        return

    next_wax = None if state.last_wax_km is None else state.last_wax_km + state.interval_km
    text = f"✅ Интервал обслуживания: {format_km_for_bot(state.interval_km)} км"
    if next_wax is not None:
        text += f"\nСледующая проварка: {format_km_for_bot(next_wax)} км"
    await update.effective_message.reply_text(text)


async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config: Config = context.application.bot_data["config"]
    if await _reject_if_unauthorized(update, config):
        return
    service: ChainWaxService = context.application.bot_data["service"]
    try:
        state = await service.update_mileage()
    except StravaUnavailable:
        await update.effective_message.reply_text("Strava временно недоступна. Попробуй позже.")
        return
    await update.effective_message.reply_text(render_status(state))


def format_km_for_bot(value: float) -> str:
    rounded = round(value, 1)
    if rounded.is_integer():
        return f"{int(rounded):,}".replace(",", " ")
    return f"{rounded:,.1f}".replace(",", " ")

