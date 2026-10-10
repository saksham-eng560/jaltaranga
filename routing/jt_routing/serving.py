"""Lambda-side serving for routing (no numpy/networkx): static passthrough, shelters, reports.

Shelter beds use the §11.4 conditional update: ``ADD occupied :d, free_beds :neg`` with
``free_beds >= :d`` (and the mirror ``occupied >= :abs`` for releases). DynamoDB conditions cannot
contain arithmetic, which is why ``free_beds`` is stored and maintained.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import uuid
from datetime import datetime
from decimal import Decimal

from jt_shared import io
from jt_shared.models import FieldReport, Manifest, Shelter
from jt_shared.naming import s3_key
from jt_shared.timeutil import IST, iso, parse_ts, snap_to_step

UPLOAD_MAX_BYTES = 1_048_576
UPLOAD_EXPIRES_S = 300


class Conflict(Exception):
    pass


class NotFoundError(Exception):
    pass


def snap_at(scenario_id: str, at: str | None) -> str:
    try:
        m = Manifest.model_validate(io.read_json(s3_key("manifest", scenario_id=scenario_id)))
    except io.NotFound as exc:
        raise NotFoundError(f"unknown scenario {scenario_id}") from exc
    t = parse_ts(at) if at else (m.default_at or m.valid_at[0])
    t = snap_to_step(t, m.step_min, m.start)
    t = min(max(t, m.valid_at[0]), m.valid_at[-1])
    return iso(t)


def read_step(kind: str, scenario_id: str, at: str | None) -> list:
    t = snap_at(scenario_id, at)
    return io.read_json_or(s3_key(kind, scenario_id=scenario_id, valid_at=t), [])


# --- shelters ------------------------------------------------------------------------------------
def _seed_shelters() -> dict[str, dict]:
    feats = io.read_json(s3_key("shelters"))["features"]
    return {f["properties"]["shelter_id"]: Shelter.model_validate(f["properties"]).model_dump(mode="json")
            for f in feats}


class LocalShelters:
    _lock = threading.Lock()

    def _path(self):
        return io.local_path("state/shelters.json")

    def _load(self) -> dict[str, dict]:
        p = self._path()
        return json.loads(p.read_text("utf-8")) if p.exists() else _seed_shelters()

    def _save(self, d: dict) -> None:
        p = self._path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(d, ensure_ascii=False, indent=1), "utf-8")

    def list(self) -> list[dict]:
        return sorted(self._load().values(), key=lambda s: s["shelter_id"])

    def adjust(self, shelter_id: str, delta: int) -> dict:
        with self._lock:
            d = self._load()
            s = d.get(shelter_id)
            if s is None:
                raise NotFoundError(shelter_id)
            if delta >= 0 and s["free_beds"] < delta:
                raise Conflict(f"only {s['free_beds']} free beds")
            if delta < 0 and s["occupied"] < -delta:
                raise Conflict(f"only {s['occupied']} occupied")
            s["occupied"] += delta
            s["free_beds"] -= delta
            s["updated_at"] = iso(datetime.now(IST))
            self._save(d)
            return s


def _plain(o):
    if isinstance(o, list):
        return [_plain(x) for x in o]
    if isinstance(o, dict):
        return {k: _plain(v) for k, v in o.items()}
    if isinstance(o, Decimal):
        return int(o) if o == o.to_integral_value() else float(o)
    return o


class DynamoShelters:
    def __init__(self, table: str, resource=None):
        import boto3

        self.t = (resource or boto3.resource("dynamodb")).Table(table)

    def list(self) -> list[dict]:
        items, resp = [], self.t.scan()
        items += resp["Items"]
        while "LastEvaluatedKey" in resp:
            resp = self.t.scan(ExclusiveStartKey=resp["LastEvaluatedKey"])
            items += resp["Items"]
        return sorted((_plain(i) for i in items), key=lambda s: s["shelter_id"])

    def adjust(self, shelter_id: str, delta: int) -> dict:
        if delta >= 0:
            cond, vals = "attribute_exists(shelter_id) AND free_beds >= :d", {":d": delta, ":neg": -delta}
        else:
            cond, vals = "attribute_exists(shelter_id) AND occupied >= :abs", {":d": delta, ":neg": -delta,
                                                                                  ":abs": -delta}
        vals[":now"] = iso(datetime.now(IST))
        try:
            resp = self.t.update_item(
                Key={"shelter_id": shelter_id}, UpdateExpression="ADD occupied :d, free_beds :neg SET updated_at = :now",
                ConditionExpression=cond, ExpressionAttributeValues=vals, ReturnValues="ALL_NEW")
        except self.t.meta.client.exceptions.ConditionalCheckFailedException as exc:
            item = self.t.get_item(Key={"shelter_id": shelter_id}).get("Item")
            if not item:
                raise NotFoundError(shelter_id) from exc
            raise Conflict("not enough free beds" if delta >= 0 else "release exceeds occupied") from exc
        return _plain(resp["Attributes"])


def shelter_store():
    if io.local_root() is not None:
        return LocalShelters()
    return DynamoShelters(os.environ["JT_SHELTERS_TABLE"])


# --- reports -------------------------------------------------------------------------------------
def make_report(body: dict, reporter_seed: str = "") -> dict:
    """Validate a POST /reports body into a FieldReport (§5.8). Trust is a constant (formula is Won't)."""
    report_id = str(uuid.uuid4())
    has_photo = bool(body.get("has_photo") or body.get("photo"))
    report = {
        "report_id": report_id,
        "ts": body.get("ts") or iso(datetime.now(IST)),
        "location": body.get("location"),
        "kind": body.get("kind"),
        "depth_cm": body.get("depth_cm"),
        "photo_key": s3_key("report_upload", report_id=report_id) if has_photo else None,
        "reporter_id": "anon-" + hashlib.sha256((reporter_seed or report_id).encode()).hexdigest()[:12],
        "trust": 0.6 if has_photo else 0.3,
        "verified": False,
    }
    return FieldReport.model_validate(report).model_dump(mode="json")


def presigned_upload(key: str, s3=None) -> dict | None:
    if io.local_root() is not None or not io.bucket():
        return None
    import boto3

    s3 = s3 or boto3.client("s3")
    post = s3.generate_presigned_post(
        Bucket=io.bucket(), Key=key, Fields={"Content-Type": "image/jpeg"},
        Conditions=[{"Content-Type": "image/jpeg"}, ["content-length-range", 1, UPLOAD_MAX_BYTES]],
        ExpiresIn=UPLOAD_EXPIRES_S)
    return {"url": post["url"], "fields": post["fields"]}


def store_report(report: dict, replay_at: str | None) -> None:
    item = {**report, "replay_at": replay_at}
    if io.local_root() is not None:
        p = io.local_path("state/reports.json")
        data = json.loads(p.read_text("utf-8")) if p.exists() else []
        data.append(item)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, ensure_ascii=False, indent=1), "utf-8")
        return
    import boto3

    table = boto3.resource("dynamodb").Table(os.environ["JT_REPORTS_TABLE"])
    table.put_item(Item=json.loads(json.dumps(item), parse_float=Decimal))
