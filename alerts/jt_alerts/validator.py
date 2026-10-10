"""Deterministic dispatch validator (plan §4.3). Check names are what the UI chips show.

pre  (LLM/template text, slots still in place): numbers_match, names_match, slots_used
post (final text after substitution):           numbers_match (traceable), phones_whitelist, length, script
Only ``script``/``length`` may ever be loosened; never numbers, names or phones (plan §10).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from jt_shared import constants as C

from .facts import DispatchFacts, Gazetteer, required_slots, slot_values
from .numerals import DIGIT_RE, DIGIT_RUN_RE, LATIN_WORD_RE, devanagari_share, hi_words, normalise_hi, number_words, \
    to_ascii_digits
from .slots import KNOWN_SLOTS, MAX_USES, NUMERIC_SLOTS, Span, in_spans, slots_in, strip_slots, substitute

CHECKS = ("numbers_match", "names_match", "slots_used", "phones_whitelist", "length", "script")
FIELDS = ("message_hi", "message_en", "sms_hi")

LANDMARKS_HI = {normalise_hi(w) for w in (
    "पुल", "स्टेशन", "स्कूल", "अस्पताल", "मंदिर", "मार्ग", "रोड", "गेट", "मेट्रो", "कैंप", "चौक", "शिविर", "भवन",
    "हॉल", "बाज़ार", "फ्लाईओवर", "बैराज")}
LANDMARKS_EN = {"road", "roads", "bridge", "bridges", "station", "school", "hospital", "temple", "gate", "metro",
                "camp", "chowk", "marg", "hall", "market", "bazaar", "flyover", "barrage", "street", "underpass"}
EN_CAPS_ALLOWED = {"WARNING", "URGENT", "LEAVE", "NOW", "NOTICE", "PREPARE", "ALERT", "ALL", "CLEAR", "CAUTION",
                   "WATER", "HAS", "ARRIVED", "Help", "SMS", "Jaltaranga", "Yamuna", "I"}
MESSAGE_MAX = 600
SMS_MAX = 160
SCRIPT_MIN = 0.60
PHONE_OK = set(C.HELPLINES)


@dataclass
class FieldResult:
    field: str
    final: str | None = None
    failed: dict[str, list[str]] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return not self.failed

    def fail(self, check: str, why: str) -> None:
        self.failed.setdefault(check, []).append(why)


def _is_initial(text: str, start: int) -> bool:
    before = text[:start].rstrip()
    return before == "" or before[-1] in ".!?:;(\"'—-"


def pre_check(text: str, field_name: str, facts: DispatchFacts, gaz: Gazetteer, r: FieldResult) -> None:
    body = strip_slots(text)
    if DIGIT_RE.search(body):
        r.fail("numbers_match", "digit typed outside a slot")
    words = number_words(body)
    if words:
        r.fail("numbers_match", f"number words: {words}")

    hits = gaz.find(body)
    if hits:
        r.fail("names_match", f"gazetteer names typed: {hits}")
    if field_name in ("message_hi", "sms_hi"):
        latin = LATIN_WORD_RE.findall(body)
        if latin:
            r.fail("names_match", f"Latin tokens in Hindi text: {latin}")
        lm = [w for w in hi_words(body) if w in LANDMARKS_HI]
    else:
        caps = [m.group(0) for m in LATIN_WORD_RE.finditer(body)
                if m.group(0)[0].isupper() and m.group(0) not in EN_CAPS_ALLOWED and not _is_initial(body, m.start())]
        if caps:
            r.fail("names_match", f"capitalised words: {caps}")
        lm = [w for w in LATIN_WORD_RE.findall(body) if w.lower() in LANDMARKS_EN]
        lm += [w for w in hi_words(body) if w in LANDMARKS_HI]
    if lm:
        r.fail("names_match", f"landmark nouns: {lm}")

    used = slots_in(text)
    unknown = sorted({s for s in used if s not in KNOWN_SLOTS})
    if unknown:
        r.fail("slots_used", f"unknown slots: {unknown}")
    over = sorted({s for s in used if used.count(s) > MAX_USES})
    if over:
        r.fail("slots_used", f"slots used more than {MAX_USES}x: {over}")
    missing = sorted(required_slots(facts, field_name) - set(used))
    if missing:
        r.fail("slots_used", f"missing required slots: {missing}")


def post_check(final: str, spans: list[Span], field_name: str, r: FieldResult) -> None:
    for m in DIGIT_RE.finditer(final):
        if not in_spans(m.start(), spans):
            r.fail("numbers_match", f"untraceable digit at {m.start()}")
            break
    for m in DIGIT_RUN_RE.finditer(final):
        run = to_ascii_digits(m.group(0))
        if len(run) >= 3 and run not in PHONE_OK and not in_spans(m.start(), spans, NUMERIC_SLOTS):
            r.fail("phones_whitelist", f"number {run} is not 1077/112")
    if re.search(r"\+\s*91|(?<!\d)\d{10}(?!\d)", to_ascii_digits(final)):
        r.fail("phones_whitelist", "phone-like pattern")
    if field_name == "sms_hi":
        if len(final) > SMS_MAX:
            r.fail("length", f"sms is {len(final)} > {SMS_MAX} chars")
        if "1077" not in to_ascii_digits(final):
            r.fail("length", "sms must contain 1077")
    elif len(final) > MESSAGE_MAX:
        r.fail("length", f"{field_name} is {len(final)} > {MESSAGE_MAX} chars")
    if field_name == "message_hi" and devanagari_share(final) < SCRIPT_MIN:
        r.fail("script", f"Devanagari share {devanagari_share(final):.2f} < {SCRIPT_MIN}")


def validate_field(text: str, field_name: str, facts: DispatchFacts, gaz: Gazetteer) -> FieldResult:
    r = FieldResult(field_name)
    pre_check(text, field_name, facts, gaz, r)
    channel = {"message_hi": "hi", "message_en": "en", "sms_hi": "sms"}[field_name]
    try:
        final, spans = substitute(text, slot_values(facts, channel))
    except KeyError as exc:
        r.fail("slots_used", f"slot {{{exc.args[0]}}} has no value for this plan")
        return r
    post_check(final, spans, field_name, r)
    r.final = final
    return r


def validate(texts: dict[str, str], facts: DispatchFacts, gaz: Gazetteer) -> dict[str, FieldResult]:
    return {f: validate_field(texts.get(f, ""), f, facts, gaz) for f in FIELDS}
