"""Generate ForecastNode list for a specific issued_at timestamp."""

from datetime import datetime, timedelta
from typing import List, Optional
import numpy as np
import pandas as pd
from jt_shared.constants import HORIZONS_H, DELHI_RLY_BRIDGE, DEFAULT_SCENARIO_ID
from jt_shared.models import ForecastNode
from jt_shared.timeutil import format_iso
from jt_ml.data.causal import build_causal_series_at, extract_lag_features_at
from jt_ml.models.lagreg import LagRegModel
from jt_ml.models.conformal import SplitConformalCalibrator


def generate_forecast_nodes(
    scenario_id: str,
    issued_at: datetime,
    anchors_df: pd.DataFrame,
    hk_df: Optional[pd.DataFrame] = None,
    lagreg_model: Optional[LagRegModel] = None,
    conformal: Optional[SplitConformalCalibrator] = None,
) -> List[ForecastNode]:
    """Produce [ForecastNode] for horizons [1, 3, 6, 12, 24] using causal inputs."""
    hourly, age_h = build_causal_series_at(anchors_df, issued_at)
    curr_level = float(hourly.iloc[-1])
    feats = extract_lag_features_at(hourly, hk_df, issued_at)

    model_name = "persistence"
    predicted_levels = {h: curr_level for h in HORIZONS_H}
    if lagreg_model is not None and lagreg_model.is_fitted:
        predicted_levels = lagreg_model.predict_levels(curr_level, feats)
        model_name = "lagreg-v1"

    calib = conformal or SplitConformalCalibrator(alpha=0.2)
    # Default floor if not calibrated
    if not calib.q_values:
        calib.fit({h: [0.1 * np.sqrt(h)] for h in HORIZONS_H})

    nodes = []
    for h in HORIZONS_H:
        valid_at_dt = issued_at + timedelta(hours=h)
        pred = round(float(predicted_levels[h]), 3)
        lo_m, hi_m, _ = calib.get_interval(h, pred)
        nodes.append(
            ForecastNode(
                scenario_id=scenario_id,
                issued_at=format_iso(issued_at),
                station_id=DELHI_RLY_BRIDGE,
                horizon_h=h,
                valid_at=format_iso(valid_at_dt),
                level_m=pred,
                lo_m=lo_m,
                hi_m=hi_m,
                coverage=0.8,
                model=model_name,
            )
        )
    return nodes
