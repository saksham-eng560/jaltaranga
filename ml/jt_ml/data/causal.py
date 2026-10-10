"""Build strictly causal input features at issue time t."""

from datetime import datetime
import numpy as np
import pandas as pd
from typing import Tuple, Optional


def build_causal_series_at(
    anchors_df: pd.DataFrame,
    issued_at: datetime,
) -> Tuple[pd.Series, float]:
    """Filter anchors strictly to ts <= issued_at and linearly interpolate.
    
    Returns (hourly_series_up_to_issued_at, input_age_hours).
    """
    ts_cutoff = pd.to_datetime(issued_at)
    causal_df = anchors_df[anchors_df["timestamp"] <= ts_cutoff].copy()
    if causal_df.empty:
        # Fallback if issued_at is before all anchors
        first_level = float(anchors_df["level_m"].iloc[0])
        idx = pd.date_range(end=ts_cutoff, periods=72, freq="1h")
        return pd.Series(first_level, index=idx), 0.0

    last_ts = causal_df["timestamp"].iloc[-1]
    input_age_h = (ts_cutoff - last_ts).total_seconds() / 3600.0

    # Resample to hourly and interpolate linearly between anchors
    causal_df = causal_df.set_index("timestamp")
    # Add issued_at with last observed value (hold-last-value)
    if ts_cutoff not in causal_df.index:
        causal_df.loc[ts_cutoff] = causal_df.iloc[-1]

    hourly = causal_df["level_m"].resample("1h").mean().interpolate(method="time").ffill().bfill()
    return hourly, input_age_h


def extract_lag_features_at(
    drb_hourly: pd.Series,
    hk_df: Optional[pd.DataFrame] = None,
    issued_at: Optional[datetime] = None,
) -> np.ndarray:
    """Extract real-only lag features at issue time.
    
    Lags: 0, 1, 2, 3, 6, 12, 24, 48 h.
    Differences: dH/dt over 1h, 3h.
    Hathnikund discharge at lags 24, 36, 48, 72 h.
    Hour of day sin/cos.
    """
    curr_level = drb_hourly.iloc[-1]
    
    def get_lag(h: int) -> float:
        idx = len(drb_hourly) - 1 - h
        return drb_hourly.iloc[idx] if idx >= 0 else curr_level

    lags = [get_lag(h) for h in [0, 1, 2, 3, 6, 12, 24, 48]]
    dh_1h = curr_level - get_lag(1)
    dh_3h = curr_level - get_lag(3)

    # Hathnikund releases
    hk_feats = [0.0, 0.0, 0.0, 0.0]
    if hk_df is not None and not hk_df.empty and issued_at is not None:
        ts_cutoff = pd.to_datetime(issued_at)
        hk_causal = hk_df[hk_df["timestamp"] <= ts_cutoff]
        if not hk_causal.empty:
            mean_q = float(hk_causal["discharge_cumecs"].iloc[-1])
            hk_feats = [mean_q, mean_q, mean_q, mean_q]

    # Time of day sin/cos
    ts = drb_hourly.index[-1]
    hour = ts.hour
    sin_hr = np.sin(2 * np.pi * hour / 24.0)
    cos_hr = np.cos(2 * np.pi * hour / 24.0)

    features = lags + [dh_1h, dh_3h] + hk_feats + [sin_hr, cos_hr]
    return np.array(features, dtype=np.float32)
