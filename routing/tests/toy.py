"""Tiny synthetic graphs and rasters for unit tests."""

import networkx as nx
import numpy as np

from jt_routing.cutoff import Raster
from jt_routing.graph import from_networkx

LAT0 = 28.6
M_PER_DEG_LAT = 111_195.0


def graph(nodes: dict[int, tuple[float, float]], edges: list[tuple], directed_both=True):
    """nodes: id → (x_m, y_m) metres from origin. edges: (u, v, attrs) or (u, v)."""
    g = nx.MultiDiGraph()
    lon_m = M_PER_DEG_LAT * np.cos(np.radians(LAT0))
    for n, (x, y) in nodes.items():
        g.add_node(n, x=77.2 + x / lon_m, y=LAT0 + y / M_PER_DEG_LAT)
    for e in edges:
        u, v = e[0], e[1]
        attrs = dict(e[2]) if len(e) > 2 else {}
        lo, hi = min(u, v), max(u, v)
        key = g.number_of_edges(lo, hi)
        attrs.setdefault("edge_id", f"osm:{lo}:{hi}:{key}")
        attrs.setdefault("highway", "residential")
        g.add_edge(lo, hi, key=key, **attrs)
        if directed_both:
            g.add_edge(hi, lo, key=key, **attrs)
    return from_networkx(g)


def raster(arr, west=77.19, north=28.62, px=0.0005, nodata=-9999.0):
    return Raster(arr=np.asarray(arr, float), west=west, north=north, px_x=px, px_y=px, nodata=nodata)
