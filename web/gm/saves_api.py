"""S5 world-save API (gm-portal-s5-saves).

Thin transport adapters over ``server.saves.snapshot``: list, create a manual
save, request a restore, delete a manual save, and stream a download. They
validate shape only and never write game state; the save module owns every
filesystem change. Writes are POST-only behind the portal's CSRF contract and
emit ``gm_action`` with the operator account and target save.

Status codes: ``invalid_save_id`` 400, ``save_not_found`` 404, and the domain
refusals ``save_incompatible`` / ``save_in_progress`` /
``save_delete_forbidden`` 409 — never 403, so a refusal can never be mistaken
for an account permission denial. An unexpected failure while creating a save
is ``save_failed`` 500 (the module has already removed its partial files).
"""

from __future__ import annotations

import json
from typing import Any

from django.http import HttpRequest, HttpResponse, StreamingHttpResponse

from server.console import snapshot_policy
from server.saves import snapshot
from server.saves.layout import (
    InvalidSaveId,
    SaveDeleteForbidden,
    SaveError,
    SaveIncompatible,
    SaveInProgress,
    SaveNotFound,
    normalize_label,
)
from web.gm import responses
from web.gm.access import account_label
from world.observability import log_info

_STATUS: dict[type[SaveError], int] = {
    InvalidSaveId: 400,
    SaveNotFound: 404,
    SaveIncompatible: 409,
    SaveInProgress: 409,
    SaveDeleteForbidden: 409,
}


def _method_not_allowed(allowed: str) -> HttpResponse:
    response = responses.error("method_not_allowed", 405)
    response["Allow"] = allowed
    return response


def _refusal(error: SaveError) -> HttpResponse:
    for kind, status in _STATUS.items():
        if isinstance(error, kind):
            return responses.error(kind.code, status)
    return responses.error("save_failed", 500)


def _action(request: HttpRequest, action: str, target: str, outcome: str) -> None:
    log_info(
        "gm_action",
        context={
            "account": account_label(request.user),
            "action": action,
            "target": target,
            "outcome": outcome,
        },
    )


def _label_from(request: HttpRequest) -> str:
    try:
        body = json.loads(request.body or b"{}")
    except ValueError:  # observability: ignore R2: a malformed body is treated as an unlabelled save
        return ""
    return normalize_label(body.get("label") if isinstance(body, dict) else "")


def _listing() -> dict[str, Any]:
    return {
        "saves": [info.to_dict() for info in snapshot.list_saves()],
        "restore_result": snapshot.latest_restore_result(),
        "pending": snapshot.pending_restore(),
        "autosave_keep": snapshot.autosave_keep(),
    }


def saves_collection(request: HttpRequest) -> HttpResponse:
    """``GET`` lists saves; ``POST`` creates a labelled manual save."""
    if request.method == "GET":
        return responses.ok(_listing())
    if request.method != "POST":
        return _method_not_allowed("GET, POST")
    label = _label_from(request)
    try:
        info = snapshot_policy.manual_save(label)
    except SaveError as error:  # observability: ignore R2: a domain refusal is answered by its code and recorded through gm_action
        _action(request, "save_create", "new", error.code)
        return _refusal(error)
    except Exception:  # noqa: BLE001  # observability: ignore R2: the save module already emitted save_failed with the exception
        _action(request, "save_create", "new", "save_failed")
        return responses.error("save_failed", 500)
    _action(request, "save_create", info.id, "created")
    return responses.ok(info.to_dict(), status=201)


def save_restore(request: HttpRequest, save_id: str) -> HttpResponse:
    """``POST`` saves the current world, stages ``save_id``, and shuts down."""
    if request.method != "POST":
        return _method_not_allowed("POST")
    try:
        result = snapshot.request_restore(save_id)
    except SaveError as error:  # observability: ignore R2: a domain refusal is answered by its code and recorded through gm_action
        _action(request, "save_restore", save_id[:64], error.code)
        return _refusal(error)
    except Exception:  # noqa: BLE001  # observability: ignore R2: the save module already emitted save_failed with the exception; nothing was staged
        _action(request, "save_restore", save_id[:64], "save_failed")
        return responses.error("save_failed", 500)
    _action(request, "save_restore", save_id, "requested")
    return responses.ok(result, status=202)


def save_delete(request: HttpRequest, save_id: str) -> HttpResponse:
    """``POST`` deletes one manual save."""
    if request.method != "POST":
        return _method_not_allowed("POST")
    try:
        snapshot.delete_save(save_id)
    except SaveError as error:  # observability: ignore R2: a domain refusal is answered by its code and recorded through gm_action
        _action(request, "save_delete", save_id[:64], error.code)
        return _refusal(error)
    _action(request, "save_delete", save_id, "deleted")
    return responses.ok({"deleted": save_id})


def save_download(request: HttpRequest, save_id: str) -> HttpResponse:
    """``GET`` streams the save as an uncompressed tar.

    Validation happens before the first byte, so every refusal is still the
    JSON envelope; a successful response is the binary exception.
    """
    if request.method != "GET":
        return _method_not_allowed("GET")
    try:
        plan = snapshot.plan_archive(save_id)
    except SaveError as error:  # observability: ignore R2: a domain refusal is answered by its code and recorded through gm_action
        _action(request, "save_download", save_id[:64], error.code)
        return _refusal(error)
    # The archive holds the whole database: every download is recorded.
    _action(request, "save_download", save_id, "streamed")
    response = StreamingHttpResponse(snapshot.iter_archive(plan), content_type="application/x-tar")
    response["Content-Length"] = str(plan.length)
    response["Content-Disposition"] = f'attachment; filename="{plan.filename}"'
    response["Cache-Control"] = "no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


__all__ = ["save_delete", "save_download", "save_restore", "saves_collection"]
