"""Data access with a local-filesystem fallback (§8): JT_LOCAL_DATA=./data → no AWS needed."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class NotFound(KeyError):
    pass


def local_root() -> Path | None:
    root = os.environ.get("JT_LOCAL_DATA")
    return Path(root) if root else None


def bucket() -> str | None:
    return os.environ.get("JT_DATA_BUCKET")


_s3 = None


def _client():
    global _s3
    if _s3 is None:
        import boto3  # only needed in AWS mode

        _s3 = boto3.client("s3")
    return _s3


def local_path(key: str) -> Path:
    root = local_root()
    if root is None:
        raise RuntimeError("JT_LOCAL_DATA is not set")
    return root / key


def read_bytes(key: str) -> bytes:
    root = local_root()
    if root is not None:
        p = root / key
        if not p.exists():
            raise NotFound(key)
        return p.read_bytes()
    b = bucket()
    if not b:
        raise RuntimeError("neither JT_LOCAL_DATA nor JT_DATA_BUCKET is set")
    client = _client()
    try:
        return client.get_object(Bucket=b, Key=key)["Body"].read()
    except client.exceptions.NoSuchKey as exc:
        raise NotFound(key) from exc
    except Exception as exc:  # 403 behind OAC means absent too (§11.8-9)
        code = getattr(exc, "response", {}).get("Error", {}).get("Code")
        if code in ("404", "403", "NoSuchKey", "AccessDenied"):
            raise NotFound(key) from exc
        raise


def write_bytes(key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    root = local_root()
    if root is not None:
        p = root / key
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return
    _client().put_object(Bucket=bucket(), Key=key, Body=data, ContentType=content_type)


def exists(key: str) -> bool:
    try:
        read_bytes(key)
        return True
    except NotFound:
        return False


def read_json(key: str) -> Any:
    return json.loads(read_bytes(key).decode("utf-8"))


def read_json_or(key: str, default: Any) -> Any:
    try:
        return read_json(key)
    except NotFound:
        return default


def dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=False)


def write_json(key: str, obj: Any) -> None:
    write_bytes(key, dumps(obj).encode("utf-8"), "application/json")
