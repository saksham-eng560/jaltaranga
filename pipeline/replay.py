"""Scenario Replay Engine and CLI for Jaltaranga.

Simulates and plays back historical or counterfactual Yamuna flood events
(e.g., yamuna-2023-07, yamuna-2025-09), synchronizing river gauge levels,
concurrent ERA5 hourly rainfall context ('ERA5 reanalysis - not IMD'),
dynamic DTM water surfaces, and critical infrastructure exposure.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from pipeline.dtm import DTMGrid, build_calibrated_dtm, compute_water_surface_elevation
from pipeline.exposure import ExposedInfrastructure, compute_infrastructure_exposure
from pipeline.ledger import record
from pipeline.rainfall import ERA5_DISCLAIMER, fetch_era5_rainfall

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SCENARIOS_DIR = DATA_DIR / "scenarios"

# Key floodplain localities and their threshold elevations
DELHI_FLOODPLAIN_COLONIES = [
    {"name": "Yamuna Pushta (Bela Ghat)", "lat": 28.655, "lon": 77.245, "ground_m": 205.80, "evac_threshold_m": 205.50},
    {"name": "Monastery Market / ISBT Lowlands", "lat": 28.670, "lon": 77.230, "ground_m": 206.80, "evac_threshold_m": 206.50},
    {"name": "Usmanpur Floodplain Basti", "lat": 28.685, "lon": 77.252, "ground_m": 206.40, "evac_threshold_m": 206.00},
    {"name": "Majnu Ka Tila Tibetan Settlement", "lat": 28.700, "lon": 77.228, "ground_m": 207.20, "evac_threshold_m": 206.90},
    {"name": "Geeta Colony Khadar", "lat": 28.648, "lon": 77.260, "ground_m": 206.60, "evac_threshold_m": 206.20},
    {"name": "WHO Building / Drain 12 Regulator", "lat": 28.627, "lon": 77.248, "ground_m": 207.90, "evac_threshold_m": 208.00},
]


@dataclass
class ReplayStepResult:
    step_index: int
    timestamp: str
    gauge_drb_m: float
    hathnikund_cusecs: int
    delta_danger_m: float
    status: str
    rainfall_hourly_mm: float
    rainfall_cumulative_mm: float
    rainfall_source: str
    inundated_facilities: List[Dict[str, Any]]
    affected_colonies: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def load_scenario(scenario_id: str) -> Dict[str, Any]:
    """Load scenario definition JSON file."""
    path = SCENARIOS_DIR / f"{scenario_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Scenario file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def replay_scenario(
    scenario_id: str = "yamuna-2023-07",
    step_filter: Optional[int] = None,
    verbose: bool = True,
) -> Dict[str, Any]:
    """Execute complete scenario playback."""
    scenario = load_scenario(scenario_id)
    timesteps = scenario.get("timesteps", [])
    if not timesteps:
        raise ValueError(f"Scenario {scenario_id} contains no timesteps.")

    # Load terrain and infrastructure
    dtm = build_calibrated_dtm()
    facilities = compute_infrastructure_exposure(dtm=dtm)

    # Fetch real ERA5 rainfall context
    rainfall_data = fetch_era5_rainfall(scenario_id)
    rain_lookup = {
        r["timestamp"][:13]: r  # Match by YYYY-MM-DDTHH
        for r in rainfall_data.get("records", [])
    }

    danger_level = scenario.get("danger_level_m", 205.33)
    results: List[ReplayStepResult] = []

    if verbose:
        print("=" * 90)
        print(f"JALTARANGA FLOOD REPLAY: {scenario['name'].upper()}")
        print(f"Scenario: {scenario_id} | Gauge: {scenario['gauge_station']}")
        print(f"Danger Mark: {danger_level:.2f} m | Peak: {scenario.get('peak_level_m', 0.0):.2f} m")
        print(f"Rainfall Context: {ERA5_DISCLAIMER}")
        print("=" * 90)

    for idx, ts in enumerate(timesteps):
        if step_filter is not None and idx != step_filter:
            continue

        timestamp = ts["timestamp"]
        gauge_drb = float(ts["gauge_level_drb_m"])
        cusecs = int(ts.get("hathnikund_cusecs", 0))
        delta_danger = round(gauge_drb - danger_level, 2)
        status = ts.get("status", "ACTIVE")

        # Match rainfall
        hour_key = timestamp[:13]
        rain_rec = rain_lookup.get(hour_key, {"precipitation_mm": 0.0, "cumulative_mm": 0.0})
        rain_hourly = rain_rec.get("precipitation_mm", 0.0)
        rain_cum = rain_rec.get("cumulative_mm", 0.0)

        # Check submerged facilities at this exact water level
        inundated: List[Dict[str, Any]] = []
        for fac in facilities:
            wse = compute_water_surface_elevation(gauge_drb, fac.lat)
            depth = max(0.0, wse - fac.ground_elevation_m)
            if depth >= 0.10:  # 10 cm water threshold for facility alert
                inundated.append({
                    "id": fac.id,
                    "name": fac.name,
                    "category": fac.category,
                    "depth_m": round(depth, 2),
                    "criticality": fac.criticality,
                })

        # Check affected colonies
        affected_colonies: List[str] = []
        for col in DELHI_FLOODPLAIN_COLONIES:
            wse_col = compute_water_surface_elevation(gauge_drb, col["lat"])
            if wse_col >= col["evac_threshold_m"]:
                affected_colonies.append(col["name"])

        step_res = ReplayStepResult(
            step_index=idx,
            timestamp=timestamp,
            gauge_drb_m=gauge_drb,
            hathnikund_cusecs=cusecs,
            delta_danger_m=delta_danger,
            status=status,
            rainfall_hourly_mm=rain_hourly,
            rainfall_cumulative_mm=rain_cum,
            rainfall_source=ERA5_DISCLAIMER,
            inundated_facilities=inundated,
            affected_colonies=affected_colonies,
        )
        results.append(step_res)

        if verbose:
            danger_flag = f"[+{delta_danger:+.2f}m ABOVE DANGER]" if delta_danger > 0 else f"[{delta_danger:+.2f}m below]"
            print(f"\n[Step {idx:02d} | {timestamp}] Level: {gauge_drb:6.2f}m {danger_flag:24s} | Discharge: {cusecs:6d} cfs")
            print(f"  Rainfall ({ERA5_DISCLAIMER}): {rain_hourly:4.1f} mm/h (Accum: {rain_cum:5.1f} mm) | Status: {status}")
            if affected_colonies:
                print(f"  Flooded Localities ({len(affected_colonies)}): {', '.join(affected_colonies)}")
            if inundated:
                top_facs = [f"{f['name']} ({f['depth_m']}m)" for f in inundated[:3]]
                print(f"  Submerged Facilities ({len(inundated)}): {', '.join(top_facs)}{'...' if len(inundated) > 3 else ''}")
            else:
                print(f"  Submerged Facilities: None (dry corridor)")

    summary = {
        "scenario_id": scenario_id,
        "name": scenario["name"],
        "total_timesteps": len(timesteps),
        "steps_evaluated": len(results),
        "danger_mark_m": danger_level,
        "all_time_peak_m": scenario.get("peak_level_m"),
        "hero_timestamp": scenario.get("hero_timestamp"),
        "rainfall_disclaimer": ERA5_DISCLAIMER,
        "steps": [r.to_dict() for r in results],
    }

    # Save summary
    out_file = SCENARIOS_DIR / f"{scenario_id}_replay_summary.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    record(
        dataset=f"replay-{scenario_id}",
        source_url=f"local://data/scenarios/{scenario_id}_replay_summary.json",
        source_name=f"Jaltaranga Scenario Replay ({scenario_id})",
        licence="Government Open Data Licence & Copernicus Open Access",
        qc_flag="suspect",
        qc_notes=f"Replay output of {len(results)} timesteps against uncalibrated DTM (delta = 0, radar surface model, includes buildings/trees)",
        metadata={
            "scenario": scenario_id,
            "max_inundated_facilities": max((len(r.inundated_facilities) for r in results), default=0),
            "hero_timestamp": scenario.get("hero_timestamp"),
        },
    )

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Jaltaranga Yamuna Flood Replay CLI")
    parser.add_argument("--scenario", type=str, default="yamuna-2023-07", help="Scenario ID (default: yamuna-2023-07)")
    parser.add_argument("--step", type=int, default=None, help="Evaluate a single step index")
    parser.add_argument("--json", action="store_true", help="Output summary JSON directly to stdout")
    args = parser.parse_args()

    summary = replay_scenario(
        scenario_id=args.scenario,
        step_filter=args.step,
        verbose=not args.json,
    )

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print("\n" + "=" * 90)
        print(f"Replay complete. Summary saved to data/scenarios/{args.scenario}_replay_summary.json")
        print("=" * 90)


if __name__ == "__main__":
    main()
