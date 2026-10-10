"""Deterministic slot templates in Hindi, English and SMS Hindi: the floor that always validates.

The template text contains no digit, number word, name or landmark noun; every fact enters through a
slot (SHARED §11.6). SMS variants are tried longest first until one fits in 160 code points.
Hindi review: docs/workstreams/saksham/HINDI_TEMPLATE_REVIEW.md.
"""

from __future__ import annotations

from .facts import DispatchFacts, slot_values
from .slots import substitute

URGENT, PREPARE, ALL_CLEAR, SIP = "URGENT_EVACUATION_DISPATCH", "PREPARE", "ALL_CLEAR", "SHELTER_IN_PLACE"
SMS_MAX = 160

# F1: fixed, validated sentence appended by code for high-vulnerability colonies.
VULNERABLE_HI = " पहले बुज़ुर्गों, गर्भवती महिलाओं और बच्चों को निकालें ({ELDERLY} बुज़ुर्ग)।"
VULNERABLE_EN = " Help the elderly, pregnant women and young children leave before others ({ELDERLY} elderly residents)."


def _plural_avoid(f: DispatchFacts) -> bool:
    return len(f.avoid) > 1


def _vulnerable(f: DispatchFacts) -> bool:
    return f.vulnerable_priority and f.alert_type == URGENT and bool(f.vulnerable.get("elderly"))


def message_hi(f: DispatchFacts) -> str:
    if f.alert_type == SIP:
        head = ("पानी आ चुका है: {COLONY} में पानी भर गया है।" if f.wet
                else "सावधान: {COLONY} से अभी कोई सुरक्षित पैदल रास्ता उपलब्ध नहीं है।")
        return (head + " पानी में चलकर बाहर न निकलें। छत या ऊपरी मंज़िल पर जाएं और बिजली बंद रखें।"
                " नाव और बचाव के लिए {HELP} पर कॉल करें।")
    if f.alert_type == ALL_CLEAR:
        return ("राहत: {COLONY} के लिए बाढ़ का खतरा कम हुआ है और जलस्तर घट रहा है। सावधानी से लौटें,"
                " बिजली के तारों और गहरे पानी से दूर रहें। मदद: {HELP}")
    parts = []
    if f.alert_type == URGENT:
        parts.append("तुरंत निकलें: {COLONY} में पानी किसी भी समय आ सकता है ({TSUB} तक)।" if f.imminent
                     else "चेतावनी: {LEAD} घंटे में, यानी {TSUB} तक, {COLONY} में पानी आने की आशंका है।")
    else:
        parts.append("सूचना: {COLONY} में {LEAD} घंटे में ({TSUB} तक) पानी आ सकता है।"
                     " ज़रूरी सामान, दवाइयां और कागज़ात तैयार रखें।")
    if f.has_avoid:
        parts.append(" {AVOID} {CUT} से बंद हैं, उन रास्तों से न जाएं।" if _plural_avoid(f)
                     else " {AVOID} {CUT} से बंद है, उस रास्ते से न जाएं।")
    go = "तुरंत" if f.alert_type == URGENT else "ज़रूरत पड़ने पर"
    parts.append(f" {go} {{VIA}} होकर पैदल {{SHELTER}} जाएं (खाली जगह: {{BEDS}})।" if f.has_via
                 else f" {go} पैदल {{SHELTER}} जाएं (खाली जगह: {{BEDS}})।")
    if _vulnerable(f):
        parts.append(VULNERABLE_HI)
    parts.append(" मदद: {HELP}")
    return "".join(parts)


def message_en(f: DispatchFacts) -> str:
    if f.alert_type == SIP:
        head = ("WATER HAS ARRIVED: {COLONY} is flooded." if f.wet
                else "CAUTION: There is no safe walking route out of {COLONY} right now.")
        return (head + " Do not walk through the water. Move to the roof or an upper floor and switch off power."
                " Call {HELP} for a boat and rescue.")
    if f.alert_type == ALL_CLEAR:
        return ("ALL CLEAR: The flood risk for {COLONY} has eased and the river is falling. Return carefully and"
                " keep away from power lines and deep water. Help: {HELP}")
    parts = []
    if f.alert_type == URGENT:
        parts.append("LEAVE NOW: Water may reach {COLONY} at any time (by {TSUB})." if f.imminent
                     else "WARNING: Water is likely to reach {COLONY} by {TSUB} (in about {LEAD} h).")
    else:
        parts.append("NOTICE: Water may reach {COLONY} by {TSUB} (in about {LEAD} h)."
                     " Keep medicines, documents and essentials ready.")
    if f.has_avoid:
        parts.append(" {AVOID} are closed from {CUT}; do not use them." if _plural_avoid(f)
                     else " {AVOID} is closed from {CUT}; do not use it.")
    lead = "Walk now" if f.alert_type == URGENT else "If asked to leave, walk"
    parts.append(f" {lead} via {{VIA}} to {{SHELTER}} (free places: {{BEDS}})." if f.has_via
                 else f" {lead} to {{SHELTER}} (free places: {{BEDS}}).")
    if _vulnerable(f):
        parts.append(VULNERABLE_EN)
    parts.append(" Help: {HELP}")
    return "".join(parts)


def sms_variants(f: DispatchFacts) -> list[str]:
    if f.alert_type == SIP:
        first = "{COLONY}: पानी आ चुका है।" if f.wet else "{COLONY}: सुरक्षित रास्ता नहीं।"
        return [first + " छत पर जाएं, पानी में न चलें। नाव हेतु {HELP}", first + " छत पर जाएं। {HELP}",
                "छत पर जाएं। नाव हेतु {HELP}"]
    if f.alert_type == ALL_CLEAR:
        return ["{COLONY}: खतरा कम, सावधानी से लौटें। मदद {HELP}", "खतरा कम, सावधानी से लौटें। मदद {HELP}"]
    if f.alert_type == URGENT:
        head = "{COLONY}: पानी कभी भी आ सकता है।" if f.imminent else "{COLONY}: {LEAD} घंटे में पानी।"
        short_head = "पानी कभी भी आ सकता है।" if f.imminent else "{LEAD} घंटे में पानी।"
    else:
        head, short_head = "{COLONY}: {LEAD} घंटे में पानी संभव।", "पानी संभव।"
    avoid = " {AVOID} पर न जाएं।" if f.has_avoid else ""
    via = " {VIA} से" if f.has_via else ""
    return [
        f"{head}{avoid}{via} {{SHELTER}} जाएं। मदद {{HELP}}",
        f"{head}{avoid} {{SHELTER}} जाएं। मदद {{HELP}}",
        f"{head} {{SHELTER}} जाएं। मदद {{HELP}}",
        f"{short_head} {{SHELTER}} जाएं। {{HELP}}",
        "{SHELTER} जाएं। {HELP}",
    ]


def template_texts(f: DispatchFacts) -> dict[str, str]:
    """Slot templates per field (before substitution). SMS = the longest variant that fits."""
    sms = sms_variants(f)
    values = slot_values(f, "sms")
    chosen = sms[-1]
    for cand in sms:
        try:
            final, _ = substitute(cand, values)
        except KeyError:
            continue
        if len(final) <= SMS_MAX:
            chosen = cand
            break
    return {"message_hi": message_hi(f), "message_en": message_en(f), "sms_hi": chosen}
