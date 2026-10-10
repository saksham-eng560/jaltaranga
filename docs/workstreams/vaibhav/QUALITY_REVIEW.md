# Quality Review (round 2): Vaibhav, ML/AI Core (`ml/`): forecasting and inundation

Reviewer: independent senior technical reviewer (not the round-1 reviewer) · Reviewed: Fri Oct 9, 2026 · Plan: `feature/vaibhav/IMPLEMENTATION_PLAN.md` v1.1 · Contracts: `main/SHARED_RESOURCES.md` incl. §11 (v1.1), `main/INTEGRATION_PLAN.md` · Cross-checked against Shivansh's, Saksham's and Arjav's v1.1 plans.

| Criterion | Rating (1–5) |
|---|---|
| Technical Soundness | 4 |
| Feasibility (~25 focused h, one person, from Fri Oct 9) | 3 |
| Integration (v1.1 contracts) | 4 |
| AWS Alignment | 4 |
| Innovation | 4 |
| Completeness | 4 |
| Risk Assessment | 4 |
| **Total** | **27 / 35 → 15.4 / 20** |

**Verdict: APPROVED (>=15/20)**

The approval is narrow, and it holds only if the P1 items in "Actionable improvements" are done before the Sat 14:00 checkpoint. The v1.1 revision fixes every required change from round 1, and it conforms to §11 better than any other ML-shaped plan I would expect from a 48-hour team. The score is unchanged from round 1 for two reasons. First, closer reading turned up new problems: a train/serve mismatch caused by the causal-input fix itself, stale inputs during the demo window, and a bund floor that does not hold up once the slope is applied. Second, the plan still conflicts with `INTEGRATION_PLAN.md` on the merge gate and the video storyboard.

---

## Resolved since previous review

| Round-1 item | Status | Evidence in v1.1 |
|---|---|---|
| RC-1 Evaluation leakage (simulator fitted on TEST, champion picked on TEST) | **Resolved** | Pre-registered DEV / TEST / SYN split (§2.3). The simulator is fitted only on the 20–25 Jul pulse plus the 2013 and 2019 points. The champion rule is fixed in advance at h = 6 DEV MAE, and the GAT must beat lagreg on SYN and on DEV. One champion covers all horizons. `evaluate --split test` refuses to run unless `registry.frozen`. This matches §11.6. |
| RC-2 Non-causal replay forecasts | **Resolved** (but creates new issue T1/T2 below) | §2.2: the replay `forecasts/` use anchors with `ts ≤ issued_at`, and a test asserts it. PCHIP is used only for the "observed" line and for replay depth. |
| RC-3 13–18 Jul recession gap | **Resolved** | Added 13 Jul 10:00 208.53 (PTI), 14 Jul 11:00 208.35 (AIR) and the 15–17 Jul 08:00 bulletins. The `~15:00` row is dropped. Digitising now belongs to Shivansh per §11.3. |
| RC-4 Release-driven F1 not credible | **Resolved** | F1 is now a gauge-level ladder slider read from the onset raster (§11.4 `/whatif?level_m=`). The release-driven version is demoted to Could. |
| RC-5 F3 shelter demand | **Resolved (cut)** | The reason for cutting it is sound: §11.2 fixes the `colony_thresholds.json` shape, and `unreachable.json` already carries population. |
| RC-6 No slack, overrun rated Medium | **Resolved** | 3.0 h of explicit slack, §11.7 checkpoints each with a cut line, overrun rated High, and Sat 18:00–19:00 reserved for integration. |
| RC-7 Burn value and Wazirabad pond | **Mostly resolved** | The burn is `max(P95 within 60 m, 210.0 m)`, agreed with Shivansh (his §3.4). The domain is clipped to Wazirabad–Okhla chainage. *New issue T3 below: the 210 m floor is absolute, but the water surface is sloped.* |
| RC-8 Golden-test definition + additive fields | **Resolved at team level** | `valid_at` and `depth_class` are adopted in §11.3. `INTEGRATION_PLAN.md` §3 already writes the golden test as "intersects Yamuna Pushta (300 m buffer)". The plan still calls this "not settled", which is stale but harmless. |
| Recommended: EMF metric, manylinux aarch64 zip, fan-chart reveal, ground-truth table, improvement loop, live-mode Could, dependency risk budgeted | **Adopted** | §3.1, §5, §7 F4, §10, §11 |
| Recommended: point the depth index at ladder files | **Rejected, with a valid reason** | §5.3 defines per-`valid_at` paths, and Saksham reads `depth/<t>.tif` directly. I agree. |

---

## Per-criterion explanations

