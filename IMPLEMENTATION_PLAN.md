# Jaltaranga — Routing & Alerting (routing/, alerts/) — Implementation Plan v1.1 (owner: Saksham)

> **Contracts:** SHARED_RESOURCES **v1.1**. Where §11 differs from an earlier section, §11 wins. I **produce** `RoadSegmentStatus` (§5.4), `EvacuationPlan` (§5.6 + §11.3 `avoid[].edge_ids`), `DispatchCard` (§5.7), `plans/<t>.unreachable.json`, `plans/<t>.candidates.json`, `routing/trap_summary.json` and `audio/<sha256>.mp3` (§11.2). I own `/roads`, `/plans`, dispatch draft/approve/list, `GET|PATCH /shelters` and `POST /reports` (§7, §11.4). I **consume** `ForecastNode`, `FloodSurface`, Vaibhav's `cutoff_0p30.tif` + `colony_thresholds.json` (§11.2), Shivansh's graphml/seeds/manifest. I never do datum arithmetic (§11.1), and I never mint an `edge_id` (§11.3).
> **Budget:** about 25 focused hours, Fri 9 Oct 16:00 → Sun 11 Oct, including **3.0 h of explicit slack**. Heavy work is precomputed offline. The frontend reads my outputs as **static files** (§11.4 data-access ladder). The API is needed only for dispatch, reports and shelters.

## 0. The one thing that must run

The demo moment I own, at replay time **13 Jul 2023 00:00 IST**. The times, names and bed counts are placeholders: **the data decides**, and we never hand-edit statuses.

1. The Ring Road edges near Yamuna Pushta are **amber**, with a forecast `cutoff_at`. At the step where depth exceeds 0.30 m they turn **red**. The whole named road is highlighted through `avoid[].edge_ids`.
2. `DEL-YP-04` (or the **backup hero colony**, §11.6) is at the top of the plan list. Its primary walking route goes to a shelter with `free_beds > 0`. It avoids every red edge and every edge that closes less than 30 min after the walker would arrive. The trap counter shows how many people the flood-blind route would have sent into water (F5).
3. The officer clicks *Draft*. Nova writes a **slot-filled** Hindi/English/SMS text, code fills in every fact, and the validator chips turn green. The officer clicks *Approve*, an SNS email arrives (ASCII subject, Hindi body), and the Kajal audio plays.

If Bedrock, Polly or OR-Tools fails, the same moment still works: the pre-drafted card from `dispatch_cache`, or the template, plus the device voice and greedy assignment.

## 1. Research summary (verified 9 Oct 2026)

| Topic | Finding | Decision |
|---|---|---|
| Python libs | networkx 3.7, rasterio 1.5.2 and numpy 2.5.3 need Python ≥3.12. ortools 9.15.6755 ships manylinux wheels of about 28 MB | Use **Python 3.12**. ortools, rasterio and osmnx run **offline only**. The Lambdas get pydantic, Powertools (arm64 layer) and `jt_shared` only |
| Bedrock region (§11.6) | The Nova Micro card lists `us.`/`eu.` geo profiles and no global profile. ap-south-1 is not an in-region location. Nova 2 Lite documents `global.amazon.nova-2-lite-v1:0` | Probe order: `aws bedrock list-inference-profiles --region ap-south-1` → `global.amazon.nova-2-lite-v1:0` → `us.amazon.nova-micro-v1:0` in us-east-1. The result goes into `JT_BEDROCK_REGION`/`JT_BEDROCK_MODEL_ID` |
| Nova structured output | Nova supports `toolChoice:{tool:…}`, and a tool config turns on constrained decoding | Use a forced tool `emit_dispatch` at temperature 0. Its fields hold **slot templates**, not facts (§11.6) |
| Polly | Kajal is a neural voice for hi-IN and also bilingual en-IN. Neural voices support `<p>`, `<s>` and `<break>`. `<prosody>` is partial and `<emphasis>` is unsupported | Use simple SSML and MP3 at 22.05 kHz. Cache by content hash at `audio/<sha256>.mp3` |
| SNS email | `Subject` must be ASCII, under 100 characters, with no newlines | English subject. Hindi goes only in the body (§11.6) |
| DynamoDB | ConditionExpressions cannot contain arithmetic | `ADD occupied :d, free_beds :neg` with `free_beds >= :d` (§11.4) |
| Routing | With fixed walk times and edges that close at known times, the network is FIFO. Earliest-arrival Dijkstra is exact. A cost-Dijkstra with an arrival-time side check is safe but **incomplete** | Cost-Dijkstra first. If no shelter is feasible, fall back to **earliest-arrival Dijkstra** before declaring a colony unreachable |
| Capacity | OR-Tools `SimpleMinCostFlow` solves about 30×15 arcs in milliseconds | Greedy by priority is Must. Min-cost flow is Should, offline only |
| SMS reality | Devanagari SMS is UCS-2: 70 characters per segment, 67 per part when concatenated | Hard cap ≤160 (§5.7), internal target ≤134 (two segments). This goes in the blog |

## 2. Architecture

