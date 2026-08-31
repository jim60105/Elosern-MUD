r"""
Evennia settings file.

The available options are found in the default settings file found
here:

https://www.evennia.com/docs/latest/Setup/Settings-Default.html

Remember:

Don't copy more from the default file than you actually intend to
change; this will make sure that you don't overload upstream updates
unnecessarily.

When changing a setting requiring a file system path (like
path/to/actual/file.py), use GAME_DIR and EVENNIA_DIR to reference
your game folder and the Evennia library folders respectively. Python
paths (path.to.module) should be given relative to the game's root
folder (typeclasses.foo) whereas paths within the Evennia library
needs to be given explicitly (evennia.foo).

If you want to share your game dir, including its settings, you can
put secret game- or server-specific settings in secret_settings.py.

"""

# Use the defaults from Evennia unless explicitly overridden
from evennia.settings_default import *
from collections.abc import Callable
import math
import os
import sys

from django.core.exceptions import ImproperlyConfigured

######################################################################
# Environment-variable override helpers (settings-environment-overrides)
######################################################################

# Truthy/falsy word list for boolean knobs. A bare bool(text) would treat
# "False" as True, so only these explicit words convert; anything else is a
# configuration error, never a truthy accident. Intentionally stricter than
# evennia.settings_default's truthy env parsing — deployment knobs must fail
# loud, not guess.
_ENV_BOOL_TRUE = frozenset({"1", "true", "yes", "on"})
_ENV_BOOL_FALSE = frozenset({"0", "false", "no", "off"})
_ENV_BOOL_RULE = (
    "expected a boolean word (one of 1/true/yes/on/0/false/no/off, "
    "case-insensitive)"
)

def _env_bool_word(text: str) -> bool:
    """Convert a boolean knob word; raises ValueError off the word list."""
    lowered = text.lower()
    if lowered in _ENV_BOOL_TRUE:
        return True
    if lowered in _ENV_BOOL_FALSE:
        return False
    raise ValueError(text)


def _env_str(name: str, default: str = "") -> str:
    """Free-text knob: absent or blank-after-strip yields `default`; present
    content is used stripped. The three generation free-text knobs declare
    the empty string as their "server's default" sentinel, so blank-to-default
    is also their spec-mandated present-but-empty behaviour; the URL knob
    (non-empty default) treats blank as unset."""
    text = os.environ.get(name, "").strip()
    return text or default


def _env_typed(
    name: str,
    convert: Callable[[str], object],
    default: object,
    *,
    minimum: int | float | None = None,
    multiple: int | None = None,
    rule: str,
) -> object:
    """Typed environment override with fail-closed validation.

    Absent, or present-but-blank after stripping, yields `default` (an open
    knob carries no intent and must not poison a typed value). Otherwise the
    stripped value is converted and bounded: `minimum` is an EXCLUSIVE lower
    bound (pass 0 to require positivity; non-finite results are rejected
    first so inf/nan can never slip past the bound), `multiple` requires
    divisibility. Any conversion or bound violation raises
    ImproperlyConfigured naming the variable, quoting the raw value, and
    stating the violated `rule` — a mis-set deployment knob is loud at boot,
    never silently inert.
    """
    raw = os.environ.get(name)
    if raw is None:
        return default
    text = raw.strip()
    if not text:
        return default
    try:
        value = convert(text)
    except ValueError:
        raise ImproperlyConfigured(
            f"setting {name}: invalid environment value '{raw}' ({rule})"
        ) from None
    if isinstance(value, float) and not math.isfinite(value):
        raise ImproperlyConfigured(
            f"setting {name}: invalid environment value '{raw}' ({rule})"
        )
    if minimum is not None and value <= minimum:
        raise ImproperlyConfigured(
            f"setting {name}: invalid environment value '{raw}' ({rule})"
        )
    if multiple is not None and value % multiple:
        raise ImproperlyConfigured(
            f"setting {name}: invalid environment value '{raw}' ({rule})"
        )
    return value


def _env_int(name: str, default: int) -> int:
    """Positive-bound integer knob (zero and negatives fail closed)."""
    return _env_typed(
        name, int, default, minimum=0, rule="expected a positive integer"
    )


def _env_dimension(name: str, default: int) -> int:
    """Scene/portrait dimension: positive multiple of 8 (SDXL contract)."""
    return _env_typed(
        name,
        int,
        default,
        minimum=0,
        multiple=8,
        rule="expected a positive multiple of 8",
    )


