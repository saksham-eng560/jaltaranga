"""jt-<env>-alerts-fn: dispatch draft, approve, list, ack (SHARED §7, §11.4). 25 s timeout, 18 s draft budget."""

from __future__ import annotations

from jt_alerts.service import DispatchService, ServiceError
from jt_alerts.store import default_store
from jt_shared.http import HttpError, Router

router = Router()
_service: DispatchService | None = None


def service() -> DispatchService:
    global _service
    if _service is None:
        _service = DispatchService(default_store())
    return _service


def _call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except ServiceError as exc:
        raise HttpError(exc.status, exc.code, exc.message) from exc


@router.route("POST", "/scenarios/{id}/colonies/{cid}/dispatch")
def draft(query, body, id, cid):
    scenario_id, colony_id = id, cid
    fresh = str(query.get("fresh", "")).lower() in ("1", "true", "yes")
    return 201, _call(service().draft, scenario_id, colony_id, query.get("at"), fresh=fresh)


@router.route("POST", "/dispatches/{dispatch_id}/approve")
def approve(query, body, dispatch_id):
    return 200, _call(service().approve, dispatch_id, body.get("approved_by") or "officer-demo")


@router.route("GET", "/dispatches")
def list_dispatches(query, body):
    return 200, _call(service().list, query.get("scenario_id"))


@router.route("POST", "/dispatches/{dispatch_id}/ack")
def ack(query, body, dispatch_id):
    return 200, _call(service().ack, dispatch_id)


def handler(event, context=None):
    return router(event, context)
