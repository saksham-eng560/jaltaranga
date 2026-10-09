# Jaltaranga — Shared Resources & Contracts

> **Source of truth for all four workstreams.** If you need to change anything in this file, raise it in the team channel first and update this file on `main` in the same PR. Workstream plans live on `feature/<name>` branches as `IMPLEMENTATION_PLAN.md`.

**Project:** Jaltaranga — Predict. Route. Protect. (Track 02: Heat and Water)
**Team:** ChaapSeekers — Arjav, Vaibhav, Shivansh, Saksham
**Hackathon:** Bharat Builds Tour 2026 · WeMakeDevs × AWS Environmental Hacks, Oct 8–11, 2026 (3-minute recorded demo, no live demo)

---

## 1. Ground truth we all use

| Fact | Value | Use |
|---|---|---|
| Reference gauge | CWC **Delhi Railway Bridge (Old Railway Bridge)**, station code `CWC_015-UYDDEL` on Google Flood Hub | The "city" water level everyone quotes |
| Warning level | **204.50 m** | Amber status trigger |
| Danger level | **205.33 m** | Red status trigger |
| Evacuation level | **206.00 m** (Delhi evacuation begins) | Dispatch trigger |
| Record (HFL) | **208.66 m on 13 Jul 2023** (prev. 207.49 m, 1978) | Primary replay scenario |
| 2025 peak | ~**207.43 m on 3 Sep 2025**; >14,000 evacuated | Secondary/validation scenario |
| 2023 evacuation | >25,000 people evacuated | Impact slide |
| Upstream release point | Hathnikund Barrage (Haryana), ~48–72 h travel time to Delhi | Lead-time story |
| Helplines | **1077** (district disaster control), **112** (emergency) | Only numbers allowed in alerts |

Every number a user sees comes from code or from this table — never from the LLM.

## 2. Scope decision (applies to everyone)

- **Demo is replay-first.** No flood is happening in October, so the demo runs the **July 2023 event** on a simulated clock (`scenario_id = "yamuna-2023-07"`). We may add a live mode that shows the current gauge reading, but it is optional.
- **Pilot corridor:** Wazirabad Barrage → Okhla Barrage, about 1–2 km either side of the river. Bounding box (WGS84): `[77.20, 28.53, 77.33, 28.75]` (minLon, minLat, maxLon, maxLat).
- **Every risky component needs a degrade path:** GAT → lag-regression baseline → persistence. MapLibre 2.5D terrain → flat 2D. Bedrock → template message. SMS → email/in-app.
- **"One feature that runs beats five that almost do."** The *Must* path is: replay clock → water level forecast → flood mask → road cutoffs → safe route → validated Hindi alert → map. Everything else is extra.

## 3. Repository layout (one top-level folder per owner, which avoids merge conflicts)

```
/
├── shared/                 # Owned jointly; changes via PR to main only
│   ├── schemas/            # JSON Schemas (source of truth for §5)
│   ├── fixtures/           # Tiny sample payloads for every schema (for mocks/tests)
│   └── py/jt_shared/       # Python package: pydantic models, constants (§1), naming helpers
├── frontend/               # Arjav     — React + Vite + MapLibre GL PWA
├── ml/                     # Vaibhav   — GAT forecaster, conformal intervals, inundation mapper
├── pipeline/               # Shivansh  — ingestion, cleaning, DEM/OSM processing, replay builder
├── infra/                  # Shivansh  — AWS SAM template(s), deploy scripts
├── routing/                # Saksham   — road cutoff + evacuation routing
├── alerts/                 # Saksham   — Bedrock dispatch, validator, Polly, SNS
└── docs/                   # Demo script, blog draft, architecture diagram
```

## 4. AWS resource naming & configuration

