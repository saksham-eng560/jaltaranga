"""``make -C routing precompute SCENARIO=<id> [WINDOW=demo|all] [STEP=1] [SOLVER=greedy|ortools]``

Reads and writes only under ``$JT_LOCAL_DATA`` (no AWS credentials, SHARED §11.5) and exits
non-zero if any safety invariant fails. Writes per step ``roads/<t>.json``, ``plans/<t>.json``,
``plans/<t>.unreachable.json`` (always, may be ``[]``), ``plans/<t>.candidates.json``; once per
run ``routing/trap_summary.json`` and ``static/osm/edge_cutoffs.json``.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime

from jt_shared import constants as C
from jt_shared import io
from jt_shared.models import Colony, ColonyThreshold, Manifest, Shelter, TrapSummary
from jt_shared.naming import s3_key
from jt_shared.timeutil import iso, parse_ts

from . import cutoff as cut
from .forecast import ObservedSeries, load_step_forecast
from .graph import WalkGraph, haversine_m, load_graphml
from .plan import Context, build_step, check_invariants
from .priority import Normaliser


class InvariantError(RuntimeError):
    pass


def _open_raster(key: str) -> cut.Raster | None:
    try:
        return cut.Raster.open(io.local_path(key))
    except Exception:
        return None


def _features(key: str) -> list[dict]:
    fc = io.read_json(key)
    return [f["properties"] for f in fc["features"]]


def load_context(scenario_id: str, solver: str = "greedy") -> tuple[Context, Manifest, ObservedSeries]:
    manifest = Manifest.model_validate(io.read_json(s3_key("manifest", scenario_id=scenario_id)))
    g = load_graphml(io.local_path(s3_key("graphml")))
    cutoff_r = _open_raster(s3_key("cutoff_raster"))
    if cutoff_r is None:
        print("WARNING: cutoff_0p30.tif missing → red-only mode (no amber, closures = red now)", file=sys.stderr)
    levels = cut.edge_cutoff_levels(g, cutoff_r)
    io.write_json(s3_key("edge_cutoffs"), cut.edge_cutoffs_json(g, levels))
    colonies = [Colony.model_validate(p) for p in _features(s3_key("colonies"))]
    shelters = [Shelter.model_validate(p) for p in _features(s3_key("shelters"))]
    thresholds = [ColonyThreshold.model_validate(t) for t in io.read_json(s3_key("colony_thresholds"))]
    wet_at = {t.colony_id: t.wet_at_level_m for t in thresholds}
    ctx = Context(scenario_id=scenario_id, g=g, levels=levels, colonies=colonies, shelters=shelters, wet_at=wet_at,
                  onset=_open_raster(s3_key("onset")), norm=Normaliser(colonies), solver=solver)
    observed = ObservedSeries(io.read_json(s3_key("gauges", scenario_id=scenario_id)), manifest.ref_station)
    return ctx, manifest, observed


def select_steps(manifest: Manifest, window: str, step: int) -> list[datetime]:
    steps = list(manifest.valid_at)
    if window == "demo":
        centre = manifest.default_at or steps[len(steps) // 2]
        steps = [t for t in steps if abs((t - centre).total_seconds()) <= 6 * 3600]
    elif window != "all":
        a, b = (parse_ts(x) for x in window.split("/"))
        steps = [t for t in steps if a <= t <= b]
    return steps[::step]


def load_reports(path: str | None, g: WalkGraph) -> list[tuple[datetime, str, set[int]]]:
    """F2b (Could): verified road_blocked reports → edges within 30 m turn red from replay_at."""
    if not path:
        return []
    from .config import FIELD_REPORT_RADIUS_M

    out = []
    for r in json.loads(open(path, encoding="utf-8").read()):
        if r.get("kind") != "road_blocked" or not r.get("verified"):
            continue
        lon, lat = r["location"]
        d = haversine_m(g.sample_lon, g.sample_lat, lon, lat)
        edges = {int(e) for e in g.sample_edge[d <= FIELD_REPORT_RADIUS_M]}
        out.append((parse_ts(r.get("replay_at", r["ts"])), r["report_id"], edges))
    return out


def run(scenario_id: str, window: str = "all", step: int = 1, solver: str = "greedy",
        reports: str | None = None, strict: bool = True, quiet: bool = False) -> dict:
    t0 = time.time()
    ctx, manifest, observed = load_context(scenario_id, solver)
    envelope = {f["properties"]["edge_id"] for f in io.read_json(s3_key("roads_geojson"))["features"]}
    depth_ok = True
    steps = select_steps(manifest, window, step)
    free_beds = {s.shelter_id: int(s.free_beds or 0) for s in ctx.shelters}
    blocked = load_reports(reports, ctx.g)

    # red_since needs the history before the window starts (§5.4 cutoff_at for red = first red step).
    history = [t for t in manifest.valid_at if t < steps[0]] if steps else []
    red_since: dict[int, datetime] = {}
    for t in history[-48:]:
        depth_r = _open_raster(s3_key("depth_tif", scenario_id=scenario_id, valid_at=t))
        fc = load_step_forecast(scenario_id, t, observed, manifest.issued_at)
        cut.update_red_since(cut.step_status(ctx.g, ctx.levels, cut.edge_depths(ctx.g, depth_r), fc), red_since)

    trap_steps, errors, prev_routes = [], [], None
    n_plans = n_unreach = 0
    for t in steps:
        depth_r = _open_raster(s3_key("depth_tif", scenario_id=scenario_id, valid_at=t))
        depth_ok &= depth_r is not None
        fc = load_step_forecast(scenario_id, t, observed, manifest.issued_at)
        forced = {e: rid for ts, rid, edges in blocked if ts <= t for e in edges}
        st = cut.step_status(ctx.g, ctx.levels, cut.edge_depths(ctx.g, depth_r), fc, set(forced))
        cut.update_red_since(st, red_since)
        res = build_step(ctx, fc, st, depth_r, red_since, free_beds, forced or None, prev_routes)
        errors += check_invariants(ctx, st, res, envelope)
        prev_routes = res.routes
        io.write_json(s3_key("roads", scenario_id=scenario_id, valid_at=t), res.roads)
        io.write_json(s3_key("plans", scenario_id=scenario_id, valid_at=t), res.plans)
        io.write_json(s3_key("unreachable", scenario_id=scenario_id, valid_at=t), res.unreachable)
        io.write_json(s3_key("candidates", scenario_id=scenario_id, valid_at=t), res.candidates)
        trap_steps.append(res.trap)
        n_plans += len(res.plans)
        n_unreach += len(res.unreachable)
        if not quiet:
            red = sum(1 for r in res.roads if r["status"] == "red")
            print(f"{iso(t)}  level={fc.observed:7.2f}  red={red:4d} amber={len(res.roads) - red:4d}  "
                  f"plans={len(res.plans):2d} unreachable={len(res.unreachable):2d}  "
                  f"trapped={res.trap['trapped_population']}")

    # Merge into an existing trap summary so a demo-window run does not drop other steps.
    key = s3_key("trap_summary", scenario_id=scenario_id)
    old = {s["valid_at"]: s for s in io.read_json_or(key, {}).get("steps", [])}
    old.update({s["valid_at"]: s for s in trap_steps})
    merged = [old[k] for k in sorted(old)]
    peak = max(merged, key=lambda s: s["trapped_population"], default=None)
    summary = {"scenario_id": scenario_id, "steps": merged,
               "max_trapped_population": peak["trapped_population"] if peak else 0,
               "max_at": peak["valid_at"] if peak and peak["trapped_population"] else None}
    TrapSummary.model_validate(summary)
    io.write_json(key, summary)

    out = {"scenario_id": scenario_id, "steps": len(steps), "plans": n_plans, "unreachable": n_unreach,
           "violations": len(errors), "depth_rasters": "ok" if depth_ok else "missing",
           "seconds": round(time.time() - t0, 1)}
    if errors:
        for e in errors[:20]:
            print("INVARIANT:", e, file=sys.stderr)
        if strict:
            raise InvariantError(f"{len(errors)} invariant violations")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Precompute road status and evacuation plans for a scenario")
    ap.add_argument("--scenario", default=C.PRIMARY_SCENARIO)
    ap.add_argument("--window", default="all", help="all | demo | <from>/<to>")
    ap.add_argument("--step", type=int, default=1)
    ap.add_argument("--solver", choices=("greedy", "ortools"), default="greedy")
    ap.add_argument("--reports", help="JSON list of FieldReport + replay_at (F2b)")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)
    if io.local_root() is None:
        print("JT_LOCAL_DATA must be set (precompute never touches AWS)", file=sys.stderr)
        return 2
    try:
        out = run(a.scenario, a.window, a.step, a.solver, a.reports, quiet=a.quiet)
    except InvariantError as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
