"""Synthetic *dev world* for offline development and CI.

It writes, under ``$JT_LOCAL_DATA``, stand-ins for every upstream artefact routing and alerts
consume (SHARED §6/§11.2): the walk graph and roads envelope (Shivansh), colony/shelter seeds
(Shivansh), the manifest and observed gauge curve (Shivansh), ``onset.tif`` /
``cutoff_0p30.tif`` / ``colony_thresholds.json`` / per-step depth rasters / forecasts (Vaibhav).

Everything here is **synthetic** and labelled so (``source="synthetic"``, ``model="synthetic-dev"``,
``manifest.artefacts = "fixture"``). Geography is the real Wazirabad→Okhla corridor and the
observed curve is seeded from the press-reported July 2023 Delhi Railway Bridge anchors, but the
flood surface is an analytic function of distance to the river, not a DEM. The real artefacts
replace these files one by one; nothing in routing/alerts knows the difference.

Usage: ``python -m jt_routing.devworld [--scenario yamuna-2023-07]``
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timedelta
from pathlib import Path

import networkx as nx
import numpy as np

from jt_shared import constants as C
from jt_shared import io
from jt_shared.naming import s3_key
from jt_shared.timeutil import IST, iso, parse_ts

NAMES_HI = json.loads((Path(__file__).resolve().parents[1] / "data" / "names_hi.json").read_text("utf-8"))

# --- geography ----------------------------------------------------------------------------------
# Raster extent (inside the §2 bbox) and resolution (~44 m; the real DTM is ~30 m).
WEST, EAST, SOUTH, NORTH = 77.200, 77.330, 28.570, 28.730
PX = 0.0004
KM_PER_DEG_LON = 111.32 * math.cos(math.radians(28.65))
KM_PER_DEG_LAT = 110.95

RIVER = [  # approximate Yamuna centreline, Wazirabad → Okhla
    (77.231, 28.735), (77.236, 28.712), (77.240, 28.690), (77.244, 28.675), (77.249, 28.661),
    (77.256, 28.645), (77.262, 28.628), (77.266, 28.610), (77.272, 28.590), (77.285, 28.570),
]
RIVER_HALF_WIDTH_KM = 0.18

ROADS = {  # name → (highway, foot_ok, polyline)
    "Ring Road": ("trunk", True, [(77.2255, 28.722), (77.229, 28.700), (77.2315, 28.684), (77.2335, 28.670),
                                  (77.2385, 28.659), (77.2435, 28.647), (77.2485, 28.632), (77.2535, 28.612),
                                  (77.2595, 28.592), (77.270, 28.575)]),
    "Pushta Road": ("primary", True, [(77.2535, 28.722), (77.2575, 28.700), (77.263, 28.682), (77.2695, 28.664),
                                      (77.2745, 28.646), (77.2785, 28.628), (77.2835, 28.608), (77.293, 28.588)]),
    "Netaji Subhash Marg": ("secondary", True, [(77.2405, 28.6575), (77.2395, 28.645), (77.2400, 28.632)]),
    "Lothian Road": ("secondary", True, [(77.2265, 28.6640), (77.2320, 28.6600), (77.2380, 28.6560)]),
    "Shamnath Marg": ("secondary", True, [(77.2215, 28.6930), (77.2240, 28.6800), (77.2260, 28.6680)]),
    "Vikas Marg": ("primary", True, [(77.2610, 28.6300), (77.2780, 28.6320), (77.3000, 28.6340), (77.3200, 28.6360)]),
    "GT Road": ("primary", True, [(77.2700, 28.6680), (77.2850, 28.6720), (77.3050, 28.6760), (77.3250, 28.6800)]),
    "Wazirabad Road": ("primary", True, [(77.2560, 28.7100), (77.2750, 28.7050), (77.2950, 28.7000), (77.3200, 28.6950)]),
    "Mathura Road": ("primary", True, [(77.2420, 28.6300), (77.2470, 28.6100), (77.2560, 28.5900), (77.2650, 28.5750)]),
    "NH-24": ("motorway", False, [(77.2850, 28.6200), (77.3000, 28.6170), (77.3250, 28.6130)]),
}

# Named streets that follow the lane grid (grid edges within 120 m of the polyline take the name).
LANE_NAMES = {
    "Bela Road": ("tertiary", [(77.2445, 28.6560), (77.2395, 28.6530), (77.2350, 28.6495), (77.2310, 28.6460)]),
}

BRIDGES = {"Wazirabad Bridge": 28.711, "Old Iron Bridge": 28.661, "Geeta Colony Bridge": 28.651,
           "ITO Bridge": 28.630, "Nizamuddin Bridge": 28.592}

# Synthetic colonies (real place names, synthetic populations; SHARED §5.5 says demo data is synthetic).
COLONIES = [
    ("DEL-YP-04", "Yamuna Pushta Sector C", "यमुना पुश्ता सेक्टर सी", (77.2425, 28.6550), 4200, (310, 45, 520, 60)),
    ("DEL-YBZ-10", "Yamuna Bazaar", "यमुना बाज़ार", (77.2365, 28.6635), 2600, (240, 30, 300, 40)),
    ("DEL-MON-03", "Monastery Market Camp", "मॉनेस्ट्री मार्केट कैंप", (77.2350, 28.6740), 1800, (90, 12, 210, 25)),
    ("DEL-MKT-01", "Majnu ka Tilla", "मजनू का टीला", (77.2305, 28.7010), 3100, (260, 38, 340, 45)),
    ("DEL-GRH-08", "Garhi Mandu", "गढ़ी मांडू", (77.2485, 28.7015), 2200, (210, 40, 310, 35)),
    ("DEL-USM-07", "Old Usmanpur", "पुराना उस्मानपुर", (77.2560, 28.6880), 3800, (300, 50, 450, 55)),
    ("DEL-SPK-06", "Shastri Park", "शास्त्री पार्क", (77.2610, 28.6735), 4600, (350, 60, 520, 70)),
    ("DEL-GTC-05", "Geeta Colony Khadar", "गीता कॉलोनी खादर", (77.2665, 28.6545), 2900, (230, 35, 380, 40)),
    ("DEL-CKD-09", "Chilla Khadar", "चिल्ला खादर", (77.2830, 28.6075), 1500, (160, 30, 230, 30)),
    ("DEL-BLA-02", "Bela Estate", "बेला एस्टेट", (77.2470, 28.6475), 1200, (60, 10, 140, 15)),
]

SHELTERS = [
    ("SH-KG-01", "Kashmiri Gate Community Hall", "कश्मीरी गेट सामुदायिक भवन", (77.2255, 28.6665), 1200, 300, "community_hall"),
    ("SH-CL-02", "Civil Lines Govt School", "सिविल लाइंस सरकारी स्कूल", (77.2205, 28.6815), 2000, 400, "school"),
    ("SH-DG-03", "Daryaganj Relief Camp", "दरियागंज राहत शिविर", (77.2325, 28.6430), 1500, 300, "relief_camp"),
    ("SH-SH-04", "Shahdara Community Hall", "शाहदरा सामुदायिक भवन", (77.2925, 28.6735), 1800, 500, "community_hall"),
    ("SH-LN-05", "Laxmi Nagar School", "लक्ष्मी नगर स्कूल", (77.2830, 28.6315), 1200, 400, "school"),
    ("SH-BH-06", "Bhajanpura Relief Camp", "भजनपुरा राहत शिविर", (77.2710, 28.7000), 1500, 300, "relief_camp"),
    ("SH-TM-07", "Timarpur School", "तिमारपुर स्कूल", (77.2215, 28.7065), 1200, 300, "school"),
    ("SH-PV-08", "Preet Vihar Medical Camp", "प्रीत विहार चिकित्सा शिविर", (77.3020, 28.6420), 400, 100, "medical"),
]

# Observed DRB curve (m above MSL). Anchors on 12–14 Jul follow SHARED §1 / the press reports
# quoted in the plans; the rest is a smooth synthetic rise and recession. Peak hour is unverified.
ANCHORS = [
    ("2023-07-09T00:00", 203.20), ("2023-07-09T12:00", 203.55), ("2023-07-10T00:00", 204.25),
    ("2023-07-10T12:00", 205.05), ("2023-07-10T20:00", 205.45), ("2023-07-11T04:00", 205.85),
    ("2023-07-11T12:00", 206.30), ("2023-07-11T20:00", 206.70), ("2023-07-12T04:00", 207.00),
    ("2023-07-12T08:00", 207.25), ("2023-07-12T11:00", 207.38), ("2023-07-12T20:00", 207.71),
    ("2023-07-13T00:00", 207.95), ("2023-07-13T08:00", 208.48), ("2023-07-13T10:00", 208.53),
    ("2023-07-13T18:00", 208.66), ("2023-07-14T00:00", 208.62), ("2023-07-14T11:00", 208.35),
    ("2023-07-14T20:00", 207.95), ("2023-07-15T08:00", 207.40), ("2023-07-15T20:00", 206.80),
    ("2023-07-16T08:00", 206.20), ("2023-07-16T23:00", 205.60),
]
START, END = "2023-07-09T00:00:00+05:30", "2023-07-16T23:00:00+05:30"
HALF_WIDTH = {1: 0.10, 3: 0.18, 6: 0.28, 12: 0.45, 24: 0.70}
NODATA = -9999.0


# --- helpers ------------------------------------------------------------------------------------
def _to_km(lon: np.ndarray, lat: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return (np.asarray(lon) - WEST) * KM_PER_DEG_LON, (np.asarray(lat) - SOUTH) * KM_PER_DEG_LAT


def dist_to_polyline_km(lon, lat, line) -> np.ndarray:
    x, y = _to_km(lon, lat)
    best = np.full(np.shape(x), np.inf)
    for (a_lon, a_lat), (b_lon, b_lat) in zip(line, line[1:]):
        ax, ay = _to_km(a_lon, a_lat)
        bx, by = _to_km(b_lon, b_lat)
        dx, dy = bx - ax, by - ay
        t = np.clip(((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy), 0, 1)
        best = np.minimum(best, np.hypot(x - (ax + t * dx), y - (ay + t * dy)))
    return best


def _bump(lon, lat, c_lon, c_lat, radius_km, amp):
    x, y = _to_km(lon, lat)
    cx, cy = _to_km(c_lon, c_lat)
    return amp * np.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (2 * radius_km ** 2))


def onset_level(lon, lat) -> np.ndarray:
    """DRB gauge level (m) at which a point first gets wet. Analytic stand-in for Vaibhav's onset.tif."""
    lon, lat = np.asarray(lon, float), np.asarray(lat, float)
    d = dist_to_polyline_km(lon, lat, RIVER)
    z = 205.10 + 1.30 * np.clip(d - RIVER_HALF_WIDTH_KM, 0, None) + 0.10 * np.clip(d - 2.5, 0, None) ** 2
    z = z + 0.12 * np.sin(lon * 900.0) * np.cos(lat * 700.0)  # micro-relief
    z = z - _bump(lon, lat, 77.2350, 28.6700, 0.35, 0.80)  # low stretch of Ring Road near ISBT
    z = z - _bump(lon, lat, 77.2440, 28.6480, 0.30, 0.55)  # Ring Road dip south of Yamuna Pushta
    z = z - _bump(lon, lat, 77.2385, 28.6525, 0.12, 1.20)  # low lane SW of Yamuna Pushta (trap for direct route)
    z = z + _bump(lon, lat, 77.2420, 28.6550, 0.20, 0.80)  # Yamuna Pushta sits on a low mound
    z = z + _bump(lon, lat, 77.2220, 28.6800, 1.00, 2.50)  # Civil Lines ridge
    z = z + _bump(lon, lat, 77.2950, 28.6700, 1.20, 1.20)  # Shahdara high ground
    z = z + _bump(lon, lat, 77.2850, 28.6350, 0.80, 0.90)  # Laxmi Nagar
    river = d < RIVER_HALF_WIDTH_KM
    return np.where(river, 199.0, z)


