"""GM views: the SPA shell and the read-only operator APIs.

Every view is registered through ``web.gm.urls.gm_path`` (``gm_required``).
Every API here is GET-only and changes no state. The dashboard folds the S1
Django/database health into its process slot and never probes LLM services;
the call-detail view reads the retained S2a transcript on demand.
"""

from __future__ import annotations

import re

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, resolve_url
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_safe

from web.gm import dashboard as dashboard_snapshot
from web.gm import responses
from web.gm.access import route_label
from web.gm.version import game_version
from world.observability import log_error
from world.observability import transcript

CALL_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")


@require_safe
@ensure_csrf_cookie
def shell(request: HttpRequest, rest: str = "") -> HttpResponse:
    """Serve the SPA shell; client-side history routing owns ``rest``."""
    response = render(
        request,
        "gm/index.html",
        {
            "gm_login_url": resolve_url(settings.LOGIN_URL),
            "gm_logout_url": resolve_url(settings.LOGOUT_URL),
        },
    )
    response["Cache-Control"] = "no-store"
    return response


def _get_only(request: HttpRequest) -> HttpResponse | None:
    if request.method in ("GET", "HEAD"):
        return None
    response = responses.error("method_not_allowed", 405)
    response["Allow"] = "GET, HEAD"
    return response


def session(request: HttpRequest) -> HttpResponse:
    """Current operator identity, server time, and game version."""
    rejected = _get_only(request)
    if rejected is not None:
        return rejected
    try:
        version = game_version()
    except (OSError, ValueError) as exc:  # TOMLDecodeError is a ValueError
        log_error(
            "gm_version_unavailable",
            exc=exc,
            context={"route": route_label(request.path_info), "account": request.user.username},
        )
        return responses.error("version_unavailable", 500)
    user = request.user
    return responses.ok(
        {
            "account_name": user.username,
            "permission_level": "superuser" if user.is_superuser else "Developer",
            "server_time": timezone.localtime().isoformat(),
            "game_version": version,
        }
    )


def dashboard(request: HttpRequest) -> HttpResponse:
    """One read-only operations snapshot with independently failing slots."""
    rejected = _get_only(request)
    if rejected is not None:
        return rejected
    return responses.ok(dashboard_snapshot.build_snapshot())


def llm_call(request: HttpRequest, call_id: str) -> HttpResponse:
    """Retained transcript records for one guarded LLM call.

    Lookup is best-effort (S2a): an empty result is ``transcript_not_found``
    even if some file was unreadable, and available records are returned
    without fabricating missing ones.
    """
    rejected = _get_only(request)
    if rejected is not None:
        return rejected
    if not CALL_ID_PATTERN.match(call_id):
        return responses.error("invalid_call_id", 400)
    try:
        records = transcript.find(call_id)
    except transcript.TranscriptDisabled:  # observability: ignore R2: disabled transcripts are a reported state, answered by the 409 envelope
        return responses.error("transcript_disabled", 409)
    if not records:
        return responses.error("transcript_not_found", 404)
    outcomes = [record for record in records if record.get("kind") == "outcome"]
    exchanges = [record for record in records if record.get("kind") == "exchange"]
    return responses.ok({"outcome": outcomes[-1] if outcomes else None, "exchanges": exchanges})


def api_not_found(request: HttpRequest, rest: str = "") -> HttpResponse:
    """Unknown ``/gm/api`` paths answer with the JSON 404, never the shell."""
    return responses.error("not_found", 404)
