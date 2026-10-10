# routing/: road cutoffs, evacuation routing, shelter assignment (owner: Saksham)

This package turns the forecast and the flood rasters into per-step **road status** and **evacuation plans**.
All heavy work runs offline (`make precompute`) and is served as static JSON (SHARED §6, §11.4).

```
cutoff_0p30.tif ─► per-edge cutoff level (min over 15 m samples; bridges inherit their approaches)
forecasts + gauges ─► level / lo / hi curves (h=0 is the observation) ─► exact crossing times
depth/<t>.tif ─► red (depth > 0.30 m now) · amber (max hi over (t, t+2h] reaches the cutoff)
colony_thresholds ─► t_submersion (central), earliest (hi), latest (lo)   (SHARED §11.8-3)
walk graph ─► cost-Dijkstra with closures → earliest-arrival fallback (exact) → K=3 shelters × best/alt
           ─► greedy | OR-Tools min-cost-flow assignment (never over free beds)
           ─► flood-blind path → avoid[] (+edge_ids) and the trap counterfactual (F5)
```

## Run it

```bash
pip install -r routing/requirements-offline.txt
make -C routing demo-local          # dev world → precompute (192 steps) → T_hero → predraft, ~25 s, no AWS
make -C routing inspect AT=2023-07-11T09:00:00+05:30
make -C routing inspect HERO=1      # hero candidates (SHARED §11.8-1)
make -C routing test                # or `pytest` at the repo root for everything
```

Against real teammate artefacts, drop `devworld` and point `JT_LOCAL_DATA` at the data folder built by
`make -C pipeline scenario` and `make -C ml replay-local`:

```bash
make -C routing precompute SCENARIO=yamuna-2023-07 [WINDOW=demo|all|<from>/<to>] [STEP=3] [SOLVER=ortools]
make -C routing hero [WRITE_MANIFEST=1]
make -C routing publish BUCKET=jt-demo-data-<acct>    # the only target that needs AWS credentials
```

`precompute` exits non-zero if any safety invariant fails: a route crosses a red edge, an edge
violates `arrival + 30 min ≤ close_at`, `primary.max_depth_m > 0.30`, a shelter gets more people than
it has free beds, or an `edge_id` does not join `roads.geojson`.

## Inputs → outputs

| Reads (under `$JT_LOCAL_DATA`) | Writes |
|---|---|
| `static/osm/corridor_roads.graphml`, `static/osm/roads.geojson` | `scenarios/<id>/roads/<t>.json` (non-green `RoadSegmentStatus`) |
| `static/colonies.geojson`, `static/shelters.geojson` | `scenarios/<id>/plans/<t>.json` (`EvacuationPlan`, sorted by priority) |
| `models/inundation/v1/{cutoff_0p30,onset}.tif`, `colony_thresholds.json` | `plans/<t>.unreachable.json` (always written), `plans/<t>.candidates.json` |
| `scenarios/<id>/{manifest,gauges}.json`, `forecasts/<t>.json`, `depth/<t>.tif` | `scenarios/<id>/routing/{trap_summary,hero}.json`, `static/osm/edge_cutoffs.json` |

## Degrade paths

- **No `cutoff_0p30.tif`:** red-only mode. There's no amber, and closures are "red now". A warning is printed. We never fall back to our own datum arithmetic (§11.1).
- **No depth raster for a step:** status comes from the forecast only (depth 0).
- **No forecast for a step:** persistence. The latest earlier forecast is used if one exists.
- **OR-Tools missing:** greedy, which satisfies the same capacity invariant.

## Lambda (`handlers/api.py`, `jt_routing/serving.py`)

No numpy or networkx at runtime. It serves `GET /scenarios/{id}/roads|plans|unreachable?at=`, `GET /shelters`,
`PATCH /shelters/{id}` (`{delta}`, conditional `ADD occupied :d, free_beds :neg` with `free_beds >= :d`, which returns 409 when full)
and `POST /reports` (validates a `FieldReport` and returns a presigned POST ≤ 1 MB JPEG, valid for 5 min). The SAM block is in
[`infra/sections/routing_alerts.yaml`](../infra/sections/routing_alerts.yaml).

## The dev world

`jt_routing/devworld.py` writes **synthetic** stand-ins for every upstream artefact. It uses the real corridor
geography and the July 2023 gauge anchors, but the flood surface is analytic. Everything it writes is labelled
`synthetic` / `fixture`. It exists so this workstream (and CI) runs end to end before `pipeline/` and `ml/` land.
In the dev world, `T_hero` = 11 Jul 2023 09:00. At that point Yamuna Pushta has 2.5 h of lead, the primary route is a 46-minute
walk to Daryaganj Relief Camp, Bela Road is on the avoid list (red since 01:00), and the flood-blind route traps 4,200 people.
These are dev-world numbers, not claims.