def _env_float(name: str, default: float) -> float:
    """Positive-bound float knob."""
    return _env_typed(
        name, float, default, minimum=0, rule="expected a positive float"
    )


def _env_bool(name: str, default: bool) -> bool:
    """Boolean knob from the fixed truthy/falsy word list."""
    return _env_typed(
        name, _env_bool_word, default, rule=_ENV_BOOL_RULE
    )

######################################################################
# Evennia base server config
######################################################################

# This is the name of your game. Make it catchy!
SERVERNAME = "Elosern"

# Keep mutable SQLite state in the dedicated container volume.
DATABASES["default"]["NAME"] = os.path.join(GAME_DIR, "server", "db", "evennia.db3")

# Project-authored Evennia trait types.
TRAIT_CLASS_PATHS = [
    "world.rules.sexual_state.OrderedLevelTrait",
    "world.rules.traits.DeterministicGaugeTrait",
]

# xyzgrid contrib: make the `evennia xyzgrid` CLI and its map prototypes
# available (map-anchor-grid).
EXTRA_LAUNCHER_COMMANDS["xyzgrid"] = "evennia.contrib.grid.xyzgrid.launchcmd.xyzcommand"

# "world.prototypes" is already the settings_default entry; re-list it so the
# contrib's module is appended without duplicating the project module.
PROTOTYPE_MODULES = ["world.prototypes", "evennia.contrib.grid.xyzgrid.prototypes"]

# Portal WebSocket protocol: preserves the shared-login uid across abnormal
# closes so the same browser tab can re-authenticate on reconnect without a
# page reload (server/conf/websocket_protocol.py).
WEBSOCKET_PROTOCOL_CLASS = "server.conf.websocket_protocol.WebSocketClient"

# Generative-layer LLM endpoint profiles (llm-client). Local-first by default:
# base_url derives from OLLAMA_BASE_URL (the compose runtime) or falls back to a
# bare-metal localhost endpoint.
from world.ai.profiles import build_profiles, default_profiles

LLM_PROFILES = default_profiles()

######################################################################
# Deterministic art-assets backend (art-assets)
######################################################################

# Root directory for generated scene/portrait asset outputs. Gitignored and
# mounted at /app/server/.art in the container so it can never shadow the
# importable world/art/ package. Deliberately NOT environment-overridable: a
# mistyped value would silently relocate generated art off the persistent
# volume; the rare nonstandard layout uses secret_settings.py explicitly.
ART_STORE_ROOT = os.path.join(GAME_DIR, "server", ".art")

# ---------------------------------------------------------------------------
# Internal sd-webui client (design D11 amendment: the engine now owns the
# image-generation call instead of shelling out to an external worker).
# ---------------------------------------------------------------------------

# Base URL of the sd-webui / Forge API. Derives from the compose runtime's
# SD_WEBUI_BASE_URL environment variable and falls back to a bare-metal
# localhost endpoint.
ART_SD_BASE_URL = _env_str("SD_WEBUI_BASE_URL", "http://127.0.0.1:7860")

# Bounded wall-clock budget for one txt2img exchange (seconds). sd-webui
# generation is slow; the lease-reclaim bound sizes itself by the worst-case
# batch (ART_SCHEDULER_LIMIT x this timeout + margin).
ART_SD_TIMEOUT_SECONDS = _env_int("ART_SD_TIMEOUT_SECONDS", 600)

# Generation parameters. Empty sampler/scheduler/checkpoint mean "the server's
# default"; when set, the values pass through as sampler_name/scheduler/
# override_settings.sd_model_checkpoint and must match the server's
# enumeration exactly.
ART_SD_STEPS = _env_int("ART_SD_STEPS", 30)
ART_SD_CFG_SCALE = _env_float("ART_SD_CFG_SCALE", 7.0)
ART_SD_SAMPLER = _env_str("ART_SD_SAMPLER", "")
ART_SD_SCHEDULER = _env_str("ART_SD_SCHEDULER", "")
ART_SD_CHECKPOINT = _env_str("ART_SD_CHECKPOINT", "")

# Per-aspect-ratio output sizes (multiples of 8, SDXL-friendly): scenes use
# 16:9 and portraits use 3:4.
ART_SD_SCENE_WIDTH = _env_dimension("ART_SD_SCENE_WIDTH", 1344)
ART_SD_SCENE_HEIGHT = _env_dimension("ART_SD_SCENE_HEIGHT", 768)
ART_SD_PORTRAIT_WIDTH = _env_dimension("ART_SD_PORTRAIT_WIDTH", 768)
ART_SD_PORTRAIT_HEIGHT = _env_dimension("ART_SD_PORTRAIT_HEIGHT", 1024)

