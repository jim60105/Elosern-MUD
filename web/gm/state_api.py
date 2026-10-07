"""Read-only runtime state transport (gm-portal-s3-runtime-state §6/§7).

Every route below is a thin HTTP shell over :mod:`web.gm.readers.registry`:
it parses the request, dispatches, and renders the existing JSON envelope. The
transport owns only the status codes the delta spec fixes — 404
``object_not_found``/``kind_mismatch``, 400 ``query_too_long`` before recall
execution, and the pagination/filter rejections — and never repairs, recomputes
or writes anything. Recall is POST so a long query rides the body; CSRF stays
enforced by Django's middleware even though the route writes nothing.
"""

from __future__ import annotations

from django.http import HttpRequest, HttpResponse

from web.gm import pagination, responses
from web.gm.readers import registry
from web.gm.readers.errors import ReaderError


def _safe_only(request: HttpRequest) -> HttpResponse | None:
    if request.method in ("GET", "HEAD"):
        return None
    return responses.error("method_not_allowed", 405)


def _post_only(request: HttpRequest) -> HttpResponse | None:
    if request.method == "POST":
        return None
    return responses.error("method_not_allowed", 405)


def _failure(error: Exception) -> HttpResponse:
    """Render a reader/pagination failure as its envelope."""
    if isinstance(error, ReaderError):
        return responses.error(error.code, error.status, error.message)
    if isinstance(error, pagination.PaginationError):
        return responses.error(error.code, 400, error.message)
    raise error


def state_list(request: HttpRequest, kind: str) -> HttpResponse:
    """``GET /gm/api/state/<kind>?cursor=&limit=&<filters>``"""
    rejected = _safe_only(request)
    if rejected is not None:
        return rejected
    try:
        data = registry.build_list(kind, request.GET)
    except (ReaderError, pagination.PaginationError) as error:
        return _failure(error)
    return responses.ok(data)


def state_detail(request: HttpRequest, kind: str, entity_id: str) -> HttpResponse:
    """``GET /gm/api/state/<kind>/<id>``"""
    rejected = _safe_only(request)
    if rejected is not None:
        return rejected
    try:
        data = registry.detail(kind, entity_id, registry.filters_of(request.GET))
    except (ReaderError, pagination.PaginationError) as error:
        return _failure(error)
    return responses.ok(data)


def state_object_raw(request: HttpRequest, dbref: str) -> HttpResponse:
    """``GET /gm/api/state/object/<dbref>/raw`` for any Evennia object."""
    rejected = _safe_only(request)
    if rejected is not None:
        return rejected
    try:
        data = registry.raw_object(dbref)
    except (ReaderError, pagination.PaginationError) as error:
        return _failure(error)
    return responses.ok(data)


def state_search(request: HttpRequest) -> HttpResponse:
    """``GET /gm/api/state/search?q=``"""
    rejected = _safe_only(request)
    if rejected is not None:
        return rejected
    try:
        data = registry.search_items(request.GET.get("q"))
    except (ReaderError, pagination.PaginationError) as error:
        return _failure(error)
    return responses.ok(data)


def state_recall(request: HttpRequest, dbref: str) -> HttpResponse:
    """``POST /gm/api/state/npc/<dbref>/recall`` — the read-only preview."""
    rejected = _post_only(request)
    if rejected is not None:
        return rejected
    import json

    body: object = {}
    if request.body:
        try:
            body = json.loads(request.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return responses.error("invalid_query", 400, "請求內容必須是 JSON。")
    try:
        data = registry.recall_preview(dbref, body)
    except (ReaderError, pagination.PaginationError) as error:
        return _failure(error)
    return responses.ok(data)


__all__ = [
    "state_detail",
    "state_list",
    "state_object_raw",
    "state_recall",
    "state_search",
]
