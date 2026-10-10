"""Tests for Step 2 - Provenance & QC Ledger."""
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.ledger import LedgerEntry, inspect_ledger, load_ledger, record, validate_ledger


class TestStep2Ledger(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.ledger_file = Path(self.temp_dir.name) / "test_ledger.jsonl"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_record_and_load(self):
        entry = record(
            dataset="cwc-delhi-railway-bridge-gauges",
            source_url="https://cwc.gov.in/ffs",
            source_name="Central Water Commission Flood Forecasting",
            licence="Government Open Data Licence - India",
            qc_flag="digitized",
            qc_notes="Extracted from hourly official flood advisories July 2023",
            metadata={"peak_m": 208.66, "station": "Delhi Railway Bridge (Old)"},
            ledger_path=self.ledger_file,
        )
        self.assertTrue(self.ledger_file.exists())
        self.assertEqual(entry.qc_flag, "digitized")

        entries = load_ledger(self.ledger_file)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].dataset, "cwc-delhi-railway-bridge-gauges")
        self.assertEqual(entries[0].metadata["peak_m"], 208.66)

    def test_invalid_qc_flag_raises(self):
        with self.assertRaises(ValueError):
            record(
                dataset="test-data",
                source_url="https://example.com",
                source_name="Test Source",
                licence="MIT",
                qc_flag="invalid_flag",
                qc_notes="Invalid test",
                ledger_path=self.ledger_file,
            )

    def test_validate_ledger(self):
        record(
            dataset="copernicus-glo30-dem",
            source_url="s3://copernicus-dem-30m/",
            source_name="Copernicus GLO-30 DSM",
            licence="Copernicus Open Access",
            qc_flag="ok",
            qc_notes="30m elevation model clipped to Delhi Wazirabad-Okhla corridor",
            ledger_path=self.ledger_file,
        )
        self.assertTrue(validate_ledger(self.ledger_file))


if __name__ == "__main__":
    unittest.main()
