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

import json


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

# Portal WebSocket protocol (production parity): preserves the shared-login
# uid across abnormal closes so the reconnect tests exercise the real
# reconnect-authentication path, not the client's one-shot page reload.
WEBSOCKET_PROTOCOL_CLASS = "server.conf.websocket_protocol.WebSocketClient"

# Vue/legacy XOR load flag (webclient-vue-01-foundation). C4 flipped the
# production default to the Vue SPA, so the browser-test environment mirrors
# that: the default is Vue; set ``ELOSERN_BROWSER_VUE_CLIENT=0`` to explicitly
# select the legacy fallback branch (the rollback / bundle-blocked scenario).
ELOSERN_VUE_CLIENT = os.environ.get("ELOSERN_BROWSER_VUE_CLIENT") != "0"

# Expose the flag to the webclient templates through the project context
# processor (this module does not import server.conf.settings, so the
# registration there does not apply here; the ``?__vue=1`` review fixture
# depends on it in the browser acceptance tests).
TEMPLATES = [
    {
        **engine,
        "OPTIONS": {
            **engine.get("OPTIONS", {}),
            "context_processors": [
                *engine.get("OPTIONS", {}).get("context_processors", []),
                "web.webclient.context_processors.elosern_webclient",
            ],
        },
    }
    for engine in TEMPLATES
]

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
            subrace_key="human_commoner",
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

# ---------------------------------------------------------------------------
# Deterministic action-options client (webclient-options-surface).
#
# Only when the options-surface fixture is opted in
# (``ELOSERN_BROWSER_OPTIONS_SURFACE=1``, set on the harness runtime) does the
# action_options client become a replay double so the suggestions trigger is
# fully deterministic: generations for the options-surface plaza room resolve
# a fixed four-card OptionSet after a short reactor delay (so the transient
# ``generating`` state stays observable by a polling journey), generations
# for the empty-ground room fail with a scripted transport error (the
# memoized degraded path), and any other room matches no fixture and degrades
# exactly like an offline endpoint. No socket is ever opened. Sibling browser
# suites keep the production client (and its plain offline degrade), exactly
# as before this change. The room names below are authored by the seed
# fixture in seed.py.
# ---------------------------------------------------------------------------
import server.option_proposal_service as _options_service  # noqa: E402

PLAZA_ROOM_NAME = "選項測試廣場"
EMPTY_GROUND_ROOM_NAME = "選項測試空地"
SOUTH_GATE_EXIT_KEY = "離開廣場"
_GENERATION_DELAY_SECONDS = 1.5


def _room_matcher(room_name: str):
    """Match a request whose user message names exactly ``room_name``."""
    prefix = "場景名稱：" + room_name

    def matches(descriptor) -> bool:
        return any(
            str(message.get("content") or "").startswith(prefix)
            for message in getattr(descriptor, "messages", ())
        )

    return matches


def _browser_character():
    """The deterministic seeded player character (see seed.py)."""
    from typeclasses.characters import PlayerCharacter

    name = os.environ.get("ELOSERN_BROWSER_CHARACTER", "BrowserTest")
    return PlayerCharacter.objects.filter(db_key=name).first()


def _plaza_option_set_json() -> str | None:
    """Build the fixed plaza OptionSet from the canonical affordances.

    The cards are derived from ``exploration_affordances(actor)`` at call time
    so every ``params`` value (exit ref, npc id, monster id) is byte-identical
    to what the prompt context carries: the schema ladder's exact-match stage
    can never reject the fixture. Returns ``None`` (degrade) when the fixture
    room or any required affordance is absent.
    """
    from web.webclient.presentation.affordances import exploration_affordances

    actor = _browser_character()
    if actor is None or getattr(actor, "location", None) is None:
        return None
    if str(getattr(actor.location, "key", "")) != PLAZA_ROOM_NAME:
        return None
    affordances = exploration_affordances(actor)

    def _pick(action_id, **preds):
        for entry in affordances:
            if entry.action_id != action_id:
                continue
            params = entry.params or {}
            if all(params.get(key) == value for key, value in preds.items()):
                return entry
        return None

    look = _pick("explore.look", room=True)
    engage = _pick("explore.engage")
    freeform = _pick("explore.talk_freeform")
    # The move card names the 離開廣場 exit (its destination is 南門), so the
    # fixture label matches what the player actually walks through. The exit
    # lookup is scoped to the plaza room itself so a same-keyed exit elsewhere
    # can never be picked.
    gate_exit = next(
        (
            exit_obj
            for exit_obj in getattr(actor.location, "exits", ())
            if getattr(exit_obj, "key", None) == SOUTH_GATE_EXIT_KEY
        ),
        None,
    )
    move = (
        _pick("explore.move", exit_ref=str(gate_exit.id))
        if gate_exit is not None
        else None
    )
    if None in (look, move, freeform, engage):
        return None
    cards = [
        {
            "action_code": "explore.look",
            "label": "查看四周",
            "params": dict(look.params),
            "hint": "觀察廣場四周的動靜",
        },
        {
            "action_code": "explore.move",
            "label": "前往南門",
            "params": dict(move.params),
        },
        {
            # The plaza hosts exactly one NPC, so the freeform binding is
            # always npc_index 0 (the context's stable NPC order).
            "npc_index": 0,
            "label": "我們聊聊好嗎？",
            "hint": "對廣場夥伴說出這句話",
        },
        {
            "action_code": "explore.engage",
            "label": "試試身手",
            "params": dict(engage.params),
        },
    ]
    return json.dumps(
        {"context_kind": "exploration", "cards": cards}, ensure_ascii=False
    )


from twisted.internet import reactor  # noqa: E402


class _DeterministicOptionsClient:
    """Replay double with a delayed plaza response and scripted failures.

    Implements the same ``get_response(descriptor)`` protocol as
    ``world.ai.fake_client.FakeLLMClient`` (whose conventions this fixture
    follows): the plaza request fires after ``_GENERATION_DELAY_SECONDS`` so
    the dock's ``generating`` line is observable, the empty-ground request
    errbacks with ``LLMTransportError`` (the memoized degraded path), and any
    other request errbacks with ``MissingFixtureError`` — a plain generation
    failure that degrades without a memo, exactly like an offline endpoint.
    """

    def __init__(self, plaza_text: str | None) -> None:
        self._plaza_text = plaza_text

    def get_response(self, descriptor):
        from twisted.internet import defer
        from twisted.python.failure import Failure

        from world.ai.errors import LLMTransportError
        from world.ai.fake_client import MissingFixtureError

        if _room_matcher(EMPTY_GROUND_ROOM_NAME)(descriptor):
            return defer.fail(
                Failure(LLMTransportError("connection", "simulated offline"))
            )
        if _room_matcher(PLAZA_ROOM_NAME)(descriptor):
            if self._plaza_text is None:
                return defer.fail(Failure(MissingFixtureError("plaza unavailable")))
            result = defer.Deferred()
            reactor.callLater(
                _GENERATION_DELAY_SECONDS,
                lambda: result.callback(self._plaza_text),
            )
            return result
        return defer.fail(Failure(MissingFixtureError("no fixture for this room")))


def _browser_options_client():
    """Deterministic action_options client for the options-surface journeys."""
    try:
        plaza_text = _plaza_option_set_json()
    except Exception:
        plaza_text = None
    return _DeterministicOptionsClient(plaza_text)


if os.environ.get("ELOSERN_BROWSER_OPTIONS_SURFACE") == "1":
    _options_service._build_action_options_client = _browser_options_client
