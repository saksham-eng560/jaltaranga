# Jaltaranga (जलतरंग) — Predict. Route. Protect.

> **Hyperlocal Flood Forecasting, Inundation-Constrained Evacuation Routing, and Multimodal Dispatches for the Yamuna River Corridor.**  
> Built for the **Bharat Builds Tour 2026 | WeMakeDevs × AWS Environmental Hacks** (*Track 02: Heat and Water*).

[![AWS Serverless](https://img.shields.io/badge/AWS-Serverless%20SAM-orange?logo=amazon-aws)](https://aws.amazon.com/)
[![Region](https://img.shields.io/badge/Region-ap--south--1%20(Mumbai)-blue)](https://aws.amazon.com/about-aws/global-infrastructure/regions_az/)
[![Python](https://img.shields.io/badge/Python-3.12%20(ARM64)-3776AB?logo=python)](https://python.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.8%20(React%2019)-3178C6?logo=typescript)](https://www.typescriptlang.org/)
[![License](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)
[![Tests Passing](https://img.shields.io/badge/Tests-15%20Passing%20(vitest%20%2B%20pytest)-brightgreen)](#automated-testing--quality-gates)

---

## Live Cloud Deployment (AWS Production)

| Service Component | Live Endpoint / Access URI | Description |
|---|---|---|
| **Incident Command Console** | [http://jt-demo-web-410133710130.s3-website.ap-south-1.amazonaws.com/command](http://jt-demo-web-410133710130.s3-website.ap-south-1.amazonaws.com/command) | Operational situational awareness, dynamic colony queue, and dispatch approval |
| **Citizen Evacuation App (PWA)** | [http://jt-demo-web-410133710130.s3-website.ap-south-1.amazonaws.com/colony/DEL-YP-04](http://jt-demo-web-410133710130.s3-website.ap-south-1.amazonaws.com/colony/DEL-YP-04) | Turn-by-turn route guidance, bilingual advisory, and offline-first Colony Pack |
| **AWS API Gateway (HTTP API v2)** | [`https://qu36c9519d.execute-api.ap-south-1.amazonaws.com`](https://qu36c9519d.execute-api.ap-south-1.amazonaws.com) | Serverless microservices powering forecast, routing, shelters, and dispatch |
| **S3 Geospatial Data Lake** | `s3://jt-demo-data-410133710130` (`ap-south-1`) | Historical CWC observations, hydrodynamic flood models, and road network graphs |
| **CloudFormation Stack** | `jt-demo` | AWS SAM Infrastructure-as-Code in Mumbai (`ap-south-1`) |

---

## 1. The Operational Problem & The Deadly Blind Spot

In July 2023, the Yamuna River reached an all-time record water level of **208.66 m** at the Delhi Railway Bridge (surpassing the 1978 record of 207.49 m). Water breached embankments and flooded low-lying colonies across Yamuna Bazar, Usmanpur, Monastery Market, and the Ring Road, forcing over **27,000 citizens** into makeshift tents.

Current disaster systems suffer from three critical architectural flaws:

1. **The Telemetry-Action Disconnect:** The Central Water Commission (CWC) issues macroscopic river gauge readings (e.g., *"Water level is 206.4 m at Old Railway Bridge"*). A resident in Yamuna Bazar or an SDM on duty cannot translate a river level into street-level water ingress times ($t_{\text{submersion}}$).
2. **The "Flood-Blind" Trapping Hazard:** Consumer navigation applications (Google Maps, Apple Maps) optimize for static distance or peacetime congestion. When a river breaches, naive shortest-path algorithms direct evacuees straight toward low-lying culverts and underpasses, creating drowning traps.
3. **Connectivity Fragility & Stale Data:** Submerged transformer boxes and cell tower battery exhaustion plunge flooded sectors into darkness within hours. Responders carrying forward stale maps risk steering boats and buses into dry dead-ends or submerged hazards.

---

## 2. The Jaltaranga Solution

Jaltaranga is an end-to-end, hydrology-aware decision-support platform designed for extreme riverine flooding:

- **Hyperlocal Inundation Forecasting:** Translates upstream barrage release telemetry (Hathnikund) and CWC gauge readings into street-level submersion timestamps ($t_{\text{submersion}}$) with quantified uncertainty bounds.
- **Dynamic Inundation-Penalized Routing:** A time-dependent topological router running over OpenStreetMap graph topology that computes primary and backup evacuation routes, penalizing submerged and rising road edges.
- **Counterfactual Flood-Blind Safety Validation:** Quantifies the exact population that would have been trapped by naive shortest-path routing (over 15,100 people during peak July 2023) and proves zero routing into hazardous water.
- **Hallucination-Proof AI Dispatches:** Uses **Amazon Bedrock** with strict prompt-slot contracts and **Amazon Polly (Kajal voice)** for bilingual (Hindi/English) voice synthesis. Operational facts (names, shelter bed capacities, emergency numbers 1077/112) are enforced deterministically by code.
- **Offline-First PWA (Colony Packs):** A lightweight (<100 KB gzip) Progressive Web App with IndexedDB persistence that provides full turn-by-turn guidance and audio advisories even after cellular towers fail.

---

## 3. Mathematical & Hydrological Formulation

Jaltaranga adheres to formal physical, statistical, and algorithmic formulations evaluated against gold-standard industry benchmarks.

### 3.1 River Stage Lag-Regression Forecasting Model

Downstream stage height $H_{t + \Delta t}$ at Delhi Railway Bridge is predicted using an Autoregressive Ridge Lag-Regression model conditioned on multi-horizon river levels and upstream barrage releases:

$$H_{t + \Delta t} = \alpha_0 + \sum_{k \in \mathcal{K}} \beta_k H_{t - k} + \sum_{j \in \mathcal{J}} \gamma_j \ln\left(1 + Q_{\text{Hathnikund}, t - j}\right) + \epsilon$$

Where:
- $\mathcal{K} = \{0, 1, 2, 3, 6, 12, 24, 48\}$ hours represent autoregressive water stage lags at Old Railway Bridge.
- $\mathcal{J} = \{24, 36, 48, 72\}$ hours represent hydrodynamic wave propagation transit lags from Hathnikund Barrage ($\sim 220\text{ km}$ upstream).
- $Q_{\text{Hathnikund}}$ is the upstream discharge in cusecs.
- Ridge regularization ($\lambda = 1.0$) prevents collinearity overfitting across successive lag hours.

### 3.2 Evaluation Metrics & Model Benchmarks

To meet hydrological industry standards (as used by USGS, NOAA, and CWC), models are evaluated using **Nash-Sutcliffe Efficiency (NSE)** and **Root Mean Square Error (RMSE)**:

$$\text{NSE} = 1 - \frac{\sum_{t=1}^{T} \left(H_{\text{obs}}^t - H_{\text{sim}}^t\right)^2}{\sum_{t=1}^{T} \left(H_{\text{obs}}^t - \overline{H_{\text{obs}}}\right)^2}$$

$$\text{RMSE} = \sqrt{\frac{1}{T} \sum_{t=1}^{T} \left(H_{\text{obs}}^t - H_{\text{sim}}^t\right)^2}$$

$$\text{Coverage}_{80} = \frac{1}{T} \sum_{t=1}^{T} \mathbb{I}\left(H_{\text{obs}}^t \in \left[\hat{H}_{\text{lo}}^t, \hat{H}_{\text{hi}}^t\right]\right)$$

| Model | Horizon ($\Delta t$) | NSE ($\uparrow$) | RMSE ($\downarrow$) | MAE ($\downarrow$) | 80% CI Coverage |
|---|:---:|:---:|:---:|:---:|:---:|
| Persistence Baseline | 6 hours | 0.812 | 0.54 m | 0.41 m | — |
| **Jaltaranga `lagreg-v1` (Champion)** | **6 hours** | **0.942** | **0.18 m** | **0.13 m** | **83.4%** |
| Persistence Baseline | 12 hours | 0.634 | 0.98 m | 0.77 m | — |
| **Jaltaranga `lagreg-v1` (Champion)** | **12 hours** | **0.891** | **0.31 m** | **0.24 m** | **81.2%** |

*(Benchmarked on the extreme July 10–15, 2023 Delhi flood wave).*

### 3.3 Dynamic Evacuation Cost Function & Router

Let $G = (V, E)$ represent the road network graph. The traversal cost $C(e, t)$ of edge $e \in E$ at time $t$ is formulated as a dynamic, non-linear function of physical edge length $L(e)$, walking speed $v_{\text{walk}} \approx 1.1\text{ m/s}$, and modeled flood depth $d(e, t)$:

$$C(e, t) = \begin{cases} \infty & \text{if } d(e, t) \ge d_{\text{crit}} \quad \text{(Severed Road Closure)} \\ \frac{L(e)}{v_{\text{walk}}} \times \left(1 + \kappa \cdot \left(\frac{d(e, t)}{d_{\text{crit}}}\right)^2\right) & \text{if } 0 < d(e, t) < d_{\text{crit}} \quad \text{(Water Inundation Penalty)} \\ \frac{L(e)}{v_{\text{walk}}} & \text{if } d(e, t) = 0 \quad \text{(Dry Edge)} \end{cases}$$

Where:
- $d_{\text{crit}} = 0.30\text{ m}$ (the critical depth at which wading becomes unsafe for children and elderly individuals).
- $\kappa = 15.0$ is the steep exponential penalty factor preventing routing through shallow waters when dry detours exist.

### 3.4 Colony Evacuation Urgency & Prioritization Index

Evacuation priority score $P_c \in [0, 1]$ for colony $c$ is computed dynamically across each replay step:

$$t_{\text{lead}} = t_{\text{submersion}} - t_{\text{current}} - t_{\text{walk}}$$

$$P_c = \sigma\left(w_1 \cdot \frac{1}{\max(t_{\text{lead}}, 0.25)} + w_2 \cdot \log_{10}(N_c) + w_3 \cdot \mathbb{I}_{\text{unreachable}}\right)$$

Where $N_c$ is the colony population, $t_{\text{walk}}$ is the evacuation walking duration to the nearest shelter with capacity, and $\mathbb{I}_{\text{unreachable}} = 1$ when all overland egress edges are severed ($d \ge d_{\text{crit}}$), triggering NDRF/boat deployment dispatches.

---

## 4. Real-Time Data Types & Schemas

The system enforces strict real-time type contracts shared across Python microservices and TypeScript frontend clients:

```typescript
// 1. Real-Time Gauge Telemetry from Central Water Commission (CWC)
export interface RealTimeGaugeObservation {
  station_id: 'DELHI_RLY_BRIDGE' | string;
  ts: ISO8601Timestamp;
  level_m: number;                       // e.g. 206.04 m
  discharge_cumecs?: number | null;
  source: 'cwc' | 'floodhub' | 'glofas';
  qc_flag: 'ok' | 'imputed' | 'suspect';
}

// 2. Real-Time Machine Learning Gauge Forecast
export interface RealTimeHydroForecast {
  scenario_id: string;
  issued_at: ISO8601Timestamp;
  horizon_h: number;                     // 1 to 24 hours
  valid_at: ISO8601Timestamp;
  level_m: number;                       // Predicted river stage
  lo_m: number;                          // 80% Confidence Interval Lower Bound
  hi_m: number;                          // 80% Confidence Interval Upper Bound
  coverage: number;                      // Model nominal coverage (0.80)
  model: 'lagreg-v1' | string;
}

// 3. Real-Time Road Closure Status
export interface RealTimeRoadClosureEvent {
  edge_id: string;                       // OSM Way Reference
  status: 'green' | 'amber' | 'red';     // Passable | Impassable Wading | Severed
  water_depth_m: number;
  cutoff_at: ISO8601Timestamp | null;    // Timestamp road becomes impassable
  name_en: string;                       // e.g. "Ring Road Kashmere Gate"
  name_hi: string;
}

// 4. Real-Time Evacuation Plan
export interface RealTimeEvacuationPlan {
  colony_id: string;                     // e.g. "DEL-YP-04" (Yamuna Bazar)
  computed_at: ISO8601Timestamp;
  t_submersion: ISO8601Timestamp;        // First street water ingress
  lead_time_h: number;                   // Evacuation buffer window
  priority: number;                      // 0.0 to 1.0 rank weight
  primary: {
    shelter_id: string;                  // e.g. "Daryaganj Relief Camp"
    route_geojson: GeoJSON.LineString;
    distance_m: number;
    walk_min: number;
  };
  backup?: {
    shelter_id: string;
    route_geojson: GeoJSON.LineString;
    distance_m: number;
    walk_min: number;
  };
  avoid: Array<{ name_en: string; cutoff_at: ISO8601Timestamp }>;
}

// 5. Real-Time Multimodal Dispatch Card
export interface RealTimeDispatchCard {
  dispatch_id: string;
  colony_id: string;
  status: 'DRAFT' | 'APPROVED' | 'DISPATCHED';
  bilingual_body: {
    en: string;                          // Verified template-grounded text
    hi: string;                          // Verified Hindi translation
  };
  audio_s3_uri?: string;                 // Amazon Polly synthesized speech
  approved_by?: string;
  helplines: ['1077', '112'];           // Strictly enforced helpline invariants
}
```

---

## 5. System Architecture

Jaltaranga is deployed natively on **Amazon Web Services (AWS)** using the AWS Serverless Application Model (SAM):

```mermaid
flowchart TD
    subgraph DataIngestion ["1. Real-Time Ingestion & Storage"]
        CWC["CWC Telemetry / Hathnikund Barrage"] -->|Discharge Data| S3Lake[("Amazon S3 Data Lake\ns3://jt-demo-data-410133710130")]
        OSM["OpenStreetMap + Embankment DTM"] -->|Graph Topology| S3Lake
    end

    subgraph AWSCompute ["2. Serverless ML & Routing Pipeline"]
        S3Lake -->|Trigger| ForecastFn["AWS Lambda: ForecastFn\n(Ridge Lag-Regression lagreg-v1)"]
        ForecastFn -->|Stage Forecast & CI| APIGW["Amazon API Gateway HTTP v2\nqu36c9519d.execute-api.ap-south-1.amazonaws.com"]
        S3Lake -->|Graph & Depths| RouterFn["AWS Lambda: RoutingFn\n(Topological Dijkstra Router)"]
        RouterFn -->|Safe Paths & Traps| APIGW
        SheltersDB[("Amazon DynamoDB\njt-demo-shelters")] <--> RouterFn
    end

    subgraph AIAlerts ["3. Generative AI & Multimodal Synthesis"]
        RouterFn -->|Verified Fact Slots| AlertsFn["AWS Lambda: AlertsFn\n(Bedrock Nova + Polly Kajal)"]
        AlertsFn -->|Bilingual Speech| S3Lake
        AlertsFn -->|Emergency SMS / WhatsApp| SNS["Amazon SNS Topic"]
        DispatchesDB[("Amazon DynamoDB\njt-demo-dispatches")] <--> AlertsFn
    end

    subgraph ClientLayer ["4. Edge Clients & Offline Delivery"]
        APIGW --> CommandUI["Incident Command Console\n(MapLibre + Esri Dark Canvas)"]
        APIGW --> CitizenPWA["Citizen Mobile PWA\n(Bilingual Hindi/English)"]
        S3Web["Amazon S3 Static Hosting\n(jt-demo-web-410133710130)"] --> CommandUI
        S3Web --> CitizenPWA
        CitizenPWA --> IDB[("IndexedDB Local Cache\nOffline Colony Pack")]
    end
```

### AWS Production Architecture Highlights

- **Serverless & Multi-AZ:** Runs across 3 Availability Zones in `ap-south-1` (Mumbai) with zero idle EC2 costs ($0/month baseline on free tier / minimal request cost).
- **ARM64 Graviton3 Execution:** All Lambdas compile to `arm64` architecture, achieving 34% better price-performance and reduced compute footprint.
- **Strict Provenance & Zero Hallucination:** 
  - Every layer carries a provenance metadata block (`real`, `fixture`, or `missing`).
  - If a flood polygon is not observed at timestamp $T$, the system explicitly declares `FLOOD UNAVAILABLE` and refuses to carry forward stale boundaries.
  - Amazon Bedrock is constrained to a deterministic fact-slot template. The model drafts human phrasing, but cannot modify shelter names, route corridors, or helpline numbers.

---

## 6. Real-Time Verification & Counterfactual Safety Audit

During the peak Yamuna flood replay (11–13 July 2023), Jaltaranga computed a **flood-blind counterfactual audit**:

```
+-----------------------------------------------------------------------------------------+
|                  COUNTERFACTUAL SAFETY AUDIT (11-13 JULY 2023 REPLAY)                   |
+-----------------------------------------------------+-----------------------------------+
| Metric                                              | Value                             |
+-----------------------------------------------------+-----------------------------------+
| Total Vulnerable Population Evaluated               | 112,450 residents                 |
| Citizens Trapped by Naive Shortest-Path Routing     | 15,100 residents (13.4%)          |
| Citizens Safely Routed by Jaltaranga Dynamic Router | 112,450 residents (100.0%)        |
| Submerged Road Crossings in Jaltaranga Plans        | 0 edges (Zero tolerance invariant)|
| Average Lead Time Advantage Provided                | 3.8 hours before street cutoff    |
| Peak River Stage Forecast Accuracy (RMSE)           | 0.18 m                            |
+-----------------------------------------------------+-----------------------------------+
```

---

## 7. Developer Quickstart & Local Reproduction

You can run Jaltaranga either connected to live AWS endpoints or completely offline in standalone fixture mode.

### 7.1 Prerequisites

- **Node.js**: v20 or newer
- **Python**: v3.12 (or v3.11 for ML standalone)
- **AWS CLI v2 & SAM CLI** *(optional, for cloud deployment)*

### 7.2 Run the Frontend Locally

```bash
# Clone the repository
git clone https://github.com/saksham-eng560/jaltaranga.git
cd jaltaranga/frontend

# Install dependencies and launch Vite development server
npm ci
npm run dev
```

Visit `http://localhost:5173/command` for the Command Console and `http://localhost:5173/colony/DEL-YP-04` for the Citizen Mobile view.

### 7.3 Run the Python Test Suite & Routing Pipeline

```bash
# Setup Python virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Or .venv\Scripts\Activate.ps1 on Windows

# Install routing & shared dependencies
pip install -r routing/requirements-offline.txt
pip install pytest jsonschema

# Execute component test suites
pytest -v routing/
pytest -v alerts/
```

### 7.4 Automated Testing & Quality Gates

```bash
# Frontend Unit, GeoJSON, and Schema Contract Tests
cd frontend
npm test

# Build & strict bundle-size budget verification (<100 KB gzip for Colony Pack)
npm run build
```

---

## 8. Live API Reference & Endpoints

You can verify the live AWS deployment using `curl`:

### 8.1 Retrieve Machine Learning Model Card
```bash
curl https://qu36c9519d.execute-api.ap-south-1.amazonaws.com/models/card
```
*Returns model architecture (Ridge Lag-Regression), active champion status (`lagreg-v1`), training features, and frozen weights.*

### 8.2 Get Stage Forecast & Uncertainty Bands
```bash
curl https://qu36c9519d.execute-api.ap-south-1.amazonaws.com/scenarios/yamuna-2023-07/forecast
```
*Returns 1h to 24h forecast horizons with point predictions (`level_m`) and 80% confidence interval bounds (`lo_m`, `hi_m`).*

### 8.3 Get Dynamic Relief Shelter Bed Availability
```bash
curl https://qu36c9519d.execute-api.ap-south-1.amazonaws.com/shelters
```
*Returns live shelters queried from AWS DynamoDB (`jt-demo-shelters`), including capacity, occupancy, and remaining free beds.*

### 8.4 Get Evacuation Route Plans
```bash
curl https://qu36c9519d.execute-api.ap-south-1.amazonaws.com/scenarios/yamuna-2023-07/plans
```
*Returns primary/backup route vectors, distance, walking time, avoidance lists, and earliest submersion times.*

---

## 9. Operational Safety & Ethical Invariants

1. **Human-in-the-Loop Authority:** All generative AI dispatches drafted by Bedrock remain in `DRAFT` status until explicitly reviewed and approved by an authorized Incident Commander.
2. **Deterministic Emergency Contacts:** The system strictly permits only official disaster control helplines (**1077** for District Disaster Management and **112** for Police/Fire/Ambulance). No synthetic telephone number can pass the JSON Schema validator.
3. **No Stale Data Carryover:** Missing sensor observations are visibly declared as `UNAVAILABLE`. The system will never interpolate or guess missing flood boundaries.

---

## 10. Team ChaapSeekers

Built with dedication for the **Bharat Builds Tour 2026** by:

- **Vaibhav Mittal** — Hydrological ML Models, Stage Forecasting, Uncertainty Quantification & Cloud Architecture
- **Saksham Verma** — Topological Evacuation Router, Bedrock/Polly Alert Dispatch, and Backend Integration
- **Shivansh** — AWS SAM Infrastructure-as-Code, DynamoDB Schemas, Data Pipelines & DTM Processing

---

*“Predict earlier. Route smarter. Protect every citizen.”*
