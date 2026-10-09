# Quality Review (v1.1 re-review): Arjav, Frontend & Visualization (`frontend/`)

Independent re-review of `arjav/IMPLEMENTATION_PLAN.md` v1.1, checked against `main/SHARED_RESOURCES.md` (SR, including §11 "Contract amendments v1.1"), `main/INTEGRATION_PLAN.md`, the teammates' v1.1 plans (Shivansh, Vaibhav, Saksham) and the spec's Workstream A. Today is Fri 9 Oct 2026. Submission is Sun 11 Oct. The budget is about 25 focused hours for one person.

| Criterion | Rating (1–5) |
|---|---|
| Technical Soundness | 4 |
| Feasibility (~25 h, one person, from Fri 9 Oct) | 4 |
| Integration (conforms to SR v1.1) | 4 |
| AWS Alignment | 4 |
| Innovation | 4 |
| Completeness (assigned scope + ≥3 new features) | 4 |
| Risk Assessment | 4 |
| **Total** | **28 / 35 → 16.0 / 20** |

**Verdict: APPROVED (>=15/20)**

This is a clear pass, not a narrow one. Both earlier deal-breakers (the Amplify build spec and the missing dependency-slip trigger) are fixed. All seven technical findings and all four scope cuts were acted on, and the schedule now adds up, with 3.25 h of real slack. It is not a 5 across the board, for three reasons. The rewritten time-to-water band now collapses against Saksham's definition of `t_submersion`. Some degrade paths have subtle failure modes: S3 returns 403 for missing objects behind OAC, and a `+` in `?at=` gets decoded as a space. And the plan has drifted from `INTEGRATION_PLAN.md` on the merge gate and the demo storyboard.

---

## Resolved since previous review

| Prev. item | Status | Evidence in v1.1 |
|---|---|---|
| **Deal-breaker 1 / T1**: Amplify monorepo build spec | **Resolved** | `frontend/amplify.yml` is removed. The app uses a manual zip deploy through Shivansh's `deploy_frontend.sh`, and Shivansh's plan agrees (`create-deployment → zip → start-deployment`, App + Branch with `CustomRules`). The AWS docs confirm manual deploys need no Git repo or build spec. A root `amplify.yml` is used only if the app becomes Git-connected. The S3 `web/` fallback is kept |
| **Deal-breaker 2 / P2**: dependency-slip trigger | **Resolved** | All five SR §11.7 checkpoints are in §6, each with a cut line. Sat 14:00 decides the recording data source, and integration has a hard stop at 17:30 |
| S1: 2-mode GET ladder | Resolved | GETs go static → fixtures, and the API handles writes only. `api` GET mode is Won't (matches SR §11.4) |
| S2: Lite merged into Colony | Resolved | `?lite=1` on `/colony/:cid` |
| S3: Playwright on the deployed URL moved to Should | Resolved | Now a Sun 09:00 Should |
| S4: Saturday buffer | Resolved | Contrast mode is a Sun Could. Slack is 0.5 h Fri, 1.25 h Sat and 1.5 h Sun |
| T2: PMTiles 206 caching | Resolved | No SW route for `*.pmtiles`. "Offline" is defined as the colony pack in §0, §8.1 and the demo flow |
| T3: band inconsistent with hydraulics | **Partially resolved; see N1** | The plan now uses `L* = wet_at_level_m` and has no `ground_elev_m` arithmetic or clamping. But "centre = `t_submersion`" no longer holds once Saksham's definition is taken into account |
| T4: bundle size | Resolved | Lazy `MapView`, dynamic `import('maplibre-gl')`, and a `check-size.mjs` gate of ≤100 KB gz |
| T5: static-mode rules | Resolved | Rules table in §3, unit-tested. `issued_at[]` is adopted in the manifest |
| T6: S3 GET CORS for audio; desktop speechSynthesis | Resolved | Adopted in SR §11.6. The device voice is documented as online-only on desktop |
| T7: Ring Road by name | Resolved | Uses `avoid[].edge_ids[]` with a name-match fallback |
| P1: contract PR | Superseded | Every ask is adopted in SR v1.1. Only the fixture PR remains |
| P3: NGT 207.1 m caption | Resolved | Used only if quoted by Sat 22:00 |
| P4: deadline | Partially | Assumed 18:00 IST, confirmed Fri 24:00, with a rule to move every slot earlier if needed. Acceptable |
| Stacked CloudFront | Resolved | §12: Amplify's own CDN serves the app. The data CloudFront serves data only |
| Hindi names only from payloads | Resolved | §5 |

