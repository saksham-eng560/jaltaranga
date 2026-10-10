"""F5: the flood-blind route, the named avoid list and the "death-trap" counterfactual.

For each planned colony we compute the shortest walk to its assigned shelter **ignoring** flood
information (what people would do without Jaltaranga).

* ``avoid[]``: named roads on that path that the safe router would reject (the walker would not
  clear them 30 min before they close). Each entry carries the earliest closure and every
  non-green edge of that name within 1 km of the path, so the UI can highlight the whole road.
* Trap: the walker *enters* an edge that is already impassable (> 0.30 m) when they reach it.
  This stricter test is what the trap counter reports, so the headline number is conservative.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

import numpy as np

from jt_shared.timeutil import iso

from . import config
from .cutoff import GREEN, StepStatus
from .graph import WalkGraph, haversine_m
from .tdsp import EdgeTimes, search


@dataclass
class NaiveResult:
    path: list[tuple[int, int]]
    avoid: list[dict] = field(default_factory=list)
    trapped: bool = False
    trap_roads: list[str] = field(default_factory=list)
    trap_edge_ids: list[str] = field(default_factory=list)


def naive_path(g: WalkGraph, origin: int, target: int, times: EdgeTimes) -> list[tuple[int, int]] | None:
    res = search(g, origin, times, speed_kmh=3.0, mode="length", targets={target}, ignore_closures=True,
                 max_walk_s=float("inf"))
    return res.path(target) if res.reached(target) else None


def analyse(g: WalkGraph, path: list[tuple[int, int]], st: StepStatus, times: EdgeTimes, speed_kmh: float,
            red_since: dict[int, datetime]) -> NaiveResult:
    speed_ms = speed_kmh / 3.6
    buffer_s = config.SAFETY_BUFFER_MIN * 60
    t = 0.0
    unsafe_by_name: dict[str, list[int]] = {}
    trap_names, trap_ids, trapped = [], [], False
    for _, ei in path:
        e = g.edges[ei]
        entry, t = t, t + e.length_m / speed_ms
        close = float(times.close_s[ei])
        if t + buffer_s > close and e.name:
            unsafe_by_name.setdefault(e.name, []).append(ei)
        if close <= entry:
            trapped = True
            trap_ids.append(e.edge_id)
            if e.name and e.name not in trap_names:
                trap_names.append(e.name)

    path_nodes = [n for n, _ in path] + ([g.other(g.edges[path[-1][1]], path[-1][0])] if path else [])
    plon, plat = g.lon[path_nodes], g.lat[path_nodes]
    avoid = []
    for name, eis in unsafe_by_name.items():
        closes = []
        for ei in eis:
            if st.close_h[ei] == 0:
                closes.append(red_since.get(ei, st.t))
            else:
                closes.append(st.t + timedelta(seconds=round(float(st.close_h[ei]) * 3600)))
        ids = {g.edges[ei].edge_id for ei in eis}
        for e in g.edges:
            if e.name != name or st.status[e.idx] == GREEN or e.edge_id in ids:
                continue
            mlon, mlat = np.mean([c[0] for c in e.coords]), np.mean([c[1] for c in e.coords])
            if float(np.min(haversine_m(plon, plat, mlon, mlat))) <= config.AVOID_NAME_RADIUS_M:
                ids.add(e.edge_id)
        first = g.edges[eis[0]]
        avoid.append({"name_en": name, "name_hi": first.name_hi or name, "cutoff_at": iso(min(closes)),
                      "edge_ids": sorted(ids)})
    avoid.sort(key=lambda a: a["cutoff_at"])
    return NaiveResult(path=path, avoid=avoid, trapped=trapped, trap_roads=trap_names, trap_edge_ids=trap_ids)
