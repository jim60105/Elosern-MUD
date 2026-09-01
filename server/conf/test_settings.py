"""Explicit settings for local and CI Evennia test runs."""

import os
import sys

from django.core.exceptions import ImproperlyConfigured


if os.environ.get("MUD_TEST_SETTINGS") != "1" or sys.argv[1:2] != ["test"]:
    raise ImproperlyConfigured(
        "server.conf.test_settings is restricted to test commands with "
        "MUD_TEST_SETTINGS=1"
    )

# The production settings derive their initial values from the environment
# (settings-environment-overrides). A test run must never inherit a
# developer's or CI runner's deployment shell, so pop every env-backed
# override name before star-importing those settings: the effective settings
# under test are exactly the documented code defaults. The override-name
# inventory test in server/conf/tests/test_env_overrides.py keeps this list
# in lockstep with settings.py.
_ENV_OVERRIDES = (
    "SD_WEBUI_BASE_URL",
    "ART_SD_TIMEOUT_SECONDS",
    "ART_SD_STEPS",
    "ART_SD_CFG_SCALE",
    "ART_SD_SAMPLER",
    "ART_SD_SCHEDULER",
    "ART_SD_CHECKPOINT",
    "ART_SD_STYLES",
    "ART_SD_MODULES",
    "ART_SD_SCENE_WIDTH",
    "ART_SD_SCENE_HEIGHT",
    "ART_SD_PORTRAIT_WIDTH",
    "ART_SD_PORTRAIT_HEIGHT",
    "ART_SD_MAX_RESPONSE_BYTES",
    "ART_SD_MAX_IMAGE_DIMENSIONS",
    "ART_SD_MAX_IMAGE_PIXELS",
    "ART_SD_PREPIN_SAMPLES_FORMAT",
    "ART_SD_OUTPUT_FORMAT",
    "ART_SD_OUTPUT_QUALITY",
    "ART_SD_PRESERVE_GENERATION_METADATA",
    "ART_SD_PROBE_TIMEOUT_MS",
    "ART_SD_PROBE_CACHE_SECONDS",
    "ART_SCHEDULER_ENABLED",
    "ART_SCHEDULER_INTERVAL_SECONDS",
    "ART_SCHEDULER_LIMIT",
    "ELOSERN_VUE_CLIENT",
)

for _name in _ENV_OVERRIDES:
    os.environ.pop(_name, None)

# Every generated LLM knob name (23 globals + 23 per layer for seven layers)
# is sanitized too, via the inert knob table so no second list can drift. The
# literal _ENV_OVERRIDES tuple above stays literal-only: the AST inventory
# extractor recognises just that tuple.
from server.conf.llm_knobs import llm_env_names

for _llm_name in llm_env_names():
    os.environ.pop(_llm_name, None)

from server.conf.settings import *  # noqa: E402,F401,F403


PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
DATABASES["default"].setdefault("TEST", {})["NAME"] = os.path.join(
    GAME_DIR,
    "server",
    "db",
    "evennia-test.sqlite3",
)
