# Jaltaranga — Shared Resources & Contracts

> **Source of truth for all four workstreams.** If you need to change anything in this file, raise it in the team channel first and update this file on `main` in the same PR. Workstream plans live on `feature/<name>` branches as `IMPLEMENTATION_PLAN.md`.

**Project:** Jaltaranga — Predict. Route. Protect. (Track 02: Heat and Water) · **Contract version: v1.2** (§11)
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
| Record (HFL) | **208.66 m on 13 Jul 2023** (prev. 207.49 m, 1978). 208.53 m at 10:00 on 13 Jul; the hour of the peak is **unverified**, so the manifest `peak` event carries `ts_verified:false` until a CWC bulletin confirms it | Primary replay scenario |
| 2025 peak | **207.48 m at ~06:00 on 4 Sep 2025** (SANDRP/Tribune; some outlets reported 207.43 m at 22:00 on 3 Sep); >14,000 evacuated | Secondary/validation scenario |
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
2. **Replay end-to-end (golden test):** for `yamuna-2023-07` at `manifest.default_at` (= `T_hero`, see §11.8-1):
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

---

## 11. Contract amendments v1.1 (agreed after the quality reviews, Fri Oct 9)

These changes are **additive**. Where they conflict with an earlier section, they win.

### 11.1 Vertical datum: one owner
- **Shivansh** ships `static/dem/corridor_dtm.tif` on **EGM2008 (Δ = 0)**: Copernicus GLO-30 (or FABDEM if it downloads in time) with embankment burn-back. Bridges are kept off the flood DEM and recorded on graph edges as `is_bridge`, `elev_min_m`. He also ships one merged `static/dem/calib_points.csv` (≥ 15 wet + ≥ 15 dry overbank points with reasons; ITO, the Supreme Court area and Rajghat are excluded because that flooding was Drain No. 12 backflow).
- **Vaibhav** (`ml/inundation/calibrate.py`) is the **only** place that fits the offset δ and the water-surface slope S. Everyone else (Shivansh's infra-exposure layer, the roads envelope, Saksham's cutoffs) uses Vaibhav's `onset.tif` / `cutoff_0p30.tif` and never applies "level − ground_elev_m" on their own.

### 11.2 New S3 artefacts (§6)
```
static/dem/corridor_dtm.tif, static/dem/meta.json, static/dem/calib_points.csv      # Shivansh
static/osm/river.geojson, static/osm/centreline.geojson                             # Shivansh (by Fri 18:45)
models/inundation/v1/onset.tif      # float32, metres at DRB gauge level at which the cell first gets wet (nodata = never)
models/inundation/v1/cutoff_0p30.tif# float32, DRB gauge level at which depth > 0.30 m  (= max(onset, z' + 0.30))
models/inundation/v1/colony_thresholds.json  # [{colony_id, wet_at_level_m, cutoff_at_level_m, buffer_m:150}]
models/registry.json, models/<model>/<ver>/metrics.json, MODEL_CARD.md
scenarios/<id>/gauges.json, provenance.json, infra/<valid_at>.json                   # Shivansh
scenarios/<id>/plans/<t>.unreachable.json  # [{colony_id, reason, population}]  (shown in the UI as "boat / NDRF needed")
scenarios/<id>/plans/<t>.candidates.json, routing/trap_summary.json                 # Saksham
audio/<sha256>.mp3                                                                  # Saksham (Polly cache)
tiles/basemap/delhi.pmtiles, tiles/terrain/{z}/{x}/{y}.png                          # Arjav/Shivansh
```

### 11.3 Schema changes (§5)
- `GaugeReading.level_m` and `discharge_cumecs` are both **nullable**, and at least one must be set. `source` gains `glofas`. New optional fields: `source_ref` (id into `manifest.sources`) and `note`. The pipeline never synthesises levels. Synthetic upstream levels stay inside `ml/` with `source="synthetic"`.
- **Manifest** (`scenarios/<id>/manifest.json`): `{scenario_id, mode, title_en, title_hi, start, end, step_min, valid_at[], issued_at[], default_at, ref_station, thresholds{warning,danger,evacuation,hfl}, events[{kind,ts,level_m,ts_verified}], artefacts{gauges,forecasts,depth,roads,plans,infra: real|fixture|missing}, context?, sources[], built_at, git_sha, data_version}`. Replay window: `2023-07-09T00:00+05:30` → `2023-07-16T23:00+05:30`, step 60 min.
- `FloodSurface` GeoJSON polygons carry `depth_class ∈ {"0.05-0.3","0.3-1","1-2",">2"}`. `GET /flood` also returns `valid_at`.
- **`edge_id` is direction-agnostic**, `osm:<min(u,v)>:<max(u,v)>:<key>`. The u→v and v→u edges share it. `static/osm/roads.geojson` is the *flood envelope* (major roads plus every edge that can ever flood, ≤ 8 MB), and every `RoadSegmentStatus.edge_id` must join to it (join test in CI). Graph edges also carry `name`, `name:hi`, `highway`, `foot_ok`, `is_bridge`, `elev_min_m`.
- `EvacuationPlan.avoid[]` also carries `edge_ids[]`, so the UI can highlight a whole named road such as Ring Road and not just a single edge.
- `Shelter` gains `free_beds` (maintained as `capacity − occupied`).

