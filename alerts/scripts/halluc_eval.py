"""Hallucination test (SHARED §9.3): N drafts → validator → report.

Live mode (``--live``, needs ``JT_BEDROCK_MODEL_ID`` + credentials) drafts N dispatches with Nova and
records the raw tool outputs to ``alerts/tests/recorded/live_<n>.json`` so CI can replay them.
Replay mode (default) re-validates every recorded output in ``alerts/tests/recorded/``.

Report: pass rate of raw LLM fields, fallback count, and **untraceable tokens in final cards** (must
be 0: every digit sits in a slot span and no gazetteer name appears outside a slot span).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from jt_alerts.drafter import Drafter
from jt_alerts.facts import build_facts
from jt_alerts.numerals import DIGIT_RE
from jt_alerts.service import colony_state, manifest, static_data, vulnerable_priority
from jt_alerts.slots import in_spans, substitute
from jt_alerts.facts import slot_values
from jt_alerts.templates import template_texts
from jt_alerts.validator import FIELDS, validate_field
from jt_alerts import lifecycle
from jt_shared import constants as C
from jt_shared.timeutil import parse_ts

RECORDED = Path(__file__).resolve().parents[1] / "tests" / "recorded"


def untraceable(text: str, facts, field: str, gaz) -> list[str]:
    channel = {"message_hi": "hi", "message_en": "en", "sms_hi": "sms"}[field]
    final, spans = substitute(text, slot_values(facts, channel))
    bad = [m.group(0) for m in DIGIT_RE.finditer(final) if not in_spans(m.start(), spans)]
    for name in gaz.names_en + gaz.names_hi:
        for m in re.finditer(re.escape(name), final):
            if not in_spans(m.start(), spans):
                bad.append(name)
    return bad


def facts_for(scenario_id: str, colony_id: str, t: str, alert_type: str):
    """Rebuild the facts a recorded output was drafted against (None if the data no longer supports it)."""
    colonies, shelters, _ = static_data()
    if colony_id not in colonies:
        return None
    plan, unreach = colony_state(scenario_id, parse_ts(t), colony_id)
    if alert_type in ("URGENT_EVACUATION_DISPATCH", "PREPARE") and plan is None:
        return None
    shelter = shelters.get(plan["primary"]["shelter_id"]) if plan else None
    wet = bool(unreach and unreach.get("reason") == "already_wet")
    return build_facts(scenario_id, colonies[colony_id], alert_type, t, plan, shelter, wet,
                       vulnerable_priority(colonies[colony_id]))


def facts_for_samples(scenario_id: str, n: int):
    colonies, shelters, gaz = static_data()
    out = []
    for t in manifest(scenario_id).valid_at:
        for cid, colony in colonies.items():
            plan, unreach = colony_state(scenario_id, t, cid)
            at, wet = lifecycle.decide(plan, unreach, None)
            if at is None:
                continue
            shelter = shelters.get(plan["primary"]["shelter_id"]) if plan else None
            out.append(build_facts(scenario_id, colony, at, t, plan, shelter, wet, vulnerable_priority(colony)))
    # spread samples over the scenario and alert types
    step = max(1, len(out) // n)
    return out[::step][:n], gaz


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default=C.PRIMARY_SCENARIO)
    ap.add_argument("-n", type=int, default=20)
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--report", default="-")
    a = ap.parse_args()

    samples, gaz = facts_for_samples(a.scenario, a.n)
    rows = []
    if a.live:
        drafter = Drafter(enabled=True)
        recorded = []
        for f in samples:
            dr = drafter.draft(f, gaz)
            raw = next((x["output"] for x in dr.llm_raw if x.get("output")), None)
            recorded.append({"source": "bedrock-live", "model_id": drafter.model_id, "colony_id": f.colony_id,
                             "computed_at": f.computed_at.isoformat(), "alert_type": f.alert_type,
                             "output": raw, "latency_ms": dr.latency_ms})
        RECORDED.mkdir(parents=True, exist_ok=True)
        (RECORDED / f"live_{len(recorded)}.json").write_text(json.dumps(recorded, ensure_ascii=False, indent=1))
        outputs = [(f, r["output"]) for f, r in zip(samples, recorded)]
    else:
        outputs, skipped = [], 0
        for path in sorted(RECORDED.glob("*.json")):
            for r in json.loads(path.read_text("utf-8")):
                f = facts_for(a.scenario, r["colony_id"], r["computed_at"], r["alert_type"])
                if f is None:
                    skipped += 1
                    continue
                outputs.append((f, r.get("output")))

    raw_pass = raw_total = fallbacks = untrace = 0
    for f, out in outputs:
        tmpl = template_texts(f)
        final_fields = {}
        for fld in FIELDS:
            raw_total += 1
            text = (out or {}).get(fld, "")
            res = validate_field(text, fld, f, gaz) if out else None
            if res is not None and res.passed:
                raw_pass += 1
                final_fields[fld] = text
            else:
                fallbacks += 1
                final_fields[fld] = tmpl[fld]
            untrace += len(untraceable(final_fields[fld], f, fld, gaz))
        rows.append({"colony_id": f.colony_id, "alert_type": f.alert_type, "fields_from_llm":
                     [k for k in FIELDS if out and final_fields[k] == out.get(k)]})
    report = {"mode": "live" if a.live else "replay", "drafts": len(outputs),
              "skipped_recorded": 0 if a.live else skipped,
              "raw_field_pass_rate": round(raw_pass / raw_total, 3) if raw_total else None,
              "fields_falling_back_to_template": fallbacks, "untraceable_tokens_in_final_cards": untrace,
              "rows": rows}
    text = json.dumps(report, ensure_ascii=False, indent=1)
    if a.report == "-":
        print(text)
    else:
        Path(a.report).write_text(text, "utf-8")
    return 1 if untrace else 0


if __name__ == "__main__":
    sys.exit(main())
