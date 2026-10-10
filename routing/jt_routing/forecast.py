"""ForecastNode → piecewise-linear level/lo/hi curves and an exact crossing-time solver.

Times are hours after the step time ``t``. The h = 0 point is the observed level at ``t``
(SHARED §11.8-3: the curve starts at the observation), then the forecast horizons 1/3/6/12/24 h.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np

from jt_shared import constants as C
from jt_shared import io
from jt_shared.naming import s3_key
from jt_shared.timeutil import hours_between, iso, parse_ts


@dataclass(frozen=True)
class Curve:
    h: tuple[float, ...]  # strictly increasing, h[0] == 0
    v: tuple[float, ...]

    def at(self, h: float) -> float:
        return float(np.interp(h, self.h, self.v))

    def first_crossing(self, level: float | None, h_max: float = math.inf, h_min: float = 0.0) -> float | None:
        """First h in [h_min, min(h_max, end)] where the curve reaches ``level`` (>=). Exact on segments."""
        if level is None or (isinstance(level, float) and math.isnan(level)):
            return None
        if self.at(h_min) >= level:
            return h_min
        for (h0, _v0), (h1, v1) in zip(zip(self.h, self.v), zip(self.h[1:], self.v[1:])):
            if h1 <= h_min:
                continue
            a = max(h0, h_min)
            va = self.at(a)
            if v1 >= level > va:
                hc = a + (level - va) / (v1 - va) * (h1 - a)
                return hc if hc <= h_max else None
            if h1 >= h_max:
                break
        return None

    def window_max(self, h0: float, h1: float) -> float:
        """max over (h0, h1] (§11.8-4: amber uses the window maximum, not a point sample)."""
        pts = [self.at(h1)] + [v for h, v in zip(self.h, self.v) if h0 < h <= h1]
        return max(pts)


@dataclass(frozen=True)
class StepForecast:
    t: datetime
    observed: float
    level: Curve
    lo: Curve
    hi: Curve
    issued_at: datetime | None
    model: str

    def abs_time(self, h: float | None) -> datetime | None:
        return None if h is None else self.t + timedelta(hours=h)


def build_curves(t: datetime, observed: float, nodes: list[dict], station: str = C.REF_STATION) -> StepForecast:
    pts: dict[float, tuple[float, float, float]] = {}
    issued, model = None, "persistence"
    for n in nodes:
        if n.get("station_id", station) != station:
            continue
        h = hours_between(t, parse_ts(n["valid_at"]))
        if h <= 0:
            continue
        pts[h] = (float(n["level_m"]), float(n["lo_m"]), float(n["hi_m"]))
        issued, model = parse_ts(n["issued_at"]), n.get("model", model)
    hs = [0.0] + sorted(pts)
    lv = [observed] + [pts[h][0] for h in hs[1:]]
    lo = [observed] + [pts[h][1] for h in hs[1:]]
    hi = [observed] + [pts[h][2] for h in hs[1:]]
    if len(hs) == 1:  # no forecast at all → persistence (degrade path)
        hs, lv, lo, hi = [0.0, 24.0], [observed] * 2, [observed] * 2, [observed] * 2
    return StepForecast(t, observed, Curve(tuple(hs), tuple(lv)), Curve(tuple(hs), tuple(lo)),
                        Curve(tuple(hs), tuple(hi)), issued, model)


class ObservedSeries:
    """Observed reference-gauge level from ``scenarios/<id>/gauges.json`` (linear interpolation)."""

    def __init__(self, readings: list[dict], station: str = C.REF_STATION):
        rows = sorted((parse_ts(r["ts"]), float(r["level_m"])) for r in readings
                      if r.get("station_id") == station and r.get("level_m") is not None)
        if not rows:
            raise ValueError(f"no observed levels for {station}")
        self.t0 = rows[0][0]
        self.x = np.array([hours_between(self.t0, t) for t, _ in rows])
        self.y = np.array([v for _, v in rows])

    def at(self, t: datetime) -> float:
        return float(np.interp(hours_between(self.t0, t), self.x, self.y))


def load_step_forecast(scenario_id: str, t: datetime, observed: ObservedSeries,
                       issued_at: list[datetime] | None = None) -> StepForecast:
    """Forecast issued at, or just before, ``t`` (SHARED §7 /forecast semantics)."""
    nodes = io.read_json_or(s3_key("forecasts", scenario_id=scenario_id, issued_at=t), None)
    if nodes is None and issued_at:
        earlier = [u for u in issued_at if u <= t]
        for u in sorted(earlier, reverse=True)[:6]:
            nodes = io.read_json_or(s3_key("forecasts", scenario_id=scenario_id, issued_at=iso(u)), None)
            if nodes is not None:
                break
    return build_curves(t, observed.at(t), nodes or [])