```
OFFLINE  make -C routing precompute SCENARIO=<id> [WINDOW=demo]   (reads/writes $JT_LOCAL_DATA only, no AWS creds, §11.5)
 static/osm/corridor_roads.graphml ─┐ graph.py    walk graph (foot_ok edges), 15 m edge samples, edge_id read verbatim
 models/inundation/v1/cutoff_0p30 ──┤ cutoff.py   per-edge cutoff_level_m = min over samples; bridges inherit approaches
 colony_thresholds.json ────────────┤ forecast.py per-step hi_m(t) curve (obs at h=0; h=1,3,6,12,24) → crossing times
 forecasts/*.json, depth/<t>.tif ───┘ status      → roads/<t>.json  (red: depth>0.30 now; amber: hi_m crosses within 2 h)
 static/colonies|shelters.geojson ──► tdsp.py (cost-Dijkstra → earliest-arrival fallback) → candidates.py (K=3 × best/alt)
                                      assign.py (greedy | OR-Tools) → avoid.py (naive path, edge_ids, trap) → priority.py
                                      plan.py → plans/<t>.json, <t>.unreachable.json, <t>.candidates.json, trap_summary.json
 make -C alerts predraft  ──────────► scenarios/<id>/dispatch_cache/<t>/<colony>.json  (+ audio/<sha>.mp3 when creds exist)
 make -C routing publish ENV=demo  ─► aws s3 sync (separate from replay-local)

ONLINE  (HTTP API jt-demo-api, 2 Lambdas, python3.12 arm64, Powertools resolver)
 jt-demo-routing-fn : GET roads|plans (thin S3 passthrough, kept for the §7 smoke)  GET /shelters  PATCH /shelters/{id}
                      POST /reports (+ presigned POST)
 jt-demo-alerts-fn  : POST …/dispatch?at= → lifecycle → facts → [dispatch_cache hit] → Nova slot draft → validator
                      → [fail → template] → Polly (if budget) → DynamoDB draft        (18 s wall-clock deadline)
                      POST /dispatches/{id}/approve → Polly if missing → SNS (ASCII subject) → sent
                      GET /dispatches?scenario_id= (re-presigns audio URLs on read)
```

**Key design choices**
- **Cutoff as a level threshold.** An edge's `cutoff_level_m` is the **minimum** of Vaibhav's `cutoff_0p30.tif` over its 15 m samples. After that, every replay step is a scalar comparison against the forecast curve, which takes about 1 ms for 100k edges.
  - **Red** follows §5.4: the maximum of `depth/<t>.tif` over the edge's samples is above 0.30.
  - **Amber**: `cutoff_level_m ≤ hi_m(t+2h)`. `cutoff_at` is the time the interpolated curve crosses the cutoff level.
  - Edges with `is_bridge=true` are **not sampled**, because the raster under a bridge is river. A bridge takes the worse status of its two approach edges.
  - The vertical datum, the DSM-to-DTM correction and the slope are owned upstream (§11.1). I never compute `level − ground_elev_m`.
- **Closure for routing.** `close_at(e)` is the first time the `hi_m` curve reaches `cutoff_level_m`, searched up to 6 h ahead. A red edge has `close_at = t`. An edge is usable only if `arrival + 30 min ≤ close_at`. Walking speed is 3.0 km/h (2.0 km/h for high-vulnerability colonies, F1). Walks over 90 min are infeasible. Edges with `foot_ok=false` are never walked, but they stay in the status layer and in `avoid[]`.
- **Edge cost** is `walk_s × (1 + 5·depth_now) × (1.5 if amber)`. If this cost-Dijkstra finds no feasible shelter, an **earliest-arrival** Dijkstra (exact on FIFO networks) runs before a colony is declared unreachable.
- **Colony timing.** `t_submersion` is the first time the `hi_m` curve reaches the colony's `wet_at_level_m` (§11.2). Plans are made only for colonies that get wet within 24 h or are already wet.
- **Static-first serving.** Lambdas never load the graph, and the UI reads `plans/`, `roads/` and `dispatch_cache/` from CloudFront. Live re-routing in Lambda is Won't.
- **Replay clock.** `computed_at` is the step's `valid_at` (`+05:30`). This keeps dedup, validation and tests deterministic.
- **The LLM never types a fact (§11.6).** Code picks the alert type and every number, time, name and helpline. The LLM writes sentences that contain `{SLOTS}`, and code fills them in.

## 3. File structure

```
routing/
├── Makefile                 # precompute SCENARIO= [WINDOW=demo|all] [STEP=1|3] · fixtures · test · publish ENV= · package
├── pyproject.toml           # offline extra: networkx==3.7 numpy rasterio shapely ortools==9.15.6755; core: jt_shared
├── jt_routing/
│   ├── config.py            # speeds, 30 min buffer, K=3, cost weights, JT_SHELTER_RATE=0.25
│   ├── graph.py             # load graphml, walk subgraph (foot_ok), 15 m sampling, numpy haversine snapping
│   ├── forecast.py          # ForecastNode → piecewise-linear level/hi curve, crossing-time solver
│   ├── cutoff.py            # per-edge cutoff_level_m, bridge inheritance, RoadSegmentStatus per step
│   ├── tdsp.py              # cost-Dijkstra with close_at + earliest-arrival fallback
│   ├── candidates.py        # K shelters × {best, alt (×10 penalty, overlap <50%)}
│   ├── assign.py            # greedy by priority (Must) | OR-Tools min-cost flow (Should); same output type
│   ├── avoid.py             # naive flood-blind path → avoid[] (+edge_ids) and trap counterfactual (F5)
│   ├── priority.py          # urgency/population/vulnerability score (F1)
│   ├── plan.py              # assemble + validate via jt_shared.models; unreachable list
│   ├── reports.py           # Could: offline verified road_blocked → edges within 30 m red (F2b)
│   └── precompute.py        # CLI over manifest valid_at; multiprocessing per step; invariants inline
├── handlers/api.py          # roads/plans passthrough, shelters GET/PATCH, reports POST
├── data/names_hi.json       # curated hi names for about 25 demo roads/places
├── scripts/{make_fixtures.py, inspect_step.py}   # fixtures; GeoJSON dump + --hero-candidates
└── tests/{test_cutoff,test_tdsp,test_assign,test_invariants,test_schema,test_handlers}.py
alerts/
├── Makefile  pyproject.toml   # predraft SCENARIO= · test · halluc-eval
├── jt_alerts/
│   ├── facts.py             # plan+colony+shelter → DispatchFacts + slot values + per-plan gazetteer
│   ├── lifecycle.py         # alert_type (Must); dedup/cooldown + ALL_CLEAR (Should, F4)
│   ├── templates.py         # deterministic slot templates hi/en/sms (the floor; always pass)
│   ├── prompts/system.md    # slot rules + 1 few-shot built from the template
│   ├── drafter.py           # Converse + forced tool emit_dispatch; deadline-aware repair
│   ├── slots.py             # slot grammar, substitution, span tracking
│   ├── validator.py         # pre-substitution (LLM text) + post-substitution checks
│   ├── polly.py             # SSML from validated message_hi → audio/<sha>.mp3, presign
│   ├── notify.py            # SNS publish (ASCII subject); local outbox/*.eml when offline
│   └── store.py             # DynamoDB | local JSON backend (JT_LOCAL_DATA)
├── handlers/api.py          # dispatch draft, approve, list
├── scripts/{probe_bedrock.py, predraft.py, halluc_eval.py}
└── tests/{test_validator,test_mutations,test_templates,test_lifecycle,test_drafter_recorded,test_deadline,test_schema}.py
    tests/recorded/*.json    # real Nova outputs, replayed offline in CI
```

