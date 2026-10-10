"""F2b (Could): a verified road_blocked report turns nearby edges red from replay_at and re-plans."""

import json

from jt_routing import precompute
from jt_shared import io
from jt_shared.naming import s3_key

A, B = "2023-07-11T16:00:00+05:30", "2023-07-11T17:00:00+05:30"


def test_report_blocks_edges_and_marks_replan(world, tmp_path):
    precompute.run("yamuna-2023-07", window=f"{A}/{A}", quiet=True)
    plans = io.read_json(s3_key("plans", scenario_id="yamuna-2023-07", valid_at=A))
    assert plans
    p = plans[0]
    coords = p["primary"]["route_geojson"]["geometry"]["coordinates"]
    mid = coords[len(coords) // 2]
    report = [{"report_id": "rep-1", "ts": B, "replay_at": B, "location": mid, "kind": "road_blocked",
               "reporter_id": "anon", "trust": 0.6, "verified": True}]
    path = tmp_path / "reports.json"
    path.write_text(json.dumps(report))
    out = precompute.run("yamuna-2023-07", window=f"{A}/{B}", reports=str(path), quiet=True)
    assert out["violations"] == 0
    roads = io.read_json(s3_key("roads", scenario_id="yamuna-2023-07", valid_at=B))
    blocked = {r["edge_id"] for r in roads if r["reason"] == "field_report"}
    assert blocked and all(r["status"] == "red" for r in roads if r["reason"] == "field_report")
    after = {x["colony_id"]: x for x in io.read_json(s3_key("plans", scenario_id="yamuna-2023-07", valid_at=B))}
    if p["colony_id"] in after:
        q = after[p["colony_id"]]
        assert q["ext"]["replanned_due_to"] == "rep-1"
        assert not set(q["primary"]["route_geojson"]["properties"]["edge_ids"]) & blocked
    before = {r["edge_id"] for r in io.read_json(s3_key("roads", scenario_id="yamuna-2023-07", valid_at=A))
              if r["reason"] == "field_report"}
    assert not before  # nothing blocked before replay_at
