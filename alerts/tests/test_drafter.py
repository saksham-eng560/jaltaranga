"""Drafter on recorded outputs (no network) and the 18 s deadline (plan §8)."""

import socket

from jt_alerts.drafter import Drafter


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


class StubBedrock:
    def __init__(self, outputs, clock=None, delays=None, raise_after=None):
        self.outputs, self.clock, self.delays = list(outputs), clock, list(delays or [])
        self.raise_after, self.calls = raise_after, []

    def converse(self, **kw):
        self.calls.append(kw)
        if self.clock is not None and self.delays:
            self.clock.t += self.delays.pop(0)
        if self.raise_after is not None:
            raise socket.timeout("Read timeout on endpoint URL")
        out = self.outputs.pop(0)
        return {"output": {"message": {"role": "assistant", "content": [
            {"toolUse": {"toolUseId": "x", "name": "emit_dispatch", "input": out}}]}}}


def test_good_recorded_output_is_used(hero_facts, recorded):
    f, gaz, _ = hero_facts
    good = next(r for r in recorded if r["expect"] == "pass")["output"]
    stub = StubBedrock([good])
    d = Drafter(client=stub, model_id="m", enabled=True)
    res = d.draft(f, gaz)
    assert res.source == "bedrock" and not res.fallback_used and not res.repaired
    assert all(r.passed for r in res.results.values())
    call = stub.calls[0]
    assert call["toolConfig"]["toolChoice"] == {"tool": {"name": "emit_dispatch"}}
    assert call["inferenceConfig"]["temperature"] == 0
    # the model never sees a fact: no colony/shelter name or number in the request
    sent = str(call["messages"])
    assert "Yamuna Pushta" not in sent and "यमुना पुश्ता" not in sent and "1200" not in sent
    assert "बुज़ुर्ग" in res.results["message_hi"].final  # F1 sentence appended by code


def test_bad_output_repaired_once_then_per_field_fallback(hero_facts, recorded):
    f, gaz, _ = hero_facts
    bad = [r["output"] for r in recorded if r["expect"] == "fail"]
    good = next(r for r in recorded if r["expect"] == "pass")["output"]
    # repair fixes message_hi and sms_hi only; message_en stays bad → template for that field
    repaired = {**good, "message_en": bad[0]["message_en"]}
    stub = StubBedrock([bad[0], repaired])
    res = Drafter(client=stub, model_id="m", enabled=True).draft(f, gaz)
    assert res.repaired and len(stub.calls) == 2
    assert res.fallback_fields == ["message_en"] and res.fallback_used
    assert {"numbers_match", "names_match"} <= set(res.llm_failed_checks)
    assert all(r.passed for r in res.results.values())
    assert "toolResult" in str(stub.calls[1]["messages"])  # errors were sent back


def test_timeout_falls_back_to_template_within_deadline(hero_facts):
    f, gaz, _ = hero_facts
    clock = FakeClock()
    stub = StubBedrock([], clock=clock, delays=[7.0], raise_after=0)  # 7 s read timeout
    res = Drafter(client=stub, model_id="m", enabled=True, clock=clock).draft(f, gaz)
    assert res.source == "template" and res.fallback_used and not res.repaired
    assert res.latency_ms <= 18_000 and len(stub.calls) == 1
    assert all(r.passed for r in res.results.values())


def test_no_repair_when_less_than_8s_left(hero_facts, recorded):
    f, gaz, _ = hero_facts
    clock = FakeClock()
    bad = next(r for r in recorded if r["expect"] == "fail")["output"]
    stub = StubBedrock([bad], clock=clock, delays=[11.0])
    res = Drafter(client=stub, model_id="m", enabled=True, clock=clock).draft(f, gaz)
    assert not res.repaired and len(stub.calls) == 1
    assert res.fallback_used and res.latency_ms <= 18_000
    assert all(r.passed for r in res.results.values())


def test_disabled_and_all_clear_are_template_only(hero_facts):
    f, gaz, _ = hero_facts
    assert Drafter(enabled=False).draft(f, gaz).source == "template"
    ac = type(f)(**{**f.__dict__, "alert_type": "ALL_CLEAR"})
    stub = StubBedrock([])
    assert Drafter(client=stub, model_id="m", enabled=True).draft(ac, gaz).source == "template"
    assert stub.calls == []
