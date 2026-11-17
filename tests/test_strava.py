from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import httpx
import pytest

from app.strava import StravaClient, _parse_mileage

TZ = ZoneInfo("Europe/Chisinau")


def test_year_mileage_and_fallback():
    reading = _parse_mileage({"all_ride_totals": {"distance": 100000},
                              "ytd_ride_totals": {"distance": 2000}})
    assert (reading.km, reading.year_km) == (100, 2)
    reading = _parse_mileage({"ytd_ride_totals": {"distance": 2000}})
    assert (reading.km, reading.year_km, reading.source) == (2, 2, "ytd")


@pytest.mark.asyncio
async def test_period_boundaries_pagination_and_cycling_filter():
    # Jan 1 is Friday: this week includes rides in the previous year.
    now = datetime(2027, 1, 3, 12, tzinfo=TZ)
    def ride(start, distance=1000, kind="Ride"):
        return {"id": 2**63 - 1, "type": kind, "start_date": start, "distance": distance}
    pages = [
        [ride("2026-12-31T23:00:00Z")] * 200,  # Jan 1 locally
        [ride("2026-12-28T10:00:00Z", 2000),
         ride("2026-12-27T21:59:59Z", 4000),  # before local Monday
         ride("2027-01-02T10:00:00Z", 9000, "Run"),
         ride("2027-01-02T10:00:00Z", 3000, "VirtualRide"),
         ride("2027-01-04T10:00:00Z", 8000)],
    ]
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(200, json=pages[int(request.url.params["page"]) - 1])
    client = StravaClient(SimpleNamespace(), None)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        assert await client._get_recent_mileage(http, "token", now) == (203, 205)
    assert len(requests) == 2
    assert int(requests[0].url.params["after"]) == int(datetime(2026, 12, 28, tzinfo=TZ).timestamp()) - 1


@pytest.mark.asyncio
async def test_missing_activity_permission_preserves_total_and_year(tmp_path, monkeypatch):
    from app.state import StateStore
    import app.strava as module
    store = StateStore(tmp_path / "state.json", 500)
    def handler(request):
        if request.url.path == "/oauth/token":
            return httpx.Response(200, json={"access_token": "access", "refresh_token": "rotated"})
        if request.url.path.endswith("/stats"):
            return httpx.Response(200, json={"all_ride_totals": {"distance": 100000},
                                             "ytd_ride_totals": {"distance": 2000}})
        return httpx.Response(403)
    original = httpx.AsyncClient
    monkeypatch.setattr(module.httpx, "AsyncClient", lambda **kwargs: original(
        transport=httpx.MockTransport(handler), **kwargs))
    config = SimpleNamespace(strava_athlete_id=2**63-1, timezone=TZ,
                             strava_refresh_token="old", strava_client_id="id", strava_client_secret="secret")
    reading = await StravaClient(config, store).get_mileage()
    assert (reading.km, reading.year_km, reading.month_km, reading.week_km) == (100, 2, None, None)
    assert reading.periods_date is not None
    assert store.load().strava_refresh_token == "rotated"


@pytest.mark.asyncio
async def test_no_rides_is_zero():
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=[]))) as http:
        assert await StravaClient(None, None)._get_recent_mileage(
            http, "token", datetime(2026, 11, 17, tzinfo=TZ)) == (0, 0)
