"""Assemble one replay step: road status → candidates → assignment → plans, unreachable, trap (plan §4.2).

Outputs are validated with ``jt_shared.models`` before they are returned.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import numpy as np

from jt_shared import constants as C
from jt_shared.models import Colony, EvacuationPlan, RoadSegmentStatus, Shelter, UnreachableEntry
from jt_shared.timeutil import iso

from . import config, priority
from .assign import Demand, assign, check_capacity
from .avoid import analyse, naive_path
from .candidates import ColonyCandidates, Route, build_candidates
from .cutoff import RED, Raster, StepStatus, road_status_rows
from .forecast import StepForecast
from .graph import WalkGraph
from .tdsp import EdgeTimes


@dataclass
class Context:
    scenario_id: str
    g: WalkGraph
    levels: np.ndarray  # per-edge cutoff level
    colonies: list[Colony]
    shelters: list[Shelter]
    wet_at: dict[str, float | None]
    onset: Raster | None
    norm: priority.Normaliser
    solver: str = "greedy"
    shelter_node: dict[str, int] = field(default_factory=dict)
    shelter_onset: dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        for s in self.shelters:
            self.shelter_node[s.shelter_id] = self.g.nearest_node(*s.location)[1]
            lvl = float("nan")
            if self.onset is not None:
                lvl = float(self.onset.sample(np.array([s.location[0]]), np.array([s.location[1]]))[0])
            self.shelter_onset[s.shelter_id] = lvl


@dataclass
class StepResult:
    t: datetime
    roads: list[dict]
    plans: list[dict]
    unreachable: list[dict]
    candidates: list[dict]
    trap: dict
    routes: dict[str, dict[str, list[int]]]  # colony → {"primary": edge idxs, "backup": edge idxs}


def _abs(t: datetime, h: float | None) -> str | None:
    return None if h is None else iso(t + timedelta(minutes=round(h * 60)))


def _round_half(x: float) -> float:
    return math.floor(x * 2 + 0.5) / 2


def _via(g: WalkGraph, r: Route) -> tuple[list[str], list[str]]:
    totals: dict[str, float] = {}
    first: dict[str, int] = {}
    hi: dict[str, str] = {}
    for i, (_, ei) in enumerate(r.path):
        e = g.edges[ei]
        if not e.name:
            continue
        totals[e.name] = totals.get(e.name, 0.0) + e.length_m
        first.setdefault(e.name, i)
        hi.setdefault(e.name, e.name_hi or e.name)
    top = sorted(sorted(totals, key=lambda n: -totals[n])[:2], key=lambda n: first[n])
    return top, [hi[n] for n in top]


def _route_json(g: WalkGraph, r: Route) -> dict:
    coords: list[list[float]] = []
    for start, ei in r.path:
        seg = g.coords_from(g.edges[ei], start)
        pts = [[round(x, 6), round(y, 6)] for x, y in seg]
        coords.extend(pts if not coords else pts[1:])
    if not coords:  # origin is the shelter node
        n = r.shelter_node
        coords = [[round(float(g.lon[n]), 6), round(float(g.lat[n]), 6)]] * 2
    via_en, via_hi = _via(g, r)
    return {
        "shelter_id": r.shelter_id,
        "route_geojson": {"type": "Feature", "geometry": {"type": "LineString", "coordinates": coords},
                          "properties": {"edge_ids": [g.edges[e].edge_id for e in r.edge_idxs]}},
        "distance_m": round(r.distance_m),
        "walk_min": r.walk_min,
        "via_names_en": via_en,
        "via_names_hi": via_hi,
        "max_depth_m": round(r.max_depth_m, 2),
    }


def _cand_json(g: WalkGraph, r: Route | None) -> dict | None:
    if r is None:
        return None
    return {"shelter_id": r.shelter_id, "walk_min": r.walk_min, "distance_m": round(r.distance_m),
            "max_depth_m": round(r.max_depth_m, 2), "mode": r.mode,
            "edge_ids": [g.edges[e].edge_id for e in r.edge_idxs]}


def pick_origin(g: WalkGraph, c: Colony, node_depth: np.ndarray, st: StepStatus) -> tuple[int, float] | None:
    """Nearest *dry* graph node within 300 m (§11.8-2): node depth ≤ 0.05 m and a non-red incident edge."""
    for dist, n in g.nearest_nodes(c.centroid[0], c.centroid[1], radius_m=config.ORIGIN_RADIUS_M):
        if node_depth[n] > C.WET_DEPTH_M:
            continue
        if any(st.status[ei] != RED for _, ei in g.adj[n]):
            return n, dist
    return None


def build_step(ctx: Context, fc: StepForecast, st: StepStatus, depth_r: Raster | None,
               red_since: dict[int, datetime], free_beds: dict[str, int],
               forced_red_reports: dict[int, str] | None = None,
               prev_routes: dict[str, dict[str, list[int]]] | None = None) -> StepResult:
    g, t = ctx.g, fc.t
    times = EdgeTimes(close_s=st.close_h * 3600.0, depth=st.depth, amber=st.status == 1)
    node_depth = depth_r.sample(g.lon, g.lat) if depth_r is not None else np.zeros(len(g.node_ids))
    node_depth = np.nan_to_num(node_depth, nan=0.0)

    # usable shelters: dry now, stay dry ≥ 6 h on hi_m, free beds left
    usable: dict[str, int] = {}
    for s in ctx.shelters:
        if free_beds.get(s.shelter_id, 0) <= 0:
            continue
        sd = node_depth[ctx.shelter_node[s.shelter_id]]
        lvl = ctx.shelter_onset.get(s.shelter_id, float("nan"))
        if sd > C.WET_DEPTH_M:
            continue
        if not math.isnan(lvl) and fc.hi.first_crossing(lvl, h_max=config.SHELTER_SAFE_H) is not None:
            continue
        usable[s.shelter_id] = ctx.shelter_node[s.shelter_id]

    unreachable: list[dict] = []
    staged: dict[str, dict] = {}
    for c in ctx.colonies:
        wet_at = ctx.wet_at.get(c.colony_id)
        if wet_at is None:
            continue
        if fc.observed >= wet_at:
            unreachable.append({"colony_id": c.colony_id, "reason": "already_wet", "population": c.population_est})
            continue
        h_sub = fc.level.first_crossing(wet_at, h_max=config.PLAN_HORIZON_H)
        if h_sub is None:
            continue
        v_norm = ctx.norm.v_norm(c)
        speed = priority.walk_speed(v_norm)
        origin = pick_origin(g, c, node_depth, st)
        if origin is None:
            unreachable.append({"colony_id": c.colony_id, "reason": "no_dry_origin", "population": c.population_est})
            continue
        cands = build_candidates(g, origin[0], usable, times, speed)
        if not cands.candidates:
            unreachable.append({"colony_id": c.colony_id, "reason": "no_feasible_route",
                                "population": c.population_est})
            continue
        lead = h_sub
        best = cands.candidates[0].best
        prio = priority.score(lead, ctx.norm.pop_norm(c), v_norm, best.amber_share)
        staged[c.colony_id] = {"colony": c, "h_sub": h_sub, "speed": speed, "origin": origin, "cands": cands,
                               "priority": prio, "v_norm": v_norm,
                               "demand": int(math.ceil(c.population_est * config.SHELTER_RATE))}

    demands = [Demand(cid, s["priority"], s["demand"],
                      [(cd.best.shelter_id, cd.best.walk_min) for cd in s["cands"].candidates])
               for cid, s in staged.items()]
    allocs = assign(demands, free_beds, ctx.solver)
    check_capacity(allocs, free_beds)

    plans, cand_rows, routes = [], [], {}
    trap_pop, trap_cols, trap_roads = 0, [], []
    for cid, s in staged.items():
        c: Colony = s["colony"]
        cands: ColonyCandidates = s["cands"]
        a = allocs[cid]
        cand_rows.append({
            "colony_id": cid, "origin_node": g.node_ids[cands.origin], "origin_offset_m": round(s["origin"][1]),
            "speed_kmh": cands.speed_kmh, "search_mode": cands.mode, "demand": s["demand"],
            "candidates": [{"best": _cand_json(g, cd.best), "alt": _cand_json(g, cd.alt)} for cd in cands.candidates],
            "allocations": [{"shelter_id": k, "people": v} for k, v in sorted(a.allocations.items())],
            "unassigned": a.unassigned,
        })
        if a.primary is None:
            unreachable.append({"colony_id": cid, "reason": "no_shelter_capacity", "population": c.population_est})
            continue
        by_shelter = {cd.best.shelter_id: cd for cd in cands.candidates}
        prim_cd = by_shelter[a.primary]
        primary = prim_cd.best
        others = [cd.best for cd in cands.candidates if cd.best.shelter_id != a.primary]
        others.sort(key=lambda r: (-(a.allocations.get(r.shelter_id, 0)), r.walk_s))
        backup = others[0] if others else prim_cd.alt

        h_early = fc.hi.first_crossing(ctx.wet_at[cid], h_max=config.PLAN_HORIZON_H)
        h_late = fc.lo.first_crossing(ctx.wet_at[cid], h_max=config.PLAN_HORIZON_H)

        naive = naive_path(g, g.nearest_node(*c.centroid)[1], ctx.shelter_node[a.primary], times)
        avoid, replanned = [], None
        if naive:
            nr = analyse(g, naive, st, times, s["speed"], red_since)
            avoid = nr.avoid
            if nr.trapped:
                trap_pop += c.population_est
                trap_cols.append(cid)
                trap_roads.extend(r for r in nr.trap_roads if r not in trap_roads)
        if forced_red_reports and prev_routes and cid in prev_routes:
            hit = [forced_red_reports[e] for e in prev_routes[cid].get("primary", []) if e in forced_red_reports]
            replanned = hit[0] if hit else None

        transport = s["speed"] < config.WALK_SPEED_KMH and primary.walk_min > config.TRANSPORT_WALK_MIN
        prio = priority.score(s["h_sub"], ctx.norm.pop_norm(c), s["v_norm"], primary.amber_share)
        plan = {
            "scenario_id": ctx.scenario_id, "colony_id": cid, "computed_at": iso(t),
            "t_submersion": _abs(t, s["h_sub"]), "t_submersion_earliest": _abs(t, h_early),
            "t_submersion_latest": _abs(t, h_late), "lead_time_h": _round_half(s["h_sub"]),
            "primary": _route_json(g, primary), "backup": _route_json(g, backup) if backup else None,
            "avoid": avoid, "priority": prio,
            "ext": {"walk_speed_kmh": s["speed"], "transport_needed": transport, "replanned_due_to": replanned,
                    "origin_offset_m": round(s["origin"][1]), "assigned_people": sum(a.allocations.values()),
                    "demand_people": s["demand"]},
        }
        EvacuationPlan.model_validate(plan)
        plans.append(plan)
        routes[cid] = {"primary": primary.edge_idxs, "backup": backup.edge_idxs if backup else [],
                       "speed": s["speed"]}

    plans.sort(key=lambda p: (-p["priority"], p["colony_id"]))
    for u in unreachable:
        UnreachableEntry.model_validate(u)
    roads = road_status_rows(g, st, red_since)
    for r in roads:
        RoadSegmentStatus.model_validate(r)
    trap = {"valid_at": iso(t), "trapped_population": trap_pop, "colonies": sorted(trap_cols), "roads": trap_roads}
    return StepResult(t=t, roads=roads, plans=plans, unreachable=unreachable, candidates=cand_rows, trap=trap,
                      routes=routes)


def check_invariants(ctx: Context, st: StepStatus, res: StepResult, envelope_ids: set[str] | None) -> list[str]:
    """INTEGRATION_PLAN §3 safety invariants. Returns a list of violations (empty = OK)."""
    from .tdsp import route_is_safe

    g = ctx.g
    times = EdgeTimes(close_s=st.close_h * 3600.0, depth=st.depth, amber=st.status == 1)
    errs = []
    for p in res.plans:
        r = res.routes[p["colony_id"]]
        for kind in ("primary", "backup"):
            idxs = r.get(kind) or []
            if any(st.status[e] == RED for e in idxs):
                errs.append(f"{iso(res.t)} {p['colony_id']} {kind} crosses a red edge")
            path = [(0, e) for e in idxs]
            if idxs and not route_is_safe(g, path, times, r["speed"]):
                errs.append(f"{iso(res.t)} {p['colony_id']} {kind} violates arrival+30min <= close_at")
        if p["primary"]["max_depth_m"] > C.DEPTH_CUTOFF_M:
            errs.append(f"{iso(res.t)} {p['colony_id']} primary.max_depth_m > 0.30")
    if envelope_ids is not None:
        missing = [r["edge_id"] for r in res.roads if r["edge_id"] not in envelope_ids]
        missing += [e for p in res.plans for a in p["avoid"] for e in a["edge_ids"] if e not in envelope_ids]
        if missing:
            errs.append(f"{iso(res.t)} {len(missing)} edge_ids do not join roads.geojson, e.g. {missing[0]}")
    return errs