### 11.4 API changes (§7)
| Method & path | Owner | Notes |
|---|---|---|
| `GET /colonies` | Shivansh | Colony list **without `contacts`** (public map) |
| `POST /reports` | Saksham | Returns `{ report: FieldReport, upload: { url, fields } \| null }` (presigned POST, ≤ 1 MB JPEG, 5 min) |
| `PATCH /shelters/{id}` | Saksham | Body `{delta}`. DynamoDB `UpdateExpression: ADD occupied :d, free_beds :neg` with `ConditionExpression: free_beds >= :d`. Arithmetic is not allowed inside DynamoDB conditions. Returns 409 when full |
| `GET /scenarios/{id}/whatif?level_m=` | Vaibhav (Should) | Colonies and roads that are wet or cut at a hypothetical DRB level (ladder lookup) |
| `GET /models/card` | Vaibhav (Should) | registry + metrics |
| `GET\|POST /dispatches/{id}/ack` | Saksham (Should) | Acknowledgement link |
| `POST /ask` | Saksham (Could) | Strands "Ask Jaltaranga" agent |

**Data-access ladder (frontend):** `GET`s read precomputed JSON from CloudFront `scenarios/*` and `static/*` first, then fall back to `shared/fixtures/`. The HTTP API is **required** only for dispatch draft/approve, reports and shelters. If any Lambda is down, the recorded demo still works.

### 11.5 Make-target contract (§9.4)
Each target takes `SCENARIO=<id>`, reads and writes only under `$JT_LOCAL_DATA`, needs no AWS credentials, and exits non-zero on failure:
`make -C pipeline scenario` → `make -C ml replay-local` → `make -C routing precompute` → `make -C alerts predraft`. Root `make replay-local` runs them in that order and records `manifest.artefacts`.

### 11.6 Operational decisions
- **Bedrock probe (Fri, Saksham):** first run `aws bedrock list-inference-profiles --region ap-south-1`. Then try a global Nova profile (e.g. `global.amazon.nova-2-lite-v1:0`), then `us.amazon.nova-micro-v1:0` in `us-east-1`. Record the result in `JT_BEDROCK_REGION` / `JT_BEDROCK_MODEL_ID`.
- **Alert text is slot-filled:** the LLM chooses wording and structure, and code substitutes every fact slot (`{SHELTER}`, `{VIA}`, `{AVOID}`, `{LEAD}`, `{TSUB}`, `{HELP}`). The validator rejects any Latin token or landmark noun that is not in the plan's gazetteer.
- **SNS:** the email `Subject` is ASCII English and under 100 chars. Hindi goes in the body only. Email subscriptions are confirmed during deploy.
- **Draft Lambda deadline:** 18 s wall clock in total. The repair call and Polly are skipped when the budget runs low (the API Gateway HTTP API limit is 30 s).
- **Amplify monorepo:** the build spec lives at the repo root (`amplify.yml` with `appRoot: frontend`) or in the console, with `AMPLIFY_MONOREPO_APP_ROOT=frontend`. S3 CORS allows GET from the Amplify origin.
- **Hero colony:** Yamuna Pushta (`DEL-YP-04`), with a backup hero colony picked on Sat morning in case its routes are all red at the demo timestamp.
- **Evaluation honesty:** forecast skill is reported only on anchors that were **not** used for calibration or model selection, using causal inputs (no data later than the issue time). The champion rule is fixed in advance: lowest held-out MAE at h = 6, and GAT must beat lag-regression to be used.

### 11.7 Team checkpoints (go / no-go)
| When | Checkpoint | If missed |
|---|---|---|
| **Fri 23:00** | Fixtures for every schema are in `shared/fixtures/`. The v1.1 contract PR is merged | Frontend builds on what exists; owners post their ETA |
| **Sat 14:00** | Precomputed forecasts, depth, roads and plans for the demo window (13 Jul 00:00–06:00) are in S3 | Record the video from static or fixture data. Stop new integration at 17:30 |
| **Sat 20:00** | **Feature freeze.** Only bug fixes and polish after this | — |
| **Sun 09:00** | Golden test (§9.2) on `demo` | Fix the blockers only |
| **Sun 13:00–14:30** | Record the demo video (3 min) | The recording takes priority over everything |
| **Sun (deadline − 2 h)** | Submit: video, repo, blog | — |

