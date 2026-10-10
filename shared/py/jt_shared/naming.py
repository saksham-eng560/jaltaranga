"""jt_shared S3 naming helpers."""

import urllib.parse


def forecast_key(scenario_id: str, issued_at: str) -> str:
    safe_ts = urllib.parse.quote(issued_at, safe="")
    return f"scenarios/{scenario_id}/forecasts/{safe_ts}.json"


def depth_tif_key(scenario_id: str, valid_at: str) -> str:
    safe_ts = urllib.parse.quote(valid_at, safe="")
    return f"scenarios/{scenario_id}/depth/{safe_ts}.tif"


def depth_geojson_key(scenario_id: str, valid_at: str) -> str:
    safe_ts = urllib.parse.quote(valid_at, safe="")
    return f"scenarios/{scenario_id}/depth/{safe_ts}.geojson"


def depth_index_key(scenario_id: str) -> str:
    return f"scenarios/{scenario_id}/depth/index.json"


def ladder_geojson_key(level_m: float) -> str:
    return f"models/inundation/v1/ladder/{level_m:.1f}.geojson"


def whatif_json_key(level_m: float) -> str:
    return f"models/inundation/v1/whatif/{level_m:.1f}.json"
