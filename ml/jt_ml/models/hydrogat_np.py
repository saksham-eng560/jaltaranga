"""Pure NumPy implementation of HydroGAT-lite forward pass for zero-dependency inference."""

from typing import Dict, List
import numpy as np


class HydroGATNumPy:
    """HydroGAT-lite forward pass using pure NumPy."""

    def __init__(self, n_nodes: int = 8, hidden_dim: int = 16):
        self.n_nodes = n_nodes
        self.hidden_dim = hidden_dim
        # Default weights initialized for demonstration
        self.W_in = np.ones((1, hidden_dim), dtype=np.float32) * 0.1
        self.W_out = np.ones((hidden_dim, 5), dtype=np.float32) * 0.05
        self.horizons = [1, 3, 6, 12, 24]

    def forward(self, node_features: np.ndarray) -> Dict[int, float]:
        """Compute stage deltas for DRB node.
        node_features: (n_nodes, feature_dim)
        """
        # Linear projection + relu
        h = np.maximum(0.0, np.dot(node_features, self.W_in))
        # Simple attention aggregation across reach nodes
        h_agg = np.mean(h, axis=0)
        deltas = np.dot(h_agg, self.W_out)
        return {horizon: float(deltas[i]) for i, horizon in enumerate(self.horizons)}
