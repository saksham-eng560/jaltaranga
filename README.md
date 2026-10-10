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
npm install
npm run dev
```

Open the local URL printed by Vite (by default, `http://localhost:5173`). Map tiles are provided by OpenStreetMap and require an internet connection; the replay controls, sample colony data, and dispatch demo work locally.
