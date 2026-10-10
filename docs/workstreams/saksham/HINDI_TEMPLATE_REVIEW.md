# Hindi / English template review (`alerts/jt_alerts/templates.py`)

This is the plan §6 template review, done line by line against the rendered cards for every alert type,
with one and two avoided roads, bed counts of 1 and 1,200, and very long names (`alerts/tests/test_templates.py`).

| # | Before | After | Why |
|---|---|---|---|
| 1 | `{AVOID} {CUT} से बंद है` for two roads | `… बंद हैं, उन रास्तों से न जाएं` when there are 2 roads | Verb agreement: "रिंग रोड और बेला रोड … बंद हैं" |
| 2 | `उधर न जाएं` | `उस रास्ते से न जाएं` | "उधर" (over there) is vague. Name the action: don't take that route |
| 3 | `({BEDS} जगह खाली)` | `(खाली जगह: {BEDS})` | Reads correctly for any count, including 1 (no है/हैं agreement) |
| 4 | `तुरंत {VIA} होकर {SHELTER} जाएं` | `तुरंत {VIA} होकर पैदल {SHELTER} जाएं` | Routes are walking routes. Say "on foot" |
| 5 | SMS `{AVOID} न जाएं` | `{AVOID} पर न जाएं` | "Don't go *on* Bela Road". Without पर it reads "don't go Bela Road" |
| 6 | SMS `पानी कभी भी।` | `पानी कभी भी आ सकता है।` | A complete sentence. The variants shorten automatically if 160 chars is exceeded |
| 7 | EN `in about {LEAD} hours` | `by {TSUB} (in about {LEAD} h)` | Avoids "1 hours". The clock time is the more useful fact and comes first |
| 8 | EN `({BEDS} places free)`, `is closed … use it` | `(free places: {BEDS})`; `are closed … use them` for 2 roads | Same agreement fixes in English |

Kept as is: `चेतावनी / सूचना / तुरंत निकलें / पानी आ चुका है / सावधान / राहत` headings, `मदद: 1077 या 112`, the SHELTER_IN_PLACE
safety lines (`पानी में चलकर बाहर न निकलें। छत या ऊपरी मंज़िल पर जाएं और बिजली बंद रखें।`) and the vulnerable-first sentence.

Every template still passes all six validator checks: no digit, number word, name or landmark noun outside a slot.
That is enforced by `test_templates_always_validate_on_real_plans` over every plan × alert type.
Before the demo recording, have a teammate read three rendered cards aloud (URGENT, PREPARE, SHELTER_IN_PLACE)
together with the Kajal audio. That checks how it sounds, which a text review cannot.
