"""Replay builder: precomputes all offline forecasts, depth surfaces, thresholds, and what-if artifacts."""

import sys
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import numpy as np
import pandas as pd

# Add shared/py and ml to sys.path
REPO_ROOT = Path(__file__).resolve().parents[2]
SHARED_PY = REPO_ROOT / "shared" / "py"
if str(SHARED_PY) not in sys.path:
    sys.path.insert(0, str(SHARED_PY))

from jt_shared.constants import DEFAULT_SCENARIO_ID, DEFAULT_HERO_COLONY
from jt_shared.models import DepthIndexEntry
from jt_shared.timeutil import format_iso, parse_iso
from jt_ml.paths import get_out_dir
from jt_ml.data.load import load_drb_anchors, load_hathnikund_releases
from jt_ml.train import train_lagreg_pipeline
from jt_ml.evaluate import evaluate_on_test_split
from jt_ml.model_card import generate_model_registry_and_card
from jt_ml.forecast_run import generate_forecast_nodes
from jt_ml.inundation.grid import make_synthetic_grid
from jt_ml.inundation.onset import compute_onset_raster, compute_cutoff_0p30_raster, depth_at_level
from jt_ml.inundation.surface import export_depth_cog, export_depth_geojson
from jt_ml.inundation.thresholds import compute_colony_thresholds, save_colony_thresholds
from jt_ml.inundation.ladder import build_whatif_ladder
from jt_ml.inundation.edge_cutoffs import compute_edge_cutoffs, save_edge_cutoffs

IST = timezone(timedelta(hours=5, minutes=30))


