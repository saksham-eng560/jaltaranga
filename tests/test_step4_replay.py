"""Tests for Step 4 - Rainfall Context & Scenario Replay CLI."""
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.rainfall import ERA5_DISCLAIMER, fetch_era5_rainfall
from pipeline.replay import load_scenario, replay_scenario


class TestStep4Replay(unittest.TestCase):
    def test_era5_rainfall_ingestion(self):
        rain = fetch_era5_rainfall("yamuna-2023-07")
        self.assertEqual(rain["scenario"], "yamuna-2023-07")
        self.assertEqual(rain["data_label"], ERA5_DISCLAIMER)
        self.assertGreater(rain["total_rainfall_mm"], 50.0, "Total rainfall in Delhi during July 2023 should exceed 50mm")
        self.assertGreater(len(rain["records"]), 50)

    def test_load_scenarios(self):
        s2023 = load_scenario("yamuna-2023-07")
        self.assertEqual(s2023["scenario_id"], "yamuna-2023-07")
        self.assertEqual(s2023["peak_level_m"], 208.66)
        self.assertGreater(len(s2023["timesteps"]), 10)

        s2025 = load_scenario("yamuna-2025-09")
        self.assertEqual(s2025["scenario_id"], "yamuna-2025-09")
        self.assertEqual(s2025["peak_level_m"], 207.48)

    def test_replay_2023_simulation(self):
        # Run step 18 (near peak 208.66m)
        summary = replay_scenario("yamuna-2023-07", step_filter=18, verbose=False)
        self.assertEqual(summary["scenario_id"], "yamuna-2023-07")
        self.assertEqual(len(summary["steps"]), 1)
        step = summary["steps"][0]
        self.assertEqual(step["gauge_drb_m"], 208.66)
        self.assertGreater(step["delta_danger_m"], 3.0)  # > 3m above danger
        self.assertGreater(len(step["inundated_facilities"]), 0, "Facilities must be submerged at all-time peak 208.66m")
        self.assertIn("Yamuna Pushta (Bela Ghat)", step["affected_colonies"])


if __name__ == "__main__":
    unittest.main()
