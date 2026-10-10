"""``make -C alerts predraft SCENARIO=<id> [WINDOW=demo|all|<from>/<to>]``

Pre-drafts a validated DispatchCard for every planned or unreachable colony at each step and writes
``scenarios/<id>/dispatch_cache/<t>/<colony_id>.json`` (SHARED §11.8-10), the frontend's ladder
rung when the live draft API is unavailable. Reads/writes only under $JT_LOCAL_DATA. Uses Bedrock
when ``JT_BEDROCK_MODEL_ID`` is set and credentials exist; otherwise the validated templates
(``fallback_used=true``, ``source="template"``). Exits non-zero if any card fails validation.
"""

from __future__ import annotations

import argparse
import json
import sys

from jt_shared import constants as C
from jt_shared import io
from jt_shared.naming import s3_key
from jt_shared.timeutil import iso, parse_ts

from . import lifecycle, polly
from .drafter import Drafter
from .facts import build_facts
from .service import colony_state, gauge_context, make_card, manifest, static_data, vulnerable_priority

PREDRAFT_PRESIGN_S = 7 * 24 * 3600  # static cards stay playable through recording (plan §4.4)


def steps_for(scenario_id: str, window: str) -> list:
    m = manifest(scenario_id)
    steps = list(m.valid_at)
    if window == "demo":
        centre = m.default_at or steps[len(steps) // 2]
        steps = [t for t in steps if abs((t - centre).total_seconds()) <= 6 * 3600]
    elif window != "all":
        a, b = (parse_ts(x) for x in window.split("/"))
        steps = [t for t in steps if a <= t <= b]
    return steps


def run(scenario_id: str, window: str = "demo", drafter: Drafter | None = None, audio: bool = False) -> dict:
    drafter = drafter or Drafter()
    colonies, shelters, gaz = static_data()
    alerted: set[str] = set()
    n = failed = fallback = 0
    for t in steps_for(scenario_id, window):
        gauge = gauge_context(scenario_id, t)
        for cid, colony in colonies.items():
            plan, unreach = colony_state(scenario_id, t, cid)
            alert_type, wet = lifecycle.decide(plan, unreach, gauge, cid in alerted)
            if alert_type is None:
                continue
            if alert_type != "ALL_CLEAR":
                alerted.add(cid)
            else:
                alerted.discard(cid)
            shelter = shelters.get(plan["primary"]["shelter_id"]) if plan else None
            facts = build_facts(scenario_id, colony, alert_type, t, plan, shelter, wet, vulnerable_priority(colony))
            dr = drafter.draft(facts, gaz)
            url = None
            if audio:
                try:
                    url = polly.synthesize(polly.build_ssml(dr.results["message_hi"].final, facts.shelter_hi),
                                           presign_s=PREDRAFT_PRESIGN_S)
                except Exception:
                    url = None
            card = make_card(facts, dr, url)
            io.write_json(s3_key("dispatch_cache", scenario_id=scenario_id, valid_at=iso(t), colony_id=cid), card)
            n += 1
            failed += not card["validation"]["passed"]
            fallback += card["validation"]["fallback_used"]
    return {"scenario_id": scenario_id, "window": window, "cards": n, "validation_failed": failed,
            "fallback_used": fallback, "bedrock": drafter.enabled}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Pre-draft validated dispatch cards into dispatch_cache/")
    ap.add_argument("--scenario", default=C.PRIMARY_SCENARIO)
    ap.add_argument("--window", default="demo")
    ap.add_argument("--audio", action="store_true", help="synthesise Polly audio (needs AWS + JT_DATA_BUCKET)")
    a = ap.parse_args(argv)
    if io.local_root() is None:
        print("JT_LOCAL_DATA must be set", file=sys.stderr)
        return 2
    out = run(a.scenario, a.window, audio=a.audio)
    print(json.dumps(out))
    return 1 if out["validation_failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