def run_full_replay(scenario_id: str = DEFAULT_SCENARIO_ID, out_dir: Path = None):
    out_dir = out_dir or get_out_dir()
    print(f"[*] Running full replay for scenario: {scenario_id} into {out_dir}")

    # 1. Train forecasting models & conformal calibrator
    print("[1/6] Training forecasting models...")
    model, calib = train_lagreg_pipeline(out_dir)

    # 2. Evaluate on test split
    print("[2/6] Evaluating on held-out TEST split...")
    metrics = evaluate_on_test_split(model, out_dir)

    # 3. Inundation grid & rasters
    print("[3/6] Setting up corridor grid and computing onset/cutoff rasters...")
    grid = make_synthetic_grid()
    calibration = {
        "delta_m": 0.0,
        "slope_m_per_km": 0.22,
        "balanced_acc": 0.88,
        "n_wet": 15,
        "n_dry": 15,
    }
    zprime = grid.compute_zprime(delta_m=calibration["delta_m"], slope_m_per_km=calibration["slope_m_per_km"])
    onset = compute_onset_raster(zprime, grid.river_mask)
    cutoff = compute_cutoff_0p30_raster(onset, zprime)

    # Save onset and cutoff rasters
    bounds = (float(grid.lons[0]), float(grid.lats[-1]), float(grid.lons[-1]), float(grid.lats[0]))
    models_inundation_dir = out_dir / "models" / "inundation" / "v1"
    models_inundation_dir.mkdir(parents=True, exist_ok=True)
    export_depth_cog(onset, bounds, models_inundation_dir / "onset.tif")
    export_depth_cog(cutoff, bounds, models_inundation_dir / "cutoff_0p30.tif")

    # Save zprime and onset npy for fast Lambda access
    np.save(models_inundation_dir / "zprime.npy", zprime)
    np.save(models_inundation_dir / "onset.npy", onset)

    with open(models_inundation_dir / "calibration.json", "w") as f:
        json.dump(calibration, f, indent=2)

    # Generate Model Card and Registry
    generate_model_registry_and_card(metrics, calibration, out_dir)

    # 4. Colonies thresholds (F6)
    print("[4/6] Computing colony thresholds (Feature F6)...")
    colonies = [
        {"colony_id": "DEL-YP-04", "name": "Yamuna Pushta Sector C", "centroid": [77.245, 28.655]},
        {"colony_id": "DEL-MKT-01", "name": "Majnu ka Tilla", "centroid": [77.230, 28.700]},
        {"colony_id": "DEL-MV-02", "name": "Mayur Vihar Ext Phase 1", "centroid": [77.295, 28.605]},
        {"colony_id": "DEL-CP-01", "name": "Connaught Place", "centroid": [77.218, 28.632]},
    ]
    thresholds = compute_colony_thresholds(colonies, onset, cutoff, grid.lons, grid.lats)
    save_colony_thresholds(thresholds, models_inundation_dir / "colony_thresholds.json")

    # Road edges & cutoffs
    roads_sample = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"edge_id": "osm:101:102:0", "name": "Ring Road ISBT segment"},
                "geometry": {"type": "LineString", "coordinates": [[77.235, 28.665], [77.240, 28.668]]},
            },
            {
                "type": "Feature",
                "properties": {"edge_id": "osm:201:202:0", "name": "Vikas Marg approach"},
                "geometry": {"type": "LineString", "coordinates": [[77.255, 28.630], [77.260, 28.632]]},
            },
        ],
    }
    edge_cutoffs = compute_edge_cutoffs(roads_sample, cutoff, grid.lons, grid.lats)
    save_edge_cutoffs(edge_cutoffs, models_inundation_dir / "edge_cutoffs.json")

    # 5. Build What-If ladder (F1)
    print("[5/6] Building What-If ladder (Feature F1)...")
    build_whatif_ladder(onset, zprime, grid.lons, grid.lats, colonies, edge_cutoffs, out_dir)

    # 6. Generate Replay Steps for Demo Window (July 12 12:00 to July 13 18:00)
    print("[6/6] Generating hourly forecast & flood depth steps...")
    anchors = load_drb_anchors()
    hk_df = load_hathnikund_releases()

    forecast_dir = out_dir / "scenarios" / scenario_id / "forecasts"
    depth_dir = out_dir / "scenarios" / scenario_id / "depth"
    forecast_dir.mkdir(parents=True, exist_ok=True)
    depth_dir.mkdir(parents=True, exist_ok=True)

    # Key demo timestamps
    demo_timestamps = [
        datetime(2023, 7, 12, 12, 0, tzinfo=IST),
        datetime(2023, 7, 12, 18, 0, tzinfo=IST),
        datetime(2023, 7, 13, 0, 0, tzinfo=IST), # Golden step
        datetime(2023, 7, 13, 6, 0, tzinfo=IST),
        datetime(2023, 7, 13, 10, 0, tzinfo=IST),
        datetime(2023, 7, 13, 18, 0, tzinfo=IST), # Peak
    ]

    index_entries = []
    for dt in demo_timestamps:
        ts_str = format_iso(dt)
        safe_name = ts_str.replace(":", "_")

        # 6a. Forecast nodes
        fn_list = generate_forecast_nodes(scenario_id, dt, anchors, hk_df, model, calib)
        fn_path = forecast_dir / f"{safe_name}.json"
        with open(fn_path, "w") as f:
            json.dump([fn.model_dump() for fn in fn_list], f, indent=2)

        # 6b. Depth surface
        # Find closest observed level
        obs_matches = anchors[anchors["timestamp"] <= pd.to_datetime(dt)]
        ref_level = float(obs_matches["level_m"].iloc[-1]) if not obs_matches.empty else 206.0

        depth = depth_at_level(onset, zprime, ref_level)
        tif_p = depth_dir / f"{safe_name}.tif"
        geojson_p = depth_dir / f"{safe_name}.geojson"

        export_depth_cog(depth, bounds, tif_p)
        export_depth_geojson(depth, grid.lons, grid.lats, geojson_p)

        index_entries.append(
            DepthIndexEntry(
                valid_at=ts_str,
                tif=f"/scenarios/{scenario_id}/depth/{safe_name}.tif",
                geojson=f"/scenarios/{scenario_id}/depth/{safe_name}.geojson",
                level_m_ref=round(ref_level, 2),
            ).model_dump()
        )

    with open(depth_dir / "index.json", "w") as f:
        json.dump(index_entries, f, indent=2)

    print("[*] Replay build complete successfully!")


if __name__ == "__main__":
    run_full_replay()
