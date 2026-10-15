"""Dream-stage journey fixture (change ``unified-dream-rendering``).

Two independent, test-only opt-ins, both unset by default:

* ``ELOSERN_BROWSER_DREAM=1`` moves the character into a fresh room holding no
  living monster, because the committed sleep preflight refuses a time skip
  beside one (``world.rules.skip_safety``) and the shared seed room hosts the
  combat fixtures' monsters. The room carries no authored scene metadata, so
  the journey's "the dream inherits no physical-room background" assertion is a
  real claim about the room the player is actually in.
* ``ELOSERN_BROWSER_DREAM_ART=1`` additionally writes the OPTIONAL
  operator-preferred image the stage's first source position resolves: the exact
  identity ``npc/dream_goddess/dream-throne.webp`` (the dream chain's own
  constant) under the runtime official root BEFORE server startup, so the
  startup catalog admits it exactly like a deployed catalog and the committed
  descriptor carries it at ``scene.operator``.

Nothing else is seeded: the required bundled ``dream_throne`` illustration and
the distinct town terminal are the committed collection. Unset, this module is
a no-op and never affects the unrelated browser suites.
"""

from __future__ import annotations

import os
from io import BytesIO
from pathlib import Path

# The admitted image's decoded size. Any shape the operator catalog admits
# works here; a landscape frame matches how the stage presents it.
_IMAGE_SIZE = (1600, 900)


def _fixture_webp() -> bytes:
    """A real, decodable WebP the operator catalog admits at the exact identity.

    The preferred identity's extension is ``.webp``, so the bytes must be a
    WebP and not the shared PNG fixture: the catalog serves the identity it
    indexed, and the browser decodes what the route returns.
    """
    from PIL import Image

    buffer = BytesIO()
    Image.new("RGB", _IMAGE_SIZE, (214, 218, 231)).save(buffer, format="WEBP")
    return buffer.getvalue()


def _dream_art_fixture(character) -> None:
    """Seed the safe dream room and, when flagged, the preferred official image."""
    safe_room = os.environ.get("ELOSERN_BROWSER_DREAM") == "1"
    preferred_art = os.environ.get("ELOSERN_BROWSER_DREAM_ART") == "1"
    if not safe_room and not preferred_art:
        return
    if safe_room:
        from evennia.utils.create import create_object
        from typeclasses.rooms import Room

        room = create_object(Room, key="夢境測試起點")
        character.location = room
        character.save()
        print(f"seeded dream room {room.key} ({room.pk})")
    if not preferred_art:
        return
    from django.conf import settings

    from world.art.scene_definitions import DREAM_PREFERRED_OFFICIAL_IDENTITY

    root = os.environ.get("ART_OFFICIAL_ROOT") or str(
        getattr(settings, "ART_OFFICIAL_ROOT", "") or ""
    )
    if not root:
        raise AssertionError("the dream artwork fixture needs a runtime official root")
    target = Path(root) / DREAM_PREFERRED_OFFICIAL_IDENTITY
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(_fixture_webp())
    print(
        "seeded dream artwork fixture "
        f"identity={DREAM_PREFERRED_OFFICIAL_IDENTITY} bytes={target.stat().st_size}"
    )
