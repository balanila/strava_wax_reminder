from __future__ import annotations

import logging
from dataclasses import dataclass

from app.state import State

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MileageReading:
    km: float
    source: str


def apply_mileage_reading(state: State, reading: MileageReading) -> float:
    """Update logical odometer from a Strava reading and return the new logical total."""
    current = reading.km
    previous = state.last_strava_km

    if previous is None or state.logical_total_km is None:
        state.last_strava_km = current
        state.logical_total_km = current
        return current

    if current >= previous:
        state.logical_total_km += current - previous
        state.last_strava_km = current
        return state.logical_total_km

    if reading.source == "ytd":
        state.logical_total_km += current
        state.last_strava_km = current
        logger.info("Detected yearly mileage rollover: previous=%.1f km current=%.1f km", previous, current)
        return state.logical_total_km

    logger.warning(
        "Strava all-time mileage decreased unexpectedly: previous=%.1f km current=%.1f km",
        previous,
        current,
    )
    return state.logical_total_km


def distance_since_wax(logical_total_km: float | None, last_wax_km: float | None) -> float | None:
    if logical_total_km is None or last_wax_km is None:
        return None
    return logical_total_km - last_wax_km


def should_alert(logical_total_km: float | None, last_wax_km: float | None, interval_km: float) -> bool:
    distance = distance_since_wax(logical_total_km, last_wax_km)
    return distance is not None and distance >= interval_km

