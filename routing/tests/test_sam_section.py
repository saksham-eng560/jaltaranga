"""The append-only SAM block parses, and its routes match the handlers and SHARED §7 names."""

import importlib.util
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


class _Loader(yaml.SafeLoader):
    pass


for _tag in ("!Ref", "!Sub", "!GetAtt"):
    _Loader.add_constructor(_tag, lambda loader, node: loader.construct_scalar(node))


def _routes(path):
    spec = importlib.util.spec_from_file_location(f"h_{path.parent.parent.name}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return {(m, p.pattern) for m, p, _ in mod.router.routes}


def test_sam_section_matches_handlers():
    doc = yaml.load("Resources:\n" + (ROOT / "infra/sections/routing_alerts.yaml").read_text(), Loader=_Loader)
    res = doc["Resources"]
    for fn, handler in (("RoutingFunction", "routing/handlers/api.py"), ("AlertsFunction", "alerts/handlers/api.py")):
        props = res[fn]["Properties"]
        assert props["Runtime"] == "python3.12" and props["Architectures"] == ["arm64"]
        events = {(e["Properties"]["Method"], e["Properties"]["Path"]) for e in props["Events"].values()}
        router = _routes(ROOT / handler)
        assert len(events) == len(router)
        for method, path in events:
            assert "{scenario_id}" not in path and "{colony_id}" not in path  # SHARED §7 names: {id}, {cid}
            import re

            pat = "^" + re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", path) + "/?$"
            assert (method, pat) in router, (method, path)
    assert res["AlertsFunction"]["Properties"]["Timeout"] == 25
