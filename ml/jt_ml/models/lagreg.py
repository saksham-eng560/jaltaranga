"""Ridge regression lag-regression model per horizon."""

import json
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np
from sklearn.linear_model import Ridge


class LagRegModel:
    """Predicts delta H(t+h) for each horizon using Ridge regression."""

    def __init__(self, horizons: List[int] = [1, 3, 6, 12, 24], alpha: float = 1.0):
        self.horizons = horizons
        self.alpha = alpha
        self.models: Dict[int, Ridge] = {h: Ridge(alpha=alpha) for h in horizons}
        self.is_fitted = False

    def fit(self, X: np.ndarray, Y: np.ndarray):
        """Fit Ridge for each horizon. Y has columns corresponding to horizons."""
        for i, h in enumerate(self.horizons):
            self.models[h].fit(X, Y[:, i])
        self.is_fitted = True

    def predict_deltas(self, x: np.ndarray) -> Dict[int, float]:
        """Predict stage deltas for single feature vector x."""
        if not self.is_fitted:
            return {h: 0.0 for h in self.horizons}
        x_2d = x.reshape(1, -1)
        return {h: float(self.models[h].predict(x_2d)[0]) for h in self.horizons}

    def predict_levels(self, current_level: float, x: np.ndarray) -> Dict[int, float]:
        deltas = self.predict_deltas(x)
        return {h: current_level + deltas[h] for h in self.horizons}

    def export_weights(self, path: Path):
        """Export model weights to json for fast inference."""
        data = {
            "horizons": self.horizons,
            "models": {
                str(h): {
                    "coef": self.models[h].coef_.tolist(),
                    "intercept": float(self.models[h].intercept_),
                }
                for h in self.horizons
            },
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def load_weights(self, path: Path):
        with open(path, "r") as f:
            data = json.load(f)
        self.horizons = data["horizons"]
        for h_str, m_data in data["models"].items():
            h = int(h_str)
            r = Ridge(alpha=self.alpha)
            r.coef_ = np.array(m_data["coef"], dtype=np.float32)
            r.intercept_ = float(m_data["intercept"])
            self.models[h] = r
        self.is_fitted = True
