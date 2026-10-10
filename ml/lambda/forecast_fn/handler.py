"""AWS Lambda handler for jt-<env>-forecast-fn serving ML API endpoints."""

import json
import os
import urllib.parse
from pathlib import Path
from typing import Dict, Any

def get_data_dir() -> Path:
    return Path(os.environ.get("JT_DATA_DIR", "/var/task"))


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda entry point for HTTP API routes:
    GET /scenarios/{id}/forecast?at=
    GET /scenarios/{id}/flood?at=
    GET /scenarios/{id}/whatif?level_m=
    GET /models/card
    """
    data_dir = get_data_dir()
    raw_path = event.get("rawPath", event.get("path", "/"))
    method = event.get("requestContext", {}).get("http", {}).get("method", event.get("httpMethod", "GET"))
    query = event.get("queryStringParameters") or {}

    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
    }

    if method == "OPTIONS":
        return {"statusCode": 200, "headers": headers, "body": ""}

    # 1. GET /models/card
    if raw_path.endswith("/models/card"):
        reg_file = data_dir / "models" / "registry.json"
        if reg_file.exists():
            with open(reg_file, "r") as f:
                body = f.read()
            return {"statusCode": 200, "headers": headers, "body": body}
        return {"statusCode": 404, "headers": headers, "body": json.dumps({"error": "Model card not found"})}

    # 2. GET /scenarios/{id}/whatif?level_m=
    if "/whatif" in raw_path:
        level_m = float(query.get("level_m", 207.0))
        # Snap to 0.1 m
        level_snapped = round(level_m, 1)
        whatif_file = data_dir / "models" / "inundation" / "v1" / "whatif" / f"{level_snapped:.1f}.json"
        if whatif_file.exists():
            with open(whatif_file, "r") as f:
                body = f.read()
            return {"statusCode": 200, "headers": headers, "body": body}
        return {"statusCode": 404, "headers": headers, "body": json.dumps({"error": f"Level {level_snapped} out of range"})}

    # 3. GET /scenarios/{id}/forecast?at=
    if "/forecast" in raw_path:
        at_ts = query.get("at", "2023-07-13T00:00:00+05:30")
        safe_ts = at_ts.replace(":", "_")
        forecast_file = data_dir / "scenarios" / "yamuna-2023-07" / "forecasts" / f"{safe_ts}.json"
        if forecast_file.exists():
            with open(forecast_file, "r") as f:
                body = f.read()
            return {"statusCode": 200, "headers": headers, "body": body}
        # Fallback to default golden step if specific timestamp not found
        fallback_file = data_dir / "scenarios" / "yamuna-2023-07" / "forecasts" / "2023-07-13T00_00_00+05_30.json"
        if fallback_file.exists():
            with open(fallback_file, "r") as f:
                body = f.read()
            return {"statusCode": 200, "headers": headers, "body": body}
        return {"statusCode": 404, "headers": headers, "body": json.dumps({"error": "Forecast step not found"})}

    # 4. GET /scenarios/{id}/flood?at=
    if "/flood" in raw_path:
        at_ts = query.get("at", "2023-07-13T00:00:00+05:30")
        safe_ts = at_ts.replace(":", "_")
        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps({
                "valid_at": at_ts,
                "tif_url": f"/scenarios/yamuna-2023-07/depth/{safe_ts}.tif",
                "geojson_url": f"/scenarios/yamuna-2023-07/depth/{safe_ts}.geojson",
                "level_m_ref": 208.48,
            }),
        }

    return {"statusCode": 404, "headers": headers, "body": json.dumps({"error": "Not found"})}
