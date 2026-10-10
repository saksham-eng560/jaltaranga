"""Feature F1: Gauge-level what-if ladder (204.0 to 209.5 m in 0.1 m steps)."""

import json
from pathlib import Path
from typing import Dict, List
import numpy as np
from jt_shared.models import WhatIfResponse
from jt_ml.inundation.onset import depth_at_level
from jt_ml.inundation.surface import export_depth_geojson


def build_whatif_ladder(
    onset: np.ndarray,
    zprime: np.ndarray,
    lons: np.ndarray,
    lats: np.ndarray,
    colonies: List[Dict],
    edge_cutoffs: Dict[str, float],
    out_dir: Path,
    min_level: float = 204.0,
    max_level: float = 209.5,
    step: float = 0.1,
) -> List[WhatIfResponse]:
    """Precompute whatif json files and flood polygons for 56 levels."""
    levels = np.arange(min_level, max_level + 1e-5, step)
    ladder_dir = out_dir / "models" / "inundation" / "v1" / "ladder"
    whatif_dir = out_dir / "models" / "inundation" / "v1" / "whatif"
    ladder_dir.mkdir(parents=True, exist_ok=True)
    whatif_dir.mkdir(parents=True, exist_ok=True)

    responses = []

    for lvl in levels:
        lvl_round = round(float(lvl), 1)
        
        # Depth GeoJSON
        depth = depth_at_level(onset, zprime, lvl_round)
        geojson_path = ladder_dir / f"{lvl_round:.1f}.geojson"
        export_depth_geojson(depth, lons, lats, geojson_path)

        # Colonies status
        wet_cols = []
        for c in colonies:
            c_lon, c_lat = c["centroid"]
            ix = int(np.argmin(np.abs(lons - c_lon)))
            iy = int(np.argmin(np.abs(lats - c_lat)))
            if onset[iy, ix] <= lvl_round:
                wet_cols.append({
                    "colony_id": c["colony_id"],
                    "wet_at_level_m": round(float(onset[iy, ix]), 2),
                })

        # Cut edge ids
        cut_edges = [
            eid for eid, cutoff_lvl in edge_cutoffs.items()
            if cutoff_lvl <= lvl_round
        ]

        resp = WhatIfResponse(
            level_m=lvl_round,
            wet_colonies=wet_cols,
            cut_colonies=[],
            cut_edge_ids=cut_edges,
            flood_geojson_url=f"/models/inundation/v1/ladder/{lvl_round:.1f}.geojson",
        )

        whatif_path = whatif_dir / f"{lvl_round:.1f}.json"
        with open(whatif_path, "w") as f:
            json.dump(resp.model_dump(), f, indent=2)

        responses.append(resp)

    return responses
