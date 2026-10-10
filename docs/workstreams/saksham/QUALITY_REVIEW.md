# Quality Review (round 2): Saksham, Routing & Alerting (`routing/`, `alerts/`)

Reviewed: `IMPLEMENTATION_PLAN.md` v1.1 (Fri 9 Oct), against SHARED_RESOURCES v1.1 (§11 overrides), the Jaltaranga spec, the previous review, and the current plans of Shivansh, Vaibhav and Arjav plus INTEGRATION_PLAN.md. This reviewer is independent from the previous one.

| Criterion | Rating (1–5) |
|---|---|
| Technical Soundness | 4 |
| Feasibility (~25 h, one person, from Fri 9 Oct 16:00) | 3 |
| Integration (v1.1 contracts) | 4 |
| AWS Alignment | 4 |
| Innovation | 4 |
| Completeness | 4 |
| Risk Assessment | 4 |
| **Total** | **27 / 35 → 15.4 / 20** |

**Verdict: APPROVED (>=15/20)**

The approval is narrow. It holds only if the "already-wet hero colony" problem (§4, item B1) is checked on Friday night rather than Saturday afternoon. The numeric total matches round 1, but the mix has changed: feasibility went up from 2 to 3 because the scope was cut and slack was added, and completeness went down from 5 to 4 because this review checks against the spec's Workstream D list, which round 1 did not.

---

## 1. Resolved since previous review

All eight required changes and every defect from round 1 have been addressed in the plan text:

| # | Round-1 issue | Status | Where |
|---|---|---|---|
| D1 | Arithmetic in a DynamoDB ConditionExpression | **Fixed.** `ADD occupied :d, free_beds :neg` with `free_beds >= :d`, plus the mirror for negative deltas, as §11.4 specifies | §4.5 |
| D2 | Non-ASCII SNS Subject | **Fixed.** The subject is ASCII English and under 100 characters; Hindi goes only in the body. A live test email goes out Fri 16:00 on a personal dev topic | §1, §4.4, §6 |
| D3 | Fresh-draft latency could exceed the 30 s HTTP API limit | **Fixed.** 18 s wall-clock budget, `max_attempts=1`, 2 s connect and 7 s read timeouts, repair only with ≥8 s left, Polly only with ≥3 s left (else lazily at approve), plus a stubbed 10 s deadline test | §4.3, §8 |
| D4 | Cost-Dijkstra with a side constraint is incomplete | **Fixed.** An earliest-arrival Dijkstra (exact on FIFO networks with closures) runs before a colony is declared unreachable, with a unit test where the fallback finds a route the cost search misses | §2, §4.2, §8 |
| D5 | LLM could write place names outside the gazetteer | **Fixed, and better than asked.** Full slot-filling: the LLM text may contain no digits, number words, gazetteer names, Latin tokens or landmark nouns. Required slots are enforced | §4.3 |
| D6 | Rounding and number-word mismatch | **Moot.** No digit can come from the LLM | §4.3 |
| D7 | Hand-wavy planar-rise degrade path | **Removed.** Degrade order is v0, then fixture, then red-only, with no datum arithmetic (§11.1) | §4.1 |
| RC1 | No cut lines | **Fixed.** Cut lines at Fri 23:00, Sat 14:00, Sat 16:30, Sat 20:00 (with an explicit cut order), Sun 09:00 and Sun 13:00. IVR, HMAC, the trust formula and F6 are pre-cut | §6 |
| RC2 | Saturday block under-estimated | **Partly fixed.** The demo window ships first and the full window runs in the background. The 11:00–12:30 slot is still optimistic (§3.2) | §6 |
| RC7 | Contract PR for cutoff, thresholds, edge_id and unreachable | **Done by v1.1.** Remaining additive asks are listed | §11 |
| RC8 | Bedrock probe order | **Fixed.** `list-inference-profiles`, then global Nova 2 Lite, then `us.` Micro | §1, §6 |

