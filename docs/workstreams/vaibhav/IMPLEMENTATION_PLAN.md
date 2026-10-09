# Jaltaranga — ML/AI Core: forecasting + inundation (ml/) — Implementation Plan v1.1 (owner: Vaibhav)

> Branch `feature/vaibhav`. I only touch `ml/`. `shared/` (fixtures, schema notes) and my append-only `# --- ml (Vaibhav) ---` section of `infra/template.yaml` go through small PRs (SR §3/§4/§10).
> Contracts (SHARED_RESOURCES v1.1; §11 wins over earlier sections): I **produce** `ForecastNode` (§5.2), `FloodSurface` (§5.3 + §11.3 `depth_class`), `models/inundation/v1/{onset,cutoff_0p30}.tif`, `colony_thresholds.json`, `models/registry.json`, `models/<model>/<ver>/metrics.json`, `MODEL_CARD.md` (§11.2), and the routes `/scenarios/{id}/forecast`, `/scenarios/{id}/flood` (§7), `/scenarios/{id}/whatif?level_m=`, `/models/card` (§11.4, Should). I am the **only** place that fits the datum offset δ and the slope S (§11.1). I **consume** `clean/gauges/*.parquet` / `scenarios/<id>/gauges.json` (§5.1 + §11.3 nullable `level_m`), `manifest.json` (§11.3 shape), `static/dem/corridor_dtm.tif` + `calib_points.csv`, `static/osm/{river,centreline,roads}.geojson`, `static/colonies.geojson` (§11.2).
> Budget: ~25 focused h, Fri Oct 9 15:00 → Sun Oct 11. **Feature freeze Sat 20:00** (§11.7). Recording Sun 13:00–14:30 has priority over everything.

---

## 0. TL;DR (the bet)

