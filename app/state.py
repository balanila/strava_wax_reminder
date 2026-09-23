from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class State:
    last_strava_km: float | None = None
    logical_total_km: float | None = None
    last_wax_km: float | None = None
    interval_km: float = 500.0
    last_alert_date: str | None = None
    last_check_date: str | None = None
    strava_refresh_token: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any], default_interval_km: float) -> "State":
        return cls(
            last_strava_km=_optional_float(data.get("last_strava_km")),
            logical_total_km=_optional_float(data.get("logical_total_km")),
            last_wax_km=_optional_float(data.get("last_wax_km")),
            interval_km=float(data.get("interval_km", default_interval_km)),
            last_alert_date=data.get("last_alert_date"),
            last_check_date=data.get("last_check_date"),
            strava_refresh_token=data.get("strava_refresh_token"),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


class StateStore:
    def __init__(self, path: Path, default_interval_km: float) -> None:
        self.path = path
        self.default_interval_km = default_interval_km

    def load(self) -> State:
        if not self.path.exists():
            state = State(interval_km=self.default_interval_km)
            self.save(state)
            return state

        with self.path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return State.from_dict(data, self.default_interval_km)

    def save(self, state: State) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_name(f".{self.path.name}.tmp")
        with temp_path.open("w", encoding="utf-8") as file:
            json.dump(state.to_dict(), file, ensure_ascii=False, indent=2, sort_keys=True)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp_path, self.path)

