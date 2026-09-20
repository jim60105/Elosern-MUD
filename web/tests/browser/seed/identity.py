"""Deterministic browser-fixture identity values.

Slice of the former ``web/tests/browser/seed.py`` module;
every value ships verbatim."""

import os
from pathlib import Path

# Deterministic fixture identity. Password is fixed so Playwright can log in.
BROWSER_ACCOUNT_USERNAME = os.environ.get("ELOSERN_BROWSER_ACCOUNT", "browserplayer")
BROWSER_ACCOUNT_EMAIL = "browser@example.test"
BROWSER_ACCOUNT_PASSWORD = os.environ.get(
    "ELOSERN_BROWSER_PASSWORD", "ElosernBrowserTest!2026"
)
BROWSER_CHARACTER_NAME = os.environ.get("ELOSERN_BROWSER_CHARACTER", "BrowserTest")
BROWSER_ROOM_NAME = os.environ.get("ELOSERN_BROWSER_ROOM", "測試起點")

# A minimal valid 4x4 RGB PNG so a ``done`` art record's media URL actually
# decodes in the browser. Image-load-failure journeys abort this URL on the
# wire; the bytes must stay valid for the rendering journeys to pass.
FIXTURE_VALID_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000004000000040802000000"
    "269309290000001049444154789c6338d0e000470cc4710078521801"
    "1ec406c00000000049454e44ae426082"
)


# The pending-creation login account (webclient-character-creation-ui). A
# separate NON-superuser account keeps the pending shell's ownership intact:
# Evennia's one-time initial setup swaps the superuser account's typeclass with
# clean_attributes=True, which wipes _playable_characters on the superuser
# account and, because the server caches that account in process memory, an
# external repair cannot refresh it.
CREATION_ACCOUNT_USERNAME = os.environ.get("ELOSERN_BROWSER_CREATION_ACCOUNT", "browsercreator")
CREATION_ACCOUNT_EMAIL = "creation@example.test"
CREATION_ACCOUNT_PASSWORD = os.environ.get(
    "ELOSERN_BROWSER_CREATION_PASSWORD", "CreationBrowserTest!2026"
)
