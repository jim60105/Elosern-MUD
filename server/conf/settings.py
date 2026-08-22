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
import os
import sys

######################################################################
# Evennia base server config
######################################################################

# This is the name of your game. Make it catchy!
SERVERNAME = "evennia-skeleton"

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
# importable world/art/ package.
ART_STORE_ROOT = os.path.join(GAME_DIR, "server", ".art")

# ---------------------------------------------------------------------------
# Internal sd-webui client (design D11 amendment: the engine now owns the
# image-generation call instead of shelling out to an external worker).
# ---------------------------------------------------------------------------

# Base URL of the sd-webui / Forge API. Derives from the compose runtime's
# SD_WEBUI_BASE_URL environment variable and falls back to a bare-metal
# localhost endpoint.
ART_SD_BASE_URL = os.environ.get("SD_WEBUI_BASE_URL", "http://127.0.0.1:7860")

# Bounded wall-clock budget for one txt2img exchange (seconds). sd-webui
# generation is slow; the lease-reclaim bound sizes itself by the worst-case
# batch (ART_SCHEDULER_LIMIT x this timeout + margin).
ART_SD_TIMEOUT_SECONDS = 600

# Generation parameters. Empty sampler/scheduler/checkpoint mean "the server's
# default"; when set, the values pass through as sampler_name/scheduler/
# override_settings.sd_model_checkpoint and must match the server's
# enumeration exactly.
ART_SD_STEPS = 30
ART_SD_CFG_SCALE = 7.0
ART_SD_SAMPLER = ""
ART_SD_SCHEDULER = ""
ART_SD_CHECKPOINT = ""

# Per-aspect-ratio output sizes (multiples of 8, SDXL-friendly): scenes use
# 16:9 and portraits use 3:4.
ART_SD_SCENE_WIDTH = 1344
ART_SD_SCENE_HEIGHT = 768
ART_SD_PORTRAIT_WIDTH = 768
ART_SD_PORTRAIT_HEIGHT = 1024

# Dotted path of the client class (the swappable seam). Tests and the browser
# harness point this at world.art.fake_sd_client.FakeSDWebUIClient so no test
# ever opens a socket to an image service.
ART_SD_CLIENT = "world.art.sd_worker.SDWebUIClient"

# Resource caps: response body/base64 payload size (bytes), PNG width/height,
# and total pixels. Violations settle records failed with the bounded
# sd_response_too_large / sd_image_dimensions_too_large codes.
ART_SD_MAX_RESPONSE_BYTES = 52428800
ART_SD_MAX_IMAGE_DIMENSIONS = 4096
ART_SD_MAX_IMAGE_PIXELS = 16777216

# Opt-in one-time samples_format=png pre-pin via POST /sdapi/v1/options. The
# pre-pin permanently mutates the shared server's persistent default, so it
# defaults to False and is meant only for a dedicated sd-webui instance.
ART_SD_PREPIN_SAMPLES_FORMAT = False

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
ART_SCHEDULER_ENABLED = True
ART_SCHEDULER_INTERVAL_SECONDS = 30
ART_SCHEDULER_LIMIT = 4

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
# (the design's test-routed page fixture).
ELOSERN_VUE_CLIENT = True

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
