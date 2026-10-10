import math

import numpy as np

from jt_routing import cutoff as cut
from jt_routing.forecast import Curve, StepForecast
from jt_shared.timeutil import parse_ts

import toy

T = parse_ts("2023-07-11T09:00:00+05:30")


def fc(hi_points, observed=205.0):
    h = tuple(p[0] for p in hi_points)
    v = tuple(p[1] for p in hi_points)
    flat = Curve(h, tuple(observed for _ in h))
    return StepForecast(T, observed, flat, flat, Curve(h, v), None, "test")


def two_edge_graph(bridge=False):
    # node 1 (0,0) — node 2 (200 m east) — node 3 (400 m east); edge 2-3 optionally a bridge
    return toy.graph({1: (0, 0), 2: (200, 0), 3: (400, 0)},
                     [(1, 2), (2, 3, {"is_bridge": bridge, "name": "Old Iron Bridge" if bridge else None})])


def raster_for(g, value_fn):
    # 40 x 40 raster around the toy graph
    arr = np.zeros((60, 60))
    r = toy.raster(arr, west=77.199, north=28.601, px=0.0001)
    lon = r.west + (np.arange(60) + 0.5) * r.px_x
    lat = r.north - (np.arange(60) + 0.5) * r.px_y
    LON, LAT = np.meshgrid(lon, lat)
    r.arr = value_fn(LON, LAT)
    return r


def test_edge_cutoff_is_minimum_over_samples():
    g = two_edge_graph()
    # cutoff rises eastwards; one low cell in the middle of edge 1-2
    mid_lon = (g.lon[0] + g.lon[1]) / 2
    r = raster_for(g, lambda lon, lat: 206.0 + (lon - 77.2) * 100 - 0.8 * (np.abs(lon - mid_lon) < 0.0001))
    lv = cut.edge_cutoff_levels(g, r)
    assert lv[0] < 205.5  # picks up the low cell
    assert lv[1] > lv[0]


def test_red_amber_green_rules():
    g = two_edge_graph()
    levels = np.array([206.0, 207.0])
    depth = np.array([0.31, 0.10])
    st = cut.step_status(g, levels, depth, fc([(0, 205.0), (1, 206.5), (3, 206.9)]))
    assert st.status[0] == cut.RED and st.reason[0] == "depth>0.3m" and st.close_h[0] == 0
    assert st.status[1] == cut.GREEN  # window max of hi over (t, t+2h] = 206.7 < 207.0
    assert np.isinf(st.close_h[1])  # hi never reaches 207.0 within the 6 h search
    st2 = cut.step_status(g, levels, np.array([0.30, 0.0]), fc([(0, 205.0), (1, 206.5), (2, 207.1)]))
    assert st2.status[0] == cut.AMBER  # 0.30 is not > 0.30; hi reaches 206.0 within 2 h
    assert st2.status[1] == cut.AMBER and st2.reason[1] == "forecast_cutoff<2h"
    assert math.isfinite(st2.cutoff_h[1])


def test_nan_cutoff_never_closes_and_missing_raster_is_red_only():
    g = two_edge_graph()
    st = cut.step_status(g, np.array([np.nan, np.nan]), np.zeros(2), fc([(0, 205), (24, 210)]))
    assert (st.status == cut.GREEN).all() and np.isinf(st.close_h).all()
    assert np.isnan(cut.edge_cutoff_levels(g, None)).all()


def test_bridge_samples_only_its_approaches():
    g = two_edge_graph(bridge=True)
    bridge = g.edge_index[[e.edge_id for e in g.edges if e.is_bridge][0]]
    # the river (very low cutoff) lies strictly between node 2 and node 3
    lon2, lon3 = g.lon[1], g.lon[2]
    r = raster_for(g, lambda lon, lat: np.where((lon > lon2 + 0.0003) & (lon < lon3 - 0.0003), 199.0, 207.0))
    lv = cut.edge_cutoff_levels(g, r)
    assert lv[bridge] == 207.0  # not 199: the span over the river is not sampled
    samples = (g.sample_edge == bridge).sum()
    assert samples == 2


def test_red_since_carried_forward():
    g = two_edge_graph()
    red_since = {}
    levels = np.array([206.0, 207.0])
    f = fc([(0, 205), (1, 205)])
    st1 = cut.step_status(g, levels, np.array([0.5, 0]), f)
    cut.update_red_since(st1, red_since)
    later = StepForecast(parse_ts("2023-07-11T10:00:00+05:30"), 205, f.level, f.lo, f.hi, None, "t")
    st2 = cut.step_status(g, levels, np.array([0.6, 0]), later)
    cut.update_red_since(st2, red_since)
    rows = cut.road_status_rows(g, st2, red_since)
    assert rows[0]["cutoff_at"] == "2023-07-11T09:00:00+05:30"
    st3 = cut.step_status(g, levels, np.array([0.2, 0]), later)
    cut.update_red_since(st3, red_since)
    assert red_since == {}
