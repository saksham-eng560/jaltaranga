"""Devanagari normalisation, digits and number words (validator `numbers_match`)."""

from __future__ import annotations

import re
import unicodedata

DEV_DIGITS = "०१२३४५६७८९"
_DIGIT_MAP = {ord(d): str(i) for i, d in enumerate(DEV_DIGITS)}

DIGIT_RE = re.compile(r"[0-9०-९]")
DIGIT_RUN_RE = re.compile(r"[0-9०-९]+")
DEV_WORD_RE = re.compile(r"[ऀ-ॣॱ-ॿ]+")
LATIN_WORD_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")

_HI_NUMBER_WORDS = {
    "शून्य", "एक", "दो", "तीन", "चार", "पांच", "पाँच", "छह", "छः", "छे", "सात", "आठ", "नौ", "दस",
    "ग्यारह", "बारह", "तेरह", "चौदह", "पंद्रह", "सोलह", "बीस", "तीस", "चालीस", "पचास", "साठ", "सत्तर",
    "अस्सी", "नब्बे", "सौ", "हज़ार", "हजार", "लाख", "करोड़", "डेढ़", "ढाई", "साढ़े", "सवा", "पौने",
    "आधा", "आधे", "आधी", "दर्जन", "दोनों", "पहला", "दूसरा", "तीसरा",
}
EN_NUMBER_WORDS = {
    "zero", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
    "fifteen", "twenty", "thirty", "forty", "fifty", "hundred", "hundreds", "thousand", "thousands", "lakh",
    "lakhs", "crore", "half", "dozen", "dozens", "twice", "thrice", "quarter", "first", "second", "third",
}


def normalise_hi(text: str) -> str:
    """NFC, strip nukta, chandrabindu → anusvara: so पाँच == पांच and ज़ == ज when matching."""
    t = unicodedata.normalize("NFD", text)
    t = t.replace("़", "").replace("ँ", "ं")
    return unicodedata.normalize("NFC", t)


HI_NUMBER_WORDS = {normalise_hi(w) for w in _HI_NUMBER_WORDS}


def to_ascii_digits(text: str) -> str:
    return text.translate(_DIGIT_MAP)


def hi_words(text: str) -> list[str]:
    return DEV_WORD_RE.findall(normalise_hi(text))


def number_words(text: str) -> list[str]:
    found = [w for w in hi_words(text) if w in HI_NUMBER_WORDS]
    found += [w for w in LATIN_WORD_RE.findall(text) if w.lower() in EN_NUMBER_WORDS]
    return found


def devanagari_share(text: str) -> float:
    dev = len(re.findall(r"[ऀ-ॣॱ-ॿ]", text))
    lat = len(re.findall(r"[A-Za-z]", text))
    return dev / (dev + lat) if (dev + lat) else 0.0
