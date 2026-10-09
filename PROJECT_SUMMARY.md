# Jaltaranga — Project Summary

**Predict. Route. Protect.** Flood evacuation intelligence for the Yamuna floodplain in Delhi.
Team **ChaapSeekers** · Bharat Builds Tour 2026 · WeMakeDevs × AWS Environmental Hacks · Track 02: Heat and Water · Oct 8–11, 2026

Related docs: [`SHARED_RESOURCES.md`](SHARED_RESOURCES.md) (contracts, v1.2) · [`INTEGRATION_PLAN.md`](INTEGRATION_PLAN.md) (merge, test, deploy, demo) · `IMPLEMENTATION_PLAN.md` + `QUALITY_REVIEW.md` on each `feature/<name>` branch.

---

## 1. Enhanced overview

Flood warnings in Delhi stop at the gauge: "Yamuna crossed 205.33 m". In July 2023 the river hit a record **208.66 m** and more than **25,000 people** were evacuated. In September 2025 it peaked at **207.48 m** and more than 14,000 were evacuated. Nobody living on the floodplain can turn a gauge height into a plan.

Jaltaranga turns the gauge level into street-level instructions:

1. **Predict** the Delhi Railway Bridge level 1–24 h ahead, with honest 80% split-conformal intervals. Simple baselines go first; a small graph-attention model ("HydroGAT-lite") is used only if it beats them on held-out data.
2. **Translate the gauge into streets.** A precomputed **onset raster** (morphological reconstruction over an embankment-aware DEM) gives, for every 30 m cell, the gauge level at which it first floods. This yields "your lane gets wet at 206.3 m and is impassable at 206.7 m" and a time-to-water countdown for every colony.
3. **Route.** It predicts which roads exceed the 0.30 m wading limit and when, then computes safe walking routes to shelters that still have free beds. It names the roads to avoid and shows the "death-trap" counterfactual: the route people would have taken without flood information.
4. **Protect.** Bedrock drafts a Hindi and English dispatch in which **every fact is filled in by code** and checked by a validator. An officer approves it, it is delivered by email (SMS after DLT registration), Polly *Kajal* reads it aloud in Hindi, and residents can save it for offline use.

The demo is a **replay of the July 2023 flood** on a simulated clock, because there is no flood in October. Every number on screen carries provenance.

### What the team added beyond the original idea (16 new or enhanced features)

| Owner | Feature | MoSCoW |
|---|---|---|
| Vaibhav | **Street flood thresholds** ("your lane floods at X m") per colony and road, from the onset and cutoff rasters | Must |
| Vaibhav | **Gauge-level what-if slider** (204.0–209.5 m): colonies, roads and the flood polygon update instantly | Should |
| Vaibhav | **Model card and honest skill report** (champion rule fixed in advance; skill reported on held-out data only) | Should |
| Vaibhav | Rate-of-rise / threshold-ETA / upstream-surge flags | Could |
| Vaibhav | Drainage backflow toggle (Drain No. 12, the regulator failure behind the 2023 ITO flooding) | Could |
| Saksham | **"Death-trap" counterfactual and named avoid list** (how many residents a flood-blind route would have trapped) | Must (avoid list) / Should (summary) |
| Saksham | **Vulnerability-aware priority and mobility** (elderly, disabled, pregnant, under-5s) | Should (basic priority is Must) |
| Saksham | **Capacity-aware shelter assignment** (greedy Must → OR-Tools min-cost flow Should; no shelter over its free beds) | Must / Should |
| Saksham | **Polly Kajal Hindi voice briefing** (cached by content hash) | Should |
| Saksham | Alert lifecycle: PREPARE → URGENT → ALL_CLEAR, SHELTER_IN_PLACE, de-dup/cooldown | Must (types) / Should |
| Shivansh | **Embankment-aware DTM with one shared calibration set** (bridges on edges, published exclusions) | Must enhancement |
| Shivansh | **Provenance and QC ledger** (every value has a source, QC flag and licence) | Should |
| Shivansh | **Critical-infrastructure exposure** (hospitals, metro, substations, WTPs, underpasses) | Should |
| Shivansh | Rainfall context strip (ERA5, labelled "not IMD") · Replay-any-flood CLI (`yamuna-2025-09`) | Should / Could |
| Arjav | **Offline Colony Pack** (route as SVG, shelters, dispatch and audio in IndexedDB; works in airplane mode) | Should |
| Arjav | **Time-to-water countdown** with forecast band | Must (countdown) / Should (band) |
| Arjav | **Split-screen "basin warning vs street plan"** for the video | Should |
| Arjav | "सुनें / Listen" accessibility mode · citizen field-report pins · Director mode for recording | Should / Could / Should |

## 2. Team responsibilities

