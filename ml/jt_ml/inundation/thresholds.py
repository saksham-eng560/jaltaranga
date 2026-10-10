"""Feature F6: Street flood thresholds per colony."""

import json
from pathlib import Path
from typing import List, Dict, Optional
import numpy as np
from shapely.geometry import Point
from jt_shared.models import ColonyThreshold


def compute_colony_thresholds(
    colonies: List[Dict],
    onset_raster: np.ndarray,
    cutoff_raster: np.ndarray,
    lons: np.ndarray,
    lats: np.ndarray,
    buffer_m: int = 150,
) -> List[ColonyThreshold]:
    """Compute 10th percentile onset level and cutoff level within 150m buffer of colony centroid."""
    results = []
    # ~30m per cell at 28.6 N
    cell_size_m = 30.0
    radius_cells = int(np.ceil(buffer_m / cell_size_m))

    for col in colonies:
        cid = col["colony_id"]
        c_lon, c_lat = col["centroid"]

        # Find nearest cell
        ix = int(np.argmin(np.abs(lons - c_lon)))
        iy = int(np.argmin(np.abs(lats - c_lat)))

        x_min = max(0, ix - radius_cells)
        x_max = min(len(lons), ix + radius_cells + 1)
        y_min = max(0, iy - radius_cells)
        y_max = min(len(lats), iy + radius_cells + 1)

        onset_sub = onset_raster[y_min:y_max, x_min:x_max].flatten()
        cutoff_sub = cutoff_raster[y_min:y_max, x_min:x_max].flatten()

        # Filter out dry/nodata cells (> 250 m)
        valid_onset = onset_sub[onset_sub < 250.0]
        valid_cutoff = cutoff_sub[cutoff_sub < 250.0]

        wet_at = None
        cutoff_at = None

        if len(valid_onset) > 0:
            wet_at = round(float(np.percentile(valid_onset, 10.0)), 2)
        if len(valid_cutoff) > 0:
            cutoff_at = round(float(np.percentile(valid_cutoff, 10.0)), 2)

        results.append(
            ColonyThreshold(
                colony_id=cid,
                wet_at_level_m=wet_at,
                cutoff_at_level_m=cutoff_at,
                buffer_m=buffer_m,
            )
        )

    return results


def save_colony_thresholds(thresholds: List[ColonyThreshold], path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump([t.model_dump() for t in thresholds], f, indent=2)
