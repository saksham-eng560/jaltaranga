from jt_alerts import lifecycle as L
from jt_shared.timeutil import parse_ts


def plan(lead, tsub_h=None, at="2023-07-11T09:00:00+05:30"):
    t = parse_ts(at)
    from datetime import timedelta

    return {"lead_time_h": lead, "computed_at": at, "t_submersion": (t + timedelta(hours=tsub_h or lead)).isoformat(),
            "primary": {"shelter_id": "S1", "via_names_en": ["A"]}, "avoid": [{"name_en": "Ring Road"}]}


def g(now=206.0, prev=205.9, hi12=206.5, hi=206.8):
    return L.GaugeContext(now, prev, hi12, hi)


def test_types():
    assert L.decide(plan(2.5), None, g()) == (L.URGENT, False)
    assert L.decide(plan(6.0), None, g()) == (L.URGENT, False)
    assert L.decide(plan(10), None, g(hi=205.9)) == (L.PREPARE, False)
    assert L.decide(plan(10), None, g(hi=206.2)) == (L.URGENT, False)  # hi ≥ 206 and water within 12 h
    assert L.decide(plan(18), None, g(hi=206.2)) == (L.PREPARE, False)
    assert L.decide(None, {"reason": "already_wet"}, g()) == (L.SIP, True)
    assert L.decide(None, {"reason": "no_feasible_route"}, g()) == (L.SIP, False)
    assert L.decide(None, None, g()) == (None, False)


def test_all_clear_needs_prior_falling_and_low_hi():
    low = g(now=205.0, prev=205.2, hi12=205.2, hi=205.3)
    assert L.decide(None, None, low, had_prior_alert=True) == (L.ALL_CLEAR, False)
    assert L.decide(None, None, low, had_prior_alert=False) == (None, False)
    assert L.decide(None, None, g(now=205.0, prev=204.9, hi12=205.2), True) == (None, False)  # rising
    assert L.decide(None, None, g(now=205.0, prev=205.2, hi12=205.4), True) == (None, False)  # 12 h max above danger


def test_dedup_cooldown_and_material_change():
    at = parse_ts("2023-07-11T09:00:00+05:30")
    h = L.plan_hash(L.URGENT, plan(2.5))
    prev = {"plan_hash": h, "at": "2023-07-11T08:30:00+05:30", "dispatch_id": "d1"}
    assert L.is_duplicate(prev, at, h)
    assert not L.is_duplicate({**prev, "at": "2023-07-11T07:30:00+05:30"}, at, h)  # cooldown over
    assert not L.is_duplicate(prev, at, L.plan_hash(L.URGENT, plan(2.0)))  # material change
    assert L.dedup_key("s", "c", L.URGENT) != L.dedup_key("s", "c", L.PREPARE)  # escalation bypasses
