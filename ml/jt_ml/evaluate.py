"""Evaluate models on pre-registered TEST split and output honest skill report."""

import json
from pathlib import Path
from typing import Dict
import numpy as np
import pandas as pd
from jt_ml.data.load import load_drb_anchors, load_hathnikund_releases
from jt_ml.data.causal import build_causal_series_at, extract_lag_features_at
from jt_ml.models.lagreg import LagRegModel
from jt_ml.metrics import compute_metrics
from jt_shared.constants import HORIZONS_H


def evaluate_on_test_split(
    model: LagRegModel,
    out_dir: Path,
) -> Dict:
    """Run honest evaluation on TEST pulse (July 9-18, 2023)."""
    anchors = load_drb_anchors()
    hk_df = load_hathnikund_releases()

    # Filter to test range (July 9 to July 18)
    test_start = pd.to_datetime("2023-07-09T00:00:00+05:30")
    test_end = pd.to_datetime("2023-07-18T23:59:59+05:30")
    test_anchors = anchors[(anchors["timestamp"] >= test_start) & (anchors["timestamp"] <= test_end)]

    metrics_by_h = {}

    for h in HORIZONS_H:
        y_true = []
        y_pred = []
        y_persist = []

        for i in range(len(test_anchors) - 1):
            ts = test_anchors["timestamp"].iloc[i]
            target_ts = ts + pd.Timedelta(hours=h)
            actual_match = test_anchors[test_anchors["timestamp"] >= target_ts]
            if actual_match.empty:
                continue

            hourly, _ = build_causal_series_at(anchors, ts)
            curr_level = float(hourly.iloc[-1])
            x = extract_lag_features_at(hourly, hk_df, ts)

            pred_deltas = model.predict_deltas(x)
            pred_level = curr_level + pred_deltas[h]
            actual_level = float(actual_match["level_m"].iloc[0])

            y_true.append(actual_level)
            y_pred.append(pred_level)
            y_persist.append(curr_level)

        if len(y_true) > 0:
            metrics_by_h[str(h)] = compute_metrics(
                np.array(y_true), np.array(y_pred), np.array(y_persist)
            )

    metrics_path = out_dir / "models" / "lagreg" / "v1" / "metrics.json"
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    with open(metrics_path, "w") as f:
        json.dump(metrics_by_h, f, indent=2)

    return metrics_by_h
