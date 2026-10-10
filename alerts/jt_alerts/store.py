"""Dispatch log and lifecycle state: DynamoDB in AWS, JSON files under $JT_LOCAL_DATA/state offline.

Tables (SHARED §4): ``jt-<env>-dispatches`` (pk ``dispatch_id``, attribute ``scenario_id``) and
``jt-<env>-scenario-state`` (pk ``pk``) for dedup records.
"""

from __future__ import annotations

import json
import os
import threading
from decimal import Decimal
from typing import Any

from jt_shared import io


class ConditionFailed(Exception):
    pass


class LocalStore:
    _lock = threading.Lock()

    def _path(self, name: str):
        return io.local_path(f"state/{name}.json")

    def _load(self, name: str) -> dict:
        p = self._path(name)
        return json.loads(p.read_text("utf-8")) if p.exists() else {}

    def _save(self, name: str, data: dict) -> None:
        p = self._path(name)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, ensure_ascii=False, indent=1), "utf-8")

    def put(self, card: dict) -> None:
        with self._lock:
            d = self._load("dispatches")
            d[card["dispatch_id"]] = card
            self._save("dispatches", d)

    def get(self, dispatch_id: str) -> dict | None:
        return self._load("dispatches").get(dispatch_id)

    def list(self, scenario_id: str | None = None) -> list[dict]:
        cards = list(self._load("dispatches").values())
        if scenario_id:
            cards = [c for c in cards if c["plan_ref"]["scenario_id"] == scenario_id]
        return sorted(cards, key=lambda c: c["ts"])

    def transition(self, dispatch_id: str, from_status: str, to_status: str, **fields: Any) -> dict:
        with self._lock:
            d = self._load("dispatches")
            card = d.get(dispatch_id)
            if card is None or card["status"] != from_status:
                raise ConditionFailed(dispatch_id)
            card.update(fields, status=to_status)
            self._save("dispatches", d)
            return card

    def get_state(self, pk: str) -> dict | None:
        return self._load("scenario_state").get(pk)

    def put_state(self, pk: str, value: dict) -> None:
        with self._lock:
            d = self._load("scenario_state")
            d[pk] = value
            self._save("scenario_state", d)


def _to_ddb(obj: Any) -> Any:
    return json.loads(json.dumps(obj), parse_float=Decimal)


def _from_ddb(obj: Any) -> Any:
    if isinstance(obj, list):
        return [_from_ddb(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _from_ddb(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        return int(obj) if obj == obj.to_integral_value() else float(obj)
    return obj


class DynamoStore:
    def __init__(self, dispatches_table: str, state_table: str, resource=None):
        import boto3

        ddb = resource or boto3.resource("dynamodb")
        self.t = ddb.Table(dispatches_table)
        self.s = ddb.Table(state_table)

    def put(self, card: dict) -> None:
        self.t.put_item(Item=_to_ddb({**card, "scenario_id": card["plan_ref"]["scenario_id"]}))

    def get(self, dispatch_id: str) -> dict | None:
        item = self.t.get_item(Key={"dispatch_id": dispatch_id}).get("Item")
        if not item:
            return None
        item = _from_ddb(item)
        item.pop("scenario_id", None)
        return item

    def list(self, scenario_id: str | None = None) -> list[dict]:
        from boto3.dynamodb.conditions import Attr

        kwargs = {"FilterExpression": Attr("scenario_id").eq(scenario_id)} if scenario_id else {}
        items, resp = [], self.t.scan(**kwargs)
        items += resp["Items"]
        while "LastEvaluatedKey" in resp:
            resp = self.t.scan(ExclusiveStartKey=resp["LastEvaluatedKey"], **kwargs)
            items += resp["Items"]
        out = [_from_ddb(i) for i in items]
        for c in out:
            c.pop("scenario_id", None)
        return sorted(out, key=lambda c: c["ts"])

    def transition(self, dispatch_id: str, from_status: str, to_status: str, **fields: Any) -> dict:
        names = {"#s": "status"}
        values = {":from": from_status, ":to": to_status}
        sets = ["#s = :to"]
        for i, (k, v) in enumerate(fields.items()):
            names[f"#f{i}"] = k
            values[f":v{i}"] = _to_ddb(v)
            sets.append(f"#f{i} = :v{i}")
        try:
            resp = self.t.update_item(Key={"dispatch_id": dispatch_id}, UpdateExpression="SET " + ", ".join(sets),
                                      ConditionExpression="#s = :from", ExpressionAttributeNames=names,
                                      ExpressionAttributeValues=values, ReturnValues="ALL_NEW")
        except self.t.meta.client.exceptions.ConditionalCheckFailedException as exc:
            raise ConditionFailed(dispatch_id) from exc
        item = _from_ddb(resp["Attributes"])
        item.pop("scenario_id", None)
        return item

    def get_state(self, pk: str) -> dict | None:
        item = self.s.get_item(Key={"pk": pk}).get("Item")
        return _from_ddb(item)["value"] if item else None

    def put_state(self, pk: str, value: dict) -> None:
        self.s.put_item(Item={"pk": pk, "value": _to_ddb(value)})


def default_store():
    if io.local_root() is not None:
        return LocalStore()
    return DynamoStore(os.environ["JT_DISPATCHES_TABLE"], os.environ["JT_STATE_TABLE"])
