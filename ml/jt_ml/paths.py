"""Data loading and path resolution for ML core."""

import os
import sys
from pathlib import Path

# Add shared/py to sys.path if not present
REPO_ROOT = Path(__file__).resolve().parents[2]
SHARED_PY = REPO_ROOT / "shared" / "py"
if str(SHARED_PY) not in sys.path:
    sys.path.insert(0, str(SHARED_PY))

DATA_DIR = Path(os.environ.get("JT_LOCAL_DATA", REPO_ROOT))
ML_DIR = REPO_ROOT / "ml"
OUT_DIR = ML_DIR / "out"


def get_data_dir() -> Path:
    return DATA_DIR


def get_out_dir() -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUT_DIR
