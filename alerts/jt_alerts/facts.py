"""Facts for one dispatch, computed by code only (plan §4.3).

``DispatchFacts`` holds every fact a message may contain. ``slot_values`` turns them into slot
strings per channel; ``Gazetteer`` lists every place/road name in the corridor so the validator
can reject a name that the LLM typed instead of a slot.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime

from jt_shared import constants as C
from jt_shared.timeutil import hhmm, parse_ts

from .numerals import LATIN_WORD_RE, hi_words, normalise_hi

IMMINENT_LEAD_H = 1.0  # below this the message says "any time now" instead of "in {LEAD} hours"


@dataclass
class DispatchFacts:
    scenario_id: str
    colony_id: str
    computed_at: datetime
    alert_type: str
    colony_en: str
    colony_hi: str
    shelter_id: str | None = None
    shelter_en: str | None = None
    shelter_hi: str | None = None
    free_beds: int | None = None
    walk_min: float | None = None
    lead_time_h: float | None = None
    t_sub: datetime | None = None
    via_en: list[str] = field(default_factory=list)
    via_hi: list[str] = field(default_factory=list)
    avoid: list[dict] = field(default_factory=list)  # {name_en, name_hi, cutoff_at}
    vulnerable: dict[str, int] = field(default_factory=dict)
    vulnerable_priority: bool = False
    wet: bool = False  # SHELTER_IN_PLACE because water has arrived (vs. no safe route)
    helplines: tuple[str, ...] = C.HELPLINES

    @property
    def has_via(self) -> bool:
        return bool(self.via_en)

    @property
    def has_avoid(self) -> bool:
        return bool(self.avoid)

    @property
    def imminent(self) -> bool:
        return self.lead_time_h is not None and self.lead_time_h < IMMINENT_LEAD_H

    @property
    def cut_time(self) -> datetime | None:
        return min((parse_ts(a["cutoff_at"]) for a in self.avoid), default=None)

    def flags(self) -> dict[str, bool]:
        """What the LLM is told (booleans only; it never sees a name or a number)."""
        return {"has_shelter": self.shelter_id is not None, "has_via": self.has_via, "has_avoid": self.has_avoid,
                "imminent": self.imminent, "water_arrived": self.wet}


def _lead(h: float) -> str:
    return str(int(h)) if float(h).is_integer() else f"{h:.1f}"


def slot_values(f: DispatchFacts, channel: str) -> dict[str, str]:
    """channel ∈ {hi, en, sms}."""
    hi = channel in ("hi", "sms")
    v: dict[str, str] = {"COLONY": f.colony_hi if hi else f.colony_en}
    if channel == "sms":
        v["HELP"] = "/".join(f.helplines)
    else:
        v["HELP"] = (" या " if hi else " or ").join(f.helplines)
    if f.shelter_id:
        v["SHELTER"] = f.shelter_hi if hi else f.shelter_en
    if f.free_beds is not None:
        v["BEDS"] = str(f.free_beds)
    if f.via_en:
        v["VIA"] = (" और " if hi else " and ").join(f.via_hi if hi else f.via_en)
    if f.avoid:
        names = [a["name_hi"] if hi else a["name_en"] for a in f.avoid]
        v["AVOID"] = (" और " if hi else " and ").join(names)
        v["CUT"] = hhmm(f.cut_time)
    if f.lead_time_h is not None:
        v["LEAD"] = _lead(f.lead_time_h)
    if f.t_sub is not None:
        v["TSUB"] = hhmm(f.t_sub)
    if f.vulnerable.get("elderly"):
        v["ELDERLY"] = str(f.vulnerable["elderly"])
    return v


def required_slots(f: DispatchFacts, field_name: str) -> set[str]:
    if field_name == "sms_hi":
        req = {"HELP"}
        if f.alert_type in ("URGENT_EVACUATION_DISPATCH", "PREPARE"):
            req.add("SHELTER")
        return req
    if f.alert_type in ("SHELTER_IN_PLACE", "ALL_CLEAR"):
        return {"COLONY", "HELP"}
    req = {"SHELTER", "HELP"}
    if f.has_via:
        req.add("VIA")
    if f.has_avoid:
        req |= {"AVOID", "CUT"}
    if f.alert_type == "URGENT_EVACUATION_DISPATCH":
        req |= {"TSUB"} if f.imminent else {"LEAD", "TSUB"}
    return req


# Generic words inside names that are not themselves names (so "colony" or "भवन" in prose is fine).
_GENERIC = {
    "colony", "market", "bazaar", "camp", "community", "hall", "school", "govt", "government", "relief", "sector",
    "road", "marg", "bridge", "park", "lines", "old", "nagar", "vihar", "medical", "estate", "khadar", "ka", "the",
    "कॉलोनी", "बाजार", "मार्केट", "कैंप", "सामुदायिक", "भवन", "सरकारी", "स्कूल", "राहत", "शिविर", "सेक्टर",
    "रोड", "मार्ग", "पुल", "पार्क", "लाइंस", "पुराना", "नगर", "विहार", "चिकित्सा", "एस्टेट", "खादर", "का", "की",
}
# The river is ground truth (SHARED §1), not a place the LLM could get wrong.
_ALLOWED = {"yamuna", "यमुना"}


class Gazetteer:
    """Every corridor colony, shelter and road name (hi + en), and their distinctive tokens."""

    def __init__(self, names_en: list[str], names_hi: list[str]):
        self.names_en = sorted({n for n in names_en if n}, key=len, reverse=True)
        self.names_hi = sorted({normalise_hi(n) for n in names_hi if n}, key=len, reverse=True)
        generic_hi = {normalise_hi(w) for w in _GENERIC}
        self.tokens_en = {w.lower() for n in self.names_en for w in LATIN_WORD_RE.findall(n)
                          if len(w) > 2 and w.lower() not in _GENERIC and w.lower() not in _ALLOWED}
        self.tokens_hi = {w for n in self.names_hi for w in hi_words(n)
                          if len(w) > 2 and w not in generic_hi and w not in _ALLOWED}

    def find(self, text: str) -> list[str]:
        """Names or distinctive name tokens present in ``text``."""
        hits = [n for n in self.names_en if re.search(rf"(?<![A-Za-z]){re.escape(n)}(?![A-Za-z])", text, re.I)]
        norm = normalise_hi(text)
        hits += [n for n in self.names_hi if n in norm]
        hits += [w for w in LATIN_WORD_RE.findall(text) if w.lower() in self.tokens_en]
        hits += [w for w in hi_words(text) if w in self.tokens_hi]
        return hits

    @classmethod
    def from_sources(cls, colonies: list[dict], shelters: list[dict], roads: dict[str, str]) -> Gazetteer:
        en = [c["name_en"] for c in colonies] + [s["name_en"] for s in shelters] + list(roads)
        hi = [c["name_hi"] for c in colonies] + [s["name_hi"] for s in shelters] + list(roads.values())
        return cls(en, hi)


def build_facts(scenario_id: str, colony: dict, alert_type: str, computed_at: datetime | str,
                plan: dict | None = None, shelter: dict | None = None, wet: bool = False,
                vulnerable_priority: bool = False) -> DispatchFacts:
    f = DispatchFacts(scenario_id=scenario_id, colony_id=colony["colony_id"], computed_at=parse_ts(computed_at),
                      alert_type=alert_type, colony_en=colony["name_en"], colony_hi=colony["name_hi"],
                      vulnerable=dict(colony.get("vulnerable") or {}), wet=wet,
                      vulnerable_priority=vulnerable_priority)
    if plan and alert_type in ("URGENT_EVACUATION_DISPATCH", "PREPARE"):
        prim = plan["primary"]
        f.shelter_id = prim["shelter_id"]
        if shelter:
            f.shelter_en, f.shelter_hi = shelter["name_en"], shelter["name_hi"]
            f.free_beds = shelter.get("free_beds")
        f.walk_min = prim.get("walk_min")
        f.lead_time_h = plan.get("lead_time_h")
        f.t_sub = parse_ts(plan["t_submersion"]) if plan.get("t_submersion") else None
        f.via_en = list(prim.get("via_names_en") or [])
        f.via_hi = list(prim.get("via_names_hi") or f.via_en)
        f.avoid = [{"name_en": a["name_en"], "name_hi": a["name_hi"], "cutoff_at": a["cutoff_at"]}
                   for a in plan.get("avoid") or []][:2]
    return f
