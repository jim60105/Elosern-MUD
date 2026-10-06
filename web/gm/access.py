"""GM access policy: one decision shared by the middleware gate and views.

Every ``/gm/`` page and API requires an authenticated account whose
``check_permstring("Developer")`` passes; superusers pass too. Staff status is
deliberately not a substitute. Pages redirect anonymous visitors to
``LOGIN_URL`` and answer insufficient permission with a 403 page; APIs answer
with the 401 ``unauthenticated`` / 403 ``forbidden`` envelopes.
"""

from __future__ import annotations

import functools
from typing import Any, Callable

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from web.gm import responses
from world.observability import log_warn

GM_PREFIX = "/gm/"
GM_API_ROOT = "/gm/api"

ALLOWED = "allowed"
ANONYMOUS = "anonymous"
FORBIDDEN = "forbidden"

#: Attribute the URL-resolver contract test reads on every GM view callback.
PROTECTED_MARKER = "gm_protected"

#: Event context carries at most this many characters of a request path, so a
#: scanner probing long /gm/ paths cannot inflate every log line.
ROUTE_LABEL_LIMIT = 200


def route_label(path: str) -> str:
    """The request path for event context, truncated to a fixed length."""
    if len(path) <= ROUTE_LABEL_LIMIT:
        return path
    return path[:ROUTE_LABEL_LIMIT] + "…"


def is_gm_path(path: str) -> bool:
    """True for every path under the mounted ``/gm/`` namespace."""
    return path.startswith(GM_PREFIX)


def is_gm_api_path(path: str) -> bool:
    """True for the API root (``/gm/api`` or ``/gm/api/``) and its descendants."""
    return path == GM_API_ROOT or path.startswith(GM_API_ROOT + "/")


def access_decision(user: Any) -> str:
    """Classify ``user`` as allowed, anonymous, or forbidden for the portal."""
    if user is None or not getattr(user, "is_authenticated", False):
        return ANONYMOUS
    if getattr(user, "is_superuser", False):
        return ALLOWED
    check = getattr(user, "check_permstring", None)
    if callable(check) and check("Developer"):
        return ALLOWED
    return FORBIDDEN


def account_label(user: Any) -> str:
    """Account name for event context, or ``anonymous``."""
    if user is None or not getattr(user, "is_authenticated", False):
        return "anonymous"
    return str(getattr(user, "username", "") or "anonymous")


def denial_response(request: HttpRequest, decision: str) -> HttpResponse:
    """Emit ``gm_denied`` and build the page or API refusal for ``decision``."""
    route = request.path_info
    log_warn(
        "gm_denied",
        context={
            "account": account_label(getattr(request, "user", None)),
            "route": route_label(route),
        },
    )
    if is_gm_api_path(route):
        if decision == ANONYMOUS:
            return responses.error("unauthenticated", 401)
        return responses.error("forbidden", 403)
    if decision == ANONYMOUS:
        return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)
    response = render(request, "gm/forbidden.html", status=403)
    response["Cache-Control"] = "no-store"
    return response


def gm_required(view: Callable[..., HttpResponse]) -> Callable[..., HttpResponse]:
    """Wrap a GM view with the portal access policy and mark it protected."""

    @functools.wraps(view)
    def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        decision = access_decision(getattr(request, "user", None))
        if decision != ALLOWED:
            return denial_response(request, decision)
        return view(request, *args, **kwargs)

    # Set after functools.wraps so the marker sits on the wrapper itself; any
    # outer functools.wraps-style decorator copies it along with __dict__.
    setattr(wrapper, PROTECTED_MARKER, True)
    return wrapper
