"""Bedrock region/model probe (SHARED §11.6, Saksham plan §1).

Order: list inference profiles in ap-south-1 → global Nova 2 Lite → us. Nova Micro in us-east-1.
For each candidate, one forced-tool Hindi call is made. Prints the env values to post:
JT_BEDROCK_REGION / JT_BEDROCK_MODEL_ID. Needs AWS credentials (run on Friday with the *Lambda role*
too, §11.8-11).
"""

from __future__ import annotations

import json
import sys
import time

CANDIDATES = [
    ("ap-south-1", "global.amazon.nova-2-lite-v1:0"),
    ("ap-south-1", "apac.amazon.nova-micro-v1:0"),
    ("us-east-1", "global.amazon.nova-2-lite-v1:0"),
    ("us-east-1", "us.amazon.nova-micro-v1:0"),
    ("us-east-1", "us.amazon.nova-lite-v1:0"),
]


def main() -> int:
    import boto3
    from botocore.config import Config

    from jt_alerts.drafter import TOOL

    report: dict = {"profiles_ap_south_1": None, "attempts": []}
    try:
        bedrock = boto3.client("bedrock", region_name="ap-south-1")
        profiles = bedrock.list_inference_profiles().get("inferenceProfileSummaries", [])
        report["profiles_ap_south_1"] = [p["inferenceProfileId"] for p in profiles if "nova" in
                                         p["inferenceProfileId"]]
    except Exception as exc:
        report["profiles_ap_south_1"] = f"error: {type(exc).__name__}: {exc}"

    chosen = None
    for region, model in CANDIDATES:
        client = boto3.client("bedrock-runtime", region_name=region,
                              config=Config(connect_timeout=2, read_timeout=10, retries={"max_attempts": 1}))
        t0 = time.time()
        try:
            resp = client.converse(
                modelId=model,
                messages=[{"role": "user", "content": [{"text": "Write a one-line Hindi flood warning using the "
                                                                 "slot {SHELTER} and {HELP}; no digits."}]}],
                toolConfig={"tools": [TOOL], "toolChoice": {"tool": {"name": "emit_dispatch"}}},
                inferenceConfig={"temperature": 0, "maxTokens": 300})
            out = next((b["toolUse"]["input"] for b in resp["output"]["message"]["content"] if "toolUse" in b), None)
            report["attempts"].append({"region": region, "model": model, "ok": True,
                                       "latency_ms": int((time.time() - t0) * 1000), "sample": out})
            chosen = chosen or (region, model)
        except Exception as exc:
            report["attempts"].append({"region": region, "model": model, "ok": False,
                                       "error": f"{type(exc).__name__}: {str(exc)[:200]}"})
    print(json.dumps(report, ensure_ascii=False, indent=1))
    if chosen:
        print(f"\nexport JT_BEDROCK_REGION={chosen[0]}\nexport JT_BEDROCK_MODEL_ID={chosen[1]}")
        return 0
    print("\nNo Nova profile worked: run template-only (JT_BEDROCK_DISABLED=1), labelled 'template'.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
