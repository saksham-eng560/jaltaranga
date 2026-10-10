# The LLM never types a fact

*Draft section for the AWS Builder Center post "Gauge to street: honest flood evacuation on serverless AWS".*

A flood dispatch is not the place for a creative model. If the message says "go to Kashmiri Gate" when the shelter
is in Daryaganj, or "you have 3 hours" when the plan says 2.5, people walk into water. So in Jaltaranga the model
writes the **sentences**, and code writes every **fact**.

**1. The model never sees a fact.** The Bedrock Nova call (Converse API, one forced tool `emit_dispatch`, temperature 0)
receives the alert type, a few booleans (*is there a road to avoid? is water imminent?*) and the list of slots it must
use. It is never told the colony, the shelter, the road names, the time or any number. It cannot leak what it never saw.

**2. It writes slots, code fills them.** The model answers with text such as
`"{AVOID} {CUT} से बंद है। तुरंत {SHELTER} जाएं ({BEDS} जगह खाली)। मदद: {HELP}"`. Code substitutes values computed
from the evacuation plan and records the exact character span of every substituted value.

**3. A deterministic validator checks both sides.** Before substitution, the text must contain no digit (ASCII or
Devanagari), no number word (दो, ढाई, साढ़े, two, half), no place name or distinctive name token from the corridor
gazetteer, no landmark noun (मार्ग, पुल, गेट, road, bridge), no Latin in Hindi, and every required slot. After
substitution, every digit must sit inside a slot span. The only phone numbers allowed are 1077 and 112. The SMS must
fit in 160 characters and carry 1077, and the Hindi message must be mostly Devanagari. Those six checks are the green
chips the officer sees on the card.

**4. Failure is boring.** One repair call carries the validator errors back to the model, and only when at least 8 of the
18 seconds remain. Any field that still fails is replaced by a deterministic template that passes the same validator by
construction. So the worst case is a plainer message, never a wrong one, and the card says `fallback_used`.

**5. A human approves.** Nothing is sent until an officer clicks *Approve*. Then SNS emails the pradhan (an ASCII
subject, with Hindi in the body), and Amazon Polly's Kajal voice reads the *validated* Hindi text aloud.

What we measure: across replayed drafts, the number of untraceable tokens in any card shown to the officer must be **0**
(`make -C alerts halluc-eval`). The fallback rate is reported, not hidden.

*Limits:* the validator guarantees that facts come from the plan. It does not make the plan right. The plan is only as
good as the DEM, the forecast and the shelter data behind it, and the demo's contacts and capacities are synthetic.