Recommended items that were also adopted:
- backup hero colony
- POST-only ack (now a Could)
- DSM bias handed to the upstream owner
- rough clips recorded Sat 20:45
- bridge-edge inheritance, which is new and a good catch
- 3.0 h of explicit slack
- `wet_at_level_m` replacing `onset_level_m`. Vaibhav's plan still says Saksham uses `onset_level_m`; that note is now stale on his side.

---

## 2. Spot checks (Oct 2026)

| Claim | Result |
|---|---|
| Global CRIS IAM: "region `*` for a global profile" | **Partly right.** AWS documents three statements: (1) the regional `inference-profile/global.*` ARN; (2) the source-region foundation-model ARN; (3) `arn:aws:bedrock:::foundation-model/<model>`, which has an **empty** region, with `aws:RequestedRegion = "unspecified"` and a `bedrock:InferenceProfileArn` condition. A `*` region wildcard probably matches, but use the documented form so the first live call does not fail with AccessDenied. |
| `ortools==9.15.6755` | **Confirmed.** On PyPI since Jan 2026, Python ≥3.9. |
| `networkx==3.7` "requires Python ≥3.12" | **Not verified.** Search found 3.6.1 (Python ≥3.11) as the newest documented release. An exact pin to a version that may not resolve can break the 16:00 scaffold. Pin `networkx>=3.4,<4` and lock whatever resolves. |
| Nova `toolChoice:{tool}`; Polly Kajal neural hi-IN; SNS Subject ASCII ≤100; HTTP API 30 s limit; UCS-2 SMS 70/67 | Consistent with round 1's checks and current docs. |
| **2023 levels around the demo timestamp** | 207.25 m at 08:00 on 12 Jul, then 207.38 at 11:00 and about 207.71 that evening. 208.48 at 08:00 on 13 Jul, peaking at 208.66. **13 Jul 00:00 is therefore about 207.9–208.1 m**, roughly 2.5 m above danger level and about 2 m above the 206.0 evacuation trigger, which was first crossed around 10 Jul 23:00. See B1. |

---

## 3. Per-criterion explanations

### 3.1 Technical Soundness: 4/5

**Strengths**
- **Level-threshold cutoffs.** Each edge's `cutoff_level_m` is the minimum of `cutoff_0p30.tif` over its 15 m samples. This is consistent with Vaibhav's `cutoff_0p30 = max(onset, z'+0.30)`, so red (from `depth/<t>.tif`) and the forecast closure come from the same model and cannot disagree.
- **Bridge inheritance.** Bridges are not sampled and take the worse status of their approach edges. This is correct and was not in round 1.
- **Exact routing fallback.** With no waiting allowed, earlier arrival is never worse under an `arrival+30 ≤ close_at` rule, so earliest-arrival Dijkstra is exact. The completeness gap is closed.
- **Slot-filled drafting.** Forced tool plus slot-filling plus pre- and post-substitution validation with per-field template fallback is the strongest "zero hallucination" design among the four plans, and it can be shown on screen as chips.
- **Deterministic replay clock.** `computed_at = valid_at`.
- **Correct conditional update.** `PATCH /shelters` now uses a valid conditional update.

**Remaining defects**
1. **There is no "already wet" message or lifecycle path.** Plans are made for colonies that are "already wet", but every template is future-tense (*"{LEAD} घंटे में … पानी आने की आशंका"*). The slot rules require `{LEAD}`/`{TSUB}` for URGENT, and `lead_time_h` is rounded to 0.5 h. With `lead ≤ 0`, the card would say "within 0 hours, water may come" to a colony under 2 m of water.
   - Fix: add a `t_sub ≤ t` branch with its own template ("पानी आ चुका है"). It drops `{LEAD}`/`{TSUB}` from the required slots and makes `alert_type` URGENT.
2. **Routing origin inside the flood.** `tdsp` departs "from the colony", but nothing says how the origin node is chosen when the centroid itself is in water. If it snaps to the nearest graph node, the first edge is red, the colony becomes unreachable, and the honest "boat/NDRF" label fills the plan list at the demo time.
   - Fix: define the origin as the nearest node whose incident edges are not red, within 300 m. If the walker must wade to reach it, record the wading depth as `ext.origin_wade_m`. Otherwise the colony stays unreachable.
