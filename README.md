# Jaltaranga — Predict. Route. Protect.

Flood evacuation intelligence for the Yamuna corridor in Delhi. Built by team **ChaapSeekers** (Arjav, Vaibhav, Shivansh, Saksham) for Bharat Builds Tour 2026 · WeMakeDevs × AWS Environmental Hacks (Track 02: Heat and Water).

| Doc | What it is |
|---|---|
| [`PROJECT_SUMMARY.md`](PROJECT_SUMMARY.md) | Enhanced overview, architecture, owners, timeline, risks, metrics |
| [`SHARED_RESOURCES.md`](SHARED_RESOURCES.md) | Contracts every workstream builds against: schemas, API, S3, AWS naming |
| [`INTEGRATION_PLAN.md`](INTEGRATION_PLAN.md) | Merge order, integration tests, deployment, demo-video script |

Workstream plans and quality reviews are grouped by owner under `docs/workstreams/<owner>/`. The separate folders let all four workstreams merge without overwriting one another.

## Routing & Alerting (Saksham)

| Path | What |
|---|---|
| [`routing/`](routing/README.md) | Road cutoffs (red/amber), time-dependent safe walking routes, capacity-aware shelter assignment (greedy + OR-Tools), avoid list + "death-trap" counterfactual, `T_hero` |
| [`alerts/`](alerts/README.md) | Slot-filled Bedrock Nova dispatch ("the LLM never types a fact"), 6-check validator, templates, Polly Kajal, SNS, dispatch log |
| `shared/py/jt_shared`, `shared/schemas`, `shared/fixtures` | Contract package (pydantic models for SHARED §5/§11), exported JSON Schemas, fixtures from the real writers |
| `infra/sections/routing_alerts.yaml` | Append-only SAM block for the two Lambdas |
| [`docs/workstreams/saksham/STATUS.md`](docs/workstreams/saksham/STATUS.md) | What is built and tested vs the plan, and what still needs AWS |

```bash
pip install -r routing/requirements-offline.txt jsonschema
pytest                              # 136 tests: invariants, validator mutations, handlers, schemas
make -C routing demo-local          # synthetic dev world → precompute → T_hero → predraft, offline, ~25 s
```
