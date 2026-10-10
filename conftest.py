"""Repo-wide pytest setup: import paths and a session-scoped synthetic dev world.

The `world` fixture builds the dev world (routing/jt_routing/devworld.py) into a temp
JT_LOCAL_DATA, precomputes the routing window around T_hero, picks T_hero and predrafts
dispatch cards, so routing and alerts tests run offline against real writer outputs.
"""

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent
for p in ("shared/py", "routing", "alerts"):
    sys.path.insert(0, str(ROOT / p))

WINDOW = "2023-07-10T21:00:00+05:30/2023-07-11T15:00:00+05:30"


@pytest.fixture(scope="session")
def world(tmp_path_factory):
    data = tmp_path_factory.mktemp("jt_data")
    old = os.environ.get("JT_LOCAL_DATA")
    os.environ["JT_LOCAL_DATA"] = str(data)
    for k in ("JT_BEDROCK_MODEL_ID", "JT_SNS_TOPIC_ARN", "JT_DATA_BUCKET"):
        os.environ.pop(k, None)
    from jt_routing import devworld, hero, precompute

    devworld.build()
    out = precompute.run("yamuna-2023-07", window=WINDOW, quiet=True)
    hero.main(["--write-manifest"])
    from jt_alerts import predraft, service

    service.static_data.cache_clear()
    service.manifest.cache_clear()
    drafted = predraft.run("yamuna-2023-07", "demo")
    yield {"data": data, "precompute": out, "predraft": drafted}
    if old is None:
        os.environ.pop("JT_LOCAL_DATA", None)
    else:
        os.environ["JT_LOCAL_DATA"] = old
