# Quality Review, round 3: Shivansh's plan (Data Pipeline & AWS Infrastructure: `pipeline/`, `infra/`, `shared/`)

Reviewer: independent senior technical reviewer (not the author of rounds 1–2) · Reviewed: Fri 9 Oct 2026, ~20:15 · Plan reviewed: `shivansh/IMPLEMENTATION_PLAN.md` **v1.1** (re-baselined Fri 20:00). I checked it against `main/SHARED_RESOURCES.md` (SR) including **§11 Contract amendments v1.1**, `main/INTEGRATION_PLAN.md`, the round-2 review, and the current plans of Vaibhav, Saksham and Arjav where they depend on this one.

| Criterion | Rating (1–5) | Round 2 |
|---|---|---|
| Technical Soundness | 4 | 4 |
| Feasibility (~25 h, one person, from Fri 9 Oct) | 3 | 4 |
| Integration (conforms to v1.1 contracts) | 4 | 4 |
| AWS Alignment | 4 | 5 |
| Innovation | 4 | 4 |
| Completeness (assigned scope + ≥3 new features) | 4 | 4 |
| Risk Assessment | 4 | 5 |
| **Total** | **27 / 35 → 15.4 / 20** | 30 / 35 → 17.1 / 20 |

**Verdict: APPROVED (>=15/20)**, narrowly.

The v1.1 rewrite closes the round-2 datum defect (C1) properly, and it now conforms to SR §11 almost everywhere. I score it lower than round 2 for three reasons:
- The plan was re-baselined at 20:00 but does not say which of the 4 h of pre-20:00 "baseline" rows are actually done.
- Two Must blocks (Fri 19:30 SAM v0, Sat 11:00 infra v1) are under-estimated, and the authoring of CloudFront, Amplify and SNS has no slot of its own.
- Several new technical defects appeared in the calibration set and the burn layer, and they touch the hero colony and the headline WTP claim.

None of these needs a redesign. Approval is conditional on items P1–P4 in §4, all done before Sat 08:30.

---

## 0. Resolved since the previous review

| # | Round-2 item | Status in v1.1 |
|---|---|---|
| C1 | Flat-plane Δ fit, stacked offsets, planar exposure/envelope | **Resolved.** `corridor_dtm.tif` is on EGM2008 with Δ = 0; `meta.json.delta_m=null, calibrated_by="ml/calibrate.py"`; Vaibhav is the sole fitter of δ and S (SR §11.1, Vaibhav §3.2 step 8). Infra Exposure samples `onset.tif`/`cutoff_0p30.tif` (`method:"onset_v1"`), and the envelope uses onset ≤ HFL + 3 m, so neither does `level − ground_elev_m` arithmetic. The embankment guard is gone |
| C2 | DEM/river delivered after Vaibhav's inundation block | **Resolved.** `river.geojson`, `centreline.geojson` and DTM v0 (raw clip) ship at **Fri 18:05**, before his 18:45 slot. He keeps a 45-min self-fetch fallback |
| C3 | Backup-deployer dry run collided with Saksham's routing block | **Only partly resolved.** This plan moves it to **Arjav, Sat 21:00–21:30**. But Arjav's plan still shows Sat 21:00–21:30 as "Slack (bug fixes only)" with no dry run and no prerequisite install, and **Saksham's plan still schedules the dry run at Sat 12:30–13:00** (his line 210). The dry run also "follows only `infra/README.md`", which is not written until **Sun 10:00**. See P3 |
| R4 | Calibration-point collection overloads Sat 08:30 | **Resolved** (moved to Fri 22:00–22:30). The 30 min allowed is optimistic (round 2 estimated about 1 h) |
| — | Sparse OSM bunds | **Resolved** with a name selector (`Pushta|Bund|Marginal`) and a QGIS check. **This creates a new risk; see T2** |
| R5 | Golden test only on Sunday | **Resolved.** First golden run Sat 18:45 (may be red); Sun 09:00 must pass |
| R6 | SR §5.1 edit and the HydroSwift answer | **Resolved / moot.** Nullable `level_m` is adopted in SR §11.3; the HydroSwift "no" was posted to Vaibhav at 16:30 |
| R7 | Re-baseline to the real start time; cut 2025 now | **Mostly resolved.** Re-baselined at 20:00, and `yamuna-2025-09` is cut to Could. **But the completion status of the pre-20:00 rows is not stated (F1)** |
| R8 | Confirm SNS subscriptions | **Resolved** (Sat 11:00 block, `smoke.sh`, README checklist) |
| — | Missing risks: slope/double offset, wall-clock slip | **Resolved.** Both are now in the §11 risk table |
| — | Vaibhav's ask (e), a SAM review of his section | **Resolved.** Named in the Sat 11:00 block |
| — | SR §11 conformance | **Resolved:** `edge_id = osm:<min>:<max>:<key>`, envelope `roads.geojson`, `GET /colonies` without contacts, `free_beds`, manifest `issued_at[]` with a CI join test, root `make replay-local` per §11.5, §11.7 checkpoints as schedule rows with cut lines |

