"""DEM Grid representation, domain clipping and chainage calculation."""

import numpy as np
from pathlib import Path
from typing import Tuple, Optional
from scipy.spatial import cKDTree
from jt_ml.paths import get_data_dir


class CorridorGrid:
    """Represents the 1 arcsecond (~30m) Yamuna corridor DTM grid:
    bbox: [77.20, 28.53, 77.33, 28.75]
    Clipping domain: between Wazirabad (28.712 N) and Okhla (28.545 N).
    """

    def __init__(
        self,
        dtm: np.ndarray,
        lons: np.ndarray,
        lats: np.ndarray,
        river_mask: np.ndarray,
        chainage_s: np.ndarray, # km along river from Wazirabad
        s_drb: float = 8.0,      # DRB chainage km
    ):
        self.dtm = dtm
        self.lons = lons
        self.lats = lats
        self.river_mask = river_mask
        self.chainage_s = chainage_s
        self.s_drb = s_drb
        self.shape = dtm.shape

    def compute_zprime(self, delta_m: float, slope_m_per_km: float) -> np.ndarray:
        """Compute sloped gauge-referenced ground level:
        z' = DTM + delta + S * (s - s_drb)
        Downstream cells (s > s_drb) have positive term, needing higher DRB reading to flood.
        """
        # Slope in m / km: slope_m_per_km * (s - s_drb)
        zprime = self.dtm + delta_m + (slope_m_per_km * (self.chainage_s - self.s_drb))
        return zprime.astype(np.float32)


def make_synthetic_grid(
    nx: int = 100,
    ny: int = 150,
    min_lon: float = 77.20,
    max_lon: float = 77.33,
    min_lat: float = 28.53,
    max_lat: float = 28.75,
) -> CorridorGrid:
    """Construct synthetic DEM for Yamuna corridor if DTM GeoTIFF not yet provided."""
    lons = np.linspace(min_lon, max_lon, nx)
    lats = np.linspace(max_lat, min_lat, ny) # North to South
    xx, yy = np.meshgrid(lons, lats)

    # Centreline running near lon 77.245 (at Yamuna Pushta lat 28.655)
    centre_lon = 77.245 + 0.02 * np.sin((yy - 28.53) / (28.75 - 28.53) * np.pi)
    dist_to_river_km = np.abs(xx - centre_lon) * 111.0 * np.cos(np.radians(28.64))

    # Channel elevation slopes from ~202 m at Wazirabad down to ~197 m at Okhla
    # At DRB (lat ~28.66) channel bed is ~200.0 m, river surface at low flow is ~203 m.
    channel_elev = 202.0 - (5.0 * (28.75 - yy) / (28.75 - 28.53))
    # Low-lying floodplain near river (0 to 2 km) with realistic 0.05m/100m rise
    floodplain_rise = 3.5 * np.minimum(1.0, dist_to_river_km / 1.5)
    highland_rise = 10.0 * np.maximum(0.0, (dist_to_river_km - 1.5) / 2.0)
    dtm = channel_elev + floodplain_rise + highland_rise

    # Embankments (bunds) protecting city side (dist > 0.6 km)
    bund_mask = (dist_to_river_km >= 0.55) & (dist_to_river_km <= 0.65)
    dtm[bund_mask] = np.maximum(dtm[bund_mask], 210.5)

    river_mask = dist_to_river_km < 0.15 # 150m half-width

    # Chainage s (km) from North (Wazirabad) to South (Okhla)
    total_len_km = 25.0
    chainage_s = (28.75 - yy) / (28.75 - 28.53) * total_len_km

    # Clip outside Wazirabad (28.712 N) and Okhla (28.545 N) to inf / nodata
    outside = (yy > 28.712) | (yy < 28.545)
    dtm[outside] = 999.0 # will stay dry / nodata

    return CorridorGrid(
        dtm=dtm.astype(np.float32),
        lons=lons,
        lats=lats,
        river_mask=river_mask,
        chainage_s=chainage_s.astype(np.float32),
        s_drb=10.0,
    )
