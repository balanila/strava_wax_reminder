from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


@dataclass(frozen=True)
class Config:
    strava_client_id: str
    strava_client_secret: str
    strava_refresh_token: str
    strava_athlete_id: int
    telegram_bot_token: str
    telegram_chat_id: int
    check_time: str
    default_interval_km: float
    timezone: ZoneInfo
    state_path: Path

    @classmethod
    def from_env(cls) -> "Config":
        tz_name = os.getenv("TZ", "Europe/Chisinau")
        return cls(
            strava_client_id=_required("STRAVA_CLIENT_ID"),
            strava_client_secret=_required("STRAVA_CLIENT_SECRET"),
            strava_refresh_token=_required("STRAVA_REFRESH_TOKEN"),
            strava_athlete_id=int(_required("STRAVA_ATHLETE_ID")),
            telegram_bot_token=_required("TELEGRAM_BOT_TOKEN"),
            telegram_chat_id=int(_required("TELEGRAM_CHAT_ID")),
            check_time=os.getenv("CHECK_TIME", "10:00"),
            default_interval_km=float(os.getenv("DEFAULT_INTERVAL_KM", "500")),
            timezone=ZoneInfo(tz_name),
            state_path=Path(os.getenv("STATE_PATH", "/app/data/state.json")),
        )