---

## 1. Ratings with explanation

### Technical Soundness: 4/5

**Strengths**
- The DTM pipeline is now well designed:
  - DSM → (FABDEM | GLO-30 3×3 min + median) → embankment burn
  - bridges kept off the raster and recorded on edges as `is_bridge`/`elev_min_m`, so the connectivity fill is not dammed
  - one shared calibration set, with published exclusions (ITO, Supreme Court and Rajghat, all Drain No. 12 backflow)
- The `edge_id` scheme is deterministic and direction-agnostic. It is minted once and stored, and it is tested for stability across two runs on the cached response.
- The single OSMnx query (`network_type="walk"` + `custom_filter`) is correct. A custom filter overrides the preset's way filter, and bidirectionality still follows `network_type`. A side effect is that it also avoids the 2.0.1 change that makes the `walk` preset drop ways with separately mapped sidewalks.
- PCHIP between anchors (monotone, no overshoot past the peak) is the right interpolator. The QC rules are concrete, and "the pipeline never synthesises levels" holds the line on honesty.
- The "envelope only ever grows" rule is a clean way to keep Saksham's join from breaking when the envelope is re-exported.

**Defects**
- **T1. The burn floor (210.0 m) is in EGM2008 but is applied before δ is known.**
  - Vaibhav fits δ ∈ [−3, +2] m afterwards, so the effective crest of a burned bund in gauge terms is anywhere from about 207 to 212 m.
  - At δ ≈ −2 the bunds sit *below* the 208.66 m HFL, the model overtops them, and large parts of trans-Yamuna East Delhi go wet. That would contradict 2023, when the bunds largely held.
  - The burn value was agreed with Vaibhav, so this is a joint defect. It is still real.
  - Fix: either ship the burn **mask** as a separate artefact (`static/dem/burn_mask.tif`) and let `calibrate.py` re-apply the floor in z′ (gauge) space after fitting, or have `calibrate.py` assert `z′ ≥ HFL + 0.5 m` on burn cells and log any violations.
- **T2. The name regex `Pushta|Bund|Marginal` can seal the hero colony.**
  - Lanes inside **Yamuna Pushta** (`DEL-YP-04`, the hero colony) and floodplain-side service roads often carry "Pushta" in their name. Burning them to ≥210 m would make the hero colony dry, and golden check §9.2 ("flood intersects Yamuna Pushta") would fail.
  - Fix:
    - restrict name matches to `highway ∈ {primary, secondary, tertiary}` with way length > 300 m
    - freeze the selected way ids into `burn_ways.csv` after the QGIS look
    - add a test that no colony centroid or wet calibration point lies inside the burn mask
- **T3. Calibration candidates lie outside the modelled domain.**
  - **Jaitpur khadar** is at about 28.50–28.51 N, which is **outside the SR §2 bbox** (minLat 28.53).
  - **Madanpur Khadar** sits at or just below the Okhla barrage.
  - Parts of **Sonia Vihar khadar** are at the Wazirabad barrage (28.712 N), and Vaibhav's chainage clip makes everything upstream of it `nodata`.
  - Points in nodata cells are always "dry", so wet points there bias δ upward. They also put the "≥ 5 wet per third" rule at risk in the ITO–Okhla third.
  - Fix: a `test_dem` assertion that every non-excluded point is inside the bbox *and* inside Vaibhav's Wazirabad–Okhla chainage clip. Replace points that fail.
