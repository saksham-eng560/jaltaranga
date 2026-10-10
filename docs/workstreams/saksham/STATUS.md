# Saksham workstream: implementation status

This tracks the implementation against [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md), the [`QUALITY_REVIEW.md`](QUALITY_REVIEW.md)
actions and SHARED_RESOURCES §11.8 (v1.2). Branch `feature/saksham`.

**How to verify:** `pip install -r routing/requirements-offline.txt && pytest` (136 tests, ~30 s), then
`make -C routing demo-local` (the full offline chain, ~25 s, no AWS credentials).

## Built and tested

| Plan item | MoSCoW | Where | Test |
|---|---|---|---|
| Red/amber per step; amber uses the **window max** of `hi_m` over (t, t+2h] (§11.8-4) | Must | `routing/jt_routing/cutoff.py` | `test_cutoff.py`, `test_forecast.py` |
| One per-edge cutoff implementation (min over 15 m samples) → `static/osm/edge_cutoffs.json` (§11.8-5) | Must | `cutoff.py`, `precompute.py` | `test_invariants.py` |
| Bridge inheritance (bridges sampled only at their approaches) | Must | `graph.py` | `test_cutoff.py::test_bridge_samples_only_its_approaches` |
| Cost-Dijkstra with closures + **earliest-arrival fallback** (exact on FIFO) | Must | `tdsp.py`, `candidates.py` | `test_tdsp.py::test_fallback_finds_route_cost_dijkstra_misses` |
| Dry-origin rule: nearest dry node within 300 m (§11.8-2) | Must | `plan.py::pick_origin` | invariants |
| Time-to-water: `t_submersion` (central), `t_submersion_earliest` (hi), `t_submersion_latest` (lo) (§11.8-3) | Must | `plan.py` | `test_invariants.py::test_plan_ordering_and_time_to_water_fields` |
| K=3 candidates × best/alt (×10 penalty, < 50% overlap); primary/backup | Must | `candidates.py`, `plan.py` | `test_hero_and_trap.py` |
| Greedy capacity-safe assignment | Must | `assign.py` | `test_assign.py`, `test_invariants.py::test_shelters_never_over_free_beds` |
| **OR-Tools min-cost flow** (same output type; unassigned sink) | Should | `assign.py::min_cost_flow` (`SOLVER=ortools`) | `test_assign.py` |
| `avoid[]` + `edge_ids` (whole named road within 1 km) | Must | `avoid.py` | `test_hero_and_trap.py` |
| Trap counterfactual + `routing/trap_summary.json` (scenario-scoped, §11.8-10) | Should (F5) | `avoid.py`, `precompute.py` | `test_hero_and_trap.py` |
| Priority (F1 formula) + mobility (2 km/h when `V_norm > 0.6`, transport flag) + vulnerable-first sentence | Must / Should | `priority.py`, `alerts/templates.py` | `test_assign.py::test_priority_formula`, templates |
| `unreachable.json` always written; reasons `already_wet`, `no_dry_origin`, `no_feasible_route`, `no_shelter_capacity` | Must | `plan.py` | invariants |
| **`T_hero` + backup hero from data** → `routing/hero.json`, `manifest.default_at` (§11.8-1) | Must | `hero.py` | `test_hero_and_trap.py` |
| Safety invariants inline in precompute (non-zero exit) | Must | `plan.py::check_invariants` | `test_invariants.py` |
| Slot-filled drafter (forced tool, T=0, model sees no facts), one repair if ≥ 8 s left, per-field fallback, 18 s budget | Must | `alerts/jt_alerts/drafter.py` | `test_drafter.py` (recorded + deadline) |
| Validator (6 checks) + ≥ 40 mutation tests | Must | `validator.py` | `test_validator_mutations.py` (57 cases) |
| Templates hi/en/SMS (reviewed: [`HINDI_TEMPLATE_REVIEW.md`](HINDI_TEMPLATE_REVIEW.md)) incl. **SHELTER_IN_PLACE** (wet / no safe route) and **imminent** (< 1 h) wording (review defect 1) | Must | `templates.py` | `test_templates.py` |
| Lifecycle `alert_type`; dedup key + plan hash + 60 min cooldown; ALL_CLEAR | Must / Should (F4) | `lifecycle.py`, `service.py` | `test_lifecycle.py`, handler dedup test |
| Draft / approve (idempotent) / list / ack API, DynamoDB or local store | Must (+ Could ack) | `alerts/handlers/api.py`, `service.py`, `store.py` | `test_alerts_handlers.py` |
| SNS email: ASCII subject < 100, Hindi body; offline `.eml` outbox | Must | `notify.py` | `test_alerts_handlers.py`, `test_alerts_misc.py` |
| Polly Kajal, SSML from validated text, `audio/<sha256>.mp3` cache, lazy at approve, re-presign on list | Should (F3) | `polly.py`, `service.py` | `test_alerts_misc.py` (offline parts) |
| `predraft` → `dispatch_cache/<t>/<colony>.json` (fails on any invalid card) | Must | `jt_alerts/predraft.py` | `test_alerts_misc.py::test_predraft_cards_valid` |
| Hallucination eval: replay recorded outputs, 0 untraceable tokens; live mode records | Must | `alerts/scripts/halluc_eval.py` | `test_alerts_misc.py` |
| `GET roads/plans` passthrough, `GET/PATCH /shelters` (§11.4 conditional form, 409), `POST /reports` (presigned POST) | Must / Should | `routing/handlers/api.py`, `serving.py` | `test_routing_handlers.py` |
| F2b offline field-report reroute (`REPORTS=` file → `reason=field_report`, `ext.replanned_due_to`) | Could | `precompute.py` | `test_field_reports.py` |
| Observability: EMF `DraftLatencyMs`, `FallbackUsed`, `ValidatorFail_<check>` (review action 8) | — | `metrics.py` | `test_alerts_misc.py` |
| SAM section (2 Lambdas, least-privilege IAM, documented 3-statement global-profile Bedrock policy §11.8-11), **merged** into `infra/template.yaml` with the shared resources (bucket, 5 tables, SNS + email subscription, HTTP API, jt_shared layer, USD 10 budget) | Must | `infra/sections/routing_alerts.yaml`, `infra/base.yaml` → `infra/build_template.py` → `infra/template.yaml` | `test_sam_section.py`; `cfn-lint` (incl. SAM transform) clean; SAM translator → 28 resources, 10 routes (CI step) |
| Fixtures from the real writers | Must | `routing/scripts/make_fixtures.py` → `shared/fixtures/` | `shared/py/tests/test_fixtures.py` |
| §11.5 make targets (no AWS creds; `publish` separate) | Must | `routing/Makefile`, `alerts/Makefile` | CI |

