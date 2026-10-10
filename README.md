# Jaltaranga — Predict. Route. Protect.

Flood evacuation intelligence for the Yamuna corridor in Delhi. Built by team **ChaapSeekers** (Arjav, Vaibhav, Shivansh, Saksham) for Bharat Builds Tour 2026 · WeMakeDevs × AWS Environmental Hacks (Track 02: Heat and Water).

| Doc | What it is |
|---|---|
| [`PROJECT_SUMMARY.md`](PROJECT_SUMMARY.md) | Enhanced overview, architecture, owners, timeline, risks, metrics |
| [`SHARED_RESOURCES.md`](SHARED_RESOURCES.md) | Contracts every workstream builds against: schemas, API, S3, AWS naming |
| [`INTEGRATION_PLAN.md`](INTEGRATION_PLAN.md) | Merge order, integration tests, deployment, demo-video script |

Workstream plans and quality reviews are grouped by owner under `docs/workstreams/<owner>/` on each feature branch. The separate folders let all four workstreams merge without overwriting one another.

## Run the frontend demo locally

The frontend includes sample July 2023 replay data and does not require a backend:

```bash
cd frontend
npm ci
npm run dev
```

Open the local URL printed by Vite (by default, `http://localhost:5173`). The dark-blue operations console, historical replay, fixture-backed routes, dispatch preview, report queue, and saved Colony Pack are available locally. Live APIs and an interactive basemap are optional; without a configured basemap, the app shows the route geometry from the selected plan.
