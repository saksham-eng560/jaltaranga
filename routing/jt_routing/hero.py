"""Pick ``T_hero`` and the backup hero colony from data (SHARED §11.8-1).

``T_hero`` = the latest replay step at which the hero colony is still dry, with
``2 h <= lead_time_h <= 6 h`` and at least one feasible primary route. The backup hero is chosen
by the same rule. Reads the precomputed ``plans/<t>.json``; writes ``routing/hero.json`` and, with
``--write-manifest``, ``manifest.default_at`` (in production Shivansh owns the manifest; this flag
is for the local chain and the dev world).

``python -m jt_routing.hero [--scenario ID] [--hero DEL-YP-04] [--write-manifest]``
"""

from __future__ import annotations

import argparse
import json
import sys

from jt_shared import constants as C
from jt_shared import io
from jt_shared.naming import s3_key
from jt_shared.timeutil import iso, parse_ts

LEAD_MIN_H, LEAD_MAX_H = 2.0, 6.0


def qualifying(scenario_id: str) -> dict[str, list[dict]]:
    """colony_id → qualifying steps (chronological)."""
    manifest = io.read_json(s3_key("manifest", scenario_id=scenario_id))
    trap = {s["valid_at"]: s for s in io.read_json_or(s3_key("trap_summary", scenario_id=scenario_id), {}).get(
        "steps", [])}
    out: dict[str, list[dict]] = {}
    for t in manifest["valid_at"]:
        plans = io.read_json_or(s3_key("plans", scenario_id=scenario_id, valid_at=t), [])
        for p in plans:
            if p.get("primary") and LEAD_MIN_H <= p["lead_time_h"] <= LEAD_MAX_H:
                out.setdefault(p["colony_id"], []).append({
                    "t": t, "lead_time_h": p["lead_time_h"], "shelter_id": p["primary"]["shelter_id"],
                    "walk_min": p["primary"]["walk_min"], "avoid": [a["name_en"] for a in p["avoid"]],
                    "trapped": p["colony_id"] in trap.get(t, {}).get("colonies", []),
                })
    return out


def pick(scenario_id: str, hero: str = C.HERO_COLONY) -> dict:
    q = qualifying(scenario_id)
    result: dict = {"scenario_id": scenario_id, "rule": "latest dry step with 2h <= lead <= 6h and a primary route",
                    "hero": None, "backup": None,
                    "candidates": [{"colony_id": c, **steps[-1]} for c, steps in sorted(q.items())]}
    if hero in q:
        result["hero"] = {"colony_id": hero, **q[hero][-1]}
    others = [c for c in q if c != hero]
    if others:
        ref = parse_ts(result["hero"]["t"]) if result["hero"] else None

        def rank(c: str):
            last = q[c][-1]
            gap = abs((parse_ts(last["t"]) - ref).total_seconds()) if ref else 0
            return (gap, not last["trapped"], not last["avoid"], c)

        b = min(others, key=rank)
        result["backup"] = {"colony_id": b, **q[b][-1]}
        if result["hero"] is None:  # hero never qualifies → promote the backup
            result["hero"], result["backup"] = result["backup"], None
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Compute T_hero and the backup hero colony")
    ap.add_argument("--scenario", default=C.PRIMARY_SCENARIO)
    ap.add_argument("--hero", default=C.HERO_COLONY)
    ap.add_argument("--write-manifest", action="store_true")
    a = ap.parse_args(argv)
    res = pick(a.scenario, a.hero)
    io.write_json(s3_key("hero", scenario_id=a.scenario), res)
    print(json.dumps({k: res[k] for k in ("hero", "backup")}, ensure_ascii=False, indent=1))
    if res["hero"] is None:
        print("no colony satisfies the T_hero rule", file=sys.stderr)
        return 1
    if a.write_manifest:
        key = s3_key("manifest", scenario_id=a.scenario)
        m = io.read_json(key)
        m["default_at"] = iso(parse_ts(res["hero"]["t"]))
        io.write_json(key, m)
        print(f"manifest.default_at = {m['default_at']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
