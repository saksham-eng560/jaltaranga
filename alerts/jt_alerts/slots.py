"""Slot grammar and substitution with span tracking (SHARED §11.6).

The LLM (or a template) writes text containing ``{SLOT}`` markers; code substitutes every fact.
``substitute`` records the character span each slot value occupies in the final text, so the
validator can prove that every digit and every name in the final text came from a slot.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

SLOT_RE = re.compile(r"\{([A-Za-z_]+)\}")

# §11.6 public slots + alerts-internal ones (plan §4.3).
PUBLIC_SLOTS = {"SHELTER", "VIA", "AVOID", "LEAD", "TSUB", "HELP"}
INTERNAL_SLOTS = {"COLONY", "BEDS", "CUT", "ELDERLY"}
KNOWN_SLOTS = PUBLIC_SLOTS | INTERNAL_SLOTS
NUMERIC_SLOTS = {"LEAD", "TSUB", "CUT", "BEDS", "ELDERLY"}  # their digits are not phone numbers
MAX_USES = 2


@dataclass(frozen=True)
class Span:
    start: int
    end: int
    slot: str


def slots_in(text: str) -> list[str]:
    return SLOT_RE.findall(text)


def strip_slots(text: str) -> str:
    """Text with slot markers removed (what the pre-substitution checks inspect)."""
    return SLOT_RE.sub(" ", text)


def substitute(text: str, values: dict[str, str]) -> tuple[str, list[Span]]:
    out, spans, pos = [], [], 0
    cursor = 0
    for m in SLOT_RE.finditer(text):
        out.append(text[pos:m.start()])
        cursor += m.start() - pos
        name = m.group(1)
        if name not in values or values[name] == "":
            raise KeyError(name)
        val = values[name]
        spans.append(Span(cursor, cursor + len(val), name))
        out.append(val)
        cursor += len(val)
        pos = m.end()
    out.append(text[pos:])
    return "".join(out), spans


def in_spans(i: int, spans: list[Span], slots: set[str] | None = None) -> bool:
    return any(s.start <= i < s.end and (slots is None or s.slot in slots) for s in spans)