## 4. Component specs

### 4.1 Road status (`graph.py`, `cutoff.py`) — Must
- **Inputs.** Graphml edge attributes as in §11.3: `edge_id` (read verbatim, format `osm:<min(u,v)>:<max(u,v)>:<key>`), `name`, `name:hi`, `highway`, `foot_ok`, `is_bridge`, `elev_min_m`, `geometry`.
- **Sampling.** Points every 15 m along each edge. Each raster is read once into numpy and indexed with `rowcol`.
- **Output.** `roads/<valid_at>.json` holds only non-green edges. `reason` is `depth>0.3m` or `forecast_cutoff<2h`. For red edges, `cutoff_at` is the first step at which the edge went red, carried forward until its depth falls back to ≤0.30. A CI join test checks every `edge_id` against `static/osm/roads.geojson`.
- **Degrade path.** If the calibrated `cutoff_0p30.tif` is late, use Vaibhav's v0 (Fri 23:00), then his fixture. If no cutoff raster exists at all, amber is switched off: status is red-only, routing uses red-now plus the 30 min buffer, and the manifest note says so. A planar-rise rule of my own is **not** allowed (§11.1).

### 4.2 Plans (`tdsp.py`, `candidates.py`, `assign.py`, `avoid.py`, `plan.py`) — Must
1. **Usable shelters.** The shelter point has depth ≤0.05 m now, the shelter's own `close_at` is more than 6 h away, and `free_beds > 0` (§11.3; read from `static/shelters.geojson` when precompute runs).
2. **Search.** One cost-Dijkstra per colony, departing at t, which stops once every usable shelter is settled or the walk passes 90 min. If no shelter is feasible, run the **earliest-arrival fallback**.
3. **Candidates.** The top K=3 shelters, each with a best and an alternative route. The alternative re-runs the search with the best path's edges penalised ×10 and is kept only if it overlaps the best path by less than 50%.
4. **Assignment.** Demand is `population_est × 0.25` (a documented assumption). **Greedy** in priority order is Must. **OR-Tools** min-cost flow is Should, with `cost = walk_min×100/(1+priority)` and an *unassigned* sink at cost 10⁶. The primary shelter takes the largest share. The backup is the best candidate to another shelter, else the alternative route, else `null`.
5. **Fields.** `lead_time_h` is rounded to 0.5. `max_depth_m` is the maximum of `depth_now` along the route. `via_names_*` are the two longest named segments. `priority` comes from F1.
   - `avoid[]` holds the named roads on the naive path that close before the walker would arrive (§4.3 F5). Each entry has `cutoff_at` = the earliest closure, and `edge_ids` = every non-green edge with that name within 1 km of the naive path (§11.3).
6. **Unreachable.** A colony that is still infeasible after the fallback goes into `plans/<t>.unreachable.json` as `{colony_id, reason, population}` (§11.2). The UI shows it as "boat / NDRF needed".
7. **Order of work and runtime.** First the **demo window** (13 Jul 00:00–06:00, 7 steps, about 1 min), then all 192 hourly steps (about 10–15 min with 8 processes). The degrade path is 3-hourly steps and K=2.
8. **Hero check.** `inspect_step.py --hero-candidates` lists colonies whose routes stay feasible at 00:00 and whose naive path crosses a closing edge. The **backup hero** is picked from this list on Sat 13:45.

### 4.3 Dispatch (`facts.py`, `slots.py`, `drafter.py`, `validator.py`, `templates.py`) — Must
- **Facts.** These are computed by code only:
  - `alert_type` (from `lifecycle.py`)
  - the colony and shelter names in hi/en, `free_beds`, `walk_min`
  - `lead_time_h` as `"3.5"`, `t_sub` as `"04:30"`
  - `via_hi/en[]`, `avoid[] {name, cutoff_hhmm}`
  - vulnerable counts (F1)
  - `helplines ["1077","112"]`

  From these, facts derives the slot values and a **per-plan gazetteer**: the corridor colonies, shelters and roads, together with the plan's allowed names.
- **Slots.** The six §11.6 slots are `{SHELTER}`, `{VIA}`, `{AVOID}`, `{LEAD}`, `{TSUB}` and `{HELP}`. Alerts also uses three internal ones: `{COLONY}`, `{BEDS}` and `{CUT}` (the avoid closure time). Required slots: `{SHELTER}` and `{HELP}` always; `{VIA}` when via is non-empty; `{AVOID}`+`{CUT}` when avoid is non-empty; `{LEAD}`/`{TSUB}` for URGENT. Each slot may appear at most twice. An unknown slot fails.
- **Drafter.** Converse with `toolConfig` set to a single tool `emit_dispatch{message_hi, message_en, sms_hi}` and `toolChoice:{tool:{name:"emit_dispatch"}}`, `temperature=0`, `maxTokens=600`. The prompt says: never write a digit, a name, a time or a phone number; use the slots.
- **Deadline (§11.6).** The whole draft has 18 s of wall-clock time.
  - Bedrock: connect timeout 2 s, read timeout 7 s, `max_attempts=1`.
  - **One** repair call carrying the validator errors, made only if at least 8 s remain.
  - Polly runs only if at least 3 s remain. Otherwise `audio_url_hi=null`, and approve synthesises the audio.
  - The Lambda timeout is 25 s, under the 30 s HTTP API limit.
