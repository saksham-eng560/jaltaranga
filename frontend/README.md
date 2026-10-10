# Jaltaranga frontend

React, TypeScript and Vite application for the Jaltaranga Yamuna flood replay. The UI reads the shared schemas and fixtures from the repository root and consumes scenario artifacts from CloudFront when configured.

## Run locally

```powershell
cd frontend
npm ci
Copy-Item .env.example .env.local
npm run dev
```

The local fixture adapter is prepared automatically from `shared/fixtures/` and `ml/data/fallback/drb_anchors.csv`. Its generated files in `public/fixtures/` are ignored and must not be committed. The shared routing README identifies the routing/shelter development outputs as synthetic; the UI labels them accordingly and blocks fixture-backed approval/sending.

Configure `.env.local` only when the corresponding service or artifacts exist:

| Variable | Purpose |
|---|---|
| `VITE_STATIC_BASE` | CloudFront origin for `scenarios/`, `static/`, and `models/` JSON |
| `VITE_API_BASE` | API Gateway base URL for dispatch, approval, report, and shelter APIs |
| `VITE_BASEMAP_STYLE_URL` | Optional MapLibre style URL supplied by the deployment |
| `VITE_TILES_BASE` | Optional CloudFront origin serving `tiles/basemap/delhi.pmtiles` |
| `VITE_TERRAIN_BASE` | Optional Terrarium tile URL prefix for `z/x/y.png` |
| `VITE_SCENARIO_ID` | Scenario ID; defaults to `yamuna-2023-07` |
| `VITE_HERO_COLONY` | Default colony ID; defaults to `DEL-YP-04` |

No AWS credentials belong in frontend environment variables. Variables prefixed `VITE_` are public and embedded in the browser build.

## Verification

```powershell
npm run typecheck
npm test
npm run build
npx playwright install chromium
npm run e2e
```

The build checks the Colony route's static JavaScript graph against 100 KB gzip and rejects MapLibre/PMTiles in that graph. Playwright builds and serves the production PWA, including a cold offline reload check.

## Data and safety behavior

- A replay step reads one complete source group: CloudFront artifacts, or the bundled shared-fixture adapter. It does not combine data across replay steps or fall through per layer.
- The local manifest is an adapter over the shared fixture timestamps. It does not invent additional replay observations. Missing flood polygons, plan rows, road geometry, and forecasts stay unavailable.
- Gauge rows retain the tracked `source_ref`; route, road-status, and shelter fixture outputs remain labeled synthetic.
- Countdown center/earliest/latest timestamps are rendered from the shared plan fields. No gauge-minus-ground-elevation estimate is calculated.
- Fixture-backed dispatch cards can be previewed but never approved or sent. A live approval status is shown only after the API confirms it.
- Offline storage uses IndexedDB for the selected plan, route, shelter, validated dispatch, timestamp, and audio blob when one can be retrieved. Offline mode is the saved SVG route and content, not an offline basemap. Packs older than two hours are marked stale.
- Reports use explicit location permission or manually entered coordinates. Photos are resized to at most 1280 px, re-encoded to JPEG, and capped at 1 MB before the existing presigned upload flow. A report is never marked uploaded before server confirmation.

## Map compatibility

The original workstream plan pinned MapLibre GL JS 5.24.0 for WebGL 1 support. `npm audit` reported that version affected by a critical MapLibre GL JS security advisory. The frontend uses patched MapLibre 6.13.0; its map is loaded only when a basemap is configured. Devices without the required WebGL2 support use the route SVG/Lite experience. No third-party basemap or tile service is hard-coded.

The API URL, CloudFront artifacts, real roads/colonies GeoJSON, flood polygons at the selected demo step, and deployment credentials are environment/infrastructure inputs. Until those are provided, the app clearly distinguishes unavailable layers and uses only the labeled repository fixture pack.