- **T4. The headline Infra Exposure moment is in-sample.**
  - **"Wazirabad pump house"** and **"Okhla WTP apron"** are *wet calibration points*. The model is then fitted to flood exactly those assets, so "Wazirabad WTP flagged N h before the 13 Jul shutdown" is not a prediction.
  - Fix: hold the WTP sites out of `calib_points.csv` (mark them `excluded=true, reason="held-out validation"`), or label the claim "in-sample" in the provenance ledger and the video.
- Minor:
  - **Underpasses** (`tunnel=yes`, `layer<0`) flood mainly from rain and drain surcharge, not river overbank. River `onset.tif` will mislabel them. Drop them, or label them "river-only".
  - **The envelope fallback** (`elev_min_m ≤ 211.66` when `onset.tif` is late) has no connectivity filter. On EGM2008 heights it can select most of the trans-Yamuna network and blow the 8 MB cap. Restrict it to edges within about 2 km of `centreline.geojson` on the river side of the burn lines.
  - **Seeds:** `Colony.ground_elev_m` on EGM2008 sits next to gauge levels in the same UI and invites exactly the comparison §11.1 forbids. Ask Arjav not to display it, or name it `ground_elev_egm2008_m` in the static GeoJSON.

### Feasibility: 3/5
- **The arithmetic adds up.** I re-summed every block:
  - Fri: 7.5 h work + 0.5 h buffer
  - Sat: 9.0 h + 2.5 h
  - Sun: 4.0 h + 0.75 h, plus 1.5 h on call
  - That gives 20.5 h of work + 3.75 h of buffer = 24.25 h, matching the TL;DR (Must 18.75 + Should 1.75).
