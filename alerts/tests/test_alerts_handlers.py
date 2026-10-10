import email
import importlib.util
import json
from pathlib import Path

from jt_shared import io
from jt_shared.models import DispatchCard

spec = importlib.util.spec_from_file_location("alerts_api", Path(__file__).resolve().parents[1] / "handlers" / "api.py")
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)


def call(method, path, query=None, body=None):
    r = api.handler({"version": "2.0", "rawPath": path, "queryStringParameters": query,
                     "requestContext": {"http": {"method": method, "path": path}},
                     "body": json.dumps(body) if body is not None else None})
    return r["statusCode"], json.loads(r["body"])


def test_draft_approve_list_ack(world, hero_t):
    s, card = call("POST", "/scenarios/yamuna-2023-07/colonies/DEL-YP-04/dispatch", {"at": hero_t, "fresh": "1"})
    assert s == 201, card
    DispatchCard.model_validate(card)
    assert card["status"] == "draft" and card["alert_type"] == "URGENT_EVACUATION_DISPATCH"
    assert card["validation"]["passed"] and len(card["sms_hi"]) <= 160
    assert card["plan_ref"]["computed_at"] == hero_t

    s, again = call("POST", "/scenarios/yamuna-2023-07/colonies/DEL-YP-04/dispatch", {"at": hero_t})
    assert s == 201 and again["dispatch_id"] == card["dispatch_id"]  # dedup within the cooldown

    s, sent = call("POST", f"/dispatches/{card['dispatch_id']}/approve", body={"approved_by": "officer-test"})
    assert s == 200 and sent["status"] == "sent" and sent["approved_by"] == "officer-test"
    s, sent2 = call("POST", f"/dispatches/{card['dispatch_id']}/approve")
    assert s == 200 and sent2["status"] == "sent"  # idempotent

    eml = io.local_path(f"outbox/{card['dispatch_id']}.eml")
    msg = email.message_from_bytes(eml.read_bytes())
    subject = msg["Subject"]
    assert subject.isascii() and len(subject) < 100 and "URGENT EVACUATION" in subject
    body = msg.get_payload(decode=True).decode("utf-8")
    assert card["message_hi"] in body

    s, cards = call("GET", "/dispatches", {"scenario_id": "yamuna-2023-07"})
    assert s == 200 and any(c["dispatch_id"] == card["dispatch_id"] for c in cards)
    s, acked = call("POST", f"/dispatches/{card['dispatch_id']}/ack")
    assert s == 200 and acked["status"] == "acknowledged"


def test_cache_hit_and_errors(world, hero_t):
    s, card = call("POST", "/scenarios/yamuna-2023-07/colonies/DEL-YBZ-10/dispatch", {"at": hero_t})
    assert s == 201 and card["validation"]["source"] == "cache"
    s, body = call("POST", "/scenarios/yamuna-2023-07/colonies/NOPE/dispatch", {"at": hero_t})
    assert s == 404 and body["error"]["code"] == "colony_not_found"
    s, body = call("POST", "/scenarios/yamuna-2023-07/colonies/DEL-SPK-06/dispatch",
                   {"at": "2023-07-09T00:00:00+05:30"})
    assert s == 422 and body["error"]["code"] == "no_alert_needed"
    assert call("POST", "/dispatches/nope/approve")[0] == 404
    assert call("POST", "/scenarios/nope/colonies/DEL-YP-04/dispatch")[0] == 404


def test_shelter_in_place_for_already_wet(world):
    s, card = call("POST", "/scenarios/yamuna-2023-07/colonies/DEL-BLA-02/dispatch",
                   {"at": "2023-07-11T12:00:00+05:30", "fresh": "1"})
    assert s == 201 and card["alert_type"] == "SHELTER_IN_PLACE"
    assert "पानी आ चुका है" in card["message_hi"]
