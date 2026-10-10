"""F3: Polly Kajal Hindi voice briefing, cached by content hash at ``audio/<sha256>.mp3`` (SHARED §11.2).

SSML is built only from the **validated** ``message_hi`` plus a repeat of the shelter name and 1077.
Neural voices support ``<speak> <p> <s> <break>``; nothing fancier is used.
"""

from __future__ import annotations

import hashlib
import os
from xml.sax.saxutils import escape

from jt_shared import io
from jt_shared.naming import s3_key

VOICE = os.environ.get("JT_POLLY_VOICE", "Kajal")
PRESIGN_S = int(os.environ.get("JT_AUDIO_PRESIGN_S", "3600"))


def build_ssml(message_hi: str, shelter_hi: str | None) -> str:
    repeat = f"फिर से: {escape(shelter_hi)} जाएं। मदद के लिए 1077 पर कॉल करें।" if shelter_hi \
        else "फिर से: मदद के लिए 1077 पर कॉल करें।"
    return (f'<speak><p>{escape(message_hi)}</p><break time="800ms"/>'
            f"<p>{repeat}</p></speak>")


def audio_key(ssml: str) -> str:
    return s3_key("audio", sha256=hashlib.sha256(ssml.encode("utf-8")).hexdigest())


def enabled() -> bool:
    return io.local_root() is None and os.environ.get("JT_POLLY_DISABLED", "").lower() not in ("1", "true")


def synthesize(ssml: str, polly=None, s3=None, presign_s: int = PRESIGN_S) -> str | None:
    """Return a presigned URL for the mp3 (synthesising it on a cache miss), or None if unavailable."""
    if not enabled():
        return None
    import boto3

    key = audio_key(ssml)
    bucket = io.bucket()
    s3 = s3 or boto3.client("s3")
    try:
        s3.head_object(Bucket=bucket, Key=key)
    except Exception:
        polly = polly or boto3.client("polly", region_name=os.environ.get("JT_POLLY_REGION", "ap-south-1"))
        out = polly.synthesize_speech(Engine="neural", VoiceId=VOICE, LanguageCode="hi-IN", OutputFormat="mp3",
                                      SampleRate="22050", TextType="ssml", Text=ssml)
        s3.put_object(Bucket=bucket, Key=key, Body=out["AudioStream"].read(), ContentType="audio/mpeg")
    return presign(key, s3, presign_s)


def presign(key: str, s3=None, presign_s: int = PRESIGN_S) -> str:
    import boto3

    s3 = s3 or boto3.client("s3")
    return s3.generate_presigned_url("get_object", Params={"Bucket": io.bucket(), "Key": key}, ExpiresIn=presign_s)


def key_from_url(url: str | None) -> str | None:
    if not url:
        return None
    i = url.find("audio/")
    return url[i:].split("?")[0] if i >= 0 else None
