# alerts/: slot-filled dispatch, validator, Polly, SNS (owner: Saksham)

**The LLM never types a fact.** Code picks the alert type and computes every name, number, time and helpline.
Bedrock Nova writes only sentences containing `{SLOTS}`, and code substitutes the facts. The model is shown
booleans (`has_via`, `has_avoid`, `imminent`, …) and the list of required slots. It never sees a colony name, a shelter
or a number, so it cannot leak or invent one.

```
plan / unreachable ─► lifecycle (URGENT | PREPARE | SHELTER_IN_PLACE | ALL_CLEAR, dedup + cooldown)
                   ─► facts (code) ─► [dispatch_cache hit] ─► Nova Converse, forced tool emit_dispatch, T=0
                   ─► validator (pre: numbers / names / slots · post: phones / length / script / traceable digits)
                   ─► one repair call if ≥ 8 s remain ─► per-field template fallback
                   ─► Polly Kajal (if ≥ 3 s remain, else at approve) ─► DynamoDB draft
approve ─► conditional draft→approved (idempotent) ─► SNS email (ASCII subject, Hindi body) ─► sent
```

| Check (UI chip) | Enforces |
|---|---|
| `numbers_match` | No digit (ASCII or Devanagari) and no number word (दो, ढाई, साढ़े, two, half…) in LLM text. Every digit in the final text lies inside a slot span |
| `names_match` | No corridor name or distinctive name token, no Latin in Hindi, no stray capitalised word in English, no landmark noun (मार्ग, पुल, गेट, road, bridge, school…) |
| `slots_used` | Required slots present, no unknown slot, none used more than twice, no slot without a value |
| `phones_whitelist` | Any run of 3+ digits outside a numeric slot is 1077 or 112. `+91` and 10-digit numbers are rejected |
| `length` | `sms_hi` ≤ 160 code points and contains 1077. Each message ≤ 600 |
| `script` | `message_hi` ≥ 60% Devanagari letters |

Only `script`/`length` may ever be loosened.

## Run it

```bash
make -C alerts predraft [WINDOW=demo|all] [AUDIO=1]   # dispatch_cache/<t>/<colony>.json; fails if any card is invalid
make -C alerts test
make -C alerts halluc-eval            # replays tests/recorded/*.json → 0 untraceable tokens required
make -C alerts probe                  # Bedrock region/profile probe (AWS creds; SHARED §11.6 order)
make -C alerts halluc-live N=20       # 20 live Nova drafts → report + tests/recorded/live_20.json
```

Without credentials or `JT_BEDROCK_MODEL_ID`, drafts use the validated templates (`fallback_used=true`,
`validation.source="template"`), audio is `null`, and approved emails go to `$JT_LOCAL_DATA/outbox/<id>.eml`.

**About the recorded samples:** `tests/recorded/handwritten_samples.json` contains **hand-written** stand-ins,
labelled as such, not real Nova outputs. They exercise the pass, repair and fallback paths. The first live run of
`make halluc-live` records real outputs next to them.

## Environment (Lambda `jt-<env>-alerts-fn`)

`JT_ENV`, `JT_DATA_BUCKET`, `JT_BEDROCK_REGION`, `JT_BEDROCK_MODEL_ID`, `JT_BEDROCK_DISABLED` (kill switch),
`JT_SNS_TOPIC_ARN`, `JT_POLLY_VOICE=Kajal`, `JT_DISPATCHES_TABLE`, `JT_STATE_TABLE`, `JT_DRAFT_DEADLINE_S=18`.
Metrics are CloudWatch EMF in namespace `jt`: `DraftLatencyMs`, `FallbackUsed`, `ValidatorFail_<check>`.