def observed_level(t: datetime) -> float:
    ts = [parse_ts(a + ":00+05:30") for a, _ in ANCHORS]
    vs = [v for _, v in ANCHORS]
    x = (t - ts[0]).total_seconds()
    xs = [(u - ts[0]).total_seconds() for u in ts]
    return float(np.interp(x, xs, vs))


def _grid() -> tuple[np.ndarray, np.ndarray]:
    cols = int(round((EAST - WEST) / PX))
    rows = int(round((NORTH - SOUTH) / PX))
    lon = WEST + (np.arange(cols) + 0.5) * PX
    lat = NORTH - (np.arange(rows) + 0.5) * PX
    return np.meshgrid(lon, lat)


def _write_tif(key: str, arr: np.ndarray, nodata: float | None) -> None:
    import rasterio
    from rasterio.transform import from_origin

    path = io.local_path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        path, "w", driver="GTiff", height=arr.shape[0], width=arr.shape[1], count=1, dtype="float32",
        crs="EPSG:4326", transform=from_origin(WEST, NORTH, PX, PX), nodata=nodata, compress="deflate",
        tiled=True, blockxsize=256, blockysize=256,
    ) as dst:
        dst.write(arr.astype("float32"), 1)


def _steps() -> list[datetime]:
    t, end, out = parse_ts(START), parse_ts(END), []
    while t <= end:
        out.append(t)
        t += timedelta(hours=1)
    return out


