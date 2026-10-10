# Jaltaranga Model Card: Hydrological Stage Forecasting & Inundation v1.0

## Model Summary
- **Champion Model:** `lagreg-v1` (Ridge Regression over real causal lags)
- **Fallback Baseline:** `persistence`
- **Datum Offset (δ):** 0.0 m
- **Water Surface Slope (S):** 0.22 m/km
- **Inundation Balanced Accuracy:** 0.88

## Performance Metrics (Held-out TEST Event: July 9–18, 2023)
| Horizon (h) | MAE (m) | RMSE (m) | NSE | Skill vs Persistence | Samples |
|---|---|---|---|---|---|
| 1h | 0.411 | 0.733 | 0.55 | 0.081 | 16 |
| 3h | 0.434 | 0.717 | 0.604 | 0.174 | 16 |
| 6h | 0.449 | 0.715 | 0.613 | 0.211 | 16 |
| 12h | 0.406 | 0.608 | 0.724 | 0.553 | 16 |
| 24h | 0.525 | 0.657 | 0.689 | 0.711 | 16 |

## Honest Operational Caveats
1. **Causal Inputs Only:** Forecasts use only gauge readings published prior to each issue time.
2. **DEM Bias:** Copernicus GLO-30 DSM elevations are biased high in built-up areas.
3. **ITO Regulator Backflow:** July 2023 flooding at Supreme Court/ITO occurred via Drain No. 12 backflow, not direct overbank spill.
4. **Intended Use:** Decision-support and emergency evacuation guidance only, not a legal guarantee.
