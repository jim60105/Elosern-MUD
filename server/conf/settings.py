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

# Generative-layer LLM endpoint profiles (llm-client). Local-first by default:
# base_url derives from OLLAMA_BASE_URL (the compose runtime) or falls back to a
# bare-metal localhost endpoint.
from world.ai.profiles import default_profiles

LLM_PROFILES = default_profiles()

######################################################################
# Deterministic art-assets backend (art-assets)
######################################################################

# Root directory for generated scene/portrait asset outputs. Gitignored and
# mounted at /app/server/.art in the container so it can never shadow the
# importable world/art/ package.
ART_STORE_ROOT = os.path.join(GAME_DIR, "server", ".art")

# External worker command executed for every claimed art batch. JSON lines in
# on stdin, JSON lines out on stdout; overridable by settings and pointed at a
# fixture command in tests. The worker implementation itself (local SD, a
# prompt-writing agent, or a fixture) is external to the engine and outside
# this change's code; the module is the design's swap point.
ART_WORKER_CMD = [sys.executable, "-m", "tools.art_worker"]

# Bounded wall-clock budget for one worker invocation (seconds).
ART_WORKER_TIMEOUT_SECONDS = 60

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
# Settings given in secret_settings.py override those in this file.
######################################################################
try:
    from server.conf.secret_settings import *
except ImportError:
    print("secret_settings.py file not found or failed to import.")
