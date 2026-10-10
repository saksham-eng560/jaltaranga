"""Assemble infra/template.yaml = base.yaml + every owner section in infra/sections/ (append-only, SHARED §4).

`python infra/build_template.py` (or `--check` in CI to fail when template.yaml is stale).
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUTPUTS = """
Outputs:
  ApiUrl:
    Value: !Sub https://${HttpApi}.execute-api.${AWS::Region}.amazonaws.com
  DataBucketName:
    Value: !Ref DataBucket
  DispatchTopicArn:
    Value: !Ref DispatchTopic
  RoutingFunctionName:
    Value: !Ref RoutingFunction
  AlertsFunctionName:
    Value: !Ref AlertsFunction
  ForecastFunctionName:
    Value: !Ref ForecastFunction
"""


def build() -> str:
    parts = [(HERE / "base.yaml").read_text().rstrip() + "\n"]
    for sec in sorted((HERE / "sections").glob("*.yaml")):
        parts.append("\n" + sec.read_text().rstrip() + "\n")
    return "".join(parts) + OUTPUTS


if __name__ == "__main__":
    text = build()
    out = HERE / "template.yaml"
    if "--check" in sys.argv:
        sys.exit(0 if out.exists() and out.read_text() == text else "infra/template.yaml is stale: run build_template.py")
    out.write_text(text)
    print(out)
