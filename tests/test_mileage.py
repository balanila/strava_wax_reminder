from app.mileage import MileageReading, apply_mileage_reading, should_alert
from app.state import State


def test_normal_mileage_increase() -> None:
    state = State(last_strava_km=1000, logical_total_km=1000)
    apply_mileage_reading(state, MileageReading(km=1050, source="all_time"))

    assert state.last_strava_km == 1050
    assert state.logical_total_km == 1050


def test_year_rollover_for_ytd_counter() -> None:
    state = State(last_strava_km=8123, logical_total_km=8123)
    apply_mileage_reading(state, MileageReading(km=15, source="ytd"))

    assert state.last_strava_km == 15
    assert state.logical_total_km == 8138


def test_all_time_decrease_does_not_reduce_logical_total() -> None:
    state = State(last_strava_km=8123, logical_total_km=8123)
    apply_mileage_reading(state, MileageReading(km=15, source="all_time"))

    assert state.last_strava_km == 8123
    assert state.logical_total_km == 8123


def test_last_wax_calculation_alerts_at_interval() -> None:
    assert should_alert(logical_total_km=13000, last_wax_km=12500, interval_km=500)
    assert not should_alert(logical_total_km=12999, last_wax_km=12500, interval_km=500)

