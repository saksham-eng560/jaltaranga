# Jaltaranga — Predict. Route. Protect.

Jaltaranga is a replay-first flood evacuation decision-support project for the
Yamuna floodplain in Delhi. It turns river-level observations and forecasts
into street-level flood exposure, safer walking routes to available shelters,
and validated public dispatches. The project was built by team ChaapSeekers
for Bharat Builds Tour 2026, WeMakeDevs × AWS Environmental Hacks (Track 02:
Heat and Water).

The primary demonstration replays the July 2023 Yamuna flood on a simulated
clock. Local fixture mode is available without AWS credentials or a running
backend.

## Project at a glance

The system is composed of offline data and decision pipelines, an optional
AWS-hosted API, and a progressive web frontend:

1. **Prepare data:** `pipeline/` builds and records provenance for corridor
   geography, elevation, gauge, rainfall, infrastructure, and replay inputs.
2. **Forecast and map flooding:** `ml/` generates gauge forecasts, uncertainty
   intervals, flood surfaces, and colony-level wet/cutoff thresholds.
3. **Route and alert:** `routing/` estimates road closures, computes safe
   evacuation plans, and assigns shelter capacity. `alerts/` prepares
   code-grounded Hindi/English dispatches and validates them before approval.
4. **Inform residents and officers:** `frontend/` presents live or replay
   operations, a map, plans, dispatch review, reports, comparisons, and
   offline Colony Packs.

Every stage has a local-fixture or degraded mode. The LLM does not provide
operational facts: names, numbers, times, routes, and helplines are supplied
and checked by code. Only the approved helplines 1077 and 112 are used.

## Repository layout

| Path | Purpose |
|---|---|
| `frontend/` | React, TypeScript, Vite and MapLibre PWA; officer and resident views |
| `pipeline/` | Geospatial/data ingestion, embankment-aware DTM, provenance ledger, infrastructure exposure, scenario replay |
| `ml/` | Forecasting, uncertainty, flood inundation and what-if outputs/API |
| `routing/` | Road status, time-dependent evacuation routes, shelter assignment and safety invariants |
| `alerts/` | Dispatch lifecycle, fact-slot rendering, validation, optional Bedrock/Polly/SNS integrations |
| `shared/` | Canonical Python contracts, JSON Schemas, and test fixtures |
| `data/` | Bunds, corridor inputs, scenarios, published exclusions, and sample outputs |
| `infra/` | AWS SAM templates, component sections, and deployment scripts |
| `tests/` | Repository-level and pipeline integration tests |
| `docs/` | Workstream plans, handoffs, integration guidance, and project documentation |
| `PROJECT_SUMMARY.md` | Product scope, architecture, roles, and feature overview |
| `SHARED_RESOURCES.md` | Canonical data/API contracts and shared project assumptions |
| `INTEGRATION_PLAN.md` | Integration, validation, and deployment guidance |

## Run the frontend locally

Requirements: Node.js (see `frontend/package.json`) and npm.

```bash
cd frontend
npm ci
npm run dev
```

Open the local URL printed by Vite (normally `http://localhost:5173`). The
included July 2023 fixtures let you explore the blue-and-white operations
console, historical replay, map and route views, dispatch preview, reports,
comparison, and saved Colony Pack without a backend. Live API and basemap
configuration are optional; map data falls back to the selected plan geometry.

To build and test the frontend:

```bash
cd frontend
npm run build
npm test
npm run e2e
```

The end-to-end command uses Playwright and may require its browser binaries to
be installed in the development environment.

## Run the offline Python workflows

Python components document their own supported versions and optional
dependencies. In particular, routing, alerts, and the shared package require
Python 3.12 or newer; the ML package supports Python 3.11 or newer. Use a
virtual environment and install only the component dependencies needed:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r routing/requirements-offline.txt
python -m pip install jsonschema
```

Run the synthetic routing demonstration (offline, no AWS credentials):

```bash
make -C routing demo-local
```

Run focused component tests:

```bash
make -C routing test
make -C alerts test
python -m pytest -q
```

The repository pytest configuration covers shared contracts, routing, alerts,
ML, and infrastructure tests. Additional pipeline test files are under
`tests/`; some are legacy checks for an earlier shared-package layout and are
not part of the configured default suite.

Additional workflows and dependency setup are documented in
[`pipeline/README.md`](pipeline/README.md),
[`routing/README.md`](routing/README.md), and
[`alerts/README.md`](alerts/README.md). The ML package defines its optional
development dependencies in `ml/pyproject.toml`.

The pipeline replay CLI is available as:

```bash
python -m pipeline.replay --scenario yamuna-2023-07
```

This pipeline may fetch the Copernicus elevation tile and ERA5 rainfall data
when their local caches are missing. Review its source-data notes and run it
only when those inputs are available. Routing and alert demos have a separate
synthetic offline workflow documented in their component READMEs.

## Configuration and deployment

Local fixture mode is the recommended first run. Live backend configuration
is supplied through frontend build-time variables; see
[`frontend/README.md`](frontend/README.md) and
`frontend/.env.example`. Never commit credentials or production secrets.

The AWS architecture and resource naming conventions are in
[`SHARED_RESOURCES.md`](SHARED_RESOURCES.md); deployment and integration gates
are in [`INTEGRATION_PLAN.md`](INTEGRATION_PLAN.md) and `infra/`. Cloud
deployment, Bedrock, Polly, SNS delivery, and publishing artefacts require
appropriate AWS configuration and permissions and are not necessary to run
the local demo.

## Operational safety and limitations

- This is a prototype and decision-support tool, not an official warning
  system or a substitute for local authorities and emergency services.
- Fixture and synthetic results must be visibly treated as such; do not
  present them as live measurements or validated forecasts.
- Flood depths, DEM calibration, road connectivity, shelter capacity, and
  forecast quality depend on source data and must be independently validated
  before operational use.
- The historical replay is simulated. Live mode requires correctly configured
  and validated data services.
- Dispatches are drafts until reviewed and approved by an authorized operator.
- The system uses 1077 (district disaster control) and 112 (emergency) as its
  helplines. Follow current official guidance in an actual emergency.

## Further reading

- [`PROJECT_SUMMARY.md`](PROJECT_SUMMARY.md) — features and system architecture
- [`SHARED_RESOURCES.md`](SHARED_RESOURCES.md) — canonical contracts, schemas,
  conventions, and assumptions
- [`INTEGRATION_PLAN.md`](INTEGRATION_PLAN.md) — integration and validation
  strategy
- [`frontend/README.md`](frontend/README.md) — frontend configuration and use
- [`pipeline/README.md`](pipeline/README.md) — data pipeline modules
- [`routing/README.md`](routing/README.md) — routing inputs, outputs, and safety
- [`alerts/README.md`](alerts/README.md) — dispatch validation and integrations
