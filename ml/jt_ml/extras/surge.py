"""Feature F2: Rate-of-rise and threshold ETA flags."""

from typing import Dict, List, Optional
import numpy as np


def detect_surge_flags(
    curr_level: float,
    predicted_hi_m_12h: float,
    dh_1h: float,
    dh_3h: float,
    hathnikund_surge_pct: float = 0.0,
) -> Dict:
    """Detect rapid rise and upstream surges."""
    flags = []
    
    # Rapid rise: > 0.20 m in 1 hour or > 0.45 m in 3 hours
    if dh_1h >= 0.20 or dh_3h >= 0.45:
        flags.append("RAPID_RISE")

    # Crossing danger level (205.33 m) or HFL within 12 h
    if curr_level < 205.33 and predicted_hi_m_12h >= 205.33:
        flags.append("THRESHOLD_ETA_DANGER")
    if curr_level < 206.0 and predicted_hi_m_12h >= 206.0:
        flags.append("THRESHOLD_ETA_FLOODPLAIN")

    # Upstream Hathnikund release surge
    if hathnikund_surge_pct >= 50.0:
        flags.append("UPSTREAM_SURGE")

    return {
        "flags": flags,
        "dh_1h_m": round(dh_1h, 2),
        "dh_3h_m": round(dh_3h, 2),
        "predicted_hi_m_12h": round(predicted_hi_m_12h, 2),
    }
