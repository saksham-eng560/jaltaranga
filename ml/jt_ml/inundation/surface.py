"""Generate FloodSurface TIF raster and categorized GeoJSON vectors."""

import json
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
import rasterio
from rasterio.transform import from_bounds
from shapely.geometry import Polygon, MultiPolygon, mapping
from shapely.ops import unary_union
from jt_shared.constants import DEPTH_CLASSES
from jt_ml.inundation.onset import depth_at_level


def export_depth_cog(
    depth: np.ndarray,
    bounds: Tuple[float, float, float, float], # min_lon, min_lat, max_lon, max_lat
    out_tif_path: Path,
):
    """Save depth array as GeoTIFF."""
    ny, nx = depth.shape
    transform = from_bounds(bounds[0], bounds[1], bounds[2], bounds[3], nx, ny)
    
    out_tif_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        out_tif_path,
        "w",
        driver="GTiff",
        height=ny,
        width=nx,
        count=1,
        dtype=rasterio.float32,
        crs="EPSG:4326",
        transform=transform,
        compress="deflate",
    ) as dst:
        dst.write(depth.astype(np.float32), 1)


def export_depth_geojson(
    depth: np.ndarray,
    lons: np.ndarray,
    lats: np.ndarray,
    out_geojson_path: Path,
    min_depth_m: float = 0.05,
):
    """Vectorize depth into polygon features with depth_class."""
    ny, nx = depth.shape
    dx = (lons[-1] - lons[0]) / (nx - 1)
    dy = (lats[0] - lats[-1]) / (ny - 1)

    features = []
    
    # Classify by bands
    bands = [
        ("0.05-0.3", 0.05, 0.3),
        ("0.3-1", 0.3, 1.0),
        ("1-2", 1.0, 2.0),
        (">2", 2.0, 99.0),
    ]

    for band_name, lo, hi in bands:
        mask = (depth >= lo) & (depth < hi)
        if not np.any(mask):
            continue

        # Extract cell polygons for wet cells
        polys = []
        y_idxs, x_idxs = np.where(mask)
        # Group adjacent cells into bounding squares
        for y, x in zip(y_idxs, x_idxs):
            lon_c = lons[x]
            lat_c = lats[y]
            poly = Polygon([
                (lon_c - dx / 2, lat_c - dy / 2),
                (lon_c + dx / 2, lat_c - dy / 2),
                (lon_c + dx / 2, lat_c + dy / 2),
                (lon_c - dx / 2, lat_c + dy / 2),
            ])
            polys.append(poly)

        if polys:
            merged = unary_union(polys).simplify(0.0001)
            if not merged.is_empty:
                geom = mapping(merged)
                features.append({
                    "type": "Feature",
                    "properties": {
                        "depth_class": band_name,
                        "min_depth_m": lo,
                        "max_depth_m": hi,
                    },
                    "geometry": geom,
                })

    fc = {
        "type": "FeatureCollection",
        "features": features,
    }

    out_geojson_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_geojson_path, "w") as f:
        json.dump(fc, f)