- **Pattern:** `jt-<env>-<component>-<resource>`, where `env ∈ {dev, demo}`. Examples: `jt-demo-data-bucket`, `jt-demo-forecast-fn`, `jt-demo-alerts-table`.
- **Tags on every resource:** `project=jaltaranga`, `owner=<name>`, `env=<env>`.
- **Primary region:** `ap-south-1` (Mumbai).
- **Bedrock region:** check on Day 1 whether the chosen Nova model can be invoked from `ap-south-1`. If it can't, use a **cross-region inference profile** or call `us-east-1`. Set this with the env var `JT_BEDROCK_REGION` and never hard-code it. Default model id comes from `JT_BEDROCK_MODEL_ID` (Nova Micro preferred; Nova Lite if Hindi quality is poor).
- **Polly:** voice `Kajal` (neural, hi-IN + en-IN), engine `neural`, region `ap-south-1`.
- **Budget:** an AWS Budget alarm at USD 10 is created on Day 1. No NAT gateways, no always-on EC2, no SageMaker endpoints. Training happens locally or in Colab, and inference runs in Lambda (ONNX/NumPy or slim PyTorch in a container image).
- **SMS:** sending SMS in India requires DLT sender/template registration, so the demo uses **SNS email + in-app inbox**. SMS/WhatsApp is documented as a post-hackathon step.
- **Secrets:** no keys in git. Use SSM Parameter Store `/jt/<env>/<name>`.

### Shared AWS resources (created by Shivansh in `infra/template.yaml`)

| Resource | Name | Notes |
|---|---|---|
| S3 data bucket | `jt-<env>-data-<accountid>` | Layout in §6 |
| CloudFront | in front of the Amplify app + `tiles/` prefix of the data bucket | |
| HTTP API (API Gateway v2) | `jt-<env>-api` | Routes in §7 |
| DynamoDB | `jt-<env>-colonies`, `jt-<env>-shelters`, `jt-<env>-dispatches`, `jt-<env>-reports`, `jt-<env>-scenario-state` | Single-table not required; on-demand billing |
| EventBridge Scheduler | `jt-<env>-tick` | Every 5 min in live mode; replay ticks are driven by the API |
| SNS topic | `jt-<env>-dispatch` | Email subscriptions for the demo |
| Amplify app | `jt-<env>-web` | Hosts `frontend/` |

Each owner adds their own Lambdas to the SAM template under a clearly commented section (`# --- routing (Saksham) ---`), which keeps merge conflicts limited to append-only hunks.

## 5. Data schemas (canonical; JSON Schema files live in `shared/schemas/`)

All times are ISO-8601 with an explicit `+05:30` offset. All coordinates are WGS84 `[lon, lat]`. Water levels are in **metres above MSL** (CWC convention); depths are in metres above ground.

### 5.1 `GaugeReading` (pipeline → ml)
```json
{ "station_id": "DELHI_RLY_BRIDGE", "ts": "2023-07-13T10:00:00+05:30",
  "level_m": 208.48, "discharge_cumecs": null, "source": "cwc|floodhub|digitized|synthetic",
  "qc_flag": "ok|imputed|suspect" }
```
Canonical station ids: `HATHNIKUND`, `KALANAUR`, `MAWI`, `PALLA`, `WAZIRABAD`, `DELHI_RLY_BRIDGE`, `ITO`, `OKHLA`. Anyone can add new ids in `shared/py/jt_shared/stations.py`.

### 5.2 `ForecastNode` (ml → routing, frontend)
```json
{ "scenario_id": "yamuna-2023-07", "issued_at": "...", "station_id": "DELHI_RLY_BRIDGE",
  "horizon_h": 6, "valid_at": "...", "level_m": 207.9, "lo_m": 207.5, "hi_m": 208.3,
  "coverage": 0.8, "model": "gat-v1|lagreg-v1|persistence" }
```
Horizons: **1, 3, 6, 12, 24 h**. `lo_m`/`hi_m` are split-conformal bounds at the stated coverage.

### 5.3 `FloodSurface` (ml → routing, frontend)
- Raster: Cloud-Optimized GeoTIFF of **depth in metres**, EPSG:4326, about 30 m pixels, written to `s3://…/scenarios/<scenario_id>/depth/<valid_at>.tif`
- Vector: polygon GeoJSON (depth > 0.05 m) written to `…/depth/<valid_at>.geojson`
- Index: `…/depth/index.json` → `[{ "valid_at", "tif", "geojson", "level_m_ref" }]`

### 5.4 `RoadSegmentStatus` (routing → frontend, alerts)
```json
{ "edge_id": "osm:123456789:0", "status": "green|amber|red",
  "depth_m": 0.12, "cutoff_at": "2023-07-13T02:00:00+05:30", "reason": "depth>0.3m|forecast_cutoff<2h" }
```
Rules: **red** if depth > **0.30 m** now. **Amber** if it is forecast to exceed 0.30 m within 2 h (using `hi_m`). Otherwise **green**.