## Built here because nothing existed yet

No other branch had code when this was written: `main`, `feature/shivansh`, `feature/vaibhav` and `feature/arjav` contain plans only.
So this branch also carries:

- **`shared/py/jt_shared`**: constants, pydantic models for every §5/§11 schema, naming, timeutil, io (with the
  `JT_LOCAL_DATA` fallback), a tiny HTTP API router, and exported JSON Schemas in `shared/schemas/`. Shivansh is the steward.
  This should go to `main` as the small PR described in INTEGRATION_PLAN §1 row 0, and his version wins if one already exists.
- **`routing/jt_routing/devworld.py`**: synthetic stand-ins for the graph, seeds, manifest, gauges, onset/cutoff/depth
  rasters, forecasts and colony thresholds, so routing and alerts run end to end. Replace with the real artefacts by
  pointing `JT_LOCAL_DATA` at the data Shivansh and Vaibhav build. Nothing else changes.

## Deployed (2026-10-10): stack `jt-demo`, ap-south-1, account 410133710130

| Step | Result |
|---|---|
| `make -C alerts probe` | **Failed.** Every Nova profile returns `AccessDeniedException: Your account is currently being verified`. Deployed with the template defaults (`us-east-1`, `us.amazon.nova-micro-v1:0`). Until verification clears, the drafter falls back per field to the templates (`fallback_used: true`). |
| `sam build` + `sam deploy` | OK. Built without a container (local python3.12). API `https://qu36c9519d.execute-api.ap-south-1.amazonaws.com`, bucket `jt-demo-data-410133710130`, topic `jt-demo-dispatch` (email subscription confirmed). |
| `make -C routing publish`, `make -C alerts publish` | OK, after `make -C routing demo-local`. Data is still the **dev world**. |
| Extra (not in the scripts) | Uploaded `manifest.json`, `gauges.json` and `static/{colonies,shelters}.geojson`, because the API 404s without the manifest. Seeded `jt-demo-shelters` (8 rows) from `shelters.geojson`, because nothing seeds the table. |
| Smoke test | `GET /shelters`, `/scenarios/yamuna-2023-07/{roads,plans,unreachable}` → 200. Draft for DEL-BLA-02 passed validation (6/6), approve → `sent`. Polly returned no `audio_url` (likely also blocked by verification). |
| `make -C alerts halluc-live N=20` | **Not run:** Bedrock is blocked. |

**Still to do once AWS finishes verifying the account:** re-run `make -C alerts probe`. If the probe picks a different
profile, re-deploy with its `BedrockRegion`/`BedrockModelId`. Then run `make -C alerts halluc-live N=20` and check Polly audio on approve.
Add the manifest, static and shelter-seeding steps to the publish targets so a fresh deploy does not need them by hand.

Once Shivansh's `pipeline/` outputs exist, point `JT_LOCAL_DATA` at them and re-run
`make -C routing precompute && make -C routing hero WRITE_MANIFEST=1 && make -C alerts predraft`, then publish again.

## Follow-on integration branch (2026-10-10; not yet deployed)

The current integration branch adds a third SAM Lambda for the ML read API, with forecast, flood, model-card, and
what-if routes backed by the private data bucket. `ml/scripts/publish_artifacts.py` provides a dry-run-first,
non-deleting upload path for the tracked `ml/out/` artifacts. The forecast endpoint selects the latest issued
forecast at or before the requested timestamp, while flood and what-if responses return short-lived presigned
asset URLs.

The six operational routes (shelter patch, report upload, dispatch draft/approve/list/ack) are configured for
AWS IAM authorization; public read routes remain public. These template changes have not been deployed to the
existing `jt-demo` stack. The AWS Core session currently identifies as the account root user and local AWS/SAM
CLIs are unavailable, so do not promote this branch until deployment is performed through a least-privilege
deployment role and the updated API and signed asset links are smoke-tested.

## Deviations (declared)

- `EvacuationPlan` gains `t_submersion_earliest` / `t_submersion_latest` (the §11.8-3 `earliest`/`latest`) and the
  optional `ext` block. `DispatchCard.validation` gains `failed_checks`, `fallback_fields` and `source`, and
  `alert_type` gains `SHELTER_IN_PLACE` (§11.8-2). All additive, see [`CONTRACT_ADDITIONS.md`](CONTRACT_ADDITIONS.md).
- PREPARE is drafted only for colonies that have a plan, because it needs a shelter. Colonies without a plan get no PREPARE.
- `POST /dispatches/{id}/ack` is implemented as POST-only (plan: Could). `POST /ask` remains Won't.
- Trap counting uses the stricter "the walker *enters* an already-impassable edge" test, so the headline number is
  conservative. `avoid[]` uses the router's safety rule (`exit + 30 min > close_at`).
