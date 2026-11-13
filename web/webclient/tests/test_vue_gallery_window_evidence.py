"""Evidence that the gallery window satisfies its capability contract.

Each test executes the part of the Vitest suite that pins one requirement of
``webclient-gallery-window`` and fails when that part is red or matches no
test.

Test-to-requirement mapping (applied at archive):

- ``the-圖庫-tool-opens-the-gallery-window``:
  ``app_client_gallery.test.js`` "opens the window from the 圖庫 tool under the
  gallery drawer key and restores focus on Escape" and "locks the open window
  with the committed reason when the panel becomes unavailable".
- ``the-rail-switches-category-through-the-server``:
  ``gallery_window.test.js`` "the rail switches category through the server"
  (pressed mark before the commit, rejected requests, disabled tabs).
- ``footer-presses-map-to-one-action-or-one-editor``:
  "footer presses map to one action or one editor" (default, official keys,
  in-flight and locked gates, the generate editor).
- ``image-selection-is-client-local-and-follows-the-committed-subject``:
  "initialImage (the selection rule)" and "image selection is client-local and
  follows the committed subject" (default card, vanished image, editors).
- ``focus-is-rescued-and-escape-closes-in-layers``:
  "focus is rescued and Escape closes in layers" (rail rescue, tray to owner
  tile, then close).
"""

from __future__ import annotations

import re
import unittest

from ._showcase_build import run_npm
from tools.spec_traceability import covers_requirement


def _run_vitest_group(*groups: str, suite: str = "components/gallery_window") -> None:
    """Run the Vitest cases named by ``groups`` in the file named by ``suite``."""
    pattern = "|".join(re.escape(group) for group in groups)
    result = run_npm(
        ["test", "--", suite, "-t", pattern],
        timeout=600,
    )
    assert result.returncode == 0, (
        "Vitest suite failed:\n" + result.stdout + result.stderr
    )
    assert re.search(r"\d+ passed", result.stdout), (
        "No test ran for " + pattern + ":\n" + result.stdout
    )


class GalleryWindowEvidenceTests(unittest.TestCase):
    @covers_requirement(
        "webclient-gallery-window::the-圖庫-tool-opens-the-gallery-window"
    )
    def test_tool_opens_the_window_suite_passes(self):
        """The 圖庫 tool opens the drawer-keyed window; an unavailable panel locks it."""
        _run_vitest_group(
            "opens the window from the 圖庫 tool under the gallery drawer key "
            "and restores focus on Escape",
            "locks the open window with the committed reason when the panel "
            "becomes unavailable",
            suite="tests/app_client_gallery",
        )

    @covers_requirement(
        "webclient-gallery-window::the-rail-switches-category-through-the-server"
    )
    def test_rail_category_suite_passes(self):
        """The pressed mark, rejection and disabled tabs hold under Vitest."""
        _run_vitest_group("the rail switches category through the server")

    @covers_requirement(
        "webclient-gallery-window::footer-presses-map-to-one-action-or-one-editor"
    )
    def test_footer_press_suite_passes(self):
        """Footer keys, gates and the generate editor hold under Vitest."""
        _run_vitest_group("footer presses map to one action or one editor")

    @covers_requirement(
        "webclient-gallery-window::image-selection-is-client-local-and-follows-the-committed-subject"
    )
    def test_image_selection_suite_passes(self):
        """The selection rule and vanished-image handling hold under Vitest."""
        _run_vitest_group(
            "initialImage (the selection rule)",
            "image selection is client-local and follows the committed subject",
        )

    @covers_requirement(
        "webclient-gallery-window::focus-is-rescued-and-escape-closes-in-layers"
    )
    def test_focus_and_escape_suite_passes(self):
        """Focus rescue and layered Escape hold under Vitest."""
        _run_vitest_group("focus is rescued and Escape closes in layers")
