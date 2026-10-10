"""Safety invariants re-checked independently from the written artefacts (INTEGRATION_PLAN §3)."""


from jt_shared import io
from jt_shared.naming import s3_key


def steps(world):
    m = io.read_json(s3_key("manifest", scenario_id="yamuna-2023-07"))
    return [t for t in m["valid_at"] if io.exists(s3_key("plans", scenario_id="yamuna-2023-07", valid_at=t))]


def test_precompute_reports_no_violations(world):
    assert world["precompute"]["violations"] == 0
    assert world["precompute"]["plans"] > 0


def test_no_route_crosses_a_red_edge_and_depth_limit(world):
    ts = steps(world)
    assert ts
    n_routes = 0
    for t in ts:
        roads = io.read_json(s3_key("roads", scenario_id="yamuna-2023-07", valid_at=t))
        red = {r["edge_id"] for r in roads if r["status"] == "red"}
        for p in io.read_json(s3_key("plans", scenario_id="yamuna-2023-07", valid_at=t)):
            assert p["primary"]["max_depth_m"] <= 0.30
            for kind in ("primary", "backup"):
                if p[kind]:
                    ids = set(p[kind]["route_geojson"]["properties"]["edge_ids"])
                    assert not ids & red, f"{t} {p['colony_id']} {kind} crosses red {ids & red}"
                    n_routes += 1
    assert n_routes > 0


def test_shelters_never_over_free_beds(world):
    beds = {f["properties"]["shelter_id"]: f["properties"]["free_beds"]
            for f in io.read_json(s3_key("shelters"))["features"]}
    for t in steps(world):
        used = {}
        for c in io.read_json(s3_key("candidates", scenario_id="yamuna-2023-07", valid_at=t)):
            for a in c["allocations"]:
                used[a["shelter_id"]] = used.get(a["shelter_id"], 0) + a["people"]
        for sid, n in used.items():
            assert n <= beds[sid], f"{t}: {sid} assigned {n} > {beds[sid]}"


def test_edge_ids_join_roads_geojson_and_unreachable_always_written(world):
    envelope = {f["properties"]["edge_id"] for f in io.read_json(s3_key("roads_geojson"))["features"]}
    for t in steps(world):
        for r in io.read_json(s3_key("roads", scenario_id="yamuna-2023-07", valid_at=t)):
            assert r["edge_id"] in envelope
        for p in io.read_json(s3_key("plans", scenario_id="yamuna-2023-07", valid_at=t)):
            for a in p["avoid"]:
                assert set(a["edge_ids"]) <= envelope
        assert isinstance(io.read_json(s3_key("unreachable", scenario_id="yamuna-2023-07", valid_at=t)), list)


def test_edge_id_is_direction_agnostic(world):
    import networkx as nx

    g = nx.read_graphml(io.local_path(s3_key("graphml")))
    for u, v, d in list(g.edges(data=True))[:500]:
        back = g.get_edge_data(v, u)
        back = back if "edge_id" in back else next(iter(back.values()))  # Multi(Di)Graph from OSMnx
        assert back["edge_id"] == d["edge_id"]
        lo, hi = sorted((int(u), int(v)))
        assert d["edge_id"].startswith(f"osm:{lo}:{hi}:")


def test_edge_cutoffs_written_for_whatif(world):
    cut = io.read_json(s3_key("edge_cutoffs"))
    assert len(cut) > 1000 and all(v is None or 199 < v < 230 for v in cut.values())


def test_plan_ordering_and_time_to_water_fields(world):
    for t in steps(world):
        plans = io.read_json(s3_key("plans", scenario_id="yamuna-2023-07", valid_at=t))
        assert [p["priority"] for p in plans] == sorted((p["priority"] for p in plans), reverse=True)
        for p in plans:
            assert p["computed_at"] == t
            assert p["lead_time_h"] * 2 == int(p["lead_time_h"] * 2)
            if p["t_submersion_earliest"]:
                assert p["t_submersion_earliest"] <= p["t_submersion"]
            if p["t_submersion_latest"]:
                assert p["t_submersion_latest"] >= p["t_submersion"]
