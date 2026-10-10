"""§9.1: every routing output validates against jt_shared models (and the exported JSON Schemas)."""

import json
from pathlib import Path

import jsonschema

from jt_shared import io
from jt_shared.models import EvacuationPlan, RoadSegmentStatus, TrapSummary, UnreachableEntry

SCHEMAS = Path(__file__).resolve().parents[2] / "shared" / "schemas"


def schema(name):
    return json.loads((SCHEMAS / f"{name}.schema.json").read_text())


def test_outputs_validate(world):
    root = Path(io.local_root()) / "scenarios" / "yamuna-2023-07"
    plan_schema, road_schema = schema("evacuation_plan"), schema("road_segment_status")
    n = 0
    for p in sorted((root / "plans").glob("*+05:30.json")):
        for row in json.loads(p.read_text()):
            EvacuationPlan.model_validate(row)
            jsonschema.validate(row, plan_schema)
            n += 1
    for p in sorted((root / "plans").glob("*.unreachable.json")):
        for row in json.loads(p.read_text()):
            UnreachableEntry.model_validate(row)
    for p in sorted((root / "roads").glob("*.json"))[:5]:
        for row in json.loads(p.read_text()):
            RoadSegmentStatus.model_validate(row)
            jsonschema.validate(row, road_schema)
    TrapSummary.model_validate(json.loads((root / "routing" / "trap_summary.json").read_text()))
    assert n > 0
