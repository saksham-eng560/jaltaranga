import importlib.util
import json
from pathlib import Path


spec = importlib.util.spec_from_file_location("routing_api", Path(__file__).resolve().parents[1] / "handlers" / "api.py")
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)


def ev(method, path, query=None, body=None):
    return {"version": "2.0", "rawPath": path, "queryStringParameters": query,
            "requestContext": {"http": {"method": method, "path": path}, "stage": "$default"},
            "body": json.dumps(body) if body is not None else None, "isBase64Encoded": False}


def call(*a, **k):
    r = api.handler(ev(*a, **k))
    return r["statusCode"], json.loads(r["body"]) if r["body"] else None, r["headers"]


def test_plans_and_roads(world):
    m = json.loads((Path(world["data"]) / "scenarios/yamuna-2023-07/manifest.json").read_text())
    s, plans, h = call("GET", "/scenarios/yamuna-2023-07/plans", {"at": m["default_at"].replace("+", " ")})
    assert s == 200 and plans and h["Access-Control-Allow-Origin"]
    assert plans[0]["priority"] >= plans[-1]["priority"]
    s, roads, _ = call("GET", "/scenarios/yamuna-2023-07/roads", {"at": "2023-07-11T09:59:00%2B05%3A30",
                                                                  "status": "red"})
    assert s == 200 and roads and all(r["status"] == "red" for r in roads)
    s, body, _ = call("GET", "/scenarios/nope/plans")
    assert s == 404 and body["error"]["code"] == "scenario_not_found"


def test_shelter_patch_conditional(world):
    s, shelters, _ = call("GET", "/shelters")
    assert s == 200
    sh = next(x for x in shelters if x["shelter_id"] == "SH-PV-08")
    free = sh["free_beds"]
    s, after, _ = call("PATCH", "/shelters/SH-PV-08", body={"delta": 10})
    assert s == 200 and after["free_beds"] == free - 10 and after["occupied"] == sh["occupied"] + 10
    s, body, _ = call("PATCH", "/shelters/SH-PV-08", body={"delta": free})
    assert s == 409 and body["error"]["code"] == "shelter_full"
    s, back, _ = call("PATCH", "/shelters/SH-PV-08", body={"delta": -10})
    assert s == 200 and back["free_beds"] == free
    s, body, _ = call("PATCH", "/shelters/SH-PV-08", body={"delta": -100000})
    assert s == 409
    assert call("PATCH", "/shelters/NOPE", body={"delta": 1})[0] == 404
    assert call("PATCH", "/shelters/SH-PV-08", body={"delta": "x"})[0] == 400


def test_post_report(world):
    s, body, _ = call("POST", "/reports", body={"location": [77.24, 28.65], "kind": "road_blocked", "depth_cm": 40,
                                                "has_photo": True, "replay_at": "2023-07-11T09:00:00+05:30"})
    assert s == 201
    assert body["report"]["trust"] == 0.6 and body["report"]["verified"] is False
    assert body["report"]["photo_key"].startswith("uploads/reports/")
    assert body["upload"] is None  # offline: no presign
    s, body, _ = call("POST", "/reports", body={"location": [77.24], "kind": "road_blocked"})
    assert s == 400 and body["error"]["code"] == "invalid_report"


def test_router_basics(world):
    assert api.handler(ev("OPTIONS", "/shelters"))["statusCode"] == 204
    assert call("DELETE", "/shelters")[0] == 405
    assert call("GET", "/nope")[0] == 404