## Spot-checks (9 Oct 2026)

| Claim | Check | Result |
|---|---|---|
| maplibre-gl 5.24.0 (23 Apr) is the last 5.x; 6.0.0 on 22 Jul | npm `time` | Confirmed. The latest release is 6.13.0 (6 Oct) |
| vite-plugin-pwa 1.3.0 (5 May) peers `vite ^8`; 2.0.0 is from 3 Oct | npm | Confirmed |
| "every release ≥14 days old"; `vite` **8.3.3** | npm | **Contradiction.** 8.3.3 was published **6 Oct (3 days old)**. 8.3.1 (24 Sep) or 8.3.0 (10 Sep) meets the rule. 8.3.3 was a coordinated multi-line patch (6.4.4, 7.3.7, 8.2.4 and 8.3.3 all on 6 Oct), which suggests a security fix. If that is why it was chosen, say so. Similarly, `vitest` "5.0.x": 5.0.3 is 9 days old, so pin 5.0.2 (25 Sep). `@tanstack/react-query` latest 5.104.1 is from 2 Oct, so pin ≤ 5.103.2 (21 Sep) |
| plugin-react 6.1.1, React 19.2.8, TS 6.0.3, zustand 5.0.15, pmtiles 4.5.0, basemaps 5.7.2, json-schema-to-typescript 16.0.0, workbox-window 7.4.1, idb-keyval 6.3.0, Playwright 1.63.0 | npm | All exist and are ≥14 days old. plugin-react 6.1.1 peers `vite ^8` |
| Amplify manual deploy without Git | [AWS docs](https://docs.aws.amazon.com/amplify/latest/userguide/manual-deploys.html), [StartDeployment](https://docs.aws.amazon.com/amplify/latest/APIReference/API_StartDeployment.html) | Confirmed: `create-deployment` → upload the zip → `start-deployment` within 8 h. Not supported for SSR, which does not affect this static SPA |
| `unreachable.json` "404 → `[]`" via the data CloudFront | [re:Post: S3 403 vs 404](https://repost.aws/knowledge-center/s3-rest-api-cloudfront-error-403) | **Gotcha.** Behind OAC, S3 returns **403** for a missing key unless the principal has `s3:ListBucket`. Shivansh's bucket policy grants ListBucket only to `catalog-fn`, not to CloudFront. See N2 |

---

## Per-criterion explanations

### Technical Soundness: 4/5
**Strengths.** The plan has a single replay clock snapped to `manifest.valid_at[]` and mirrored to the URL. Query keys include `at`, with prefetch. The map is driven imperatively with feature-state joined on the opaque `edge_id`. `depth_class` is drawn as GeoJSON instead of the 4326 COG, which is correct. Terrain is bundled as whole-file 200s and is cacheable, and the SPA rewrite excludes `.png` so a missing tile is a 404 and not HTML. The pure, unit-tested `static.ts` and `tsub.ts` are good. "Failed validation is never rendered without the fallback banner" is tested. The plan keeps credentials out of the browser and uses presigned POST with conditions.

**Issues:**
- **N1. The band collapses: "centre" = "earliest".** Saksham defines `t_submersion` as the **first time `hi_m` reaches `wet_at_level_m`**, and Vaibhav's F6 says the same. The plan sets centre = `t_submersion − at` and earliest = the first time `hi_m ≥ L*` with `L* = wet_at_level_m`. These are the same instant. The example "about 3½ h (earliest 2 h 40 m)" can never occur, and the "Done when" (the centre matches `lead_time_h`) checks the conservative bound, not a central estimate. **Fix (pure, ~15 min):** earliest = `plan.t_submersion` (the hi crossing, which is what the routing used). Centre = first time the interpolated central `level_m ≥ L*`. Latest = first time `lo_m ≥ L*`, or "may not flood". Since lo ≤ level ≤ hi at every horizon, the crossing times are ordered earliest ≤ centre ≤ latest by construction. Update the Done-when to "earliest == `lead_time_h`". The headline copy should say "earliest about X h", which is also the safer message for residents.
- **N6. `+05:30` in the URL query.** The plan mirrors `?at=2023-07-13T00:00+05:30`. `URLSearchParams` and form decoding turn `+` into a space, so deep links, Director keyframes and Playwright URLs can break. Write `at` with `URLSearchParams.set` (it encodes `+` as `%2B`), or use a compact `?at=20230713T0000`. Also, the plan uses both `T00:00:00+05:30` and `T00:00+05:30` forms. Rule: **S3 key segments are the manifest's `valid_at[]` / `issued_at[]` strings verbatim**. Never re-serialise them through `Date`. Add one unit test for this.
- Smaller items: pydantic v2 exports JSON Schema **2020-12**, so use `Ajv2020` (`ajv/dist/2020`), not the default draft-07 `Ajv`, or every fixture "fails". `ext.replanned_due_to` is not in any SR schema (Saksham lists "ext yes/no" as an open huddle item), so keep the re-routed badge optional and out of every Done-when. Set `bounds` on the bundled `raster-dem` source to stop out-of-bbox tile 404s.

### Feasibility: 4/5
The hours now add up: Fri 4.0 + 0.5 slack, Sat 10.25 + 1.25, Sun 5.5 + 1.5, about 23 h. The Must column is about 12 h. Every SR §11.7 checkpoint has a cut line, and the cut order at the freeze is explicit and never touches Must. Could items (Report) are not scheduled at all, which is correct. Not a 5, because several slots are still optimistic:
- **Fri 20:30–21:30 (1 h):** the ladder, static rules, `+` encoding, write stub, 5×3 thin mocks and ajv over every fixture. Realistically this is 1.5–2 h.
- **Fri 21:30–23:00 (1.5 h):** lazy map, basemap, three layers, store, scrubber and URL sync. This is likely to spill into the Fri slack.
- **Sat 17:30–18:45 (1.25 h):** PWA plus the full offline pack (IndexedDB, auto-save on approve, audio blob, stale stamp, airplane-mode test).
- **Sun 14:30–15:45:** 75 min to edit a 3-minute video with captions, while Arjav is also the demo owner (INTEGRATION §2.5).

The 3.25 h of slack absorbs one or two of these overruns, not all of them. The Sat 13:15 public URL depends on Shivansh's stack at 12:30, but the S3 `web/` fallback is available.

### Integration: 4/5
SR v1.1 conformance is strong and explicit. The plan uses `depth_class` strings, the opaque direction-agnostic `edge_id`, `avoid[].edge_ids`, manifest `events[]` / `issued_at[]` / `artefacts`, `unreachable.json` shown as "boat / NDRF needed", `free_beds`, static colonies without contacts (Shivansh confirms the stripped `static/*.geojson`), slot-filled dispatch with the `dispatch_cache` rung, the datum rule (no "level − ground_elev"), the §11.4 data-access ladder, and `{report, upload}`. The teammate times in §14 match their plans. Deductions:
- **N4. Merge gate conflict with `INTEGRATION_PLAN.md` §1.** Row 4 says `feature/arjav → main` **Sat 17:00**, gated on "Playwright smoke on fixtures; **Amplify preview builds**". The plan has no merge slot, schedules Playwright at Sat 20:00–21:00, and uses a manual deploy (no previews). INTEGRATION §4 step 5 still describes a Git-connected Amplify app. Arjav should get Shivansh to update both rows, or move a minimal smoke test earlier and merge at 17:30. INTEGRATION §1 also asks for "≥1 PR per owner per half-day", which the plan never schedules.
- **N5. The demo storyboard diverges from `INTEGRATION_PLAN.md` §5, and Arjav owns the video.** INTEGRATION shows a **street threshold** ("your lane floods at X m", Vaibhav F6 `wet_at_level_m`, his "headline differentiator") and a **trap counter** (Saksham F5 `trap_summary.json`). The plan uses `wet_at_level_m` only inside the band maths and never displays it. It never reads `trap_summary.json`. Its §11 flow differs from INTEGRATION §5. The `trap_summary.json` path is also ambiguous in SR §11.2: `routing/trap_summary.json` sits next to `scenarios/<id>/…`. It must be under a prefix the data CloudFront serves, which Shivansh's OAC lists as `static/ scenarios/ tiles/ models/inundation/ web/`.

### AWS Alignment: 4/5
The plan uses Amplify Hosting with a manual zip deploy (one CDN, no stacking), a separate data CloudFront over S3, AWS Open Data Terrain Tiles (bundled from the registry), Polly Kajal audio through presigned S3 with CORS, API Gateway for writes, a presigned POST with size, type and prefix conditions, and tags. Cost is effectively $0. Not a 5: the frontend itself uses no AWS service beyond hosting, reading and audio playback. Bundling the terrain tiles weakens the "reads from AWS Open Data at runtime" story slightly. That is fine, but name it in the architecture still. Amplify's deploy/access logs or a CloudWatch RUM snippet (Could) would be cheap additions to the "built on AWS" story.

### Innovation: 4/5
Three product features earn their place: the **Offline Colony Pack** (airplane-mode route as SVG, audio blob, staleness stamp), the **Compare split-screen** (basin gauge vs a street plan on one clock) and the **time-to-water band** (conformal intervals shown to residents, once N1 is fixed). Listen/a11y is on theme. Field reports are rightly a Could, and Director mode is honestly labelled as tooling. Not a 5, because the most distinctive teammate outputs, the street threshold (F6) and the trap counterfactual (F5), are not surfaced. Showing "DRB danger 205.33 m | **your colony gets wet at 206.3 m**" on the Compare sparkline would be the strongest 5 seconds of the video, and it costs about 20 min.

### Completeness: 4/5
Workstream A is covered: 2.5D terrain with 2D/Lite fallback, colony vulnerability (T_sub pins plus vulnerable counts), G/A/R roads, the alert UI (draft → chips → approve → `sent`), mobile layout, and offline (stated honestly as the colony pack, not offline map tiles). There are at least three new features, plus testing, deployment, the demo flow and teammate asks/commitments. Deductions: the spec's "offline map caching" is consciously delivered as an offline route SVG (correct, but a gap against the literal spec), and the INTEGRATION §5 beats (threshold, trap counter, skill card) are not planned anywhere in the frontend.

### Risk Assessment: 4/5
The five-rung degrade ladder, the three cut lines tied to SR §11.7, the hard integration stop, the protected recording slot, the fresh-profile `demo-v1` recording and the permanent REPLAY badge are among the best of any workstream. Missing items:
- **N2. A missing object returns 403, not 404.** Behind OAC without `s3:ListBucket`, an absent `unreachable.json` (or any not-yet-published step) returns 403. The "404 → `[]`" rule never fires. The ladder treats the 403 as a failure and drops to the **bundled fixture**, which can put fixture "boat" colonies on real data.
- **N3. Per-layer fallback mixes sources within one frame.** If roads come from fixtures but plans are real, a primary route can appear to cross a red road on camera. The global "data: static / cached / demo" chip hides this.
- N6 (the `+` in `?at=`) and the presign expiry of audio in the baked snapshot are not listed. Saksham presigns for 7 days, but `bake-static` should still download the mp3 blobs into `public/demo/`.

---

## Remaining risks / blockers
No deal-breakers. Ranked by how badly each could hurt the recorded video:
1. **N3/N2: mixed or wrong-source frames on camera** (credibility). Medium likelihood on Sat afternoon.
2. **N1: band copy says "about" for what is actually the earliest bound.** Low effort to fix, but visible in the hero beat.
3. **N5/N4: storyboard and merge-gate drift with INTEGRATION_PLAN.** It risks a Sat 20:00 argument about the shot list, and a late merge to `main` from which Shivansh's golden test cannot see the frontend.
4. Optimistic Friday slots push Saturday's Command/Dispatch start. Mitigated by slack and the Fri cut line (2D-only).
5. Deadline still unconfirmed (assumed 18:00 IST).

## Specific actionable improvements (prioritised)
1. **(15 min, Fri) Fix N1.** earliest = `plan.t_submersion`; centre = central `level_m` crossing; latest = `lo_m` crossing. Done-when: "earliest == `lead_time_h`". Copy: "पानी जल्द से जल्द ~X घंटे में" ("water in about X hours at the earliest") + "likely ~Y h".
2. **(15 min, Fri) Fix N2.** In `static.ts`, treat **403 or 404 on an optional artefact as "absent"**, not as a ladder failure. Better still, ask Saksham to always write `<t>.unreachable.json` (`[]` when empty). Use `manifest.artefacts` to decide whether a layer *should* exist before falling back.
3. **(20 min, Sat) Fix N3.** Resolve the ladder **per step, all-or-nothing**. If any Must layer (plans, roads, flood) for `at` fails, render the whole step from one source and show a **per-layer** source chip. Add a unit test: "never real plans + fixture roads".
4. **(10 min, Fri) Fix N6.** Use `URLSearchParams.set` for `at`, take key segments verbatim from the manifest, and add a unit test with a `+05:30` round-trip.
5. **(10 min, Fri) Fix N4.** Post in the channel: merge `feature/arjav → main` at **Sat 17:30** with the gate "build + tsc + vitest + one Playwright spec on fixtures". Ask Shivansh to change INTEGRATION §1 row 4 and §4 step 5 to the manual zip deploy. Open small PRs to `main` at Fri 23:30 and Sat 12:30.
6. **(40 min, Sat, Should) N5.** (a) Add a colony threshold line `wet_at_level_m` (and `cutoff_at_level_m`) to the gauge sparkline on Compare and Colony: "your colony gets wet at X m" (from Vaibhav's `colony_thresholds.json`). (b) Add a trap-counter chip on Command from `trap_summary.json`, after its CloudFront path is confirmed. Reconcile §11 with INTEGRATION §5 at the Sat 20:00 shot-list lock. Pay for this by moving "terrain tuning" earlier in the cut order.
7. **(5 min) Pins.** Use vite 8.3.1 (or justify 8.3.3 as a security patch), vitest 5.0.2 and react-query ≤5.103.2. Use `Ajv2020`.
8. **(10 min, Sun) `bake-static`** downloads the audio mp3s and the PMTiles-free fallback layers into `public/demo/`, so the recording build makes no presigned or remote calls.
9. Set `bounds` on the terrain source, and switch the router between hash and history via an env flag, so the S3 `web/` fallback works with no code change.

## Alternatives considered
- **Offline basemap:** use a pre-sliced z12–15 raster tile set (whole-file 200s, CacheFirst) instead of PMTiles if a map-in-airplane-mode shot is wanted. It costs about 1 h and 10–20 MB. Not recommended this weekend; the SVG route is the right call.
- **Band alternative:** show only "earliest X h" plus a coverage label (drop centre/latest). This is simpler and avoids interpolating three curves. Acceptable if Saturday slips.
- **Data ladder alternative:** for the recording, read **only** the baked `public/demo/` snapshot (one source, fully offline, deterministic), and keep the CloudFront ladder for the public URL. This eliminates N2 and N3 on camera at zero cost. Recommended as the default for the take.
- **Hosting alternative:** if Amplify manual deploy fails, use the S3 `web/` prefix behind the data CloudFront with hash routing, which is already planned. A second option is `aws amplify` drag-and-drop in the console, the same manual-deploy path with no script.

## Sources
- [AWS Amplify: Deploying without a Git repository (manual deploys)](https://docs.aws.amazon.com/amplify/latest/userguide/manual-deploys.html)
- [AWS Amplify API: StartDeployment](https://docs.aws.amazon.com/amplify/latest/APIReference/API_StartDeployment.html)
- [AWS re:Post: CloudFront + S3 REST origin 403 (missing object without s3:ListBucket)](https://repost.aws/knowledge-center/s3-rest-api-cloudfront-error-403)
- [AWS re:Post: origin group gets 403 on 404 failover](https://repost.aws/questions/QUzVrEDMK_TzqGFMga1flMQg/origin-group-getting-403-on-404-failover)
- npm registry `time` metadata (registry.npmjs.org) for maplibre-gl, vite, vite-plugin-pwa, @vitejs/plugin-react, react, typescript, vitest, @playwright/test, @tanstack/react-query, ajv, zustand, pmtiles, @protomaps/basemaps, json-schema-to-typescript, workbox-window and idb-keyval (checked 9 Oct 2026)

---

## Orchestrator follow-up (after the final review)

The cross-plan issues raised in this review and in the other three final reviews were resolved centrally in **SHARED_RESOURCES.md §11.8 (contract v1.2)** on `main`. Where §11.8 differs from this plan, §11.8 wins. The resolutions cover: the data-driven demo timestamp `T_hero`, the SHELTER_IN_PLACE path for already-wet colonies, the time-to-water definitions, amber using a window maximum, a single per-edge cutoff implementation, the bund floor applied in gauge space, calibration hold-outs, causal training inputs, always-written optional artefacts and 403 treated as absent, scenario-scoped paths, Bedrock IAM for inference profiles, frontend zip deploy, version pins, and volunteer-coordination scope. The owner should re-check their timeline against §11.7 / §11.8 at the Fri 23:00 sync.
