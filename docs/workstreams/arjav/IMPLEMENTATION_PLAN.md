# Jaltaranga — Frontend & Visualization (frontend/) — Implementation Plan v1.1 (owner: Arjav)

> Branch `feature/arjav` · Folder `frontend/` only (plus small PRs to `shared/fixtures/`, per SHARED_RESOURCES §10).
> Contracts are **not** redefined here: schemas §5 + §11.3, routes §7 + §11.4, S3 §6 + §11.2, checkpoints §11.7 of `SHARED_RESOURCES.md` (SR). Where SR §11 differs from §1–§10, §11 wins and this plan follows it.
> Budget: about 25 focused hours, Fri 9 Oct 19:30 → Sun 11 Oct submission, including **≈3.25 h of explicit slack**.

## 0. What the frontend must prove in the 3-minute video

A judge watches the **July 2023 replay** being scrubbed: water spreads over the terrain, Ring Road turns **amber, then red**, Yamuna Pushta's pin counts down to submersion. The officer opens the ranked plan, drafts a **validated Hindi dispatch** and approves it. The resident's phone, in airplane mode, still shows **one route, one shelter, 1077**.

Flood Hub and CWC already show the gauge. Every screen has to go past the gauge to the street, the route and a verified instruction. "Offline" in this plan and in the video means the **Offline Colony Pack** (route drawn as SVG), **not** an offline basemap.

---

## 1. Research findings that shaped decisions (verified 9 Oct 2026)

