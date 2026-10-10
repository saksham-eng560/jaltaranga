"""Capacity-aware shelter assignment (F2). Invariant: no shelter is assigned more than its free beds.

``greedy`` (Must) walks colonies in priority order and fills their nearest feasible shelters.
``min_cost_flow`` (Should) solves the same problem with OR-Tools ``SimpleMinCostFlow`` and an
*unassigned* sink at cost 10⁶. Both return the same type, so the plan builder does not care.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Demand:
    colony_id: str
    priority: float
    people: int
    options: list[tuple[str, float]]  # (shelter_id, walk_min), nearest first


@dataclass
class Allocation:
    colony_id: str
    allocations: dict[str, int]  # shelter_id → people
    unassigned: int

    @property
    def primary(self) -> str | None:
        if not self.allocations:
            return None
        return max(self.allocations.items(), key=lambda kv: (kv[1], kv[0]))[0]


def greedy(demands: list[Demand], free_beds: dict[str, int]) -> dict[str, Allocation]:
    left = dict(free_beds)
    out: dict[str, Allocation] = {}
    for d in sorted(demands, key=lambda d: (-d.priority, d.colony_id)):
        need, alloc = d.people, {}
        for sid, _ in d.options:
            if need <= 0:
                break
            take = min(need, left.get(sid, 0))
            if take > 0:
                alloc[sid] = alloc.get(sid, 0) + take
                left[sid] -= take
                need -= take
        out[d.colony_id] = Allocation(d.colony_id, alloc, need)
    return out


UNASSIGNED_COST = 1_000_000


def min_cost_flow(demands: list[Demand], free_beds: dict[str, int]) -> dict[str, Allocation]:
    from ortools.graph.python import min_cost_flow as mcf

    smcf = mcf.SimpleMinCostFlow()
    shelters = sorted(free_beds)
    colonies = [d for d in demands if d.people > 0]
    src, sink, unassigned = 0, 1, 2
    c_node = {d.colony_id: 3 + i for i, d in enumerate(colonies)}
    s_node = {s: 3 + len(colonies) + i for i, s in enumerate(shelters)}
    total = sum(d.people for d in colonies)
    arcs = []
    for d in colonies:
        smcf.add_arc_with_capacity_and_unit_cost(src, c_node[d.colony_id], d.people, 0)
        for sid, walk_min in d.options:
            if sid in s_node:
                cost = int(round(walk_min * 100 / (1 + d.priority)))
                a = smcf.add_arc_with_capacity_and_unit_cost(c_node[d.colony_id], s_node[sid], d.people, cost)
                arcs.append((a, d.colony_id, sid))
        # Higher priority colonies pay more for being left unassigned, so they are served first.
        smcf.add_arc_with_capacity_and_unit_cost(c_node[d.colony_id], unassigned, d.people,
                                                 int(UNASSIGNED_COST * (1 + d.priority)))
    for sid in shelters:
        smcf.add_arc_with_capacity_and_unit_cost(s_node[sid], sink, max(0, free_beds[sid]), 0)
    smcf.add_arc_with_capacity_and_unit_cost(unassigned, sink, total, 0)
    smcf.set_node_supply(src, total)
    smcf.set_node_supply(sink, -total)
    status = smcf.solve()
    if status != smcf.OPTIMAL:
        raise RuntimeError(f"min-cost flow failed with status {status}")
    out = {d.colony_id: Allocation(d.colony_id, {}, d.people) for d in demands}
    for a, cid, sid in arcs:
        f = smcf.flow(a)
        if f > 0:
            out[cid].allocations[sid] = out[cid].allocations.get(sid, 0) + f
            out[cid].unassigned -= f
    return out


def assign(demands: list[Demand], free_beds: dict[str, int], solver: str = "greedy") -> dict[str, Allocation]:
    if solver == "ortools":
        try:
            return min_cost_flow(demands, free_beds)
        except ImportError:
            pass  # degrade path: greedy satisfies the same invariant
    return greedy(demands, free_beds)


def check_capacity(allocs: dict[str, Allocation], free_beds: dict[str, int]) -> None:
    used: dict[str, int] = {}
    for a in allocs.values():
        for sid, n in a.allocations.items():
            used[sid] = used.get(sid, 0) + n
    over = {s: (n, free_beds.get(s, 0)) for s, n in used.items() if n > free_beds.get(s, 0)}
    if over:
        raise AssertionError(f"shelter over capacity: {over}")
