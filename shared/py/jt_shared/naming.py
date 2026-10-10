"""AWS resource names (§4) and S3 keys (§6, §11.2, §11.8-10)."""

from __future__ import annotations

from datetime import datetime
from urllib.parse import quote

from .timeutil import iso


def resource_name(component: str, resource: str, env: str = "demo") -> str:
    if env not in ("dev", "demo"):
        raise ValueError(f"env must be dev|demo, got {env!r}")
    return f"jt-{env}-{component}-{resource}"


def _ts(value: str | datetime) -> str:
    return iso(value) if isinstance(value, datetime) else value


_KEYS = {
    "graphml": "static/osm/corridor_roads.graphml",
    "roads_geojson": "static/osm/roads.geojson",
    "edge_cutoffs": "static/osm/edge_cutoffs.json",
    "colonies": "static/colonies.geojson",
    "shelters": "static/shelters.geojson",
    "onset": "models/inundation/v1/onset.tif",
    "cutoff_raster": "models/inundation/v1/cutoff_0p30.tif",
    "colony_thresholds": "models/inundation/v1/colony_thresholds.json",
    "manifest": "scenarios/{scenario_id}/manifest.json",
    "gauges": "scenarios/{scenario_id}/gauges.json",
    "forecasts": "scenarios/{scenario_id}/forecasts/{issued_at}.json",
    "depth_tif": "scenarios/{scenario_id}/depth/{valid_at}.tif",
    "depth_geojson": "scenarios/{scenario_id}/depth/{valid_at}.geojson",
    "depth_index": "scenarios/{scenario_id}/depth/index.json",
    "roads": "scenarios/{scenario_id}/roads/{valid_at}.json",
    "plans": "scenarios/{scenario_id}/plans/{valid_at}.json",
    "unreachable": "scenarios/{scenario_id}/plans/{valid_at}.unreachable.json",
    "candidates": "scenarios/{scenario_id}/plans/{valid_at}.candidates.json",
    "trap_summary": "scenarios/{scenario_id}/routing/trap_summary.json",
    "hero": "scenarios/{scenario_id}/routing/hero.json",
    "dispatch_cache": "scenarios/{scenario_id}/dispatch_cache/{valid_at}/{colony_id}.json",
    "audio": "audio/{sha256}.mp3",
    "report_upload": "uploads/reports/{report_id}.jpg",
}


def s3_key(kind: str, **parts: str | datetime) -> str:
    try:
        template = _KEYS[kind]
    except KeyError as exc:
        raise KeyError(f"unknown s3 key kind {kind!r}") from exc
    return template.format(**{k: _ts(v) for k, v in parts.items()})


def url_key(key: str) -> str:
    """Encode a key for an HTTP path (`+05:30` → `%2B05%3A30`), keeping '/'."""
    return quote(key, safe="/")


# Helpers used by the ml/ workstream. Keys keep the raw timestamp (same as s3_key); use url_key for HTTP paths.
def forecast_key(scenario_id: str, issued_at: str | datetime) -> str:
    return s3_key("forecasts", scenario_id=scenario_id, issued_at=issued_at)


def depth_tif_key(scenario_id: str, valid_at: str | datetime) -> str:
    return s3_key("depth_tif", scenario_id=scenario_id, valid_at=valid_at)


def depth_geojson_key(scenario_id: str, valid_at: str | datetime) -> str:
    return s3_key("depth_geojson", scenario_id=scenario_id, valid_at=valid_at)


def depth_index_key(scenario_id: str) -> str:
    return s3_key("depth_index", scenario_id=scenario_id)


def ladder_geojson_key(level_m: float) -> str:
    return f"models/inundation/v1/ladder/{level_m:.1f}.geojson"


def whatif_json_key(level_m: float) -> str:
    return f"models/inundation/v1/whatif/{level_m:.1f}.json"
