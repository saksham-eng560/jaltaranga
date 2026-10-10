"""Tests for Step 5 - Published Exclusions, Shared Seeds, and System Manifest."""
import json
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.jt_shared.colonies import get_all_colonies
from shared.jt_shared.constants import HERO_COLONY
from shared.jt_shared.manifest import RIVER_YAMUNA_CENTERLINE, get_manifest
from shared.jt_shared.shelters import get_all_shelters


class TestStep5SharedAndExclusions(unittest.TestCase):
    def test_published_exclusions_geojson(self):
        geojson_path = PROJECT_ROOT / "data" / "exclusions" / "published_exclusions.geojson"
        self.assertTrue(geojson_path.exists(), "published_exclusions.geojson must exist")
        with open(geojson_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data.get("type"), "FeatureCollection")
        features = data.get("features", [])
        self.assertGreaterEqual(len(features), 5)
        for f in features:
            props = f.get("properties", {})
            self.assertIn("exclusion_id", props)
            self.assertIn("deck_elevation_m", props)
            self.assertGreater(props["deck_elevation_m"], 208.66)
            self.assertEqual(f["geometry"]["type"], "Polygon")

    def test_canonical_colonies_contract(self):
        colonies = get_all_colonies()
        self.assertGreaterEqual(len(colonies), 6)
        colony_ids = [c.colony_id for c in colonies]
        self.assertIn(HERO_COLONY, colony_ids, f"Hero colony {HERO_COLONY} must exist")
        self.assertIn("DEL-YP-04", colony_ids)
        self.assertIn("DEL-MON-03", colony_ids)

        for c in colonies:
            self.assertTrue(c.colony_id.startswith("DEL-") or c.colony_id.startswith("col_"))
            self.assertGreater(c.population, 1000)
            self.assertGreater(c.vulnerability.elderly, 0)
            self.assertGreater(c.vulnerability.children_u5, 0)
            self.assertTrue(28.52 <= c.lat <= 28.75)
            self.assertTrue(77.18 <= c.lon <= 77.35)

    def test_canonical_shelters_contract(self):
        shelters = get_all_shelters()
        self.assertGreaterEqual(len(shelters), 8)
        shelter_ids = [s.shelter_id for s in shelters]
        self.assertIn("SH-KG-01", shelter_ids)
        self.assertIn("SH-DG-03", shelter_ids)

        for s in shelters:
            self.assertTrue(s.shelter_id.startswith("SH-") or s.shelter_id.startswith("sh_"))
            self.assertGreater(s.capacity_total, 300)
            self.assertGreater(s.free_beds, 0)
            self.assertLessEqual(s.free_beds, s.capacity_total)
            self.assertGreater(s.ground_elevation_m, 208.66)

    def test_manifest_and_hero_anchor(self):
        manifest = get_manifest()
        self.assertEqual(manifest["data_version"], "1.2.0")
        self.assertEqual(manifest["scenario_id"], "yamuna-2023-07")
        self.assertEqual(manifest["default_at"], "2023-07-11T09:00:00+05:30")
        self.assertEqual(manifest["thresholds"]["hfl"], 208.66)
        self.assertGreater(len(RIVER_YAMUNA_CENTERLINE), 8)

    def test_upstream_schema_conformance(self):
        """Verify that exported data files strictly conform to shared/schemas/."""
        import jsonschema

        schemas_dir = PROJECT_ROOT / "shared" / "schemas"

        # 1. Manifest
        manifest = json.loads((PROJECT_ROOT / "data" / "manifest.json").read_text(encoding="utf-8"))
        m_schema = json.loads((schemas_dir / "manifest.schema.json").read_text(encoding="utf-8"))
        jsonschema.validate(instance=manifest, schema=m_schema)

        # 2. Shelters
        shelters = json.loads((PROJECT_ROOT / "data" / "shelters.json").read_text(encoding="utf-8"))
        s_schema = json.loads((schemas_dir / "shelter.schema.json").read_text(encoding="utf-8"))
        for s in shelters:
            jsonschema.validate(instance=s, schema=s_schema)

        # 3. Colonies
        colonies = json.loads((PROJECT_ROOT / "data" / "colonies.json").read_text(encoding="utf-8"))
        c_schema = json.loads((schemas_dir / "colony.schema.json").read_text(encoding="utf-8"))
        for c in colonies:
            jsonschema.validate(instance=c, schema=c_schema)


if __name__ == "__main__":
    unittest.main()
