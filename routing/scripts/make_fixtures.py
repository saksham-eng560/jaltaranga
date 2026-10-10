"""Regenerate Saksham's ``shared/fixtures/`` from the real writers (plan §6 Fri 19:45, §11).

Needs a precomputed dev world in $JT_LOCAL_DATA (``make -C routing demo-local``). Every fixture is
produced by the same code that produces the S3 artefacts, then trimmed to a few KB.
"""

from __future__ import annotations

import json
import sys
from datetime import timedelta
from pathlib import Path

from jt_alerts.drafter import Drafter
from jt_alerts.facts import build_facts
from jt_alerts.service import make_card, static_data, vulnerable_priority
from jt_shared import io
from jt_shared.models import (DispatchCard, EvacuationPlan, ReportPostResponse, RoadSegmentStatus, Shelter,
                              TrapSummary, UnreachableEntry)
from jt_shared.naming import s3_key
from jt_shared.timeutil import iso, parse_ts
from jt_routing import serving

OUT = Path(__file__).resolve().parents[2] / "shared" / "fixtures"
SID = "yamuna-2023-07"
STABLE_TS = "2023-07-11T09:02:00+05:30"


def write(name: str, obj) -> None:
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1) + "\n", "utf-8")
    print("wrote", OUT / name)


class _Stub:
    """Replays a hand-written failing LLM output so the fallback fixture shows the per-field path."""

    def __init__(self, out):
        self.out = out

    def converse(self, **kw):
        return {"output": {"message": {"content": [{"toolUse": {"name": "emit_dispatch", "input": self.out}}]}}}


def _stable(card: dict, n: int) -> dict:
    card = dict(card)
    card["dispatch_id"] = f"00000000-0000-4000-8000-{n:012d}"
    card["ts"] = STABLE_TS
    return DispatchCard.model_validate(card).model_dump(mode="json")


def main() -> int:
    if io.local_root() is None:
        print("JT_LOCAL_DATA must point at a precomputed dev world", file=sys.stderr)
        return 2
    OUT.mkdir(parents=True, exist_ok=True)
    hero = io.read_json(s3_key("hero", scenario_id=SID))
    t_hero = parse_ts(hero["hero"]["t"])
    hero_id, backup_id = hero["hero"]["colony_id"], (hero["backup"] or {}).get("colony_id")

    roads = io.read_json(s3_key("roads", scenario_id=SID, valid_at=t_hero))
    red = [r for r in roads if r["status"] == "red"][:15]
    amber = [r for r in roads if r["status"] == "amber"][:10]
    rows = [RoadSegmentStatus.model_validate(r).model_dump(mode="json") for r in red + amber]
    write("road_segment_status.json", rows)

    steps = [t_hero + timedelta(hours=h) for h in (-6, -3, 0, 3, 6)]
    plans_by_step, keep = {}, None
    for t in steps:
        plans = io.read_json_or(s3_key("plans", scenario_id=SID, valid_at=t), [])
        if keep is None:
            others = [p["colony_id"] for p in plans if p["colony_id"] not in (hero_id, backup_id)]
            keep = {hero_id, backup_id, *(others[:1])} - {None}
        plans_by_step[iso(t)] = [EvacuationPlan.model_validate(p).model_dump(mode="json")
                                 for p in plans if p["colony_id"] in keep]
    write("evacuation_plans.json", plans_by_step)

    unreach = io.read_json(s3_key("unreachable", scenario_id=SID, valid_at=steps[-1]))
    write("plans_unreachable.json", [UnreachableEntry.model_validate(u).model_dump(mode="json") for u in unreach])
    cands = [c for c in io.read_json(s3_key("candidates", scenario_id=SID, valid_at=t_hero))
             if c["colony_id"] == hero_id]
    write("plans_candidates.json", cands)

    trap = io.read_json(s3_key("trap_summary", scenario_id=SID))
    window = {iso(t) for t in steps}
    trap["steps"] = [s for s in trap["steps"] if s["valid_at"] in window]
    write("trap_summary.json", TrapSummary.model_validate(trap).model_dump(mode="json"))
    write("hero.json", {k: hero[k] for k in ("scenario_id", "rule", "hero", "backup")})
    cut = io.read_json(s3_key("edge_cutoffs"))
    write("edge_cutoffs_sample.json", dict(list(cut.items())[:30]))

    colonies, shelters, gaz = static_data()
    write("shelters.json", [Shelter.model_validate(s).model_dump(mode="json") for s in shelters.values()])

    plan = next(p for p in io.read_json(s3_key("plans", scenario_id=SID, valid_at=t_hero))
                if p["colony_id"] == hero_id)
    facts = build_facts(SID, colonies[hero_id], "URGENT_EVACUATION_DISPATCH", t_hero, plan,
                        shelters[plan["primary"]["shelter_id"]], vulnerable_priority=vulnerable_priority(colonies[hero_id]))
    card = _stable(make_card(facts, Drafter(enabled=False).draft(facts, gaz), None), 1)
    write("dispatch_card.json", card)

    samples = json.loads((Path(__file__).resolve().parents[2] / "alerts" / "tests" / "recorded" /
                          "handwritten_samples.json").read_text("utf-8"))
    bad = next(s["output"] for s in samples if s["expect"] == "fail")
    good = next(s["output"] for s in samples if s["expect"] == "pass")
    mixed = {**good, "message_en": bad["message_en"]}
    dr = Drafter(client=_Stub(mixed), model_id="handwritten-sample", enabled=True).draft(facts, gaz)
    write("dispatch_card_fallback.json", _stable(make_card(facts, dr, None), 2))

    wet = next((u for u in unreach if u["reason"] == "already_wet"), None)
    if wet:
        f2 = build_facts(SID, colonies[wet["colony_id"]], "SHELTER_IN_PLACE", steps[-1], wet=True)
        write("dispatch_card_shelter_in_place.json",
              _stable(make_card(f2, Drafter(enabled=False).draft(f2, gaz), None), 3))

    cached = io.read_json_or(s3_key("dispatch_cache", scenario_id=SID, valid_at=t_hero, colony_id=hero_id), None)
    if cached:
        write("dispatch_cache_sample.json",
              {"key": s3_key("dispatch_cache", scenario_id=SID, valid_at=t_hero, colony_id=hero_id),
               "card": _stable(cached, 4)})

    report = serving.make_report({"location": [77.2405, 28.6535], "kind": "road_blocked", "depth_cm": 45,
                                  "has_photo": True, "ts": iso(t_hero)}, reporter_seed="fixture")
    report["report_id"] = "00000000-0000-4000-8000-0000000000aa"
    report["photo_key"] = s3_key("report_upload", report_id=report["report_id"])
    resp = {"report": report, "upload": {"url": "https://jt-demo-data-123456789012.s3.amazonaws.com/",
                                         "fields": {"key": report["photo_key"], "Content-Type": "image/jpeg",
                                                    "policy": "<base64-policy>", "x-amz-signature": "<sig>"}}}
    write("report_post_response.json", ReportPostResponse.model_validate(resp).model_dump(mode="json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
