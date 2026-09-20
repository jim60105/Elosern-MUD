"""Deterministic account/character seeding for browser acceptance tests.

Run as a one-off process against a freshly migrated browser-test database:

    ELOSERN_BROWSER_* uv run --locked python -m web.tests.browser.seed

The harness runs ``evennia migrate`` first. This process then creates Account
#1 (the superuser Evennia's launcher requires), an activated
PlayerCharacter owned by that account, a start room, and places the character
in it. The world bootstrap (lore sync, maps, clock) is left to the
managed server's ``at_server_start`` hook. Everything is deterministic: no
network service, no LLM, and no random sampling beyond the validated magic
band seeded to its deterministic lower bound.

Importing this package has no side effects; all setup and database work happens
only when it is executed as ``python -m web.tests.browser.seed`` (``__main__``).

The single-module history is split into modules of a shared surface (the
``web.browser_support.browser_fixtures_data`` package precedent applies
here): ``identity`` holds the deterministic fixture identity and the valid
PNG payload; ``minimap_fixture``, ``art_fixture``, ``services_fixture``
(with the ``services_synth`` synthetic-install variant),
``exploration_fixture``, ``options_surface_fixture`` and ``titles_fixture``
the flag-gated seeding fixtures; ``runner`` the ``main()`` entry point.

Every name resolves through this package's namespace exactly as the single
``web/tests/browser/seed.py`` module exported it: consumers keep importing
``web.tests.browser.seed`` and the harness keeps running
``python -m web.tests.browser.seed``.
"""

# Re-export aliases of the original module's leaked stdlib imports: the
# former single module exposed them at top level, and ``dir()`` parity keeps
# the seams that resolved them working.
import os
from pathlib import Path

from web.tests.browser.seed.identity import (
    BROWSER_ACCOUNT_EMAIL,
    BROWSER_ACCOUNT_PASSWORD,
    BROWSER_ACCOUNT_USERNAME,
    BROWSER_CHARACTER_NAME,
    BROWSER_ROOM_NAME,
    CREATION_ACCOUNT_EMAIL,
    CREATION_ACCOUNT_PASSWORD,
    CREATION_ACCOUNT_USERNAME,
    FIXTURE_VALID_PNG,
)
from web.tests.browser.seed.art_fixture import _art_fixture
from web.tests.browser.seed.exploration_fixture import _exploration_fixture
from web.tests.browser.seed.minimap_fixture import _minimap_fixture
from web.tests.browser.seed.options_surface_fixture import _options_surface_fixture
from web.tests.browser.seed.services_fixture import _services_fixture
from web.tests.browser.seed.services_synth import _services_fixture_synth
from web.tests.browser.seed.titles_fixture import _titles_fixture
from web.tests.browser.seed.runner import main