### Technical Soundness: 4/5
**Strengths**
- **The onset raster is correct and efficient.** `reconstruction(seed, z', method="erosion")`, with seed = z' on river cells and z'.max() elsewhere, gives the minimax spill height from the river to each cell. That is the priority-flood result in about 1 s. Folding the slope into `z' = DTM + δ + S·(s − s_DRB)` makes `depth = L − z'` exact under the planar-surface assumption, and the sign is right: downstream cells need a higher DRB reading to flood. `cutoff_0p30 = max(onset, z' + 0.30)` is exactly the §5.4 red rule expressed as a level. The grid size of 470 × 790 cells at 1″ over a 0.13° × 0.22° box checks out.
- **The evaluation design is now textbook-honest.** It predicts deltas, reports skill against persistence, never quotes NSE on its own, uses a frozen registry before TEST, runs one champion, and reports TEST coverage even when it falls below 0.8.
- The conformal quantile `⌈(n+1)(1−α)⌉−1` (0-indexed) is the correct finite-sample split-conformal quantile. MAPIE v1's `SplitConformalRegressor(confidence_level=…)` with `fit → conformalize → predict_interval` exists as the plan describes ([MAPIE docs](https://mapie.readthedocs.io/en/stable/generated/mapie.regression.SplitConformalRegressor.html)), so the cross-check test is valid.

