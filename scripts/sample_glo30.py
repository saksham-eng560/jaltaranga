import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import csv
from pipeline.dtm import build_calibrated_dtm

dtm = build_calibrated_dtm()
with open("data/calibration_points.csv", "r", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

updated_rows = []
for r in rows:
    lat, lon = float(r["lat"]), float(r["lon"])
    glo30_val = round(dtm.get_elevation_at(lat, lon), 2)
    r["glo30_m"] = str(glo30_val)
    # Update basis to "approximate, unverified" and add Mayur Vihar note
    if "Mayur Vihar" in r["name"]:
        r["basis"] = "approximate, unverified (dry at 208.66m only because an embankment protects it)"
    else:
        r["basis"] = "approximate, unverified"
    updated_rows.append(r)
    print(f"{r['name']}: est={r['estimated_m']}, glo30={glo30_val}")

fieldnames = ["name", "lat", "lon", "reach", "estimated_m", "glo30_m", "is_estimate", "is_wet_at_hfl", "excluded", "exclusion_reason", "basis"]
with open("data/calibration_points.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(updated_rows)

# also sync calib_points.csv
with open("data/calib_points.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(updated_rows)

print("Updated data/calibration_points.csv successfully!")
