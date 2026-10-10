"""AWS Lambda handler for the read-only Jaltaranga ML API."""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path, PurePosixPath
from typing import Any

LOGGER = logging.getLogger(__name__)
SCENARIO_ID = "yamuna-2023-07"
DEFAULT_FORECAST_AT = "2023-07-13T00:00:00+05:30"
PRESIGNED_URL_TTL_SECONDS = 900
SCENARIO_ROUTE = re.compile(r"/scenarios/([^/]+)/(forecast|flood|whatif)\Z")


def _get_s3_client() -> Any:
    """Create an S3 client lazily so local runs need no AWS SDK or credentials."""
    import boto3

    return boto3.client("s3")


def _is_not_found_error(error: Exception) -> bool:
    response = getattr(error, "response", {})
    error_response = response.get("Error", {}) if isinstance(response, dict) else {}
    code = error_response.get("Code")
    status = response.get("ResponseMetadata", {}).get("HTTPStatusCode") if isinstance(response, dict) else None
    return code in {"NoSuchKey", "NotFound", "404"} or status == 404


class ArtifactStore:
    """Read local demo artifacts or their published S3 copies."""

    def __init__(self) -> None:
        local_dir = os.environ.get("JT_DATA_DIR")
        self.local_root = Path(local_dir).resolve() if local_dir else Path("/var/task").resolve()
        self.bucket = os.environ.get("JT_DATA_BUCKET") if not local_dir else None
        self.s3 = _get_s3_client() if self.bucket else None

    @property
    def is_s3(self) -> bool:
        return self.bucket is not None

    def read_bytes(self, key: str) -> bytes | None:
        normalized_key = _normalize_key(key)
        if not self.bucket:
            path = (self.local_root / PurePosixPath(normalized_key)).resolve()
            if not path.is_relative_to(self.local_root):
                return None
            try:
                return path.read_bytes()
            except FileNotFoundError:
                return None

        try:
            response = self.s3.get_object(Bucket=self.bucket, Key=normalized_key)
        except Exception as error:
            if _is_not_found_error(error):
                return None
            raise

        body = response["Body"]
        try:
            return body.read()
        finally:
            body.close()

    def list_keys(self, prefix: str) -> list[str]:
        normalized_prefix = _normalize_key(prefix).rstrip("/") + "/"
        if not self.bucket:
            directory = (self.local_root / PurePosixPath(normalized_prefix)).resolve()
            if not directory.is_relative_to(self.local_root):
                return []
            if not directory.is_dir():
                return []
            return [
                path.relative_to(self.local_root).as_posix()
                for path in directory.glob("*.json")
                if path.is_file()
            ]

        paginator = self.s3.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=self.bucket, Prefix=normalized_prefix)
        keys = []
        for page in pages:
            keys.extend(
                item["Key"]
                for item in page.get("Contents", [])
                if item.get("Key", "").startswith(normalized_prefix)
            )
        return keys

    def presign_get(self, key: str) -> str:
        if not self.bucket:
            return "/" + _normalize_key(key)
        return self.s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": _normalize_key(key)},
            ExpiresIn=PRESIGNED_URL_TTL_SECONDS,
        )


def _normalize_key(key: str) -> str:
    """Normalize artifact keys and reject parent traversal."""
    path = PurePosixPath(str(key).lstrip("/"))
    normalized = path.as_posix()
    if normalized in {"", "."} or ".." in path.parts:
        raise ValueError("Invalid artifact key")
    return normalized


def _parse_timestamp(value: str) -> datetime | None:
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        return None
    return timestamp


def _format_timestamp(timestamp: datetime) -> str:
    return timestamp.isoformat(timespec="seconds")


def _timestamp_from_forecast_key(key: str) -> datetime | None:
    if not key.endswith(".json"):
        return None
    stem = PurePosixPath(key).stem
    # Filenames encode the time separators and UTC-offset separator as underscores.
    return _parse_timestamp(stem.replace("_", ":"))


