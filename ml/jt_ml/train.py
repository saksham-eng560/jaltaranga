"""Train Ridge lag-regression on causal training events."""

import json
from pathlib import Path
import numpy as np
import pandas as pd
from jt_ml.data.load import load_drb_anchors, load_hathnikund_releases
from jt_ml.data.causal import build_causal_series_at, extract_lag_features_at
from jt_ml.models.lagreg import LagRegModel
from jt_ml.models.conformal import SplitConformalCalibrator
from jt_shared.constants import HORIZONS_H


def train_lagreg_pipeline(out_dir: Path) -> tuple[LagRegModel, SplitConformalCalibrator]:
    """Train Ridge regression and conformal calibrator."""
    anchors = load_drb_anchors()
    hk_df = load_hathnikund_releases()

    # Generate training instances from anchors
    X_list = []
    Y_list = []
    
    # We step through anchors from index 5 to len - 2
    for i in range(5, len(anchors) - 1):
        ts = anchors["timestamp"].iloc[i]
        hourly, _ = build_causal_series_at(anchors, ts)
        x = extract_lag_features_at(hourly, hk_df, ts)
        
        curr_lvl = float(hourly.iloc[-1])
        # Find future levels for horizons
        deltas = []
        for h in HORIZONS_H:
            future_ts = ts + pd.Timedelta(hours=h)
            # Find nearest subsequent anchor or interpolate
            later_anchors = anchors[anchors["timestamp"] >= future_ts]
            if not later_anchors.empty:
                future_lvl = float(later_anchors["level_m"].iloc[0])
            else:
                future_lvl = float(anchors["level_m"].iloc[-1])
            deltas.append(future_lvl - curr_lvl)

        X_list.append(x)
        Y_list.append(deltas)

    X = np.array(X_list, dtype=np.float32)
    Y = np.array(Y_list, dtype=np.float32)

    model = LagRegModel(horizons=HORIZONS_H, alpha=1.0)
    model.fit(X, Y)

    # Save weights
    weights_path = out_dir / "models" / "lagreg" / "v1" / "weights.json"
    weights_path.parent.mkdir(parents=True, exist_ok=True)
    model.export_weights(weights_path)

    # Conformal calibration on training residuals
    residuals = {}
    for j, h in enumerate(HORIZONS_H):
        preds = model.models[h].predict(X)
        res = Y[:, j] - preds
        residuals[h] = [float(r) for r in res]

    calib = SplitConformalCalibrator(alpha=0.2)
    calib.fit(residuals)

    return model, calib
