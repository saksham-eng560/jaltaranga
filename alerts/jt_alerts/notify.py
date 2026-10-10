"""SNS email dispatch (SHARED §11.6): ASCII English subject < 100 chars, Hindi only in the body.

Offline (JT_LOCAL_DATA set or no topic) the message is written to ``<JT_LOCAL_DATA>/outbox/<id>.eml``.
"""

from __future__ import annotations

import os
import re
import unicodedata
from email.message import EmailMessage

from jt_shared import io

LABELS = {"URGENT_EVACUATION_DISPATCH": "URGENT EVACUATION", "PREPARE": "PREPARE",
          "SHELTER_IN_PLACE": "SHELTER IN PLACE", "ALL_CLEAR": "ALL CLEAR"}
SUBJECT_MAX = 99


def ascii_only(text: str) -> str:
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[\r\n\t]+", " ", t).strip()


def subject(alert_type: str, colony_en: str) -> str:
    s = ascii_only(f"[Jaltaranga] {LABELS.get(alert_type, alert_type)}: {colony_en}")
    return s[:SUBJECT_MAX]


def body(card: dict) -> str:
    lines = [card["message_hi"], "", card["message_en"], "", f"SMS: {card['sms_hi']}"]
    if card.get("audio_url_hi"):
        lines += ["", f"Audio (Hindi): {card['audio_url_hi']}"]
    v = card["validation"]
    lines += ["", f"Validated: {', '.join(v['checks'])}"
              + (" (template fallback used)" if v["fallback_used"] else ""),
              f"Dispatch {card['dispatch_id']} approved by {card.get('approved_by') or '-'}",
              "Synthetic demo data. Helplines: 1077 (district control room), 112 (emergency)."]
    return "\n".join(lines)


def publish(card: dict, colony_en: str, sns=None) -> str:
    subj, text = subject(card["alert_type"], colony_en), body(card)
    topic = os.environ.get("JT_SNS_TOPIC_ARN")
    if io.local_root() is not None or not topic:
        msg = EmailMessage()
        msg["Subject"], msg["From"], msg["To"] = subj, "jaltaranga@localhost", "dispatch@localhost"
        msg.set_content(text)
        io.write_bytes(f"outbox/{card['dispatch_id']}.eml", bytes(msg), "message/rfc822")
        return f"outbox/{card['dispatch_id']}.eml"
    import boto3

    sns = sns or boto3.client("sns")
    out = sns.publish(TopicArn=topic, Subject=subj, Message=text, MessageAttributes={
        "colony_id": {"DataType": "String", "StringValue": card["plan_ref"]["colony_id"]},
        "alert_type": {"DataType": "String", "StringValue": card["alert_type"]}})
    return out["MessageId"]
