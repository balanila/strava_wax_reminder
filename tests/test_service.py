from datetime import date
from zoneinfo import ZoneInfo

import pytest

from app.mileage import MileageReading
from app.service import ChainWaxService
from app.state import StateStore


class FakeStravaClient:
    def __init__(self, km: float, source: str = "all_time") -> None:
        self.km = km
        self.source = source

    async def get_mileage(self) -> MileageReading:
        return MileageReading(km=self.km, source=self.source)


@pytest.fixture
def service(tmp_path) -> ChainWaxService:
    store = StateStore(tmp_path / "state.json", default_interval_km=500)
    store.load()
    return ChainWaxService(
        state_store=store,
        strava_client=FakeStravaClient(13000),
        timezone=ZoneInfo("Europe/Chisinau"),
        check_time="10:00",
    )


def test_after_wax_command_sets_last_wax(service: ChainWaxService) -> None:
    state = service.set_wax(12910)

    assert state.last_wax_km == 12910


@pytest.mark.asyncio
async def test_daily_alert_not_sent_twice_same_day(service: ChainWaxService) -> None:
    state = service.state_store.load()
    state.last_strava_km = 13000
    state.logical_total_km = 13000
    state.last_wax_km = 12500
    state.interval_km = 500
    service.state_store.save(state)
    sent: list[str] = []

    async def send_alert(text: str) -> None:
        sent.append(text)

    await service.check_and_alert(send_alert)
    await service.check_and_alert(send_alert)

    assert len(sent) == 1


@pytest.mark.asyncio
async def test_wax_resets_alert_state(service: ChainWaxService) -> None:
    state = service.state_store.load()
    state.last_alert_date = date.today().isoformat()
    service.state_store.save(state)

    state = service.set_wax(12910)

    assert state.last_alert_date is None


@pytest.mark.asyncio
async def test_update_mileage_preserves_refresh_token(service: ChainWaxService) -> None:
    state = service.state_store.load()
    state.strava_refresh_token = "new-refresh-token"
    service.state_store.save(state)

    state = await service.update_mileage()

    assert state.strava_refresh_token == "new-refresh-token"
