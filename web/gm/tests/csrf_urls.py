"""Test-only URL map: the real project URLs plus one protected GM POST view.

S1 ships no production write endpoint, so the CSRF convention is exercised
against this view, mounted under ``/gm/api/`` (so the real boundary
middleware and CSRF failure view apply) only through ``override_settings``.
"""

from django.urls import path
from django.views.decorators.http import require_POST

from web.gm import responses
from web.gm.access import gm_required
from web.urls import urlpatterns as project_urlpatterns


@require_POST
def protected_write(request):
    return responses.ok({"accepted": True})


urlpatterns = [path("gm/api/_test/write", gm_required(protected_write))] + project_urlpatterns
