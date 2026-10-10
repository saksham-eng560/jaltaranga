import networkx as nx
import numpy as np

from jt_routing.candidates import build_candidates
from jt_routing.tdsp import EdgeTimes, route_is_safe, search

import toy

SPEED = 3.0  # km/h → 0.8333 m/s


def times(g, close=None, depth=None, amber=None):
    n = g.n_edges
    return EdgeTimes(close_s=np.array(close if close is not None else [np.inf] * n, float),
                     depth=np.array(depth if depth is not None else [0.0] * n, float),
                     amber=np.array(amber if amber is not None else [False] * n, bool))


def idx(g, u, v):
    a, b = g.node_ids.index(str(u)), g.node_ids.index(str(v))
    for e in g.edges:
        if {e.u, e.v} == {a, b}:
            return e.idx
    raise KeyError((u, v))


def node(g, n):
    return g.node_ids.index(str(n))


def test_edge_closing_one_minute_too_early_is_rejected():
    g = toy.graph({1: (0, 0), 2: (300, 0)}, [(1, 2)])
    walk = g.edges[0].length_m / (SPEED / 3.6)
    ok = search(g, node(g, 1), times(g, close=[walk + 1800]), SPEED, targets={node(g, 2)})
    assert ok.reached(node(g, 2))
    late = search(g, node(g, 1), times(g, close=[walk + 1800 - 60]), SPEED, targets={node(g, 2)})
    assert not late.reached(node(g, 2))


def test_red_edge_never_used_and_detour_taken():
    # square 1-2-3 with direct 1-3 red
    g = toy.graph({1: (0, 0), 2: (200, 200), 3: (400, 0)}, [(1, 3), (1, 2), (2, 3)])
    t = times(g, close=[0 if {e.u, e.v} == {node(g, 1), node(g, 3)} else np.inf for e in g.edges])
    res = search(g, node(g, 1), t, SPEED, targets={node(g, 3)})
    path = [g.edges[e] for _, e in res.path(node(g, 3))]
    assert len(path) == 2


def test_fallback_finds_route_cost_dijkstra_misses():
    # O→A short but wet (cost ×2.25), O→B long and dry; both join C; C→T closes soon.
    g = toy.graph({0: (0, 0), 1: (300, 0), 2: (0, 600), 3: (300, 100), 4: (400, 100)},
                  [(0, 1), (0, 2), (1, 3), (2, 3), (3, 4)])
    for e in g.edges:  # force exact lengths for a clean construction
        e.length_m = {(0, 1): 300, (0, 2): 600, (1, 3): 100, (2, 3): 100, (3, 4): 100}[
            tuple(sorted((int(g.node_ids[e.u]), int(g.node_ids[e.v]))))]
    v = SPEED / 3.6
    close = [np.inf] * g.n_edges
    close[idx(g, 3, 4)] = (500 / v) + 1800 + 30  # only the 500 m route (via A) clears it 30 min early
    depth = [0.0] * g.n_edges
    depth[idx(g, 0, 1)] = 0.25
    t = times(g, close=close, depth=depth)
    T, O = node(g, 4), node(g, 0)
    assert not search(g, O, t, SPEED, mode="cost", targets={T}).reached(T)
    assert search(g, O, t, SPEED, mode="arrival", targets={T}).reached(T)
    cands = build_candidates(g, O, {"SH": T}, t, SPEED)
    assert cands.mode == "arrival" and cands.candidates[0].best.shelter_id == "SH"
    assert route_is_safe(g, cands.candidates[0].best.path, t, SPEED)


def test_without_closures_equals_networkx_shortest_path():
    rng = np.random.default_rng(1)
    nodes = {i: (float(rng.uniform(0, 1500)), float(rng.uniform(0, 1500))) for i in range(12)}
    gx = nx.Graph()
    for i in nodes:
        for j in nodes:
            if i < j and np.hypot(nodes[i][0] - nodes[j][0], nodes[i][1] - nodes[j][1]) < 700:
                gx.add_edge(i, j)
    g = toy.graph({n: nodes[n] for n in gx.nodes}, list(gx.edges))
    for u, v in gx.edges:
        gx[u][v]["w"] = g.edges[idx(g, u, v)].length_m
    src = list(gx.nodes)[0]
    for dst in list(gx.nodes)[1:]:
        if not nx.has_path(gx, src, dst):
            continue
        res = search(g, node(g, src), times(g), SPEED, max_walk_s=1e9)
        ours = [node(g, src)] + [g.other(g.edges[e], n) for n, e in res.path(node(g, dst))]
        theirs = [node(g, n) for n in nx.dijkstra_path(gx, src, dst, weight="w")]
        assert np.isclose(sum(gx[a][b]["w"] for a, b in zip(nx.dijkstra_path(gx, src, dst, weight="w"),
                                                             nx.dijkstra_path(gx, src, dst, weight="w")[1:])),
                          res.arrival_s[node(g, dst)] * SPEED / 3.6)
        assert ours[0] == theirs[0] and ours[-1] == theirs[-1]


def test_walk_limit():
    g = toy.graph({1: (0, 0), 2: (5000, 0)}, [(1, 2)])
    assert not search(g, node(g, 1), times(g), SPEED, targets={node(g, 2)}).reached(node(g, 2))
