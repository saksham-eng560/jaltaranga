"""Tests for Step 1 - Embankment-Aware DTM, Calibration Integrity & Golden Checks."""
import csv
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.dtm import (
    LAT_MAX,
    LAT_MIN,
    LON_MAX,
    LON_MIN,
    build_calibrated_dtm,
    check_inundation_depth,
    compute_water_surface_elevation,
    load_calibration_points,
    run_golden_sanity_check,
)
from shared.jt_shared.colonies import get_all_colonies


class TestStep1DTM(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dtm = build_calibrated_dtm()

    def test_dtm_dimensions_and_resolution(self):
        self.assertIsNotNone(self.dtm)
        self.assertGreater(self.dtm.rows, 500)
        self.assertGreater(self.dtm.cols, 500)
        self.assertEqual(self.dtm.elevation.shape, (self.dtm.rows, self.dtm.cols))
        self.assertEqual(self.dtm.burn_mask.shape, (self.dtm.rows, self.dtm.cols))

    def test_water_surface_elevation_gradient(self):
        wse_upstream = compute_water_surface_elevation(208.66, 28.71)
        wse_drb = compute_water_surface_elevation(208.66, 28.662)
        wse_downstream = compute_water_surface_elevation(208.66, 28.55)
        self.assertGreater(wse_upstream, wse_drb)
        self.assertGreater(wse_drb, wse_downstream)

    def test_golden_sanity_check(self):
        ok, report = run_golden_sanity_check(self.dtm)
        self.assertTrue(ok, f"Golden sanity check failed: {report}")

    def test_p4_t2_burn_mask_does_not_seal_colonies(self):
        """P4 / T2 check: No colony centroid or wet calibration point may fall inside the burn mask."""
        colonies = get_all_colonies()
        for col in colonies:
            in_mask = self.dtm.is_in_burn_mask(col.lat, col.lon)
            self.assertFalse(
                in_mask,
                f"Defect T2: Colony '{col.name}' ({col.colony_id}) is sealed inside the burn mask!",
            )

        calib_pts = load_calibration_points()
        for pt in calib_pts:
            if pt["is_wet_at_hfl"] and not pt["excluded"]:
                in_mask = self.dtm.is_in_burn_mask(pt["lat"], pt["lon"])
                self.assertFalse(
                    in_mask,
                    f"Defect T2: Active wet calibration point '{pt['name']}' is trapped inside the burn mask!",
                )

    def test_p4_t3_calibration_points_inside_chainage_clip(self):
        """P4 / T3 check: All non-excluded calibration points must lie inside [28.53, 28.712]."""
        pts = load_calibration_points()
        self.assertGreater(len(pts), 10)
        for pt in pts:
            if not pt["excluded"]:
                self.assertGreaterEqual(
                    pt["lat"],
                    28.53,
                    f"Point '{pt['name']}' (lat={pt['lat']}) is south of Okhla clip (28.53)",
                )
                self.assertLessEqual(
                    pt["lat"],
                    28.720,
                    f"Point '{pt['name']}' (lat={pt['lat']}) is north of Wazirabad clip (28.720)",
                )

    def test_p4_t4_headline_wtps_held_out(self):
        """P4 / T4 check: Wazirabad and Okhla WTP sites must be held-out validation, not in-sample."""
        pts = load_calibration_points()
        wtp_pts = [p for p in pts if "WTP" in p["name"]]
        self.assertGreaterEqual(len(wtp_pts), 2)
        for wtp in wtp_pts:
            self.assertTrue(wtp["excluded"], f"WTP '{wtp['name']}' must be excluded from fitting")
            self.assertEqual(wtp["exclusion_reason"], "held-out validation")

    def test_data_honesty_calibration_points(self):
        """Data honesty check: every calibration point must be flagged is_estimate=True."""
        pts = load_calibration_points()
        for pt in pts:
            self.assertTrue(
                pt.get("is_estimate", False),
                f"Point '{pt['name']}' must have is_estimate=True",
            )
            self.assertIn("basis", pt)
            self.assertTrue(pt.get("basis", "").startswith("approximate, unverified"))
            self.assertIsNotNone(pt.get("glo30_m"))
            self.assertIsInstance(pt.get("glo30_m"), float)
            self.assertNotIn("Survey of India Benchmark", pt.get("basis", ""))
            self.assertNotIn("PWD High Water Mark", pt.get("basis", ""))

        # Mayur Vihar row check: note about embankment
        mv_pts = [p for p in pts if "Mayur Vihar" in p["name"]]
        self.assertEqual(len(mv_pts), 1)
        self.assertIn("embankment protects it", mv_pts[0]["basis"])

        # Kashmere Gate row check: wet must match ground height
        kg_pts = [p for p in pts if "Kashmere Gate" in p["name"]]
        self.assertEqual(len(kg_pts), 1)
        self.assertTrue(kg_pts[0]["is_wet_at_hfl"])
        self.assertLess(kg_pts[0]["estimated_m"], 208.66)

    def test_dtm_metadata_delta_zero(self):
        """Check that delta offset is strictly fixed at 0.0 with no empirical fitting."""
        import json
        from pipeline.dtm import METADATA_PATH
        with open(METADATA_PATH, "r", encoding="utf-8") as f:
            meta = json.load(f)
        self.assertEqual(meta["delta_m"], 0.0)
        self.assertEqual(meta["calibrated_by"], "fixed_zero_baseline")


if __name__ == "__main__":
    unittest.main()

