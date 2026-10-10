"""Every shared fixture validates against the jt_shared models (SHARED §7: frontend never waits on a backend)."""

import json
from pathlib import Path

import pytest

from jt_shared.models import (DispatchCard, EvacuationPlan, ReportPostResponse, RoadSegmentStatus, Shelter,
                              TrapSummary, UnreachableEntry)

FIX = Path(__file__).resolve().parents[2] / "fixtures"


def load(name):
    return json.loads((FIX / name).read_text("utf-8"))


@pytest.mark.parametrize("name,model,many", [
    ("road_segment_status.json", RoadSegmentStatus, True),
    ("plans_unreachable.json", UnreachableEntry, True),
    ("shelters.json", Shelter, True),
    ("dispatch_card.json", DispatchCard, False),
    ("dispatch_card_fallback.json", DispatchCard, False),
    ("dispatch_card_shelter_in_place.json", DispatchCard, False),
    ("report_post_response.json", ReportPostResponse, False),
    ("trap_summary.json", TrapSummary, False),
])
def test_fixture_validates(name, model, many):
    data = load(name)
    for row in (data if many else [data]):
        model.model_validate(row)


def test_plans_fixture():
    plans = load("evacuation_plans.json")
    assert len(plans) == 5
    n = sum(len(v) for v in plans.values())
    assert n > 0
    for rows in plans.values():
        for p in rows:
            EvacuationPlan.model_validate(p)


def test_fallback_fixture_shows_per_field_fallback():
    c = load("dispatch_card_fallback.json")
    assert c["validation"]["passed"] and c["validation"]["fallback_used"]
    assert c["validation"]["fallback_fields"] and c["validation"]["failed_checks"]
    DispatchCard.model_validate(load("dispatch_cache_sample.json")["card"])
