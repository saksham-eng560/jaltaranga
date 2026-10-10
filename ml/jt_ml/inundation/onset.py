"""Morphological priority-flood reconstruction to compute onset.tif and cutoff_0p30.tif."""

import numpy as np
from skimage.morphology import reconstruction


def compute_onset_raster(zprime: np.ndarray, river_mask: np.ndarray) -> np.ndarray:
    """Compute minimax spill level (onset raster) using grayscale morphological reconstruction.
    
    seed = z' on river cells, max(z') elsewhere (seed >= mask).
    onset = reconstruction(seed, z', method='erosion')
    
    A cell floods when DRB gauge reading L >= onset.
    Basins behind dykes remain dry until water overtops the spill elevation.
    """
    mask = zprime.copy()
    seed = np.full_like(mask, fill_value=mask.max())
    seed[river_mask] = mask[river_mask]

    # Morphological erosion reconstruction: finds minimum path maximum height
    onset = reconstruction(seed, mask, method="erosion")
    return onset.astype(np.float32)


def compute_cutoff_0p30_raster(onset: np.ndarray, zprime: np.ndarray) -> np.ndarray:
    """Compute DRB gauge level at which water depth reaches 0.30 m:
    cutoff_0p30 = max(onset, z' + 0.30)
    """
    cutoff = np.maximum(onset, zprime + 0.30)
    return cutoff.astype(np.float32)


def depth_at_level(onset: np.ndarray, zprime: np.ndarray, gauge_level_m: float) -> np.ndarray:
    """Compute instant flood depth at any DRB gauge level:
    depth = where(onset <= L, L - z', 0)
    """
    is_wet = onset <= gauge_level_m
    depth = np.where(is_wet, np.maximum(0.0, gauge_level_m - zprime), 0.0)
    return depth.astype(np.float32)