# Dotted path of the client class (the swappable seam). Tests and the browser
# harness point this at world.art.fake_sd_client.FakeSDWebUIClient so no test
# ever opens a socket to an image service. Deliberately NOT
# environment-overridable (settings-environment-overrides): an
# environment-controlled import seam would let any inherited process
# environment import arbitrary code at engine startup.
ART_SD_CLIENT = "world.art.sd_worker.SDWebUIClient"

# Resource caps: response body/base64 payload size (bytes), PNG width/height,
# and total pixels. Violations settle records failed with the bounded
# sd_response_too_large / sd_image_dimensions_too_large codes.
ART_SD_MAX_RESPONSE_BYTES = _env_int("ART_SD_MAX_RESPONSE_BYTES", 52428800)
ART_SD_MAX_IMAGE_DIMENSIONS = _env_int("ART_SD_MAX_IMAGE_DIMENSIONS", 4096)
ART_SD_MAX_IMAGE_PIXELS = _env_int("ART_SD_MAX_IMAGE_PIXELS", 16777216)

# Opt-in one-time samples_format=png pre-pin via POST /sdapi/v1/options. The
# pre-pin permanently mutates the shared server's persistent default, so it
# defaults to False and is meant only for a dedicated sd-webui instance.
ART_SD_PREPIN_SAMPLES_FORMAT = _env_bool("ART_SD_PREPIN_SAMPLES_FORMAT", False)

######################################################################
# Prompt library (prompt-library)
######################################################################

# Root directory of the admin-facing prompt data folder, the sole source of
# every LLM prompt the application owns. Overridable via the PROMPT_ROOT
# environment variable for bare-metal or nonstandard layouts; the compose
# runtime bind-mounts the host folder here read-only at /app/prompts.
PROMPT_ROOT = os.environ.get("PROMPT_ROOT", os.path.join(GAME_DIR, "prompts"))

# Periodic queue drain control. When ART_SCHEDULER_ENABLED is False the
# ArtDrainScript never drains; records stay missing/pending and placeholders
# remain.
ART_SCHEDULER_ENABLED = _env_bool("ART_SCHEDULER_ENABLED", True)
ART_SCHEDULER_INTERVAL_SECONDS = _env_int("ART_SCHEDULER_INTERVAL_SECONDS", 30)
ART_SCHEDULER_LIMIT = _env_int("ART_SCHEDULER_LIMIT", 4)

# The periodic art drain Script. It survives reloads and is recreated
# automatically; at_script_creation reads the interval from the settings above.
# When ART_SCHEDULER_ENABLED is False the Script never drains (records remain
# pending and placeholders remain).
GLOBAL_SCRIPTS = {
    "art_drain": {
        "typeclass": "world.art.scheduler.ArtDrainScript",
        "repeats": -1,
        "desc": "Periodic deterministic art-queue drain.",
    },
}


######################################################################
# WebClient Vue SPA load flag (webclient-vue-01-foundation)
######################################################################

# Mutually-exclusive Vue/legacy script-load flag for the webclient template
# (base.html XOR flag, design D4). The production default is the Vue SPA
# (flipped to True by the C4 atomic production flip,
# webclient-vue-10-wire-views-browser); the ``?__vue=1`` query parameter
# still forces the Vue branch per request for the offline-load browser check
# (the design's test-routed page fixture). The ELOSERN_VUE_CLIENT environment
# variable overrides it so an operator can execute the documented emergency
# rollback to the legacy webclient without a rebuild (=off, then restart).
ELOSERN_VUE_CLIENT = _env_bool("ELOSERN_VUE_CLIENT", True)

# Expose the flag to the webclient templates through the project context
# processor (Evennia's general_context does not carry it).
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

######################################################################
# Settings given in secret_settings.py override those in this file.
######################################################################
try:
    from server.conf.secret_settings import *
except ImportError:
    print("secret_settings.py file not found or failed to import.")

# Validate the effective profile map after every settings override, so a
# misconfigured action_options structured-output slot fails at startup rather
# than at the first live call, even when it arrives via secret_settings.
build_profiles(LLM_PROFILES)
