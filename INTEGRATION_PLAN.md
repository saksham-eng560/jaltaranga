# Jaltaranga — Integration Plan

How the four workstream branches come together into one deployed, demo-ready system by **Sunday Oct 11, 2026**. Contracts are in [`SHARED_RESOURCES.md`](SHARED_RESOURCES.md) (read §11 v1.1 first). The project overview is in [`PROJECT_SUMMARY.md`](PROJECT_SUMMARY.md).

| Branch | Owner | Folders | Plan |
|---|---|---|---|
| `feature/shivansh` | Shivansh | `pipeline/`, `infra/`, `shared/` (steward) | `IMPLEMENTATION_PLAN.md` on that branch |
| `feature/vaibhav` | Vaibhav | `ml/` | 〃 |
| `feature/saksham` | Saksham | `routing/`, `alerts/` | 〃 |
| `feature/arjav` | Arjav | `frontend/` | 〃 |

---

## 1. Merge order and why

Data flows **pipeline → ml → routing/alerts → frontend**, so we merge in that order. Each merge leaves `main` in a runnable state: every later stage can fall back to `shared/fixtures/`.

| # | Merge | Gate (must pass on the PR before it merges) | Target time |
|---|---|---|---|
| 0 | Small PRs to `main`: `shared/` (jt_shared models, JSON Schemas, fixtures, v1.1 contract) | `pytest shared -k schema` green; one teammate review | Fri 16:30 → 23:00, rolling |
| 1 | `feature/shivansh` → `main` | `sam validate`, `make -C pipeline scenario SCENARIO=yamuna-2023-07` passes offline, `/health` live on `demo` | **Sat 11:00** |
| 2 | `feature/vaibhav` → `main` | `make -C ml replay-local` writes `forecasts/`, `depth/`, `onset.tif`, `cutoff_0p30.tif` and `colony_thresholds.json`. Conformal and schema tests pass. Artefacts are in S3 and readable through CloudFront. The `/forecast` and `/flood` Lambdas are Should and can merge later | **Sat 13:00** |
| 3 | `feature/saksham` → `main` | `make -C routing precompute` and `make -C alerts predraft` pass. Invariant test: 0 red primaries, max depth ≤ 0.30 m. 20-draft validator report attached | **Sat 15:00** |
| 4 | `feature/arjav` → `main` | `npm run build`, `tsc`, bundle-size gate, Playwright smoke on fixtures; `infra/deploy_frontend.sh` zip deploy succeeds on `demo` | **Sat 17:00** (first PR); final PR before the Sat 20:00 freeze |
| 5 | `main` → deploy `demo` | Golden test §9.2 on the deployed stack | **Sat 18:45** (first run, even if it fails), **Sun 09:00** (must pass) |

**Earlier merges are fine.** Anyone can merge as soon as their gate is green. Before Sat 20:00, merges should be small and frequent: at least one PR per owner per half-day.

### Rules
- Use `git merge` (no rebase or force-push on shared branches). Before opening a PR, merge `main` into your feature branch and resolve conflicts there.
- **Each owner only touches their own folder(s).** Expected conflicts are limited to:
  - `infra/template.yaml`: each owner appends to their own commented section. Shivansh resolves conflicts in this file.
  - Root `Makefile` and `amplify.yml`: Shivansh owns them; others ask.
  - `shared/`: changes only via small PRs to `main`, never inside a feature branch.
- One PR reviewer is enough. Saturday reviews should be turned around within 30 minutes.

## 2. Conflict-resolution process

