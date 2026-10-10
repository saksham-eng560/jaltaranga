import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from jt_shared import io, naming, timeutil
from jt_shared.export_schemas import export
from jt_shared.models import ALL_MODELS, GaugeReading, Shelter

SHARED = Path(__file__).resolve().parents[2]


def test_parse_ts_variants():
    a = timeutil.parse_ts("2023-07-13T00:00:00+05:30")
    assert timeutil.parse_ts("2023-07-13T00:00:00%2B05%3A30") == a
    assert timeutil.parse_ts("2023-07-13T00:00:00 05:30") == a
    assert timeutil.parse_ts("2023-07-12T18:30:00Z") == a
    assert timeutil.iso(a) == "2023-07-13T00:00:00+05:30"
    with pytest.raises(ValueError):
        timeutil.parse_ts("2023-07-13T00:00:00")


def test_snap_to_step():
    t = timeutil.snap_to_step("2023-07-13T04:59:00+05:30", 60)
    assert timeutil.iso(t) == "2023-07-13T04:00:00+05:30"


def test_naming():
    assert naming.resource_name("alerts", "fn", "demo") == "jt-demo-alerts-fn"
    with pytest.raises(ValueError):
        naming.resource_name("alerts", "fn", "prod")
    k = naming.s3_key("plans", scenario_id="yamuna-2023-07", valid_at="2023-07-13T00:00:00+05:30")
    assert k == "scenarios/yamuna-2023-07/plans/2023-07-13T00:00:00+05:30.json"
    assert "%2B05%3A30" in naming.url_key(k)
    assert naming.s3_key("trap_summary", scenario_id="x") == "scenarios/x/routing/trap_summary.json"


def test_gauge_needs_a_value():
    with pytest.raises(ValidationError):
        GaugeReading(station_id="HATHNIKUND", ts="2023-07-11T00:00:00+05:30", source="cwc")
    GaugeReading(station_id="HATHNIKUND", ts="2023-07-11T00:00:00+05:30", source="cwc", discharge_cumecs=3000)


def test_shelter_free_beds_default():
    s = Shelter(shelter_id="S", name_en="a", name_hi="ए", location=[77.2, 28.6], capacity=400, occupied=150,
                type="school")
    assert s.free_beds == 250


def test_local_io_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("JT_LOCAL_DATA", str(tmp_path))
    io.write_json("a/b.json", {"x": "यमुना"})
    assert io.read_json("a/b.json") == {"x": "यमुना"}
    assert io.read_json_or("missing.json", []) == []
    with pytest.raises(io.NotFound):
        io.read_json("missing.json")


def test_schemas_up_to_date(tmp_path):
    export(tmp_path)
    for name in ALL_MODELS:
        fresh = json.loads((tmp_path / f"{name}.schema.json").read_text())
        committed = json.loads((SHARED / "schemas" / f"{name}.schema.json").read_text())
        assert fresh == committed, f"schema drift in {name}: run python -m jt_shared.export_schemas"
