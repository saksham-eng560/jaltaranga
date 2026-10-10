"""Routing constants (Saksham plan §2, §4.2, F1). Everything tunable lives here."""

import os

WALK_SPEED_KMH = 3.0
SLOW_WALK_SPEED_KMH = 2.0  # F1: high-vulnerability colonies
SLOW_V_NORM = 0.6
TRANSPORT_WALK_MIN = 30.0  # F1: slow colony with a longer walk → transport needed

SAFETY_BUFFER_MIN = 30.0  # an edge is usable only if exit + 30 min <= close_at
MAX_WALK_MIN = 90.0
CLOSE_SEARCH_H = 6.0  # close_at search horizon
SHELTER_SAFE_H = 6.0  # a shelter must stay dry this long
PLAN_HORIZON_H = 24.0  # plans only for colonies wet within 24 h

SAMPLE_SPACING_M = 15.0
ORIGIN_RADIUS_M = 300.0  # §11.8-2 nearest dry node within 300 m

K_SHELTERS = 3
ALT_PENALTY = 10.0
ALT_MAX_OVERLAP = 0.5

DEPTH_COST_WEIGHT = 5.0
AMBER_COST_FACTOR = 1.5

SHELTER_RATE = float(os.environ.get("JT_SHELTER_RATE", "0.25"))  # documented assumption

AVOID_NAME_RADIUS_M = 1000.0

# F1 priority weights
W_URGENCY, W_POP, W_VULN, W_RISK = 0.45, 0.25, 0.20, 0.10
VULN_WEIGHTS = {"elderly": 1.5, "disabled": 2.0, "children_u5": 1.3, "pregnant": 1.8}

FIELD_REPORT_RADIUS_M = 30.0