### 5.5 `Colony`, `Shelter` (pipeline seeds → DynamoDB; read by everyone)
```json
{ "colony_id": "DEL-YP-04", "name_en": "Yamuna Pushta Sector C", "name_hi": "यमुना पुश्ता सेक्टर सी",
  "centroid": [77.245, 28.655], "population_est": 4200, "ground_elev_m": 205.1,
  "vulnerable": { "elderly": 310, "disabled": 45, "children_u5": 520, "pregnant": 60 },
  "contacts": [{ "role": "pradhan", "name": "…", "channel": "email|sms", "address": "…" }] }
```
```json
{ "shelter_id": "SH-KG-01", "name_en": "Kashmiri Gate Community Hall", "name_hi": "कश्मीरी गेट सामुदायिक भवन",
  "location": [77.229, 28.667], "ground_elev_m": 213.0, "capacity": 400, "occupied": 150,
  "type": "school|community_hall|relief_camp|medical", "updated_at": "…" }
```
Demo contact data is **synthetic**. Never commit real phone numbers.

### 5.6 `EvacuationPlan` (routing → alerts, frontend)
```json
{ "scenario_id": "...", "colony_id": "DEL-YP-04", "computed_at": "...",
  "t_submersion": "2023-07-13T04:30:00+05:30", "lead_time_h": 3.5,
  "primary": { "shelter_id": "SH-KG-01", "route_geojson": {…}, "distance_m": 2100, "walk_min": 32,
               "via_names_en": ["Lal Kuan lane"], "via_names_hi": ["लाल कुआं मार्ग"], "max_depth_m": 0.0 },
  "backup":  { … same shape … } | null,
  "avoid":   [{ "name_en": "Ring Road", "name_hi": "रिंग रोड", "cutoff_at": "2023-07-13T02:00:00+05:30" }],
  "priority": 0.87 }
```

### 5.7 `DispatchCard` (alerts → frontend, SNS)
```json
{ "dispatch_id": "uuid", "plan_ref": { "scenario_id": "...", "colony_id": "...", "computed_at": "..." },
  "alert_type": "URGENT_EVACUATION_DISPATCH|PREPARE|ALL_CLEAR",
  "message_hi": "…", "message_en": "…", "sms_hi": "≤ 160 chars incl. 1077",
  "audio_url_hi": "s3 presigned | null",
  "validation": { "passed": true, "checks": ["numbers_match","names_match","phones_whitelist","length"], "fallback_used": false },
  "status": "draft|approved|sent|acknowledged", "approved_by": "officer-demo", "ts": "..." }
```

### 5.8 `FieldReport` (frontend → alerts/routing; crowdsourced)
```json
{ "report_id": "uuid", "ts": "...", "location": [lon, lat], "kind": "water_depth|road_blocked|shelter_full|sos",
  "depth_cm": 40, "photo_key": "s3 key | null", "reporter_id": "anon-hash", "trust": 0.0-1.0, "verified": false }
```

## 6. S3 layout (`jt-<env>-data-<acct>`)

```
raw/<source>/<yyyy>/<mm>/…                 # untouched downloads (pipeline)
clean/gauges/<station_id>.parquet          # hourly GaugeReading (pipeline)
static/dem/corridor_cop30.tif              # clipped Copernicus GLO-30 (pipeline)
static/osm/corridor_roads.graphml          # OSMnx drive+walk graph (pipeline)
static/osm/roads.geojson                   # same, for the map (pipeline)
static/colonies.geojson, static/shelters.geojson
models/<model>/<version>/…                 # ml artefacts (ml)
scenarios/<scenario_id>/manifest.json      # timeline: start, end, step, available valid_at list
scenarios/<scenario_id>/forecasts/<issued_at>.json   # [ForecastNode] (ml)
scenarios/<scenario_id>/depth/…            # FloodSurface (ml)
scenarios/<scenario_id>/roads/<valid_at>.json        # [RoadSegmentStatus] (routing)
scenarios/<scenario_id>/plans/<valid_at>.json        # [EvacuationPlan] (routing)
tiles/…                                    # PMTiles / terrain tiles for the frontend (pipeline/frontend)
uploads/reports/<report_id>.jpg            # FieldReport photos (frontend → alerts)
```

**Precompute principle:** the heavy steps (forecast, inundation, routing for every replay timestep) run **offline** and write to `scenarios/`. Lambdas mostly serve, filter and validate, which keeps the demo fast and cheap. A "recompute now" endpoint exists for live mode.

