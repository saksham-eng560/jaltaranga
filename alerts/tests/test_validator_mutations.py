"""Validator mutation test (plan §8): 100% of injected faults must be caught."""

import pytest

from jt_alerts.slots import substitute
from jt_alerts.facts import slot_values
from jt_alerts.templates import template_texts
from jt_alerts.validator import FieldResult, post_check, validate, validate_field

HI_INJECT = [
    ("numbers_match", "2"), ("numbers_match", "१२"), ("numbers_match", "दो"), ("numbers_match", "ढाई"),
    ("numbers_match", "साढ़े"), ("numbers_match", "डेढ़"), ("numbers_match", "पाँच"), ("numbers_match", "सौ"),
    ("numbers_match", "हज़ार"), ("numbers_match", "10:30"),
    ("names_match", "यमुना पुश्ता"), ("names_match", "दरियागंज"), ("names_match", "कश्मीरी"), ("names_match", "बेला"),
    ("names_match", "शिविर"), ("names_match", "पुल"), ("names_match", "मार्ग"), ("names_match", "मेट्रो"),
    ("names_match", "अस्पताल"), ("names_match", "मंदिर"), ("names_match", "Bela"), ("names_match", "ISBT"),
    ("names_match", "रोड"), ("names_match", "स्टेशन"),
    ("slots_used", "{PHONE}"), ("slots_used", "{shelter}"), ("slots_used", "{HELP} {HELP}"),
]
EN_INJECT = [
    ("numbers_match", "3"), ("numbers_match", "two"), ("numbers_match", "half"), ("numbers_match", "Twelve"),
    ("names_match", "Daryaganj"), ("names_match", "Ring Road"), ("names_match", "Kashmiri"),
    ("names_match", "the bridge"), ("names_match", "the school"), ("names_match", "the metro"),
    ("names_match", "near the temple"), ("names_match", "go via ISBT"), ("names_match", "the camp"),
    ("slots_used", "{SHELTERS}"),
]


@pytest.mark.parametrize("check,inject", HI_INJECT)
def test_hindi_injection_caught(hero_facts, check, inject):
    f, gaz, _ = hero_facts
    base = template_texts(f)["message_hi"]
    r = validate_field(base.replace("मदद:", f"{inject} मदद:"), "message_hi", f, gaz)
    assert check in r.failed, (inject, r.failed)


@pytest.mark.parametrize("check,inject", EN_INJECT)
def test_english_injection_caught(hero_facts, check, inject):
    f, gaz, _ = hero_facts
    base = template_texts(f)["message_en"]
    r = validate_field(base.replace("Help:", f"Then {inject}. Help:"), "message_en", f, gaz)
    assert check in r.failed, (inject, r.failed)


@pytest.mark.parametrize("fld", ["message_hi", "message_en", "sms_hi"])
def test_missing_required_slot_caught(hero_facts, fld):
    f, gaz, _ = hero_facts
    text = template_texts(f)[fld].replace("{SHELTER}", "")
    assert "slots_used" in validate_field(text, fld, f, gaz).failed


def test_slot_without_value_caught(hero_facts):
    f, gaz, _ = hero_facts
    f2 = type(f)(**{**f.__dict__, "via_en": [], "via_hi": []})
    r = validate_field("{VIA} होकर {SHELTER} जाएं। {LEAD} {TSUB} {AVOID} {CUT} मदद: {HELP}", "message_hi", f2, gaz)
    assert "slots_used" in r.failed


def test_latin_in_sms_caught(hero_facts):
    f, gaz, _ = hero_facts
    assert "names_match" in validate_field("{SHELTER} jao. {HELP}", "sms_hi", f, gaz).failed


@pytest.mark.parametrize("final,check", [
    ("मदद 1077 या 9876543210", "phones_whitelist"),
    ("मदद +91 1077", "phones_whitelist"),
    ("मदद 1800 पर", "phones_whitelist"),
    ("मदद १०८", "phones_whitelist"),
    ("पानी " * 40 + "1077", "length"),
    ("पानी आ रहा है, मदद 112", "length"),
])
def test_post_checks_on_final_sms(final, check):
    r = FieldResult("sms_hi")
    post_check(final, [], "sms_hi", r)
    assert check in r.failed


def test_script_check():
    r = FieldResult("message_hi")
    post_check("WARNING water is coming to the colony now 1077", [], "message_hi", r)
    assert "script" in r.failed


def test_untraceable_digit_in_final_text_caught():
    r = FieldResult("message_en")
    post_check("Walk 5 minutes. Help: 1077", [], "message_en", r)
    assert "numbers_match" in r.failed


def test_slot_digits_are_traceable_and_not_phones(hero_facts):
    f, gaz, _ = hero_facts
    res = validate(template_texts(f), f, gaz)
    assert all(r.passed for r in res.values()), {k: v.failed for k, v in res.items()}
    final, spans = substitute(template_texts(f)["message_en"], slot_values(f, "en"))
    assert any(s.slot == "BEDS" for s in spans)  # e.g. 1200 beds is a 4-digit run but not a phone


def test_toy_gazetteer_partial_tokens(toy_gaz):
    assert toy_gaz.find("go to Kashmiri now")
    assert toy_gaz.find("कश्मीरी की ओर जाएं")
    assert not toy_gaz.find("यमुना का जलस्तर बढ़ रहा है")  # the river is not a place name
    assert not toy_gaz.find("अपनी कॉलोनी से निकलें")  # generic word inside names
