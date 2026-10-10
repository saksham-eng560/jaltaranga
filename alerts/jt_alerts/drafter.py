"""Slot-filled Bedrock drafting with an 18 s wall-clock deadline (plan §4.3, SHARED §11.6).

Converse with one forced tool ``emit_dispatch`` at temperature 0. The model only sees booleans and
the required slots, never a fact. Each field is validated; one repair call carrying the validator
errors is made only if ≥ 8 s remain; whatever still fails falls back **per field** to the template.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .facts import DispatchFacts, Gazetteer, required_slots
from .templates import ALL_CLEAR, VULNERABLE_EN, VULNERABLE_HI, _vulnerable, template_texts
from .validator import FIELDS, FieldResult, validate, validate_field

PROMPT = (Path(__file__).parent / "prompts" / "system.md").read_text("utf-8")
DEADLINE_S = float(os.environ.get("JT_DRAFT_DEADLINE_S", "18"))
REPAIR_MIN_S = 8.0
CALL_MIN_S = 3.0
TOOL = {
    "toolSpec": {
        "name": "emit_dispatch",
        "description": "Emit the slot-templated flood dispatch in Hindi, English and Hindi SMS.",
        "inputSchema": {"json": {
            "type": "object",
            "properties": {"message_hi": {"type": "string"}, "message_en": {"type": "string"},
                           "sms_hi": {"type": "string"}},
            "required": ["message_hi", "message_en", "sms_hi"],
        }},
    }
}


@dataclass
class DraftResult:
    texts: dict[str, str]  # slot templates per field (final choice)
    results: dict[str, FieldResult]  # validation of the final choice
    source: str  # bedrock | template
    fallback_fields: list[str] = field(default_factory=list)
    llm_failed_checks: list[str] = field(default_factory=list)
    llm_raw: list[dict] = field(default_factory=list)
    latency_ms: int = 0
    repaired: bool = False

    @property
    def fallback_used(self) -> bool:
        return self.source == "template" or bool(self.fallback_fields)


def bedrock_enabled() -> bool:
    if os.environ.get("JT_BEDROCK_DISABLED", "").lower() in ("1", "true", "yes"):
        return False
    return bool(os.environ.get("JT_BEDROCK_MODEL_ID"))


def make_client():
    import boto3
    from botocore.config import Config

    cfg = Config(connect_timeout=2, read_timeout=7, retries={"max_attempts": 1})
    return boto3.client("bedrock-runtime", region_name=os.environ.get("JT_BEDROCK_REGION", "us-east-1"), config=cfg)


def user_message(facts: DispatchFacts, errors: dict[str, list[str]] | None = None) -> str:
    payload: dict[str, Any] = {
        "alert_type": facts.alert_type,
        "flags": facts.flags(),
        "required_slots": {f: sorted(required_slots(facts, f)) for f in FIELDS},
    }
    if errors:
        payload["validator_errors_from_your_previous_answer"] = errors
        payload["instruction"] = "Fix every error. Keep all rules. Call emit_dispatch again."
    return json.dumps(payload, ensure_ascii=False)


def _system(facts: DispatchFacts) -> str:
    example = json.dumps(template_texts(facts), ensure_ascii=False, indent=1)
    return PROMPT.replace("{EXAMPLE}", example)


def _extract(resp: dict) -> dict[str, str] | None:
    for block in resp.get("output", {}).get("message", {}).get("content", []):
        tu = block.get("toolUse")
        if tu and tu.get("name") == "emit_dispatch":
            inp = tu.get("input") or {}
            return {f: str(inp.get(f, "")) for f in FIELDS}
    return None


def _with_vulnerable(texts: dict[str, str], facts: DispatchFacts) -> dict[str, str]:
    """F1: code appends the fixed vulnerable-first sentence to LLM messages (templates already have it)."""
    if not _vulnerable(facts):
        return texts
    out = dict(texts)
    if "{ELDERLY}" not in out.get("message_hi", ""):
        out["message_hi"] = out.get("message_hi", "") + VULNERABLE_HI
    if "{ELDERLY}" not in out.get("message_en", ""):
        out["message_en"] = out.get("message_en", "") + VULNERABLE_EN
    return out


class Drafter:
    def __init__(self, client=None, model_id: str | None = None, deadline_s: float = DEADLINE_S,
                 clock: Callable[[], float] = time.monotonic, enabled: bool | None = None):
        self.enabled = bedrock_enabled() if enabled is None else enabled
        self.model_id = model_id or os.environ.get("JT_BEDROCK_MODEL_ID", "")
        self._client = client
        self.deadline_s = deadline_s
        self.clock = clock

    @property
    def client(self):
        if self._client is None:
            self._client = make_client()
        return self._client

    def _call(self, facts: DispatchFacts, errors: dict[str, list[str]] | None, prev: dict | None) -> dict:
        messages = [{"role": "user", "content": [{"text": user_message(facts)}]}]
        if errors and prev is not None:
            messages.append({"role": "assistant", "content": [{"toolUse": {
                "toolUseId": "prev", "name": "emit_dispatch", "input": prev}}]})
            messages.append({"role": "user", "content": [
                {"toolResult": {"toolUseId": "prev", "content": [{"text": user_message(facts, errors)}],
                                "status": "error"}}]})
        return self.client.converse(
            modelId=self.model_id, system=[{"text": _system(facts)}], messages=messages,
            toolConfig={"tools": [TOOL], "toolChoice": {"tool": {"name": "emit_dispatch"}}},
            inferenceConfig={"temperature": 0, "maxTokens": 600},
        )

    def draft(self, facts: DispatchFacts, gaz: Gazetteer) -> DraftResult:
        t0 = self.clock()
        remaining = lambda: self.deadline_s - (self.clock() - t0)  # noqa: E731
        tmpl = template_texts(facts)
        if facts.alert_type == ALL_CLEAR or not self.enabled or remaining() < CALL_MIN_S:
            res = validate(tmpl, facts, gaz)
            return DraftResult(tmpl, res, "template", latency_ms=int((self.clock() - t0) * 1000))

        raw_log: list[dict] = []
        llm: dict[str, str] | None = None
        results: dict[str, FieldResult] = {}
        failed: set[str] = set()
        repaired = False
        try:
            llm = _extract(self._call(facts, None, None))
            raw_log.append({"attempt": 1, "output": llm})
            if llm:
                llm = _with_vulnerable(llm, facts)
                results = validate(llm, facts, gaz)
                bad = {f: r.failed for f, r in results.items() if not r.passed}
                failed |= {c for r in bad.values() for c in r}
                if bad and remaining() >= REPAIR_MIN_S:
                    errors = {f: [f"{c}: {'; '.join(w)}" for c, w in r.items()] for f, r in bad.items()}
                    fixed = _extract(self._call(facts, errors, llm))
                    raw_log.append({"attempt": 2, "output": fixed})
                    repaired = True
                    if fixed:
                        fixed = _with_vulnerable(fixed, facts)
                        for f in bad:
                            r2 = validate_field(fixed.get(f, ""), f, facts, gaz)
                            if r2.passed:
                                llm[f], results[f] = fixed[f], r2
        except Exception as exc:  # timeout, throttling, AccessDenied → template floor
            raw_log.append({"error": type(exc).__name__, "message": str(exc)[:300]})
            llm = None

        if not llm:
            res = validate(tmpl, facts, gaz)
            return DraftResult(tmpl, res, "template", llm_failed_checks=sorted(failed), llm_raw=raw_log,
                               latency_ms=int((self.clock() - t0) * 1000), repaired=repaired)

        texts, fallback = {}, []
        for f in FIELDS:
            if results.get(f) and results[f].passed:
                texts[f] = llm[f]
            else:
                texts[f] = tmpl[f]
                results[f] = validate_field(tmpl[f], f, facts, gaz)
                fallback.append(f)
        return DraftResult(texts, results, "bedrock", fallback_fields=fallback, llm_failed_checks=sorted(failed),
                           llm_raw=raw_log, latency_ms=int((self.clock() - t0) * 1000), repaired=repaired)
