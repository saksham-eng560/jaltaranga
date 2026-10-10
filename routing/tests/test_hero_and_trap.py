from jt_routing.hero import LEAD_MAX_H, LEAD_MIN_H, pick
from jt_shared import io
from jt_shared.naming import s3_key


def test_t_hero_follows_the_rule(world):
    res = io.read_json(s3_key("hero", scenario_id="yamuna-2023-07"))
    h = res["hero"]
    assert h and h["colony_id"] == "DEL-YP-04"
    assert LEAD_MIN_H <= h["lead_time_h"] <= LEAD_MAX_H
    m = io.read_json(s3_key("manifest", scenario_id="yamuna-2023-07"))
    assert m["default_at"] == h["t"]
    # it is the *latest* qualifying step
    later = [t for t in m["valid_at"] if t > h["t"]]
    for t in later:
        for p in io.read_json_or(s3_key("plans", scenario_id="yamuna-2023-07", valid_at=t), []):
            if p["colony_id"] == "DEL-YP-04":
                assert not (LEAD_MIN_H <= p["lead_time_h"] <= LEAD_MAX_H)
    assert res["backup"] and res["backup"]["colony_id"] != "DEL-YP-04"
    assert pick("yamuna-2023-07")["hero"]["t"] == h["t"]


def test_hero_plan_has_avoid_and_trap_counterfactual(world):
    t = io.read_json(s3_key("manifest", scenario_id="yamuna-2023-07"))["default_at"]
    plan = next(p for p in io.read_json(s3_key("plans", scenario_id="yamuna-2023-07", valid_at=t))
                if p["colony_id"] == "DEL-YP-04")
    assert plan["avoid"] and plan["avoid"][0]["edge_ids"]
    assert plan["primary"]["shelter_id"] != (plan["backup"] or {}).get("shelter_id")
    trap = io.read_json(s3_key("trap_summary", scenario_id="yamuna-2023-07"))
    step = next(s for s in trap["steps"] if s["valid_at"] == t)
    assert "DEL-YP-04" in step["colonies"] and step["trapped_population"] >= 4200
    assert trap["max_trapped_population"] >= step["trapped_population"]
