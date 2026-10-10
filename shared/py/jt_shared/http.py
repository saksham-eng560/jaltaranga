"""Minimal API Gateway HTTP API (payload v2) router: no dependency, easy to unit test.

Errors use the SHARED §7 envelope ``{"error": {"code", "message"}}`` with a proper status.
"""

from __future__ import annotations

import base64
import json
import os
import re
from typing import Any, Callable

Handler = Callable[..., Any]


class HttpError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def cors_headers() -> dict[str, str]:
    return {
        "Access-Control-Allow-Origin": os.environ.get("JT_CORS_ORIGIN", "*"),
        "Access-Control-Allow-Methods": "GET,POST,PATCH,OPTIONS",
        "Access-Control-Allow-Headers": "content-type,authorization",
    }


def response(status: int, body: Any) -> dict:
    return {"statusCode": status, "headers": {"content-type": "application/json; charset=utf-8", **cors_headers()},
            "body": json.dumps(body, ensure_ascii=False)}


def error(status: int, code: str, message: str) -> dict:
    return response(status, {"error": {"code": code, "message": message}})


class Router:
    def __init__(self):
        self.routes: list[tuple[str, re.Pattern, Handler]] = []

    def route(self, method: str, path: str):
        pattern = re.compile("^" + re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", path) + "/?$")

        def deco(fn: Handler) -> Handler:
            self.routes.append((method.upper(), pattern, fn))
            return fn

        return deco

    def __call__(self, event: dict, context: Any = None) -> dict:
        http = event.get("requestContext", {}).get("http", {})
        method = (http.get("method") or event.get("httpMethod") or "GET").upper()
        path = event.get("rawPath") or http.get("path") or event.get("path") or "/"
        stage = event.get("requestContext", {}).get("stage")
        if stage and stage != "$default" and path.startswith(f"/{stage}/"):
            path = path[len(stage) + 1:]
        if method == "OPTIONS":
            return {"statusCode": 204, "headers": cors_headers(), "body": ""}
        query = event.get("queryStringParameters") or {}
        raw = event.get("body")
        if raw and event.get("isBase64Encoded"):
            raw = base64.b64decode(raw).decode("utf-8")
        allowed = False
        for m, pat, fn in self.routes:
            match = pat.match(path)
            if not match:
                continue
            allowed = True
            if m != method:
                continue
            try:
                body = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                return error(400, "bad_json", "request body is not valid JSON")
            try:
                status, payload = fn(query=query, body=body, **match.groupdict())
                return response(status, payload)
            except HttpError as exc:
                return error(exc.status, exc.code, exc.message)
            except ValueError as exc:
                return error(400, "bad_request", str(exc))
        if allowed:
            return error(405, "method_not_allowed", f"{method} not allowed on {path}")
        return error(404, "not_found", f"no route for {method} {path}")
