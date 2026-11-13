"""Evidence that the gallery image page satisfies its capability contract.

Each test executes the part of the Vitest suite that pins one requirement of
``webclient-gallery-image-page`` and fails when that part is red or matches no
test.

Test-to-requirement mapping (applied at archive):

- ``the-footer-follows-the-declared-capabilities``:
  ``gallery_image_page.test.js`` "galleryFooter (the footer follows the
  declared capabilities)" (button order, 設為預設 versus 目前預設, one-card
  kinds with and without deletion).
- ``non-card-selections-have-fixed-footers``:
  "galleryFooter (non-card selections have fixed footers)" (pending, failed,
  empty subject, read-only and current official entries).
- ``deletion-takes-two-steps``: "deletion takes two steps" (arming, cancel,
  Escape, changed selection, confirmation emits once).
- ``the-page-renders-committed-facts-in-cells``: "committed facts in cells"
  and "galleryRibbon" (cells, chips, conditions, description, ribbon).
- ``scene-selections-use-the-landscape-page``:
  "the landscape page of a scene" (a bundled scene's 官方內建圖 and 生成新圖,
  a stored card's 生成圖 with 刪除 and 重新生成, and the description beside
  the facts).
"""

from __future__ import annotations

import re
import unittest

from ._showcase_build import run_npm
from tools.spec_traceability import covers_requirement


def _run_vitest_group(*groups: str) -> None:
    """Run the ``gallery_image_page`` describe blocks named by ``groups``."""
    pattern = "|".join(re.escape(group) for group in groups)
    result = run_npm(
        ["test", "--", "components/gallery_image_page", "-t", pattern],
        timeout=600,
    )
    assert result.returncode == 0, (
        "Vitest suite failed:\n" + result.stdout + result.stderr
    )
    assert re.search(r"\d+ passed", result.stdout), (
        "No gallery image page test ran for " + pattern + ":\n" + result.stdout
    )


class GalleryImagePageEvidenceTests(unittest.TestCase):
    @covers_requirement(
        "webclient-gallery-image-page::the-footer-follows-the-declared-capabilities"
    )
    def test_capability_footer_suite_passes(self):
        """Capability buttons, order and the default card's reason hold under Vitest."""
        _run_vitest_group("the footer follows the declared capabilities")

    @covers_requirement(
        "webclient-gallery-image-page::non-card-selections-have-fixed-footers"
    )
    def test_fixed_footer_suite_passes(self):
        """Pending, failed, empty and official footers hold under Vitest."""
        _run_vitest_group("non-card selections have fixed footers")

    @covers_requirement(
        "webclient-gallery-image-page::deletion-takes-two-steps"
    )
    def test_two_step_deletion_suite_passes(self):
        """Arming, cancel, Escape and confirmation hold under Vitest."""
        _run_vitest_group("deletion takes two steps")

    @covers_requirement(
        "webclient-gallery-image-page::the-page-renders-committed-facts-in-cells"
    )
    def test_committed_fact_cells_suite_passes(self):
        """Fact cells, chips, conditions, description and ribbon hold under Vitest."""
        _run_vitest_group("committed facts in cells", "galleryRibbon")

    @covers_requirement(
        "webclient-gallery-image-page::scene-selections-use-the-landscape-page"
    )
    def test_scene_landscape_page_suite_passes(self):
        """Bundled and generated scene labels, footers and column layout hold under Vitest."""
        _run_vitest_group("the landscape page of a scene")
