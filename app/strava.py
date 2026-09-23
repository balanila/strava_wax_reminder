from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
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
                    return _parse_mileage(response.json())
            except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
                last_error = exc
                logger.warning("Strava request failed on attempt %s: %s", attempt + 1, exc)
                if attempt < 2:
                    await asyncio.sleep(2**attempt)

        raise StravaUnavailable("Strava is temporarily unavailable") from last_error

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
    all_ride_distance = payload.get("all_ride_totals", {}).get("distance")
    if all_ride_distance is not None:
        return MileageReading(km=float(all_ride_distance) / 1000, source="all_time")

    ytd_ride_distance = payload["ytd_ride_totals"]["distance"]
    return MileageReading(km=float(ytd_ride_distance) / 1000, source="ytd")

