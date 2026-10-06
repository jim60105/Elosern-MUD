"""GM views: the SPA shell and the two S1 read-only APIs.

Every view is registered through ``web.gm.urls.gm_path`` (``gm_required``).
The session and health endpoints are GET-only and change no state; health
performs one real database read and never probes LLM or SD services.
"""

from __future__ import annotations

from django.conf import settings
from django.db import DatabaseError
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, resolve_url
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_safe
from evennia.accounts.models import AccountDB

from web.gm import responses
from web.gm.access import route_label
from web.gm.version import game_version
from world.observability import log_error, log_warn


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


def health(request: HttpRequest) -> HttpResponse:
    """Skeleton health: Django responding and the database readable."""
    rejected = _get_only(request)
    if rejected is not None:
        return rejected
    try:
        # One bounded primary-key read against a real table.
        list(AccountDB.objects.order_by().values_list("id", flat=True)[:1])
    except DatabaseError as exc:
        log_warn(
            "gm_health_database_unreadable",
            exc=exc,
            context={"route": route_label(request.path_info), "account": request.user.username},
        )
        return responses.error("database_unreadable", 503)
    return responses.ok({"django": "ok", "database": "readable"})


def api_not_found(request: HttpRequest, rest: str = "") -> HttpResponse:
    """Unknown ``/gm/api`` paths answer with the JSON 404, never the shell."""
    return responses.error("not_found", 404)
