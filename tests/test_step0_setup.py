"""Tests for Step 0 - Project layout and structure check."""
import unittest
from pathlib import Path


class TestStep0Setup(unittest.TestCase):
    def setUp(self):
        self.project_root = Path(__file__).resolve().parent.parent

    def test_required_directories_exist(self):
        expected_dirs = [
            self.project_root / "pipeline",
            self.project_root / "shared" / "jt_shared",
            self.project_root / "tests",
            self.project_root / "data",
        ]
        for directory in expected_dirs:
            self.assertTrue(directory.exists() and directory.is_dir(), f"Missing directory: {directory}")

    def test_pipeline_readme_exists(self):
        readme_path = self.project_root / "pipeline" / "README.md"
        self.assertTrue(readme_path.exists() and readme_path.is_file(), "pipeline/README.md is missing")
        content = readme_path.read_text(encoding="utf-8")
        self.assertIn("Jaltaranga", content)
        self.assertIn("Embankment-Aware DTM", content)

    def test_makefile_exists(self):
        makefile = self.project_root / "Makefile"
        self.assertTrue(makefile.exists() and makefile.is_file(), "Makefile is missing")
        content = makefile.read_text(encoding="utf-8")
        self.assertIn("replay-local", content)


if __name__ == "__main__":
    unittest.main()
