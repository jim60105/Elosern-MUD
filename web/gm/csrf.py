"""CSRF failure view: GM API rejections speak the JSON envelope.

Installed as ``CSRF_FAILURE_VIEW``. Only the GM API namespace changes; every
other path keeps Django's stock failure page.
"""

from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.views.csrf import csrf_failure as django_csrf_failure

from web.gm import responses
from web.gm.access import is_gm_api_path


def csrf_failure(request: HttpRequest, reason: str = "", **kwargs) -> HttpResponse:
    """403 ``csrf_failed`` envelope for GM APIs; Django's page elsewhere."""
    if is_gm_api_path(request.path_info):
        return responses.error("csrf_failed", 403)
    return django_csrf_failure(request, reason=reason, **kwargs)