| Topic | Finding | Decision | Source |
|---|---|---|---|
| MapLibre major | v6.0.0 (22 Jul 2026) is ESM-only and **WebGL2-only**; 5.24.0 (23 Apr 2026) is the last 5.x and still runs on WebGL1 | Pin **maplibre-gl `5.24.0` exactly** (low-end Android). v6 is post-hackathon | [v5→v6 guide](https://raw.githubusercontent.com/maplibre/maplibre-gl-js/main/docs/guides/v5-to-v6-migration-guide.md), [npm](https://registry.npmjs.org/maplibre-gl) |
| Terrain | AWS Open Data **Terrain Tiles**, Terrarium PNGs, needs `encoding:"terrarium"` (wrong encoding renders as noise, no error). About 45 tiles for z8–13 over the bbox, <2 MB | **Bundle** the z8–13 tiles into the app (`public/terrain/`) so they ship with the Amplify deploy, load fast and are whole-file 200s that the SW can cache. Direct AWS URL is the fallback | [AWS registry](https://registry.opendata.aws/terrain-tiles), [style spec](https://maplibre.org/maplibre-style-spec/sources) |
| Basemap | `pmtiles extract --bbox --maxzoom` gives one small file; Protomaps daily builds have no CORS | I extract `delhi.pmtiles` (z≤15); Shivansh uploads to `tiles/basemap/` (SR §11.2) behind the data CloudFront | [Protomaps](https://docs.protomaps.com/basemaps/downloads) |
| PMTiles + service worker | PMTiles uses `Range` → `206`. The Cache API refuses 206 and Workbox caches only 200 by default | **No SW route for `*.pmtiles`** (pass-through, network only). Offline = colony pack (§8.1) | [W3C thread](https://lists.w3.org/Archives/Public/public-webapps-github/2016Jun/0774.html) |
| Depth COG | `@geomatico/maplibre-cog-protocol` accepts only EPSG:3857; §5.3 COGs are 4326 | Draw the §5.3 GeoJSON polygons styled by `depth_class` (SR §11.3). No COG protocol | [README](https://github.com/geomatico/maplibre-cog-protocol) |
| Amplify deploy | Shivansh's stack creates the Amplify App + Branch for **manual (zip) deploys** via `infra/scripts/deploy_frontend.sh`. In a Git-connected monorepo, `frontend/amplify.yml` is ignored; the spec must be at repo root or in the console with `AMPLIFY_MONOREPO_APP_ROOT=frontend` (SR §11.6) | **No `frontend/amplify.yml`.** I build locally (`VITE_*` baked from `.env.demo`) and `deploy_frontend.sh` zips `frontend/dist`. Only if the app is switched to Git-connected does a root `amplify.yml` (appRoot `frontend`) get added, by PR to `main` | [Amplify monorepo](https://docs.aws.amazon.com/amplify/latest/userguide/monorepo-configuration.html), [manual deploys](https://docs.aws.amazon.com/amplify/latest/userguide/manual-deploys.html) |
| Hosting cost | Amplify allowance (1,000 build-min, 15 GB served, 5 GB stored); accounts after mid-2025 use credits | Footprint about 5 MB shell + small JSON → effectively $0 | [Amplify pricing](https://aws.amazon.com/amplify/pricing/) |
| Hindi audio | Polly **Kajal** is bilingual hi-IN/en-IN neural. Presigned S3 GET needs S3 CORS from the Amplify origin (adopted SR §11.6). Desktop Chrome hi-IN `speechSynthesis` uses a *network* voice | Play `audio_url_hi`; cache the blob in the colony pack. `speechSynthesis` is labelled "device voice" and is **not** an offline path on desktop | [Polly bilingual](https://docs.aws.amazon.com/polly/latest/dg/bilingual-voices.html) |
| PWA | vite-plugin-pwa 2.0.0 shipped 3 Oct (too fresh); 1.3.0 peers `vite ^8` | Pin **vite-plugin-pwa `1.3.0`** | [npm](https://registry.npmjs.org/vite-plugin-pwa) |
| S3 keys with `+05:30` | Static keys like `plans/2023-07-13T00:00:00+05:30.json` contain `+` and `:`; S3 can decode a raw `+` in a path as a space | Build every static URL with `encodeURIComponent(key segment)`; a contract test fetches one real key through CloudFront | — |
| Comparison baseline | Flood Hub gauge `CWC_015-UYDDEL` thresholds 204.5 / 205.33 / 208.66 m. An NGT filing says CWC's 12 Jul 2023 forecast was about 207.1 m | Split-screen is gauge-level only, no third-party branding. **The 207.1 m caption is used only if the exact page/line is quoted by Sat 22:00; otherwise the caption says "gauge-level forecast"** | [Flood Hub](https://sites.research.google/floods/l/28.6625/77.2467/13/g/CWC_015-UYDDEL), [NGT reply](https://www.greentribunal.gov.in/sites/default/files/news_updates/ADDITIONAL%20REPLY%20BY%20R-1%20AND%20R-2%20IN%20OA%20NO.%20635%20of%202024%20NEWS%20ITEM%20TITLED%202023%20DELHI%20FLOODS%20HOW%20GOVT.%20DID%20NOT%20SEE%20DELHI,S%20WORST%20FLOOD%20COMING%20-EVEN%2024%20HOURS%20BEFORE%20IT.pdf) |

## 2. Technology choices (exact pins; every release ≥14 days old)

| Concern | Choice | Why |
|---|---|---|
| Build | `vite` **8.3.3** (not 8.3.4, one day old), `@vitejs/plugin-react` 6.1.1, `typescript` 6.0.3 (skip TS 7) | Fast HMR, static output |
| UI | `react` / `react-dom` 19.2.8, plain CSS tokens, **no component library** | Small bundle, full control of type and contrast |
| Map | `maplibre-gl` 5.24.0, imperative `useMap` hook, **lazy-loaded** (`React.lazy` + dynamic `import('maplibre-gl')`) | Terrain/feature-state direct; map engine (~230 KB gz) never ships to Colony/Lite |
| Tiles | `pmtiles` 4.5.0, `@protomaps/basemaps` 5.7.2 | Self-hosted one-file basemap |
| State | `zustand` 5.0.15; `@tanstack/react-query` 5.x (exact version locked at scaffold, ≥14 days old) | Replay clock; cache keyed by `at` + prefetch |
| Offline | `vite-plugin-pwa` 1.3.0, `workbox-window` 7.4.1, `idb-keyval` 6.3.0 | Precached shell + IndexedDB colony pack |
| i18n / fonts | Hand-rolled `t()` (`hi.json`/`en.json`, ~120 strings); self-hosted Noto Sans + Noto Sans Devanagari subsets (~120 KB) | No dependency, works offline |
| Types | `json-schema-to-typescript` 16.0.0 → `src/shared/types.ts` | One source of truth (SR §8) |
| Tests | `vitest` 5.0.x, `ajv` 8.x (exact in lockfile), `@playwright/test` 1.63.x | Units, fixture conformance, §9.5 smoke |

## 3. Architecture

```
 Amplify Hosting jt-demo-web (manual zip deploy; Amplify already includes CloudFront — no second CDN in front)
   index.html + hashed JS/CSS + sw.js + fonts + /terrain/{z}/{x}/{y}.png + /fixtures + /demo
        │
 DataClient — SR §11.4 data-access ladder
   GETs  : static  → https://<data-CF>/scenarios/<id>/… and /static/…   (precomputed, same files Lambdas serve)
           fixtures→ /fixtures/* (shared/fixtures + thin mocks, bundled)          → fully offline
   WRITES: HTTP API jt-demo-api only for dispatch draft/approve, GET /dispatches, POST /reports, PATCH /shelters
   Tiles : <data-CF>/tiles/basemap/delhi.pmtiles (Range, SW pass-through) · /terrain/* bundled (SW CacheFirst)
 Service worker: precache shell+fonts+fixtures+terrain; NetworkFirst(3 s) scenario JSON; pmtiles not cached;
                 colony pack in IndexedDB (plan, shelters, route, dispatch, audio blob)
```

**Replay clock (single source of truth).** zustand holds `scenarioId, at, playing, speed`. `at` snaps to `manifest.valid_at[]`; default is `manifest.default_at` (SR §11.3). It is mirrored to the URL (`?at=…&view=command&colony=DEL-YP-04`). Every query key includes `at`; while playing, `at+1..3` are prefetched. A permanent **"REPLAY · 13 Jul 2023 · not a live alert"** badge is always visible. The hero colony is `DEL-YP-04`, overridable by `?colony=` / `VITE_HERO_COLONY` for the backup hero picked Sat morning (SR §11.6).

**Threshold events** come from `manifest.events[]` (warning/danger/evacuation/record_broken/peak). A `peak` with `ts_verified:false` is labelled "peak (hour unverified)". The client computes events from gauges + `manifest.thresholds` only as a fallback, and a unit test checks both agree on the fixture.

**Static-mode resolution rules** (`api/static.ts`, unit-tested):
| Layer | Rule |
|---|---|
| manifest | `scenarios/<id>/manifest.json`; `artefacts{…: real\|fixture\|missing}` drives the data chip |
| gauges | `scenarios/<id>/gauges.json`, filter `ts ≤ at` |
| forecast | `max(manifest.issued_at[] ≤ at)` → `forecasts/<issued_at>.json` |
| flood | `depth/index.json` → entry with `valid_at == at` → its `geojson` |
| roads | `roads/<valid_at>.json`, filtered to non-green defensively; joined to `static/osm/roads.geojson` on the opaque, direction-agnostic `edge_id` (SR §11.3) |
| plans | `plans/<valid_at>.json` + `plans/<valid_at>.unreachable.json` (404 → `[]`) |
| colonies / shelters | `static/colonies.geojson` (contacts already stripped, SR §11.4) and `static/shelters.geojson` (`free_beds`) |

**Degrade ladder (automatic, shown in `StatusBanner` as "data: static / cached / demo" plus the `manifest.artefacts` chip).**
1. Static GET fails or takes >3 s → last SW-cached copy → bundled fixture.
2. WebGL2 + terrain → **2.5D** (pitch 60, exaggeration ~6×, hillshade). WebGL1 or frame time >50 ms → **2D**. No WebGL, `saveData`, `effectiveType ∈ {slow-2g, 2g}` or `?lite=1` → **Colony Lite** (no map chunk, RouteSvg only).
3. PMTiles fails → plain background + `static/osm/roads.geojson` + river polygon (`static/osm/river.geojson`) + our layers.
4. Dispatch draft API fails → Saksham's validated pre-draft `scenarios/<id>/dispatch_cache/<t>/<colony>.json` if present → client template from plan fields, labelled `fallback_used`. **A card with `validation.passed=false` is never rendered without the fallback banner** (unit-tested).
5. Polly audio missing → `speechSynthesis` hi-IN ("device voice", online only on desktop) → text.

**Datum rule (SR §11.1).** The frontend never computes "level − `ground_elev_m`". Pin colours come from `plan.t_submersion`; the time-to-water band uses Vaibhav's `colony_thresholds.json` (§8.2).

## 4. File structure (`frontend/`)

```
frontend/
├── package.json  vite.config.ts  tsconfig.json  index.html  .env.example  .env.demo  playwright.config.ts
├── public/
│   ├── icons/  fonts/  terrain/{z}/{x}/{y}.png        # bundled Terrarium z8–13 (mirror-terrain.mjs)
│   └── demo/yamuna-2023-07/                           # baked static snapshot for recording (Sun 11:00)
├── mocks/yamuna-2023-07/      # thin gap-fillers only (plans/roads/dispatch until Saksham's fixtures land Fri 23:00)
├── scripts/
│   ├── gen-types.mjs  sync-fixtures.mjs (shared/fixtures wins over mocks)  bake-static.mjs
│   ├── mirror-terrain.mjs  extract-basemap.sh (pmtiles extract → hand to Shivansh)  check-size.mjs
├── src/
│   ├── main.tsx  App.tsx  routes.tsx                  # /command, /colony/:cid (?lite=1), /compare, /report (Could)
│   ├── shared/types.ts (generated)  constants.ts (§1 thresholds, bbox, 1077/112, 0.30 m)
│   ├── api/client.ts (ladder, timeout, §7 error envelope)  static.ts (resolution rules)  writes.ts  queries.ts
│   ├── state/replay.ts (clock + URL sync)  prefs.ts (lang, a11y, render mode; localStorage in try/catch)
│   ├── map/MapView.tsx (lazy)  useMap.ts  capability.ts  style.ts  director.ts
│   │   └── layers/terrain.ts flood.ts roads.ts colonies.ts routes.ts shelters.ts
│   ├── views/CommandView.tsx  ColonyView.tsx  CompareView.tsx  ReportView.tsx (Could)
│   ├── components/TimelineScrubber GaugeSparkline(+forecast fan) PlanList PlanCard DispatchCard ValidationChips
│   │   TimeToWaterCard RouteSvg ShelterList AudioBrief Legend StatusBanner UnreachableList LangToggle DebugPanel
│   ├── i18n/en.json hi.json t.ts
│   ├── lib/time.ts (IST)  tsub.ts  geo.ts  colonyPack.ts  image.ts (Could)  reportQueue.ts (Could)
│   └── styles/tokens.css a11y.css
└── tests/unit/*.test.ts  tests/e2e/smoke.spec.ts
```

## 5. Screens

| Screen | Content | Done when |
|---|---|---|
| **Command** (desktop, officer) | Map (flood by `depth_class`, G/A/R roads, colony pins by T_sub, selected route) · left: ranked `EvacuationPlan` list (priority, lead time, population, vulnerable counts) + **"Boat / NDRF needed"** list from `unreachable.json` · right: plan detail (primary solid, backup dashed, `avoid[]` with cutoff times; avoided roads highlighted via `avoid[].edge_ids[]`, falling back to `name` match) + "re-routed" badge if `ext.replanned_due_to` · **Draft dispatch** → `DispatchCard` (hi/en, SMS preview + char count, validation chips, audio) → **Approve** → `sent` · bottom: scrubber + gauge sparkline with threshold lines and forecast fan | Scrub to 13 Jul 00:00 → the whole Ring Road is red, YP-04 is top, draft → approve shows `sent` |
| **Colony** (mobile, resident/pradhan) | Hindi by default (EN toggle), 28 px+ Devanagari, one card: "पानी लगभग 3½ घंटे में" + band, **one** route (RouteSvg + "via लाल कुआं मार्ग"), shelter + `free_beds`, "रिंग रोड न लें", tap-to-call **1077 / 112**, ▶ सुनें, "Save for offline". `?lite=1` = no map chunk | Works at 360 px; Colony chunk ≤100 KB gz; opens in airplane mode after save |
| **Compare** (video) | Split view on one clock: left "basin bulletin" (gauge number from payload, danger line, generic text), right the Colony card + mini-map | One scrub drives both panes |
| **Report** (Could) | Kind, depth slider, photo, location → queue → presigned upload | Pin appears on Command |

Encodings are fixed in the Legend (shape + colour): roads green / amber / red-dashed; pins by `t_sub − at`: already flooded dark violet ✕, <2 h red, 2–6 h amber, 6–12 h yellow, no plan grey-green; unreachable = boat icon; depth = 4 blues for `depth_class` `0.05-0.3 | 0.3-1 | 1-2 | >2`. Every name and number on screen comes from a payload (including Hindi street names), never from free text.

## 6. Timeline with SR §11.7 checkpoints and cut lines

Each slot is done only when its **Done when** passes. **Slack** rows are real; they are the first thing spent when a slot overruns.

### Fri 9 Oct (19:30–24:00, 4.5 h incl. 0.5 h slack)
| Time (IST) | Task | Done when |
|---|---|---|
| 19:30–20:00 | Scaffold, exact pins (§2), tree, ESLint, `.env.example`/`.env.demo` (`VITE_DATA_MODE=static\|fixtures`, `VITE_STATIC_BASE`, `VITE_API_BASE`, `VITE_TILES_BASE`, `VITE_HERO_COLONY`) | `npm run build` passes |
| 20:00–20:30 | `gen-types` from Shivansh's PR #1 schemas (in since 16:30) + `constants.ts`. **Post `VITE_*` names, build dir `frontend/dist` and manifest-key feedback to Shivansh (his Fri 20:00 ask)** | `tsc --noEmit` passes importing `manifest.json`, `gauges.json`, Vaibhav's `forecast_nodes.json` |
| 20:30–21:30 | DataClient: static + fixtures ladder, `static.ts` rules, `+` encoding, `writes.ts` stub. Thin mocks for plans/roads/dispatch only (5 steps, 12 Jul 18:00 → 13 Jul 18:00, 3 colonies, Ring Road red from 02:00 — same shape Saksham generates) | `plans?at=2023-07-13T00:00+05:30` resolves in fixtures mode; ajv passes on all fixtures |
| 21:30–23:00 | Lazy `MapView` + basemap (public demo PMTiles for now) + flood/roads/colonies layers + replay store + scrubber + URL sync | Scrubbing changes flood extent, road colours and pin colours |
| **23:00** | **CHECKPOINT Fri 23:00 (SR §11.7): fixtures for every schema in `shared/fixtures/`, v1.1 PR merged.** Pull them; `sync-fixtures` prefers them over my mocks; open PR `shared/fixtures/field_report.json` | ajv green on every shared fixture |
| 23:00–23:30 | Swap to Saksham's plans/roads/dispatch fixtures; fix drift; push; post a GIF | Map runs on shared fixtures only |
| 23:30–24:00 | **Slack** | — |

**Cut line Fri 23:00:** a missing fixture → keep my mock for it and ping the owner for an ETA. If the map does not scrub by 23:30 → drop 2.5D terrain to 2D-only for Saturday's first half (terrain is retried only in its own slot).

### Sat 10 Oct (DTU build day, 09:00–21:30)
| Time | Task | Done when |
|---|---|---|
| 09:00–10:30 | Command view: PlanList, PlanCard, primary/backup routes, `avoid[].edge_ids` highlight, UnreachableList, re-routed badge, flyTo on select | Clicking YP-04 frames its route; all Ring Road edges red |
| 10:30–12:00 | DispatchCard: draft → chips → approve → inbox (`writes.ts` to the API, with ladder rung 4). AudioBrief ▶ button | Works on fixtures; `validation.passed=false` fixture shows the fallback banner |
| 12:00–12:30 | **Slack** (deploy prep: `check-size.mjs`, SPA rewrite list for Shivansh) | — |
| 12:30–13:15 | First deploy as soon as Shivansh posts stack URLs (his Sat 12:30): `npm run build` with `.env.demo` → `deploy_frontend.sh`. Fallback: `dist/` → S3 `web/` behind the data CloudFront with hash routing | **Public Amplify URL in channel by 13:15** |
| 13:15–13:45 | Lunch + team integration huddle (edge_id join, `depth_class`, manifest) | — |
| **14:00** | **CHECKPOINT Sat 14:00 (SR §11.7): demo-window data (13 Jul 00:00–06:00 forecasts, depth, roads, plans) in S3?** Check `manifest.artefacts` | Decision posted: **record from static (real)** or **from fixtures** |
| 14:00–15:30 | Colony view (bilingual, RouteSvg, ShelterList, call links, `?lite=1`) + TimeToWaterCard with band (§8.2). 10-min Hindi review by a teammate at 15:20 | Passes at 360×740; Colony chunk ≤100 KB gz |
| 15:30–16:30 | Terrain: bundled Terrarium `raster-dem` + hillshade, pitch/exaggeration tuning, `capability.ts` 2.5D → 2D → Lite | `?render=2d` / `?lite=1` work; floodplain reads as relief |
| 16:30–17:30 | **Integration** (Saksham's live writes from 16:00): static GETs from the data CloudFront, live draft/approve/inbox, DebugPanel ajv errors per layer. **Stops at 17:30 regardless** | Each layer renders real data or a gap is filed with the ajv error |
| 17:30–18:45 | PWA (precache shell/fonts/fixtures/terrain, pmtiles pass-through) + **Offline Colony Pack** (§8.1) | DevTools Offline → cold reload `/colony/DEL-YP-04` → full card + audio |
| 18:45–19:15 | Dinner | — |
| 19:15–20:00 | **Compare view** (§8.3), reusing Colony card + sparkline | One scrub drives both panes |
| **20:00** | **CHECKPOINT Sat 20:00 (SR §11.7): FEATURE FREEZE.** Anything not green is cut (order below) | — |
| 20:00–21:00 | Vitest units + Playwright §9.5 smoke on fixtures; redeploy | `npm test`, `npx playwright test` pass locally |
| 21:00–21:30 | **Slack** (bug fixes only); verify or drop the 207.1 m caption by 22:00 | — |

**Cut line Sat 14:00 (data):** if the demo window is not in S3 → the recording uses `public/demo/` built from shared fixtures tuned to Shivansh's real gauge curve, with the badge reading "illustrative scenario"; the 16:30 integration slot shrinks to the write calls only and **stops at 17:30**.
**Cut line Sat 14:00 (mine):** if Command + Dispatch are not green → Compare moves to Could and the mirrored-terrain tuning drops to "direct AWS tiles, default exaggeration".
**Cut order at Sat 20:00 (first cut first):** Report view → a11y mode → terrain tuning (ship 2D + hillshade) → time-to-water band (keep the plain countdown) → Compare → Offline pack audio blob (keep text + route). The Must column is never cut.

### Sun 11 Oct (09:00–16:00)
| Time | Task | Done when |
|---|---|---|
| **09:00–10:00** | **CHECKPOINT Sun 09:00 (SR §11.7): golden test §9.2 on `demo`** with the team; I fix frontend blockers only. Playwright against the deployed URL (Should) | §9.2 green; smoke green on the URL (or on the local build if the URL fails) |
| 10:00–11:00 | Recording tooling + polish: Director mode `?demo=1` (hides chrome, keyframed camera, keys `Space`/`←`/`→`/`1-4`); a11y high-contrast mode **only if golden test is green** (CSS tokens, no new data paths) | Full flow plays from the keyboard |
| 11:00–11:30 | `bake-static.mjs` (after teammates' last `scenarios/` sync at 11:00) → `public/demo/`; tag `demo-v1`; redeploy | Recording build runs with Wi-Fi off |
| 11:30–13:00 | **Slack 1.5 h** + two full rehearsals with Saksham's pre-drafted dispatches | — |
| **13:00–14:30** | **CHECKPOINT Sun 13:00–14:30: record** (OBS, 1080p60, two takes per segment). Recording beats everything | All segments captured |
| 14:30–15:45 | Edit with the team: Kajal clip, captions, source captions | Video ≤ 3:00 |
| 15:45–16:00 | **CHECKPOINT Sun (deadline − 2 h): submit** — URL in incognito, repo, video, blog. Deadline assumed 18:00 IST (Shivansh's plan); **confirmed in the channel Fri night**; if earlier, every Sun slot moves up and the 11:30 slack absorbs it | Submitted |

**Cut line Sun 11:00:** if `bake-static` fails → record from the fixtures build. **Sun 13:00:** record with whatever is frozen; no fixes during recording.

**Hours:** Fri 4.0 work + 0.5 slack; Sat 10.25 work + 1.25 slack (+ meals); Sun 5.5 work + 1.5 slack. Total ≈ 19.75 h build/demo + **3.25 h slack** ≈ 23 h, inside the ~25 h budget.

## 7. MoSCoW (the Must column alone gives a demo-able feature)

| Must (~12 h) | Should (~5 h) | Could (~3 h) | Won't (this weekend) |
|---|---|---|---|
| Skeleton, types, **2-mode GET ladder (static → fixtures)** + API for writes only | Offline Colony Pack (§8.1) | Field-report capture + presigned upload + offline queue (§8.5) | `api` GET mode (Lambdas for reads) |
| Replay clock, scrubber, `?at=`, manifest events | Time-to-water band (§8.2; plain countdown is Must) | a11y high-contrast mode (§8.4; ▶ Listen is Should) | Offline basemap |
| Map: flood by `depth_class`, G/A/R roads, pins by T_sub, routes, shelters, unreachable list | Split-screen Compare (§8.3) | Provenance drawer from `provenance.json` (Shivansh) | Vaibhav's what-if slider / model-card page (land after freeze) |
| 2.5D terrain (bundled Terrarium) + 2D/Lite fallback | ▶ Listen (AudioBrief) | Infra-exposure layer (Shivansh) | Push, SMS UI, websockets |
| Command: ranked plans → draft → approve, chips, fallback banner | Director mode (recording tooling, not a product feature) | Depth PNG overlay | Auth/RBAC (officer is `officer-demo`) |
| Colony view (bilingual, one route, 1077/112, `?lite=1`) | Playwright against the deployed URL | Sep 2025 scenario switcher | Multi-basin |
| Amplify deploy, SW shell precache, Playwright smoke on fixtures | | | |

## 8. New and enhanced features

### 8.1 Offline Colony Pack: "works in airplane mode" (Should, ~1.25 h)
- **Value.** The network fails in heavy rain (spec §5); the pradhan's phone needs the plan saved *before* that.
- **How.** "Save for offline" (and an automatic save when a dispatch for that colony is approved) writes `{plan, shelters[], route_geojson, dispatch(hi/en/sms), audio blob, savedAt, at}` to IndexedDB. `RouteSvg` projects `route_geojson` to a 320×320 inline SVG with street labels from `via_names_hi` and needs **no tiles**. The Colony route reads the pack first, the network second. A "saved 13 Jul 04:00, may be outdated" stamp turns amber after 2 h. Audio is a blob because presigned URLs expire (1 h). No basemap offline (PMTiles 206, §1).
- **Done when.** Airplane mode + cold reload of `/colony/DEL-YP-04` shows route, shelter, 1077 and plays the Kajal audio.

### 8.2 Time-to-water countdown with forecast band (countdown Must; band Should, ~1 h)
- **Value.** "Water in about 3½ h (earliest 2 h 40 m)" is actionable; a gauge height in metres is not.
- **How (hydraulically consistent, SR §11.1).** Centre = `plan.t_submersion − at` (routing). The colony's gauge-equivalent trigger `L*` is `wet_at_level_m` from Vaibhav's `models/inundation/v1/colony_thresholds.json` (DRB gauge level at which the 150 m buffer first gets wet). If that file is missing, `L*` = central `level_m` interpolated at `plan.t_submersion`. Earliest = first time the interpolated `hi_m ≥ L*`; latest = first time `lo_m ≥ L*` ("may not flood" if never). Because `lo ≤ level ≤ hi`, the band contains the centre by construction — **no clamping**, and no `ground_elev_m` arithmetic. Label: "gauge-equivalent estimate, `coverage` band". `tsub.ts` is pure and unit-tested. Pin colour uses the earliest time.
- **Done when.** At 00:00 the YP-04 centre matches `lead_time_h`, the band contains it, and the band narrows as the replay advances.

### 8.3 Split-screen "Basin warning vs Jaltaranga street plan" (Should, ~0.75 h)
- **Value.** Differentiation in 10 seconds of video: the left is what Delhi had (a gauge number), the right is what a colony needs.
- **How.** `/compare?colony=DEL-YP-04`. Left: big gauge number from `gauges.json`, sparkline with 204.5/205.33/206.0 lines, a paraphrased bulletin sentence from `constants.ts`; **no third-party logos**. Right: the Colony card, a mini-map with the route and the red Ring Road, the Hindi dispatch. Shared clock. Caption cites the Flood Hub gauge page (and NGT only if verified, §1).
- **Done when.** Scrubbing 12 Jul 18:00 → 13 Jul 06:00 shows the left only crossing lines while the right changes route and status.

### 8.4 Accessibility mode and "सुनें / Listen" (Listen Should, Sat; contrast mode Could, Sun)
- **How.** ▶ plays `audio_url_hi` (Kajal), else `speechSynthesis` hi-IN on the same validated `message_hi`, labelled "device voice". The Could toggle (default from `prefers-contrast`) switches to 7:1 tokens, 1.35× type, Devanagari line-height 1.7, 48 px targets; `aria-live` announces "रिंग रोड बंद".
- **Done when.** Audio plays (offline from the pack); with the toggle, Lighthouse a11y ≥95 on Colony.

### 8.5 Citizen field reports (Could, ~2 h)
`/report` collects `kind`, depth (cm), optional photo, GPS. `image.ts` re-encodes to a 1280 px JPEG (≤ ~300 KB, EXIF stripped). `POST /reports` returns `{report, upload:{url, fields}|null}` (**adopted in v1.1**, SR §11.4); the browser POSTs to `uploads/reports/<id>.jpg`. An IndexedDB queue retries on `online`. Pins by `trust`, hollow when `verified=false`; demo reports are labelled **synthetic**. If this is cut, Saksham's "report → re-route" beat is driven by his API call and my UI still shows the re-routed badge on the plan.

## 9. Integration points (aligned to teammates' committed times)

| Direction | Contract | Producer → consumer | Status |
|---|---|---|---|
| Consume | Manifest incl. `issued_at[]`, `default_at`, `events[]`, `artefacts`, `thresholds` | Shivansh (fixture Fri 16:30, real 18:45) | **Adopted in v1.1** (§11.3) |
| Consume | `gauges.json` (`level_m` nullable; skip nulls in the sparkline) | Shivansh | Adopted in v1.1 |
| Consume | `[ForecastNode]` + `forecasts/<issued_at>.json` | Vaibhav (fixture Fri 19:00, v0 Fri 23:00, champion Sat 21:00) | §5.2 |
| Consume | FloodSurface GeoJSON with `depth_class` + `depth/index.json` | Vaibhav | **Adopted in v1.1** (replaces my `depth_band` ask) |
| Consume | `colony_thresholds.json` (`wet_at_level_m`) | Vaibhav (Sat 09:30) | Adopted in v1.1 (§11.2) |
| Consume | `roads/<t>.json` + `static/osm/roads.geojson` joined on `edge_id` `osm:<min>:<max>:<key>` | Saksham / Shivansh | **Adopted in v1.1**; CI join test is theirs |
| Consume | `plans/<t>.json` (`avoid[].edge_ids[]`), `plans/<t>.unreachable.json`, `DispatchCard` (slot-filled, validated) | Saksham (fixtures Fri 23:00, S3 Sat 13:15, live writes Sat 16:00, audio + reports Sat 18:00) | Adopted in v1.1 |
| Consume | `static/colonies.geojson` (no contacts), `static/shelters.geojson` (`free_beds`) | Shivansh (Sat 11:00) | Adopted in v1.1 (`GET /colonies` exists but the ladder reads static) |
| Produce | `FieldReport` via `POST /reports` | Arjav UI → Saksham handler | Adopted in v1.1 |
| Produce | `shared/fixtures/field_report.json`; `delhi.pmtiles` extract (Shivansh uploads); Playwright §9.5 | Arjav | Fri 23:00 / Sat 11:00 / Sat 21:00 |

Every earlier "proposed PR" (manifest keys, `GET /colonies`, `{report, upload}`, `depth_band`, `edge_id` on roads.geojson, extra CloudFront behaviours, S3 GET CORS, monorepo build spec) is **adopted in v1.1**, so I open no contract PR beyond the fixture.

## 10. Testing strategy
- **Unit (vitest):** `tsub.ts` (band ⊇ centre, monotone, "may not flood", missing-thresholds fallback); `static.ts` (issued_at lookup, index lookup, non-green filter, `+` encoding, unreachable 404 → `[]`); snap to `valid_at`; manifest events = client events on the fixture; status → style; IST formatting (no UTC leaks); ladder (static 500 → cache → fixture); "no failed-validation text without the fallback banner".
- **Contract (vitest + ajv):** every file in `shared/fixtures/` and `mocks/` validates against `shared/schemas/`; `?debug=1` runs the same check on live payloads.
- **Bundle:** `check-size.mjs` fails the build if the Colony route's chunks exceed 100 KB gz or pull in maplibre.
- **E2E (Playwright, §9.5):** `/command` → scrub to T+6 h → ≥1 red road (via a `data-testid` feature counter, not pixels) → draft → card visible → approve → `sent`. Second spec: `/colony/DEL-YP-04`, save, `context.setOffline(true)`, reload. Runs on fixtures (Must) and on the deployed URL (Should).
- **Manual:** Slow 3G + 4× CPU on `?lite=1`; a low-end Android on venue Wi-Fi; airplane mode on an iPhone.

## 11. Demo screen flow (3:00, Director mode)
| t | Screen | Beat |
|---|---|---|
| 0:00–0:20 | Compare, 12 Jul 18:00 | "Delhi gets this (gauge value from the replay). A colony needs this." |
| 0:20–0:55 | Command, 2.5D, play | Water spreads over the terrain; Ring Road amber → red; pins count down |
| 0:55–1:35 | Command → YP-04 plan | Ranked list, primary/backup, "avoid Ring Road (cut off 02:00)", forecast band, one "boat / NDRF needed" colony |
| 1:35–2:10 | Draft → chips → approve | Hindi card, Kajal audio, SNS email in the team inbox |
| 2:10–2:40 | Phone: Colony, airplane mode | One route, shelter, 1077 (the pack, not the map) |
| 2:40–3:00 | Architecture still (Shivansh's `docs/`) | AWS services, degrade paths, sources |

## 12. Deployment, IAM and cost
- **Amplify Hosting** `jt-demo-web` (Shivansh's stack), **manual zip deploy**: I run `npm ci && npm run build` with `.env.demo`, then `infra/scripts/deploy_frontend.sh`. No build spec is needed; if the app becomes Git-connected, a root `amplify.yml` with `appRoot: frontend` + `AMPLIFY_MONOREPO_APP_ROOT=frontend` (SR §11.6). Ask to Shivansh (template `CustomRules` / custom headers): SPA rewrite `/<*>` → `/index.html` (200) excluding asset extensions incl. `.webmanifest`, `.mp3`, `.png`; `sw.js` and `index.html` `no-cache`; `/assets/*` immutable. Tags `project=jaltaranga, owner=arjav, env=demo`.
- **One CDN per origin:** the app uses the Amplify domain (which already includes CloudFront); the separate data CloudFront serves only `tiles/ scenarios/ static/ models/inundation/` — no stacked distributions.
- **No AWS credentials in the browser.** Public CloudFront reads; writes via the HTTP API; uploads by presigned POST (≤5 min, ≤1 MB, `image/jpeg`, prefix `uploads/reports/`).
- **CORS (all adopted in v1.1 / Shivansh's infra):** API allows the Amplify domain + `http://localhost:5173`; data CloudFront allows `GET, HEAD` with `Range`, exposes `ETag`; **S3 bucket CORS allows GET from the Amplify origin** (presigned audio) and `POST` (upload).
- **Cost:** shell ~1 MB gz + terrain ~2 MB, basemap 10–30 MB, ~50 KB JSON per step → effectively $0, no always-on resources.

## 13. Risks and degrade paths
| Risk | Likelihood | Degrade path |
|---|---|---|
| Backends late / contract drift | High | Static-first ladder, fixtures fallback, DebugPanel ajv errors; Sat 14:00 go/no-go; integration hard stop 17:30 |
| Amplify app or deploy script not ready at 12:30 | Med | `dist/` → S3 `web/` behind the data CloudFront with hash routing; URL still on AWS |
| S3 keys with `+05:30` 404 or decode as space | Med | `encodeURIComponent` per segment + contract test on one real key |
| PMTiles not uploaded / Range broken | Med | Rung 3: roads.geojson + river polygon; never cached by SW |
| Terrain looks flat | Med | Exaggeration 6–10×, hillshade, pitch 60; else 2D + hillshade + depth classes |
| Low-end device / no WebGL2 | Med | maplibre 5 (WebGL1), 2D, Colony Lite with SVG route |
| Bedrock/Polly unavailable | Med | Pre-draft from `dispatch_cache` → client template; `speechSynthesis`; banner shows `fallback_used` |
| Stale SW during recording | Med | `autoUpdate`, `no-cache` on `sw.js`; record from `demo-v1` in a fresh profile |
| Replay mistaken for a live alert / unverified numbers | Low | Permanent REPLAY badge; numbers only from payloads; NGT number only if quoted |
| Running out of time | High | Must first; cut order at 20:00 (§6); 3.25 h slack; recording slot protected |

## 14. What I need from teammates (times = their own commitments)
| From | What | By |
|---|---|---|
| Shivansh | Manifest/gauges/colony/shelter fixtures (PR #1, real curve PR #2) | Fri 16:30 / 18:45 |
| Shivansh | `static/osm/roads.geojson` (`edge_id`, `name`, `name:hi`), `river.geojson`, `colonies.geojson` (no contacts), `shelters.geojson` | Fri 22:15 (prelim) / Sat 11:00 |
| Shivansh | Stack URLs (API, data CloudFront, Amplify), `deploy_frontend.sh`, CORS, SPA `CustomRules` + headers; upload my `delhi.pmtiles` | Sat 12:30 |
| Vaibhav | Fixtures (`forecast_nodes`, `depth_index`, `depth_sample.geojson` with `depth_class`) / `colony_thresholds.json` / champion replay in demo bucket | Fri 19:00 / Sat 09:30 / Sat 21:00 |
| Saksham | Fixtures (roads, 5×3 plans, dispatch + fallback card, `report_post_response`) | Fri 23:00 |
| Saksham | Plans/roads in S3; live draft/approve/`GET /dispatches` + CORS; `audio_url_hi`, `POST /reports` presign; pre-drafted demo dispatches | Sat 13:15 / 16:00 / 18:00 / Sun 12:00 |
| One teammate | 10-min Hindi review of `hi.json` and the Colony screen | Sat 15:20 |
| All | Deadline time confirmed in the channel | Fri 24:00 |

## 15. What teammates can rely on from me
| What | When |
|---|---|
| `VITE_*` names + build dir to Shivansh; manifest-key feedback | Fri 20:00 |
| `src/shared/types.ts`; map driven by shared fixtures; PR `shared/fixtures/field_report.json` | Fri 23:00 |
| `delhi.pmtiles` extract handed to Shivansh | Sat 11:00 |
| **Public Amplify URL**; `?debug=1` shows raw JSON + ajv errors per layer for anyone's payload | Sat 13:15 |
| Recording data-source decision posted (static real vs fixtures) | Sat 14:00 |
| Command + Colony on real static data + live writes, gap list per owner | Sat 17:30 |
| Offline pack, Compare, Playwright smoke green on fixtures (feature freeze) | Sat 20:00 / 21:00 |
| Golden-test fixes; frozen `demo-v1` with baked data | Sun 10:00 / 11:30 |
| Recorded screen segments + screenshots for blog/README | Sun 14:30 |

---

## Revision log (v1.1, Fri 9 Oct, after QUALITY_REVIEW + SR §11)

| Item | Resolution |
|---|---|
| **Deal-breaker 1 / T1** Amplify monorepo build spec | Removed `frontend/amplify.yml`. Aligned with Shivansh's manual zip deploy (`deploy_frontend.sh`), so no build spec is needed; root `amplify.yml` + `AMPLIFY_MONOREPO_APP_ROOT` only if Git-connected (SR §11.6). SPA rewrites/headers requested as template `CustomRules`. S3 `web/` fallback with hash routing |
| **Deal-breaker 2 / P2** No dependency-slip trigger | All five SR §11.7 checkpoints are in §6 with explicit cut lines; Sat 14:00 decides the recording data source; integration stops at 17:30 regardless |
| **S1** 2-mode DataClient | Done: GETs static → fixtures (SR §11.4 ladder); API only for writes. `api` GET mode is Won't |
| **S2** Merge Lite into Colony | Done: `LiteView` removed; Colony `?lite=1` |
| **S3** Playwright on deployed URL | Moved to Should (Sun 09:00) |
| **S4** Saturday buffer / a11y to Sunday | Done: ▶ Listen stays Sat; contrast mode is Could on Sun (CSS only); 3.25 h slack in total |
| **T2** PMTiles 206 caching | No SW route for `*.pmtiles`; offline = colony pack, stated in §0, §8.1 and the demo flow. Terrain bundled in the app (200s, cacheable) |
| **T3** Band inconsistent with hydraulics | Rewritten: `L*` = Vaibhav's `wet_at_level_m` (SR §11.1 datum owner), fallback `level_m` at `t_submersion`; band contains centre by construction, no clamping, no `ground_elev_m` arithmetic |
| **T4** Bundle size | Lazy MapView + dynamic maplibre import; `check-size.mjs` gate ≤100 KB gz for Colony |
| **T5** Static-mode rules | Table in §3, unit-tested; `issued_at[]` adopted in the v1.1 manifest; `+` encoding rule added |
| **T6** S3 GET CORS for audio; desktop speechSynthesis | Adopted in SR §11.6; desktop device voice documented as online-only |
| **T7** Ring Road by name | Highlight via `avoid[].edge_ids[]` (SR §11.3), falling back to `name` match |
| **P1** Contract PR | Superseded: every ask is adopted in SR v1.1 (§9 table); only the fixture PR remains |
| **P3** NGT 207.1 m caption | Used only if quoted by Sat 22:00, otherwise "gauge-level forecast" |
| **P4** Deadline | Assumed 18:00 IST (as Shivansh's plan); confirmed Fri 24:00; submit at deadline − 2 h per SR §11.7 |
| SR §11 conformance | `depth_band` → `depth_class` strings; `edge_id` treated as opaque `osm:<min>:<max>:<key>`; manifest events used instead of only client-side; `unreachable.json` shown as "boat / NDRF needed"; `free_beds`; slot-filled dispatch + pre-draft rung; colonies from static (no contacts); Compare and Offline pack moved before the **Sat 20:00 freeze** (previously Sunday) |
| Teammate alignment | Times in §6/§14 match Shivansh (16:30/18:45/12:30), Vaibhav (19:00/09:30/21:00) and Saksham (23:00/13:15/16:00/18:00) plans; added their asks (VITE names, PMTiles hand-off, re-routed badge, unreachable list, fan chart); what-if/model-card pages are Won't because they land after the freeze |
| Rejected | None of the review's items rejected. Director mode stays (Should) but is classed as recording tooling, not counted as a product feature |
