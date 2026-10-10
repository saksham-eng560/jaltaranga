"""CloudWatch Embedded Metric Format (no dependency): DraftLatencyMs, FallbackUsed, ValidatorFail."""

from __future__ import annotations

import json
import os
import sys
import time

NAMESPACE = "jt"


def emit(metrics: dict[str, float], dimensions: dict[str, str] | None = None, unit: dict[str, str] | None = None,
         stream=None) -> dict:
    dims = {"env": os.environ.get("JT_ENV", "local"), **(dimensions or {})}
    doc = {
        "_aws": {"Timestamp": int(time.time() * 1000), "CloudWatchMetrics": [{
            "Namespace": NAMESPACE, "Dimensions": [list(dims)],
            "Metrics": [{"Name": k, "Unit": (unit or {}).get(k, "Count")} for k in metrics]}]},
        **dims, **metrics,
    }
    if os.environ.get("AWS_LAMBDA_FUNCTION_NAME") or stream is not None:
        print(json.dumps(doc), file=stream or sys.stdout)
    return doc
