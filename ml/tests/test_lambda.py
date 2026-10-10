import json
import importlib.util
import io
from types import SimpleNamespace

from botocore.exceptions import ClientError

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


class FakeS3Client:
    """In-memory S3 client that keeps integration tests offline."""

    def __init__(self, objects):
        self.objects = objects
        self.get_object_calls = []
        self.list_objects_calls = []
        self.presigned_calls = []
        self.exceptions = SimpleNamespace(NoSuchKey=FakeNoSuchKey)

    def get_object(self, *, Bucket, Key):
        self.get_object_calls.append((Bucket, Key))
        if Key not in self.objects:
            raise FakeNoSuchKey()
        return {"Body": io.BytesIO(self.objects[Key].encode("utf-8"))}

    def get_paginator(self, operation):
        assert operation == "list_objects_v2"
        return self

    def paginate(self, *, Bucket, Prefix):
        self.list_objects_calls.append((Bucket, Prefix))
        yield {"Contents": [{"Key": key} for key in sorted(self.objects) if key.startswith(Prefix)]}

    def generate_presigned_url(self, ClientMethod, *, Params, ExpiresIn):
        self.presigned_calls.append((ClientMethod, Params, ExpiresIn))
        return f"https://s3.example.test/{Params['Key']}?expires={ExpiresIn}"


class FakeNoSuchKey(ClientError):
    def __init__(self):
        super().__init__({"Error": {"Code": "NoSuchKey", "Message": "Not found"}}, "GetObject")


def _api_event(path, query=None):
    return {
        "rawPath": path,
        "requestContext": {"http": {"method": "GET"}},
        "queryStringParameters": query or {},
    }


def _fake_s3(monkeypatch, objects):
    client = FakeS3Client(objects)
    monkeypatch.setenv("JT_DATA_BUCKET", "jaltaranga-test-artifacts")
    monkeypatch.delenv("JT_DATA_DIR", raising=False)
    monkeypatch.setattr(handler_mod, "_get_s3_client", lambda: client)
    return client


def test_lambda_s3_reads_model_and_latest_forecast_not_after_requested_time(monkeypatch):
    selected_at = "2023-07-13T10:00:00+05:30"
    selected_key = "scenarios/yamuna-2023-07/forecasts/2023-07-13T10_00_00+05_30.json"
    client = _fake_s3(
        monkeypatch,
        {
            "models/registry.json": '{"champion":"lagreg-v1"}',
            selected_key: json.dumps({"valid_at": selected_at, "forecast": []}),
            "scenarios/yamuna-2023-07/forecasts/2023-07-13T06_00_00+05_30.json": '{"valid_at":"earlier"}',
            "scenarios/yamuna-2023-07/forecasts/2023-07-13T12_00_00+05_30.json": '{"valid_at":"future"}',
        },
    )

    cases = [
        (_api_event("/models/card"), "models/registry.json", {"champion": "lagreg-v1"}),
        (
            _api_event("/scenarios/yamuna-2023-07/forecast", {"at": "2023-07-13T11:00:00+05:30"}),
            selected_key,
            {"valid_at": selected_at, "forecast": []},
        ),
    ]

    for event, expected_key, expected_body in cases:
        response = handler(event, None)
        assert response["statusCode"] == 200
        assert json.loads(response["body"]) == expected_body
        assert client.get_object_calls[-1] == ("jaltaranga-test-artifacts", expected_key)
    assert client.list_objects_calls == [
        ("jaltaranga-test-artifacts", "scenarios/yamuna-2023-07/forecasts/")
    ]


