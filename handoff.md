# Jaltaranga — Workstream Handoff (Vaibhav: ML/AI Core & Inundation Engine)

**Owner:** Vaibhav  
**Branch:** `feature/vaibhav`  
**Commit:** `6cdbfd7` (and latest handoff commit)  
**Status:** ✅ Fully Implemented, Tested, Replay Built & Committed  

---

## 1. Executive Summary

The **ML/AI Core (`ml/`)** workstream for Jaltaranga is complete and verified against all contracts specified in `SHARED_RESOURCES.md` and `docs/workstreams/vaibhav/IMPLEMENTATION_PLAN.md`.

This workstream establishes the **"Gauge to Street"** intelligence bridge: converting abstract river gauge levels at the Old Delhi Railway Bridge (DRB) into hyper-local street-level flood thresholds, 2-hour road cutoff forecasts, and a 56-step interactive what-if simulation ladder.

---

## 2. Deliverables & Integration Map for Teammates

### 2.1 For Saksham (Routing & Dispatches)
* **Colony Thresholds:** `shared/fixtures/colony_thresholds.json` and `ml/out/models/inundation/v1/colony_thresholds.json`
  * Contains exact `wet_at_level_m` and `cutoff_at_level_m` per colony (e.g., Yamuna Pushta `wet_at_level_m = 203.22 m`, `cutoff_at_level_m = 203.52 m`).
  * Used directly by Saksham's routing planner to compute `t_submersion` and colony status without raw datum arithmetic.
* **Road Cutoff Rasters:** `ml/out/models/inundation/v1/cutoff_0p30.tif` and `onset.tif`
  * Cloud-Optimized GeoTIFFs (Deflate) sampled along OSM roads to identify when roads exceed the $0.30\text{ m}$ threshold.
* **Precomputed Cutoff Index:** `ml/out/models/inundation/v1/edge_cutoffs.json`
  * Direction-agnostic `edge_id` mapping to cutoff water level in metres.

### 2.2 For Arjav (Frontend / PWA)
* **Forecast Nodes:** `shared/fixtures/forecast_nodes.json`
  * Pre-formatted `[ForecastNode]` JSON objects across horizons $h \in \{1, 3, 6, 12, 24\}\text{ h}$ with conformal $80\%$ bounds (`lo_m`, `hi_m`).
* **What-If Slider Ladder (Feature F1):**
  * 56 discrete level steps ($204.0\text{ m}$ to $209.5\text{ m}$ in $0.1\text{ m}$ intervals):
    * GeoJSON flood polygons: `ml/out/models/inundation/v1/ladder/<level>.geojson`
    * State JSON: `ml/out/models/inundation/v1/whatif/<level>.json`
  * Sample response fixture: `shared/fixtures/whatif_response.json`.
* **Depth Surfaces Index:** `shared/fixtures/depth_index.json` and `ml/out/scenarios/yamuna-2023-07/depth/index.json`
  * Contains GeoTIFF raster URLs and polygon GeoJSONs categorized by `depth_class`: `"0.05-0.3"`, `"0.3-1"`, `"1-2"`, `">2"` metres.

### 2.3 For Shivansh (Pipeline & AWS Cloud Infrastructure)
* **Zero-Dependency Lambda Handler:** `ml/lambda/forecast_fn/handler.py`
  * Lightweight Python 3.12 arm64 Lambda serving:
    * `GET /scenarios/{id}/forecast?at=`
    * `GET /scenarios/{id}/flood?at=`
    * `GET /scenarios/{id}/whatif?level_m=`
    * `GET /models/card`
  * Zero heavy runtime dependencies (pure JSON file reader with CORS support).
* **Shared Schemas:** `shared/py/jt_shared/` (`models.py`, `constants.py`, `timeutil.py`, `naming.py`).

---

## 3. Performance & Evaluation Metrics (Model Card Summary)

Evaluated strictly on the **unseen held-out July 9–18, 2023 Yamuna Flood pulse** using causal inputs only:

### Hydrological Stage Forecasting (`lagreg-v1` Ridge Champion)
| Horizon | MAE | RMSE | NSE | Skill vs Persistence |
|---|:---:|:---:|:---:|:---:|
| **1h** | $0.41\text{ m}$ | $0.73\text{ m}$ | 0.550 | **+8.1%** |
| **3h** | $0.43\text{ m}$ | $0.72\text{ m}$ | 0.604 | **+17.4%** |
| **6h** | $0.45\text{ m}$ | $0.72\text{ m}$ | 0.613 | **+21.1%** |
| **12h** | $0.41\text{ m}$ | $0.61\text{ m}$ | 0.724 | **+55.3%** |
| **24h** | $0.52\text{ m}$ | $0.66\text{ m}$ | 0.689 | **+71.1%** |

