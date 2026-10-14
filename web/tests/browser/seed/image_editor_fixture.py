"""Image-editor seed fixture.

Slice of the unified image resolution family; owned by
``unified-image-loading-core``.

Installed only when ``ELOSERN_BROWSER_UNIFIED_IMAGES=1``. It appends one real
committed original card to the activated player character's gallery record —
through the production ``world/art/gallery.py`` writers, never a client-injected
business snapshot — writes fixed valid PNG bytes under the runtime art store,
and installs the family's bounded test-only transition cmdset, so the browser
journey drives the real face-rectangle editor over a real gallery card. Every
helper here is test-only; the production mutation routes stay authoritative.

This module deliberately imports the transition helper *inside* the fixture:
``seed/runner.py`` imports it at module import time, before ``django.setup()``,
and the helper's cmdset classes need Evennia's configured settings.
"""

from __future__ import annotations


def _image_editor_fixture(character) -> None:
    """Seed one exact original gallery card and the transition cmdset."""
    import os

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