def test_lambda_s3_whatif_rewrites_flood_geojson_to_presigned_url(monkeypatch):
    whatif_key = "models/inundation/v1/whatif/208.6.json"
    geojson_key = "models/inundation/v1/ladder/208.6.geojson"
    client = _fake_s3(
        monkeypatch,
        {
            whatif_key: json.dumps(
                {"level_m": 208.6, "wet_colonies": [], "flood_geojson_url": f"/{geojson_key}"}
            ),
            geojson_key: '{"type":"FeatureCollection","features":[]}',
        },
    )

    response = handler(_api_event("/scenarios/yamuna-2023-07/whatif", {"level_m": "208.6"}), None)

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["level_m"] == 208.6
    assert body["flood_geojson_url"].startswith(f"https://s3.example.test/{geojson_key}?")
    assert client.get_object_calls == [
        ("jaltaranga-test-artifacts", whatif_key),
        ("jaltaranga-test-artifacts", geojson_key),
    ]
    assert client.presigned_calls[0][1]["Key"] == geojson_key
    assert 0 < client.presigned_calls[0][2] <= 900


def test_lambda_s3_flood_returns_presigned_urls_from_depth_index(monkeypatch):
    valid_at = "2023-07-13T10:00:00+05:30"
    tif_key = "scenarios/yamuna-2023-07/depth/2023-07-13T10_00_00+05_30.tif"
    geojson_key = "scenarios/yamuna-2023-07/depth/2023-07-13T10_00_00+05_30.geojson"
    index = [
        {
            "valid_at": valid_at,
            "tif": f"/{tif_key}",
            "geojson": f"/{geojson_key}",
            "level_m_ref": 208.53,
        }
    ]
    client = _fake_s3(
        monkeypatch,
        {"scenarios/yamuna-2023-07/depth/index.json": json.dumps(index)},
    )

    response = handler(_api_event("/scenarios/yamuna-2023-07/flood", {"at": valid_at}), None)

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["valid_at"] == valid_at
    assert body["level_m_ref"] == 208.53
    assert body["tif_url"].startswith(f"https://s3.example.test/{tif_key}?")
    assert body["geojson_url"].startswith(f"https://s3.example.test/{geojson_key}?")
    assert client.get_object_calls == [
        ("jaltaranga-test-artifacts", "scenarios/yamuna-2023-07/depth/index.json")
    ]
    assert [call[1]["Key"] for call in client.presigned_calls] == [tif_key, geojson_key]
    assert all(0 < call[2] <= 900 for call in client.presigned_calls)


def test_lambda_s3_flood_returns_404_when_timestamp_is_not_indexed(monkeypatch):
    index = [
        {
            "valid_at": "2023-07-13T10:00:00+05:30",
            "tif": "/scenarios/yamuna-2023-07/depth/known.tif",
            "geojson": "/scenarios/yamuna-2023-07/depth/known.geojson",
            "level_m_ref": 208.53,
        }
    ]
    client = _fake_s3(
        monkeypatch,
        {"scenarios/yamuna-2023-07/depth/index.json": json.dumps(index)},
    )

    response = handler(
        _api_event("/scenarios/yamuna-2023-07/flood", {"at": "2023-07-13T11:00:00+05:30"}),
        None,
    )

    assert response["statusCode"] == 404
    assert client.presigned_calls == []


def test_lambda_s3_does_not_fallback_for_missing_forecast(monkeypatch):
    client = _fake_s3(
        monkeypatch,
        {"scenarios/yamuna-2023-07/forecasts/2023-07-13T12_00_00+05_30.json": '{"valid_at":"future"}'},
    )
    requested_at = "2023-07-13T11:00:00+05:30"

    response = handler(
        _api_event("/scenarios/yamuna-2023-07/forecast", {"at": requested_at}),
        None,
    )

    assert response["statusCode"] == 404
    assert client.get_object_calls == []


def test_lambda_rejects_invalid_ml_query_parameters(monkeypatch):
    client = _fake_s3(monkeypatch, {})

    bad_level = handler(
        _api_event("/scenarios/yamuna-2023-07/whatif", {"level_m": "not-a-number"}),
        None,
    )
    bad_timestamp = handler(
        _api_event("/scenarios/yamuna-2023-07/forecast", {"at": "not-a-timestamp"}),
        None,
    )

    assert bad_level["statusCode"] == 400
    assert bad_timestamp["statusCode"] == 400
    assert client.get_object_calls == []