def _response(status_code: int, body: str | dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    serialized_body = body if isinstance(body, str) else json.dumps(body, separators=(",", ":"))
    return {"statusCode": status_code, "headers": headers, "body": serialized_body}


def _handle_models_card(store: ArtifactStore, headers: dict[str, str]) -> dict[str, Any]:
    content = store.read_bytes("models/registry.json")
    if content is None:
        return _response(404, {"error": "Model card not found"}, headers)
    return _response(200, content.decode("utf-8"), headers)


def _handle_whatif(
    store: ArtifactStore,
    query: dict[str, str],
    headers: dict[str, str],
) -> dict[str, Any]:
    raw_level = query.get("level_m", "207.0")
    try:
        level = Decimal(raw_level)
        if not level.is_finite():
            raise InvalidOperation
        level = level.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        return _response(400, {"error": "level_m must be a finite number"}, headers)

    level_text = f"{level:.1f}"
    key = f"models/inundation/v1/whatif/{level_text}.json"
    content = store.read_bytes(key)
    if content is None:
        return _response(404, {"error": f"Level {level_text} out of range"}, headers)

    if store.is_s3:
        body = json.loads(content)
        ladder_key = f"models/inundation/v1/ladder/{level_text}.geojson"
        if store.read_bytes(ladder_key) is None:
            return _response(404, {"error": f"Flood map for level {level_text} not found"}, headers)
        body["flood_geojson_url"] = store.presign_get(ladder_key)
        return _response(200, body, headers)
    return _response(200, content.decode("utf-8"), headers)


def _handle_forecast(
    store: ArtifactStore,
    requested_at: str,
    headers: dict[str, str],
) -> dict[str, Any]:
    timestamp = _parse_timestamp(requested_at)
    if timestamp is None:
        return _response(400, {"error": "at must be an ISO-8601 timestamp with a timezone"}, headers)

    prefix = f"scenarios/{SCENARIO_ID}/forecasts/"
    candidates = []
    for key in store.list_keys(prefix):
        if not key.startswith(prefix) or PurePosixPath(key).parent.as_posix() != prefix.rstrip("/"):
            continue
        issue_time = _timestamp_from_forecast_key(key)
        if issue_time is not None and issue_time <= timestamp:
            candidates.append((issue_time, key))

    if not candidates:
        return _response(404, {"error": "No forecast was issued at or before the requested time"}, headers)

    _, key = max(candidates, key=lambda candidate: candidate[0])
    content = store.read_bytes(key)
    if content is None:
        return _response(404, {"error": "Forecast step not found"}, headers)
    return _response(200, content.decode("utf-8"), headers)


def _safe_depth_key(value: Any, scenario_id: str) -> str | None:
    if not isinstance(value, str):
        return None
    key = _normalize_key(value)
    expected_prefix = f"scenarios/{scenario_id}/depth/"
    if not key.startswith(expected_prefix) or PurePosixPath(key).name in {"", ".", ".."}:
        return None
    return key


def _handle_flood(
    store: ArtifactStore,
    scenario_id: str,
    requested_at: str,
    headers: dict[str, str],
) -> dict[str, Any]:
    timestamp = _parse_timestamp(requested_at)
    if timestamp is None:
        return _response(400, {"error": "at must be an ISO-8601 timestamp with a timezone"}, headers)

    index_key = f"scenarios/{scenario_id}/depth/index.json"
    index_content = store.read_bytes(index_key)
    if index_content is None:
        return _response(404, {"error": "Flood depth index not found"}, headers)
    index = json.loads(index_content)
    if not isinstance(index, list):
        raise ValueError("Flood depth index must be a list")

    match = next(
        (
            item
            for item in index
            if isinstance(item, dict)
            and _parse_timestamp(item.get("valid_at", "")) == timestamp
        ),
        None,
    )
    if match is None:
        return _response(404, {"error": "Flood depth step not found"}, headers)

    tif_key = _safe_depth_key(match.get("tif"), scenario_id)
    geojson_key = _safe_depth_key(match.get("geojson"), scenario_id)
    if tif_key is None or geojson_key is None:
        raise ValueError("Flood depth index contains an invalid artifact key")

    return _response(
        200,
        {
            "valid_at": _format_timestamp(timestamp),
            "tif_url": store.presign_get(tif_key),
            "geojson_url": store.presign_get(geojson_key),
            "level_m_ref": match.get("level_m_ref"),
        },
        headers,
    )


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle GET /models/card and the scenario forecast/flood/whatif routes."""
    raw_path = event.get("rawPath", event.get("path", "/"))
    method = event.get("requestContext", {}).get("http", {}).get("method", event.get("httpMethod", "GET"))
    query = event.get("queryStringParameters") or {}
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": os.environ.get("JT_CORS_ORIGIN", "*"),
        "Access-Control-Allow-Methods": "GET, OPTIONS",
    }

    if method == "OPTIONS":
        return _response(200, "", headers)
    if method != "GET":
        return _response(405, {"error": "Method not allowed"}, {**headers, "Allow": "GET, OPTIONS"})

    try:
        store = ArtifactStore()
        if raw_path.rstrip("/") == "/models/card":
            return _handle_models_card(store, headers)

        route_match = SCENARIO_ROUTE.fullmatch(raw_path.rstrip("/"))
        if route_match is None:
            return _response(404, {"error": "Not found"}, headers)

        scenario_id, action = route_match.groups()
        if scenario_id != SCENARIO_ID:
            return _response(404, {"error": "Scenario not found"}, headers)

        if action == "whatif":
            return _handle_whatif(store, query, headers)
        if action == "forecast":
            return _handle_forecast(store, query.get("at", DEFAULT_FORECAST_AT), headers)
        if action == "flood":
            return _handle_flood(store, scenario_id, query.get("at", DEFAULT_FORECAST_AT), headers)
    except Exception:
        LOGGER.exception("ML artifact request failed")
        return _response(503, {"error": "ML artifacts are temporarily unavailable"}, headers)

    return _response(404, {"error": "Not found"}, headers)