- **Fallback.** A field that still fails falls back **per field** to the template (for example, an LLM `sms_hi` that is over 160 characters after substitution). `fallback_used=true` if any field is a template. ALL_CLEAR is template-only.
- **Validator.** Every check is deterministic and runs on Devanagari-normalised text. The `checks` names are what Arjav's chips show.

| Check | Stage | What it enforces |
|---|---|---|
| `numbers_match` | pre | The LLM text has **zero** digits (ASCII or Devanagari) and zero Hindi number words (एक…दस, डेढ़, ढाई, साढ़े). Every number in the final text comes from a slot span |
| `names_match` | pre | There is no gazetteer name, no Latin token in hi/sms (except slot names), no non-initial capitalised word in en outside an allowlist, and no landmark noun (पुल, स्टेशन, स्कूल, अस्पताल, मंदिर, मार्ग, रोड, गेट, मेट्रो, कैंप, चौक; road, bridge, station, school, hospital, temple, gate, metro, camp, chowk, marg). Names enter only through slots |
| `slots_used` | pre | Every required slot is present, there are no unknown slots, and none repeats more than twice |
| `phones_whitelist` | post | Any run of 3 or more digits must be 1077 or 112. `+91` and 10-digit patterns are rejected |
| `length` | post | `sms_hi` is ≤160 code points and contains 1077. Each `message_*` is ≤600 |
| `script` | post | `message_hi` is at least 60% Devanagari letters |

- **Templates.** These are slot strings, for example: *"चेतावनी: {LEAD} घंटे में {COLONY} में पानी आने की आशंका। {AVOID} {CUT} से बंद। तुरंत {VIA} से {SHELTER} जाएं ({BEDS} जगह खाली)। मदद: {HELP}"*. A teammate does a native-Hindi review at Fri 19:15.

### 4.4 Approve, notify, log (`notify.py`, `store.py`, `polly.py`) — Must (Polly: Should)
- **Draft.** `POST /scenarios/{id}/colonies/{cid}/dispatch?at=` runs lifecycle → facts → a `dispatch_cache` hit (unless `?fresh=1`) → drafter → validator → Polly (if budget remains) → a DynamoDB put with status `draft`.
- **Approve.** `POST /dispatches/{id}/approve` does a conditional update `status = draft → approved`, so it is idempotent. Then it publishes to SNS:
  - Subject (ASCII, <100 characters): `[Jaltaranga] URGENT EVACUATION: Yamuna Pushta Sector C`.
  - Body: hi + en + SMS preview + audio link.
  - `MessageAttributes.colony_id`.

  The status becomes `sent`.
- **Polly.** The key is `audio/<sha256(ssml)>.mp3` (§11.2). SSML is built only from the *validated* `message_hi`, with a `<break>` and a repeat of the shelter name and 1077. `GET /dispatches` re-presigns the URLs (1 h). `predraft` presigns with laptop IAM-user credentials for 7 days, so the static cards stay playable through recording. Arjav caches the blob.
- **Offline.** `store.py` → `data/state/*.json`, `notify.py` → `data/outbox/*.eml`. With no credentials: template text, `audio_url_hi=null`, and `fallback_used=true` with a label.

### 4.5 Shelters and reports (`routing/handlers/api.py`) — Should
- **`PATCH /shelters/{id}`** takes body `{delta}` (§11.4). For `delta ≥ 0`: `ADD occupied :d, free_beds :neg` with `ConditionExpression: free_beds >= :d`. For `delta < 0`: the mirror with `occupied >= :abs`. Sets `updated_at`. A failed condition returns `409` with the §7 error shape. Plans are **not** re-assigned live; the next precompute picks the change up.
- **`POST /reports`** validates §5.8 and stores the report in `jt-demo-reports` with `replay_at`. It returns `{report, upload:{url,fields}|null}` (§11.4), where the upload is a presigned POST: ≤1 MB, `image/jpeg`, key `uploads/reports/<id>.jpg`, valid for 5 min. `trust` is a constant (0.6 with a photo, 0.3 without) and `verified=false`. The trust formula and the verify route are pre-cut.

## 5. New and enhanced features

| # | Feature | User value | How it works | Effort | MoSCoW |
|---|---|---|---|---|---|
| **F5** | **"Death-trap" counterfactual + named avoid list** | Makes the core claim measurable and puts it on screen: "N residents would have walked onto Ring Road after it flooded" | For each colony, compute the flood-blind shortest walk to its assigned shelter. Every edge on that path that closes before arrival goes into `avoid[]` with `cutoff_at` and `edge_ids`. `routing/trap_summary.json` holds `{trapped_population, colonies, roads}` per step for the trap counter, the impact slide and the blog | 1 h | **Must** (avoid) / **Should** (summary) |
| **F1** | **Vulnerability-aware priority and mobility** | Elderly, disabled and pregnant residents and young children move first and are never given a 70-min walk | `V = (1.5·elderly + 2.0·disabled + 1.3·children_u5 + 1.8·pregnant)/population`. `priority = 0.45·urgency + 0.25·pop_norm + 0.20·V_norm + 0.10·route_risk`. When `V_norm > 0.6`: walk speed 2.0 km/h, and if `walk_min > 30` a *transport needed* flag. **Code appends** a fixed, validated sentence "पहले बुज़ुर्गों/गर्भवती महिलाओं को निकालें ({n} बुज़ुर्ग)" | 1.5 h | **Must** (plain score) / **Should** (mobility + sentence) |
| **F3** | **Kajal Hindi voice briefing** | Low-literacy residents and feature-phone users hear the instruction, and the pradhan can play it on a loudspeaker | Polly neural Kajal on the validated `message_hi`, cached by content hash, synthesised lazily at approve when the draft deadline is tight | 1 h | **Should** |
| **F2** | **Capacity-aware assignment** (+ field-report reroute) | No shelter is ever sent more people than it has free beds | Greedy (Must), then OR-Tools min-cost flow with an overflow sink → "needs transport". **F2b (Could):** `make -C routing precompute REPORTS=data/demo_reports.json` applies a verified `road_blocked` report: edges within 30 m turn red (`reason=field_report`) from `replay_at`, the next clean candidate is promoted and `ext.replanned_due_to` is set. This happens **offline**, so the static ladder shows it | 1 h (+1.5 h F2b) | **Should** (OR-Tools) / **Could** (F2b) |
| **F4** | **Alert lifecycle** | Avoids alert fatigue, and the officer sees escalation | `alert_type` (Must): `PREPARE` when DRB ≥204.5 or `6 < lead ≤ 24 h`; `URGENT_EVACUATION_DISPATCH` when `lead ≤ 6 h` or `hi_m ≥ 206.0` with `t_sub` within 12 h. **Should:** dedup key `dedup#<scenario>#<colony>#<type>` with `plan_hash` in `jt-demo-scenario-state`, a 60 min replay cooldown that escalation or a material change bypasses, and ALL_CLEAR (template-only) when the level is below 205.33, falling, and the 12 h maximum `hi_m` is below 205.33. **Could:** `POST /dispatches/{id}/ack`, an in-app button only, with no email link and no HMAC | 1.5 h | **Must** / **Should** / **Could** as stated |

