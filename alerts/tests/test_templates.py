import itertools

import pytest

from jt_alerts.facts import DispatchFacts, build_facts
from jt_alerts.templates import SMS_MAX, template_texts
from jt_alerts.validator import validate
from jt_shared import io
from jt_shared.naming import s3_key
from jt_shared.timeutil import parse_ts

TYPES = ["URGENT_EVACUATION_DISPATCH", "PREPARE", "SHELTER_IN_PLACE", "ALL_CLEAR"]


def test_templates_always_validate_on_real_plans(static, world):
    colonies, shelters, gaz = static
    m = io.read_json(s3_key("manifest", scenario_id="yamuna-2023-07"))
    n = 0
    for t in m["valid_at"]:
        plans = io.read_json_or(s3_key("plans", scenario_id="yamuna-2023-07", valid_at=t), None)
        if plans is None:
            continue
        for p, at, vp, wet in itertools.product(plans, TYPES, (True, False), (True, False)):
            f = build_facts("yamuna-2023-07", colonies[p["colony_id"]], at, t, p,
                            shelters[p["primary"]["shelter_id"]], wet=wet, vulnerable_priority=vp)
            res = validate(template_texts(f), f, gaz)
            assert all(r.passed for r in res.values()), (p["colony_id"], at, {k: v.failed for k, v in res.items()})
            n += 1
    assert n > 100


def long_facts(alert_type, imminent=False):
    return DispatchFacts(
        scenario_id="s", colony_id="X", computed_at=parse_ts("2023-07-11T09:00:00+05:30"), alert_type=alert_type,
        colony_en="Very Long Colony Name Sector Extension Block", colony_hi="बहुत लंबी कॉलोनी नाम सेक्टर विस्तार ब्लॉक क्षेत्र",
        shelter_id="S", shelter_en="Government Senior Secondary Co-Educational School Relief Camp",
        shelter_hi="सरकारी वरिष्ठ माध्यमिक सह-शिक्षा विद्यालय राहत शिविर परिसर", free_beds=1234,
        lead_time_h=0.5 if imminent else 3.5, t_sub=parse_ts("2023-07-11T12:30:00+05:30"),
        via_en=["Netaji Subhash Marg", "Mahatma Gandhi Marg"], via_hi=["नेताजी सुभाष मार्ग", "महात्मा गांधी मार्ग"],
        avoid=[{"name_en": "Ring Road", "name_hi": "रिंग रोड", "cutoff_at": "2023-07-11T10:00:00+05:30"},
               {"name_en": "Outer Ring Road", "name_hi": "आउटर रिंग रोड", "cutoff_at": "2023-07-11T11:00:00+05:30"}],
        vulnerable={"elderly": 310})


@pytest.mark.parametrize("alert_type", TYPES)
@pytest.mark.parametrize("imminent", [False, True])
def test_sms_fits_even_with_long_names(alert_type, imminent, toy_gaz):
    f = long_facts(alert_type, imminent)
    res = validate(template_texts(f), f, toy_gaz)
    assert res["sms_hi"].passed, res["sms_hi"].failed
    assert len(res["sms_hi"].final) <= SMS_MAX and "1077" in res["sms_hi"].final


def test_imminent_and_wet_wording(toy_gaz):
    f = long_facts("URGENT_EVACUATION_DISPATCH", imminent=True)
    assert "किसी भी समय" in validate(template_texts(f), f, toy_gaz)["message_hi"].final
    sip = long_facts("SHELTER_IN_PLACE")
    sip.wet = True
    assert "पानी आ चुका है" in validate(template_texts(sip), sip, toy_gaz)["message_hi"].final
    sip.wet = False
    assert "सुरक्षित पैदल रास्ता" in validate(template_texts(sip), sip, toy_gaz)["message_hi"].final


def test_plural_agreement_and_bed_phrasing(toy_gaz):
    two = long_facts("URGENT_EVACUATION_DISPATCH")
    res = validate(template_texts(two), two, toy_gaz)
    assert "बंद हैं, उन रास्तों से न जाएं" in res["message_hi"].final
    assert "are closed from" in res["message_en"].final and "(free places: 1234)" in res["message_en"].final
    one = long_facts("URGENT_EVACUATION_DISPATCH")
    one.avoid = one.avoid[:1]
    one.free_beds = 1
    res = validate(template_texts(one), one, toy_gaz)
    assert "बंद है, उस रास्ते से न जाएं" in res["message_hi"].final and "(खाली जगह: 1)" in res["message_hi"].final
    assert "is closed from" in res["message_en"].final and "in about 3.5 h" in res["message_en"].final
