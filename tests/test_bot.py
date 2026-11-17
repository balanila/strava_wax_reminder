from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.bot import status_command, text_button_handler
from app.mileage import MileageReading
from app.service import ChainWaxService
from app.state import State, StateStore
from app.strava import StravaUnavailable
from zoneinfo import ZoneInfo


@pytest.mark.asyncio
@pytest.mark.parametrize("offline", [False, True])
async def test_status_refreshes_or_shows_saved_values(tmp_path, offline):
    store = StateStore(tmp_path / "state.json", 500)
    store.save(State(logical_total_km=100, language="ru", year_km=10,
                     month_km=5, week_km=2, periods_date="2026-11-16"))
    client = SimpleNamespace(get_mileage=AsyncMock(
        return_value=MileageReading(200, "all_time", 20, 10, 4, "2026-11-17"),
        side_effect=StravaUnavailable() if offline else None))
    service = ChainWaxService(store, client, ZoneInfo("Europe/Chisinau"), "10:00")
    context = SimpleNamespace(application=SimpleNamespace(bot_data={
        "config": SimpleNamespace(telegram_chat_id=1), "service": service}))
    message = SimpleNamespace(reply_text=AsyncMock(), text="📊 Статус")
    update = SimpleNamespace(effective_chat=SimpleNamespace(id=1), effective_message=message)
    await status_command(update, context)
    client.get_mileage.assert_awaited_once()
    text = message.reply_text.call_args.args[0]
    assert ("За этот месяц: 5 км" if offline else "За этот месяц: 10 км") in text
    assert ("2026-11-16" if offline else "2026-11-17") in text
