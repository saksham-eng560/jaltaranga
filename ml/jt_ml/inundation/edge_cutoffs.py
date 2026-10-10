"""Sample cutoff_0p30.tif along road edges to produce edge_cutoffs.json."""

import json
from pathlib import Path
from typing import Dict, List
import numpy as np


def compute_edge_cutoffs(
    roads_geojson: Dict,
    cutoff_raster: np.ndarray,
    lons: np.ndarray,
    lats: np.ndarray,
) -> Dict[str, float]:
    """Sample road edges and compute minimum cutoff level per direction-agnostic edge_id."""
    edge_cutoffs = {}

    for feature in roads_geojson.get("features", []):
        props = feature.get("properties", {})
        edge_id = props.get("edge_id")
        if not edge_id:
            continue

        coords = feature.get("geometry", {}).get("coordinates", [])
        if not coords:
            continue

        levels = []
        for pt in coords:
            lon, lat = pt[0], pt[1]
            ix = int(np.argmin(np.abs(lons - lon)))
            iy = int(np.argmin(np.abs(lats - lat)))
            val = float(cutoff_raster[iy, ix])
            if val < 250.0:
                levels.append(val)

        if levels:
            edge_cutoffs[edge_id] = round(float(np.min(levels)), 2)
        else:
            edge_cutoffs[edge_id] = 210.0 # High dry floor

    return edge_cutoffs


def save_edge_cutoffs(edge_cutoffs: Dict[str, float], path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(edge_cutoffs, f, indent=2)
