"""Explicit settings for local and CI Evennia test runs."""

import os
import sys

from django.core.exceptions import ImproperlyConfigured


if os.environ.get("MUD_TEST_SETTINGS") != "1" or sys.argv[1:2] != ["test"]:
    raise ImproperlyConfigured(
        "server.conf.test_settings is restricted to test commands with "
        "MUD_TEST_SETTINGS=1"
    )

from server.conf.settings import *  # noqa: E402,F401,F403


PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
DATABASES["default"].setdefault("TEST", {})["NAME"] = os.path.join(
    GAME_DIR,
    "server",
    "db",
    "evennia-test.sqlite3",
)