**Problems (new in this round)**
1. **T1: train/serve input mismatch caused by the causal fix.** Lagreg and the GAT are trained on SYN, where every input is a dense hourly series. At replay and TEST time, the inputs are rebuilt from sparse anchors using linear interpolation plus hold-last-value. After the last anchor, the held-flat value forces dH/dt to 0 and the lags to be constant. The Hathnikund input is also only 3–5 real points against a dense synthetic hydrograph. A Ridge trained on dense series and then fed held-flat inputs will collapse toward persistence or extrapolate badly, and TEST skill will look worse than the model really is. **Fix:** pass every SYN event through the same pipeline before training. Sub-sample it at a realistic anchor pattern (for example every 3–12 h, with random gaps up to 20 h), rebuild it with `causal.py`, and add an `input_age_h` feature (hours since the last anchor).
2. **T2: inputs are stale in the demo window.** The anchor list goes from 12 Jul 11:00 (207.54) to 13 Jul 08:00 (208.48), with only bulletin rows in between. So at the golden-test time (13 Jul 00:00) the causal input is about 13 h old and roughly 0.5 m below the PCHIP "observed" line. The fan chart will start below the observed curve, and Saksham's curve (observed at h = 0, forecast `hi_m` at h ≥ 1, per his §3) will step *down* at h = 1. That can delay amber and `t_submersion` for the hero colony. Public data can fill this gap. Press citing the CWC portal gives **207.81 m at 18:00 on 12 Jul**, and the Delhi CM cited **207.71 m that afternoon**. I did not find a public 4 am reading on 13 Jul. Add the 12 Jul 18:00 value, and look for any reading on the night of 12–13 Jul.
3. **T3: the bund floor is absolute, but the surface is sloped.** The 210.0 m floor is in DTM (EGM2008) units. In gauge-equivalent terms a burned bund cell has `z' = 210 + δ + S·(s − s_DRB)`. About 6 km upstream of DRB, with S = 0.25 m/km and δ = 0, that is ≈ 208.5 m, which is **below the 208.66 m HFL**. The model would therefore overtop upstream bunds at the peak unless the P95 term happens to dominate. Because ml owns z', `grid.py` should, after calibration, re-apply `z'_bund ≥ 208.66 + 0.5` on line cells (in gauge units) and record that in `calibration.json`. This does not touch Shivansh's file and stays within §11.1.
4. **T4: Friday's lagreg has no defined training set.** §5 ships "persistence + lagreg-v1 + conformal" at Fri 17:15, but SYN and the DEV-fitted simulator are only built Sat 09:30–11:00. Either Friday ships persistence plus a DEV-pulse Ridge, labelled v0, or Friday ships persistence only. Write down which.
5. Minor issues:
   - `q_final = max(q_syn, q_dev, 0.05√h)` loses the formal guarantee. Label it "nominal 0.8", which the realised TEST coverage already effectively does.
   - TEST has about 15 anchors per horizon. Print n next to every metric.
   - F6's 10th percentile must count nodata (never-wet) cells as +∞, not drop them. Otherwise a colony that is 5 % connected reports a misleadingly low threshold.
   - δ is a constant shift (onset(δ) = onset₀ + δ), so the calibration grid needs only 4 reconstructions, one per S, not 84. This is free speed.
   - Cells that are nodata outside the chainage clip must be set to +∞ in z' before reconstruction, or they could act as a conduit.

### Feasibility: 3/5
Strengths: the Must path is front-loaded to Fri 23:00. Every Should item is time-boxed (GAT 1.5 h, F1 1 h). There are 3 h of explicit slack and a clear cut order (F5 → F2 → GAT → F1 roads → routes → Lambda). The Sat 14:00 cut line is concrete. The scope is about 4–5 h smaller than in round 1.

What keeps it at 3:
- **The plan is not re-baselined to the clock.** The v1.1 plan was written around Fri 20:00. Shivansh's plan re-baselines explicitly at 20:00, and the session clock reads Fri 20:07 UTC / Sat 01:37 IST. Even so, Vaibhav's table still starts at Fri 15:00, and nothing says which of the 15:00–20:00 blocks are actually done: scaffold, anchors to Shivansh, causal/lagreg/conformal, the fixtures PR. If they are not done, about 5 of Friday's 7 h are gone and the Fri 23:00 checkpoint cannot be met as written. The checkpoint's cut line, finishing inundation v0 at Sat 08:00–09:00, then becomes the plan.
- **Sat 17:30–18:00:** freezing the registry, running TEST once, writing `metrics.json` for each model, generating `MODEL_CARD.md` and rendering the skill PNG in 30 min is unrealistic. Budget 1 h, and build the card generator on Friday or during slack.
- **Sat 14:00–17:30** packs four deliverables into 3.5 h: the Lambda with four routes, the F1 ladder (56 GeoJSON + 56 JSON files + `edge_cutoffs.json`), the GAT, and the freeze. Any SAM or CloudFront friction lands here.
- **The offline slider clip** (needed because Arjav lists the what-if slider as *Won't*) is squeezed into Sun 11:30–13:00 together with three other assets.

### Integration (v1.1 contracts): 4/5
**Conformant with v1.1:**
- Sole fitter of δ and S (§11.1).
- `onset.tif` / `cutoff_0p30.tif` / `colony_thresholds.json`, with the exact §11.2 field names.
- `depth_class` and `/flood` with `valid_at` (§11.3).
- Nullable `level_m`, and synthetic levels kept inside `ml/`.
- Direction-agnostic `edge_id` in `edge_cutoffs.json`.
- `/whatif` and `/models/card` as Should (§11.4).
- §11.5 make target with no AWS credentials.
- §11.7 checkpoints.
- Saksham's and Arjav's plans both consume `wet_at_level_m` / `cutoff_0p30` as the plan specifies.

**Conflicts still open:**
1. **Merge gate.** `INTEGRATION_PLAN.md` §1 row 2 gates the `feature/vaibhav` merge at **Sat 13:00** on "`/forecast` and `/flood` return 200 on `demo`". The plan instead builds the Lambda Sat 14:00–15:00 on **dev**, rates it Should, and puts it last in the cut order. Either move a minimal static-proxy Lambda before 12:30, or get the gate changed to "static paths readable on CloudFront".
2. **Video storyboard.** At 0:40–1:05 the storyboard shows a **"Hathnikund surge" flag**, which is F2. F2 is a Could and second in the cut order. Either promote F2's `UPSTREAM_SURGE` rule only (about 20 min, deterministic) or have Arjav remove it from the shot list.
3. **Stale teammate times:**
   - Shivansh now delivers river, centreline and DTM v0 at **Fri 18:05** and `calib_points.csv` at **Fri 23:00**. The plan says 18:45 / 22:15 and Sat 11:00, so calibration could start Sat 09:30.
   - Arjav expects the champion replay at **Sat 21:00**, which is after the freeze, and fixtures at Fri 19:00. Vaibhav promises 19:45 and 18:15. Earlier is fine, but post one agreed table.
   - Arjav has already marked the slider and model-card page as *Won't*, so the "decide at the 13:00 huddle" step is moot. Plan the offline clip now.
4. **The h = 0 semantics between forecast and observed** (T2) need a one-line agreement with Saksham. Proposal: routing uses `max(observed, hi_m)` per step, and the forecast file carries `input_age_h`.

### AWS Alignment: 4/5
The architecture is correct for a $10 budget:
- Offline compute → S3 → CloudFront static reads (the §11.4 ladder).
- A numpy-only arm64 python3.12 Lambda (512 MB, 10 s) built from manylinux2014_aarch64 wheels.
- An EMF metric `jt/ForecastModelUsed`.
- Least-privilege read-only IAM, tags, and no SageMaker, EC2 or NAT.
- GLO-30 from AWS Open Data, which is a good blog point.

The Lambda quotas quoted are correct. The weakness is that the ML workstream's live AWS footprint is optional: Lambda is Should and last in the cut order, and the EventBridge hourly inference from the spec is a Could. If cuts happen, ML's AWS story shrinks to "files in S3". Keep the Lambda; it is only about 1 h of work, and the merge gate needs it.

### Innovation: 4/5
- **F6 street thresholds** ("your lane floods when the Old Railway Bridge gauge reads X m") is the project's clearest differentiator over Flood Hub and CWC, at almost no cost.
- **F1, the gauge-level slider**, is physically consistent and visually strong.
- **F4, the honest model card**, ships with a pre-registered split and an improvement loop.

The GAT is honestly framed as a challenger, and the plan says outright that attention weights are not discovered lag times. Not a 5, because the forecasting side is standard: Ridge, persistence and conformal. There is also an unused, high-impact benchmark. CWC itself forecast **"208.75 m by 4 pm"** on 13 Jul at about 08:00. A row reading "our h = 6/8 forecast vs CWC's published forecast vs actual" would be a striking, honest comparison.

### Completeness: 4/5
Workstream B coverage:
- GAT: Should, time-boxed.
- 6/12/24 h forecasts, plus 1 h and 3 h.
- Conformal intervals.
- Training.
- Accuracy monitoring: F4 and the EMF metric.
- Model improvement loop: new anchors → `make eval` → re-select → registry bump.

New features: F6 (Must), F1 and F4 (Should), F2 and F5 (Could), so ≥3 new features is satisfied. Gaps:
- The spec's "EventBridge hourly inference" is only a Could.
- The spec's "inundation IoU vs Sentinel-1" is replaced by in-sample balanced accuracy, which is honestly labelled. The out-of-sample inundation check is therefore only the 10-row table.

### Risk Assessment: 4/5
The risk table is thorough. It covers overrun (High), contamination, late data with a budgeted self-fetch, GAT losing, too few residuals, DSM and datum, bund sealing, the ITO miss, the unverified peak hour, Lambda and GeoJSON weight. Each risk has a concrete degrade path and a cut order. Missing:
- T1, train/serve mismatch: the most likely cause of a bad TEST table.
- T2, demo-window input staleness.
- The not-re-baselined clock.
- The merge-gate and storyboard conflicts.
- Demo-bucket availability at Sat 12:30, which is the same minute Shivansh posts the stack URLs.

---

## Remaining risks / blockers

There are no hard blockers. The **conditional** risks:
1. If the Fri 15:00–20:00 blocks are not done, the Fri 23:00 ML checkpoint slips, and fixtures for Arjav and Saksham are late.
2. If T1 is not fixed, the TEST skill table, which is the core of the "honest forecast" story in the video, is likely to show lagreg ≈ persistence or worse.
3. If T2 is not fixed, the hero-colony fan chart at 13 Jul 00:00 starts about 0.5 m below the observed line, which looks broken on camera.
4. The merge gate at Sat 13:00 cannot pass as written.

---

## Actionable improvements (prioritised)

**P1 (before Sat 14:00)**
1. **Re-baseline §5 to the current clock** (one line per block: done / moved). Post it to the channel with the Fri 23:00 ETA, as Shivansh did.
2. **Sparsify SYN before training (T1).** Sample anchor-like times, rebuild the inputs with `causal.py`, add an `input_age_h` feature, and use the same pipeline for DEV residuals. This takes about 45 min and replaces part of the GAT time box.
3. **Densify the 12–13 Jul night (T2).** Ask Shivansh to add 12 Jul 18:00 207.81 m (press citing the CWC portal) and the 12 Jul afternoon 207.71 m, each with a `source_ref`, plus any 13 Jul early-morning reading he can source. Write `input_age_h` into the forecast-file note, and agree `max(observed, hi_m)` at h = 0 with Saksham.
4. **Resolve the merge gate.** Ship a minimal Lambda (`/forecast`, `/flood` reading static files) on demo by Sat 12:30, or get Shivansh to amend the gate.
5. **Bund floor in gauge units (T3).** After calibration, set `z'_bund ≥ 209.16` (HFL + 0.5 m) on burned line cells, and log it in `calibration.json`.

