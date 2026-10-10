"""Load gauges and historical records."""

import pandas as pd
from pathlib import Path
from typing import Optional
from jt_ml.paths import get_data_dir, ML_DIR


def load_drb_anchors(data_dir: Optional[Path] = None) -> pd.DataFrame:
    """Load DRB gauge anchors from pipeline parquet or fallback csv."""
    dd = data_dir or get_data_dir()
    clean_p = dd / "clean" / "gauges" / "DELHI_RLY_BRIDGE.parquet"
    if clean_p.exists():
        df = pd.read_parquet(clean_p)
        if "qc_flag" in df.columns:
            df = df[df["qc_flag"] == "ok"]
    else:
        fb_p = ML_DIR / "data" / "fallback" / "drb_anchors.csv"
        df = pd.read_csv(fb_p)

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.dropna(subset=["level_m"]).sort_values("timestamp").reset_index(drop=True)
    return df


def load_hathnikund_releases(data_dir: Optional[Path] = None) -> pd.DataFrame:
    """Load Hathnikund release data."""
    dd = data_dir or get_data_dir()
    clean_p = dd / "clean" / "gauges" / "HATHNIKUND.parquet"
    if clean_p.exists():
        df = pd.read_parquet(clean_p)
    else:
        fb_p = ML_DIR / "data" / "fallback" / "hathnikund_releases.csv"
        df = pd.read_csv(fb_p)

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.dropna(subset=["discharge_cumecs"]).sort_values("timestamp").reset_index(drop=True)
    return df
