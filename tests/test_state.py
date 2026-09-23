import json

from app.state import State, StateStore


def test_state_created_when_missing(tmp_path) -> None:
    store = StateStore(tmp_path / "state.json", default_interval_km=500)

    state = store.load()

    assert state.interval_km == 500
    assert (tmp_path / "state.json").exists()


def test_state_round_trip(tmp_path) -> None:
    store = StateStore(tmp_path / "state.json", default_interval_km=500)
    store.save(State(last_strava_km=1, logical_total_km=2, last_wax_km=3, interval_km=450, language="ro"))

    data = json.loads((tmp_path / "state.json").read_text())
    state = store.load()

    assert data["last_wax_km"] == 3
    assert state.interval_km == 450
    assert state.language == "ro"
