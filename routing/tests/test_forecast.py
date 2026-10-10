from datetime import timedelta

import pytest

from jt_routing.forecast import Curve, build_curves
from jt_shared.timeutil import iso, parse_ts

T = parse_ts("2023-07-11T09:00:00+05:30")


def nodes(levels, his=None, los=None):
    out = []
    for i, h in enumerate((1, 3, 6, 12, 24)):
        lv = levels[i]
        out.append({"scenario_id": "s", "issued_at": iso(T), "station_id": "DELHI_RLY_BRIDGE", "horizon_h": h,
                    "valid_at": iso(T + timedelta(hours=h)), "level_m": lv,
                    "lo_m": (los or levels)[i] - (0 if los else 0.2), "hi_m": (his or levels)[i] + (0 if his else 0.2),
                    "coverage": 0.8, "model": "test"})
    return out


def test_curve_starts_at_observation_and_crosses_exactly():
    fc = build_curves(T, 206.0, nodes([206.1, 206.3, 206.6, 207.0, 207.5]))
    assert fc.level.at(0) == 206.0
    h = fc.level.first_crossing(206.2)
    assert h == pytest.approx(2.0)  # linear between h=1 (206.1) and h=3 (206.3)
    assert fc.level.first_crossing(206.0) == 0.0
    assert fc.level.first_crossing(210.0) is None
    assert fc.level.first_crossing(206.2, h_max=1.5) is None


def test_window_max_catches_peak_inside_window_on_falling_limb():
    # §11.8-4: point sample at t+2h misses a crossing inside (t, t+2h]
    c = Curve((0.0, 1.0, 3.0), (206.0, 206.5, 205.5))
    assert c.at(2.0) == pytest.approx(206.0)
    assert c.window_max(0.0, 2.0) == pytest.approx(206.5)


def test_persistence_when_no_forecast():
    fc = build_curves(T, 205.0, [])
    assert fc.hi.at(24) == 205.0 and fc.model == "persistence"
