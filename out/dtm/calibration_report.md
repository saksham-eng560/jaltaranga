# DTM Calibration Report

**Pipeline Component**: Shivansh's Track (`pipeline.dtm`)  
**Status**: Calibrated Baseline with Fixed Zero Offset & Radar Pit Clamping  
**Date**: October 2026  

---

## 1. Height Offset Decision: $\delta = 0.0\text{ m}$

In accordance with strict data honesty principles, **no calibration points from `data/calibration_points.csv` were used to fit an empirical vertical datum offset ($\delta$)**.

- **Fitted Offset ($\delta$):** `0.0 m` (fixed baseline)
- **Calibrated By:** `fixed_zero_baseline`
- **Rationale:** The rows in `data/calibration_points.csv` are approximate radar samples and indicative floodplain heights, not certified Great Trigonometrical Survey (GTS) field benchmarks. Using unverified estimates to optimize a mathematical height offset would risk overfitting and introduce false precision.

---

## 2. Terrain Baseline & Radar Pit Clamping

The Digital Terrain Model is derived directly from the **Copernicus GLO-30 DSM** (AWS Open Data Registry):
- **Raw Tile:** `Copernicus_DSM_COG_10_N28_00_E077_00_DEM.tif`
- **Horizontal Resolution:** 30 m grid
- **Corridor Bounds:** Lat $[28.53, 28.72]$, Lon $[77.18, 77.34]$ (683 rows $\times$ 576 cols)
- **Hydraulic Carving:** 9 bridge decks (Signature Bridge, Old Railway Bridge, ISBT Setu, etc.) are carved down to riverbed level so bridge decks do not form artificial dams.
- **Radar Pit Clamping:** Radar specular reflection dropouts over open water (which originally caused artificial low cells down to 182 m between Nizamuddin and Okhla) have been clamped to the physical bed sill floor at Okhla Barrage (**197.5 m**), eliminating fake sinks and pits.
- **Embankment Burn Mask:** Separate uint8 mask generated in gauge space (`data/dem/burn_mask.npy`) with wall lines aligned west of Ring Road to prevent false sealing of low-lying riverbank colonies.

---

## 3. Measured Hit Rate on Non-Held-Out Points (Peak Level: 208.66 m)

At the July 2023 all-time record flood level ($208.66\text{ m}$ at Old Delhi Railway Bridge), there are **9 non-held-out locations** documented as wet in ground-truth flood observations:

- **Measured Hit Rate:** **5 / 9 (55.6%)** show wet on the uncalibrated DTM ($\delta = 0.0\text{ m}$).

### Places that show WET on DTM (True Positives):
1. **Yamuna Pushta Floodplain Bench (`DEL-YP-04`):** Ground = $206.77\text{ m}$, WSE = $208.54\text{ m}$ $\rightarrow$ **Wet (+1.77 m depth)**
2. **Usmanpur Khadar Riverbank:** Ground = $206.68\text{ m}$, WSE = $209.04\text{ m}$ $\rightarrow$ **Wet (+2.36 m depth)**
3. **Geeta Colony Khadar Agricultural Belt:** Ground = $205.28\text{ m}$, WSE = $208.43\text{ m}$ $\rightarrow$ **Wet (+3.15 m depth)**
4. **Nizamuddin Khadar Lowland:** Ground = $198.50\text{ m}$, WSE = $207.43\text{ m}$ $\rightarrow$ **Wet (+8.93 m depth)**
5. **Kalindi Kunj Riverbank:** Ground = $197.50\text{ m}$, WSE = $206.73\text{ m}$ $\rightarrow$ **Wet (+9.23 m depth)**

### Places that show DRY on DTM (False Negatives due to Radar DSM Surface Artifacts):
1. **Monastery Market Low-lying Khadar:** Ground on DTM = **$216.48\text{ m}$**, WSE = **$208.80\text{ m}$** (dry by $7.68\text{ m}$).  
   *Cause:* The 30 m Copernicus radar pixel includes the adjacent elevated Ring Road carriageway and ISBT flyover ramp.
2. **Majnu Ka Tila Floodplain:** Ground on DTM = **$217.57\text{ m}$**, WSE = **$209.29\text{ m}$** (dry by $8.28\text{ m}$).  
   *Cause:* Multi-story Tibetan colony buildings and dense riverbank trees elevate the satellite radar return above water level.
3. **Bela Estate Kisan Basti:** Ground on DTM = **$209.86\text{ m}$**, WSE = **$208.31\text{ m}$** (dry by $1.55\text{ m}$).  
   *Cause:* Agricultural tree canopy cover elevating radar surface.
4. **Kashmere Gate Outer Ring Road:** Ground on DTM = **$209.04\text{ m}$**, WSE = **$208.76\text{ m}$** (dry by $0.28\text{ m}$).  
   *Cause:* Elevated road embankment height on the 30 m radar grid sits slightly above the local river water surface.

---

## 4. Golden Sanity Check Validation

Terrain integrity is validated by the **Golden Sanity Check** at $208.66\text{ m}$:
1. **Low-lying Floodplain (Yamuna Pushta `DEL-YP-04`):** Inundated depth = **$1.77\text{ m}$** (expected $> 0.30\text{ m}$).
2. **Urban High Ground (Connaught Place `DEL-CP-01`):** Inundated depth = **$0.00\text{ m}$** (expected $0.00\text{ m}$, dry).

Result: **PASS**.
