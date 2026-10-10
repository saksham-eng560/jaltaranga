# Jaltaranga — Data Pipeline & AWS Infrastructure (pipeline/, infra/, shared/) — Implementation Plan (owner: Shivansh) — v1.1

> Branch `feature/shivansh` · My folders: `pipeline/`, `infra/`, root `Makefile` (and root `amplify.yml` only if Amplify becomes Git-connected). `shared/` is **jointly owned**; I am its steward and merge contract PRs (INTEGRATION_PLAN §2), but every change is a reviewed PR to `main`.
> Contracts follow **SHARED_RESOURCES v1.1 (SR)**. Where SR §11 differs from §1–§10, **§11 wins** and this plan follows it. Schemas are referenced, never redefined.
> Re-baselined Fri 9 Oct 20:00 (review RC-7). Rows before 19:30 are the committed baseline teammates already build on (Arjav, Vaibhav and Saksham all assume PR #1 at 16:30 and the real curve at 18:45). Any of them not actually done at 20:00 runs next, in row order, and pushes into the Fri buffer. The 2025 scenario is **cut to Could now**, not at a later checkpoint.

## 0. TL;DR

I own the **data foundation** (gauges, DTM, OSM, seeds, replay manifest), the `jt_shared` package, and the **single SAM stack** everyone deploys into. The demo-critical path from my side is: **real ORB curve → manifest → DTM + calib points → graph + roads envelope → seeds → S3/CloudFront serving `static/*` and `scenarios/*`** (SR §11.4 data-access ladder rung 1). My API routes are deployed but are *not* on the recorded-demo path.

| Bucket | Hours |
|---|---|
| Must | 18.75 |
| Should | 1.75 |
| Could | 0 scheduled (2025 replay runs only from Buffer A if every Must is green) |
| **Explicit buffer** | **3.75** (Fri 0.5, Sat 2.5, Sun 0.75) |
| **Focused total** | **24.25**, plus 1.5 h on call during recording (Sun 13:00–14:30) |

Milestones: fixtures + v1.1 merged **Fri 23:00** · DTM + calib points **Sat 10:00** · graph, envelope, seeds **Sat 11:00** · demo stack URLs **Sat 12:30** · go/no-go **Sat 14:00** · first golden run **Sat 18:45** · freeze **Sat 20:00** · golden green **Sun 09:00** · infra freeze **Sun 12:00**.

## 1. Research findings that shape the plan

| Topic | Finding | Consequence | Source |
|---|---|---|---|
| Copernicus GLO-30 on AWS | Public `s3://copernicus-dem-30m` (eu-central-1), unsigned, COG tiles. **Verified from the sandbox (ranged GET → 206).** Bbox (SR §2) is inside tile N28/E077 | Windowed `/vsis3/` read with `AWS_NO_SIGN_REQUEST=YES`; ~470×800 px; no full download | [registry](https://registry.opendata.aws/copernicus-dem/) |
| GLO-30 is a **DSM** on **EGM2008** | Includes buildings and trees; not the CWC gauge datum | DTM step + burn (§3.4). **No offset in my file** (SR §11.1): Vaibhav's `calibrate.py` is the only fitter of δ and slope S | same |
| FABDEM | Forest/building-removed GLO-30, CC BY-NC-SA 4.0, 10°×10° zips from Bristol (multi-GB). No per-tile mirror found | Preferred **only if** the background download finishes by Sat 08:30; otherwise GLO-30 3×3 + burn | [EEA catalogue](https://cis2.eea.europa.eu/data/745) |
| ORB July 2023 levels | No public hourly API. Anchors: 12 Jul 207.00 (04:00), 207.25 (08:00), ~207.5 (11:00); 13 Jul 208.48 (08:00), **208.53 (10:00, PTI)**; peak 208.66 (hour only from SANDRP); 14 Jul 208.35 (~11:00) | One CSV, `source_ref` per row, seeded from **Vaibhav's 15 anchors** + CWC 08:00 bulletins. Peak hour **unverified** unless a CWC bulletin confirms it (SR §1 already says so) | [DH](https://www.deccanherald.com/amp/story/india%2Fdelhi-metro-trains-crossing-yamuna-bridges-with-restricted-speed-as-yamuna-swells-1236570.html), [SANDRP](https://sandrp.in/tag/old-railway-bridge/), [CWC 12 Jul](https://cwc.gov.in/sites/default/files/cfcrcwcdfb12.07.2023_5.pdf) |
| HydroSwift / India-WRIS | WRIS level modules are daily/monthly; HydroSwift's resolution is undocumented | **Not attempted.** Told Vaibhav at 16:30 that the digitised anchors are final (his ask (d)) | his plan §1 |
| Open-Meteo Flood + Archive | Daily GloFAS v4 discharge; ERA5 `precipitation_sum`. Hosts blocked in the sandbox | Pull on the laptop once (15 min), commit raw CSVs to `pipeline/data/cache/`. ERA5 is context only (§8.4) | [flood API](https://open-meteo.com/en/docs/flood-api) |
| IMD gridded rainfall | Registration + binary format | **Won't**; ERA5 labelled "not IMD" | — |
| OSMnx 2.1.1 | Inspected the wheel: graphs are bidirectional when `network_type` ∈ `bidirectional_network_types` (default `["walk"]`), **even with `custom_filter`**. Built-in `walk` filter drops trunk/motorway and `foot=no` | One query, `network_type="walk"` + custom filter that keeps them (§3.5) | `osmnx/graph.py`, `settings.py` |
| OSM bunds | `man_made=embankment|dyke` coverage along the Delhi Yamuna is sparse; bunds often exist only as roads named "Pushta/Bund/Marginal" | Name-based selector added to the burn layer; burn mask viewed once in QGIS | review §1 |
| Critical infra story | 13 Jul 2023: **Wazirabad, Chandrawal, Okhla WTPs shut**, ~25% supply cut | Checkable demo moment for §8.2 | [Tribune](https://www.tribuneindia.com/news/delhi/overflowing-yamuna-water-treatment-plants-shut-drinking-supply-to-be-hit-in-delhi-525283) |
| Drain No. 12 / ITO | ITO, Supreme Court, Rajghat flooding was regulator backflow, not overbank | Excluded from `calib_points.csv` with reasons (SR §11.1) | Vaibhav §1 |
| Amplify without Git | Manual deploy: `create-deployment` → zip → `start-deployment`; `AWS::Amplify::App` supports `CustomRules` / `CustomHeaders` | Template creates App + Branch with Arjav's SPA rules; `deploy_frontend.sh` uploads `frontend/dist`. Fallback: S3 `web/` behind the data CloudFront | [manual deploys](https://docs.aws.amazon.com/amplify/latest/userguide/manual-deploys.html) |
| Budgets in CFN | Changing a notification **forces replacement** | Define once, never edit | [CFN ref](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-budgets-budget.html) |
| SAM images | `resolve_image_repos = true` creates SAM-managed ECR repos; `--use-container` needs Docker | Docker is a deployer prerequisite (Saksham's arm64 pydantic-core build) | SAM CLI docs |

Pins in `pipeline/requirements.lock`: osmnx 2.1.1, geopandas 1.2.0, networkx 3.7, shapely 2.2.0, rasterio 1.5.2, pandas 3.0.6, pyarrow 26.0.0, scipy 1.18.1, pydantic 2.14.0, boto3 1.43.x; aws-sam-cli 1.167.0, cfn-lint 1.57.2, ruff 0.16.x. Any pin under two weeks old drops back one minor.

## 2. Architecture

```
 OFFLINE (laptop / CI: make data, make replay-local)          AWS ap-south-1 (stack jt-<env>, one SAM template)
 ┌───────────────────────────────────────────────────┐      ┌────────────────────────────────────────────────────┐
 │ seed/gauges_2023_07.csv (source_ref per row)       │      │ S3 jt-<env>-data-<acct> (SR §6 + §11.2;            │
 │ cache/openmeteo_{glofas,era5}_*.csv (committed)    │      │    lifecycle raw/ 30 d, abort MPU 1 d)             │
 │ copernicus-dem-30m window | FABDEM (if in time)    │ sync │ Data CloudFront (OAC, CORS GET/HEAD, Range, ETag)  │
 │ Overpass/OSMnx (one cached query)                  │ ───▶ │   static/* scenarios/* tiles/* models/inundation/* │
 │   ▼ jt_pipeline: ingest → clean → dem → osm        │      │   ← frontend ladder rung 1 (SR §11.4)              │
 │     → seeds → scenario → provenance → infra        │      │ HTTP API jt-<env>-api → catalog-fn (5 GET routes)  │
 │   ▼ root make replay-local (SR §11.5 chain)        │      │                       → teammates' fns             │
 │ ./data/ (== S3 layout, JT_LOCAL_DATA)              │      │ DynamoDB ×5 on-demand · SNS dispatch + ops         │
 └───────────────────────────────────────────────────┘      │ Scheduler jt-<env>-tick (DISABLED) · Budget $10    │
                                                             │ 2 alarms · Amplify jt-<env>-web (manual zip)       │
                                                             └────────────────────────────────────────────────────┘
```
Rules: (1) **S3 + CloudFront is the integration bus**; Lambdas only filter, rasters never go through the API (6 MB cap). (2) The local tree mirrors S3 via `JT_LOCAL_DATA`. (3) Every stage is idempotent (`_stage.json` with input hash). (4) One serving Lambda (`catalog-fn`) for my routes.

## 3. Technology choices

| Need | Choice | Why / rejected |
|---|---|---|
| Contracts | pydantic v2 `jt_shared.models`; JSON Schema via `python -m jt_shared.export_schemas` | SR §8; CI fails on drift |
| Light imports | `constants/io/naming/timeutil` = stdlib + boto3; `models` imports pydantic lazily | Small Lambda zips |
| Gauge cleaning | pandas + scipy `PchipInterpolator` | Monotone between anchors; no overshoot past the peak |
| DTM | FABDEM, else GLO-30 3×3 min + 3×3 median, then embankment burn (§3.4); COG driver | No datum offset here (SR §11.1) |
| Roads | OSMnx 2.1.1, one query (§3.5) | One simplification → one `edge_id` space |
| IaC / CI | AWS SAM, one `infra/template.yaml` with append-only owner sections · GitHub Actions (ruff, pytest, drift, join tests, cfn-lint), no AWS creds | `sam validate --lint` |
| Data bundle | `jt-data-bundle-v<N>.tar.gz` on a GitHub Release + `s3://…/bundles/` | Teammates/CI never call Overpass or Open-Meteo |

### 3.4 DTM (SR §11.1: I ship the surface, Vaibhav owns δ and S)
`pipeline/jt_pipeline/dem.py`:
1. **Source:** (A) FABDEM N28E077 clipped to the bbox (`dtm_source="fabdem-v1-2"`), or (B) GLO-30 3×3 min-filter + 3×3 median (`"glo30-min3-burn"`). **v0 (Fri 18:00)** is the raw GLO-30 clip at the same path, `meta.json.version="v0-raw"`, so Vaibhav's grid loads from Friday.
2. **Burn (value agreed with Vaibhav, his §3.2):** on OSM `man_made=embankment|dyke`, `embankment=yes` **and** `highway` with `name~"Pushta|Bund|Marginal"`, buffered 1 px, set `z = max(P95 of DSM within 60 m of the line, 210.0 m)`. Burn mask rendered once in QGIS before shipping. **Bridges/flyovers** (`bridge=yes`, highway `layer≥1`) are **not** burned (would dam the river in the connectivity fill); their DSM height goes onto graph edges as `elev_min_m`, `is_bridge=true`.
3. **Calibration points, not a fit:** `static/dem/calib_points.csv` (`id, lon, lat, label, source_ref, segment, excluded, reason`), ≥15 wet + ≥15 dry, overbank-only, ground level, ≥5 of each per third (Wazirabad–ORB, ORB–ITO barrage, ITO–Okhla). Wet candidates: Yamuna Bazaar, Monastery Market/ISBT Ring Road, Majnu ka Tila, Bela Estate, Garhi Mandu, Usmanpur, Sonia Vihar khadar, Wazirabad pump house, Geeta Colony khadar, Mayur Vihar Ph-1 camp, Chilla Khadar, Madanpur Khadar, Jaitpur khadar, Batla House bank, Okhla WTP apron. Dry: open ground only (Red Fort lawn, Civil Lines ridge road, Akshardham forecourt, Laxmi Nagar Vikas Marg, Shahdara GT Road, Daryaganj, Kalindi Kunj road…). Excluded rows kept with `excluded=true`: ITO, Supreme Court/Tilak Marg, Rajghat–Shantivan (Drain No. 12 backflow), metro concourses/underpasses, rooftop-only sources.
4. **Outputs:** `static/dem/corridor_dtm.tif` (EGM2008, Δ = 0) + `meta.json` `{version, dtm_source, vertical_datum:"EGM2008", delta_m:null, calibrated_by:"ml/calibrate.py", burn_rule, burn_layers[], n_wet, n_dry, excluded_points[{id,reason}]}`. Node `elev_m` and edge `elev_min_m` are on **EGM2008** and labelled so; nobody compares them with gauge levels (SR §11.1).

### 3.5 Road graph (SR §11.3)
- **Query:** `ox.graph_from_bbox(bbox, network_type="walk", custom_filter=JT_FILTER, simplify=True)`; `JT_FILTER = ["highway"]["area"!~"yes"]["highway"!~"abandoned|bus_guideway|construction|corridor|elevator|escalator|planned|platform|proposed|raceway|razed|steps_disused"]["access"!~"private"]` keeps motorway, trunk and `foot=no` (Ring Road, NH-24). `useful_tags_way` += `name:hi`, `foot`, `bridge`, `layer`, `embankment`.
- **Edge attributes:** `edge_id`, `name`, `name:hi`, `highway`, `geometry`, `length`, `foot_ok` (false for `foot=no` or motorway/_link), `is_drive`, `is_bridge`, `elev_min_m`. Node: `elev_m`.
- **`edge_id` = `osm:<min(u,v)>:<max(u,v)>:<key>`** (SR §11.3), u, v = OSM node ids of the simplified edge; `<key>` = 0-based index among parallel undirected edges between that pair, ordered by (min osmid, length). u→v and v→u share it. Written into graphml and roads.geojson once, never recomputed.
- **Fallback:** `nx.compose(walk, drive)` + drop drive edges within 3 m of a same-osmid walk edge.
- **Map file `static/osm/roads.geojson` = flood envelope** (≤ 8 MB raw, 5 dp, props `edge_id, name, name:hi, highway`, one feature per undirected edge): (i) all `motorway…tertiary` (+`_link`) and `unclassified`; (ii) every edge whose **minimum `onset.tif` along it is ≤ 211.66 m** (HFL + 3 m, covers Vaibhav's δ ∈ [−3, +2]) using his v0 raster, then re-unioned with the calibrated raster at Sat 13:00. **The envelope only ever grows**, so a re-export can't break Saksham's join. If `onset.tif` is missing at Sat 10:00, (ii) uses `elev_min_m ≤ 211.66` as a generous selector (a selection rule, not a flood claim). Over 8 MB → 5 m Douglas–Peucker. Full graph stays in `corridor_roads.graphml` (routing only).

## 4. File structure

```
shared/   schemas/*.schema.json · fixtures/{manifest,scenarios,gauges,colony,shelter,health,provenance,infra_exposure}.json
          py/jt_shared/{constants,stations,models,export_schemas,naming,timeutil,io}.py · py/tests/
pipeline/ pyproject.toml requirements.lock
          data/seed/{gauges_2023_07,gauges_2025_09,calib_points,colonies,shelters,infra_overrides}.csv
          data/cache/openmeteo_{glofas,era5}_*.csv
          jt_pipeline/{cli,ingest_gauges,ingest_openmeteo,clean,dem,osm,seeds,infra,provenance,scenario,seed_ddb,bundle}.py
          tests/{test_clean,test_dem,test_osm_ids,test_joins,test_scenario,test_offline}.py · tests/golden/
infra/    template.yaml samconfig.toml README.md · functions/catalog/app.py · layers/jt_shared/
          scripts/{deploy_frontend,smoke,secrets,destroy}.sh · tests/test_catalog_handler.py
Makefile (root) · .github/workflows/ci.yml
```

## 5. Contracts: produced, consumed, status

**I produce:** SR §5.1 `GaugeReading` (`clean/gauges/*.parquet`, `scenarios/<id>/gauges.json`); §5.5 `Colony`/`Shelter` with `free_beds` (`static/*.geojson` without contacts, DynamoDB with contacts); `static/dem/{corridor_dtm.tif, meta.json, calib_points.csv}`; `static/osm/{corridor_roads.graphml, roads.geojson, river.geojson, centreline.geojson}`; `scenarios/<id>/{manifest,provenance}.json`, `infra/<valid_at>.json`; routes `GET /scenarios`, `/scenarios/{id}/timeline`, `/scenarios/{id}/gauges`, `/colonies` (no contacts), `/health`; every SR §4 resource; root `make replay-local`.
**I consume:** Vaibhav's `models/inundation/v1/{onset,cutoff_0p30}.tif` (roads envelope, infra exposure) and `forecasts/` (infra "watch" status); teammates' §11.5 make targets.

| Item | Status |
|---|---|
| Nullable `level_m` / `discharge_cumecs` (≥1 set), `source: glofas`, `source_ref`, `note`; pipeline never synthesises levels | **Adopted in v1.1** (§11.3); implemented in PR #1 (Fri 16:30) |
| Manifest keys incl. `issued_at[]`, `events[].ts_verified`, `artefacts`, `context?`, window 09–16 Jul, 60 min | **Adopted in v1.1** (§11.3). `issued_at[]` = the hourly grid (same as `valid_at`); a CI join test checks every forecast `issued_at` is in it |
| SR §1 corrections (2025 peak 207.48 m ~06:00 4 Sep; 2023 peak hour unverified) | **Adopted in v1.1** (§1 already updated); my former PR #3 is dropped |
| Direction-agnostic `edge_id`, envelope `roads.geojson`, edge attributes, CI join test | **Adopted in v1.1** (§11.3) |
| `GET /colonies` without contacts; data-access ladder | **Adopted in v1.1** (§11.4) |
| Make-target chain `pipeline scenario → ml replay-local → routing precompute → alerts predraft` | **Adopted in v1.1** (§11.5); former PR #4 dropped, I only implement the root target |
| Datum: `corridor_dtm.tif` Δ = 0; δ, S fitted only in `ml/calibrate.py` | **Adopted in v1.1** (§11.1) |
| Open PRs from me | PR #1 models + synthetic fixtures (Fri 16:30) · PR #2 real-curve fixtures (Fri 19:00) · PR #3 `provenance` + `infra_exposure` models and stub fixtures (Fri 23:00, additive) |

Manifest example (shape per SR §11.3): `{"scenario_id":"yamuna-2023-07","mode":"replay","start":"2023-07-09T00:00:00+05:30","end":"2023-07-16T23:00:00+05:30","step_min":60,"default_at":"2023-07-13T00:00:00+05:30","ref_station":"DELHI_RLY_BRIDGE","events":[{"kind":"peak","ts":"…","level_m":208.66,"ts_verified":false}],"artefacts":{"gauges":"real","forecasts":"fixture",…},"context":{"rain_mm_daily":[…],"rain_source":"era5-open-meteo"},"sources":[{"id":"cwc-bull-2023-07-12","kind":"cwc","url":"…"}],…}`. `events` is computed from the cleaned ORB series (a test checks Arjav's client-side thresholds agree).

## 6. Schedule with SR §11.7 checkpoints and cut lines

### Fri 9 Oct (7.5 h work + 0.5 h buffer)
| Time | Task | Done when |
|---|---|---|
| 15:00–16:30 | `jt_shared` (constants, stations, models per §5 + §11.3, export_schemas, naming, timeutil, io with `JT_LOCAL_DATA`) + **synthetic-curve fixtures** (manifest, scenarios, gauges incl. a null-level HATHNIKUND row, colony, shelter, health) | **PR #1 open 16:30**; Arjav and Vaibhav unblocked |
| 16:30–17:45 | Digitise `gauges_2023_07.csv` from Vaibhav's anchors + CWC 08:00 bulletins + 13 Jul 10:00 = 208.53 + Hathnikund cusecs. Peak-hour check (15-min box). GloFAS + ERA5 pull (laptop). **Post to Vaibhav: HydroSwift not attempted, anchors final** | ≥20 anchors with `source_ref`; peak `ts_verified` decided |
| 17:45–19:00 | **First 20 min (review C2):** `river.geojson`, `centreline.geojson`, `corridor_dtm.tif` v0 (raw clip) → local + dev bucket, posted to Vaibhav by 18:05. Then `clean.py` (hourly PCHIP, QC), parquet, `gauges.json`, manifest (`issued_at[]`, events, rain context) | Vaibhav has river/DTM v0 before his 18:45 slot. **PR #2 (real curve) open 19:00** |
| 19:00–19:30 | Break | |
| 19:30–20:45 | SAM v0 → `dev`: bucket (+lifecycle), 5 tables, HTTP API, `catalog-fn` (5 routes), budget, tags, Scheduler DISABLED stub | `smoke.sh` 200s for my 5 routes on dev |
| 20:45–22:00 | Start FABDEM download (background). `osm.py`: one Overpass pull, §3.5 attributes and `edge_id`, preliminary graphml + roads.geojson part (i) | Ring Road present; u→v and v→u share `edge_id`; **graph spec + prelim files posted to Saksham 22:00** |
| 22:00–22:30 | `calib_points.csv` collection (review RC-4, moved off Sat morning) | ≥15 wet + ≥15 dry, exclusions with reasons |
| 22:30–23:00 | PR #3 (`provenance` + `infra_exposure` stub fixtures); review and merge the v1.1 contract PRs (mine, Saksham's additive one, Vaibhav's) into `shared/` | Every schema has a fixture in `shared/fixtures/` |
| **23:00** | **CHECKPOINT Fri 23:00 (§11.7): fixtures for every schema + v1.1 merged** | — |
| 23:00–23:30 | **Buffer** | |

**Cut line Fri 23:00:** PR #1/#2 and fixtures are never cut; they run first. If behind: drop the ERA5 rain context (manifest `context` omitted); finish `calib_points.csv` in Sat 08:30–08:50; if the graph is not out, Saksham keeps his local 3×3 km pull until Sat 09:00 (his fallback) and my prelim graph moves to Sat 08:30.

### Sat 10 Oct (9.0 h work + 2.5 h buffer)
| Time | Task | Done when |
|---|---|---|
| 08:30–10:00 | DTM v1 (§3.4): FABDEM if downloaded, else GLO-30 3×3 + burn incl. name selector; QGIS look at the burn mask; `meta.json`; node `elev_m`, edge `elev_min_m`/`is_bridge`; final graphml. (Team sync 09:00–09:15) | `test_dem` green; **DTM + calib points to Vaibhav 10:00** (he calibrates 11:00) |
| 10:00–11:00 | `seeds.py`: ~10 colonies, ~8 shelters (`free_beds`), ground elev = DTM median within 150 m (EGM2008, labelled), synthetic populations labelled, plus-address contacts in DDB only. `seed_ddb.py`. roads.geojson envelope (ii) from Vaibhav's v0 `onset.tif`. `jt-data-bundle-v1` | **Saksham: final graph + seeds; Arjav: colonies/shelters/roads — 11:00** |
| 11:00–12:30 | Infra v1. `sam deploy --config-env demo` first (CloudFront takes 5–15 min). Data CloudFront OAC + CORS (Range, ETag) for `static/ scenarios/ tiles/ models/inundation/ web/`; S3 CORS GET from Amplify origin + POST for uploads; Amplify App + Branch with Arjav's `CustomRules`/headers + `deploy_frontend.sh`; SNS `dispatch` + `ops` (**confirm subscriptions**); `secrets.sh` (SSM SecureString `/jt/<env>/ack-hmac`); Outputs; review Vaibhav's and Saksham's SAM sections (Vaibhav's ask (e)); upload Arjav's `delhi.pmtiles` to `tiles/basemap/`. **Merge `feature/shivansh` → `main` (gate: `sam validate`, offline `make -C pipeline scenario`, `/health` on demo)** | **Stack URLs posted 12:30** (Arjav deploys 12:30, Vaibhav publishes to demo 12:30) |
| 12:30–13:00 | Root `make replay-local` (§11.5 order, fixture fallback, writes `manifest.artefacts`) + `make sync ENV=` | Offline run with no AWS credentials passes on fixtures |
| 13:00–13:45 | Lunch + integration huddle | |
| 13:45–14:00 | Re-union envelope with calibrated `onset.tif`; `make sync ENV=demo`; check `manifest.artefacts` and `aws s3 ls` for 13 Jul 00:00–06:00 | |
| **14:00** | **CHECKPOINT Sat 14:00 (§11.7): demo-window forecasts, depth, roads, plans in S3** | Go/no-go posted |
| 14:00–14:30 | **Should:** Provenance ledger (§8.1) | `provenance.json` real for 2023 |
| 14:30–15:30 | **Should:** Critical-Infra Exposure on `onset.tif` (§8.2) | `scenarios/yamuna-2023-07/infra/*.json` |
| 15:30–16:15 | CI: ruff, pytest, schema drift, cfn-lint, **join tests** (`edge_id` ↔ roads.geojson, plan colony/shelter ids ↔ seeds, forecast `issued_at` ↔ manifest) (Must, 0.5) + **Should:** 2 alarms (API 5xx ≥5/5 min, Lambda Errors ≥5/5 min → `ops`) | CI green |
| 16:15–17:15 | **Buffer A** (Could: `yamuna-2025-09` only if every Must is green) | |
| 17:15–18:00 | Integration sync of teammates' artefacts (Saksham live from 16:00); `smoke.sh` across all SR §7/§11.4 routes + CloudFront Range→206 + SNS confirmed | Smoke green or gaps filed |
| 18:00–18:45 | Dinner | |
| 18:45–19:30 | **First golden run (§9.2) on demo** (`make golden ENV=demo`, even if red; review RC-5, INTEGRATION_PLAN §1) | Fix list posted with owners |
| 19:30–20:00 | **Buffer** | |
| **20:00** | **CHECKPOINT Sat 20:00 (§11.7): FEATURE FREEZE** | — |
| 20:00–21:00 | **Buffer B**: bug fixes only; re-sync after Vaibhav's 19:45 final rebuild and Saksham's re-precompute | |
| 21:00–21:30 | **Backup-deployer dry run (Arjav, his Sat 21:00 slack; review C3):** `make deploy ENV=dev` from a clean checkout following only `infra/README.md`. I stay hands-off and fix the README | Arjav's deploy succeeds, or the gap is written into the README |
| 22:00 | `static/` freeze. Teammates may sync `scenarios/` until Sun 11:00 | |

**Cut line Sat 14:00:** if *team* data for the demo window is missing → no new integration after 17:30, I drop Infra Exposure and alarms and give the time to whoever is blocking (sync, envelope, seeds). If *my* items are late (stack not live at 12:30 or seeds/DTM late) → Provenance and Infra Exposure are dropped, Buffer A goes to the Must item, Amplify falls back to S3 `web/`, and `catalog-fn` keeps only `/health` (the ladder reads CloudFront).
**Cut order at Sat 20:00 (first cut first):** 2025 replay → infra "watch" status from forecasts → alarms → Infra Exposure → Provenance (fixture stays). The Must column is never cut.

### Sun 11 Oct (4.0 h work + 0.75 h buffer + 1.5 h on call)
| Time | Task | Done when |
|---|---|---|
| **09:00–10:00** | **CHECKPOINT Sun 09:00 (§11.7): golden test on demo** + offline test in CI. Blockers only | `pytest -k "schema or golden or offline"` green |
| 10:00–10:30 | `infra/README.md` "Deploy in 10 minutes" + static cost table + deploy checklist (Docker, SNS confirmations, `secrets.sh`) | README merged |
| 10:30–11:15 | **Buffer.** 11:00: teammates' last `scenarios/` sync → `make sync` + smoke (Arjav bakes at 11:00) | |
| 11:15–12:00 | Video assets: architecture diagram (Arjav's 2:40 still), ORB hydrograph with events, provenance/infra stills. **Infra freeze 12:00, tag `v1.0-demo`** | Assets in `docs/` |
| 12:00–12:30 | Recording dry run with the team | |
| 12:30–13:00 | Lunch | |
| **13:00–14:30** | **CHECKPOINT: recording.** On call for re-sync only, no redeploys | Video recorded |
| 14:30–15:15 | Blog section: AWS Open Data DEM, SAM stack, cost | Merged |
| 15:15–15:45 | Incognito URL check, Budget/Cost check, help with submission | |
| **16:00** | **CHECKPOINT: submit (deadline − 2 h; deadline assumed 18:00 IST, confirmed Fri night)** | Submitted |

**Cut line Sun 09:00:** if golden is red, fix only §9.2 blockers; README shrinks to the runbook (no cost table); blog section shrinks to 3 bullets. **Sun 13:00:** whatever is frozen is recorded.

### 6.4 Make targets
`make setup` · `make data` (bundle first, `FROM_SOURCE=1` rebuilds) · `make scenario SCENARIO=` · `make replay-local SCENARIO=` · `make validate` · `make layer` · `make deploy ENV=` (sam build/deploy, secrets, seed, sync, frontend) · `make sync ENV=` · `make smoke ENV=` · `make golden ENV=` · `make destroy ENV=` (empties bucket, deletes stack).

## 7. MoSCoW

The Must column alone is demo-able: the real 2023 ORB curve with thresholds and events, a DTM and roads envelope that Vaibhav and Saksham build on, seeds, and a stack that serves it all from CloudFront.

| Must (18.75 h) | Should (1.75 h) | Could (0 h; Buffer A only) | Won't |
|---|---|---|---|
| `jt_shared` + fixtures (PR #1–#3), digitised + cleaned 2023 ORB, Hathnikund, GloFAS | Provenance & QC Ledger (0.5) | **Replay-Any-Flood: `yamuna-2025-09`** (cut from Should, review RC-7) | Live gauge mode, `LiveMode` param |
| River/centreline + DTM v0 Fri; embankment-aware DTM v1 + `calib_points.csv` | Critical-Infra Exposure on `onset.tif` (1.0) | Infra "watch" status from forecast `hi_m` | Own datum offset or flat-plane exposure (§11.1) |
| OSM graph + envelope `roads.geojson` | ERA5 rain context (inside the Fri 16:30 block) | Sentinel-1 IoU, chainage labels | Judge one-command deploy, Cost Explorer report, CloudWatch dashboard |
| Seeds (geojson + DDB) + data bundle | 2 alarms (0.25) | | IMD gridded rainfall, HydroSwift/CWC scraping |
| SAM stack: S3, data CloudFront, HTTP API + `catalog-fn` (5 routes), DDB, SNS, SSM, Amplify (S3 `web/` fallback) | | | SMS/DLT, Cognito, multi-basin, PMTiles generation |
| Root `replay-local`, CI + join tests, integration sync, golden runs, backup dry run, README, video/blog assets | | | `stages.toml` hooks |

## 8. New and enhanced features

### 8.1 Provenance & QC Ledger — Should, 0.5 h
- **Value:** every number has a receipt: "208.53 m · PTI 13 Jul 10:00 · ok", "207.81 m · PCHIP · imputed", "peak hour unverified", "upstream levels synthetic (ml)". Backs SR §1 ("every number from code") and answers judges before they ask.
- **How:** fields already exist (`source`, `qc_flag`, `source_ref`). `provenance.py` writes `scenarios/<id>/provenance.json`: per dataset licence (OSM ODbL, Copernicus, FABDEM CC BY-NC-SA, Open-Meteo CC-BY 4.0, CWC bulletin), `retrieved_at`, transform chain (`raw → PCHIP → hourly`, `DSM → filter → burn`, `δ,S by ml/calibrate.py`), QC counts, DTM exclusions. Stub fixture Fri 23:00. Arjav renders it if he reaches his Could item; otherwise it feeds the blog and the video's sources caption.

### 8.2 Critical-Infrastructure Exposure — Should, 1.0 h (re-designed for SR §11.1)
- **Value:** which hospitals, metro entrances, substations, WTPs and underpasses go under, and when; the checkable "Wazirabad WTP flagged N h before the 13 Jul shutdown" moment, if the data says so.
- **How:** assets from `features_from_bbox` (`amenity=hospital|clinic`, `railway=subway_entrance|station`, `power=substation`, `man_made=water_works|wastewater_plant`, highways with `tunnel=yes` or `layer<0`) + `infra_overrides.csv` for WTP pump houses. Per asset, sample Vaibhav's **`onset.tif`** and **`cutoff_0p30.tif`** (min within 30 m). At each `valid_at` with ORB level `L`: `wet` if `L ≥ onset`, `critical` if `L ≥ cutoff_0p30`, else `dry`; `first_wet_at` = first step where `L ≥ onset`. **No `level − ground_elev_m` arithmetic, no embankment guard**: slope, offset and connectivity are inside Vaibhav's rasters. Output `static/infra.geojson` + `scenarios/<id>/infra/<valid_at>.json` (`[{asset_id, kind, name_en, name_hi, exposure, first_wet_at, method:"onset_v1"}]`). If `onset.tif` is missing, the layer is not shipped. Statuses are never hand-edited.

### 8.3 Embankment-aware DTM + shared calibration set — Must enhancement (Fri 22:00 + Sat 08:30 blocks)
- **Value:** the step from "the river is at 208 m" to "*your lane* floods, the bund protects the next one", which Flood Hub and CWC don't take. It is also what makes Vaibhav's sloped fit trustworthy: one surface, one point set, one fitter.
- **How:** §3.4. Burn rule agreed with Vaibhav, bridges on edges, published exclusions.

### 8.4 Rainfall context strip — Should, 0.25 h (inside the Fri 16:30 block; first Fri cut)
- **Value:** answers "was it raining in Delhi?" with data: the 8–9 Jul downpour, then an upstream-release peak on 13 Jul under mostly dry skies.
- **How:** ERA5 `precipitation_sum` corridor mean from the cached Open-Meteo archive → `manifest.context.rain_mm_daily`, labelled "ERA5 reanalysis (not IMD)". Omitted if the cache is missing.

### 8.5 Replay-Any-Flood (`yamuna-2025-09`) — Could
- **Value:** a second event (peak 207.48 m, SR §1) shows the pipeline isn't tuned to one flood.
- **How:** `jt scenario build --id yamuna-2025-09 --gauges seed/gauges_2025_09.csv --start 2025-09-01T00:00+05:30 --end 2025-09-07T00:00+05:30 --step 60`, then `make replay-local SCENARIO=yamuna-2025-09`. Missing teammate artefacts are recorded as `"missing"`. Runs only in Buffer A before the 20:00 freeze.

## 9. Testing strategy
- **Contracts:** fixtures round-trip, incl. a discharge-only row; a row with both values null is **rejected**. Drift: `export_schemas && git diff --exit-code shared/schemas`. `make validate` checks every JSON under `data/`.
- **Cleaning:** PCHIP stays within neighbouring anchors; `|Δh| > 0.5 m/h` or outside [195, 212] m → `suspect`; gaps > 6 h → `imputed`; every ts has `+05:30`; peak event = series max and `ts_verified` matches the anchor note.
- **DEM:** burned pixels = `max(P95 DSM 60 m, 210.0)` (same 20-cell check as Vaibhav's `grid.py`); bridge pixels not burned; `meta.json.delta_m is null`; ≥15+15 points with ≥5 per third; ITO/Supreme Court/Rajghat/underground rows `excluded=true` with reasons.
- **OSM:** `edge_id` matches `osm:<min>:<max>:<key>`, unique per undirected edge, identical for u→v/v→u, stable across two runs on the cached response; "Ring Road" present; every colony centroid within 500 m of a node.
- **Joins (CI, INTEGRATION_PLAN §3):** every `RoadSegmentStatus.edge_id` in roads.geojson; envelope ⊇ previous envelope; roads.geojson ≤ 8 MB; plan `colony_id`/`shelter_id` in seeds; forecast `issued_at` in `manifest.issued_at`.
- **Handler:** `catalog/app.py` on `JT_LOCAL_DATA` fixtures; `at` before start → `[]`, after end → clamped; bad id → 404 in the SR §7 envelope; `/colonies` has no `contacts`; CORS headers present.
- **Infra exposure:** an asset with onset 207.0 is `dry` at 206.9 and `wet` at 207.0; monotone in `L`.
- **Integration:** golden (§9.2) Sat 18:45 (may fail) and Sun 09:00 (must pass); offline: `env -u AWS_ACCESS_KEY_ID -u AWS_PROFILE JT_LOCAL_DATA=./data make replay-local`; `smoke.sh`: every route, CloudFront Range → 206, SNS subscriptions `Confirmed`.
- **Manual:** ORB plot vs events; burn mask and roads.geojson in QGIS; calib points over the DTM.

## 10. Deployment, IAM and cost
- **Stack** `jt-<env>` in ap-south-1; tags `project=jaltaranga, owner=<name>, env=<env>`; parameters `Env, OpsEmail, BedrockRegion, BedrockModelId, AllowedOrigins`.
- **Operators:** primary Shivansh; **backup Arjav** (INTEGRATION_PLAN §4), dry run Sat 21:00. Prerequisites: AWS CLI v2, SAM CLI 1.167, Python 3.13, **Docker** (`sam build --use-container`). Arjav installs them in any slack before Sat 21:00.
- **Frontend hosting:** Amplify manual zip deploy (Arjav's plan agrees; SR §11.6 allows it). `CustomRules`: SPA rewrite `/<*>` → `/index.html` (200) excluding asset extensions incl. `.webmanifest .mp3 .png`; headers `sw.js`/`index.html` no-cache, `/assets/*` immutable. A root `amplify.yml` (`appRoot: frontend`, `AMPLIFY_MONOREPO_APP_ROOT=frontend`) is added only if we switch to Git-connected.
- **Lambda:** `catalog-fn` python3.13 arm64, 256 MB, 10 s, module-level ETag cache; `jt_shared` layer has no binary deps. Image functions: `resolve_image_repos = true`, keep-last-3 ECR lifecycle; packaging declared by Sat 11:00.
- **IAM (one role per function):** `catalog-fn`: `s3:GetObject` on `scenarios/*`, `static/*`; `s3:ListBucket` on `scenarios/`; `dynamodb:GetItem` on `scenario-state`, `Scan` on `colonies`. CloudFront OAC, bucket policy scoped to the five prefixes, Block Public Access on. SSM `/jt/<env>/*` readable only by the alerts role. I review teammates' policies for wildcard actions.
- **Hygiene:** lifecycle expires `raw/` at 30 d and aborts incomplete MPU at 1 d; `make destroy` empties the bucket; `dev` deleted after submission.
- **Static cost table (README):** Lambda $0 (free tier) · HTTP API ≈$0.10 · S3 ≈$0.05 · CloudFront $0 (free tier) · DynamoDB ≈$0.05 · SNS email $0 · Scheduler (disabled) $0 · 2 alarms $0 · Bedrock + Polly cents (Saksham) → **< $2**, hard $10 budget alarm (50/80/100% actual, 100% forecast). No NAT, EC2, SageMaker or provisioned concurrency. Copernicus/FABDEM reads run on the laptop, never in Lambda.

## 11. Risks and degrade paths

| Risk | Likelihood | Degrade path |
|---|---|---|
| No hourly 2023 ORB data | High (confirmed) | Digitised anchors + PCHIP, labelled `imputed`; threshold and peak anchors keep events exact |
| Peak hour unverifiable | Med | `ts_verified:false`; provenance says "hour unverified" |
| **Water-surface slope / stacked offsets** | Was high | Resolved by §11.1: Δ = 0 in my file, one fitter (Vaibhav), one point set; exposure and envelope read his rasters |
| **Wall-clock slip** (plan re-baselined at Fri 20:00) | Med | Earlier rows run first; 2025 already cut; Fri cut line drops rain context and moves calib/graph to Sat 08:30 |
| FABDEM late | Med | GLO-30 3×3 + burn, same calib set |
| OSM bunds missing | Med | Name selector (Pushta/Bund/Marginal) + QGIS check; Vaibhav drops a burn segment that seals a known-wet point (his `calibration.json`) |
| `onset.tif` late | Med | Envelope from `elev_min_m ≤ 211.66` (generous selection); Infra Exposure not shipped |
| roads.geojson too heavy | Med | Envelope design, then 5 m simplification |
| Overpass / Open-Meteo down | Med | Cached responses in the bundle → `overpass.kumi.systems` → Geofabrik PBF; committed Open-Meteo cache, else `context` omitted |
| **I am a single point of failure** | Med | Arjav backup deployer (dry run Sat 21:00), README runbook, data bundle, Saksham second approver on `infra/` |
| Backup lacks Docker/SAM on Sat 21:00 | Med | Prerequisites listed Fri; gap recorded in the README so the runbook still works for a judge |
| API Lambda down during recording | Low | Ladder: frontend GETs read CloudFront `static/`/`scenarios/` then fixtures (§11.4) |
| CloudFront/Amplify create latency | Med | Demo deploy first in the 11:00 block; S3 `web/` fallback |
| Synthetic upstream looks circular | Med | Pipeline writes only real or GloFAS rows; provenance and blog say so |
| SAM merge conflicts | Med | Append-only sections, I resolve, `cfn-lint` + `sam validate` in CI, `dev` before `demo` |

## 12. What I need from teammates

| From | What | By |
|---|---|---|
| Vaibhav | Ack burn rule + Δ = 0 surface; `onset.tif` v0 in dev (envelope) | Fri 23:00 |
| Vaibhav | Calibrated `onset.tif`/`cutoff_0p30.tif` in demo; Lambda packaging; `make -C ml replay-local` per §11.5 | Sat 12:30 / Sat 11:00 / Sat 13:00 |
| Saksham | Ack graph spec; Bedrock region/model values; team inbox for SNS + plus-addresses | Fri 23:00 |
| Saksham | SAM section (he deploys to demo 13:45); `make -C routing precompute`, `make -C alerts predraft`; second approver on `infra/` | Sat 13:00 / Sat 15:00 |
| Arjav | `VITE_*` names + build dir (done 20:00); `delhi.pmtiles`; SPA rewrite list | Fri 20:00 / Sat 11:00 / Sat 12:00 |
| Arjav | **Add the 30-min backup-deployer dry run to his plan** (Sat 21:00–21:30 slack) and install prerequisites | Sat 21:00 |
| All | Reviews within 30 min on Saturday; tag `owner=<name>`; no credentials in git | Ongoing |

## 13. What teammates can rely on from me

| When | Deliverable |
|---|---|
| **Fri 16:30** | PR #1: `jt_shared` (§11.3 models), schemas, synthetic-curve fixtures |
| **Fri 18:05** | `river.geojson`, `centreline.geojson`, `corridor_dtm.tif` v0 (raw clip) |
| **Fri 19:00** | PR #2: real-curve `gauges.json` + manifest; `clean/gauges/DELHI_RLY_BRIDGE.parquet` |
| **Fri 20:45** | Dev stack, my 5 routes live |
| **Fri 22:00** | Preliminary graphml + roads.geojson (major roads), graph spec |
| **Fri 23:00** | PR #3 provenance/infra fixtures; v1.1 contract PRs merged; `calib_points.csv` |
| **Sat 10:00** | `corridor_dtm.tif` v1 + `meta.json` + final `calib_points.csv` |
| **Sat 11:00** | Final graphml, envelope roads.geojson, colonies/shelters geojson, DDB seeded, `jt-data-bundle-v1`; `feature/shivansh` merged |
| **Sat 12:30** | Demo stack URLs (API, data CloudFront, Amplify), CORS, SNS ARN + confirmed subscriptions, SSM secret, PMTiles uploaded |
| **Sat 13:00** | Root `make replay-local` |
| **Sat 15:30** | `provenance.json`, `infra/*.json` (if `onset.tif` landed) |
| **Sat 16:15** | CI with join tests |
| **Sat 19:30** | First golden run result + fix list |
| **Sun 09:00** | Golden green on demo; **Sun 12:00** infra freeze, `v1.0-demo` |

## Revision log

**Rev 2 (Fri 9 Oct, round-1 review):** hours re-balanced with explicit buffer; judge deploy, Cost Explorer, live mode, dashboard and `stages.toml` cut; FABDEM / GLO-30 3×3 + burn-back with bridges kept off the raster; nullable `level_m` + synthetic fixtures at 16:30; single walk+custom-filter graph; envelope `roads.geojson`; unverified peak hour; IMD → ERA5 context; Docker/ECR prerequisites.

### Revision log (v1.1, Fri 9 Oct 20:00, round-2 review + SR §11)
1. **C1 datum (review RC-1 + SR §11.1):** I no longer fit Δ. `corridor_dtm.tif` (renamed from `corridor_cop30.tif`) is on EGM2008 with Δ = 0 and `meta.json.delta_m=null, calibrated_by="ml/calibrate.py"`. I ship one merged `calib_points.csv` with exclusions; Vaibhav fits δ and S jointly. Burn value aligned to his stated rule `max(P95 DSM 60 m, 210.0 m)`.
2. **Flat-plane arithmetic removed:** Infra Exposure samples Vaibhav's `onset.tif`/`cutoff_0p30.tif` (method `onset_v1`); the embankment guard is dropped. The roads envelope uses onset ≤ HFL + 3 m and only ever grows.
3. **C2:** `river.geojson`, `centreline.geojson` and DTM v0 ship at **Fri 18:05** (first 20 min of the 17:45 block), before Vaibhav's 18:45 slot, matching SR §11.2's "by Fri 18:45".
4. **C3 backup deployer:** moved from Saksham (no slot in his 11:15–13:15 block) to **Arjav**, as INTEGRATION_PLAN §4 names him; dry run Sat 21:00–21:30 in his slack, and I asked him to add it to his plan.
5. **RC-4:** calibration-point collection moved to Fri 22:00–22:30; name-based bund selector + QGIS check added; Sat 08:30 block no longer contains a fit.
6. **RC-5:** first golden run Sat 18:45 on demo (INTEGRATION_PLAN §1), even if red; Sun 09:00 must pass.
7. **RC-6:** HydroSwift "no" posted to Vaibhav at 16:30. The SR §5.1 edit is moot: nullable `level_m` is **adopted in v1.1** §11.3.
8. **RC-7 re-baseline:** plan re-baselined at Fri 20:00; earlier rows are the committed baseline; `yamuna-2025-09` cut to **Could** now.
9. **RC-8:** SNS subscription confirmation in Sat 11:00 block, `smoke.sh` and the README checklist (also SR §11.6).
10. **SR §11 conformance:** `edge_id` changed to `osm:<min(u,v)>:<max(u,v)>:<key>`; `GET /colonies` (no contacts) added to `catalog-fn`; `Shelter.free_beds` seeded; manifest `issued_at[]` added with a CI join test; former PRs #3 (SR §1), #4 (make targets) and the graph-spec PR are **adopted in v1.1** and dropped; data-access ladder means my GET routes are off the demo path, so the cut line can reduce `catalog-fn` to `/health`; Amplify stays manual-zip (Arjav agrees, §11.6 allows) with `CustomRules`/headers and S3 CORS for the Amplify origin.
11. **SR §11.7 checkpoints** are rows in §6 (Fri 23:00, Sat 14:00, Sat 20:00, Sun 09:00, Sun 13:00–14:30, submit at deadline − 2 h) with cut lines at each. The old Sat 20:15 2025 slot sat after the freeze and is gone. Buffer: 3.75 h explicit (+1.5 h on call during recording).
12. **Feature set:** Provenance (Should), Infra Exposure (Should, re-designed), embankment-aware DTM + shared calibration set (Must), ERA5 context (Should), 2025 replay (Could). `merge feature/shivansh → main` gate added at Sat 11:00; join tests (edge, colony/shelter, `issued_at`) added to CI; `/colonies` Scan permission added.
