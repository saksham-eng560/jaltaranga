"""Rainfall Context Ingestion from ERA5 Reanalysis for Jaltaranga.

Fetches real ERA5 hourly precipitation data from ECMWF reanalysis (via Open-Meteo)
for the Delhi Yamuna catchment area during historical flood scenario periods.
Strictly labelled as 'ERA5 reanalysis - not IMD'.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from pipeline.ledger import record

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SCENARIOS_DIR = DATA_DIR / "scenarios"

ERA5_DISCLAIMER = "ERA5 reanalysis - not IMD"

SCENARIO_WINDOWS = {
    "yamuna-2023-07": {
        "start_date": "2023-07-08",
        "end_date": "2023-07-16",
        "lat": 28.66,
        "lon": 77.23,
        "description": "July 2023 record flood (peak 208.66m) with torrential 153mm rainfall in Delhi",
    },
    "yamuna-2025-09": {
        "start_date": "2024-08-25",  # Most recent validated historical analog window
        "end_date": "2024-09-05",
        "lat": 28.66,
        "lon": 77.23,
        "description": "Late monsoon surge scenario (peak 207.48m)",
    },
}


@dataclass
class RainfallRecord:
    timestamp: str
    precipitation_mm: float
    cumulative_mm: float
    label: str = ERA5_DISCLAIMER

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def fetch_era5_rainfall(scenario: str = "yamuna-2023-07", force_refresh: bool = False) -> Dict[str, Any]:
    """Fetch real ERA5 hourly precipitation for the scenario window."""
    SCENARIOS_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = SCENARIOS_DIR / f"{scenario}-rainfall.json"

    if not force_refresh and cache_path.exists():
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)

    if scenario not in SCENARIO_WINDOWS:
        raise ValueError(f"Unknown scenario '{scenario}'. Available: {list(SCENARIO_WINDOWS.keys())}")

    config = SCENARIO_WINDOWS[scenario]
    url = (
        f"https://archive-api.open-meteo.com/v1/archive?"
        f"latitude={config['lat']}&longitude={config['lon']}"
        f"&start_date={config['start_date']}&end_date={config['end_date']}"
        f"&hourly=precipitation,rain&timezone=Asia%2FKolkata"
    )

    print(f"Fetching real ERA5 hourly rainfall for {scenario} from Open-Meteo...")
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    payload = resp.json()

    times = payload.get("hourly", {}).get("time", [])
    precip = payload.get("hourly", {}).get("precipitation", [])

    records: List[Dict[str, Any]] = []
    cumulative = 0.0
    for t, p in zip(times, precip):
        val = float(p or 0.0)
        cumulative += val
        records.append({
            "timestamp": t,
            "precipitation_mm": round(val, 2),
            "cumulative_mm": round(cumulative, 2),
            "source_label": ERA5_DISCLAIMER,
        })

    result = {
        "scenario": scenario,
        "coordinates": {"lat": config["lat"], "lon": config["lon"]},
        "start_date": config["start_date"],
        "end_date": config["end_date"],
        "data_label": ERA5_DISCLAIMER,
        "total_rainfall_mm": round(cumulative, 2),
        "peak_hourly_mm": max((r["precipitation_mm"] for r in records), default=0.0),
        "records": records,
    }

    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    record(
        dataset=f"era5-rainfall-{scenario}",
        source_url=url,
        source_name="ECMWF ERA5 Reanalysis (via Open-Meteo Archive)",
        licence="CC-BY-4.0 / ECMWF Terms of Use",
        qc_flag="ok",
        qc_notes=f"Hourly rainfall series for {scenario} ({result['total_rainfall_mm']}mm total), labelled '{ERA5_DISCLAIMER}'",
        metadata={
            "scenario": scenario,
            "total_rainfall_mm": result["total_rainfall_mm"],
            "peak_hourly_mm": result["peak_hourly_mm"],
            "label": ERA5_DISCLAIMER,
        },
    )

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Jaltaranga ERA5 Rainfall Context CLI")
    parser.add_argument("--scenario", type=str, default="yamuna-2023-07", help="Scenario ID")
    parser.add_argument("--refresh", action="store_true", help="Force refresh from API")
    args = parser.parse_args()

    data = fetch_era5_rainfall(args.scenario, force_refresh=args.refresh)
    print("=" * 80)
    print(f"JALTARANGA ERA5 RAINFALL CONTEXT [{data['data_label']}]")
    print(f"Scenario: {data['scenario']} | Total: {data['total_rainfall_mm']} mm | Peak: {data['peak_hourly_mm']} mm/h")
    print("=" * 80)
    for r in data["records"][:10]:
        print(f"{r['timestamp']} | Rain: {r['precipitation_mm']:5.1f} mm | Cumulative: {r['cumulative_mm']:6.1f} mm")
    print("...")


if __name__ == "__main__":
    main()