* **Conformal Uncertainty:** $80\%$ split-conformal coverage band guarantees empirical bounds.

### Inundation Engine Accuracy
* **Balanced Accuracy:** **`88.0%` (0.88)** against ground truth overbank points.
* **Datum Offset ($\delta$):** $0.0\text{ m}$ (EGM2008 alignment).
* **River Surface Slope ($S$):** $0.22\text{ m/km}$.
* **Monotonicity & Physical Sanity:** Monotonically non-decreasing inundation area with respect to gauge height; low floodplains flood correctly while high ground (e.g. Connaught Place) remains dry.

---

## 4. Codebase Structure (`ml/`)

```
ml/
├── config/
│   ├── stations.yaml              # River gauge and barrage locations
│   ├── inundation.yaml            # Domain bbox and calibration bounds
│   └── events_split.yaml          # Pre-registered DEV/TEST splits
├── data/fallback/
│   ├── drb_anchors.csv            # July 2023 verified CWC bulletin readings
│   └── hathnikund_releases.csv    # Hathnikund barrage release discharge
├── jt_ml/
│   ├── paths.py                   # Path and environment resolution
│   ├── data/
│   │   ├── load.py                # Pipeline parquet / fallback CSV loader
│   │   └── causal.py              # Strict ts <= issued_at causal feature generator
│   ├── models/
│   │   ├── persistence.py         # Persistence baseline (Delta = 0)
│   │   ├── lagreg.py              # Multi-horizon Ridge regression forecaster
│   │   ├── conformal.py           # Finite-sample split-conformal calibrator
│   │   └── hydrogat_np.py         # Zero-dependency NumPy HydroGAT-lite model
│   ├── inundation/
│   │   ├── grid.py                # Corridor DTM & chainage k-d tree
│   │   ├── onset.py               # Grayscale morphological priority flood reconstruction
│   │   ├── calibrate.py           # Balanced accuracy solver for delta and S
│   │   ├── surface.py             # GeoTIFF and GeoJSON vectorizer
│   │   ├── thresholds.py          # Colony 10th-percentile threshold extractor (F6)
│   │   ├── ladder.py              # 56-level what-if scenario generator (F1)
│   │   └── edge_cutoffs.py        # Road edge sample cutoffs
│   ├── extras/
│   │   └── surge.py               # Rate-of-rise and surge detection flags (F2)
│   ├── train.py                   # Model fitting script
│   ├── evaluate.py                # Evaluation on held-out split
│   ├── model_card.py              # MODEL_CARD.md and registry.json generator
│   ├── forecast_run.py            # [ForecastNode] generator
│   └── replay_build.py            # End-to-end offline replay builder
├── lambda/
│   └── forecast_fn/
│       └── handler.py             # Serverless API router
├── tests/
│   ├── test_causal.py             # Causal integrity & no future leakage
│   ├── test_conformal.py          # Finite-sample interval assertions
│   ├── test_onset.py              # Morphological priority flood & monotonicity
│   └── test_lambda.py             # Lambda endpoint mock tests
├── out/                           # S3 artifact mirror (GeoTIFFs, JSONs, GeoJSONs)
├── pyproject.toml                 # Package configuration
└── uv.lock                        # Pinned lockfile
```

---

## 5. How to Run & Verify

1. **Run Full Test Suite:**
   ```bash
   uv run pytest ml/tests
   ```
   *(All 7 unit and integration tests pass).*

2. **Re-build Entire Offline Replay:**
   ```bash
   uv run python -m jt_ml.replay_build
   ```
   *(Generates all forecasts, depth rasters, GeoJSON vectors, and what-if ladder steps in `ml/out/`).*

---

## 6. Known Scope & Assumptions
* **Drain No. 12 Regulator Backflow:** July 2023 flooding at Supreme Court/ITO occurred via regulator backflow, not river overbank spill. This is documented as a known caveat in `MODEL_CARD.md`.
* **Zero Cloud GPU Spend:** The entire ML suite trains and infers on standard CPUs with zero GPU requirements.
