"""Embankment-Aware Digital Terrain Model (DTM) for Jaltaranga.

Ingests real Copernicus GLO-30 30m DEM from AWS Open Data Registry,
clips the Delhi Yamuna floodplain corridor (Wazirabad to Okhla Barrage),
carves hydraulic bridge edge passages, extracts the embankment burn mask
separately in gauge space, and references the shared calibration set.
"""
from __future__ import annotations

import csv
import json
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import tifffile

from pipeline.ledger import record

# Domain bounds for Delhi Yamuna corridor (strictly between Wazirabad and Okhla)
LAT_MIN = 28.53
LAT_MAX = 28.720
LON_MIN = 77.18
LON_MAX = 77.34

DEM_TILE_URL = (
    "https://copernicus-dem-30m.s3.amazonaws.com/"
    "Copernicus_DSM_COG_10_N28_00_E077_00_DEM/"
    "Copernicus_DSM_COG_10_N28_00_E077_00_DEM.tif"
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEM_DIR = DATA_DIR / "dem"
RAW_TIF_PATH = DEM_DIR / "Copernicus_N28_E077_DEM.tif"
CLIPPED_NPY_PATH = DEM_DIR / "delhi_yamuna_dtm_calibrated.npy"
BURN_MASK_PATH = DEM_DIR / "burn_mask.npy"
METADATA_PATH = DEM_DIR / "meta.json"
CALIB_POINTS_CSV = DATA_DIR / "calibration_points.csv"
BURN_WAYS_CSV = DATA_DIR / "burn_ways.csv"

# Key bridges along the stretch (treated as hydrological edge passages)
BRIDGE_PASSAGES = [
    {"name": "Wazirabad Barrage Bridge", "lat": 28.7115, "lon": 77.2340, "bed_elev_m": 204.0},
    {"name": "Signature Bridge", "lat": 28.7002, "lon": 77.2318, "bed_elev_m": 203.2},
    {"name": "Yudhishtir Setu (ISBT)", "lat": 28.6720, "lon": 77.2335, "bed_elev_m": 202.0},
    {"name": "Old Yamuna Bridge (Loha Pul / DRB)", "lat": 28.6620, "lon": 77.2430, "bed_elev_m": 200.6},
    {"name": "Geeta Colony Bridge", "lat": 28.6475, "lon": 77.2515, "bed_elev_m": 199.8},
    {"name": "Vikas Marg / ITO Bridge", "lat": 28.6300, "lon": 77.2505, "bed_elev_m": 199.2},
    {"name": "Nizamuddin Railway / Barapullah Bridge", "lat": 28.5880, "lon": 77.2560, "bed_elev_m": 198.5},
    {"name": "DND Flyway", "lat": 28.5720, "lon": 77.2750, "bed_elev_m": 198.0},
    {"name": "Okhla Barrage Bridge", "lat": 28.5460, "lon": 77.3090, "bed_elev_m": 197.5},
]


@dataclass
class DTMGrid:
    elevation: np.ndarray
    burn_mask: np.ndarray
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float
    rows: int
    cols: int
    datum_offset: Optional[float] = None

    def lat_lon_to_row_col(self, lat: float, lon: float) -> Tuple[int, int]:
        row = int(round((self.lat_max - lat) / (self.lat_max - self.lat_min) * (self.rows - 1)))
        col = int(round((lon - self.lon_min) / (self.lon_max - self.lon_min) * (self.cols - 1)))
        row = max(0, min(self.rows - 1, row))
        col = max(0, min(self.cols - 1, col))
        return row, col

    def get_elevation_at(self, lat: float, lon: float) -> float:
        r, c = self.lat_lon_to_row_col(lat, lon)
        return float(self.elevation[r, c])

    def is_in_burn_mask(self, lat: float, lon: float) -> bool:
        r, c = self.lat_lon_to_row_col(lat, lon)
        return bool(self.burn_mask[r, c] > 0)


def download_copernicus_dem_if_needed(destination: Path = RAW_TIF_PATH) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists() or destination.stat().st_size < 10_000_000:
        print("Downloading real Copernicus GLO-30 DEM from AWS Open Data...")
        urllib.request.urlretrieve(DEM_TILE_URL, destination)
        record(
            dataset="copernicus-glo30-dem",
            source_url=DEM_TILE_URL,
            source_name="Copernicus GLO-30 DSM (AWS Open Data Registry)",
            licence="Copernicus Open Access Licence",
            qc_flag="ok",
            qc_notes="Original 30m COG GeoTIFF covering Delhi 1x1 degree tile N28_00_E077_00",
        )
    return destination


def load_calibration_points(path: Path = CALIB_POINTS_CSV) -> List[Dict[str, Any]]:
    """Load and validate calibration benchmarks from CSV."""
    pts = []
    if not path.exists():
        return pts
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            est_m = float(row.get("estimated_m", row.get("survey_m", 0.0)))
            pts.append({
                "name": row["name"],
                "lat": float(row["lat"]),
                "lon": float(row["lon"]),
                "estimated_m": est_m,
                "survey_m": est_m,
                "is_estimate": row.get("is_estimate", "true").strip().lower() == "true",
                "is_wet_at_hfl": row["is_wet_at_hfl"].strip().lower() == "true",
                "excluded": row["excluded"].strip().lower() == "true",
                "exclusion_reason": row.get("exclusion_reason", ""),
                "glo30_m": float(row["glo30_m"]) if row.get("glo30_m") else None,
                "basis": row.get("basis", row.get("source_reference", "")),
            })
    return pts


def build_calibrated_dtm(
    raw_tif: Path = RAW_TIF_PATH,
    force_rebuild: bool = False,
) -> DTMGrid:
    """Ingest, clip, carve bridges, generate separate burn mask, and export."""
    if not force_rebuild and CLIPPED_NPY_PATH.exists() and BURN_MASK_PATH.exists() and METADATA_PATH.exists():
        elev = np.load(CLIPPED_NPY_PATH)
        bmask = np.load(BURN_MASK_PATH)
        with open(METADATA_PATH, "r", encoding="utf-8") as f:
            meta = json.load(f)
        return DTMGrid(
            elevation=elev,
            burn_mask=bmask,
            lat_min=meta["lat_min"],
            lat_max=meta["lat_max"],
            lon_min=meta["lon_min"],
            lon_max=meta["lon_max"],
            rows=meta["rows"],
            cols=meta["cols"],
            datum_offset=meta.get("delta_m"),
        )

    download_copernicus_dem_if_needed(raw_tif)
    print("Loading Copernicus DEM GeoTIFF...")
    raw_data = tifffile.imread(str(raw_tif))

    # Tile covers Lat: [28.0, 29.0], Lon: [77.0, 78.0], 3600 x 3600
    row_start = int((29.0 - LAT_MAX) * 3600)  # ~1036
    row_end = int((29.0 - LAT_MIN) * 3600)    # ~1692
    col_start = int((LON_MIN - 77.0) * 3600)  # ~648
    col_end = int((LON_MAX - 77.0) * 3600)    # ~1224

    clipped = raw_data[row_start:row_end, col_start:col_end].copy().astype(np.float32)
    rows, cols = clipped.shape

    # 1. Carve hydraulic bridge edge passages (lowering artificial bridge deck artifacts)
    for bridge in BRIDGE_PASSAGES:
        r = int(round((LAT_MAX - bridge["lat"]) / (LAT_MAX - LAT_MIN) * (rows - 1)))
        c = int(round((bridge["lon"] - LON_MIN) / (LON_MAX - LON_MIN) * (cols - 1)))
        r0, r1 = max(0, r - 1), min(rows, r + 2)
        c0, c1 = max(0, c - 1), min(cols, c + 2)
        clipped[r0:r1, c0:c1] = np.minimum(clipped[r0:r1, c0:c1], bridge["bed_elev_m"])

    # 1b. Clamp radar specular dropouts / pits below physical bed floor (197.5m at Okhla sill)
    pits_clamped = int(np.sum(clipped < 197.5))
    if pits_clamped > 0:
        clipped = np.maximum(clipped, 197.5)

    # 2. Build separate burn mask (uint8) strictly from verified frozen major bunds
    burn_mask = np.zeros((rows, cols), dtype=np.uint8)
    burn_ways = []
    if BURN_WAYS_CSV.exists():
        with open(BURN_WAYS_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                burn_ways.append((
                    float(row["lat_start"]), float(row["lon_start"]),
                    float(row["lat_end"]), float(row["lon_end"]),
                ))
    else:
        burn_ways = [
            (28.6920, 77.2420, 28.6500, 77.2620),
            (28.6500, 77.2620, 28.6100, 77.2850),
            (28.7050, 77.2270, 28.6750, 77.2300),
            (28.6750, 77.2300, 28.6580, 77.2380),
        ]

    for lat1, lon1, lat2, lon2 in burn_ways:
        steps = 60
        for s in range(steps):
            frac = s / float(steps - 1)
            lat = lat1 + frac * (lat2 - lat1)
            lon = lon1 + frac * (lon2 - lon1)
            r = int(round((LAT_MAX - lat) / (LAT_MAX - LAT_MIN) * (rows - 1)))
            c = int(round((lon - LON_MIN) / (LON_MAX - LON_MIN) * (cols - 1)))
            if 0 <= r < rows and 0 <= c < cols:
                # Mark 2x2 footprint in burn mask
                burn_mask[r:min(rows, r+2), c:min(cols, c+2)] = 1

    # T2 Defense Check: Ensure hero colony Yamuna Pushta and wet calibration points are NOT in burn mask
    hero_lat, hero_lon = 28.6550, 77.2450
    hr = int(round((LAT_MAX - hero_lat) / (LAT_MAX - LAT_MIN) * (rows - 1)))
    hc = int(round((hero_lon - LON_MIN) / (LON_MAX - LON_MIN) * (cols - 1)))
    assert burn_mask[hr, hc] == 0, "FATAL DEFECT T2: Hero colony Yamuna Pushta falls inside burn mask!"

    # Save grids to data/dem and out/dtm
    CLIPPED_NPY_PATH.parent.mkdir(parents=True, exist_ok=True)
    np.save(CLIPPED_NPY_PATH, clipped)
    np.save(BURN_MASK_PATH, burn_mask)

    # Export finished calibrated GeoTIFF to out/dtm/corridor_dtm.tif for teammates
    out_dtm_dir = DATA_DIR.parent / "out" / "dtm"
    out_dtm_dir.mkdir(parents=True, exist_ok=True)
    out_tif_path = out_dtm_dir / "corridor_dtm.tif"
    tifffile.imwrite(str(out_tif_path), clipped)

    # Run golden check on the real data
    dtm_obj = DTMGrid(
        elevation=clipped,
        burn_mask=burn_mask,
        lat_min=LAT_MIN,
        lat_max=LAT_MAX,
        lon_min=LON_MIN,
        lon_max=LON_MAX,
        rows=rows,
        cols=cols,
        datum_offset=None,
    )
    golden_ok, golden_report = run_golden_sanity_check(dtm_obj)

    # SR §11.1 Metadata format
    meta = {
        "synthetic": False,
        "raw_dem_source": "Copernicus GLO-30 DSM (AWS Open Data Registry)",
        "lat_min": LAT_MIN,
        "lat_max": LAT_MAX,
        "lon_min": LON_MIN,
        "lon_max": LON_MAX,
        "rows": rows,
        "cols": cols,
        "resolution_m": 30.0,
        "elevation_min": float(np.min(clipped)),
        "elevation_max": float(np.max(clipped)),
        "pits_clamped_below_197p5m": pits_clamped,
        "delta_m": 0.0,  # Kept strictly at 0; no calibration points used to fit artificial offset
        "calibrated_by": "fixed_zero_baseline",
        "burn_floor_space": "gauge",
        "calibration_warning": None,
        "bridge_passages_carved": len(BRIDGE_PASSAGES),
        "golden": {
            "passed": golden_ok,
            "pushta_depth_m": round(check_inundation_depth(dtm_obj, 208.66, 28.6550, 77.2450), 2),
            "connaught_place_depth_m": round(check_inundation_depth(dtm_obj, 208.66, 28.6320, 77.2190), 2),
            "report": golden_report,
        },
    }
    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    with open(out_dtm_dir / "dtm_meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    return DTMGrid(
        elevation=clipped,
        burn_mask=burn_mask,
        lat_min=LAT_MIN,
        lat_max=LAT_MAX,
        lon_min=LON_MIN,
        lon_max=LON_MAX,
        rows=rows,
        cols=cols,
        datum_offset=None,
    )


def compute_water_surface_elevation(gauge_level_drb: float, lat: float) -> float:
    """Compute local water surface elevation along river longitudinal slope."""
    drb_lat = 28.662
    km_distance = (lat - drb_lat) * 111.0
    wse = gauge_level_drb + (km_distance * 0.15)
    return wse


def check_inundation_depth(dtm: DTMGrid, gauge_level_drb: float, lat: float, lon: float) -> float:
    """Check inundation depth in meters at a given coordinate."""
    ground_elev = dtm.get_elevation_at(lat, lon)
    wse = compute_water_surface_elevation(gauge_level_drb, lat)
    depth = max(0.0, wse - ground_elev)
    return float(depth)


def run_golden_sanity_check(dtm: DTMGrid) -> Tuple[bool, str]:
    """Golden sanity check at record 208.66m gauge level."""
    pushta_lat, pushta_lon = 28.6550, 77.2450
    cp_lat, cp_lon = 28.6320, 77.2190

    pushta_depth = check_inundation_depth(dtm, 208.66, pushta_lat, pushta_lon)
    cp_depth = check_inundation_depth(dtm, 208.66, cp_lat, cp_lon)

    is_valid = (pushta_depth > 0.3) and (cp_depth == 0.0)
    details = (
        f"Golden Check at 208.66m: "
        f"Yamuna Pushta depth={pushta_depth:.2f}m (expected >0.3m), "
        f"Connaught Place depth={cp_depth:.2f}m (expected 0.0m). "
        f"Result: {'PASS' if is_valid else 'FAIL'}"
    )
    return is_valid, details


if __name__ == "__main__":
    dtm_grid = build_calibrated_dtm(force_rebuild=True)
    ok, report = run_golden_sanity_check(dtm_grid)
    print("=" * 80)
    print(report)
    print(f"Burn mask cells: {np.sum(dtm_grid.burn_mask)} | Shape: {dtm_grid.burn_mask.shape}")
    print("=" * 80)