3. **Amber uses a single point, `hi_m(t+2h)`.** It should use the maximum of `hi_m` over `[t, t+2h]`. Near the peak, or on the falling limb, the point value can miss a crossing inside the window. The same applies to the `close_at` search: it should report the first crossing, not a sampled one. The fix is one line.
4. **`t_submersion` comes from `hi_m`**, which is conservative and good, while `lead_time_h` is shown as if it were the expected time. Label it in the UI/blog as "earliest likely (80 % upper bound)", or the blog's honesty claims weaken.
5. **Library pins:** see §2 (`networkx==3.7`).

### 3.2 Feasibility: 3/5

**Credit**
- Scope was cut materially. `replan_lite`, `snap`, HMAC, IVR, the trust formula, the verify route and F6 are gone, and F2b moved offline as a Could.
- 3.0 h of slack is explicit: Fri 0.5, Sat 1.0, Sun 1.5.
- The Should block is honestly time-boxed (Sat 18:15–20:00) with a written cut order.
- The Must column is demo-able on its own.

**Deductions**

The Must column is still very large for about 22.5 working hours. Two slots remain under-estimated:
- **Fri 21:00–22:15 (75 min).** `forecast.py` (curve and crossing solver), `cutoff.py` (sampling, bridge inheritance) and `tdsp.py` (cost search, close_at, fallback), plus four test classes. A realistic estimate is 2–2.5 h. It will eat the Fri 22:30 slack and push the drafter past midnight.
- **Sat 11:00–12:30 (90 min).** `candidates` (K=3 × best/alt with a penalty re-run), greedy `assign`, `avoid` (naive path and the 1 km name search), `priority`, `plan`, `unreachable`, the invariants **on real data for the first time**, and publish. A realistic estimate is 3 h. The first real-data run will fail an invariant or produce an unreachable hero (B1).

Several slots are not needed or are double-booked:
- **Sat 12:30–13:00 backup-deployer dry run.** Shivansh's plan explicitly moved this role to **Arjav** (dry run Sat 21:00). These 30 minutes are free to reclaim.
- **Sat 14:00–14:45.** Starting the full precompute, running `predraft` and a **20-draft live** hallucination eval, and opening the merge PR, all in 45 min, is tight. The live eval alone involves 20 × (2–9 s) calls plus a review of the failures.

**Net:** the Must path fits only if the slack is spent on these slots, which leaves the whole Should column (F5 summary, F1 mobility, F4 dedup, OR-Tools, and possibly Polly) at real risk. Because cut lines exist and the Must path is coherent, this is "tight", not "over-scoped". That earns a 3 and not a 4.

### 3.3 Integration: 4/5