**P2 (Sat, from slack)**

6. Settle the storyboard surge flag. Either build `UPSTREAM_SURGE` only (about 20 min) or have the shot list changed.
7. Write the model-card generator early (fill it from the DEV metrics on Saturday morning), so that Sat 17:30 is just "freeze + run TEST + regenerate". Give that block 1 h.
8. Add the **CWC 13 Jul forecast vs ours vs actual** row to F4.
9. Make F6 treat never-wet cells as +∞, and calibrate with 4 reconstructions instead of 84.
10. Print n beside every TEST metric. Add a bootstrap 80 % CI on skill vs persistence (5 lines of code).

**P3 (only if green)**

11. TEST-2 on Sep 2025, run as data only.
12. The EventBridge live-mode handler.

---

## Alternatives considered

- **Drop the GAT entirely** and give its 1.5 h to T1, T2 and the model card. Lagreg plus honest conformal intervals is already the story, and §11.6 makes a GAT win unlikely. I recommend this if Friday is behind.
- **Replay-forecast semantics:** instead of strict anchor-causality, treat the hourly PCHIP as a stand-in for the hourly CWC FFS feed that existed in 2023, and use it as the input. Keep the anchor-causal pipeline for the reported TEST skill only. The demo fan chart would look better, but it would be a pseudo-forecast, so it must be labelled. Strict causality plus denser anchors (P1-3) is the more defensible choice.
- **Bund handling:** instead of burning in the DTM, ml could treat embankment lines as a separate "barrier" mask with a crest set to HFL + 0.5 in gauge units. That is cleaner, but it moves work from Shivansh to Vaibhav. P1-5 gets most of the benefit at no cost.
- **What-if slider rendering:** since Arjav has declared it Won't, a 56-frame offline ladder animation (matplotlib or MapLibre screenshot loop) is the realistic path. Script it on Friday night with the ladder writer.

