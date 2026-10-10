"""jt_shared time utilities."""

from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))


def parse_iso(ts_str: str) -> datetime:
    """Parse ISO timestamp, ensuring datetime with timezone."""
    # Handle Z or +05:30
    if ts_str.endswith("Z"):
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    return datetime.fromisoformat(ts_str)


def format_iso(dt: datetime) -> str:
    """Format datetime into standard ISO format with timezone."""
    return dt.isoformat()


def snap_to_step(dt: datetime, step_minutes: int = 60) -> datetime:
    """Snap datetime down to the nearest minute interval."""
    discard = timedelta(
        minutes=dt.minute % step_minutes,
        seconds=dt.second,
        microseconds=dt.microsecond
    )
    return dt - discard
