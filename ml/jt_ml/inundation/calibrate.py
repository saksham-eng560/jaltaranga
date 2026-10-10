"""Datum offset delta and slope S calibration on ground truth calibration points."""

import json
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd
from jt_ml.inundation.grid import CorridorGrid
from jt_ml.inundation.onset import compute_onset_raster


def calibrate_delta_slope(
    grid: CorridorGrid,
    calib_points_df: pd.DataFrame,
    peak_level_m: float = 208.66,
    delta_range: Tuple[float, float] = (-3.0, 2.0),
    delta_step: float = 0.25,
    slopes: List[float] = [0.15, 0.20, 0.25, 0.30],
) -> Dict:
    """Fit delta and S using balanced accuracy on calib_points at peak 2023 flood level.
    
    Balanced accuracy = 0.5 * (True Positive Rate + True Negative Rate).
    Only 4 reconstructions needed (one per slope S) since delta is an additive constant!
    """
    wet_pts = calib_points_df[calib_points_df["label"] == 1]
    dry_pts = calib_points_df[calib_points_df["label"] == 0]

    deltas = np.arange(delta_range[0], delta_range[1] + 1e-5, delta_step)

    best_score = -1.0
    best_delta = 0.0
    best_slope = slopes[0]
    best_tpr = 0.0
    best_tnr = 0.0

    # Fast evaluation: precompute onset for each slope at delta=0
    for slope in slopes:
        zprime_base = grid.compute_zprime(delta_m=0.0, slope_m_per_km=slope)
        onset_base = compute_onset_raster(zprime_base, grid.river_mask)

        for delta in deltas:
            onset = onset_base + delta
            
            # Predict for points
            # For each point, find grid index
            def eval_points(pts: pd.DataFrame) -> np.ndarray:
                preds = []
                for _, r in pts.iterrows():
                    # Nearest grid index
                    ix = int(np.argmin(np.abs(grid.lons - r["lon"])))
                    iy = int(np.argmin(np.abs(grid.lats - r["lat"])))
                    flooded = onset[iy, ix] <= peak_level_m
                    preds.append(1 if flooded else 0)
                return np.array(preds)

            wet_preds = eval_points(wet_pts) if not wet_pts.empty else np.array([1])
            dry_preds = eval_points(dry_pts) if not dry_pts.empty else np.array([0])

            tpr = np.mean(wet_preds == 1)
            tnr = np.mean(dry_preds == 0)
            bacc = 0.5 * (tpr + tnr)

            if bacc > best_score:
                best_score = bacc
                best_delta = float(delta)
                best_slope = float(slope)
                best_tpr = float(tpr)
                best_tnr = float(tnr)

    result = {
        "delta_m": round(best_delta, 2),
        "slope_m_per_km": round(best_slope, 3),
        "balanced_acc": round(best_score, 3),
        "tpr": round(best_tpr, 3),
        "tnr": round(best_tnr, 3),
        "n_wet": len(wet_pts),
        "n_dry": len(dry_pts),
        "fallback": best_score < 0.70,
    }
    return result
