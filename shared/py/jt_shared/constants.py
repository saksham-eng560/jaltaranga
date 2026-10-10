"""jt_shared constants per SHARED_RESOURCES.md."""

DELHI_RLY_BRIDGE = "DELHI_RLY_BRIDGE"
HATHNIKUND = "HATHNIKUND"

HORIZONS_H = [1, 3, 6, 12, 24]

# Critical flood levels at Delhi Railway Bridge (metres)
WARNING_LEVEL_M = 204.5
DANGER_LEVEL_M = 205.33
EXTREME_LEVEL_M = 208.66 # July 2023 peak

# Road cutoff depth threshold
ROAD_CUTOFF_DEPTH_M = 0.30
SHALLOW_WATER_DEPTH_M = 0.05

# Depth categories
DEPTH_CLASSES = [
    "0.05-0.3",
    "0.3-1",
    "1-2",
    ">2",
]

# Pilot corridor bounding box [min_lon, min_lat, max_lon, max_lat]
BBOX = [77.20, 28.53, 77.33, 28.75]

DEFAULT_SCENARIO_ID = "yamuna-2023-07"
DEFAULT_HERO_COLONY = "DEL-YP-04"
