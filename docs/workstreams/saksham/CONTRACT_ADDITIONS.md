# Proposed additive contract changes (for a small PR to `main`, SHARED §10)

Everything here is **additive and optional**. Existing readers keep working. This is plan §11's "still open" list,
updated after implementation. The models in `shared/py/jt_shared/models.py` already implement these changes.

1. **`scenarios/<id>/dispatch_cache/<t>/<colony_id>.json`** (already in §11.8-10): a validated `DispatchCard`.
   Arjav's ladder rung 4.
2. **`EvacuationPlan`**
   - `t_submersion_earliest`, `t_submersion_latest` (nullable timestamps): the §11.8-3 `earliest` (first `hi_m ≥ wet_at`)
     and `latest` (first `lo_m ≥ wet_at`, null if none within 24 h). The frontend renders them and never recomputes them.
   - `ext` (nullable): `{walk_speed_kmh, transport_needed, replanned_due_to, origin_offset_m, assigned_people, demand_people}`.
   - `primary.route_geojson` is a GeoJSON `Feature` (LineString) whose `properties.edge_ids` lists the route's edges.
3. **`UnreachableEntry.reason`** ∈ `already_wet | no_dry_origin | no_feasible_route | no_shelter_capacity`.
4. **`RoadSegmentStatus.reason`** adds `field_report` (only from the F2b offline reroute).
5. **`DispatchCard`**
   - `alert_type` adds `SHELTER_IN_PLACE` (§11.8-2).
   - `validation` adds `failed_checks` (checks the raw LLM text failed), `fallback_fields`
     (fields replaced by the template) and `source` ∈ `bedrock | template | cache`. Arjav's fallback banner can key on
     `fallback_used` exactly as before.
6. **New artefacts:** `scenarios/<id>/routing/hero.json` (`T_hero` + backup hero, the rule, candidates),
   `scenarios/<id>/plans/<t>.candidates.json` (already §11.2), `static/osm/edge_cutoffs.json` (already §11.8-5).
7. **New route:** `GET /scenarios/{id}/unreachable?at=` (thin passthrough, like `/plans`).
