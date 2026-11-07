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

 With ``ELOSERN_BROWSER_SYNTH_CATALOGS=1`` the process installs the synthetic
 test-data catalogs (``world/tests/synthetic_data/``) before any startup
 world mirroring, so both this module's processes — the one-off seed and the
 managed Evennia server — mirror synthetic content into the private database.
 The seed stays runnable under the flag: its base character activates from the
 kit's own preset card and the shipped-key fixtures (combat grants, monsters)
 are skipped, so the flag is documented as combinable with no other
 fixture-enabling flag. Default-off leaves shipped behavior identical.
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


def _positive_int(name: str, default: int) -> int:
    """A positive integer override; an invalid value fails at import.

    The production settings validate ``GM_AUTOSAVE_KEEP`` the same way, so a
    managed runtime can never silently run with a retention count that would
    prune every automatic save.
    """
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError as error:
        raise ValueError(f"{name} expected a positive integer") from error
    if value < 1:
        raise ValueError(f"{name} expected a positive integer")
    return value


SERVERNAME = "Elosern Browser Test"

# Account capacity: matches production default so multi-character fixtures can create characters
MAX_NR_CHARACTERS = 5

# The quest-owned normalized scene-package store (quest-scene-encounters)
# needs the same database registration as production settings; without it
# the harness database has no quests_* tables, sync_quest_runtime fails at
# boot, and the guild catalog's lazy load then rejects the shipped
# quest_rewards rows against the unpopulated definition registry.
INSTALLED_APPS = list(INSTALLED_APPS) + [
    "world.narrative.apps.NarrativeConfig",
    "world.quests.apps.QuestsConfig",
]
# Production registers the project prototypes and the xyzgrid contrib's
# ``xyz_room`` parent in one list (``server/conf/settings.py``). Sparse
# settlement synchronization flattens each authored node prototype (its
# ``prototype_parent`` is ``grid_room`` → ``xyz_room``) BEFORE any XYMap loads
# and lazily registers the contrib's own prototypes, so this runtime must
# publish the same module list or the deterministic seed fails with
# "Found 0 matching prototypes" on a fresh database.
PROTOTYPE_MODULES = ["world.prototypes", "evennia.contrib.grid.xyzgrid.prototypes"]

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

# World saves (gm-portal-s5-saves): the GM console snapshots the world before
# its first intervention after process start. ``server/saves/snapshot.py``
# derives its layout from the database, save and art roots on every call, so
# the managed runtime binds the save root and the retention count to private
# values with the same meaning as production. The database and art halves of
# every save then live under this invocation's temporary root, never the
# developer's ``server/db/saves`` or ``server/.art``. The fallback derives
# from the resolved browser cache root above, so omitting only the save-root
# override still stays inside the invocation's private tree.
GM_SAVES_ROOT = _env_path(
    "ELOSERN_BROWSER_SAVES_ROOT", os.path.join(CACHE_DIR, "saves")
)
GM_AUTOSAVE_KEEP = _positive_int("ELOSERN_BROWSER_AUTOSAVE_KEEP", 10)

MEDIA_ROOT = _env_path("ELOSERN_BROWSER_MEDIA_ROOT", MEDIA_ROOT)
STATIC_ROOT = _env_path("ELOSERN_BROWSER_STATIC_ROOT", STATIC_ROOT)

# Art store for browser acceptance: a private temporary root, and the internal
# image-generation client pointed at the deterministic fake (dotted path,
# overridable through the environment) so the harness generates images without
# a socket.
ART_STORE_ROOT = _env_path("ELOSERN_BROWSER_ART_ROOT", os.path.join(CACHE_DIR, "art"))

# Operator official-artwork root (official-artwork-catalog). This module does
# not import the production settings, so the knob is declared with the
# production default shape: an uncreated child of the runtime cache directory,
# i.e. the supported "no official artwork" configuration every bundled-art
# journey boots against. A configured-root fault journey sets
# ART_OFFICIAL_ROOT explicitly; normal absence never sets an override.
ART_OFFICIAL_ROOT = _env_path(
    "ART_OFFICIAL_ROOT", os.path.join(CACHE_DIR, "art-official")
)
# The same import-time provenance the production settings capture (this module
# deliberately does not import them). ``runtime.env`` binds ART_OFFICIAL_ROOT
# only for a configured-root fault journey; a normal default-absence boot never
# sets it, so its snapshot keeps the unconfigured meaning.
ART_OFFICIAL_ROOT_EXPLICIT = "ART_OFFICIAL_ROOT" in os.environ
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
# Optional local art-stage knobs: the harness is fully offline and
# deterministic, so each stage stays off and every seam points at a fake
# double — no test loads an optional library or reaches the network. Declared
# like every other art knob because this module deliberately does not import
# the developer settings.
ART_REMBG_ENABLED = False
ART_REMBG_BACKEND = "world.art.fake_cutout.FakeCutoutBackend"
ART_TRANSLATE_ENABLED = False
ART_TRANSLATE_BACKEND = "world.art.fake_translate.FakeTranslator"
# Translation air-gap pin, mirroring server/conf/test_settings.py: this module
# does not import the developer settings, so the knob is declared explicitly —
# the harness can never attempt a model download even if a suite resolves the
# shipped backend against an unseeded model directory.
ART_TRANSLATE_DOWNLOAD_ENABLED = False
ART_SCHEDULER_ENABLED = False
ART_SCHEDULER_INTERVAL_SECONDS = 30
ART_SCHEDULER_LIMIT = 4

