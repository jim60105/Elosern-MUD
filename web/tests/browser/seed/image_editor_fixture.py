"""Image-editor and gallery-row seed fixtures.

Slice of the unified image resolution family; owned by
``unified-image-loading-core`` and extended by ``unified-gallery-image-contract``
for the gallery's v3 row shapes and by ``unified-portrait-image-contract`` for
the portrait descriptor mode.

Installed only when ``ELOSERN_BROWSER_UNIFIED_IMAGES=1`` (one real committed
original card on the activated player character, written through the production
``world/art/gallery.py`` writers and fixed valid PNG bytes under the runtime art
store, plus the family's bounded test-only transition cmdset), and/or when
``ELOSERN_BROWSER_GALLERY_ROWS=1`` (the v3 official, pending and failed rows),
and/or when ``ELOSERN_BROWSER_PORTRAIT_DESCRIPTORS=1`` (the portrait mode: the
player's own roster portrait, one co-located live party companion, one focused
present entity and one combat participant all admitted to the same bounded art
view, plus the ``revoke_source`` availability transition). Every helper here is
test-only; the production mutation routes stay authoritative.

This module deliberately imports the transition helper *inside* the fixture:
``seed/runner.py`` imports it at module import time, before ``django.setup()``,
and the helper's cmdset classes need Evennia's configured settings.
"""

from __future__ import annotations

import os


def _image_editor_fixture(character) -> None:
    """Seed the unified-image editor card, the gallery v3 rows and the portrait mode."""
    _original_card(character)
    _gallery_rows(character)
    _portrait_descriptors(character)


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


def _portrait_descriptors(character) -> None:
    """Seed the portrait mode: one admitted real portrait for every figure scope.

    The player's own activated character gets one real committed card (its
    roster row therefore resolves a real candidate), and a co-located live
    party companion plus a present focus entity and one combat participant are
    admitted to the same bounded art view so a journey can assert that the
    roster figure, the party row, the focus standee, the dialogue host and the
    combat row all read ONE canonical descriptor shape. The bounded
    ``revoke_source`` transition is installed with the same cmdset the editor
    mode uses, so a journey can take the real candidate away and watch every
    surface fall back to the descriptor's own committed alpha terminal.
    """
    if os.environ.get("ELOSERN_BROWSER_PORTRAIT_DESCRIPTORS") != "1":
        return

    from web.browser_support.unified_image_transitions import (
        PORTRAIT_COMPANION_IMAGE_ID,
        PORTRAIT_COMPANION_KEY,
        PORTRAIT_FOCUS_KEY,
        PORTRAIT_IMAGE_ID,
        append_original_card,
        install_transition_cmdset,
        seed_portrait_companions,
    )
    from web.tests.browser.seed.identity import FIXTURE_VALID_PNG

    subject_key = f"portrait:character:{character.pk}"
    append_original_card(subject_key, PORTRAIT_IMAGE_ID, FIXTURE_VALID_PNG, set_default=True)
    install_transition_cmdset(character)
    seeded = seed_portrait_companions(character)
    print(
        "seeded portrait descriptors "
        f"player={subject_key} image={PORTRAIT_IMAGE_ID} "
        f"companion={PORTRAIT_COMPANION_KEY} focus={PORTRAIT_FOCUS_KEY} "
        f"companions={seeded} companion_image={PORTRAIT_COMPANION_IMAGE_ID}"
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
