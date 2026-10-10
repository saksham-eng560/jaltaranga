# Jaltaranga Data & Hydrology Pipeline

This module handles the geospatial, data extraction, calibration, infrastructure exposure, and scenario playback components for **Jaltaranga** (Yamuna Floodplain Evacuation Decision Support System, Delhi).

## Modules & Scope (Shivansh's Track)

1. **Step 1: Embankment-Aware DTM (`pipeline.dtm`)**
   - High-resolution (30m) GLO-30 Copernicus DEM ingestion and clipping for the Delhi Yamuna floodplain stretch (Wazirabad to Okhla Barrage).
   - Bund/embankment crest elevation enforcement with bridge crossings treated as hydrological edge passages.
   - Vertical calibration using shared benchmark ground truth points with test holdouts.
   - Exclusion masking documentation and golden sanity checks (e.g. Yamuna Pushta inundated vs. Connaught Place dry at 208.66m gauge level).

2. **Step 2: Provenance and QC Ledger (`pipeline.ledger`)**
   - Traceability ledger (`ledger.jsonl` / parquet) capturing `value_id`, `dataset`, `source_url`/`source_name`, `retrieved_at`, `licence`, `qc_flag`, and `qc_notes`.
   - Recording helper (`record(...)`), automated output validation, and inspection CLI.

3. **Step 3: Critical-Infrastructure Exposure (`pipeline.exposure`)**
   - Extraction and local caching of hospitals, metro stations, electrical substations, water treatment plants (WTPs), and underpasses from OpenStreetMap (OSM).
   - Inundation threshold computation matching water surface profile & DTM/onset rasters.
   - Generation of `infra_exposure.json` logged in the QC ledger.

4. **Step 4: Rainfall Context & Replay CLI (`pipeline.rainfall`, `pipeline.replay`)**
   - ERA5 hourly rainfall ingestion for scenario windows (labelled "ERA5 reanalysis - not IMD").
   - Scenario playback assembler for historical and hypothetical floods (`yamuna-2023-07`, `yamuna-2025-09`).
   - Integration with `make replay-local SCENARIO=...`.

## Conventions
- **Python Version**: 3.11+
- **Offline First**: All pipeline runs can be executed locally with synthetic/cached fixtures.
- **Traceability**: Zero silent synthetic data; all outputs registered with explicit QC flags (`ok`, `suspect`, `synthetic`, `digitized`).
