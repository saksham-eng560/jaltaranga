"""Exact finite-sample split-conformal prediction intervals."""

import math
from typing import Dict, List
import numpy as np


class SplitConformalCalibrator:
    """Computes exact finite-sample conformal quantile:
    q = sorted(|residuals|)[ceil((n+1)(1-alpha)) - 1]
    """

    def __init__(self, alpha: float = 0.2):
        self.alpha = alpha # 1 - alpha = 0.8 coverage
        self.q_values: Dict[int, float] = {}

    def fit(self, residuals: Dict[int, List[float]]):
        """Fit quantile from calibration residuals per horizon."""
        for h, res_list in residuals.items():
            abs_res = sorted([abs(r) for r in res_list if not math.isnan(r)])
            n = len(abs_res)
            if n == 0:
                self.q_values[h] = 0.05 * math.sqrt(h)
                continue
            
            k = int(math.ceil((n + 1) * (1.0 - self.alpha))) - 1
            k = max(0, min(k, n - 1))
            empirical_q = abs_res[k]
            # Regularization floor: max(q, 0.05 * sqrt(h))
            self.q_values[h] = max(empirical_q, 0.05 * math.sqrt(h))

    def get_interval(self, horizon_h: int, point_forecast: float) -> tuple[float, float, float]:
        """Returns (lo_m, hi_m, q) for the given horizon."""
        q = self.q_values.get(horizon_h, 0.05 * math.sqrt(horizon_h))
        lo = point_forecast - q
        hi = point_forecast + q
        return round(lo, 3), round(hi, 3), round(q, 3)
