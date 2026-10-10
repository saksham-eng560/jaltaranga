# Feature bombing plan: `feature/saksham` (routing, alerts, shared, infra)

**Owner:** Saksham · **Written:** Sat 10 Oct 2026, ~12:30 IST · **Hard stops:** feature freeze **Sat 20:00**,
recording **Sun 13:00–14:30**, submission **Sun (deadline − 2 h)** (SHARED §11.7).

The base is done and deployed (stack `jt-demo`): routing, alerts, validator, lifecycle, shelters, reports, 136 tests.
This plan adds **features judges can see in a 3-minute video** and **more real AWS usage**, in an order that never
breaks the demo. Every feature ships behind its own tests and keeps the existing invariants green
(`make -C routing demo-local` must still exit 0).

## How to read this

| Tier | Meaning | Deadline |
|---|---|---|
| **T0** | Make what exists *real* on AWS. Not new features, but every feature below depends on them | before 15:00 today |
| **T1** | Ship before the freeze. High demo visibility, ≤ 2.5 h each | Sat 20:00 |
| **T2** | Stretch. Only if T1 is green by 17:30 | Sat 20:00 |
| **T3** | Post-hackathon roadmap: goes in the blog's "what's next" section, not in code | — |

Effort figures are focused hours for one person, including tests.

---

## T0: make it real (do first)

| # | Item | Done when |
|---|---|---|
| T0.1 | **Bedrock live.** `make -C alerts probe`. Redeploy if the probe picks a different profile (see `docs/FOLLOWUPS_HANDOFF.md` §5) | predraft shows `"bedrock": true`; a fresh draft has `validation.source = "bedrock"` |
| T0.2 | **Hallucination eval, live.** `make -C alerts halluc-live N=20` and commit `alerts/tests/recorded/live_20.json` | report: 0 untraceable tokens; fallback rate written down for the blog |
| T0.3 | **Polly audio on approve** (it returned no `audio_url` before) | approving one dispatch returns a playable presigned mp3 |
| T0.4 | **Self-sufficient publish.** `make publish` uploads manifest, gauges and static seeds when present; idempotent shelter seed that never overwrites `occupied`/`free_beds` | a fresh `sam deploy` + `make publish` serves `/scenarios/*` with no manual step |
| T0.5 | **CI covers `ml/tests`** in a separate job; remove committed `ml/out/`, `ml/*.egg-info`, `__pycache__/` | both CI jobs green on `main` |

---

## T1: ship before the freeze (in this order)

### S1. "Safe even in the worst case" route badge · 1.5 h · demo beat: *Route*
- **What:** every route is checked against the **upper** (hi), **central** and **lower** forecast curves. A route that
  stays open under `hi_m` gets a green **"safe under 80% band"** badge. Today only `hi_m` closures are used, so every
  route already passes, but nobody can see that, and the backup's margin is unknown.
- **How:** `tdsp.route_is_safe` already takes `EdgeTimes`. Compute `close_s` for the central curve too, and add
  `primary.margin_min` (minutes of slack before the first edge on the route closes) plus `ext.robust: true|false`.
  Additive fields only (`CONTRACT_ADDITIONS.md`).
- **Files:** `routing/jt_routing/plan.py`, `cutoff.py`, `shared/py/jt_shared/models.py` (optional fields), fixtures.
- **Test:** a route with 10 min margin under `hi` is flagged robust; a route that only clears on the central curve is not.

### S2. Boat / NDRF plan for colonies nobody can walk out of · 2 h · demo beat: *Protect*
- **What:** colonies in `unreachable.json` (`already_wet`, `no_feasible_route`) get a concrete rescue plan: the nearest dry
  **boat launch point**, the boat trips needed (`ceil(population × rate / boat_capacity)`), and an ETA. Their
  SHELTER_IN_PLACE card adds a slot-filled line: "नाव {LAUNCH} से भेजी जा रही है, लगभग {BOATS} फेरे".
- **How:** add `static/boat_points.geojson` (synthetic in the dev world, labelled), `routing/jt_routing/boats.py`, an
  optional `boat_plan` field in `UnreachableEntry`, and the new slots `{LAUNCH}`/`{BOATS}` in `alerts/slots.py` + `templates.py`.
- **Test:** every unreachable colony gets a plan or `boat_plan: null` with a reason; the validator still rejects any digit the LLM typed.
- **Why it scores:** turns "boat / NDRF needed" from a dead end into an action. Judges see the system never abandons a colony.

### S3. Instant re-route when a field report blocks the road · 2 h · demo beat: *Route* (the dynamic moment the review asked for)
- **What:** `POST /reports` with `kind=road_blocked` near a colony's primary route **immediately** promotes the
  precomputed alternative or backup. `GET /plans` returns the re-planned route with `ext.replanned_due_to=<report_id>`.
  No graph is loaded in Lambda; it only uses the alternatives already in `plans/<t>.candidates.json`.
- **How:** `routing/jt_routing/serving.py`: after storing the report, find the edges within 30 m (from the route geometry)
  and write a small overlay to `jt-<env>-scenario-state`; `GET /plans` applies the overlay.