## 7. HTTP API contract (`jt-<env>-api`, JSON, CORS for the Amplify domain)

| Method & path | Owner | Returns |
|---|---|---|
| `GET /scenarios` | Shivansh | list of manifests |
| `GET /scenarios/{id}/timeline` | Shivansh | manifest (valid_at list) |
| `GET /scenarios/{id}/gauges?at=` | Shivansh | `[GaugeReading]` observed up to `at` |
| `GET /scenarios/{id}/forecast?at=` | Vaibhav | `[ForecastNode]` issued at/just before `at` |
| `GET /scenarios/{id}/flood?at=` | Vaibhav | `{ tif_url, geojson_url, level_m_ref }` |
| `GET /scenarios/{id}/roads?at=` | Saksham | `[RoadSegmentStatus]` (non-green only by default) |
| `GET /scenarios/{id}/plans?at=` | Saksham | `[EvacuationPlan]` sorted by priority |
| `POST /scenarios/{id}/colonies/{cid}/dispatch?at=` | Saksham | `DispatchCard` (draft) |
| `POST /dispatches/{dispatch_id}/approve` | Saksham | `DispatchCard` (sent) |
| `GET /dispatches?scenario_id=` | Saksham | `[DispatchCard]` |
| `GET /shelters`, `PATCH /shelters/{id}` | Saksham | `Shelter` |
| `POST /reports` (presigned upload) | Arjav (UI) / Saksham (handler) | `FieldReport` |
| `GET /health` | Shivansh | `{ ok, version, bedrock_region }` |

Errors use `{ "error": { "code": "…", "message": "…" } }` with the proper HTTP status. Each team member exposes mock JSON in `shared/fixtures/` **by end of Day 2**, so the frontend never waits on a backend.

## 8. Shared utilities (`shared/py/jt_shared/`)

- `constants.py`: thresholds from §1, depth cutoff 0.30 m, horizons, bounding box, helplines.
- `models.py`: pydantic v2 models for every schema in §5. These are the single source; JSON Schemas are exported from them with `python -m jt_shared.export_schemas`.
- `naming.py`: `resource_name(component, resource, env)`, `s3_key(kind, **parts)`.
- `timeutil.py`: IST helpers, `snap_to_step(at, step_min=60)`.
- `io.py`: `read_json_s3`, `write_json_s3`, `read_cog_window`. Each takes a local-filesystem fallback via `JT_LOCAL_DATA=./data` so everything runs offline without AWS.
- Frontend mirror: `frontend/src/shared/types.ts` is generated from `shared/schemas/*.json` using `json-schema-to-typescript`.

## 9. Integration test requirements

1. **Schema conformance:** every producer validates its outputs against `shared/schemas/` in CI (`pytest -k schema`).
2. **Replay end-to-end (golden test):** for `yamuna-2023-07` at `2023-07-13T00:00+05:30`:
   - the forecast for `DELHI_RLY_BRIDGE` at h=6 exists and `lo_m ≤ level_m ≤ hi_m`
   - the flood GeoJSON is non-empty and intersects Yamuna Pushta
   - at least one colony gets an `EvacuationPlan` whose `primary.max_depth_m ≤ 0.30`
   - **zero** primary routes pass through a red edge
   - the `DispatchCard` validation passes, `sms_hi` is ≤ 160 chars, and the only phone numbers are 1077 or 112
3. **Hallucination test:** when 20 generated dispatches are fed through the validator, every number, time, place name and phone number must be traceable to the `EvacuationPlan`. On failure, `fallback_used=true` and the template message is used.
4. **Offline test:** with `JT_LOCAL_DATA` set and no AWS credentials, `make replay-local` produces all scenario artefacts.
5. **Frontend smoke:** Playwright loads the app, scrubs the timeline to T+6 h, sees red roads and one dispatch card.

## 10. Branch & merge conventions

- Branches: `feature/arjav`, `feature/vaibhav`, `feature/shivansh`, `feature/saksham`, all branched from `main`.
- Only touch your own top-level folder(s). `shared/` and `infra/template.yaml` changes go through small PRs to `main`, which teammates review within 2 h.
- Commit style: `<area>: <imperative summary>` (e.g. `routing: add amber cutoff rule`).
- Merge order and the integration timeline are in `INTEGRATION_PLAN.md`.