**Pre-cut to Won't (post-hackathon list in the blog):** the IVR 8 kHz WAV, HMAC email ack links, the report trust formula and `POST /reports/{id}/verify`, F6 Strands `POST /ask`, live re-assignment or re-routing in Lambda.

## 6. Timeline (about 25 h, including 3.0 h of slack)

### Fri 9 Oct, 16:00–24:00 (about 7.25 h of work, 0.5 h slack)

| Time | Task | Done when |
|---|---|---|
| 16:00–16:45 | Scaffold `routing/` and `alerts/`, install `jt_shared`. Bedrock probe in the §11.6 order, with a Hindi forced-tool sample. Personal SNS topic `jt-dev-saksham-dispatch` (tagged, CLI): one test email, ASCII subject, Hindi body | Probe JSON is recorded. **`JT_BEDROCK_*` posted by 17:00**. The test email shows Hindi correctly |
| 16:45–19:15 | `facts`, `numerals`, `slots`, `templates`, `validator`, and ≥40 mutation tests | Templates pass. 100% of the injected digits, number words, gazetteer names, Latin tokens, landmark nouns, phones and missing or unknown slots fail |
| 19:15–19:45 | Dinner + native-Hindi template review | Corrections merged |
| 19:45–21:00 | `make_fixtures.py`: 5 steps (12 Jul 18:00 → 13 Jul 18:00) × 3 colonies matching Arjav's mocks, with `avoid[].edge_ids`, `unreachable`, `free_beds`, cards from the **real** templates and validator, one fallback card, `report_post_response`, and a sample `dispatch_cache` | Fixtures parse with `jt_shared.models`. **Fixtures PR open by 21:00** |
| 21:00–22:15 | `forecast.py`, `cutoff.py` (with bridge inheritance) and `tdsp.py` (with the earliest-arrival fallback) on a synthetic 12-node graph with a 20×20 raster | Tests pass: the red/amber rules; a route avoids an edge that closes before arrival + 30 min; **the fallback finds a route that cost-Dijkstra misses**; with no closures the result equals `nx.dijkstra_path` |
| 22:15–22:30 | Load Shivansh's graphml (his 22:15). Check that `edge_id` is the same in both directions and follows §11.3, plus `foot_ok`, `is_bridge` and `name:hi` | **Graph ack posted by 22:30**, flagging any format drift |
| 22:30–23:00 | **Slack** (fixture drift before Arjav swaps at 23:00) | — |
| **23:00** | **CHECKPOINT (§11.7): fixtures merged + v1.1 PR merged** | — |
| 23:15–24:00 | `drafter.py` (slot-filled forced tool, deadline) on the 3 fixture plans. Record the outputs to `tests/recorded/` | At least 2 of 3 pass without repair. Otherwise try Nova Lite / Nova 2 Lite and note it |

**Cut line Fri 23:00.** If the validator is not green, the fixtures ship template-only cards (the real validator still runs) and the drafter moves to Sat 14:00. If the probe found no working profile, run template-only (labelled) and drop the live half of the hallucination test. If the graphml is late, keep the synthetic graph tests and pull a local 3×3 km osmnx box on Saturday at 09:30 (never committed).

### Sat 10 Oct, 09:00–22:00 (about 10.75 h of work, 1.0 h slack)

