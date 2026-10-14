"""Unified scene journey fixtures (change ``unified-scene-rendering``).

Installed only when ``ELOSERN_BROWSER_UNIFIED_SCENES=1``. It gives one real
scene journey everything the room-aware chain needs, all of it through the
owners that really produce it:

* the activated character's room carries the authored scene metadata supported
  map construction writes — a registered archetype, a bounded logical place
  identity and a REGISTERED per-room operator override key;
* that override's operator content directory (``room/<key>/``) and the scene's
  own operator directory (``scene/<archetype>/``) are written under the
  runtime official root BEFORE server startup, so the startup catalog admits
  them exactly like a deployed catalog;
* the family's bounded test-only transition cmdset is installed, so a journey
  can drive real pending/failed/done regenerations, a binding removal and a
  move through the ordinary command line.

Every helper here is test-only; the production writers stay authoritative.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

# The manifest filename the operator catalog parses (its own convention).
MANIFEST_FILENAME = "manifest.json"
OPERATOR_FILENAME = "a.png"


def _operator_directory(root: str, kind: str, key: str) -> str:
    """Write one real operator content directory and return its image identity."""
    folder = Path(root) / kind / key
    folder.mkdir(parents=True, exist_ok=True)
    from web.tests.browser.seed.identity import FIXTURE_VALID_PNG

    (folder / OPERATOR_FILENAME).write_bytes(FIXTURE_VALID_PNG)
    (folder / MANIFEST_FILENAME).write_text(
        json.dumps({"default": OPERATOR_FILENAME}), encoding="utf-8"
    )
    return f"{kind}/{key}/{OPERATOR_FILENAME}"


def _scene_fixture(character) -> None:
    """Seed the unified scene mode: authored metadata, operator art, transitions."""
    if os.environ.get("ELOSERN_BROWSER_UNIFIED_SCENES") != "1":
        return
    from django.conf import settings

    from world.art.scene_definitions import ROOM_ART_KEY_SET, is_registered_room_art_key
    from web.browser_support.unified_image_transitions import (
        SCENE_FIXTURE_IDENTITY_PREFIX,
        install_transition_cmdset,
    )

    room = character.location
    if room is None or not getattr(room, "scene_archetype", None):
        raise AssertionError("the scene fixture needs the art room's scene archetype")

    # The authored metadata the map owner writes: a registered room-art key for
    # the override, a bounded logical place identity, and the archetype the room
    # already carries.
    keys = sorted(ROOM_ART_KEY_SET)
    if not keys:
        raise AssertionError("no authored room-art key is registered")
    room_art_key = keys[0]
    if not is_registered_room_art_key(room_art_key):
        raise AssertionError(f"{room_art_key!r} is not a registered room-art key")
    room.room_art_key = room_art_key
    room.scene_identity = f"{SCENE_FIXTURE_IDENTITY_PREFIX}{character.pk}"

    root = os.environ.get("ART_OFFICIAL_ROOT") or str(
        getattr(settings, "ART_OFFICIAL_ROOT", "") or ""
    )
    if not root:
        raise AssertionError("the unified scene mode needs a runtime official root")
    _operator_directory(root, "room", room_art_key)
    _operator_directory(root, "scene", room.scene_archetype)

    _seed_engageable_monster(character)
    install_transition_cmdset(character)
    print(f"seeded unified scene fixture: room_art_key={room_art_key}")


def _seed_engageable_monster(character) -> None:
    """One present monster the art panel admits AND the combat contract accepts.

    The scene journeys change mode through the production ``explore.engage``
    action, so the room needs a monster the panel's catalog really admits (a
    named portrait policy gives it a monster subject instead of the
    unavailable-entity placeholder) and that carries a live threat tier.
    """
    from evennia.utils.create import create_object

    from typeclasses.monsters import Monster
    from web.browser_support.browser_fixtures_data import (
        SHIPPED_MONSTER_TIER_ATTR,
        SHIPPED_MONSTER_TIER_KEY,
        scene_fixture_monster_key,
    )

    monster = create_object(
        Monster,
        key=scene_fixture_monster_key(),
        location=character.location,
        nohome=True,
    )
    monster.threat_tier = SHIPPED_MONSTER_TIER_ATTR
    monster.apply_monster_tier(SHIPPED_MONSTER_TIER_KEY)
    monster.traits.hp.base = 24
    monster.traits.hp.current = 24
    monster.db.portrait_policy = {
        "mode": "named",
        "stable_key": f"browser-scene-monster-{character.pk}",
    }
    monster.save()