def _rng(tag: str) -> np.random.Generator:
    return np.random.default_rng(int(hashlib.sha256(tag.encode()).hexdigest()[:8], 16))


# --- graph --------------------------------------------------------------------------------------
def build_graph() -> nx.MultiDiGraph:
    """Walk graph: a jittered ~250 m lane grid plus named roads and bridges.

    Edge attributes follow SHARED §11.3: ``edge_id`` = ``osm:<min(u,v)>:<max(u,v)>:<key>`` shared by
    both directions, ``name``, ``name:hi``, ``highway``, ``foot_ok``, ``is_bridge``, ``elev_min_m``.
    """
    g = nx.MultiDiGraph(crs="EPSG:4326", name="jt-devworld")
    next_id = [9_100_000_000]

    def add_node(lon: float, lat: float) -> int:
        nid = next_id[0]
        next_id[0] += 1
        g.add_node(nid, x=round(lon, 6), y=round(lat, 6), elev_m=round(float(onset_level(lon, lat)), 2))
        return nid

    def length_m(u: int, v: int) -> float:
        a, b = g.nodes[u], g.nodes[v]
        return float(math.hypot((a["x"] - b["x"]) * KM_PER_DEG_LON, (a["y"] - b["y"]) * KM_PER_DEG_LAT) * 1000)

    def add_edge(u: int, v: int, name: str | None, highway: str, foot_ok: bool, is_bridge: bool = False):
        if u == v:
            return
        lo, hi = min(u, v), max(u, v)
        key = g.number_of_edges(lo, hi)
        a, b = g.nodes[u], g.nodes[v]
        attrs = {
            "edge_id": f"osm:{lo}:{hi}:{key}", "highway": highway, "foot_ok": foot_ok, "is_bridge": is_bridge,
            "length": round(length_m(u, v), 1),
            "elev_min_m": round(min(a["elev_m"], b["elev_m"]), 2),
            "geometry": f"LINESTRING ({a['x']} {a['y']}, {b['x']} {b['y']})",
        }
        if name:
            attrs["name"] = name
            attrs["name:hi"] = NAMES_HI.get(name, name)
        g.add_edge(lo, hi, key=key, **attrs)
        g.add_edge(hi, lo, key=key, **attrs)

    # 1. lane grid
    step = 0.0025
    lons = np.arange(77.2050, 77.3251, step)
    lats = np.arange(28.5750, 28.7251, step)
    jitter = _rng("grid")
    ids: dict[tuple[int, int], int] = {}
    for i, la in enumerate(lats):
        for j, lo in enumerate(lons):
            lo2 = lo + jitter.uniform(-0.0004, 0.0004)
            la2 = la + jitter.uniform(-0.0004, 0.0004)
            if dist_to_polyline_km(lo2, la2, RIVER) < RIVER_HALF_WIDTH_KM + 0.04:
                continue
            ids[(i, j)] = add_node(float(lo2), float(la2))
    for (i, j), u in ids.items():
        for di, dj in ((0, 1), (1, 0)):
            v = ids.get((i + di, j + dj))
            if v is None:
                continue
            mid_lon = (g.nodes[u]["x"] + g.nodes[v]["x"]) / 2
            mid_lat = (g.nodes[u]["y"] + g.nodes[v]["y"]) / 2
            if dist_to_polyline_km(mid_lon, mid_lat, RIVER) < RIVER_HALF_WIDTH_KM + 0.02:
                continue
            add_edge(u, v, None, "residential", True)

    for lname, (lhw, line) in LANE_NAMES.items():
        for u, v, k, d in g.edges(keys=True, data=True):
            if d.get("name") or not (u < v):
                continue
            du = dist_to_polyline_km(g.nodes[u]["x"], g.nodes[u]["y"], line)
            dv = dist_to_polyline_km(g.nodes[v]["x"], g.nodes[v]["y"], line)
            if du <= 0.12 and dv <= 0.12:
                for a, b in ((u, v), (v, u)):
                    g.edges[a, b, k].update({"name": lname, "name:hi": NAMES_HI.get(lname, lname), "highway": lhw})

    grid_nodes = list(ids.values())
    gx = np.array([g.nodes[n]["x"] for n in grid_nodes])
    gy = np.array([g.nodes[n]["y"] for n in grid_nodes])

    def nearest_grid(lon: float, lat: float) -> int:
        d = np.hypot((gx - lon) * KM_PER_DEG_LON, (gy - lat) * KM_PER_DEG_LAT)
        return grid_nodes[int(np.argmin(d))]

    # 2. named roads as their own chains, tied into the grid every ~250 m
    for name, (highway, foot_ok, line) in ROADS.items():
        prev = None
        for (a_lon, a_lat), (b_lon, b_lat) in zip(line, line[1:]):
            seg_km = math.hypot((b_lon - a_lon) * KM_PER_DEG_LON, (b_lat - a_lat) * KM_PER_DEG_LAT)
            n = max(1, int(round(seg_km / 0.25)))
            for k in range(n + (1 if (b_lon, b_lat) == line[-1] else 0)):
                f = k / n
                lon, lat = a_lon + f * (b_lon - a_lon), a_lat + f * (b_lat - a_lat)
                node = add_node(lon, lat)
                if prev is not None:
                    add_edge(prev, node, name, highway, foot_ok)
                if foot_ok:
                    add_edge(node, nearest_grid(lon, lat), None, "service", True)
                prev = node

    # 3. bridges: span the river between the nearest dry grid nodes on each bank
    for name, lat in BRIDGES.items():
        river_lon = float(np.interp(lat, [p[1] for p in RIVER[::-1]], [p[0] for p in RIVER[::-1]]))
        west = [n for n in grid_nodes if g.nodes[n]["x"] < river_lon and abs(g.nodes[n]["y"] - lat) < 0.0016]
        east = [n for n in grid_nodes if g.nodes[n]["x"] > river_lon and abs(g.nodes[n]["y"] - lat) < 0.0016]
        if not west or not east:
            continue
        w = max(west, key=lambda n: g.nodes[n]["x"])
        e = min(east, key=lambda n: g.nodes[n]["x"])
        add_edge(w, e, name, "primary", True, is_bridge=True)
    return g


