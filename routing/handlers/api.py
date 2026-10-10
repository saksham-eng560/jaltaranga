"""jt-<env>-routing-fn: GET roads|plans (thin static passthrough), GET/PATCH shelters, POST reports.

Lambdas never load the graph; the UI normally reads plans/roads from CloudFront (SHARED §11.4).
"""

from __future__ import annotations

from jt_shared.http import HttpError, Router
from jt_shared.models import ReportPostResponse
from jt_routing import serving

router = Router()


def _step(kind: str, scenario_id: str, at: str | None) -> list:
    try:
        return serving.read_step(kind, scenario_id, at)
    except serving.NotFoundError as exc:
        raise HttpError(404, "scenario_not_found", str(exc)) from exc


@router.route("GET", "/scenarios/{id}/roads")
def roads(query, body, id):
    rows = _step("roads", id, query.get("at"))
    status = query.get("status")
    if status:
        rows = [r for r in rows if r["status"] in status.split(",")]
    return 200, rows


@router.route("GET", "/scenarios/{id}/plans")
def plans(query, body, id):
    rows = _step("plans", id, query.get("at"))
    return 200, sorted(rows, key=lambda p: -p["priority"])


@router.route("GET", "/scenarios/{id}/unreachable")
def unreachable(query, body, id):
    return 200, _step("unreachable", id, query.get("at"))


@router.route("GET", "/shelters")
def list_shelters(query, body):
    return 200, serving.shelter_store().list()


@router.route("PATCH", "/shelters/{id}")
def patch_shelter(query, body, id):
    shelter_id = id
    delta = body.get("delta")
    if not isinstance(delta, int) or isinstance(delta, bool) or delta == 0:
        raise HttpError(400, "bad_delta", "body must be {\"delta\": <non-zero integer>}")
    try:
        return 200, serving.shelter_store().adjust(shelter_id, delta)
    except serving.NotFoundError as exc:
        raise HttpError(404, "shelter_not_found", shelter_id) from exc
    except serving.Conflict as exc:
        raise HttpError(409, "shelter_full" if delta > 0 else "invalid_release", str(exc)) from exc


@router.route("POST", "/reports")
def post_report(query, body):
    try:
        report = serving.make_report(body, reporter_seed=str(body.get("device_id", "")))
    except Exception as exc:
        raise HttpError(400, "invalid_report", str(exc).splitlines()[0]) from exc
    serving.store_report(report, body.get("replay_at"))
    upload = serving.presigned_upload(report["photo_key"]) if report["photo_key"] else None
    return 201, ReportPostResponse.model_validate({"report": report, "upload": upload}).model_dump(mode="json")


def handler(event, context=None):
    return router(event, context)
