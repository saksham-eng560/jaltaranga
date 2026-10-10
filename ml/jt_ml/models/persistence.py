"""Persistence baseline model (Delta = 0)."""

from typing import List, Tuple


class PersistenceModel:
    """Predicts delta = 0 for all horizons."""
    
    def __init__(self, horizons: List[int] = [1, 3, 6, 12, 24]):
        self.horizons = horizons

    def predict(self, current_level: float) -> List[float]:
        return [current_level for _ in self.horizons]
