"""Tests for exact split-conformal calibration."""

from jt_ml.models.conformal import SplitConformalCalibrator


def test_split_conformal_quantile():
    calib = SplitConformalCalibrator(alpha=0.2) # 80% coverage
    residuals = {
        6: [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0] # 10 samples
    }
    # n=10, ceil(11 * 0.8) - 1 = ceil(8.8) - 1 = 9 - 1 = 8th index (0.9)
    calib.fit(residuals)
    lo, hi, q = calib.get_interval(6, 207.0)
    assert q >= 0.9
    assert lo == round(207.0 - q, 3)
    assert hi == round(207.0 + q, 3)
