import json
from pathlib import Path

import pytest

from jt_alerts.facts import Gazetteer, build_facts
from jt_shared import io
from jt_shared.naming import s3_key

RECORDED = Path(__file__).parent / "recorded"


@pytest.fixture(scope="session")
def static(world):
    from jt_alerts.service import static_data

    static_data.cache_clear()
    return static_data()


@pytest.fixture(scope="session")
def hero_t(world):
    return io.read_json(s3_key("manifest", scenario_id="yamuna-2023-07"))["default_at"]


@pytest.fixture(scope="session")
def hero_facts(static, hero_t):
    colonies, shelters, gaz = static
    plan = next(p for p in io.read_json(s3_key("plans", scenario_id="yamuna-2023-07", valid_at=hero_t))
                if p["colony_id"] == "DEL-YP-04")
    f = build_facts("yamuna-2023-07", colonies["DEL-YP-04"], "URGENT_EVACUATION_DISPATCH", hero_t, plan,
                    shelters[plan["primary"]["shelter_id"]], vulnerable_priority=True)
    return f, gaz, plan


@pytest.fixture
def recorded():
    return json.loads((RECORDED / "handwritten_samples.json").read_text("utf-8"))


@pytest.fixture
def toy_gaz():
    return Gazetteer(["Yamuna Pushta Sector C", "Kashmiri Gate Community Hall", "Ring Road", "Bela Road"],
                     ["यमुना पुश्ता सेक्टर सी", "कश्मीरी गेट सामुदायिक भवन", "रिंग रोड", "बेला रोड"])
