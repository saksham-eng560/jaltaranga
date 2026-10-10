import json
import importlib.util
from pathlib import Path
from jt_ml.paths import get_out_dir, ML_DIR

# Dynamically import handler because 'lambda' is a reserved python keyword
handler_path = ML_DIR / "lambda" / "forecast_fn" / "handler.py"
spec = importlib.util.spec_from_file_location("forecast_fn_handler", str(handler_path))
handler_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(handler_mod)
handler = handler_mod.handler


def test_lambda_models_card(monkeypatch):
    out_dir = get_out_dir()
    monkeypatch.setenv("JT_DATA_DIR", str(out_dir))

    event = {
        "rawPath": "/models/card",
        "requestContext": {"http": {"method": "GET"}},
    }
    resp = handler(event, None)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["champion"] == "lagreg-v1"


def test_lambda_whatif(monkeypatch):
    out_dir = get_out_dir()
    monkeypatch.setenv("JT_DATA_DIR", str(out_dir))

    event = {
        "rawPath": "/scenarios/yamuna-2023-07/whatif",
        "requestContext": {"http": {"method": "GET"}},
        "queryStringParameters": {"level_m": "208.6"},
    }
    resp = handler(event, None)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["level_m"] == 208.6
    assert len(body["wet_colonies"]) > 0


def test_lambda_flood(monkeypatch):
    out_dir = get_out_dir()
    monkeypatch.setenv("JT_DATA_DIR", str(out_dir))

    event = {
        "rawPath": "/scenarios/yamuna-2023-07/flood",
        "requestContext": {"http": {"method": "GET"}},
        "queryStringParameters": {"at": "2023-07-13T00:00:00+05:30"},
    }
    resp = handler(event, None)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert "tif_url" in body
    assert "geojson_url" in body
