"""IST helpers. All contract times are ISO-8601 with an explicit +05:30 offset (§5)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import unquote

IST = timezone(timedelta(hours=5, minutes=30), name="IST")


def parse_ts(value: str | datetime) -> datetime:
    """Parse an ISO timestamp. Accepts URL-encoded strings and a '+' decoded to a space."""
    if isinstance(value, datetime):
        dt = value
    else:
        s = unquote(value.strip())
        # A raw '+' in a query string decodes to ' ' ("2023-07-13T00:00:00 05:30").
        if len(s) > 19 and s[-6] == " " and s[-3] == ":":
            s = s[:-6] + "+" + s[-5:]
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        raise ValueError(f"timestamp without offset: {value!r}")
    return dt.astimezone(IST)


def iso(dt: datetime) -> str:
    """Manifest string form: YYYY-MM-DDTHH:MM:SS+05:30."""
    if dt.tzinfo is None:
        raise ValueError("naive datetime")
    return dt.astimezone(IST).isoformat(timespec="seconds")


def hhmm(dt: datetime) -> str:
    return dt.astimezone(IST).strftime("%H:%M")


def snap_to_step(at: str | datetime, step_min: int = 60, start: str | datetime | None = None) -> datetime:
    """Snap down to the replay grid (step_min minutes, anchored at start or midnight IST)."""
    t = parse_ts(at)
    anchor = parse_ts(start) if start is not None else t.replace(hour=0, minute=0, second=0, microsecond=0)
    steps = (t - anchor) // timedelta(minutes=step_min)
    return anchor + steps * timedelta(minutes=step_min)


def hours_between(a: datetime, b: datetime) -> float:
    return (b - a).total_seconds() / 3600.0


# Names used by the ml/ workstream.
def parse_iso(value: str | datetime) -> datetime:
    return parse_ts(value)


def format_iso(dt: datetime) -> str:
    return iso(dt)
