"""Disposable settings for the retained monster field-behaviour smoke.

Usage (never against the real development database):

    MUD_SMOKE_DB=/tmp/mud-field-smoke.sqlite3 \
        uv run --locked evennia migrate \
        --settings server.conf.monster_field_behaviour_smoke_settings --noinput
    MUD_SMOKE_DB=/tmp/mud-field-smoke.sqlite3 \
        uv run --locked evennia shell \
        --settings server.conf.monster_field_behaviour_smoke_settings --plain \
        -c "from tools.monster_field_behaviour_smoke import run; run()"
"""

import os

from server.conf.settings import *  # noqa: E402,F401,F403

DATABASES["default"]["NAME"] = os.environ["MUD_SMOKE_DB"]

# The deterministic smoke never reaches a model or image service.
LLM_PROFILES = {
    layer: {**values, "enabled": False} for layer, values in LLM_PROFILES.items()
}
ART_SCHEDULER_ENABLED = False
ART_TRANSLATE_DOWNLOAD_ENABLED = False
