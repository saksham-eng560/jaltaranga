"""Evaluation metrics: MAE, RMSE, NSE, and skill vs persistence."""

from typing import Dict, List
import numpy as np


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray, y_persist: np.ndarray) -> Dict[str, float]:
    """Calculate MAE, RMSE, NSE and skill score vs persistence."""
    errors = y_pred - y_true
    persist_errors = y_persist - y_true

    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(errors ** 2)))

    # Nash-Sutcliffe Efficiency (NSE)
    ss_res = np.sum(errors ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    nse = float(1.0 - (ss_res / ss_tot)) if ss_tot > 0 else 0.0

    # Skill score vs persistence: 1 - MSE_pred / MSE_persist
    mse_pred = np.mean(errors ** 2)
    mse_persist = np.mean(persist_errors ** 2)
    skill_vs_persist = float(1.0 - (mse_pred / mse_persist)) if mse_persist > 0 else 0.0

    return {
        "mae": round(mae, 3),
        "rmse": round(rmse, 3),
        "nse": round(nse, 3),
        "skill_vs_persistence": round(skill_vs_persist, 3),
        "n_samples": int(len(y_true)),
    }