**Strong v1.1 conformance**
- `edge_id` is read verbatim.
- `avoid[].edge_ids`, `free_beds` and the `unreachable.json` shape are used.
- The `POST /reports` response and the `PATCH` form follow §11.4.
- The ASCII subject, the 18 s deadline, the probe order and the §11.5 make targets (no credentials, `publish` separate) are all in place.
- The audio key is `audio/<sha256>.mp3`.
- Outputs are served through the static ladder.
- Fixtures are built from the real validator at Fri 21:00.
- The deviations (ack downgraded to Could, `/ask` Won't) are declared and justified.

**Cross-plan mismatches found**

| # | Mismatch | Fix |
|---|---|---|
| I1 | Arjav's Command-view "done when" says *"Scrub to 13 Jul 00:00 → the whole Ring Road is **red**, YP-04 is top"*. Saksham's demo moment says Ring Road is **amber** at 00:00 and turns red later, and that YP-04's route works. These cannot both be the script, and at about 208 m both may be wrong (B1) | Agree on one script at Fri 23:00, driven by `inspect_step` on Vaibhav's v0 |
| I2 | Backup-deployer dry run: Saksham does it Sat 12:30, but Shivansh reassigned it to Arjav | Drop it from Saksham's plan |
| I3 | Shivansh expects Saksham's SAM section by **Sat 13:00** and a deploy at **13:45**. Saksham's plan deploys 14:45–16:00 | Post the SAM section at 13:00 (YAML only), deploy at 14:45, and tell Shivansh |
| I4 | Shivansh lists Saksham as **second approver on `infra/`** and expects the "team inbox for SNS + plus-addresses" by Fri 23:00. Neither appears in Saksham's deliverables | Add both: 5 min each |
| I5 | The §11 alignment note says Shivansh writes `osm:<min(osmid)>:<k>`. His current plan uses the §11.3 form | Remove the stale note |
| I6 | `dispatch_cache/<t>/<colony>.json` is consumed by Arjav's ladder (rung 4) but is still **not in the contract**. `routing/trap_summary.json` in §11.2 is not scoped to a scenario | Merge the additive PR at Fri 23:00; use `scenarios/<id>/routing/trap_summary.json` |
| I7 | Vaibhav publishes `edge_cutoffs.json` ("same rule as Saksham's `cutoff.py`; he may import it"). Two implementations of the per-edge minimum can disagree between the what-if slider and road status on screen | Make one the source. Either Saksham imports Vaibhav's function, or Vaibhav reads Saksham's per-edge index. Decide at the 13:00 huddle |

### 3.4 AWS Alignment: 4/5
- The service mix fits the spec: Lambda arm64 Python 3.12 with Powertools, HTTP API, DynamoDB on-demand with conditional writes, SNS email, Polly Kajal neural with a content-hash cache, and Bedrock Nova through a probed inference profile with a kill switch.
- Static serving goes through S3/CloudFront, heavy compute stays offline, there is no always-on resource, a cost estimate is given and the $10 alarm stays.
- IAM is least-privilege per function.

**Deductions**
- The global-profile IAM statement is not in the documented form (§2).
- There is no observability for the two Lambdas that sit on the demo-critical write path: no Powertools Logger/Metrics/Tracer, and no metric for `fallback_used` or draft latency. A `jt/DraftLatencyMs` and `jt/FallbackUsed` metric costs about 10 min and gives the blog a real chart.
- If the probe lands on `us.` Micro in us-east-1, the alert text crosses regions. Note the data-residency implication in the blog. Only synthetic data is involved, so the risk is small.

### 3.5 Innovation: 4/5
- **F5, the trap counterfactual** ("N residents would have walked onto Ring Road after it flooded"), is the most persuasive single number in the project. It is cheap because it reuses `avoid`.
- **"The LLM never types a fact"**: slot-filling plus visible validator chips is a genuinely novel and demonstrable safety pattern for an LLM in disaster response.
- **F1** brings vulnerable-population priority and slower walking speeds into routing.
- **F3** adds a Kajal voice brief for low-literacy residents.

Not a 5: F4 dedup/ALL_CLEAR and OR-Tools are invisible in a 3-minute video, and the most visual dynamic beat (F2b report → re-route) is now a Could that will probably be cut.

### 3.6 Completeness: 4/5
Checked against spec Workstream D: road cutoff prediction, OR-Tools evacuation routing, Bedrock Hindi alerts, SNS/Pinpoint dispatch, shelter capacity tracking, volunteer coordination.

**Covered**
- road cutoff (red/amber)
- time-dependent routing with primary, backup and avoid
- the Bedrock drafter with validator and template
- SNS approve/send with a DynamoDB log
- Polly
- shelters GET/PATCH
- reports
- all four §9 test obligations

The plan also has five or more new features (F1–F5).

**Gaps**
- **"Volunteer coordination system"** is not mentioned anywhere, not even as a Won't.
- **OR-Tools** is named in the spec's **Must** list ("OR-Tools shelter routing"), but the plan makes it the *first* thing cut. The greedy fallback is defensible, but a judge reading the README against the pitch will notice. Either keep the min-cost-flow call (about 1 h, 30×15 arcs, offline) as the last Should and protect it, or rename the claim in the README and blog ("capacity-aware assignment; OR-Tools min-cost-flow when available").
- Shelter capacity tracking is only a Should.

### 3.7 Risk Assessment: 4/5
The risk table has 13 rows with likelihoods and concrete degrade paths, and it now includes schedule slip, the DSM bias, bridges, latency, edge_id drift, audio presign expiry and validator strictness. The rule "never loosen numbers, names or phones" remains the right one.

**Missing or mis-rated**
- **"Hero colony unreachable at 00:00" is rated Medium. It is High** given the gauge record (B1), and its mitigation is scheduled too late (Sat 13:45).
- There is no row for **cross-plan timing mismatches** (I1–I4) or for **unresolvable dependency pins**.
- There is no row for **IAM AccessDenied on the first live global-profile call**. The probe runs on laptop credentials, so a Lambda-role failure would first appear on Sat 14:45.

---

## 4. Remaining risks and blockers

| ID | Risk | Severity | Note |
|---|---|---|---|
| **B1** | **The hero colony is already under about 2–3 m of water at 13 Jul 00:00.** DRB is about 208 m. YP-04's seeded ground is 205.1 m (placeholder), and the Yamuna Pushta shelters were evacuated on 11–12 Jul. Expected result: `t_sub` in the past, a red origin edge, the colony unreachable, and the backup hero search at Sat 13:45, after the Sat 14:00 checkpoint inputs are already built | **Demo-breaking** for the moment this plan owns | Check Fri 23:00 on Vaibhav's v0 using `colony_thresholds.json` plus the gauge curve. This needs no routing code: just compare `wet_at_level_m` with the level at 00:00. Propose to the team either (a) a backup hero that is dry at 00:00 and gets wet at 02:00–08:00 (for example east-bank Mayur Vihar or Majnu ka Tilla, whichever the data says), or (b) an earlier hero timestamp such as 12 Jul 04:00 at about 207.0 m, keeping 13 Jul 00:00 for the golden test |
| B2 | The Fri routing-core slot overruns, pushing the drafter to Sat 14:00 | High | Take the 30 min from I2 and the Fri slack. Drafter recording stays the Fri stretch goal |
| B3 | The first real-data plan run fails invariants at Sat 12:30 | High | Run `inspect_step` on v0 data on **Fri 23:15** (graph prelim + v0 rasters) to surface surprises 10 hours earlier |
| B4 | The Lambda role lacks the global-profile foundation-model statement | Med | Use the documented 3-statement policy. `make smoke` invokes one draft on `demo` right after deploy |
| B5 | The demo script disagrees with Arjav's (I1) | Med | One script, decided Fri 23:00 and updated Sat 13:45 from data |

---

## 5. Actionable improvements (prioritised)

1. **(Fri 23:00, 15 min) Hero reality check.** Compute `level(00:00) − wet_at_level_m` for every seeded colony on v0 thresholds. Post the list of colonies that are dry at 00:00 and wet within 8 h. Move the backup-hero pick from Sat 13:45 to Fri 23:15, and update the demo script with Arjav (I1).
2. **(Fri, 30 min) Already-wet path.** Add a `t_sub ≤ t` lifecycle branch with a "water has arrived — move now" template, so `{LEAD}`/`{TSUB}` are no longer required. Add a dry-origin snap rule (nearest node with no red incident edge within 300 m). Add both to the fixtures (one of the 3 fixture colonies should be already wet).
3. **(Sat, 0 min net) Reclaim the dry-run slot.** Drop the 12:30–13:00 backup-deployer dry run (I2) and give it to `plan.py` on the real data. Post the SAM YAML at 13:00 per Shivansh (I3).
4. **(Fri 16:00, 2 min) Pins.** Use `networkx>=3.4,<4`, lock what resolves, and keep `ortools==9.15.6755`.
5. **(Sat 14:45, 10 min) IAM.** Use the documented global-CRIS three-statement policy. Add `JT_BEDROCK_DISABLED` to the smoke test so the template path is also proven on `demo`.
6. **(Sat 18:15, reorder the Should list)** Use F5 trap summary, then **OR-Tools** (it is in the spec's Must), then F1 mobility, then F4 dedup/ALL_CLEAR. F4 is invisible in the video, so cut it first.
7. **(10 min) Amber/close_at.** Use the maximum over the window, not a point sample. Add a unit test on a falling curve.
8. **(10 min) Observability.** Powertools Logger and Metrics: `DraftLatencyMs`, `FallbackUsed`, `ValidatorFail{check}`. Use them in the blog.
9. **(5 min) Contract hygiene.** Scope `trap_summary.json` to the scenario. Merge `dispatch_cache` into §6 at Fri 23:00. Remove the stale edge_id note (I5). Add the second-approver role and the SNS inbox deliverable (I4). Decide the single owner of the per-edge minimum with Vaibhav (I7).
10. **(README, 5 min)** List "volunteer coordination" as a post-hackathon item with a one-line design, for example "ward volunteers as SNS subscribers with ack". Then the spec scope is visibly addressed.

## 6. Alternatives worth considering

- **Hero timestamp versus golden timestamp.** Keep §9.2's golden test at 13 Jul 00:00 (any colony qualifies) but **record the hero moment earlier** (11 Jul 22:00 to 12 Jul 04:00, as DRB crosses 206–207 m). That is when Ring Road edges near ISBT/Yamuna Bazaar were amber and colonies still had real lead time. The "flood-blind route" counterfactual is most dramatic before the road goes red, not after.
- **Cheaper OR-Tools.** Instead of min-cost flow, call `pywraplp` (GLOP) once on the demo window only, with the same greedy output type. It is about 30 lines and keeps the spec's "OR-Tools" claim honest even if the full window stays greedy.
- **Share one cutoff implementation with Vaibhav.** Put `edge_min_cutoff()` in `jt_shared`, so the what-if slider and road status cannot disagree on screen. It also saves one of you about 45 min.
- **Pre-drafted live call in the video.** If Bedrock is flaky on Sunday, record the fresh draft on Saturday evening (20:45 clip) and use the `dispatch_cache` card on Sunday. The video can still show a real Nova call with latency and chips.

## 7. Sources

- [Global cross-Region inference: IAM (AWS docs)](https://docs.aws.amazon.com/bedrock/latest/userguide/global-cross-region-inference.html)
- [Securing Bedrock cross-Region inference: geographic and global (AWS ML blog)](https://aws.amazon.com/blogs/machine-learning/securing-amazon-bedrock-cross-region-inference-geographic-and-global/)
- [ortools on PyPI](https://pypi.org/project/ortools) and [ortools 9.15.6755 metadata](https://simple-repository.app.cern.ch/project/ortools)
- [NetworkX install docs](https://networkx.org/documentation/stable/install.html)
- [Yamuna nears all-time record (Tribune, 12 Jul 2023)](https://tribuneindia.com/news/raging-yamuna-nears-all-time-record-level-in-delhi-525003)
- [Yamuna swells further (Deccan Herald)](https://www.deccanherald.com/amp/story/india/yamuna-swells-further-in-delhi-old-railway-bridge-shut-for-traffic-1235924.html)
- [ETV Bharat, 12 Jul 2023](https://etvbharat.com/english/state/delhi/yamuna-water-level-rise/na20230712074750010010089)

---

## Orchestrator follow-up (after the final review)

The cross-plan issues raised in this review and in the other three final reviews were resolved centrally in **SHARED_RESOURCES.md §11.8 (contract v1.2)** on `main`. Where §11.8 differs from this plan, §11.8 wins. The resolutions cover: the data-driven demo timestamp `T_hero`, the SHELTER_IN_PLACE path for already-wet colonies, the time-to-water definitions, amber using a window maximum, a single per-edge cutoff implementation, the bund floor applied in gauge space, calibration hold-outs, causal training inputs, always-written optional artefacts and 403 treated as absent, scenario-scoped paths, Bedrock IAM for inference profiles, frontend zip deploy, version pins, and volunteer-coordination scope. The owner should re-check their timeline against §11.7 / §11.8 at the Fri 23:00 sync.