- The Must path is front-loaded, the cut lines are explicit at every SR §11.7 checkpoint, and the cut order at 20:00 is pre-committed. The plan is not over-scoped *on paper*. These are the reasons it reaches 3.
- **F1. The re-baseline status is ambiguous.**
  - The plan was written at about 20:00 Fri. It calls the 15:00–19:30 rows (PR #1, digitisation, DTM v0, river, `clean.py`, PR #2: 4.0 h of Must work) the "committed baseline", but it never says whether they are **done**.
  - If they are not done, the stated rule ("runs next, pushes into the Fri buffer") pushes up to 4 h into a 0.5 h Friday buffer. Everything from SAM v0 onward then slides into Saturday, which has only 2.5 h of buffer.
  - Fix: add a status column (done / partial / not started) to the Fri table before 21:00.
- **F2. Two Must blocks are under-estimated.**
  - **Fri 19:30–20:45 (1.25 h):** the first SAM template, with bucket, lifecycle, 5 tables, HTTP API, a 5-route `catalog-fn` with ETag cache and the SR §7 error envelope, the budget and the Scheduler, plus a working `dev` deploy and `smoke.sh`.
  - **Sat 11:00–12:30 (1.5 h):** a demo deploy, data CloudFront with OAC + CORS + Range/ETag, S3 CORS, the Amplify App + Branch with `CustomRules`/headers, `deploy_frontend.sh`, SNS + confirmations, `secrets.sh`, Outputs, reviewing two teammates' SAM sections, the PMTiles upload, **and** the merge gate.
  - **Writing** the CloudFront, Amplify, SNS and alarm resources has no slot anywhere. Each first CloudFront create is a 5–15 min wait, and one CORS or OAC mistake costs another cycle. This is the block most likely to miss the 12:30 hand-off that Arjav, Vaibhav and Saksham all depend on.
- **F3. Smaller over-packs.**
  - Calibration points: 30+ geocoded, source-referenced rows in 30 min.
  - Seeds: about 10 colonies with `name_hi` and vulnerable breakdowns, about 8 shelters, `seed_ddb.py`, envelope (ii) and the data bundle, all in 1 h.
  - Sat 08:30–10:00: DTM v1, burn, QGIS, graph elevations, final graphml and `test_dem`, in 1.5 h.
- **F4.** Shivansh is still the integration hub. Every teammate slip lands in his Sat 17:15 sync, 18:45 golden and 20:00 Buffer B. Buffer is 15% of total time (3.75 of 24.25 h), against a Must load of 91% of work hours.

### Integration: 4/5
**Strengths:**
- Conforms to SR §11 in every place I checked:
  - §11.1 datum ownership
  - §11.2 artefact paths: `corridor_dtm.tif`, `meta.json`, `calib_points.csv`, `river`/`centreline`, `gauges.json`, `provenance.json`, `infra/<valid_at>.json`
  - §11.3 nullable gauges, `glofas`, `source_ref`, manifest keys, `edge_id`, envelope, edge attributes, `free_beds`
  - §11.4 `GET /colonies` without contacts, and the ladder that takes the GETs off the demo path
  - §11.5 root `make replay-local` order
  - §11.6 Amplify manual zip, S3 CORS, SNS confirmation
  - §11.7 checkpoints
- The give/need tables (§12/§13) line up with teammates' times:
  - Vaibhav: DTM Sat 10:00 vs his 11:00 need
  - Saksham: graph 22:00 vs his 22:15 ack
  - Arjav: stack URLs 12:30
- CloudFront covers `models/inundation/*`, as Vaibhav asked.

**Deductions:**
- **I1. Backup deployer.** Three plans disagree (C3 above). The dry run also depends on a README that is scheduled after it.
- **I2. Calibration points vs Vaibhav's domain clip** (T3). This is a contract-level mismatch between §11.1's `calib_points.csv` and §11.2's `onset.tif` nodata convention.
- **I3. Timing drift.**
  - §13 says "`feature/shivansh` merged Sat 11:00", and INTEGRATION_PLAN §1 also says 11:00. But the merge gate needs `/health` on **demo**, which is only deployed inside the 11:00–12:30 block, so the real merge time is about 12:30.
  - PR #2 (the real curve) is promised at 19:00, while the header says teammates assume 18:45.
  - Either align the documents or tell the channel.
- **I4.** INTEGRATION_PLAN §4 step 3 still lists a "CloudWatch dashboard" and a Git-connected Amplify. The plan correctly cuts or changes both, but the main-branch document should be updated so the backup deployer isn't misled.

### AWS Alignment: 4/5
**Strengths:**
- The serverless, low-cost design is correct:
  - HTTP API, python3.13 arm64 zip Lambda
  - one role per function, scoped to prefixes
  - OAC with Block Public Access and a prefix-scoped bucket policy
  - on-demand DynamoDB
  - S3 lifecycle (`raw/` at 30 d, abort incomplete multipart uploads at 1 d)
  - SSM SecureString created by a script (CloudFormation can't create it)
  - an `AWS::Budgets::Budget` defined once, because a notification change forces replacement
  - SAM-managed ECR repos with keep-3
  - no NAT, EC2 or SageMaker
  - a credible estimate of under $2
- Copernicus GLO-30 is read from the **AWS Open Data Registry**, which is a strong "built on AWS" line.
- I checked that `AWS::Amplify::App` accepts `CustomRules` (a list) and `CustomHeaders` (a string) for a repository-less app with manual deploys.

**Deductions:**
- **A1. No cache-invalidation or TTL plan for re-published data.**
  - `make sync` re-publishes `scenarios/*` and `static/*` at least four times: Sat 13:45, Buffer B, after Vaibhav's 19:45 rebuild, and Sun 11:00.
  - With a default managed cache policy (`CachingOptimized`, 24 h default TTL), the deployed URL can serve a **stale `manifest.json`, roads or envelope** next to fresh files. That is a silent integration bug on the judge-facing URL.
  - Fix: `make sync` either runs `aws cloudfront create-invalidation --paths "/scenarios/*" "/static/*"` (cents at this scale, and well inside the free 1,000 paths) or uploads with `Cache-Control: no-cache` for `manifest.json`, `index.json` and `roads.geojson`.
- **A2.** The spec's "EventBridge: hourly inference cycles" is delivered as a DISABLED Scheduler stub with no target described. A live-mode toggle that ticks `catalog-fn`/`health` once an hour would make the service real for a few cents. As written, a judge reading the architecture slide sees EventBridge that does nothing.
- Minor: CloudWatch Logs retention is not set (it defaults to never expire). Set 7 days on every function's log group in the template.

### Innovation: 4/5
- **Critical-Infrastructure Exposure** sampled on Vaibhav's onset and cutoff rasters is the most distinctive feature. "Which hospital, metro entrance or WTP goes under, and when" is concrete and checkable against the 13 Jul 2023 Wazirabad/Chandrawal/Okhla WTP shutdowns. **T4 must be fixed** or the best moment in the video is in-sample.
- The **Provenance & QC ledger** directly operationalises SR §1. It openly says that hourly values are PCHIP-imputed, that the peak hour is unverified and that upstream levels are synthetic. That is strong defence against judges' questions.
- The **embankment-aware DTM with one shared calibration set** is the real gauge → street enabler, though it is invisible plumbing.
- The **ERA5 rain strip** is small but useful. The 2025 replay is now Could.
- Not 5, because two of the four scheduled features are plumbing or context, and both Should features are on the cut list.

### Completeness: 4/5
- The assigned scope is covered:
  - gauge ingestion: CWC bulletins and news anchors digitised with `source_ref` (the spec's "CWC API" does not exist publicly, and this is documented)
  - Open-Meteo GloFAS/ERA5
  - Copernicus DEM from AWS Open Data
  - OSMnx graph
  - cleaning/QC
  - S3 layout and lifecycle
  - the shared SAM stack
  - seeds in DynamoDB
  - the replay manifest
  - root `make replay-local`, CI join tests, golden/offline runs, README and blog assets
- New features: Provenance ledger, Infra Exposure, embankment-aware DTM + shared calibration set, ERA5 context, 2025 replay (Could). That is ≥3.
- **But** only the DTM enhancement is Must. At the Sat 14:00 cut line ("my items late"), Provenance and Infra Exposure are both dropped, and ERA5 is the first Friday cut. In that branch the plan delivers one new feature. Delivery of three is therefore likely but not guaranteed.
- Reduced or omitted relative to the spec:
  - IMD rainfall (replaced by ERA5, with a stated reason)
  - EventBridge (a stub)
  - Sentinel-1 IoU (Could)
  - SNS/Pinpoint SMS (email only, per SR §4)
  All are justified, but they are visible to a judge who reads the spec literally.

### Risk Assessment: 4/5
- The risk table is broad and every row has a concrete degrade path:
  - FABDEM late
  - OSM bunds missing
  - `onset.tif` late
  - roads.geojson too heavy
  - Overpass/Open-Meteo down
  - Shivansh as single point of failure
  - Docker/SAM missing on the backup laptop
  - CloudFront/Amplify latency
  - circularity of synthetic upstream levels
  - SAM merge conflicts
- The checkpoint rows, cut lines and pre-committed cut order are good discipline.
- **Missing:**
  - the burn floor vs δ (T1)
  - the name regex sealing the hero colony (T2)
  - calibration points outside the domain (T3)
  - in-sample WTP validation (T4)
  - stale CloudFront cache after re-sync (A1)
  - the backup-deployer dry run depending on an unwritten README (I1)
  - the unknown completion status of the pre-20:00 baseline (F1)
- The "wall-clock slip" row says likelihood "Med" with no quantity. It should state how much slip the 3.75 h buffer absorbs before the Should column is cut.

---

## 2. Remaining risks and blockers (ranked)

| # | Risk / blocker | Severity | Owner |
|---|---|---|---|
| F1 | Pre-20:00 baseline status unknown; up to 4 h of slip into a 0.5 h Friday buffer | High | Shivansh |
| F2 | Sat 11:00–12:30 infra block overloaded; CloudFront/Amplify/SNS authoring has no slot; three teammates wait on 12:30 | High | Shivansh |
| T2 | `Pushta` name burn seals Yamuna Pushta → golden §9.2 fails | High | Shivansh + Vaibhav |
| T1 | EGM2008 burn floor + δ ∈ [−3, +2] → bunds can sit below HFL | Med-High | Vaibhav + Shivansh |
| T3/I2 | Calibration points outside bbox / chainage clip bias δ and break the per-third rule | Med | Shivansh |
| A1 | CloudFront serves stale `scenarios/*` after re-sync | Med | Shivansh |
| I1 | Backup deployer: three plans disagree; README written after the dry run | Med | Shivansh + Arjav + Saksham |
| T4 | Headline WTP claim is in-sample | Med (credibility) | Shivansh |
| I3 | Merge time (11:00 vs ~12:30) and PR #2 time (18:45 vs 19:00) drift | Low | Shivansh |

## 3. Deal-breakers
None outright. P1–P4 below are **approval conditions**. Each takes 30 minutes or less, and all must be done before Sat 08:30.

## 4. Actionable improvements (prioritised)
1. **P1 (F1):** add a status column to the Fri table now. If more than 1 h of pre-20:00 work is not done, apply the Friday cut line immediately: drop ERA5, move calibration points to Sat 08:30, and give Saksham his own 3×3 km pull. Post the real ETAs for PR #2 and the river/DTM v0 in the channel.
2. **P2 (F2):** write the **complete** `template.yaml` in the Fri 19:30 block (CloudFront, OAC, CORS, Amplify App/Branch, SNS, alarms, outputs) and deploy it to `dev` on Friday night. The Sat 11:00 block then becomes `sam deploy --config-env demo` plus verification. If Friday runs out, take the time from Provenance (0.5 h) rather than from Buffer A. Reduce `catalog-fn` to `/health` + `/scenarios` + `/colonies` from the start; the ladder doesn't need the rest.
3. **P3 (I1):**
   - Write a 15-line `infra/README.md` runbook skeleton in Sat Buffer B (20:00–21:00), **before** the 21:00 dry run.
   - Get Arjav to put the dry run and the prerequisites install into his plan explicitly.
   - Ask Saksham to delete his Sat 12:30–13:00 dry-run row (that time is useful to him).
4. **P4 (T2, T3, T4):**
   - In `test_dem`, assert that:
     - every non-excluded calibration point is inside the bbox and Vaibhav's chainage clip
     - no colony centroid or wet point falls inside the burn mask
   - Restrict the name selector to major `highway` classes and ways longer than 300 m, and freeze `burn_ways.csv`.
   - Replace Jaitpur, Madanpur Khadar and any Sonia Vihar point north of 28.712 N.
   - Mark Wazirabad pump house and Okhla WTP as `excluded=true, reason="held-out validation"`.
5. **T1:** ship `static/dem/burn_mask.tif` (uint8) next to the DTM. Agree with Vaibhav that `calibrate.py` re-applies `z′ ≥ HFL + 0.5 m` on mask cells after fitting δ and S. Record `burn_floor_space:"gauge"` in `calibration.json`.
6. **A1:** `make sync ENV=` ends with a CloudFront invalidation of `/scenarios/*` and `/static/*`, or uploads manifests and indexes with `Cache-Control: no-cache`. Add a smoke check that `manifest.built_at` on CloudFront equals the local value.
7. **I3:** state the merge as "Sat ~12:30 (after the demo `/health`)" in §13, and ask the INTEGRATION_PLAN steward (Shivansh himself) to update §1 row 1 and §4 step 3 (no dashboard; Amplify manual zip).
8. **A2 / minor:**
   - Give the DISABLED Scheduler a real target (an hourly `catalog-fn` live-gauge stub) so EventBridge on the architecture slide is honest.
   - Set Logs retention to 7 d.
   - Drop underpasses from Infra Exposure or label them "river-only".
   - Restrict the envelope fallback to the river side of the burn lines and within 2 km of the centreline.
9. **Risk table:** add rows for T1–T4, A1 and I1, and quantify the slip the 3.75 h buffer absorbs before Should items are cut.

## 5. Alternatives worth considering
- **Frontend on the data CloudFront from day one** (`web/` prefix, one distribution, one CORS origin), with Amplify only as a stretch goal. This removes one stack resource and one 5–15 min create from the Sat 11:00 critical block. The cost is a weaker "Amplify Hosting" line; the S3 `web/` fallback is already planned, so this only swaps primary and fallback. Keep Amplify if P2 lands on Friday.
- **Burn as a separate mask rather than baked into the DTM** (T1). This keeps the DTM a pure surface and lets the only fitter of δ and S own every datum-dependent value.
- **Hold-out validation set:** split `calib_points.csv` into `fit` and `holdout` (the WTPs plus 3–4 well-sourced wet and dry points). Vaibhav reports balanced accuracy on the holdout set. This turns the infra-exposure moment and the blog's "reported vs model" table into honest out-of-sample evidence and matches SR §11.6's evaluation-honesty rule.
- **Seeds from a hand-curated CSV only** (no OSM polygon matching) with 6 colonies instead of about 10, if Sat 10:00–11:00 overruns. The golden test only needs the hero colony, the backup hero and the shelters they route to.

---

### Sources consulted for spot-checks
- [AWS CloudFormation `AWS::Amplify::App`](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-amplify-app.html): `CustomRules` (list of `CustomRule`) and `CustomHeaders` (string) confirmed
- [OSMnx changelog](https://data.safetycli.com/changelogs/osmnx): 2.0 bbox order (left, bottom, right, top); 2.0.1 `walk` preset drops ways whose sidewalks are mapped separately (not applicable with a custom filter)
- [OSMnx custom-filter example (v2.0.2)](https://nbviewer.org/github/gboeing/osmnx-examples/blob/v2.0.2/notebooks/08-custom-filters-infrastructure.ipynb): `custom_filter` overrides the preset's way filter
- [Wazirabad barrage (Wikipedia)](https://en.wikipedia.org/wiki/Wazirabad_barrage): 28.7124 N, 77.2332 E (Vaibhav's chainage clip)
- [Jaitpur, Badarpur coordinates](https://www.findlatitudeandlongitude.com/l/Jaitpur%2C+Badarpur%2C+New+Delhi/531468/) and [Indiamapia: Jaitpur, South Delhi](https://indiamapia.com/South_Delhi/Jaitpur.html): about 28.50–28.51 N, south of bbox minLat 28.53
- [Nanaksar–Sonia Vihar metro](https://metrogo.in/station/nanaksar-sonia-vihar-delhi-metro-station): 28.709 N. The Sonia Vihar khadar extends north of it toward the barrage clip, so each point must be checked
- Cross-plan checks:
  - `vaibhav/IMPLEMENTATION_PLAN.md` §3.2 (burn rule, δ ∈ [−3, +2], chainage clip, DTM need Sat 11:00)
  - `saksham/IMPLEMENTATION_PLAN.md` Sat 12:30–13:00 dry-run row and 22:15 graph ack
  - `arjav/IMPLEMENTATION_PLAN.md` Sat 21:00–21:30 slack row and 12:30 deploy dependency
  - `main/INTEGRATION_PLAN.md` §1 merge row 1 and §4 step 3

---

## Orchestrator follow-up (after the final review)

The cross-plan issues raised in this review and in the other three final reviews were resolved centrally in **SHARED_RESOURCES.md §11.8 (contract v1.2)** on `main`. Where §11.8 differs from this plan, §11.8 wins. The resolutions cover: the data-driven demo timestamp `T_hero`, the SHELTER_IN_PLACE path for already-wet colonies, the time-to-water definitions, amber using a window maximum, a single per-edge cutoff implementation, the bund floor applied in gauge space, calibration hold-outs, causal training inputs, always-written optional artefacts and 403 treated as absent, scenario-scoped paths, Bedrock IAM for inference profiles, frontend zip deploy, version pins, and volunteer-coordination scope. The owner should re-check their timeline against §11.7 / §11.8 at the Fri 23:00 sync.
