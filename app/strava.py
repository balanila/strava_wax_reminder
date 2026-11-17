from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Any

import httpx

from app.config import Config
from app.mileage import MileageReading
from app.state import StateStore

logger = logging.getLogger(__name__)


class StravaUnavailable(RuntimeError):
    pass


@dataclass
class StravaClient:
    config: Config
    state_store: StateStore
    timeout: float = 15.0

    async def get_mileage(self) -> MileageReading:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    token = await self._refresh_access_token(client)
                    response = await client.get(
                        f"https://www.strava.com/api/v3/athletes/{self.config.strava_athlete_id}/stats",
                        headers={"Authorization": f"Bearer {token}"},
                    )
                    response.raise_for_status()
                    reading = _parse_mileage(response.json())
                    now = datetime.now(self.config.timezone)
                    try:
                        month_km, week_km = await self._get_recent_mileage(client, token, now)
                    except (httpx.HTTPError, KeyError, TypeError, ValueError):
                        logger.warning("Monthly and weekly Strava mileage unavailable", exc_info=True)
                        month_km = week_km = None
                    return replace(reading, month_km=month_km, week_km=week_km,
                                   periods_date=now.date().isoformat())
            except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
                last_error = exc
                logger.warning("Strava request failed on attempt %s: %s", attempt + 1, exc)
                if attempt < 2:
                    await asyncio.sleep(2**attempt)

        raise StravaUnavailable("Strava is temporarily unavailable") from last_error

    async def _get_recent_mileage(
        self, client: httpx.AsyncClient, token: str, now: datetime
    ) -> tuple[float, float]:
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        week_start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=now.weekday())
        # A week can begin in the previous month or year.
        after = int(min(month_start, week_start).timestamp()) - 1
        month_m = week_m = 0.0
        page = 1
        while True:
            response = await client.get(
                "https://www.strava.com/api/v3/athlete/activities",
                headers={"Authorization": f"Bearer {token}"},
                params={"after": after, "before": int(now.timestamp()) + 1,
                        "page": page, "per_page": 200},
            )
            response.raise_for_status()
            activities = response.json()
            if not isinstance(activities, list):
                raise ValueError("Expected an activity list")
            for activity in activities:
                if activity.get("type", activity.get("sport_type")) not in {
                    "Ride", "VirtualRide", "EBikeRide", "EMountainBikeRide",
                    "MountainBikeRide", "GravelRide", "Handcycle", "Velomobile",
                }:
                    continue
                started = datetime.fromisoformat(activity["start_date"].replace("Z", "+00:00"))
                if started.tzinfo is None:
                    raise ValueError("Activity start_date must include a timezone")
                started = started.astimezone(now.tzinfo)
                if started > now:
                    continue
                distance = float(activity["distance"])
                if started >= month_start:
                    month_m += distance
                if started >= week_start:
                    week_m += distance
            if len(activities) < 200:
                return month_m / 1000, week_m / 1000
            page += 1

    async def _refresh_access_token(self, client: httpx.AsyncClient) -> str:
        state = self.state_store.load()
        refresh_token = state.strava_refresh_token or self.config.strava_refresh_token
        response = await client.post(
            "https://www.strava.com/oauth/token",
            data={
                "client_id": self.config.strava_client_id,
                "client_secret": self.config.strava_client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
        response.raise_for_status()
        payload = response.json()
        new_refresh_token = payload.get("refresh_token")
        if new_refresh_token and new_refresh_token != state.strava_refresh_token:
            state.strava_refresh_token = new_refresh_token
            self.state_store.save(state)
        access_token = payload["access_token"]
        return str(access_token)


def _parse_mileage(payload: dict[str, Any]) -> MileageReading:
    year_distance = payload.get("ytd_ride_totals", {}).get("distance")
    year_km = None if year_distance is None else float(year_distance) / 1000
    all_ride_distance = payload.get("all_ride_totals", {}).get("distance")
    if all_ride_distance is not None:
        return MileageReading(km=float(all_ride_distance) / 1000, source="all_time", year_km=year_km)

    ytd_ride_distance = payload["ytd_ride_totals"]["distance"]
    return MileageReading(km=float(ytd_ride_distance) / 1000, source="ytd", year_km=year_km)