| Time | Task | Done when |
|---|---|---|
| 09:00–09:30 | Daily sync. Pull the graphml, `cutoff_0p30` v0, `colony_thresholds.json`, forecasts and depth | **Confirmed to Vaibhav by 09:30** (`wet_at_level_m`, `cutoff_at_level_m`) |
| 09:30–11:00 | Edge index + `roads/<t>.json` for the **demo window**, then `inspect_step.py` | Ring Road status over 00:00–06:00 is known. If the data differs from the script, post the real times |
| 11:00–12:30 | `candidates`, **greedy** `assign`, `avoid` (edge_ids), plain `priority`, `plan`, unreachable, all on the demo window with Shivansh's seeds (his 11:00). `make publish` | Invariants green on the demo window. **Demo-window roads/plans (v0 inputs) in S3 by 12:30** |
| 12:30–13:00 | **Backup-deployer dry run** (Shivansh's README) | `make deploy ENV=dev` succeeds from a clean checkout |
| 13:00–13:45 | Lunch + integration huddle: the edge_id join, the `unreachable` shape, `ext` yes/no, the hero colony | Decisions in the channel |
| 13:45–14:00 | Re-run the demo window on Vaibhav's calibrated inputs (his 12:30) and publish. `--hero-candidates` → backup hero | Backup hero posted |
| **14:00** | **CHECKPOINT (§11.7): demo-window forecasts/depth/roads/plans in S3** | — |
| 14:00–14:45 | Start the full-window precompute in the background. `predraft` for the demo window. `halluc_eval.py` with 20 live drafts. Open the merge PR | **Merge gate by 15:00**: precompute + predraft pass, invariants green, the 20-draft report attached |
| 14:45–16:00 | Both `handlers/api.py`, the SAM section `# --- routing/alerts (Saksham) ---`, deploy to `demo` | `curl` on demo: plans, roads, draft, approve, list. **CORS works from Amplify by 16:00** |
| 16:00–17:00 | SNS approve on `jt-demo-dispatch` + `polly.py`. On call for Arjav's integration (16:30–17:30) | The email arrives and the Kajal mp3 plays from the card |
| 17:00–17:45 | `PATCH /shelters` (§11.4 form) + `POST /reports` presign | 409 when full. **Arjav's upload works by 18:00** |
| 17:45–18:15 | Dinner | |
| 18:15–20:00 | Should, in video-visibility order: F5 trap summary → F1 mobility + sentence → F4 dedup/ALL_CLEAR → OR-Tools. 18:45: assist the first golden run (15 min). 19:45: re-run the full precompute on Vaibhav's final rebuild (background) | Each item ships only with its tests green |
| **20:00** | **CHECKPOINT (§11.7): FEATURE FREEZE** | — |
| 20:00–20:45 | Full-window invariants on all steps, final demo `predraft`, offline `make` with no credentials, refreshed fixtures, the trap number for the impact slide | All green. Pushed |
| 20:45–21:00 | Record two rough clips (draft → chips → approve → email/audio; trap counter) | Clips in the team folder |
| 21:00–22:00 | **Slack** (bug fixes only). Shivansh's static data freeze is at 22:00 | — |

**Cut line Sat 14:00.** If the demo window is not in S3, publish whatever exists for 00:00–06:00 even on v0 inputs. Then greedy is final, and F1 mobility, F4 dedup/ALL_CLEAR and F2b are dropped. The full window runs 3-hourly with K=2. I tell Arjav to record from static or fixture data. No new integration after 17:30.
**Cut line Sat 16:30.** If the API is not live on `demo` with CORS, drop F4 (all), ack and F2b, and spend 16:30–17:30 only on deploy. The recording uses `dispatch_cache` (Arjav's ladder rung 4).
**Cut order at Sat 20:00** (first cut first): OR-Tools → F4 dedup/ALL_CLEAR → F1 mobility → F5 summary (keep avoid) → Polly (device voice). The Must column is never cut.

### Sun 11 Oct, 09:00–16:00 (about 4.5 h of work + recording, 1.5 h slack)

| Time | Task | Done when |
|---|---|---|
| **09:00–10:00** | **CHECKPOINT (§11.7): golden test §9.2 on `demo`.** Blockers only | Mine green: plan exists, `max_depth_m ≤ 0.30`, 0 red primaries, validation passed, SMS ≤160, only 1077/112 |
| 10:00–11:00 | Final pre-draft + approve of the demo dispatches, verify email + audio. **Last `scenarios/` sync before 11:00** (Arjav bakes static at 11:00) | `dispatch_cache` + audio in S3 |
| 11:00–12:00 | **Slack 1 h** (blockers; else run `SCENARIO=yamuna-2025-09` if Shivansh built it — Could) | — |
| 12:00–13:00 | Recording dry run with Arjav (12:00). Blog section "The LLM never types a fact" | Rehearsed twice without errors |
| **13:00–14:30** | **CHECKPOINT: record.** My segments: draft → chips → approve → email/audio; trap counter | Captured |
| 14:30–15:00 | Edit support. Delete `jt-dev-saksham-dispatch`. Check the budget and cost | Cost under $2 |
| 15:00–15:30 | **Slack 0.5 h** | — |
| **15:30–16:00** | **CHECKPOINT: submit at deadline − 2 h** (assumed 18:00, confirmed Fri night) | Submitted |

**Cut line Sun 09:00.** If a fresh draft is flaky, the demo uses the cached cards only. **Sun 13:00:** record whatever is frozen; no fixes during the recording.

## 7. MoSCoW

| Must (the demo-able path alone) | Should | Could | Won't (this hackathon) |
|---|---|---|---|
| Red/amber per step (demo window first) · cost-Dijkstra + earliest-arrival fallback · primary/backup · `avoid[]`+`edge_ids` (F5) · greedy capacity · plain priority (F1) · unreachable list · plans/roads JSON + thin GETs · slot-filled drafter + validator + template · `alert_type` (F4) · draft/approve/list · DynamoDB log · SNS email · `predraft`/`dispatch_cache` · fixtures · invariant, mutation and hallucination tests · §11.5 make targets | Polly Kajal (F3) · trap summary (F5) · mobility + vulnerable sentence (F1) · OR-Tools (F2) · dedup + ALL_CLEAR (F4) · `PATCH /shelters` · `POST /reports` | F2b offline field-report reroute · in-app ack POST · Sep 2025 run | IVR WAV · HMAC email ack · trust formula + verify route · Strands `/ask` · live recompute in Lambda · real SMS/WhatsApp (DLT) · vehicle routing · contraction hierarchies · auth/RBAC |

## 8. Testing strategy

- **Unit tests.**
  - Cutoff rules on a toy raster, including bridge inheritance.
  - `tdsp`: an edge closing at τ−1 min is rejected. A case where cost-Dijkstra fails but the **earliest-arrival fallback succeeds**.
  - Greedy never exceeds `free_beds`. OR-Tools agrees with greedy on a 3×2 case.
  - Lifecycle transitions. The `PATCH /shelters` condition, including the 409 case, on the local backend.
  - The SNS subject is ASCII and under 100 characters.
- **Invariant test** (`test_invariants.py`, inside precompute, over every step):
  - No primary or backup route has an edge that is red at t, and every route edge satisfies `arrival + 30 min ≤ close_at`.
  - `primary.max_depth_m ≤ 0.30`.
  - Assignments do not exceed free beds.
  - Every `edge_id` joins to `roads.geojson`.

  This covers §9.2 items 3–4.
- **Validator mutation test.** Inject into the LLM text a digit, a Devanagari digit, a number word, a gazetteer name, a Latin token, a landmark noun, an unknown slot, or a missing required slot. Inject into the final text a phone number or an overlong SMS. 100% must be caught.
- **Hallucination test (§9.3).** 20 live Nova drafts (Sat 14:00), recorded and replayed in CI. The report gives the pass rate, the fallback count and 0 untraceable tokens.
- **Deadline test.** A stubbed Bedrock that sleeps 10 s → the card comes back within 18 s with no repair, from the template, with `fallback_used=true`.
- **Schema and offline tests.** `pytest -k schema` (§9.1). `env -u AWS_ACCESS_KEY_ID -u AWS_PROFILE JT_LOCAL_DATA=./data make -C routing precompute && make -C alerts predraft` (§9.4, §11.5).
- **Lambda tests.** Handlers are called directly with API GW v2 events. One `sam local invoke` smoke run.

## 9. Deployment

- **Lambdas.** `jt-demo-routing-fn` (10 s) and `jt-demo-alerts-fn` (25 s), both python3.12 arm64 with 512 MB, the arm64 Powertools layer, and 7-day log retention in SAM. Build with `sam build --use-container`; if the pydantic-core build fails, switch to x86_64.
- **Environment variables.** `JT_ENV`, `JT_DATA_BUCKET`, `JT_BEDROCK_REGION`, `JT_BEDROCK_MODEL_ID`, `JT_BEDROCK_DISABLED` (kill switch), `JT_SNS_TOPIC_ARN`, `JT_POLLY_VOICE=Kajal`, the table names, and `JT_DRAFT_DEADLINE_S=18`.
- **IAM (least privilege).**
  - **routing-fn:** `s3:GetObject` on `scenarios/*` and `static/*`; `s3:PutObject` on `uploads/reports/*` (for the presign); DynamoDB `GetItem/Scan/UpdateItem` on `shelters` and `PutItem` on `reports`.
  - **alerts-fn:**
    - `bedrock:InvokeModel` on the profile ARN plus the foundation-model ARNs in its destination regions (region `*` for a global profile).
    - `polly:SynthesizeSpeech`.
    - S3 `Get` on `scenarios/*`; `Get/Put` on `audio/*`.
    - `sns:Publish` on `jt-demo-dispatch`.
    - DynamoDB on `dispatches` and `scenario-state`.
  - No SSM access is needed now that the HMAC ack is cut.
- **Cost.** Nova draft calls cost well under $0.50 for about 500 drafts. Polly with the hash cache is cents. Lambda, DynamoDB and SNS are within the free allowances. There is no always-on compute. The $10 budget alarm stays in place.

## 10. Risks and degrade paths

| Risk | Likelihood | Degrade path |
|---|---|---|
| Schedule slip (the review's main concern) | High | The §6 checkpoints, cut lines and pre-cut Won't list. 3 h of slack |
| No Nova profile works from ap-south-1 | High | Global Nova 2 Lite → `us.` Micro in us-east-1. Else template-only, labelled "template" |
| Nova Hindi fails validation often | Med | Slot-filling removes most failure modes. Then one repair, per-field template fallback, and pre-drafted demo cards |
| A fresh draft exceeds 30 s | Med | The 18 s deadline, repair only with ≥8 s left, lazy Polly at approve |
| The hero colony is unreachable at 00:00 (Ring Road red at t=0) | Med | Backup hero chosen Sat 13:45. Unreachable is shown honestly as "boat / NDRF needed" |
| Ring Road does not close when the script says | Med | Narrate what the data shows. Never hand-edit statuses |
| `cutoff_0p30.tif` or forecasts late | Med | Vaibhav's v0 → fixture → red-only mode (§4.1). No datum arithmetic of my own |
| DSM bias makes roads go red late (the unsafe direction) | Med | Owned upstream (DTM + calibrated δ/S, §11.1). Per-edge **minimum** cutoff + 30 min buffer. Stated in the blog's limitations |
| Bridge edges sample the river and show red | Med | Bridge edges are not sampled; they inherit their approach edges' status (§4.1) |
| Graphml `edge_id` format differs from §11.3 | Med | I read the attribute verbatim, so the join test catches drift. I flag it at the 22:30 ack |
| Precompute too slow | Med | Demo window first, then 3-hourly steps, K=2, multiprocessing |
| Presigned audio expires in static cards | Low | 7-day presign in `predraft`, re-presign on `GET /dispatches`, blob cached in Arjav's colony pack |
| Polly or SNS fails | Low | `audio_url_hi=null` → device voice. The in-app inbox is the record, and the email is shown from the outbox |
| The validator is too strict | Med | Pass rate measured Sat 14:00. Only `script`/`length` may be loosened, never `numbers`, `names` or `phones` |

## 11. Interfaces with teammates

**Already adopted in v1.1 (no PR needed):** the `cutoff_0p30.tif` / `colony_thresholds.json` formats (§11.2), the direction-agnostic `edge_id` (§11.3), `avoid[].edge_ids`, `Shelter.free_beds`, the `unreachable.json` shape, the `POST /reports` response, the `PATCH /shelters` form, the slot-filling rule, the ASCII subject, the 18 s deadline, the probe order and the make targets.
**Still open, in my Fri 21:00 fixtures PR (additive, decided at the Fri 23:00 checkpoint):** (a) `scenarios/<id>/dispatch_cache/<t>/<colony>.json` added to §6 (Arjav already reads it); (b) an optional `EvacuationPlan.ext` `{walk_speed_kmh, transport_needed, replanned_due_to}`, default null; (c) `RoadSegmentStatus.reason` value `field_report` (only used by F2b). If (b) or (c) is rejected, those F1/F2b details stay in `plans/<t>.candidates.json` and the UI shows nothing extra.

| From | What | By |
|---|---|---|
| Shivansh | Graphml + graph spec with the §11.3 `edge_id` and attributes | Fri 22:15 (ack 22:30) |
| Shivansh | DTM-based `elev_min_m`, `roads.geojson` part (ii) for the join | Sat 10:00 |
| Shivansh | `colonies/shelters.geojson` (`free_beds`) + DynamoDB seeds, team plus-address contacts | Sat 11:00 |
| Shivansh | Infra v1: `jt-demo-dispatch` (emails confirmed), tables, bucket and SNS ARN Outputs, my SAM section slot, README for the dry run | Sat 12:30 |
| Vaibhav | Fixtures → `cutoff_0p30` + `colony_thresholds` v0 → calibrated publish → final rebuild | Fri 18:15 / Fri 23:00 / Sat 12:30 / Sat 19:45 |
| Arjav | `field_report.json` fixture. The UI renders `validation.checks`, the fallback banner, `avoid[].edge_ids`, unreachable, and (if adopted) `ext.replanned_due_to` | Fri 23:00 / Sat 16:30 |
| Team | Native-Hindi template review (15 min). Confirmation of the deadline time | Fri 19:15 / Fri 24:00 |

| I deliver | When |
|---|---|
| `JT_BEDROCK_REGION`/`MODEL_ID` in the channel | Fri 17:00 |
| Fixtures PR: `road_segment_status`, `evacuation_plans` (5×3), `plans_unreachable`, `dispatch_card` (+fallback), `shelters`, `report_post_response`, `dispatch_cache` sample | Fri 21:00 (merged by 23:00) |
| Graph ack; Vaibhav input confirmation | Fri 22:30; Sat 09:30 |
| Demo-window `roads/` + `plans/` in S3 (v0 → calibrated) | Sat 12:30 → 14:00 |
| Merge PR `feature/saksham` → `main` (gate: precompute, predraft, invariants, 20-draft report) | Sat 15:00 |
| Live draft/approve/`GET /dispatches` with CORS | Sat 16:00 |
| `audio_url_hi`, `POST /reports` presign, `PATCH /shelters` | Sat 18:00 |
| Full window + final predraft + offline make + refreshed fixtures + trap number | Sat 20:45 |
| Golden assertions green on `demo`; final `dispatch_cache` + audio synced | Sun 10:00; Sun 11:00 |

## 12. Revision log (v1.1, Fri 9 Oct)

**Review deal-breakers and defects**
1. **DynamoDB arithmetic in a condition.** Fixed with the §11.4 form, `ADD occupied :d, free_beds :neg` / `free_beds >= :d`, plus the mirror for negative deltas (§4.5).
2. **SNS subject.** ASCII English, under 100 characters. Hindi only in the body. A live test email goes out Fri 16:00 on a personal dev topic, because the team topic only exists from Sat 12:30.
3. **30 s latency chain.** An 18 s wall-clock deadline: Bedrock `max_attempts=1` with a 7 s read timeout, repair only with ≥8 s left, Polly only with ≥3 s left (else at approve). A deadline test is added.
4. **Routing incompleteness.** An earliest-arrival Dijkstra fallback runs before "unreachable", with a unit test.
5. **Out-of-gazetteer names.** Replaced by **slot-filling** (adopted in v1.1, §11.6). The validator now rejects digits, number words, gazetteer names, Latin tokens and landmark nouns in the LLM text, and requires the slots.
6. **Rounding.** Moot: every number enters through a slot, and the LLM text may contain no digits.
7. **Planar-rise degrade path.** Removed. §11.1 makes Vaibhav the sole datum owner. The degrade is v0 → fixture → red-only.

**Required changes**
- RC1: §11.7 checkpoints are in the timeline, with cut lines at Fri 23:00, Sat 14:00, Sat 16:30, Sat 20:00 and Sun 09:00/13:00. IVR, HMAC ack, the trust formula and F6 are pre-cut to Won't.
- RC2: the Sat block is split. The demo window ships first (12:30 on v0, 14:00 calibrated), then the full window runs in the background. Greedy is Must; OR-Tools is the last Should.
- RC3–RC6: items 1, 2, 3 and 4 above.
- RC7: adopted in v1.1, so no PR is needed (cutoff/threshold formats, edge_id, unreachable). The remaining additive asks are in §11.
- RC8: the probe follows §11.6.

**Also from the review (recommended)**
- A backup hero colony from `--hero-candidates` (Sat 13:45).
- Ack is POST-only in the app, with no email link, which removes the email-scanner prefetch risk.
- The DSM bias is owned upstream and stated in the blog.
- Rough clips are recorded Sat 20:45.
- Bridge-edge inheritance was added, so bridges are not marked red from the river beneath them.

**v1.1 conformance**
- `edge_id` is read verbatim (§11.3).
- `wet_at_level_m` replaces `onset_level_m`.
- `avoid[].edge_ids` and `free_beds` are used.
- The audio key is `audio/<sha256>.mp3`.
- The UI reads my outputs statically (ladder), so live `replan_lite`, `snap.py` and shelter re-assignment in Lambda were removed. F2b became an offline Could.
- `make` targets need no credentials, and S3 upload is a separate `publish` target.

**Deliberate deviations**
- §11.4 lists `GET|POST /dispatches/{id}/ack` as my Should. I downgrade it to Could (in-app POST only), because it is invisible in a 3-minute video.
- `POST /ask` is Won't.
- I keep the thin `GET roads|plans` Lambdas even though the ladder does not need them, because Shivansh's smoke test covers every §7 route.

**Alignment with teammates**
- Shivansh: graph at Fri 22:15 with my ack at 22:30; seeds at Sat 11:00; infra at 12:30; my dry run at 12:30–13:00; static freeze at 22:00. His plan writes `edge_id` as `osm:<min(osmid)>:<k>`, which differs from §11.3. I flag this, and the join test guards it.
- Vaibhav: publishes at 12:30 and 19:45, and I re-run precompute after each.
- Arjav: integration 16:30–17:30, `dispatch_cache` ladder, bake at Sun 11:00.
- Integration plan: merge gate Sat 15:00.
- Slack: 3.0 h in total (Fri 0.5, Sat 1.0, Sun 1.5).