def roads_envelope(g: nx.MultiDiGraph) -> dict:
    seen, feats = set(), []
    for u, v, d in g.edges(data=True):
        if d["edge_id"] in seen:
            continue
        seen.add(d["edge_id"])
        a, b = g.nodes[u], g.nodes[v]
        feats.append({
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": [[a["x"], a["y"]], [b["x"], b["y"]]]},
            "properties": {"edge_id": d["edge_id"], "name": d.get("name"), "name:hi": d.get("name:hi"),
                           "highway": d["highway"]},
        })
    return {"type": "FeatureCollection", "features": feats}


# --- writer -------------------------------------------------------------------------------------
def build(scenario_id: str = C.PRIMARY_SCENARIO) -> dict:
    if io.local_root() is None:
        raise SystemExit("set JT_LOCAL_DATA (e.g. JT_LOCAL_DATA=./data)")
    lon, lat = _grid()
    onset = onset_level(lon, lat).astype("float32")
    cutoff = np.maximum(onset, onset + C.DEPTH_CUTOFF_M).astype("float32")  # = max(onset, z' + 0.30), z' = onset
    _write_tif(s3_key("onset"), onset, NODATA)
    _write_tif(s3_key("cutoff_raster"), cutoff, NODATA)

    g = build_graph()
    path = io.local_path(s3_key("graphml"))
    path.parent.mkdir(parents=True, exist_ok=True)
    nx.write_graphml(g, path)
    io.write_json(s3_key("roads_geojson"), roads_envelope(g))

    # seeds
    colonies = []
    for cid, en, hi, (clon, clat), pop, (el, di, ch, pr) in COLONIES:
        colonies.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [clon, clat]},
                         "properties": {"colony_id": cid, "name_en": en, "name_hi": hi, "centroid": [clon, clat],
                                        "population_est": pop, "ground_elev_m": None,
                                        "vulnerable": {"elderly": el, "disabled": di, "children_u5": ch,
                                                       "pregnant": pr},
                                        "synthetic": True}})
    shelters = []
    for sid, en, hi, (slon, slat), cap, occ, typ in SHELTERS:
        shelters.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [slon, slat]},
                         "properties": {"shelter_id": sid, "name_en": en, "name_hi": hi, "location": [slon, slat],
                                        "ground_elev_m": None, "capacity": cap, "occupied": occ,
                                        "free_beds": cap - occ, "type": typ,
                                        "updated_at": "2023-07-09T00:00:00+05:30", "synthetic": True}})
    io.write_json(s3_key("colonies"), {"type": "FeatureCollection", "features": colonies})
    io.write_json(s3_key("shelters"), {"type": "FeatureCollection", "features": shelters})

    # colony thresholds: 10th percentile of onset / cutoff within 150 m (Vaibhav F6 rule)
    thresholds = []
    for cid, *_rest in COLONIES:
        clon, clat = _rest[2]
        d = np.hypot((lon - clon) * KM_PER_DEG_LON, (lat - clat) * KM_PER_DEG_LAT)
        m = d <= 0.150
        thresholds.append({"colony_id": cid, "wet_at_level_m": round(float(np.percentile(onset[m], 10)), 2),
                           "cutoff_at_level_m": round(float(np.percentile(cutoff[m], 10)), 2), "buffer_m": 150})
    io.write_json(s3_key("colony_thresholds"), thresholds)

    # observed curve, depth rasters, forecasts
    steps = _steps()
    gauges = []
    for t in steps:
        level = round(observed_level(t), 2)
        gauges.append({"station_id": C.REF_STATION, "ts": iso(t), "level_m": level, "discharge_cumecs": None,
                       "source": "synthetic", "qc_flag": "ok", "note": "jt devworld curve seeded from press anchors"})
        depth = np.clip(level - onset, 0, None).astype("float32")
        _write_tif(s3_key("depth_tif", scenario_id=scenario_id, valid_at=t), depth, None)
        nodes = []
        rng = _rng(iso(t))
        for h in C.HORIZONS_H:
            v = t + timedelta(hours=h)
            centre = observed_level(v) + float(rng.normal(0, 0.03 * math.sqrt(h)))
            w = HALF_WIDTH[h]
            nodes.append({"scenario_id": scenario_id, "issued_at": iso(t), "station_id": C.REF_STATION,
                          "horizon_h": h, "valid_at": iso(v), "level_m": round(centre, 2),
                          "lo_m": round(centre - w, 2), "hi_m": round(centre + w, 2), "coverage": 0.8,
                          "model": "synthetic-dev"})
        io.write_json(s3_key("forecasts", scenario_id=scenario_id, issued_at=t), nodes)
    io.write_json(s3_key("gauges", scenario_id=scenario_id), gauges)

    peak = max(gauges, key=lambda r: r["level_m"])
    manifest = {
        "scenario_id": scenario_id, "mode": "replay", "title_en": "Yamuna flood, July 2023 (dev world)",
        "title_hi": "यमुना बाढ़, जुलाई 2023 (डेव वर्ल्ड)", "start": START, "end": END, "step_min": 60,
        "valid_at": [iso(t) for t in steps], "issued_at": [iso(t) for t in steps],
        "default_at": "2023-07-13T00:00:00+05:30", "ref_station": C.REF_STATION, "thresholds": C.THRESHOLDS,
        "events": [{"kind": "peak", "ts": peak["ts"], "level_m": peak["level_m"], "ts_verified": False}],
        "artefacts": {k: "fixture" for k in ("gauges", "forecasts", "depth", "roads", "plans", "infra")},
        "sources": [{"id": "jt-devworld", "kind": "synthetic",
                     "note": "routing/jt_routing/devworld.py; replaced by pipeline/ and ml/ outputs"}],
        "built_at": iso(datetime.now(IST)), "data_version": "devworld-1",
    }
    io.write_json(s3_key("manifest", scenario_id=scenario_id), manifest)
    return {"nodes": g.number_of_nodes(), "edges": g.number_of_edges() // 2, "steps": len(steps),
            "thresholds": thresholds}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--scenario", default=C.PRIMARY_SCENARIO)
    args = ap.parse_args()
    out = build(args.scenario)
    print(json.dumps({k: v for k, v in out.items() if k != "thresholds"}))
    for t in out["thresholds"]:
        print(f"  {t['colony_id']:<11} wet_at={t['wet_at_level_m']:.2f}  cutoff_at={t['cutoff_at_level_m']:.2f}")


if __name__ == "__main__":
    main()
