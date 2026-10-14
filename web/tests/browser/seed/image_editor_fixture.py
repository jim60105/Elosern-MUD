"""Image-editor and gallery-row seed fixtures.

Slice of the unified image resolution family; owned by
``unified-image-loading-core`` and extended by ``unified-gallery-image-contract``
for the gallery's v3 row shapes.

Installed only when ``ELOSERN_BROWSER_UNIFIED_IMAGES=1`` (one real committed
original card on the activated player character, written through the production
``world/art/gallery.py`` writers and fixed valid PNG bytes under the runtime art
store, plus the family's bounded test-only transition cmdset) and/or when
``ELOSERN_BROWSER_GALLERY_ROWS=1`` (the v3 official, pending and failed rows).
Every helper here is test-only; the production mutation routes stay
authoritative.

This module deliberately imports the transition helper *inside* the fixture:
``seed/runner.py`` imports it at module import time, before ``django.setup()``,
and the helper's cmdset classes need Evennia's configured settings.
"""

from __future__ import annotations

import os


def _image_editor_fixture(character) -> None:
    """Seed the unified-image editor card and/or the gallery v3 rows."""
    _original_card(character)
    _gallery_rows(character)


def _original_card(character) -> None:
    """Seed one exact original gallery card and the transition cmdset."""
    if os.environ.get("ELOSERN_BROWSER_UNIFIED_IMAGES") != "1":
        return

    from web.browser_support.unified_image_transitions import (
        SEEDED_ORIGINAL_IMAGE_ID,
        append_original_card,
        install_transition_cmdset,
    )
    from web.tests.browser.seed.identity import FIXTURE_VALID_PNG

    subject_key = f"portrait:character:{character.pk}"
    append_original_card(
        subject_key,
        SEEDED_ORIGINAL_IMAGE_ID,
        FIXTURE_VALID_PNG,
        set_default=True,
    )
    install_transition_cmdset(character)
    print(
        "seeded image-editor original card="
        f"{SEEDED_ORIGINAL_IMAGE_ID} subject={subject_key}"
    )


def _gallery_rows(character) -> None:
    """Seed the gallery's v3 official, pending and failed rows with real writers.

    The official row comes from a real operator root: the fixture writes one
    valid PNG plus its manifest under ``ART_OFFICIAL_ROOT`` (which the journey
    sets BEFORE startup) for the puppet's own activated preset key, so the
    server's startup index admits it exactly like a deployed catalog.

    The pending and failed rows attach to the first registered monster subject —
    never the puppet — because a pending row is newest-first and would otherwise
    reorder the puppet's own card rail under the loading-core journeys. Both use
    the production writers (``enqueue_gallery_job``, ``record_error``), so the
    panel projects them exactly as it projects a live request.
    """
    if os.environ.get("ELOSERN_BROWSER_GALLERY_ROWS") != "1":
        return

    from web.browser_support.unified_image_transitions import (
        GALLERY_FAILED_ERROR_CODE,
        GALLERY_PENDING_IMAGE_ID,
        seed_official_content,
        seed_pending_and_failed_rows,
    )

    seeded = seed_official_content(character)
    monster = seed_pending_and_failed_rows()
    print(
        "seeded gallery rows official="
        f"{seeded} pending={GALLERY_PENDING_IMAGE_ID} "
        f"failed={GALLERY_FAILED_ERROR_CODE} monster={monster}"
    )
