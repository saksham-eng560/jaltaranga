"""Walk graph loading, 15 m edge sampling and nearest-node snapping (plan §4.1).

``edge_id`` is read verbatim from the graphml (SHARED §11.3); this module never mints one.
One undirected record is kept per ``edge_id``; u→v and v→u share it.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path

import networkx as nx
import numpy as np

from . import config

EARTH_R_M = 6_371_000.0
_LINESTRING = re.compile(r"LINESTRING\s*\((.*)\)", re.I)


def _bool(v, default: bool) -> bool:
    if v is None:
        return default
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("true", "1", "yes")


def _parse_linestring(wkt: str | None) -> list[tuple[float, float]] | None:
    if not wkt:
        return None
    m = _LINESTRING.match(str(wkt).strip())
    if not m:
        return None
    pts = []
    for pair in m.group(1).split(","):
        x, y = pair.split()[:2]
        pts.append((float(x), float(y)))
    return pts if len(pts) >= 2 else None


def haversine_m(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(np.radians, (lon1, lat1, lon2, lat2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_R_M * np.arcsin(np.sqrt(a))


@dataclass
class Edge:
    idx: int
    edge_id: str
    u: int  # node index
    v: int
    length_m: float
    name: str | None
    name_hi: str | None
    highway: str
    foot_ok: bool
    is_bridge: bool
    coords: list[tuple[float, float]]  # from u to v


@dataclass
class WalkGraph:
    node_ids: list[str]
    lon: np.ndarray
    lat: np.ndarray
    edges: list[Edge]
    adj: list[list[tuple[int, int]]] = field(default_factory=list)  # node → [(nbr, edge_idx)] (foot_ok only)
    sample_lon: np.ndarray = field(default_factory=lambda: np.zeros(0))
    sample_lat: np.ndarray = field(default_factory=lambda: np.zeros(0))
    sample_edge: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=np.int64))
    edge_index: dict[str, int] = field(default_factory=dict)

    @property
    def n_edges(self) -> int:
        return len(self.edges)

    def nearest_nodes(self, lon: float, lat: float, radius_m: float | None = None) -> list[tuple[float, int]]:
        """(distance_m, node) sorted by distance, optionally limited to radius_m."""
        d = haversine_m(self.lon, self.lat, lon, lat)
        order = np.argsort(d)
        out = []
        for n in order:
            if radius_m is not None and d[n] > radius_m:
                break
            out.append((float(d[n]), int(n)))
            if radius_m is None and len(out) >= 1:
                break
        return out

    def nearest_node(self, lon: float, lat: float) -> tuple[float, int]:
        return self.nearest_nodes(lon, lat)[0]

    def other(self, e: Edge, node: int) -> int:
        return e.v if node == e.u else e.u

    def coords_from(self, e: Edge, start: int) -> list[tuple[float, float]]:
        return e.coords if start == e.u else list(reversed(e.coords))


def _sample_line(coords: list[tuple[float, float]], spacing_m: float) -> list[tuple[float, float]]:
    pts = [coords[0]]
    for (x0, y0), (x1, y1) in zip(coords, coords[1:]):
        seg = float(haversine_m(x0, y0, x1, y1))
        n = max(1, int(math.ceil(seg / spacing_m)))
        for k in range(1, n + 1):
            f = k / n
            pts.append((x0 + f * (x1 - x0), y0 + f * (y1 - y0)))
    return pts


def from_networkx(g: nx.MultiDiGraph | nx.MultiGraph, spacing_m: float = config.SAMPLE_SPACING_M) -> WalkGraph:
    node_ids = [str(n) for n in g.nodes]
    index = {n: i for i, n in enumerate(g.nodes)}
    lon = np.array([float(g.nodes[n]["x"]) for n in g.nodes])
    lat = np.array([float(g.nodes[n]["y"]) for n in g.nodes])
    edges: list[Edge] = []
    edge_index: dict[str, int] = {}
    for u, v, d in g.edges(data=True):
        eid = d.get("edge_id")
        if eid is None:
            raise ValueError(f"graph edge {u}->{v} has no edge_id (SHARED §11.3)")
        if eid in edge_index:
            continue
        coords = _parse_linestring(d.get("geometry"))
        ui, vi = index[u], index[v]
        if coords is None:
            coords = [(lon[ui], lat[ui]), (lon[vi], lat[vi])]
        elif float(haversine_m(*coords[0], lon[ui], lat[ui])) > float(haversine_m(*coords[-1], lon[ui], lat[ui])):
            coords = list(reversed(coords))
        length = d.get("length")
        length_m = float(length) if length is not None else float(
            sum(haversine_m(*a, *b) for a, b in zip(coords, coords[1:])))
        name = d.get("name") or None
        e = Edge(idx=len(edges), edge_id=str(eid), u=ui, v=vi, length_m=length_m, name=name,
                 name_hi=d.get("name:hi") or name, highway=str(d.get("highway", "")),
                 foot_ok=_bool(d.get("foot_ok"), True), is_bridge=_bool(d.get("is_bridge"), False), coords=coords)
        edge_index[e.edge_id] = e.idx
        edges.append(e)

    adj: list[list[tuple[int, int]]] = [[] for _ in node_ids]
    for e in edges:
        if e.foot_ok and e.u != e.v:
            adj[e.u].append((e.v, e.idx))
            adj[e.v].append((e.u, e.idx))

    s_lon, s_lat, s_edge = [], [], []
    for e in edges:
        # Bridges are not sampled along the span (the raster below is river); they are sampled at
        # their two endpoints only, i.e. they inherit the worse of their two approaches (plan §4.1).
        pts = [e.coords[0], e.coords[-1]] if e.is_bridge else _sample_line(e.coords, spacing_m)
        for x, y in pts:
            s_lon.append(x)
            s_lat.append(y)
            s_edge.append(e.idx)
    return WalkGraph(node_ids=node_ids, lon=lon, lat=lat, edges=edges, adj=adj, sample_lon=np.array(s_lon),
                     sample_lat=np.array(s_lat), sample_edge=np.array(s_edge, dtype=np.int64), edge_index=edge_index)


def load_graphml(path: str | Path) -> WalkGraph:
    return from_networkx(nx.read_graphml(path))