- **Test:** a report on the hero's primary route → the next `GET /plans` returns the backup, and it never routes onto a red edge.
- **Video:** drop a pin on Bela Road → the route bends away live.

### S4. Ack-timeout escalation with EventBridge Scheduler · 2 h · more AWS
- **What:** when a dispatch is `sent`, create a one-shot Scheduler entry. If it is still unacknowledged after
  `JT_ACK_TIMEOUT_MIN` (default 15; compressed for the demo), re-send to the colony's backup contact and set
  `status=escalated`.
- **How:** new `alerts/handlers/escalate.py` (Scheduler target), `scheduler:CreateSchedule` and `iam:PassRole` in the SAM
  section, a `jt-<env>-escalation-role`, and `escalated` added to the `DispatchCard.status` enum.
- **Test:** local store + fake clock: no ack → escalated; ack before the timeout → the schedule is deleted.

### S5. Officer situation report (sitrep) · 2 h · Bedrock, demo beat: *Protect*
- **What:** one-click **"Situation report"** for the district officer: a short hi + en paragraph covering how many
  colonies are at risk, the top 3 by priority, roads closing within 2 h, beds left, and people the flood-blind routes
  would have trapped. Same safety design: the LLM writes slot frames, code fills every number, the validator checks it.
- **How:** `alerts/jt_alerts/sitrep.py` (facts from `plans`, `unreachable`, `roads`, `trap_summary`), template fallback,
  `POST /scenarios/{id}/sitrep?at=` and `scenarios/<id>/sitrep/<t>.json` in predraft.
- **Test:** 20 mutated LLM outputs, 100 % caught; the template path always validates.

### S6. CloudWatch dashboard for the alert pipeline · 45 min · more AWS
- **What:** a `jt-<env>-alerts` dashboard: draft latency p50/p95, fallback rate, validator failures per check,
  dispatches sent and acknowledged, plus an alarm on Lambda errors.
- **How:** an `AWS::CloudWatch::Dashboard` in `infra/sections/routing_alerts.yaml`, built on the EMF metrics we already emit.
- **Why:** a screenshot for the "Built on AWS" slide and the blog.

---

## T2: stretch (only if T1 is green by 17:30)

| # | Feature | Effort | Notes |
|---|---|---|---|
| S7 | **Departure waves.** Stagger large colonies into 15-min waves so no road segment carries more than N people per wave (`ext.depart_at`, `ext.wave`) | 3 h | needs a per-edge flow cap in `assign.py`; keep greedy as the fallback |
| S8 | **Shelter check-in QR.** Per-shelter QR → officer page → `PATCH /shelters/{id}` | 1.5 h | the frontend renders it; I provide the signed URL format |
| S9 | **Beds-over-time forecast.** Project each shelter's `free_beds` across the next 6 steps from the assignments; alert when a shelter will be full | 1.5 h | `routing/trap_summary`-style `shelter_load.json` |
| S10 | **More languages (text).** Urdu (Perso-Arabic) and Punjabi (Gurmukhi) templates with a script check per language | 2 h | Polly has no voices for these: text only, say so |
| S11 | **2025 replay.** `SCENARIO=yamuna-2025-09` end to end | 1 h | only once Shivansh's pipeline builds that scenario |

## T3: roadmap (blog only)

- Real SMS / WhatsApp after DLT registration (SNS SMS, or Pinpoint / End User Messaging).
- Voice calls to feature phones via Amazon Connect, reusing the validated Kajal SSML.
- Wheelchair / stairs-free routing once the real OSM graph carries `highway=steps` and incline.
- Ward volunteers as SNS subscribers with ack, a volunteer task board.
- "Ask Jaltaranga" (Strands agent, read-only tools over plans, every answer cited).
- Live mode: EventBridge Scheduler tick → recompute on the newest CWC reading.

---

## Today's schedule (Sat 10 Oct)

| Time (IST) | Work |
|---|---|
| 12:30–15:00 | T0.1–T0.5 |
| 15:00–16:30 | S1 robust-route badge |
| 16:30–18:30 | S3 instant re-route, then S2 boat plan |
| 18:30–19:45 | S5 sitrep (or S4 escalation if the Bedrock probe still fails), S6 dashboard |
| 19:45–20:00 | full `pytest`, `make -C routing demo-local`, regenerate fixtures, publish, push |
| **20:00** | **Freeze**: bug fixes only after this |

**Cut order if late (first cut first):** S6 → S4 → S5 → S2 → S1. **S3 is the last to cut**, because it is the dynamic beat in the video.

## Definition of done (every feature)

1. Root `pytest` and `ml/tests` green; `make -C routing demo-local` exits 0 (0 safety violations).
2. Schema changes are additive, exported (`python -m jt_shared.export_schemas`), and listed in `CONTRACT_ADDITIONS.md`.
3. Fixtures regenerated (`make -C routing fixtures`), so Arjav's UI can render the new fields.
4. Any new AWS resource is in `infra/sections/routing_alerts.yaml`, `cfn-lint` passes, and the $10 budget holds.
5. No LLM text reaches a user unvalidated; every number comes from code.
