"""Candidate routes: top-K shelters per colony, each with a best and an alternative route (plan §4.2-3)."""

from __future__ import annotations

from dataclasses import dataclass, field

from . import config
from .graph import WalkGraph
from .tdsp import EdgeTimes, SearchResult, search


@dataclass
class Route:
    shelter_id: str
    shelter_node: int
    path: list[tuple[int, int]]  # (from_node, edge_idx)
    walk_s: float
    distance_m: float
    max_depth_m: float
    amber_share: float
    mode: str  # search mode that produced it: cost | arrival

    @property
    def edge_idxs(self) -> list[int]:
        return [e for _, e in self.path]

    @property
    def walk_min(self) -> float:
        return round(self.walk_s / 60.0, 1)


@dataclass
class Candidate:
    best: Route
    alt: Route | None = None


@dataclass
class ColonyCandidates:
    origin: int
    speed_kmh: float
    mode: str
    candidates: list[Candidate] = field(default_factory=list)


def _route(g: WalkGraph, res: SearchResult, node: int, shelter_id: str, times: EdgeTimes) -> Route:
    path = res.path(node)
    dist = sum(g.edges[e].length_m for _, e in path)
    amber_len = sum(g.edges[e].length_m for _, e in path if times.amber[e])
    return Route(shelter_id=shelter_id, shelter_node=node, path=path, walk_s=res.arrival_s[node], distance_m=dist,
                 max_depth_m=max((float(times.depth[e]) for _, e in path), default=0.0),
                 amber_share=(amber_len / dist) if dist > 0 else 0.0, mode=res.mode)


def overlap_share(g: WalkGraph, a: Route, b: Route) -> float:
    common = set(a.edge_idxs) & set(b.edge_idxs)
    total = a.distance_m or 1.0
    return sum(g.edges[e].length_m for e in common) / total


def build_candidates(g: WalkGraph, origin: int, shelters: dict[str, int], times: EdgeTimes, speed_kmh: float,
                     k: int = config.K_SHELTERS) -> ColonyCandidates:
    """shelters: usable shelter_id → graph node. Cost search first, earliest-arrival fallback."""
    targets = set(shelters.values())
    res = search(g, origin, times, speed_kmh, mode="cost", targets=targets)
    reached = {sid: n for sid, n in shelters.items() if res.reached(n)}
    if not reached:
        res = search(g, origin, times, speed_kmh, mode="arrival", targets=targets)
        reached = {sid: n for sid, n in shelters.items() if res.reached(n)}
    out = ColonyCandidates(origin=origin, speed_kmh=speed_kmh, mode=res.mode)
    ranked = sorted(reached.items(), key=lambda kv: (res.arrival_s[kv[1]], kv[0]))[:k]
    for sid, node in ranked:
        best = _route(g, res, node, sid, times)
        alt = None
        if best.path and res.mode == "cost":
            penalty = {e: config.ALT_PENALTY for e in best.edge_idxs}
            r2 = search(g, origin, times, speed_kmh, mode="cost", targets={node}, penalty=penalty)
            if r2.reached(node):
                cand = _route(g, r2, node, sid, times)
                if overlap_share(g, cand, best) < config.ALT_MAX_OVERLAP:
                    alt = cand
        out.candidates.append(Candidate(best=best, alt=alt))
    return out
