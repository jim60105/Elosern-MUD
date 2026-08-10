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

# Art store for browser acceptance: a private temporary root, and the internal
# image-generation client pointed at the deterministic fake (dotted path,
# overridable through the environment) so the harness generates images without
# a socket.
ART_STORE_ROOT = _env_path("ELOSERN_BROWSER_ART_ROOT", os.path.join(CACHE_DIR, "art"))
ART_SD_CLIENT = _env_path(
    "ELOSERN_BROWSER_SD_CLIENT",
    "world.art.fake_sd_client.FakeSDWebUIClient",
)
ART_SD_BASE_URL = "http://127.0.0.1:7860"
ART_SD_TIMEOUT_SECONDS = _env_int("ELOSERN_BROWSER_SD_TIMEOUT", 600)
ART_SD_STEPS = 30
ART_SD_CFG_SCALE = 7.0
ART_SD_SAMPLER = ""
ART_SD_SCHEDULER = ""
ART_SD_CHECKPOINT = ""
ART_SD_SCENE_WIDTH = 1344
ART_SD_SCENE_HEIGHT = 768
ART_SD_PORTRAIT_WIDTH = 768
ART_SD_PORTRAIT_HEIGHT = 1024
ART_SD_MAX_RESPONSE_BYTES = 52428800
ART_SD_MAX_IMAGE_DIMENSIONS = 4096
ART_SD_MAX_IMAGE_PIXELS = 16777216
ART_SD_PREPIN_SAMPLES_FORMAT = False
ART_SCHEDULER_ENABLED = False
ART_SCHEDULER_INTERVAL_SECONDS = 30
ART_SCHEDULER_LIMIT = 4
# The browser harness is fully offline: every LLM profile stays enabled for the
# layers that are never called, but ``npc_dialogue`` is disabled so the free-form
# dialogue seam degrades to the authored greeting/silence deterministically with
# no transport attempt. This mirrors the "deterministic game must remain fully
# playable offline" invariant without touching the developer environment.
from world.ai.profiles import default_profiles  # noqa: E402

_LLM_PROFILES = default_profiles()
_LLM_PROFILES["npc_dialogue"]["enabled"] = False
LLM_PROFILES = _LLM_PROFILES


# The concept journey is deterministic: ``creation.concept`` runs the guarded
# ``character_creation`` layer through the composition root, which would
# attempt a live transport in this fully offline harness. A deterministic
# placeholder replaces the proposal call at the composition root so the
# journey exercises the adapter, the fingerprint-protected apply service, the
# concept draft form, and activation end to end without any LLM (the guarded
# layer itself is covered by the unit suites). The Telnet command holds its
# own module-level reference and is unaffected; the WebClient adapter imports
# the function at call time and receives this placeholder.
import server.ai_director_service as _ai_director  # noqa: E402


def _browser_concept_proposal(client=None, *, concept):
    """Return one fixed valid character proposal (deterministic placeholder)."""
    del client, concept
    from twisted.internet import defer

    from world.ai.character_creation import CharacterProposal

    return defer.succeed(
        CharacterProposal(
            race_key="human",
            subrace_key=None,
            allocations={
                "hp": 50, "mp": 50, "sp": 50,
                "atk_phys": 10, "agility": 10, "defense": 11,
            },
            suggested_skills=("flight",),
            persona={
                "personality": "沉穩",
                "life_story": "來自邊境的小村，靠磨劍維生",
                "habit": "清晨練劍",
            },
        )
    )


_ai_director.request_character_proposal = _browser_concept_proposal


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
