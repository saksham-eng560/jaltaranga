"""Inspect one precomputed step: summary table, optional GeoJSON dump, hero candidates.

python routing/scripts/inspect_step.py --at 2023-07-11T09:00:00+05:30 [--geojson out.geojson]
python routing/scripts/inspect_step.py --hero-candidates
"""

from __future__ import annotations

import argparse
import json

from jt_routing.hero import qualifying
from jt_shared import constants as C
from jt_shared import io
from jt_shared.naming import s3_key
from jt_shared.timeutil import iso, parse_ts


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default=C.PRIMARY_SCENARIO)
    ap.add_argument("--at")
    ap.add_argument("--geojson", help="write roads + routes for this step as one FeatureCollection")
    ap.add_argument("--hero-candidates", action="store_true")
    a = ap.parse_args()
    if a.hero_candidates:
        for cid, steps in sorted(qualifying(a.scenario).items()):
            last = steps[-1]
            print(f"{cid:<11} latest={last['t']}  lead={last['lead_time_h']}h  shelter={last['shelter_id']} "
                  f"walk={last['walk_min']}min  avoid={last['avoid']}  trapped={last['trapped']}")
        return
    if not a.at:
        ap.error("--at or --hero-candidates is required")
    t = iso(parse_ts(a.at))
    roads = io.read_json(s3_key("roads", scenario_id=a.scenario, valid_at=t))
    plans = io.read_json(s3_key("plans", scenario_id=a.scenario, valid_at=t))
    unreachable = io.read_json(s3_key("unreachable", scenario_id=a.scenario, valid_at=t))
    red = sum(r["status"] == "red" for r in roads)
    print(f"{t}: {red} red, {len(roads) - red} amber edges; {len(plans)} plans; {len(unreachable)} unreachable")
    for p in plans:
        avoid = ", ".join(f"{x['name_en']}@{x['cutoff_at'][11:16]}" for x in p["avoid"]) or "-"
        print(f"  {p['colony_id']:<11} prio={p['priority']:.3f} lead={p['lead_time_h']}h "
              f"→ {p['primary']['shelter_id']} {p['primary']['walk_min']}min via={p['primary']['via_names_en']} "
              f"backup={p['backup'] and p['backup']['shelter_id']} avoid={avoid}")
    for u in unreachable:
        print(f"  {u['colony_id']:<11} UNREACHABLE ({u['reason']}, {u['population']} people)")
    if a.geojson:
        geo = {f["properties"]["edge_id"]: f for f in io.read_json(s3_key("roads_geojson"))["features"]}
        feats = []
        for r in roads:
            f = geo.get(r["edge_id"])
            if f:
                feats.append({**f, "properties": {**f["properties"], **r}})
        for p in plans:
            for kind in ("primary", "backup"):
                if p[kind]:
                    rf = p[kind]["route_geojson"]
                    feats.append({**rf, "properties": {"colony_id": p["colony_id"], "kind": kind,
                                                       "shelter_id": p[kind]["shelter_id"]}})
        with open(a.geojson, "w", encoding="utf-8") as fh:
            json.dump({"type": "FeatureCollection", "features": feats}, fh, ensure_ascii=False)
        print(f"wrote {a.geojson} ({len(feats)} features)")


if __name__ == "__main__":
    main()
