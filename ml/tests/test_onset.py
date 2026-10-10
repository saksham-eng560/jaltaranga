"""Tests for morphological onset reconstruction and monotonicity."""

import pytest
import numpy as np
from jt_ml.inundation.grid import make_synthetic_grid
from jt_ml.inundation.onset import compute_onset_raster, compute_cutoff_0p30_raster, depth_at_level


def test_onset_monotonicity():
    grid = make_synthetic_grid(nx=40, ny=60)
    zprime = grid.compute_zprime(delta_m=0.0, slope_m_per_km=0.22)
    onset = compute_onset_raster(zprime, grid.river_mask)
    cutoff = compute_cutoff_0p30_raster(onset, zprime)

    # Cutoff must be >= onset everywhere
    assert np.all(cutoff >= onset)

    # Inundation area must be monotonic with gauge level
    area_206 = np.sum(onset <= 206.0)
    area_207 = np.sum(onset <= 207.0)
    area_208 = np.sum(onset <= 208.66)

    assert area_206 <= area_207
    assert area_207 <= area_208

    # Depth is 0 when level is below the minimum onset level
    min_onset = float(np.min(onset))
    d_low = depth_at_level(onset, zprime, min_onset - 1.0)
    assert np.all(d_low == 0.0)