| Member | Branch | Workstream | Owns | Final review |
|---|---|---|---|---|
| **Arjav** | `feature/arjav` | Frontend & Visualization | `frontend/`: React + Vite + MapLibre GL PWA, Command and Colony views, replay scrubber, offline pack, Director mode. **Demo-video owner** | **16.0 / 20** ✅ |
| **Vaibhav** | `feature/vaibhav` | ML/AI Core | `ml/`: forecasting (persistence → lag-regression → HydroGAT-lite), conformal intervals, onset/cutoff rasters, FloodSurface, colony thresholds. **Owns the vertical datum fit** | **15.4 / 20** ✅ |
| **Shivansh** | `feature/shivansh` | Data Pipeline & AWS Infra | `pipeline/`, `infra/`, `shared/` steward: digitised gauges, DTM, OSM graph, seeds, manifest, SAM stack, CI, `make replay-local`. **Deploy owner** | **15.4 / 20** ✅ (17.1 in round 1 before the v1.1 re-baseline) |
| **Saksham** | `feature/saksham` | Routing & Alerting | `routing/`, `alerts/`: road cutoffs, time-dependent routing, shelter assignment, EvacuationPlan, Bedrock slot-filled dispatch, validator, SNS, Polly, DynamoDB log. **Picks `T_hero`** | **15.4 / 20** ✅ |

Scores are the mean of 7 criteria (technical soundness, feasibility, integration, AWS alignment, innovation, completeness, risk) rated 1–5, scaled to 20. The pass bar is 15/20. Review history: round 1 → one revision for Shivansh (14.9 → 17.1) → v1.1 alignment of all four plans → an independent re-review. The remaining cross-plan issues were resolved in SHARED_RESOURCES §11.8.

## 3. Technical architecture

```
                    OFFLINE (laptops / Colab) — `make replay-local SCENARIO=yamuna-2023-07`
 ┌──────────────────────────────────────────────────────────────────────────────────────────────┐
 │ pipeline/ (Shivansh)            ml/ (Vaibhav)                     routing/ + alerts/ (Saksham)│
 │ digitised CWC levels ─┐         assemble → persistence / lagreg   cutoff.py ← cutoff_0p30.tif │
 │ GloFAS/ERA5 context ──┤         → HydroGAT-lite (challenger)      edge status (green/amber/red)│
 │ Copernicus GLO-30 ────┼─► DTM ─► split-conformal 80% intervals    TD-Dijkstra primary/backup  │
 │  (+bund mask, calib)  │         onset.tif / cutoff_0p30.tif       greedy → OR-Tools assignment│
 │ OSM roads/infra ──────┤         colony_thresholds.json            avoid list + trap summary   │
 │ colony/shelter seeds ─┘         FloodSurface per step             EvacuationPlan per step     │
 │ manifest (T_hero)                                                 predraft dispatch cards     │
 └───────────────┬──────────────────────────────┬───────────────────────────────┬──────────────┘
                 ▼                              ▼                               ▼
        ┌───────────────────── S3  jt-demo-data-<acct>  (static/ models/ scenarios/ tiles/ audio/) ─────────────┐
        └──────────────┬───────────────────────────────────────────────────────────────────┬────────────────────┘
                       │ CloudFront (OAC)                                                  │
                       ▼                                                                   ▼
  ┌──────────────────────────────────────┐        ┌──────────────────── API Gateway HTTP API  jt-demo-api ─────────────────────┐
  │ Amplify Hosting  jt-demo-web          │  GET   │ Lambda: scenarios/timeline/gauges/colonies/health (Shivansh)               │
  │ React + MapLibre PWA (Arjav)          │◄──────►│ Lambda: forecast/flood/whatif/models (Vaibhav, numpy)                       │
  │  • static-first data ladder           │  POST  │ Lambda: roads/plans/dispatch draft+approve/shelters/reports (Saksham)      │
  │  • Command / Colony / Compare views   │        │      ├─► Bedrock Nova (cross-region profile) — slot-filled HI/EN text       │
  │  • offline pack (IndexedDB + SW)      │        │      ├─► Validator → template fallback (18 s budget)                         │
  └──────────────────────────────────────┘        │      ├─► Polly Kajal (hi-IN neural) → S3 audio/                              │
                                                   │      ├─► SNS jt-demo-dispatch (email; SMS after DLT)                         │
                                                   │      └─► DynamoDB: colonies, shelters(free_beds), dispatches, reports        │
                                                   └──────────────── EventBridge Scheduler jt-demo-tick (live mode, 5 min) ──────┘
  Infra as code: AWS SAM (infra/template.yaml) · CI: GitHub Actions (schemas, joins, invariants, sam validate) · Budget alarm $10
```

**AWS services:** Amplify Hosting, CloudFront, S3, API Gateway (HTTP API), Lambda (arm64), Amazon Bedrock (Nova), Amazon Polly (Kajal), DynamoDB, EventBridge Scheduler, SNS, CloudWatch, IAM, plus AWS SAM. Copernicus DEM comes from the AWS Open Data Registry. Strands Agents SDK is a post-hackathon option.

## 4. Implementation timeline (remaining hackathon, IST)

