"""Pre-startup official-content preparation for the browser journeys.

The official artwork root is READ-ONLY to the running game: no production
module resolves a write path under ``ART_OFFICIAL_ROOT`` (the
``art-offline-contract`` invariant). The one legitimate writer is this seed
package, which runs in the journey process *before* the server boots, exactly
like an operator deploying a catalog: the bytes and their manifest land under
the journey's configured ``ART_OFFICIAL_ROOT`` and the startup index then
admits them through the ordinary read-only catalog path.

This module owns that preparation for the unified-image family's gallery rows
slice. It is test-only (under ``web/tests``) and never part of the production
command surface.
"""

from __future__ import annotations

import os
from pathlib import Path

# The manifest-declared filename of the seeded operator content directory.
GALLERY_OFFICIAL_FILENAME = "a.png"
GALLERY_MANIFEST_FILENAME = "manifest.json"


def seed_official_content(character) -> str | None:
    """Write one real operator content directory for the character's own preset key.

    The bytes and their manifest land under the journey's configured
    ``ART_OFFICIAL_ROOT`` BEFORE server startup, so the startup index admits
    them exactly like a deployed catalog and the gallery's official rows come
    from the real snapshot. ``None`` when the character declares no preset
    provenance or the journey configured no official root.

    A character whose activation path wrote no (or an unregistered) preset
    provenance is given the fixture vocabulary's own preset key for the boot
    mode (checked through the public ``registered_content_key`` resolver, never
    a second registry mirror): a preset-born character's reference IS its
    provenance, so the journey exercises the real resolver rather than a
    synthetic shortcut.
    """
    import json

    from django.conf import settings

    from world.art.official_refs import (
        PRESET_PROVENANCE_ATTRIBUTE,
        registered_content_key,
    )
    from web.browser_support.browser_fixtures_data import (
        SHIPPED_PRESET_KEY,
        synth_mode_enabled,
    )
    from web.tests.browser.seed.identity import FIXTURE_VALID_PNG

    root = os.environ.get("ART_OFFICIAL_ROOT") or str(
        getattr(settings, "ART_OFFICIAL_ROOT", "") or ""
    )
    if not root:
        return None
    key = character.attributes.get(PRESET_PROVENANCE_ATTRIBUTE)
    if (
        not isinstance(key, str)
        or not key
        or not registered_content_key("preset", key)
    ):
        key = "t_pale_wren" if synth_mode_enabled() else SHIPPED_PRESET_KEY
        character.attributes.add(PRESET_PROVENANCE_ATTRIBUTE, key)
    folder = Path(root) / "preset" / key
    folder.mkdir(parents=True, exist_ok=True)
    (folder / GALLERY_OFFICIAL_FILENAME).write_bytes(FIXTURE_VALID_PNG)
    (folder / GALLERY_MANIFEST_FILENAME).write_text(
        json.dumps({"default": GALLERY_OFFICIAL_FILENAME}), encoding="utf-8"
    )
    return f"preset/{key}/{GALLERY_OFFICIAL_FILENAME}"
