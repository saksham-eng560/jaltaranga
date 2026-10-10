"""Draft → approve → send, shared by the Lambda handler and ``predraft`` (plan §4.4).

Draft: lifecycle → facts → [dedup] → [dispatch_cache hit unless fresh] → drafter → validator
→ Polly (if ≥ 3 s of the 18 s budget remain) → store (status ``draft``).
Approve: conditional ``draft → approved`` (idempotent) → Polly if missing → SNS → ``sent``.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from jt_shared import io
from jt_shared.models import DispatchCard, Manifest
from jt_shared.naming import s3_key
from jt_shared.timeutil import IST, iso, parse_ts, snap_to_step

from . import lifecycle, metrics, notify, polly
from .drafter import CALL_MIN_S, Drafter, DraftResult
from .facts import Gazetteer, build_facts
from .store import ConditionFailed
from .validator import CHECKS, FIELDS

ROADS_HI = Path(__file__).resolve().parents[2] / "routing" / "data" / "names_hi.json"
VULNERABLE_PRIORITY_V = 0.30  # F1 sentence when vulnerable weighted share is high


class ServiceError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def _features(key: str) -> list[dict]:
    return [f["properties"] for f in io.read_json(key)["features"]]


@lru_cache(maxsize=1)
def static_data() -> tuple[dict[str, dict], dict[str, dict], Gazetteer]:
    colonies = {c["colony_id"]: c for c in _features(s3_key("colonies"))}
    shelters = {s["shelter_id"]: s for s in _features(s3_key("shelters"))}
    roads: dict[str, str] = {}
    try:
        for f in io.read_json(s3_key("roads_geojson"))["features"]:
            p = f["properties"]
            if p.get("name"):
                roads[p["name"]] = p.get("name:hi") or p["name"]
    except io.NotFound:
        pass
    if ROADS_HI.exists():
        import json

        for en, hi in json.loads(ROADS_HI.read_text("utf-8")).items():
            roads.setdefault(en, hi)
    return colonies, shelters, Gazetteer.from_sources(list(colonies.values()), list(shelters.values()), roads)


@lru_cache(maxsize=8)
def manifest(scenario_id: str) -> Manifest:
    try:
        return Manifest.model_validate(io.read_json(s3_key("manifest", scenario_id=scenario_id)))
    except io.NotFound as exc:
        raise ServiceError(404, "scenario_not_found", f"unknown scenario {scenario_id}") from exc


def snap(scenario_id: str, at: str | None) -> datetime:
    m = manifest(scenario_id)
    t = parse_ts(at) if at else (m.default_at or m.valid_at[0])
    t = snap_to_step(t, m.step_min, m.start)
    return min(max(t, m.valid_at[0]), m.valid_at[-1])


def gauge_context(scenario_id: str, t: datetime) -> lifecycle.GaugeContext | None:
    gauges = io.read_json_or(s3_key("gauges", scenario_id=scenario_id), [])
    m = manifest(scenario_id)
    series = sorted((parse_ts(g["ts"]), g["level_m"]) for g in gauges
                    if g.get("station_id") == m.ref_station and g.get("level_m") is not None)
    now = [v for ts, v in series if ts <= t]
    if not now:
        return None
    prev = [v for ts, v in series if (t - ts).total_seconds() >= m.step_min * 60]
    nodes = io.read_json_or(s3_key("forecasts", scenario_id=scenario_id, issued_at=t), [])
    return lifecycle.GaugeContext.from_nodes(now[-1], prev[-1] if prev else None, nodes)


def colony_state(scenario_id: str, t: datetime, colony_id: str) -> tuple[dict | None, dict | None]:
    plans = io.read_json_or(s3_key("plans", scenario_id=scenario_id, valid_at=t), [])
    unreach = io.read_json_or(s3_key("unreachable", scenario_id=scenario_id, valid_at=t), [])
    plan = next((p for p in plans if p["colony_id"] == colony_id), None)
    u = next((x for x in unreach if x["colony_id"] == colony_id), None)
    return plan, u


def vulnerable_priority(colony: dict) -> bool:
    v, pop = colony.get("vulnerable") or {}, colony.get("population_est") or 0
    if pop <= 0:
        return False
    w = 1.5 * v.get("elderly", 0) + 2.0 * v.get("disabled", 0) + 1.3 * v.get("children_u5", 0) \
        + 1.8 * v.get("pregnant", 0)
    return w / pop >= VULNERABLE_PRIORITY_V


def make_card(facts, dr: DraftResult, audio_url: str | None, source: str | None = None) -> dict:
    finals = {f: dr.results[f].final for f in FIELDS}
    passed = all(dr.results[f].passed for f in FIELDS)
    card = {
        "dispatch_id": str(uuid.uuid4()),
        "plan_ref": {"scenario_id": facts.scenario_id, "colony_id": facts.colony_id,
                     "computed_at": iso(facts.computed_at)},
        "alert_type": facts.alert_type,
        "message_hi": finals["message_hi"], "message_en": finals["message_en"], "sms_hi": finals["sms_hi"],
        "audio_url_hi": audio_url,
        "validation": {"passed": passed, "checks": list(CHECKS) if passed else
                       [c for c in CHECKS if not any(c in dr.results[f].failed for f in FIELDS)],
                       "fallback_used": dr.fallback_used, "failed_checks": dr.llm_failed_checks,
                       "fallback_fields": list(FIELDS) if dr.source == "template" else dr.fallback_fields,
                       "source": source or dr.source},
        "status": "draft", "approved_by": None, "ts": iso(datetime.now(IST)),
    }
    return DispatchCard.model_validate(card).model_dump(mode="json")


class DispatchService:
    def __init__(self, store, drafter: Drafter | None = None, synth_audio: bool = True):
        self.store = store
        self.drafter = drafter or Drafter()
        self.synth_audio = synth_audio

    def draft(self, scenario_id: str, colony_id: str, at: str | None, fresh: bool = False,
              use_cache: bool = True) -> dict:
        t0 = time.monotonic()
        colonies, shelters, gaz = static_data()
        colony = colonies.get(colony_id)
        if colony is None:
            raise ServiceError(404, "colony_not_found", f"unknown colony {colony_id}")
        t = snap(scenario_id, at)
        plan, unreach = colony_state(scenario_id, t, colony_id)
        prior = any(c["plan_ref"]["colony_id"] == colony_id and c["alert_type"] != "ALL_CLEAR"
                    for c in self.store.list(scenario_id))
        alert_type, wet = lifecycle.decide(plan, unreach, gauge_context(scenario_id, t), prior)
        if alert_type is None:
            raise ServiceError(422, "no_alert_needed", f"{colony_id} needs no alert at {iso(t)}")

        phash = lifecycle.plan_hash(alert_type, plan)
        dkey = lifecycle.dedup_key(scenario_id, colony_id, alert_type)
        prev = self.store.get_state(dkey)
        if not fresh and lifecycle.is_duplicate(prev, t, phash):
            existing = self.store.get(prev["dispatch_id"])
            if existing:
                return existing

        shelter = shelters.get(plan["primary"]["shelter_id"]) if plan else None
        facts = build_facts(scenario_id, colony, alert_type, t, plan, shelter, wet, vulnerable_priority(colony))

        card = None
        if use_cache and not fresh:
            cached = io.read_json_or(s3_key("dispatch_cache", scenario_id=scenario_id, valid_at=t,
                                            colony_id=colony_id), None)
            if cached and cached.get("alert_type") == alert_type and cached["validation"]["passed"]:
                card = {**cached, "dispatch_id": str(uuid.uuid4()), "status": "draft", "approved_by": None,
                        "ts": iso(datetime.now(IST))}
                card["validation"] = {**card["validation"], "source": "cache"}
                card["audio_url_hi"] = self._represign(card.get("audio_url_hi"))
        if card is None:
            dr = self.drafter.draft(facts, gaz)
            remaining = self.drafter.deadline_s - (time.monotonic() - t0)
            audio = None
            if self.synth_audio and remaining >= CALL_MIN_S:
                audio = self._audio(dr.results["message_hi"].final, facts.shelter_hi)
            card = make_card(facts, dr, audio)
            failed = {c: 1 for c in dr.llm_failed_checks}
            metrics.emit({"DraftLatencyMs": dr.latency_ms, "FallbackUsed": int(dr.fallback_used),
                          **{f"ValidatorFail_{c}": n for c, n in failed.items()}},
                         {"alert_type": alert_type}, unit={"DraftLatencyMs": "Milliseconds"})
        DispatchCard.model_validate(card)
        self.store.put(card)
        self.store.put_state(dkey, {"plan_hash": phash, "at": iso(t), "dispatch_id": card["dispatch_id"]})
        return card

    def approve(self, dispatch_id: str, officer: str = "officer-demo") -> dict:
        try:
            card = self.store.transition(dispatch_id, "draft", "approved", approved_by=officer)
        except ConditionFailed as exc:
            card = self.store.get(dispatch_id)
            if card is None:
                raise ServiceError(404, "dispatch_not_found", dispatch_id) from exc
            if card["status"] in ("approved", "sent", "acknowledged"):
                if card["status"] == "approved":  # crashed between approve and send → finish the send
                    return self._send(card)
                return card
            raise ServiceError(409, "invalid_state", f"dispatch is {card['status']}") from exc
        return self._send(card)

    def _send(self, card: dict) -> dict:
        colonies, shelters, _ = static_data()
        if not card.get("audio_url_hi") and self.synth_audio:
            shelter_hi = None
            if card["alert_type"] in ("URGENT_EVACUATION_DISPATCH", "PREPARE"):
                plan, _ = colony_state(card["plan_ref"]["scenario_id"], parse_ts(card["plan_ref"]["computed_at"]),
                                       card["plan_ref"]["colony_id"])
                if plan:
                    shelter_hi = shelters.get(plan["primary"]["shelter_id"], {}).get("name_hi")
            card["audio_url_hi"] = self._audio(card["message_hi"], shelter_hi)
        colony_en = colonies.get(card["plan_ref"]["colony_id"], {}).get("name_en", card["plan_ref"]["colony_id"])
        notify.publish(card, colony_en)
        try:
            return self.store.transition(card["dispatch_id"], "approved", "sent", audio_url_hi=card["audio_url_hi"])
        except ConditionFailed:
            return self.store.get(card["dispatch_id"])

    def list(self, scenario_id: str | None) -> list[dict]:
        cards = self.store.list(scenario_id)
        for c in cards:
            c["audio_url_hi"] = self._represign(c.get("audio_url_hi"))
        return cards

    def ack(self, dispatch_id: str) -> dict:
        try:
            return self.store.transition(dispatch_id, "sent", "acknowledged")
        except ConditionFailed as exc:
            card = self.store.get(dispatch_id)
            if card is None:
                raise ServiceError(404, "dispatch_not_found", dispatch_id) from exc
            if card["status"] == "acknowledged":
                return card
            raise ServiceError(409, "invalid_state", f"dispatch is {card['status']}") from exc

    def _audio(self, message_hi: str, shelter_hi: str | None) -> str | None:
        try:
            return polly.synthesize(polly.build_ssml(message_hi, shelter_hi))
        except Exception:
            return None  # device voice fallback in the UI

    @staticmethod
    def _represign(url: str | None) -> str | None:
        key = polly.key_from_url(url)
        if not key or not polly.enabled():
            return url
        try:
            return polly.presign(key)
        except Exception:
            return url
