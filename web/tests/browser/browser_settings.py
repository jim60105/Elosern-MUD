"""Browser-test-only Evennia settings module.

Every listening port and filesystem root is read from ``ELOSERN_BROWSER_*``
environment variables prepared by the fixture helpers, so one harness instance
owns a private SQLite database, log/media/static roots, and a distinct set of
loopback ports without touching the developer database or the default
4000/4001/4002 ports.

Evennia's launcher resolves ``--settings <name>`` only under ``server.conf``,
so the thin re-export shim at ``server/conf/browser_settings.py`` imports this
module. The seeding process imports it directly through
``DJANGO_SETTINGS_MODULE=web.tests.browser.browser_settings``.
"""

from evennia.settings_default import *  # noqa: F401, F403

import os


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return int(raw)


def _env_path(name: str, default: str) -> str:
    return os.environ.get(name) or default


SERVERNAME = "Elosern Browser Test"

# The production settings register the project-authored trait types that the
# combat/sexual handlers require; without them any materialization of a
# project trait (for example ``SexualState``'s ``ordered_level``) fails.
TRAIT_CLASS_PATHS = [
    "world.rules.sexual_state.OrderedLevelTrait",
    "world.rules.traits.DeterministicGaugeTrait",
]

# Django requires a SECRET_KEY to be set; a fixed value is fine for an
# isolated loopback test server. The developer's secret_settings are never
# loaded because this module does not import ``server.conf.settings``.
SECRET_KEY = _env_path("ELOSERN_BROWSER_SECRET_KEY", "elosern-browser-test-key")

# Private SQLite database: never ``server/db/evennia.db3``.
DATABASES["default"]["NAME"] = _env_path(
    "ELOSERN_BROWSER_DB", DATABASES["default"]["NAME"]
)

# Loopback-only listening services on dynamic ports.
TELNET_ENABLED = True
TELNET_PORTS = [_env_int("ELOSERN_BROWSER_TELNET_PORT", 4100)]
TELNET_INTERFACES = ["127.0.0.1"]

WEBSERVER_ENABLED = True
WEBSERVER_PORTS = [
    (
        _env_int("ELOSERN_BROWSER_HTTP_PORT", 4101),
        _env_int("ELOSERN_BROWSER_INTERNAL_PORT", 4105),
    )
]
WEBSERVER_INTERFACES = ["127.0.0.1"]

WEBCLIENT_ENABLED = True
WEBSOCKET_CLIENT_ENABLED = True
WEBSOCKET_CLIENT_PORT = _env_int("ELOSERN_BROWSER_WS_PORT", 4102)
WEBSOCKET_CLIENT_INTERFACE = "127.0.0.1"

# The portal/server control channel must also be per-instance so concurrent
# harnesses (or a running developer server) never attach to each other.
AMP_HOST = "localhost"
AMP_INTERFACE = "127.0.0.1"
AMP_PORT = _env_int("ELOSERN_BROWSER_AMP_PORT", 4106)

# Temporary runtime and log roots.
_LOG_DIR = _env_path("ELOSERN_BROWSER_LOG_DIR", LOG_DIR)
LOG_DIR = _LOG_DIR
SERVER_LOG_FILE = os.path.join(_LOG_DIR, "server.log")
SERVER_LOG_DAY_ROTATION = 7
SERVER_LOG_MAX_SIZE = 1000000
PORTAL_LOG_FILE = os.path.join(_LOG_DIR, "portal.log")
PORTAL_LOG_DAY_ROTATION = 7
PORTAL_LOG_MAX_SIZE = 1000000
HTTP_LOG_FILE = os.path.join(_LOG_DIR, "http_requests.log")
LOCKWARNING_LOG_FILE = os.path.join(_LOG_DIR, "lockwarnings.log")
CACHE_DIR = _env_path("ELOSERN_BROWSER_CACHE_DIR", CACHE_DIR)

MEDIA_ROOT = _env_path("ELOSERN_BROWSER_MEDIA_ROOT", MEDIA_ROOT)
STATIC_ROOT = _env_path("ELOSERN_BROWSER_STATIC_ROOT", STATIC_ROOT)

# Art store for browser acceptance: a private temporary root, and a worker
# command that can be pointed at a fixture (or fixed to fail for offline
# journeys) through the environment.
ART_STORE_ROOT = _env_path("ELOSERN_BROWSER_ART_ROOT", os.path.join(CACHE_DIR, "art"))
_ART_WORKER_CMD = os.environ.get("ELOSERN_BROWSER_ART_WORKER_CMD", "")
ART_WORKER_CMD = (
    _ART_WORKER_CMD.split(",")
    if _ART_WORKER_CMD
    else ["python", "-m", "tools.art_worker"]
)
ART_WORKER_TIMEOUT_SECONDS = _env_int("ELOSERN_BROWSER_ART_TIMEOUT", 60)
ART_SCHEDULER_ENABLED = False
ART_SCHEDULER_INTERVAL_SECONDS = 30
ART_SCHEDULER_LIMIT = 4


# ---------------------------------------------------------------------------
# Evennia 6.1 webclient session detection.
#
# Evennia 6.1's WebSocket client calls ``init_session("websocket", ...)``
# (portal/webclient.py), so a real browser session carries
# ``protocol_key == "websocket"``. The project's ``is_webclient`` in
# ``web.webclient.presentation.ingress`` matches the pre-6.1 key
# ``"webclient/websocket"``, which its mock-session tests never exercise.
# The browser-test environment maps both keys so the OOB channel works against
# a real server. This patch lives here (not in the production modules) and is
# active only while this settings module is loaded.
# ---------------------------------------------------------------------------
import web.webclient.presentation.ingress as _ingress  # noqa: E402

_WEBSOCKET_PROTOCOL_KEYS = frozenset({"websocket", "webclient/websocket"})


def _browser_is_webclient(session) -> bool:
    return getattr(session, "protocol_key", None) in _WEBSOCKET_PROTOCOL_KEYS


_ingress.is_webclient = _browser_is_webclient
