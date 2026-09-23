from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Awaitable, Callable
from zoneinfo import ZoneInfo

from app.i18n import get_texts, normalize_language
from app.mileage import apply_mileage_reading, distance_since_wax, should_alert
from app.state import State, StateStore
from app.strava import StravaClient, StravaUnavailable

logger = logging.getLogger(__name__)


def format_km(value: float | None) -> str:
    if value is None:
        return "не задана"
    rounded = round(value, 1)
    if rounded.is_integer():
        return f"{int(rounded):,}".replace(",", " ")
    return f"{rounded:,.1f}".replace(",", " ")


def render_status(state: State) -> str:
    texts = get_texts(state.language)
    current = state.logical_total_km
    last_wax = state.last_wax_km
    next_wax = None if last_wax is None else last_wax + state.interval_km
    distance = distance_since_wax(current, last_wax)

    lines = [
        f"{texts.current_mileage}: {format_km(current)} {texts.km}" if current is not None else texts.current_not_set,
        f"{texts.last_wax}: {format_km(last_wax)}" + (f" {texts.km}" if last_wax is not None else ""),
    ]

    if last_wax is None:
        lines.append("")
        lines.append(texts.wax_hint)
        return "\n".join(lines)

    lines.extend(
        [
            f"{texts.distance_since_wax}: {format_km(distance)} {texts.km}",
            f"{texts.interval}: {format_km(state.interval_km)} {texts.km}",
        ]
    )
    if distance is not None and distance >= state.interval_km:
        lines.append(f"{texts.overrun}: {format_km(distance - state.interval_km)} {texts.km}")
    lines.append(f"{texts.next_wax}: {format_km(next_wax)} {texts.km}")
    if distance is not None and distance < state.interval_km:
        lines.append(f"{texts.remaining}: {format_km(state.interval_km - distance)} {texts.km}")
    return "\n".join(lines)


def render_alert(state: State) -> str:
    texts = get_texts(state.language)
    distance = distance_since_wax(state.logical_total_km, state.last_wax_km)
    over = None if distance is None else distance - state.interval_km
    return "\n".join(
        [
            texts.alert_title,
            "",
            f"{texts.current_mileage}: {format_km(state.logical_total_km)} {texts.km}",
            f"{texts.last_wax}: {format_km(state.last_wax_km)} {texts.km}",
            f"{texts.distance_since_wax}: {format_km(distance)} {texts.km}",
            f"{texts.interval}: {format_km(state.interval_km)} {texts.km}",
            f"{texts.overrun}: {format_km(over)} {texts.km}",
        ]
    )


@dataclass
class ChainWaxService:
    state_store: StateStore
    strava_client: StravaClient
    timezone: ZoneInfo
    check_time: str

    async def update_mileage(self) -> State:
        reading = await self.strava_client.get_mileage()
        state = self.state_store.load()
        logical_total = apply_mileage_reading(state, reading)
        state.last_check_date = datetime.now(self.timezone).date().isoformat()
        self.state_store.save(state)
        logger.info("Strava mileage updated: %.1f km", logical_total)
        distance = distance_since_wax(state.logical_total_km, state.last_wax_km)
        if distance is not None:
            logger.info("Distance since wax: %.1f km", distance)
        return state

    async def check_and_alert(self, send_alert: Callable[[str], Awaitable[None]]) -> State:
        state = await self.update_mileage()
        today = datetime.now(self.timezone).date().isoformat()
        if should_alert(state.logical_total_km, state.last_wax_km, state.interval_km):
            if state.last_alert_date != today:
                await send_alert(render_alert(state))
                state.last_alert_date = today
                self.state_store.save(state)
                logger.info("Wax reminder sent")
        return state

    def set_wax(self, wax_km: float) -> State:
        state = self.state_store.load()
        state.last_wax_km = wax_km
        state.last_alert_date = None
        self.state_store.save(state)
        return state

    def set_interval(self, interval_km: float) -> State:
        if interval_km < 50 or interval_km > 5000:
            raise ValueError("Interval must be between 50 and 5000 km")
        state = self.state_store.load()
        state.interval_km = interval_km
        self.state_store.save(state)
        return state

    def set_language(self, language: str) -> State:
        state = self.state_store.load()
        state.language = normalize_language(language)
        self.state_store.save(state)
        return state

    async def run_daily_scheduler(self, send_alert: Callable[[str], Awaitable[None]]) -> None:
        while True:
            await asyncio.sleep(_seconds_until_next_run(self.check_time, self.timezone))
            try:
                await self.check_and_alert(send_alert)
            except StravaUnavailable as exc:
                logger.error("Scheduled Strava check failed: %s", exc)
            except Exception:
                logger.exception("Scheduled check failed")


def _seconds_until_next_run(check_time: str, timezone: ZoneInfo) -> float:
    hour, minute = [int(part) for part in check_time.split(":", 1)]
    now = datetime.now(timezone)
    target = datetime.combine(now.date(), time(hour, minute), tzinfo=timezone)
    if target <= now:
        target = target + timedelta(days=1)
    return max((target - now).total_seconds(), 1.0)
