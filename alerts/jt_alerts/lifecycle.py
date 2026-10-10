"""Alert lifecycle (F4): which alert a colony gets, plus dedup/cooldown.

Must: alert_type. URGENT when lead ≤ 6 h, or when hi_m ≥ 206.0 m with water due within 12 h;
PREPARE for other planned colonies (lead ≤ 24 h); SHELTER_IN_PLACE for colonies listed as
unreachable (already wet, or no safe walking route; SHARED §11.8-2).
Should: ALL_CLEAR (template-only) when the level is below danger, falling, and the 12 h maximum
of hi_m is below danger, for a colony that was alerted before. Dedup key
``dedup#<scenario>#<colony>#<type>`` with a plan hash and a 60-minute replay cooldown; escalation
or a material plan change bypasses it.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime

from jt_shared import constants as C
from jt_shared.timeutil import parse_ts

URGENT, PREPARE, ALL_CLEAR, SIP = "URGENT_EVACUATION_DISPATCH", "PREPARE", "ALL_CLEAR", "SHELTER_IN_PLACE"
URGENT_LEAD_H = 6.0
URGENT_HI_WINDOW_H = 12.0
COOLDOWN_MIN = 60


@dataclass
class GaugeContext:
    level_now: float
    level_prev: float | None  # one step earlier
    hi_max_12h: float | None  # max hi_m over horizons ≤ 12 h
    hi_max_now: float | None  # max hi_m over all horizons

    @property
    def falling(self) -> bool:
        return self.level_prev is not None and self.level_now < self.level_prev

    @classmethod
    def from_nodes(cls, level_now: float, level_prev: float | None, nodes: list[dict]) -> GaugeContext:
        drb = [n for n in nodes if n.get("station_id", C.REF_STATION) == C.REF_STATION]
        h12 = [n["hi_m"] for n in drb if n["horizon_h"] <= URGENT_HI_WINDOW_H]
        return cls(level_now, level_prev, max(h12) if h12 else None, max((n["hi_m"] for n in drb), default=None))


def decide(plan: dict | None, unreachable: dict | None, gauge: GaugeContext | None,
           had_prior_alert: bool = False) -> tuple[str | None, bool]:
    """→ (alert_type | None, wet). ``wet`` selects the "water has arrived" SHELTER_IN_PLACE wording."""
    if unreachable is not None:
        return SIP, unreachable.get("reason") == "already_wet"
    if plan is not None:
        lead = float(plan["lead_time_h"])
        if lead <= URGENT_LEAD_H:
            return URGENT, False
        tsub_h = (parse_ts(plan["t_submersion"]) - parse_ts(plan["computed_at"])).total_seconds() / 3600
        if gauge and gauge.hi_max_now is not None and gauge.hi_max_now >= C.EVACUATION_LEVEL_M \
                and tsub_h <= URGENT_HI_WINDOW_H:
            return URGENT, False
        return PREPARE, False
    if had_prior_alert and gauge and gauge.level_now < C.DANGER_LEVEL_M and gauge.falling \
            and gauge.hi_max_12h is not None and gauge.hi_max_12h < C.DANGER_LEVEL_M:
        return ALL_CLEAR, False
    return None, False


def plan_hash(alert_type: str, plan: dict | None) -> str:
    """Material content of a plan: shelter, via, avoid names and lead (0.5 h buckets)."""
    core: dict = {"type": alert_type}
    if plan:
        core.update({"shelter": plan["primary"]["shelter_id"], "via": plan["primary"].get("via_names_en"),
                     "avoid": [a["name_en"] for a in plan.get("avoid", [])], "lead": plan.get("lead_time_h")})
    return hashlib.sha256(json.dumps(core, sort_keys=True).encode()).hexdigest()[:16]


def dedup_key(scenario_id: str, colony_id: str, alert_type: str) -> str:
    return f"dedup#{scenario_id}#{colony_id}#{alert_type}"


def is_duplicate(prev: dict | None, at: datetime, phash: str) -> bool:
    """prev = {"plan_hash", "at", "dispatch_id"} stored under the dedup key."""
    if not prev or prev.get("plan_hash") != phash:
        return False
    return abs((at - parse_ts(prev["at"])).total_seconds()) < COOLDOWN_MIN * 60
