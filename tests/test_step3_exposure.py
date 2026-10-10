"""Tests for Step 3 - Critical Infrastructure Exposure."""
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.exposure import (
    classify_risk_stage,
    compute_infrastructure_exposure,
    fetch_osm_infrastructure_data,
)


class TestStep3Exposure(unittest.TestCase):
    def test_classify_risk_stages(self):
        self.assertEqual(classify_risk_stage(204.0), "WARNING")
        self.assertEqual(classify_risk_stage(205.0), "DANGER")
        self.assertEqual(classify_risk_stage(206.5), "EVACUATION")
        self.assertEqual(classify_risk_stage(207.8), "EXTREME_2023")
        self.assertEqual(classify_risk_stage(212.0), "SAFE_ABOVE_2023")

    def test_fetch_and_compute_exposure(self):
        facilities = compute_infrastructure_exposure()
        self.assertGreater(len(facilities), 10)

        # Check key facilities are present
        names = [f.name for f in facilities]
        self.assertTrue(any("Wazirabad" in n for n in names))
        self.assertTrue(any("Yamuna Bank" in n for n in names))
        self.assertTrue(any("Kashmere Gate" in n for n in names))

        # Check thresholds are physically reasonable (between 195m and 260m for Delhi plains & ridge)
        for f in facilities:
            self.assertGreater(f.ground_elevation_m, 195.0)
            self.assertLess(f.ground_elevation_m, 260.0)
            self.assertIn(f.risk_stage, ["WARNING", "DANGER", "EVACUATION", "EXTREME_2023", "SAFE_ABOVE_2023"])


if __name__ == "__main__":
    unittest.main()
