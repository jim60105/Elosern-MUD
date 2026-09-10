"""Browser-harness startup-hook wrapper (add-test-synthetic-data-kit, D2b).

Installed as ``AT_SERVER_STARTSTOP_MODULE`` by ``browser_settings`` only when
``ELOSERN_BROWSER_SYNTH_CATALOGS=1``. The synthetic catalogs cannot be applied
while settings load: ``world.tests.synthetic_data`` imports Evennia contrib
code that captures the logger at import time, and the logger only exists after
``evennia._init()``. The first hook Evennia calls is ``at_server_init``, which
runs after that bootstrap and before every startup mirroring step — installing
there means the managed server's ``sync_all``/grid/clock steps all see the
synthetic catalogs, exactly like the ``ART_SD_CLIENT`` fake-client seam. Every
other hook delegates unchanged to the production startstop module.
"""

import os

_PRODUCTION_MODULE = "server.conf.at_server_startstop"


def _install_synthetic_catalogs_if_flagged() -> None:
    if os.environ.get("ELOSERN_BROWSER_SYNTH_CATALOGS") != "1":
        return
    from world.tests.synthetic_data import install_synthetic_catalogs

    install_synthetic_catalogs()


def _production(name):
    import importlib

    module = importlib.import_module(_PRODUCTION_MODULE)
    hook = getattr(module, name, None)
    return hook


def at_server_init():
    _install_synthetic_catalogs_if_flagged()
    hook = _production("at_server_init")
    if hook is not None:
        return hook()


def at_server_start():
    _install_synthetic_catalogs_if_flagged()
    hook = _production("at_server_start")
    if hook is not None:
        return hook()


def at_server_stop():
    hook = _production("at_server_stop")
    if hook is not None:
        return hook()


def at_server_reload_start():
    hook = _production("at_server_reload_start")
    if hook is not None:
        return hook()


def at_server_reload_stop():
    hook = _production("at_server_reload_stop")
    if hook is not None:
        return hook()