1. **Honest before fancy.** Persistence and Ridge lag-regression with split-conformal 80 % intervals ship Friday (Must). HydroGAT-lite is a time-boxed challenger (Should). The evaluation is pre-registered: one event tunes everything, a different event is only ever *reported* (§2.3), and replay forecasts use only data available at issue time.
2. **One raster makes every level instant.** Under a planar sloped water surface, a cell's **onset level** (the DRB gauge level at which it first connects to the river) comes from one grayscale morphological reconstruction. Depth at any level is `where(onset ≤ L, L − z', 0)`. Replay, road cutoffs, colony thresholds and the what-if slider all read it. This is the **gauge → street** link Flood Hub and CWC lack: *"your lane floods when the Old Railway Bridge gauge reads 206.3 m."*
3. **Data is scarce, and we say so.** The hourly 2023 series is Shivansh's digitised reconstruction (§11.3: pipeline never synthesises levels). Synthetic upstream levels exist only inside `ml/` with `source="synthetic"` and feed only the GAT. Skill is quoted only at real, untouched anchors.

---

## 1. Research findings (verified Oct 9, 2026; condensed)

| Topic | Finding | Consequence |
|---|---|---|
| CWC hourly data | FFS site has no API and failed for ~a week at the 2026 monsoon start ([SANDRP](https://sandrp.in/2026/06/11/cwc-flood-forecast-website-failure-at-start-of-2026-monsoon-season/)). Daily 08:00 bulletin PDFs are archived. | No hourly archive. Shivansh digitises press + bulletin anchors (≥20 rows, each with `source_ref`). |
| July 2023 anchors | Press readings ([Deccan Herald](https://www.deccanherald.com/amp/story/india/yamuna-swells-further-in-delhi-old-railway-bridge-shut-for-traffic-1235924.html), [Udayavani/PTI](https://english.udayavani.com/article/raging-yamuna-nears-all-time-record-level-in-delhi/1501337), [ETV Bharat](https://www.etvbharat.com/english/state/delhi/delhi-yamuna-water-level/na20230724135905867867269), [SANDRP](https://sandrp.in/tag/old-railway-bridge/)). 208.53 m at 10:00 on 13 Jul (PTI); 208.35 m ~11:00 on 14 Jul (AIR). **Peak hour unverified** (SR §1). Hathnikund: ~3.21 lakh cusecs 11 Jul AM, 1.62 lakh 10:00 13 Jul, 2.5–2.9 lakh 22 Jul. | Anchor list in §2.1. Peak-timing error is reported only if `ts_verified` becomes true. |
| Releases vs Delhi stage | 2023 peaked higher than 2019 on **less than half** the Hathnikund release. | A release-driven what-if is not credible (dropped, §7). Forecast leans on the Delhi gauge itself. |
| ITO 2023 | Flooding came through the failed **Drain No. 12 regulator** (backflow), not overbank ([National Herald](https://www.nationalheraldindia.com/amp/story/national/yamuna-water-flows-to-ito-rajghat-as-the-irrigation-department-regulator-suffers-damage), [SANDRP](https://sandrp.in/2024/02/20/delhi-july-2023-floods-parliamentary-committee-report-raises-more-questions/)). | Bathtub misses ITO. Excluded from calibration (§11.1). F5 (Could) or a stated caveat. |
| DEM | GLO-30 is a **DSM** on **EGM2008** ([CDSE](https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM)); AWS Open Data tile `copernicus-dem-30m/…N28_00_E077_00…` reachable. | Shivansh ships the DTM on EGM2008 with Δ = 0 (§11.1); I fit δ (gauge datum vs EGM2008) and S. Built-up areas biased high → under-prediction, documented. |
| Sentinel-1 / GFM | No CEMS/UNOSAT product for Delhi Jul 2023. GFM needs portal login. | Not attempted (cut). Validation = balanced accuracy on `calib_points.csv` + a 10-row "reported vs model" table for the blog. |
| Lambda | Zip ≤ 250 MB unzipped; 10,240 MB; 900 s ([quotas](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html)). | numpy-only zip, built with `--platform manylinux2014_aarch64 --only-binary=:all:`. |
| Libraries | Python 3.12; numpy, scipy, pandas, pyarrow, rasterio (COG driver), shapely, scikit-image, scikit-learn, torch (CPU), MAPIE v1 (`SplitConformalRegressor`, `confidence_level=0.8`). | Versions pinned to whatever resolves on Fri 15:00 (`uv lock`); no reliance on specific PyPI numbers. No ONNX: GAT inference is a numpy forward pass. |

---

## 2. Data plan

### 2.1 DRB gauge series (consumed, not produced)
- **Source of truth:** Shivansh's `clean/gauges/DELHI_RLY_BRIDGE.parquet` + `scenarios/<id>/gauges.json` (Fri 18:45). Rows with `qc_flag="ok"` are **anchors**; `imputed` rows are his PCHIP fill and are used only as the "observed" line and for replay depth.
- **My contribution (sent to Shivansh by Fri 16:00, he seeds from it):** `2023-07-09 11:00 203.14` · `07-10 17:00 205.40` · `07-10 23:00 206.04` · `07-11 12:00 206.38` · `07-12 04:00 207.00` · `07-12 08:00 207.25` · `07-12 11:00 207.54` · `07-13 08:00 208.48` · `07-13 10:00 208.53 (PTI)` · `07-13 18:00 208.66 (peak; ts_verified:false)` · `07-14 11:00 208.35 (AIR)` · `07-15/16/17 08:00 (CWC bulletins)` · `07-18 20:00 205.33` · `07-22 16:00 205.16` · `07-22 22:00 205.02` · `07-24 03:00 206.57` · `07-24 08:00 206.54`, plus 5–8 Jul and 20–25 Jul 08:00 bulletin values. **The `07-12 ~15:00 207.55` row is dropped** (no firm timestamp). This closes the 13–18 Jul recession gap with ≥4 anchors.
- **Hathnikund:** `clean/gauges/HATHNIKUND.parquet` with `level_m=null`, `discharge_cumecs` set (1 lakh cusecs ≈ 2,832 cumecs). Loader drops null-level rows for stage features and uses discharge for release features.
- **Fallback (Fri only, if PR #2 is late):** `ml/data/fallback/drb_anchors.csv` (same rows) → PCHIP locally, written only under `ml/out/`, never to `clean/`.

### 2.2 Causal inputs (used for evaluation **and** for the replay forecasts)
At issue time *t*, the DRB input series is rebuilt from anchors with `ts ≤ t` only (linear interpolation between past anchors, hold-last-value after the latest), with a mask channel for lags before the first anchor. The **replay `forecasts/<issued_at>.json` use these same causal inputs**, so the fan chart in the video is a forecast that could really have been issued. The full PCHIP stays the "observed" line (Arjav's sparkline) and drives replay depth (what actually happened). A test asserts no input row has `ts > issued_at`.

### 2.3 Pre-registered event split (§11.6 evaluation honesty)
| Split | Data | Used for | Never used for |
|---|---|---|---|
| **DEV** | 2023 second pulse 20–25 Jul anchors; 2013 (≈8.06 lakh → 207.32 m) and 2019 (≈8.28 lakh → 206.6 m) sanity points | Muskingum + rating calibration (synthetic upstream nodes), champion selection, conformal `q_dev` | Reported skill |
| **TEST** | 2023 main pulse 9–18 Jul anchors (~15) | **Reported** MAE / RMSE / NSE / skill vs persistence / coverage, run **once** after `registry.json` is frozen | Any fitting, tuning or selection |
| **TEST-2** (Could) | Sep 2025 (`gauges_2025_09.csv`, Shivansh's `yamuna-2025-09`) | Second reported event, if his manifest lands | — |
| **SYN** | 2,000 simulator events (random Hathnikund hydrographs × DEV-fitted parameter spread) | Training lagreg / GAT; synthetic validation; `q_syn` | Reported skill |

**Champion rule (fixed now, §11.6):** at h = 6, champion = lowest MAE on DEV anchors; GAT is eligible only if it beats lagreg on **both** SYN validation and DEV, else lagreg; ties → simpler model. One champion for all horizons (no per-horizon picking). `evaluate.py --split test` refuses to run unless `registry.json` has `frozen: true`.

---

## 3. Architecture

```
          OFFLINE (laptop, Python 3.12; make -C ml replay-local SCENARIO=<id>)          ONLINE (AWS ap-south-1)
clean/gauges + gauges.json ─► causal inputs ─► {persistence, lagreg-v1, gat-v1*} ─► conformal ─┐   s3 scenarios/<id>/forecasts/   ◄─┐ CloudFront (frontend
DEV/SYN (routing_sim, ensemble) ───────────────► train / select (registry.json) ──────────────┤   s3 scenarios/<id>/depth/        ◄─┤  reads these first,
static/dem/corridor_dtm.tif ─┐                                                               ├─► s3 models/inundation/v1/        ◄─┤  §11.4 ladder)
static/osm/river,centreline ─┼► z' = DTM+δ+S·(s−s_DRB) ─► onset (reconstruct) ─► cutoff_0p30 ─┤     onset, cutoff_0p30, colony_   │
calib_points.csv ────────────┘        ▲ calibrate δ,S                 └► ladder 204.0…209.5 ─┤     thresholds, ladder/, whatif/  ├─ jt-<env>-forecast-fn*
static/colonies, roads.geojson ──────► F6 thresholds, edge cutoffs ──────────────────────────┘   s3 models/registry.json, metrics ◄─┘ (py3.12 arm64 numpy,
                                                                                                                                   512 MB, 10 s)
