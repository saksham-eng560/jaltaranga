"""Per-edge cutoff levels and RoadSegmentStatus per replay step (plan §4.1, SHARED §5.4/§11.8-4/-5).

This is the **one** per-edge cutoff implementation (§11.8-5): ``cutoff_level_m`` = minimum of
Vaibhav's ``cutoff_0p30.tif`` over the edge's 15 m samples; written to
``static/osm/edge_cutoffs.json`` for the what-if endpoint. No datum arithmetic happens here (§11.1).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

import numpy as np

from jt_shared import constants as C
from jt_shared.timeutil import iso

from . import config
from .forecast import StepForecast
from .graph import WalkGraph


@dataclass
class Raster:
    arr: np.ndarray
    west: float
    north: float
    px_x: float
    px_y: float
    nodata: float | None

    @classmethod
    def open(cls, path) -> Raster:
        import rasterio

        with rasterio.open(path) as src:
            arr = src.read(1).astype("float64")
            t = src.transform
            return cls(arr=arr, west=t.c, north=t.f, px_x=t.a, px_y=-t.e, nodata=src.nodata)

    def sample(self, lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
        """Nearest-cell values; NaN for nodata or outside the raster."""
        col = np.floor((np.asarray(lon) - self.west) / self.px_x).astype(np.int64)
        row = np.floor((self.north - np.asarray(lat)) / self.px_y).astype(np.int64)
        h, w = self.arr.shape
        ok = (row >= 0) & (row < h) & (col >= 0) & (col < w)
        out = np.full(row.shape, np.nan)
        out[ok] = self.arr[row[ok], col[ok]]
        if self.nodata is not None and not math.isnan(self.nodata):
            out[out == self.nodata] = np.nan
        return out


def _reduce(values: np.ndarray, sample_edge: np.ndarray, n_edges: int, how: str) -> np.ndarray:
    fill = np.inf if how == "min" else -np.inf
    vals = np.where(np.isnan(values), fill, values)
    tmp = np.full(n_edges, fill)
    (np.minimum if how == "min" else np.maximum).at(tmp, sample_edge, vals)
    return np.where(np.isinf(tmp), np.nan, tmp)


def edge_cutoff_levels(g: WalkGraph, cutoff_raster: Raster | None) -> np.ndarray:
    """Per-edge DRB level at which depth > 0.30 m. NaN = never (or no raster: red-only mode)."""
    if cutoff_raster is None:
        return np.full(g.n_edges, np.nan)
    vals = cutoff_raster.sample(g.sample_lon, g.sample_lat)
    return _reduce(vals, g.sample_edge, g.n_edges, "min")


def edge_depths(g: WalkGraph, depth_raster: Raster | None) -> np.ndarray:
    """Per-edge maximum depth now (m). Missing raster → 0 (status then comes from the forecast only)."""
    if depth_raster is None:
        return np.zeros(g.n_edges)
    vals = depth_raster.sample(g.sample_lon, g.sample_lat)
    out = _reduce(vals, g.sample_edge, g.n_edges, "max")
    return np.nan_to_num(out, nan=0.0)


def edge_cutoffs_json(g: WalkGraph, levels: np.ndarray) -> dict[str, float | None]:
    return {e.edge_id: (None if math.isnan(levels[e.idx]) else round(float(levels[e.idx]), 3)) for e in g.edges}


@dataclass
class StepStatus:
    t: datetime
    status: np.ndarray  # 0 green, 1 amber, 2 red
    depth: np.ndarray
    close_h: np.ndarray  # hours after t until the edge is impassable (0 = now, inf = not within 6 h)
    cutoff_h: np.ndarray  # amber: hours until hi_m crosses the cutoff level (NaN otherwise)
    reason: list[str | None]


GREEN, AMBER, RED = 0, 1, 2


def step_status(g: WalkGraph, levels: np.ndarray, depth: np.ndarray, fc: StepForecast,
                forced_red: set[int] | None = None) -> StepStatus:
    """Red if depth > 0.30 m now; amber if max(hi_m over (t, t+2h]) reaches the cutoff level."""
    n = g.n_edges
    status = np.zeros(n, dtype=np.int8)
    close_h = np.full(n, np.inf)
    cutoff_h = np.full(n, np.nan)
    reason: list[str | None] = [None] * n

    red = depth > C.DEPTH_CUTOFF_M
    window_hi = fc.hi.window_max(0.0, float(C.AMBER_WINDOW_H))
    for i in range(n):
        if red[i]:
            status[i], close_h[i], reason[i] = RED, 0.0, "depth>0.3m"
            continue
        if forced_red and i in forced_red:
            status[i], close_h[i], reason[i] = RED, 0.0, "field_report"
            continue
        lvl = levels[i]
        if math.isnan(lvl):
            continue
        hc = fc.hi.first_crossing(lvl, h_max=config.CLOSE_SEARCH_H)
        if hc is not None:
            close_h[i] = hc
        if window_hi >= lvl:
            status[i], reason[i] = AMBER, "forecast_cutoff<2h"
            cutoff_h[i] = hc if hc is not None else 0.0
    return StepStatus(fc.t, status, depth, close_h, cutoff_h, reason)


def road_status_rows(g: WalkGraph, st: StepStatus, red_since: dict[int, datetime]) -> list[dict]:
    """Non-green RoadSegmentStatus rows. Red ``cutoff_at`` = first step of the current red run."""
    rows = []
    for i in np.nonzero(st.status)[0]:
        e = g.edges[int(i)]
        if st.status[i] == RED:
            cut = red_since.get(int(i), st.t)
        else:
            cut = st.t + _td(st.cutoff_h[i])
        rows.append({"edge_id": e.edge_id, "status": "red" if st.status[i] == RED else "amber",
                     "depth_m": round(float(st.depth[i]), 2), "cutoff_at": iso(cut), "reason": st.reason[int(i)]})
    return rows


def update_red_since(st: StepStatus, red_since: dict[int, datetime]) -> None:
    now_red = set(int(i) for i in np.nonzero(st.status == RED)[0])
    for i in list(red_since):
        if i not in now_red:
            del red_since[i]
    for i in now_red:
        red_since.setdefault(i, st.t)


def _td(hours: float):
    from datetime import timedelta

    return timedelta(seconds=round(float(hours) * 3600))
