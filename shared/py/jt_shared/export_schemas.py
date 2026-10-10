"""Export JSON Schemas from the pydantic models: ``python -m jt_shared.export_schemas [outdir]``."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .models import ALL_MODELS

DEFAULT_OUT = Path(__file__).resolve().parents[2] / "schemas"


def export(out: Path = DEFAULT_OUT) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for name, model in ALL_MODELS.items():
        path = out / f"{name}.schema.json"
        schema = model.model_json_schema(mode="serialization")
        schema["$id"] = f"https://jaltaranga.dev/schemas/{name}.schema.json"
        path.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        written.append(path)
    return written


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
    for p in export(target):
        print(p)