```
(* = Should)

### 3.1 Forecasting
- **Target:** `H(t+h) − H(t)` at `DELHI_RLY_BRIDGE`, h ∈ {1, 3, 6, 12, 24} (§5.2). Predicting the change keeps skill-vs-persistence readable.
- **`persistence`:** Δ = 0.
- **`lagreg-v1`:** one Ridge per horizon on **real-only features**: DRB levels at lags 0,1,2,3,6,12,24,48 h, dH/dt over 1 h and 3 h, Hathnikund discharge at lags 24–72 h (6-hourly), hour sin/cos, masks. No synthetic upstream node enters lagreg, so the simulator cannot leak into it. Coefficients exported to JSON.
- **`gat-v1` (HydroGAT-lite, Should, 1.5 h timebox):** 8 nodes (`HATHNIKUND → … → OKHLA`), per-node temporal conv → 2 dense masked GATv2-style layers (hidden 32, 2 heads, edge feature = travel time) → MLP to 5 horizons, ~15k params, CPU < 10 min, Huber loss. Upstream nodes are **synthetic** (Muskingum K, X per reach + lateral inflow + rating `h = h0 + a·Q^b`, fitted on DEV only). Exported `.npz` + `hydrogat_np.py` (parity ≤ 1e-5). Attention weights are **not** presented as discovered lag times (they would only recover the simulator's own lags).
- **Split-conformal:** per horizon, `q = sorted(|r|)[⌈(n+1)(1−α)⌉−1]`, α = 0.2 → `coverage: 0.8`. `q_final = max(q_syn, q_dev, 0.05·√h)`. `lo_m = level_m − q`, `hi_m = level_m + q`. Hand-written (Lambda stays numpy-only), cross-checked with MAPIE v1 in a test. Realised TEST coverage is reported even if < 0.8.
- **Degrade:** writer uses the champion; on a missing artefact or NaN it falls back to lagreg, then persistence. `model` always names what actually produced the number.

### 3.2 Inundation ("bathtub with connectivity")
1. **Grid:** `static/dem/corridor_dtm.tif` (EGM2008, Δ = 0, bridges off, embankments burned, §11.1), bbox `[77.20, 28.53, 77.33, 28.75]`, ~470 × 790 cells of 1″.
2. **Embankment burn (stated value, review RC-7):** burn = **max(P95 of DTM within 60 m of the line, 210.0 m)** on OSM `embankment=yes` / `man_made=dyke` lines. Shivansh applies it in `corridor_dtm.tif` (§11.1); `grid.py` asserts it on 20 sampled line cells and applies the same burn to my Friday fallback DEM. If calibration shows a known-wet `calib_points` site sealed off by a burned line, that segment's floor is dropped and recorded in `calibration.json`.
3. **Domain clip (RC-7):** river seeds and outputs are limited to chainage between the **Wazirabad barrage** (~28.712 N) and the **Okhla barrage** (~28.545 N). Cells outside are `nodata` ("outside pilot corridor; barrage pond not modelled"), so the Wazirabad pond is never treated as part of the sloped DRB surface.
4. **Chainage:** OSM centreline (`static/osm/centreline.geojson`) densified; `s` per cell via `scipy.spatial.cKDTree`.
5. **z' and onset:** `z' = DTM + δ + S·(s − s_DRB)`. `onset = skimage.morphology.reconstruction(seed, z', method="erosion")`, `seed = z'` on river cells and `z'.max()` elsewhere (seed ≥ mask). Minimax spill height from the river ≈ priority-flood, ~1 s. Enclosed basins stay dry until overtopped.
6. **Road cutoff:** `cutoff_0p30 = max(onset, z' + 0.30)` = DRB level at which depth > 0.30 m (§5.4 red rule as a level). Both rasters float32 COG, `nodata` = never (§11.2). `zprime.npy` is an internal artefact (Lambda/what-if only).
7. **Replay FloodSurface:** for each manifest `valid_at`, depth at the observed DRB level → `scenarios/<id>/depth/<valid_at>.{tif,geojson}` (COG deflate, 256 px tiles; GeoJSON depth > 0.05 m, simplified 0.0001°, `depth_class ∈ {"0.05-0.3","0.3-1","1-2",">2"}`) + `index.json` `[{valid_at, tif, geojson, level_m_ref}]`.
8. **Calibration (`calibrate.py`, sole owner of δ, S):** grid δ ∈ [−3, +2] m (0.25 step) × S ∈ {0.15, 0.20, 0.25, 0.30} m/km; objective = **balanced accuracy** on `calib_points.csv` (≥15 wet / ≥15 dry, ITO/Supreme Court/Rajghat excluded) at the 2023 peak level. Output `models/inundation/v1/calibration.json` `{delta_m, slope_m_per_km, balanced_acc, n_wet, n_dry, dropped_burn_segments[]}`. If balanced_acc < 0.7, ship the best grid point with `fallback:true` and say so in the card.

---

## 4. File structure (`ml/`)
```
ml/
├── README.md  MODEL_CARD.md (generated)  pyproject.toml (extras core/geo/train/serve)  uv.lock
├── Makefile                 # replay-local SCENARIO=  fixtures  train  eval  test  package-lambda  publish ENV=
├── config/{stations.yaml, inundation.yaml, events_split.yaml, scenario_yamuna_2023_07.yaml}
├── data/fallback/{drb_anchors.csv, hathnikund_releases.csv}   # Fri-only fallback; real data comes from clean/
├── data/{outfalls.geojson}                                     # F5 (Could)
├── jt_ml/
│   ├── paths.py             # jt_shared.naming.s3_key + jt_shared.io (JT_LOCAL_DATA)
│   ├── data/{load.py, causal.py, routing_sim.py, ensemble.py}
│   ├── models/{persistence.py, lagreg.py, hydrogat.py, hydrogat_np.py, conformal.py}
│   ├── train.py  select.py  evaluate.py  metrics.py  model_card.py
│   ├── forecast_run.py      # [ForecastNode] per manifest issued_at, causal inputs
│   ├── inundation/{grid.py, onset.py, surface.py, ladder.py, calibrate.py, thresholds.py, edge_cutoffs.py}
│   ├── extras/{whatif.py, surge.py, backflow.py}               # F1, F2, F5
│   └── replay_build.py
├── lambda/forecast_fn/{handler.py, routes.py, requirements.txt, smoke.sh}
├── tests/{test_schema.py, test_causal.py, test_conformal.py, test_onset.py, test_parity.py, test_golden.py, test_lambda.py, test_offline.py}
└── out/                     # gitignored, mirrors the S3 layout
```

**`make -C ml replay-local SCENARIO=<id>` (§11.5):** reads only `$JT_LOCAL_DATA/{scenarios/<id>/manifest.json, scenarios/<id>/gauges.json | clean/gauges/*, static/dem/*, static/osm/*, static/colonies.geojson}` and `ml/` artefacts; writes `scenarios/<id>/{forecasts,depth}/` and `models/{inundation/v1,registry.json,…}`; no AWS credentials; non-zero exit on any failure. Uploading is a separate `make -C ml publish ENV=dev|demo`.

---

## 5. Hour-by-hour plan with go/no-go checkpoints (IST)

**Fri Oct 9, 15:00–23:00 (7 h work + 0.5 h slack)**
| Time | Task | Done when |
|---|---|---|
| 15:00–15:45 | Scaffold `ml/`, `uv lock`, Makefile targets per §11.5, `paths.py` on a `jt_shared` stub (PR #1 lands 16:30). Send anchor list (§2.1) to Shivansh | `make -C ml test` runs with `JT_LOCAL_DATA` and no credentials; anchors posted by 16:00 |
| 15:45–17:15 | `load.py` (null-level drop), `causal.py`, persistence + lagreg-v1 + conformal, `forecast_run.py` on causal inputs (fallback anchors until 18:45) | `forecasts/2023-07-13T00:00:00+05:30.json` validates as `[ForecastNode]`, `lo ≤ level ≤ hi`; `test_causal` green |
| 17:15–18:15 | **Fixtures PR** (§8) generated by `make -C ml fixtures` from the real writers; depth fixtures hand-made at this point | PR open; Saksham (asked 18:45) and Arjav pinged |
| 18:15–18:45 | **Slack 0.5 h** | — |
| 18:45–19:30 | DEM + river: use Shivansh's `river.geojson`/`centreline.geojson` if in (§11.2 says 18:45; his plan says 22:15). Else self-fetch GLO-30 clip from AWS Open Data + Overpass river, apply the §3.2 burn locally (45 min hard timebox) | Grid + seeds + chainage load in `grid.py` |
| 19:30–22:00 | Inundation v0 (Δ = 0, δ = 0, S = 0.22 prior): onset, cutoff, depth writer, `depth_class`, `colony_thresholds.json` (F6) on seed colonies | At L = 208.66 the PNG shows Yamuna Pushta / Majnu ka Tilla / Mayur Vihar floodplain wet, CP dry; area monotone in L (`test_onset`) |
| 22:00–23:00 | `replay_build.py` v0 for the manifest window (9–16 Jul, 192 steps); `make replay-local`; `make publish ENV=dev` | Files under `scenarios/yamuna-2023-07/{forecasts,depth}` + `models/inundation/v1/*` in dev bucket |

> **CHECKPOINT Fri 23:00 (§11.7): fixtures merged + v1.1 contract PR merged.** Mine: fixtures in `shared/fixtures/`, v0 replay in dev. **If behind:** (a) GAT is dropped from the weekend (lagreg is final); (b) inundation v0 finishes Sat 08:00–09:00 before anything else; (c) Saksham is told to stay on fixtures until 09:30. Post ETA in channel.

**Sat Oct 10, 09:00–20:00 (≈9.25 h work + 1 h slack + 0.75 h lunch)**
| Time | Task | Done when |
|---|---|---|
| 09:00–09:30 | Pull Shivansh's real gauges/manifest; re-run `replay-local`; confirm Saksham can read `cutoff_0p30.tif` + `colony_thresholds.json` | Saksham's 09:30 confirmation received |
| 09:30–11:00 | Evaluation integrity: `routing_sim` fitted on **DEV only**, SYN ensemble, `select.py` with the fixed champion rule (lagreg vs persistence now; GAT slot reserved), `registry.json` (not yet frozen), DEV `q_dev` | `out/eval/dev_metrics.json`; `test_causal` + split guard green |
| 11:00–12:30 | Calibrate δ, S on `corridor_dtm.tif` + `calib_points.csv` (Shivansh Sat 10:00–11:00). Verify burn + Wazirabad/Okhla clip. Regenerate onset, cutoff, thresholds; replay depth for the **demo window 13 Jul 00:00–06:00 first**, then the full window | `calibration.json` committed; balanced_acc logged; peak map reviewed |
| 12:30–13:00 | `make publish ENV=demo` (forecasts + depth + inundation v1); tell Saksham to re-run `make -C routing precompute` | Demo-window files in demo bucket |
| 13:00–13:45 | Lunch + integration huddle (Arjav: `depth_class`, fan chart, slider panel yes/no; Saksham: `wet_at_level_m` rename) | Decisions recorded in channel |

> **CHECKPOINT Sat 14:00 (§11.7): forecasts, depth, roads, plans for 13 Jul 00:00–06:00 in S3.** **If my part is missing:** publish whatever exists (uncalibrated v0 is acceptable; card says "δ prior"), **drop GAT, F2 and F5**, keep only Lambda + F1-colonies + F4-MD, and stop new integration at 17:30.

| Time | Task | Done when |
|---|---|---|
| 14:00–15:00 | Lambda `jt-<env>-forecast-fn` (`/forecast`, `/flood` incl. `valid_at`; `/whatif` and `/models/card` serve static files) + EMF metric `jt/ForecastModelUsed`; SAM section already in PR since Fri | `smoke.sh` 200s on dev; Shivansh's 18:45 integration smoke can include my routes |
| 15:00–16:00 | **F1 gauge-level what-if** (ladder + static `whatif/<level>.json`, colonies + polygon; roads via `edge_cutoffs.json`) | `whatif/208.6.json` lists DEL-YP-04 wet; 56 files ≤ 2 MB total |
| 16:00–17:30 | **HydroGAT-lite** (1.5 h hard timebox): train on SYN, numpy export, parity, apply champion rule | Either GAT selected under the rule, or logged "not selected" |
| 17:30–18:00 | **Freeze `registry.json`** (`frozen: true`), run TEST once, `metrics.json` per model, **F4** `MODEL_CARD.md` + skill-table PNG | TEST metrics exist; no further model changes |
| 18:00–19:00 | **Slack / integration bugfix 1 h** (F2 surge flags only if slack is untouched at 18:00) | — |
| 19:00–19:45 | Final replay rebuild with frozen champion + calibrated δ/S → demo bucket; Saksham re-runs precompute 19:45 | `test_golden` (ML part) green on demo |
| 19:45–20:00 | Tag `ml-v1-rc`, update fixtures if any field changed (none expected) | — |

> **CHECKPOINT Sat 20:00 (§11.7): feature freeze.** Anything unstarted is dropped (F2, F5, release-driven what-if). Sep 2025 TEST-2 only runs via `make` as data, no code changes.

**Sun Oct 11, 09:00–15:30 (≈4 h work + 1.5 h slack + recording support)**
| Time | Task | Done when |
|---|---|---|
| 09:00–10:30 | **CHECKPOINT Sun 09:00: golden test (§9.2) on demo** with Saksham and Arjav. Blockers only | ML checks green |
| 10:30–11:30 | **Slack 1 h** (blockers; else TEST-2 on Sep 2025 if Shivansh's scenario exists) | — |
| 11:30–13:00 | Demo assets: fan chart with the 2023 trace **hidden past `issued_at`** then revealed; extents at 206.0 / 207.5 / 208.66; slider clip (Arjav's panel, or an offline ladder animation if he has none); model-card PNG; ML blog section via PR | Clips handed to the video editor by 13:00 |
| 13:00–14:30 | **Recording (§11.7, top priority):** on call for re-renders only | Video recorded |
| 14:30–15:30 | README, tag `ml-v1`, Cost Explorer check, delete dev-only artefacts; 0.5 h slack | `make -C ml test` green on clean clone |

**Slack total: 3.0 h** (Fri 0.5, Sat 1.0, Sun 1.5). **Cut order if behind at any point:** F5 → F2 → GAT → F1 roads (keep colonies + polygon) → `/whatif` + `/models/card` routes (static files stay) → Lambda (frontend reads static per §11.4, so the demo survives).

---

## 6. MoSCoW
| Bucket | Items |
|---|---|
| **Must** | Causal inputs + pre-registered split; persistence + lagreg-v1; split-conformal 0.8; `forecasts/<issued_at>.json`; δ/S calibration on `calib_points.csv`; `onset.tif`, `cutoff_0p30.tif`; per-`valid_at` FloodSurface COG + GeoJSON (`depth_class`) + index; **F6 colony thresholds**; fixtures; `make replay-local` (§11.5) |
| **Should** | Lambda `/forecast` + `/flood` (+ EMF metric); **F1 gauge-level what-if** (`/whatif?level_m=`); **F4 model card** (`/models/card`, MD, PNG); HydroGAT-lite challenger |
| **Could** | F2 surge/rate-of-rise flags; F5 drainage backflow; TEST-2 Sep 2025; ACI adaptive intervals; release-driven "scenario explorer"; live-mode hourly forecast handler on EventBridge; forecasts at WAZIRABAD/ITO/OKHLA |
| **Won't** | F3 shelter demand (cut, see revision log); GFM/S-1 IoU; 2D hydraulics; SageMaker; live CWC scraping |

---

## 7. New / enhanced features (≥3)

**F6. Street flood thresholds — Must, ~1 h on top of onset.** *Value:* the headline differentiator; a gauge number becomes "Yamuna Pushta gets wet at 206.3 m, its lanes are impassable at 206.7 m". *How:* per colony, `wet_at_level_m` = 10th percentile of `onset` within a 150 m buffer of the centroid (the level at which 10 % of the area is wet), `cutoff_at_level_m` = same on `cutoff_0p30`; `null` if never. File exactly as §11.2: `[{colony_id, wet_at_level_m, cutoff_at_level_m, buffer_m:150}]`. Covers the hero colony DEL-YP-04 and the Sat-morning backup hero. Saksham's `t_submersion` = first time `hi_m` reaches `wet_at_level_m`; Arjav's countdown band uses the same field instead of `ground_elev_m` (§11.1: nobody computes "level − ground_elev_m").

**F1. Gauge-level what-if slider — Should, ~1 h (re-scoped per review RC-4).** *Value:* drag the DRB level from 204.0 to 209.5 m and watch colonies, roads and the flood polygon change; the most striking 15 s of the video, zero physical risk because it is the same onset raster. *How:* ladder of 56 levels (0.1 m): `models/inundation/v1/ladder/<level>.geojson` and `whatif/<level>.json` = `{level_m, wet_colonies[{colony_id, wet_at_level_m}], cut_colonies[], cut_edge_ids[], flood_geojson_url}`. `cut_edge_ids` come from `edge_cutoffs.json` (min of `cutoff_0p30` over 15 m samples of each `static/osm/roads.geojson` edge, direction-agnostic `edge_id` per §11.3, same rule as Saksham's `cutoff.py`; he may import it). `GET /scenarios/{id}/whatif?level_m=` snaps to 0.1 m and returns the static file (§11.4); the frontend can read the file directly. Labelled "what if the river reached X m", never a forecast.

**F4. Model card + honest skill report — Should, ~0.75 h.** *Value:* scores on execution and honesty; tells officers how far to trust the number. *How:* `models/registry.json` (`frozen`, champion, versions, provenance shares % digitized / imputed / synthetic, split definitions), `models/<model>/<ver>/metrics.json` (TEST MAE, RMSE, NSE, **skill vs persistence**, coverage, width, lead time of the 206.0 m crossing vs actual), `MODEL_CARD.md`, `GET /models/card`, and a PNG for the video. Caveats: DEV/TEST split, causal inputs, DSM bias, ITO miss, synthetic upstream, "not for real evacuation". **Improvement loop:** new anchors (e.g. Sep 2025) → `make eval` → champion re-selected on DEV → `registry.json` version bump shown as a line in the card.

**F2. Rate-of-rise / threshold-ETA flags — Could, ~1 h (only from Sat slack).** dH/dt (1 h, 3 h) robust z-score vs rolling 72 h median/MAD; `RAPID_RISE`, `THRESHOLD_ETA` (champion `hi_m` crosses 205.33/206.0 within 12 h), `UPSTREAM_SURGE` (Hathnikund discharge +50 % in 6 h). `scenarios/<id>/ml/surge/<issued_at>.json`. Deterministic, traceable numbers. Not in any teammate's committed UI, hence Could.

**F5. Drainage backflow — Could, ~2.5 h (first cut).** ≤6 hand-digitised outfalls (Drain No. 12 at ITO etc.) with assumed regulator crests; "regulator failed" toggle adds the landward cell as an extra seed; `BACKFLOW_RISK` flag. Otherwise ITO is a stated caveat in card and video.

---

## 8. Integration points
| Direction | Contract | Detail / time |
|---|---|---|
| Consume | §5.1 + §11.3 gauges (`clean/gauges/*.parquet`, `gauges.json`) | Shivansh Fri 18:45. Null `level_m` rows dropped for stage; Hathnikund via `discharge_cumecs` |
| Consume | §11.3 manifest (`issued_at[]`, `valid_at[]`, 09 Jul 00:00 → 16 Jul 23:00, 60 min) | Shivansh Fri 16:30 (synthetic) / 18:45 (real). I write one forecast file per `issued_at`, one depth per `valid_at` |
| Consume | §11.1/§11.2 `corridor_dtm.tif` (Δ = 0), `calib_points.csv`, `river.geojson`, `centreline.geojson`, `roads.geojson`, `colonies.geojson` | River Fri 18:45–22:15 (self-fetch fallback Fri 18:45); DTM + calib points Sat 10:00–11:00; roads/colonies Sat 11:00 |
| Produce | §5.2 `[ForecastNode]` → `scenarios/<id>/forecasts/<issued_at>.json` | DRB × {1,3,6,12,24}; `coverage: 0.8`; `model` = actually used. v0 Fri 23:00 (dev), demo window Sat 12:30, final Sat 19:45 |
| Produce | §5.3 + §11.3 FloodSurface → `depth/<valid_at>.{tif,geojson}` + `index.json` | `depth_class` strings (**adopted in v1.1**; Arjav renders it instead of his proposed `depth_band`) |
| Produce | §11.2 `models/inundation/v1/{onset,cutoff_0p30}.tif`, `colony_thresholds.json` | v0 Fri 23:00, calibrated Sat 12:30. Field names `wet_at_level_m` / `cutoff_at_level_m` (**adopted in v1.1**; Saksham's plan still says `onset_level_m`) |
| Produce | §11.2 `models/registry.json`, `models/<model>/<ver>/metrics.json`, `MODEL_CARD.md` | Sat 18:00 |
| Produce (additive, PR Fri 23:00) | `models/inundation/v1/{calibration.json, ladder/, whatif/, edge_cutoffs.json}`, `scenarios/<id>/ml/surge/` (Could) | Paths only; no §5 change |
| Serve | §7 `/forecast?at=`, `/flood?at=` (returns `{tif_url, geojson_url, level_m_ref, valid_at}` — **adopted in v1.1**); §11.4 `/whatif?level_m=`, `/models/card` | `at` snapped down with `jt_shared.timeutil.snap_to_step`. Per §11.4 the frontend reads static files first, so these are for API completeness, the smoke test and the Ask agent |
| Make | §11.5 `make -C ml replay-local SCENARIO=<id>` | Runs after `make -C pipeline scenario`, before `make -C routing precompute` |

**Fixtures (Fri 18:15, ahead of the §11.7 Fri 23:00 checkpoint):** `shared/fixtures/{forecast_nodes.json (DRB × 5 h × 3 issued_at), flood_response.json, depth_index.json, depth_sample.geojson (depth_class), depth_sample.tif (20×20), colony_thresholds.json, whatif_response.json, model_card.json}`, regenerated by `make -C ml fixtures` from the real writers on Fri 23:00.

**Golden-test definition (review RC-8, not settled in v1.1):** "flood GeoJSON intersects Yamuna Pushta" = intersects a **300 m buffer around the DEL-YP-04 centroid**. Proposed as a one-line §9.2 note in my Fri 23:00 PR so routing, frontend and ML test the same thing.

---

## 9. Testing strategy
- **Schema (§9.1):** every writer output validated with `jt_shared.models` in CI, fixtures included.
- **Causal / split guard:** no input row has `ts > issued_at`; `evaluate --split test` fails unless `registry.frozen`; DEV and TEST timestamps disjoint.
- **Conformal:** i.i.d. synthetic coverage 0.8 ± 0.03; hand quantile equals MAPIE v1 `SplitConformalRegressor(confidence_level=0.8)`.
- **Onset/connectivity:** synthetic DEM with a channel, a basin behind a 2 m wall and an isolated pit: basin dry until L > wall, pit never wet, depth monotone in L, `cutoff_0p30 ≥ onset`; cells outside the Wazirabad–Okhla chainage are nodata.
- **Parity (if GAT):** numpy vs torch ≤ 1e-5 on 100 random inputs.
- **Golden (§9.2, ML part):** at `2023-07-13T00:00+05:30`, DRB h = 6 exists with `lo ≤ level ≤ hi`; GeoJSON non-empty and intersects the 300 m DEL-YP-04 buffer.
- **Offline (§11.5):** `env -u AWS_ACCESS_KEY_ID -u AWS_PROFILE JT_LOCAL_DATA=./data make -C ml replay-local SCENARIO=yamuna-2023-07` exits 0.
- **Lambda:** handler unit tests on a local data dir; `smoke.sh` after deploy.

## 10. Deployment, IAM, cost
- **Offline compute** on a laptop; `make publish ENV=` syncs `out/scenarios` and `out/models` (≈192 depth COG + GeoJSON pairs, ladder, ≈110 MB).
- **Lambda** `jt-<env>-forecast-fn`: python3.12, arm64, 512 MB, 10 s, numpy zip built with manylinux2014_aarch64 wheels (packaging declared to Shivansh Fri 23:00, before his Sat 11:00 deadline). Caches `index.json`, `registry.json`, `zprime.npy`/`onset.npy` globally. Env `JT_DATA_BUCKET`, `JT_ENV`, `JT_ASSET_BASE_URL`. EMF metric `jt/ForecastModelUsed{model}`. Tags `project=jaltaranga, owner=vaibhav, env=<env>`.
- **IAM:** `s3:GetObject` on `jt-<env>-data-*/scenarios/*` and `/models/*` + basic logs. No writes, no Bedrock.
- **Cost:** free-tier Lambda/API; S3 < 1 GB; no SageMaker/EC2/NAT; training local. ML cost < $0.50.

## 11. Risks and degrade paths
| Risk | Likelihood | Degrade path |
|---|---|---|
| **Time overrun** | **High** | Checkpoint cut lines (§5); cut order F5 → F2 → GAT → F1 roads → routes → Lambda; Must path done Fri 23:00 |
| Evaluation contamination (simulator or selection touching TEST) | Medium → Low after §2.3 | Pre-registered split, lagreg uses real-only features, frozen registry before TEST, CI guard |
| Shivansh's river/DTM/calib points late (Fri 18:45 / Sat 11:00) | Medium | Self-fetch GLO-30 + Overpass river Fri (45 min budgeted); calibrate on fallback DEM with prior δ if calib points miss Sat 12:00; `fallback:true` in card |
| GAT does not beat lagreg | High | Champion = lagreg; GAT listed as "trained on simulator; not selected" |
| Too few real residuals | High | `max(q_syn, q_dev, 0.05√h)`; realised TEST coverage reported honestly |
| DSM bias / datum mismatch | Medium | δ/S calibration (balanced accuracy), burn value stated, limitation documented |
| Burned bund seals a known-wet area | Low | Segment floor dropped, recorded in `calibration.json` |
| ITO missed | Certain without F5 | Caveat in card and video |
| Peak hour unverified | Certain | Peak-timing metric omitted unless `ts_verified`; peak level still evaluated at verified anchors only |
| Lambda broken at demo | Low | Frontend reads static CloudFront paths (§11.4) |
| GeoJSON too heavy for mobile | Low | Simplify, merge by `depth_class`, 60 m resample fallback |

## 12. What I need from teammates
- **Shivansh:** `jt_shared` PR #1 (Fri 16:30); real gauges + manifest with `issued_at[]` (Fri 18:45); `river.geojson` + `centreline.geojson` per §11.2 (Fri 18:45, or a "no" by 19:00 so I self-fetch); `corridor_dtm.tif` with the §3.2 burn value + `calib_points.csv` (Sat 11:00); `roads.geojson` envelope + `colonies.geojson` (Sat 11:00); my SAM section in the demo stack (Sat 12:30); CloudFront behaviour covering `models/inundation/*` as well as `scenarios/*`.
- **Saksham:** 09:30 Sat confirmation that routing reads `cutoff_0p30.tif` + `colony_thresholds.json` using the v1.1 field `wet_at_level_m`; re-run `make -C routing precompute` after my 12:30 and 19:45 publishes. (No `plans/` dependency any more: F3 cut.)
- **Arjav:** fan chart (level, lo/hi per horizon) and depth styled by `depth_class` from my fixtures; countdown band on `wet_at_level_m`; decide at the Sat 13:00 huddle whether he renders the what-if slider (else I render an offline clip). The model card is shown as a PNG in the video/blog, so no page is required from him.
- **All:** review my Fri 23:00 PR (additive paths + golden-test note) within 2 h.

## 13. What teammates can rely on from me (IST)
| When | Deliverable |
|---|---|
| Fri 16:00 | Anchor list (incl. recession anchors) to Shivansh |
| **Fri 18:15** | Fixtures PR (`forecast_nodes`, `flood_response`, `depth_index`, `depth_sample.{geojson,tif}`, `colony_thresholds`, `whatif_response`, `model_card`) |
| **Fri 23:00** | v0 replay (`forecasts`, `depth`, `models/inundation/v1/*`) in dev + via `make replay-local`; additive PR; Lambda packaging declared |
| Sat 12:30 | Calibrated inundation v1 + demo-window forecasts/depth in **demo** bucket |
| Sat 15:00 | `/forecast`, `/flood`, `/whatif`, `/models/card` on dev API |
| Sat 18:00 | Frozen `registry.json`, TEST `metrics.json`, `MODEL_CARD.md` |
| Sat 19:45 | Final replay with frozen champion in demo bucket |
| Sun 10:30 | ML side of golden test green on demo |
| Sun 13:00 | Demo clips (fan chart reveal, 3 extents, slider), model-card PNG, ML blog section |

## 14. How we report evaluation
- **Forecast (TEST only, causal inputs):** MAE, RMSE, NSE and **skill vs persistence** `1 − MSE/MSE_persist` per horizon; conformal coverage and mean width; lead time of the 206.0 m crossing vs the actual (10 Jul ~23:00). NSE is never quoted alone (persistence trivially gets > 0.90 at h = 1–3).
- **Inundation:** balanced accuracy, hit rate and false-alarm rate on `calib_points.csv`, with the honest note that these points were also used to fit δ and S (in-sample); plus the 10-row "reported vs model at 208.66 m" table. DSM, datum and ITO caveats in the same table.
- **Wording:** "Forecast inputs are only the readings published before each issue time; skill measured on a flood pulse never used for fitting or model choice; a decision-support prototype, not an operational forecast."

---

## Revision log (v1.1, Fri Oct 9)

**Review required changes**
- **RC-1 leakage — fixed.** Pre-registered DEV/TEST/SYN split (§2.3): simulator and selection use the 22–25 Jul pulse + 2013/2019 only; lagreg uses real-only features; TEST run once after `registry.frozen`; CI guard. Champion rule matches §11.6 (h = 6 held-out MAE, GAT must beat lagreg); no per-horizon picking.
- **RC-2 non-causal replay — fixed.** Replay forecasts use the same causal anchors-≤-t inputs as evaluation (§2.2); full PCHIP is only the observed line and replay depth.
- **RC-3 recession gap — fixed.** Added 13 Jul 10:00 208.53, 14 Jul 11:00 208.35, 15–17 Jul 08:00 bulletins; dropped `07-12 ~15:00`. Digitising itself now belongs to Shivansh (§11.3); I supply the list.
- **RC-4 F1 — fixed.** Gauge-level slider (§11.4 `/whatif?level_m=`); release-driven version demoted to Could "scenario explorer".
- **RC-5 F3 — cut (fold-in rejected).** §11.2 fixes the `colony_thresholds.json` shape, Saksham already reads `population_est`/`vulnerable` from `Colony`, and §11.2 adds `plans/<t>.unreachable.json` with population, so duplicating population in my file would create a second source of truth.
- **RC-6 schedule — fixed.** 3.0 h explicit slack; §11.7 checkpoints with cut lines; time overrun rated High; Sat 18:00–19:00 is integration/bugfix.
- **RC-7 burn value + pond — fixed.** Burn = max(P95 within 60 m, 210.0 m), applied by Shivansh per §11.1 and asserted by me; domain clipped to Wazirabad–Okhla chainage.
- **RC-8 golden test + additive fields — partly by v1.1.** `valid_at` and `depth_class` are **adopted in v1.1** (§11.3); the 300 m DEL-YP-04 buffer definition is still a proposal in my Fri 23:00 PR.

**Conformance to SHARED_RESOURCES §11**
- Datum: I no longer burn embankments or own the DEM; Shivansh ships `corridor_dtm.tif` (Δ = 0); I am the sole fitter of δ and S (§11.1). Calibration now uses his `calib_points.csv` (balanced accuracy); my `flooded_places_2023.geojson` and the GFM attempt are removed.
- Gauges: consumed from pipeline; nullable `level_m` handled; synthetic upstream stays in `ml/` (§11.3).
- Artefacts and names per §11.2 (`wet_at_level_m`, `cutoff_at_level_m`, `buffer_m`, `models/<model>/<ver>/metrics.json`); `zprime` is internal only.
- Routes: dropped my proposed `/surge` and `/shelter-demand` routes; `/whatif?level_m=` and `/models/card` follow §11.4; Lambda demoted to Should because the frontend data-access ladder reads static files first.
- Make targets per §11.5 (`SCENARIO=`, `$JT_LOCAL_DATA` only, no credentials, non-zero exit); publish is separate.
- `edge_id` (direction-agnostic, §11.3) used in `edge_cutoffs.json`. Slot-filled alerts (§11.6) need nothing from ML beyond traceable numbers.

**Other changes:** fixtures moved to Fri 18:15 (Saksham asked 18:45); recommended EMF metric, manylinux aarch64 packaging, fan-chart reveal and the ground-truth table adopted; live-mode EventBridge handler named as Could. **Rejected recommendation:** pointing `depth/index.json` at ladder files, because §5.3 defines per-`valid_at` paths and Saksham reads `depth/<t>.tif` directly. Library version pins removed (unverifiable); pin what resolves.
