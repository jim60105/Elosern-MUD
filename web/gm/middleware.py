"""GM request boundary: early access gate plus the ``gm_request`` event.

Django runs every ``process_view`` hook (``CsrfViewMiddleware`` included)
only after the whole middleware ``__call__`` chain has been entered, so
returning a denial from ``__call__`` here gives anonymous and unauthorized
GM API requests their 401/403 envelopes before CSRF validation. The class is
appended last to ``MIDDLEWARE`` so Evennia's ``SharedLoginMiddleware`` has
already mapped a webclient session onto the website login.

Every GM API request emits exactly one ``gm_request`` with its final status,
after the inner chain (CSRF rejections, fallbacks, view errors converted to
responses) has produced it. Pages emit only ``gm_denied`` on refusal.
"""

from __future__ import annotations

from typing import Callable

from django.db import DatabaseError
from django.http import HttpRequest, HttpResponse

from web.gm import responses
from web.gm.access import (
    ALLOWED,
    access_decision,
    account_label,
    denial_response,
    is_gm_api_path,
    is_gm_path,
    route_label,
)
from world.observability import log_info, log_warn


class GmBoundaryMiddleware:
    """Gate ``/gm/`` before CSRF view processing and log GM API outcomes."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        path = request.path_info
        if not is_gm_path(path):
            return self.get_response(request)
        user = getattr(request, "user", None)
        try:
            # Resolving the lazy session user reads the database.
            decision = access_decision(user)
        except DatabaseError as exc:
            if not is_gm_api_path(path):
                raise
            log_warn(
                "gm_access_unavailable",
                exc=exc,
                context={"route": route_label(path), "method": request.method},
            )
            response = responses.error("database_unreadable", 503)
            self._log_request(request, "unknown", path, response)
            return response
        if decision != ALLOWED:
            response = denial_response(request, decision)
        else:
            response = self.get_response(request)
        if is_gm_api_path(path):
            self._log_request(request, account_label(user), path, response)
        return response

    @staticmethod
    def _log_request(request: HttpRequest, account: str, path: str, response: HttpResponse) -> None:
        log_info(
            "gm_request",
            context={
                "account": account,
                "route": route_label(path),
                "method": request.method,
                "status": response.status_code,
            },
        )
