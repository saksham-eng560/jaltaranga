import pytest

from jt_routing.assign import Demand, assign, check_capacity, greedy, min_cost_flow
from jt_routing import priority
from jt_shared.models import Colony


def demands():
    return [Demand("A", 0.9, 300, [("S1", 10), ("S2", 30)]),
            Demand("B", 0.5, 250, [("S1", 12), ("S2", 15)]),
            Demand("C", 0.7, 200, [("S2", 20), ("S1", 40)])]


def test_greedy_respects_free_beds_and_priority():
    beds = {"S1": 350, "S2": 300}
    a = greedy(demands(), beds)
    check_capacity(a, beds)
    assert a["A"].allocations == {"S1": 300}  # highest priority served first, nearest shelter
    assert a["A"].primary == "S1"
    total = sum(sum(x.allocations.values()) for x in a.values())
    assert total == 650 and sum(x.unassigned for x in a.values()) == 100


def test_ortools_agrees_with_greedy_on_3x2_and_respects_capacity():
    beds = {"S1": 1000, "S2": 1000}  # ample capacity → both send everyone to their nearest shelter
    g, o = greedy(demands(), beds), min_cost_flow(demands(), beds)
    for cid in "ABC":
        assert g[cid].primary == o[cid].primary
        assert sum(o[cid].allocations.values()) == {"A": 300, "B": 250, "C": 200}[cid]
    tight = {"S1": 350, "S2": 300}
    o2 = min_cost_flow(demands(), tight)
    check_capacity(o2, tight)
    assert sum(sum(x.allocations.values()) for x in o2.values()) == 650
    assert o2["A"].unassigned == 0  # highest priority is never the one left out


def test_check_capacity_raises():
    with pytest.raises(AssertionError):
        check_capacity(greedy([Demand("A", 1, 10, [("S", 1)])], {"S": 10}), {"S": 5})


def test_assign_dispatch():
    assert assign(demands(), {"S1": 10, "S2": 10}, "ortools")["A"].allocations


def test_priority_formula():
    c = Colony(colony_id="X", name_en="x", name_hi="x", centroid=[77.2, 28.6], population_est=1000,
               vulnerable={"elderly": 100, "disabled": 10, "children_u5": 100, "pregnant": 10})
    assert priority.vulnerability(c) == pytest.approx((150 + 20 + 130 + 18) / 1000)
    assert priority.score(0, 1, 1, 1) == 1.0
    assert priority.score(24, 0, 0, 0) == 0.0
    assert priority.score(12, 0.5, 0.5, 0) == pytest.approx(0.45 * 0.5 + 0.25 * 0.5 + 0.2 * 0.5)
    assert priority.walk_speed(0.7) == 2.0 and priority.walk_speed(0.5) == 3.0