# Adult-scene guard for the defeat settlement's violation hook
# (defeat-aftermath-core D-C4): mirrors the production default in
# server/conf/settings.py. This module deliberately does not import the
# developer settings, so every knob the deterministic core reads must be
# declared here.
DEFEAT_ADULT_SCENES = True
# Disable dialogue transport and ordinary room-entry options generation.
# The dedicated options fixture enables its deterministic replay client only.
# Free-form dialogue uses the authored greeting/silence; other browser journeys
# use the options service's rule-card fallback without contacting a live LLM.
from world.ai.profiles import default_profiles  # noqa: E402

_LLM_PROFILES = default_profiles()
_LLM_PROFILES["npc_dialogue"]["enabled"] = False
_LLM_PROFILES["action_options"]["enabled"] = False
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

    from web.browser_support.browser_fixtures_data import (
        SHIPPED_BASE_RACE,
        SHIPPED_BASE_SUBRACE,
        SHIPPED_COMBAT_ACTIVE_SKILLS,
        synth_mode_enabled,
    )

    if synth_mode_enabled():
        # Under the synthetic install the placeholder derives its identity
        # from the live kit registries (race/subrace/budget-fill/skill) via
        # the support module instead of naming any shipped row. Affinity
        # stays empty: an empty set is always legal for every race.
        from web.browser_support.browser_fixtures_data import (
            synth_concept_proposal_values,
        )

        derived = synth_concept_proposal_values()
        return defer.succeed(
            CharacterProposal(
                race_key=derived["race_key"],
                subrace_key=derived["subrace_key"],
                allocations=derived["allocations"],
                suggested_skills=derived["suggested_skills"],
                persona={
                    "personality": "沉穩",
                    "life_story": "來自邊境的小村，靠磨劍維生",
                    "habit": "清晨練劍",
                },
                display_name="燈下學徒",
                age=30,
                apparent_age=27,
                background="在燈下抄書長大的見習劍士。",
                affinity_elements=(),
            )
        )

    return defer.succeed(
        CharacterProposal(
            race_key=SHIPPED_BASE_RACE,
            subrace_key=SHIPPED_BASE_SUBRACE,
            allocations={
                "hp": 50, "mp": 50, "sp": 50,
                "atk_phys": 10, "agility": 10, "defense": 11,
                "magic_power": 43,
            },
            # Shipped-mode placeholder (flag OFF); the skill value rides the
            # support module's shipped grant vocabulary.
            suggested_skills=(SHIPPED_COMBAT_ACTIVE_SKILLS[0],),
            persona={
                "personality": "沉穩",
                "life_story": "來自邊境的小村，靠磨劍維生",
                "habit": "清晨練劍",
            },
            # The v3 transient-fill keys (bump-creation-panel-proposal-v3):
            # already-normalized values as the guarded layer would emit them
            # (in-band ages and texts, human affinity bound of 2).
            display_name="燈下學徒",
            age=30,
            apparent_age=27,
            background="在燈下抄書長大的見習劍士。",
            affinity_elements=("fire", "wind"),
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

# Managed-runtime hook wrapper: every browser runtime installs it, so the
# startup hook can both install the synthetic catalogs (kit design D2b, only
# under ``ELOSERN_BROWSER_SYNTH_CATALOGS=1``: the install runs at
# at_server_init — the first hook Evennia calls, after evennia._init() and
# before any startup mirroring) and converge this runtime's declared
# settlements instead of the whole authored roster
# (``web/tests/browser/browser_startstop`` documents both). Every other hook
# and every shipped-mode step still delegates unchanged, so a runtime booting
# shipped catalogs behaves exactly as before apart from the bounded
# materialization.
AT_SERVER_STARTSTOP_MODULE = "web.tests.browser.browser_startstop"