---

## Fact spot-checks

| Claim | Check | Result |
|---|---|---|
| MAPIE v1 `SplitConformalRegressor(confidence_level=0.8)`, `fit → conformalize → predict_interval` | [MAPIE stable docs](https://mapie.readthedocs.io/en/stable/generated/mapie.regression.SplitConformalRegressor.html) | Correct |
| 208.53 m at 10:00, 13 Jul; 208.48 m at 08:00; peak 208.66 m | [Udayavani/PTI](https://english.udayavani.com/article/raging-yamuna-nears-all-time-record-level-in-delhi/1501337), [National Herald](https://www.nationalheraldindia.com/amp/story/national/yamuna-river-hits-a-record-water-level-of-20848m-in-delhi-capitals-secretariat-marooned-by-waterlogging), [SANDRP](https://sandrp.in/tag/metro/) | Correct. SANDRP gives the peak at **18:00** citing CWC, which matches the plan's `ts_verified:false` timestamp. Shivansh may be able to set it to verified with a CWC bulletin. |
| 207.0 m at 04:00 and 207.25 m at 08:00, 12 Jul | [ETV Bharat](https://etvbharat.com/english/state/delhi/yamuna-water-level-rise/na20230712074750010010089) | Correct |
| Anchors missing on the evening of 12 Jul | Press citing the CWC portal: **207.81 m at 18:00, 12 Jul**; CM: 207.71 m that afternoon ([search summary of Deccan Herald / Outlook coverage](https://www.outlookindia.com/national/delhi-yamuna-swells-further-old-railway-bridge-shut-for-train-traffic-news-305201)) | Add both (T2) |
| CWC forecast "208.75 m by 4 pm, 13 Jul" | [National Herald](https://www.nationalheraldindia.com/amp/story/national/yamuna-river-hits-a-record-water-level-of-20848m-in-delhi-capitals-secretariat-marooned-by-waterlogging) | Available as an F4 benchmark |
| Grid ~470 × 790 at 1″ over the bbox | 0.13° × 3600 = 468; 0.22° × 3600 = 792 | Correct |
| `reconstruction(..., method="erosion")` gives minimax fill with seed ≥ mask | skimage semantics | Correct as specified |

---

## Orchestrator follow-up (after the final review)

The cross-plan issues raised in this review and in the other three final reviews were resolved centrally in **SHARED_RESOURCES.md §11.8 (contract v1.2)** on `main`. Where §11.8 differs from this plan, §11.8 wins. The resolutions cover: the data-driven demo timestamp `T_hero`, the SHELTER_IN_PLACE path for already-wet colonies, the time-to-water definitions, amber using a window maximum, a single per-edge cutoff implementation, the bund floor applied in gauge space, calibration hold-outs, causal training inputs, always-written optional artefacts and 403 treated as absent, scenario-scoped paths, Bedrock IAM for inference profiles, frontend zip deploy, version pins, and volunteer-coordination scope. The owner should re-check their timeline against §11.7 / §11.8 at the Fri 23:00 sync.