1. **Contract disagreement** (a schema, route or file format): the producer proposes the change, the consumer approves it, and Shivansh merges it into `shared/` + `SHARED_RESOURCES.md`. If it isn't settled within 30 minutes, the **producer's current fixture wins** and the consumer adapts.
2. **Git conflict** inside `infra/template.yaml`: keep both sections, run `sam validate`, and redeploy `dev` before `demo`.
3. **Scope conflict** (a feature is late): the owner applies their pre-agreed cut line (each plan's §"cut lines" and SHARED §11.7). Nobody waits on a Should or Could item.
4. **Data conflict** (two sources disagree, e.g. on a flood level): use the value with provenance `cwc` > `news` > `digitized` > `synthetic`, and show the source chip in the UI.
5. **Deadlock or time pressure:** after Sat 20:00 the demo owner (Arjav) decides what appears in the video, and the deploy owner (Shivansh) decides what gets deployed.

## 3. Integration testing strategy

| Layer | What | Where it runs | Owner |
|---|---|---|---|
| Contract | Each producer validates its output against `shared/schemas/*.json`. The frontend checks responses with Ajv in DebugPanel | CI (GitHub Actions) on every PR | each producer |
| Join tests | Every `RoadSegmentStatus.edge_id` is in `roads.geojson`; every `EvacuationPlan.colony_id` / `shelter_id` exists in the seeds; every forecast `issued_at` is in `manifest.issued_at` | CI | Shivansh (harness), producers (data) |
| Offline replay | `env -u AWS_ACCESS_KEY_ID -u AWS_PROFILE JT_LOCAL_DATA=./data make replay-local` runs the full chain | laptop + CI | Shivansh |
| Safety invariants | No primary or backup route crosses a red edge. Every route edge satisfies arrival + 30 min ≤ cutoff. `primary.max_depth_m ≤ 0.30`. No shelter is assigned more people than its free beds | CI + `make -C routing precompute` | Saksham |
| Hallucination | 20 recorded Bedrock drafts → validator. 0 untraceable tokens in any shown card. The fallback count is reported | `alerts/tests` (recorded fixtures in CI, live on Sat) | Saksham |
| Forecast honesty | Skill measured on anchors that were not used for calibration or selection; interval coverage reported | `ml/tests` + `metrics.json` | Vaibhav |
| Golden E2E (§9.2) | At `manifest.default_at` (= `T_hero`, SHARED §11.8-1): forecast in band → flood intersects Yamuna Pushta (300 m buffer) → plan with a safe route → validated dispatch (≤ 160 chars, only 1077/112) | `make golden ENV=demo` | Shivansh runs it, everyone fixes |
| UI smoke (§9.5) | Playwright: open `/command`, scrub to T+6 h, see red roads and a dispatch card, approve it → `sent`. Then the offline colony pack test | CI on fixtures; deployed URL is Should | Arjav |

**Daily syncs (15 minutes, all four):**
- **Fri 23:00:** fixtures and v1.1 merged? Any blocker?
- **Sat 09:00:** plan for the day; DEM, OSM and data status.
- **Sat 14:00:** go/no-go: precomputed demo window in S3?
- **Sat 20:00:** feature freeze; video shot list locked.
- **Sun 09:00:** golden test result; fix list.
- **Sun 12:00:** recording dry run.

## 4. Final deployment steps (owner: Shivansh; backup: Arjav)

1. **Day-1 prerequisites (Fri):** AWS account and IAM user per member. **Budget alarm at USD 10**. Bedrock model access granted and the region/profile probed (SHARED §11.6). SNS email subscriptions confirmed. Docker available on the deployer laptop.
2. **Build the data (laptop):** `make data` (DEM, OSM, gauges, seeds) → `make replay-local SCENARIO=yamuna-2023-07`.
3. **Deploy the backend:** `sam build --use-container && sam deploy --config-env demo --resolve-image-repos` deploys S3, DynamoDB, the HTTP API, the Lambdas, EventBridge Scheduler, SNS and the CloudWatch dashboard.
4. **Upload artefacts:** `aws s3 sync ./data/static s3://jt-demo-data-<acct>/static` and the same for `scenarios/`, `models/` and `tiles/`. Then seed the DynamoDB colonies and shelters with `make seed ENV=demo`.
5. **Deploy the frontend:** `infra/deploy_frontend.sh` (zip deploy to Amplify app `jt-demo-web`, SHARED §11.8-12) with `VITE_API_BASE`, `VITE_STATIC_BASE` and `VITE_TILES_BASE` baked in at build time. Amplify CustomRules provide SPA rewrites, and S3 CORS allows GET from the Amplify origin. The fallback is `dist/` → S3 `web/` behind CloudFront.
6. **Verify:** `/health` reports the Bedrock region, then `make golden ENV=demo`, the Playwright smoke test against the URL, and one real dispatch email received with Hindi in the body.
7. **Freeze:** tag `v1.0-demo`, record the CloudWatch cost, and write the deploy steps into `README.md` so judges can reproduce them.
8. **After submission:** `sam delete` the `dev` stack. Keep `demo` running through judging, under the budget alarm.

## 5. Demo video narrative (3:00, recorded Sun 13:00–14:30)

Built in **Director mode** (`?demo=1`, baked data, scripted camera). It is recorded as screen capture with a voice-over: English with Hindi lines, and Hindi subtitles.

| Time | Scene | On screen | Voice-over (gist) |
|---|---|---|---|
| 0:00–0:20 | **Hook** | News clips and gauge chart: Yamuna at **208.66 m, 13 Jul 2023**, a record; >25,000 people evacuated | "In July 2023 the Yamuna broke a 45-year record. The warning said '205.33 metres'. Nobody living on the floodplain can turn that number into a plan." |
| 0:20–0:40 | **The gap** | Split screen: a basin warning ("Yamuna above danger mark") vs a blank street map | "Warnings stop at the gauge. People live in lanes." |
| 0:40–1:05 | **Predict** | Replay scrubber a few hours before `T_hero`; forecast fan chart with an 80% band; rate-of-rise flag (show the "Hathnikund surge" flag only if Vaibhav's F2 ships); the street threshold "Your lane floods at 207.6 m" | "Jaltaranga forecasts the river 1–24 hours ahead with honest uncertainty, and turns the river level into a street-level threshold." |
| 1:05–1:35 | **See it spread** | 2.5D terrain; flood polygons grow as the scrubber plays; colony pins turn from green to amber to red with time-to-water countdowns | "Every colony gets a countdown to water." |
| 1:35–2:05 | **Route** | Ring Road turns red at 02:00; the "flood-blind" route would have trapped people (trap counter); the safe route via Lal Kuan lane to Kashmiri Gate shelter (250 beds free) | "It knows which roads will drown first and routes people before they do, to shelters that still have beds." |
| 2:05–2:35 | **Protect** | Officer clicks Draft: a Hindi dispatch card with every fact highlighted as verified; Approve; email arrives; Polly Kajal Hindi audio plays; colony view in airplane mode still shows the route | "Bedrock writes the message. Code checks every name, time and number. The pradhan gets it in Hindi, as text and voice, and it works offline." |
| 2:35–2:50 | **Built on AWS** | Architecture slide: Amplify, CloudFront, API Gateway, Lambda, Bedrock, Polly, S3, DynamoDB, EventBridge, SNS, SAM; cost under $10 | "Serverless, reproducible with one command, and cheap." |
| 2:50–3:00 | **Impact and close** | Honest skill card and limitations; tagline | "Predict. Route. Protect. Jaltaranga." |

**Shot-list rules:** the route, shelter, time and bed figures in this storyboard (Lal Kuan, Kashmiri Gate, 250 beds, 02:00, 207.6 m) are **placeholders** taken from the spec example. Replace them with the values the system actually computes for the hero colony. Every number on screen comes from the data or from SHARED §1, and no impact claim goes beyond what we computed. Record a 2D fallback take as backup. Keep the take under 2:55.

## 6. Integration risks and mitigations

| Risk | Mitigation |
|---|---|
| Backends late → frontend blocked | Fixtures for every schema by Fri 23:00. The data-access ladder (CloudFront static → fixtures) means the UI never needs the API to render |
| Vertical-datum mismatch between the DEM and the gauge | One owner for δ and S (Vaibhav, SHARED §11.1). Calibration points are shared. The golden test checks that Yamuna Pushta floods at 208.66 m and Connaught Place stays dry |
| `edge_id` mismatch between roads and graph | Direction-agnostic ids (§11.3) plus a CI join test |
| Bedrock unavailable or slow | Cross-region profile probe on Fri; slot-filled template fallback; drafts precomputed for the demo steps |
| Lambda timeouts | 18 s draft budget; precompute heavy work offline |
| Hero colony already wet or unreachable at the demo timestamp | `T_hero` is chosen from data (SHARED §11.8-1) on Fri 23:00, with a backup hero; already-wet colonies get the SHELTER_IN_PLACE path |
| Cost overrun | Budget alarm; no EC2, NAT or SageMaker endpoints; `dev` stack deleted after submission |
| Demo recording squeezed | Sat 20:00 feature freeze; Sun 13:00 recording slot is protected |