### 11.8 Cross-plan resolutions v1.2 (from the second review round)

1. **The demo/golden timestamp is chosen from data, not hard-coded.** At `2023-07-13T00:00+05:30` the DRB gauge was already around 208 m, so low colonies were already wet and the "countdown" story falls apart. New rule: **`T_hero`** is the latest replay step at which the hero colony is still dry, with `2 h ≤ lead_time_h ≤ 6 h` and at least one feasible primary route. Saksham computes it on **Fri 23:00** from Vaibhav's v0 `colony_thresholds.json` and writes it to `manifest.default_at` (via Shivansh). It is expected around 11–12 Jul 2023. The golden test (§9.2), the storyboard and Director mode all use `manifest.default_at` and never a literal time. The backup hero colony is chosen the same way at the same time.
2. **Already-wet colonies** get an `alert_type: "SHELTER_IN_PLACE"` template (move to upper floor or roof, call 1077/112, NDRF boat request) and are listed in `unreachable.json` with `reason: "already_wet"`. Routing starts from the nearest *dry* graph node within 300 m of the centroid, or the colony is marked unreachable.
3. **Time-to-water definitions** (single source: Saksham's plan builder): `t_submersion` = the first forecast time where central `level_m ≥ wet_at_level_m`; `earliest` = first time `hi_m ≥ wet_at_level_m`; `latest` = first time `lo_m ≥ wet_at_level_m` (null if none within 24 h). `lead_time_h = t_submersion − at`. The frontend renders these fields and never recomputes them. The forecast curve used for these times starts at `max(observed_now, forecast)`.
4. **Amber uses a window maximum:** an edge is amber if `max(hi_m over (t, t+2h])` reaches its cutoff level. A point sample at t+2 h is not enough.
5. **One per-edge cutoff implementation:** Saksham's `routing/cutoff.py` samples `cutoff_0p30.tif` and writes `static/osm/edge_cutoffs.json` (`{edge_id: cutoff_at_level_m}`). Vaibhav's what-if endpoint reads that file and has no copy of its own.
6. **Bund floor applied in gauge space:** the embankment floor is re-applied *after* Vaibhav calibrates δ/S (`z'_bund ≥ HFL + 0.5 m`). Shivansh ships a separate `static/dem/bund_mask.tif` and does not bake an absolute 210 m into the DTM. The bund name selector must exclude polygons that intersect any colony footprint, so it doesn't seal Yamuna Pushta dry.
7. **Calibration hygiene:** calibration points must lie inside the bbox and the modelled chainage. The WTP and pump-house points used for the infrastructure-exposure claim are **held out** of calibration, or the claim is labelled "in-sample".
8. **Forecast inputs:** training uses the same causal, sparse-anchor input path as replay, plus an `input_age_h` feature. The press-reported 12 Jul 2023 afternoon and evening anchors go into the gauge series to avoid a 13 h input gap.
9. **Always write optional artefacts:** `plans/<t>.unreachable.json` is always written (it may be `[]`). Behind CloudFront OAC a missing object returns **403**, so the frontend treats 403 and 404 on optional artefacts as "absent". Each replay step resolves **all-or-nothing** from one source (static or fixtures), never a mix. Source chips are shown per layer.
10. **Paths:** `scenarios/<id>/routing/trap_summary.json` (scenario-scoped) and `scenarios/<id>/dispatch_cache/<t>/<colony_id>.json`. In S3 keys, timestamps are the manifest strings verbatim (`YYYY-MM-DDTHH:MM:SS+05:30`), URL-encoded in requests (`%2B05%3A30`).
11. **Bedrock IAM for global/geo inference profiles:** allow `bedrock:InvokeModel` on the inference-profile ARN **and** on `arn:aws:bedrock:*::foundation-model/<model>` (for global profiles AWS documents the condition `aws:RequestedRegion = "unspecified"`). Test with the Lambda role on Friday, not just a user profile.
12. **Frontend deploy mode:** `jt-demo-web` is deployed with a **zip upload** (`infra/deploy_frontend.sh`: `npm run build` → `aws amplify create-deployment`/`start-deployment`). No Git-connected Amplify for the demo. The fallback is `dist/` → S3 `web/` behind CloudFront.
13. **Pins:** only versions that exist and are at least 14 days old (e.g. networkx 3.6.x, not 3.7). Anything newer needs a security reason recorded in the plan.
14. **Spec coverage:** "Volunteer coordination" is **post-hackathon** and goes in the blog's roadmap. For the demo, citizen field reports appear as map pins (Arjav, Could), and report verification and the trust formula are Won't (Saksham's pre-cut). OR-Tools min-cost flow is Should, and the greedy capacity-safe assignment is the Must fallback that satisfies the same invariant (no shelter over its free beds).
