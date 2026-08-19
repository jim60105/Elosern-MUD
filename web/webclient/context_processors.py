"""Django context processors for the Elosern WebClient templates.

Exposes the mutually-exclusive Vue/legacy script-load flag (design D4,
``webclient-vue-01-foundation``) to ``base.html``. The flag is a
review-window switch only: the production default is the legacy shell
(``ELOSERN_VUE_CLIENT`` is ``False`` in ``server/conf/settings.py`` and is
flipped to ``True`` by C4), and the ``?__vue=1`` query parameter opts a
single page into the Vue branch for the offline-load browser check (the
design's ``?__vue=1`` fixture / test-routed page).
"""

from django.conf import settings


def elosern_webclient(request):
    """Return the Vue/legacy load flag for the WebClient templates.

    Args:
        request: The Django request (``None`` in non-request render paths,
            where only the configured flag applies).

    Returns:
        dict: The ``webclient_vue_enabled`` template context value.
    """
    enabled = bool(getattr(settings, "ELOSERN_VUE_CLIENT", False))
    if request is not None and request.GET.get("__vue") == "1":
        enabled = True
    return {"webclient_vue_enabled": enabled}
