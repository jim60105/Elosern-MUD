"""Dream-stage journey fixture (change ``unified-dream-rendering``).

Installed only when ``ELOSERN_BROWSER_DREAM_ART=1``. It gives one real dream
journey the OPTIONAL operator-preferred image the stage's first source position
resolves: the exact identity ``npc/dream_goddess/dream-throne.webp`` (the
dream chain's own constant) is written under the runtime official root BEFORE
server startup, so the startup catalog admits it exactly like a deployed
catalog and the committed descriptor carries it at ``scene.operator``.

Nothing else is seeded: the required bundled ``dream_throne`` illustration and
the distinct town terminal are the committed collection, and the sleeper's
physical room is deliberately left alone, so a journey can assert that the
dream inherits no room background. Unset, this module is a no-op and never
affects the unrelated browser suites.
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
    """Write the operator-preferred dream image under the runtime official root."""
    if os.environ.get("ELOSERN_BROWSER_DREAM_ART") != "1":
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
