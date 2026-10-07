"""GM URL map, mounted at ``/gm/`` by ``web/urls.py``.

Register views ONLY through :func:`gm_path`, which applies ``gm_required``;
the URL-resolver contract test fails on any unwrapped pattern. Concrete API
routes come first, then the API-root and API-descendant 404 fallbacks, and
only then the page-history catch-all, so no ``api`` path reaches the shell.
"""

from __future__ import annotations

from typing import Any, Callable

from django.urls import URLPattern, path

from web.gm import views
from web.gm.access import gm_required


def gm_path(route: str, view: Callable[..., Any], name: str | None = None) -> URLPattern:
    """``django.urls.path`` with the GM access policy applied."""
    return path(route, gm_required(view), name=name)


urlpatterns = [
    gm_path("api/session", views.session, name="gm-api-session"),
    gm_path("api/dashboard", views.dashboard, name="gm-api-dashboard"),
    gm_path("api/llm/calls/<str:call_id>", views.llm_call, name="gm-api-llm-call"),
    gm_path("api", views.api_not_found),
    gm_path("api/", views.api_not_found),
    gm_path("api/<path:rest>", views.api_not_found),
    gm_path("", views.shell, name="gm-shell"),
    gm_path("<path:rest>", views.shell),
]