| When | Arjav (frontend) | Vaibhav (ML) | Shivansh (data + infra) | Saksham (routing + alerts) |
|---|---|---|---|---|
| **Fri Oct 9 (evening)** | Vite/TS skeleton, data ladder, map + 3 layers on fixtures, scrubber | Persistence + lagreg + conformal; onset/cutoff v0 | `jt_shared` + fixtures, digitised 2023 gauges, DTM v0, river/centreline, SAM skeleton, **budget alarm** | Bedrock region/IAM probe, cutoff + TD-Dijkstra on fixtures, validator + templates, fixtures |
| **Fri 23:00 sync** | — | publishes v0 `colony_thresholds.json` | merges v1.1 contract and fixtures | **computes `T_hero`** (+ backup) |
| **Sat Oct 10 (DTU build day)** | Command flow (plans → draft → approve), Colony view, countdown, offline pack, Compare | Calibrate δ/S, ladder, replay FloodSurfaces, HydroGAT-lite time-box, model card | Calibration points, OSM graph and roads envelope, deploy `demo`, CloudFront/Amplify/SNS, `make replay-local` | Assignment, avoid list and trap summary, full precompute → S3, dispatch Lambda + SNS + Polly |
| **Sat 14:00** | go/no-go: is the precomputed demo window in S3? If not, record from static/fixtures | | | |
| **Sat 20:00** | **Feature freeze** | | | |
| **Sun Oct 11** | 09:00 golden test → fixes → 12:00 dry run → **13:00–14:30 record the 3-min video** → blog + README → **submit by deadline − 2 h** | | | |

Merge order: **Shivansh → Vaibhav → Saksham → Arjav** (INTEGRATION_PLAN §1).

## 5. Risk mitigation

| Risk | Likelihood | Mitigation |
|---|---|---|
| Not enough time (2.5 days left on Oct 9) | High | Must-path only; go/no-go at Sat 14:00; freeze at Sat 20:00; per-person cut lines; precompute instead of live inference |
| No hourly gauge archive (CWC FFS has no API, India-WRIS is daily) | High | Digitised press/CWC readings labelled `digitized`; skill reported only on held-out anchors; synthetic upstream levels confined to ML and labelled |
| GAT doesn't beat the baselines with this little data | High | Champion rule fixed in advance; ship lag-regression with honest intervals; GAT is a labelled challenger |
| DEM vertical datum and embankments wrong → the wrong streets flood | Medium | One datum owner; shared calibration set with hold-outs; bund floor applied in gauge space; golden check (Yamuna Pushta wet, CP dry) |
| Hero colony already wet at the demo time | Medium | `T_hero` chosen from data, backup hero, SHELTER_IN_PLACE path |
| LLM hallucinates a place, number or phone | Medium | Slot-filled text, gazetteer validator, whitelist 1077/112, template fallback, human approval |
| Bedrock not in ap-south-1 / IAM for inference profiles | Medium | Probe on Fri; cross-region profile; documented IAM form; predrafted cards for the demo steps |
| India SMS needs DLT | Certain | Email + in-app inbox for the demo; SMS on the roadmap |
| Overclaiming ("saves lives") | Medium | Report the computed counterfactual and lead times only; a limitations slide |
| Cost | Low | Serverless only, budget alarm at $10, `dev` stack deleted after submission |

## 6. Success metrics (for judging)

| Criterion | Metric | Target |
|---|---|---|
| Execution | Golden E2E test on the deployed `demo` stack at `T_hero` | Passes (forecast in band → flood hits hero colony → safe route → validated Hindi dispatch → email received) |
| Safety | Primary routes crossing a red edge, over all replay steps | **0** |
| Faithfulness | Untraceable tokens across 20 recorded Bedrock dispatches shown in the UI | **0**; fallback rate reported |
| Forecast honesty | h = 6 MAE vs persistence on held-out anchors; 80% interval coverage | Reported as measured (no target faking); coverage within ±10 pts of 80% |
| Inundation | Hit rate on reported flooded and dry places (and IoU vs a satellite extent if available) | Reported; Yamuna Pushta wet and Connaught Place dry at 208.66 m |
| Lead time | Hours of warning for the hero colony vs the city "evacuation" threshold crossing | Shown on screen from computed values |
| Built on AWS | Fully deployed on AWS; one-command reproducible deploy; monthly cost | ≥ 9 AWS services; < $10 |
| Design & usability | An officer can draft and approve a dispatch; a resident sees their route offline | < 60 s; works in airplane mode |
| Demo | 3-minute video following INTEGRATION_PLAN §5 | Recorded by Sun 14:30 |
| Bonus | AWS Builder Center blog: "Gauge to street: honest flood evacuation on serverless AWS" | Published at submission |

## 7. Honest limitations

- A 30 m DEM can't see curbs, manholes or basements. Results are corridor-scale guidance, not engineering certification.
- Gauge history is reconstructed from limited public readings, so forecast skill claims are limited to held-out anchors.
- A bathtub-with-connectivity model misses drain backflow (the 2023 ITO flooding) unless the backflow toggle ships.
- Colony contacts and shelter capacities in the demo are **synthetic**.
- Google Flood Hub and CWC already forecast this gauge. Jaltaranga's contribution is the **gauge → street → route → verified instruction** step after that forecast.
