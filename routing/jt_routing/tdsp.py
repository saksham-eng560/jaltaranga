"""Time-dependent walking search with edge closures (plan §2, §4.2).

Every edge has a closure time ``close_at`` (seconds after departure; 0 = red now, inf = stays open).
An edge is usable only if ``exit_time + 30 min <= close_at``. Walk speed is fixed, there is no
waiting, so the network is FIFO and **earliest-arrival Dijkstra is exact**: it finds a feasible
route whenever one exists. The cost-Dijkstra (depth/amber-weighted) prefers drier routes but, with
the arrival-time side check, is incomplete, so callers fall back to earliest-arrival before
declaring a colony unreachable.
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field

import numpy as np

from . import config
from .graph import WalkGraph


@dataclass
class EdgeTimes:
    close_s: np.ndarray  # per edge, seconds after departure
    depth: np.ndarray  # per edge, m (≤ 0.30 on any usable edge)
    amber: np.ndarray  # bool per edge


@dataclass
class SearchResult:
    origin: int
    arrival_s: dict[int, float]
    cost: dict[int, float]
    pred: dict[int, tuple[int, int]]  # node → (prev node, edge idx)
    mode: str
    settled: set[int] = field(default_factory=set)

    def reached(self, node: int) -> bool:
        return node in self.settled

    def path(self, node: int) -> list[tuple[int, int]]:
        """[(from_node, edge_idx), ...] from origin to node."""
        out = []
        while node != self.origin:
            prev, e = self.pred[node]
            out.append((prev, e))
            node = prev
        out.reverse()
        return out


def edge_cost(walk_s: float, depth: float, amber: bool) -> float:
    return walk_s * (1.0 + config.DEPTH_COST_WEIGHT * depth) * (config.AMBER_COST_FACTOR if amber else 1.0)


def search(g: WalkGraph, origin: int, times: EdgeTimes, speed_kmh: float, mode: str = "cost",
           targets: set[int] | None = None, penalty: dict[int, float] | None = None,
           max_walk_s: float = config.MAX_WALK_MIN * 60, buffer_s: float = config.SAFETY_BUFFER_MIN * 60,
           ignore_closures: bool = False) -> SearchResult:
    """Single-source search. mode="cost" keys on weighted cost, "arrival" on arrival time, and
    "length" on distance (with ignore_closures=True this is the flood-blind baseline, F5)."""
    if mode not in ("cost", "arrival", "length"):
        raise ValueError(mode)
    speed_ms = speed_kmh / 3.6
    remaining = set(targets) if targets else None
    key = {origin: 0.0}
    arrival = {origin: 0.0}
    cost = {origin: 0.0}
    pred: dict[int, tuple[int, int]] = {}
    settled: set[int] = set()
    heap = [(0.0, 0.0, origin)]
    while heap:
        k, arr, node = heapq.heappop(heap)
        if node in settled or k > key.get(node, math.inf):
            continue
        settled.add(node)
        if remaining is not None:
            remaining.discard(node)
            if not remaining:
                break
        for nbr, ei in g.adj[node]:
            if nbr in settled:
                continue
            e = g.edges[ei]
            walk_s = e.length_m / speed_ms
            exit_s = arr + walk_s
            if exit_s > max_walk_s:
                continue
            if not ignore_closures and exit_s + buffer_s > times.close_s[ei]:
                continue
            step_cost = edge_cost(walk_s, float(times.depth[ei]), bool(times.amber[ei]))
            c = cost[node] + step_cost  # true cost; the penalty only steers the search key
            if mode == "cost":
                nk = key[node] + step_cost * (penalty.get(ei, 1.0) if penalty else 1.0)
            elif mode == "arrival":
                nk = exit_s
            else:
                nk = key[node] + e.length_m
            if nk < key.get(nbr, math.inf):
                key[nbr], arrival[nbr], cost[nbr] = nk, exit_s, c
                pred[nbr] = (node, ei)
                heapq.heappush(heap, (nk, exit_s, nbr))
    return SearchResult(origin=origin, arrival_s=arrival, cost=cost, pred=pred, mode=mode, settled=settled)


def route_is_safe(g: WalkGraph, path: list[tuple[int, int]], times: EdgeTimes, speed_kmh: float,
                  buffer_s: float = config.SAFETY_BUFFER_MIN * 60) -> bool:
    """Invariant check: every edge satisfies exit + buffer <= close_at."""
    t = 0.0
    for _, ei in path:
        t += g.edges[ei].length_m / (speed_kmh / 3.6)
        if t + buffer_s > times.close_s[ei]:
            return False
    return True
