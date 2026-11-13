"""Evidence that the gallery wall satisfies its capability contract.

Each test executes the part of the Vitest suite that pins one requirement of
``webclient-gallery-wall`` and fails when that part is red or matches no test.

Test-to-requirement mapping (applied at archive):

- ``the-wall-renders-committed-groups-as-aspect-true-subject-tiles``:
  ``gallery_wall.test.js`` "committed groups as aspect-true subject tiles"
  (group headings and counts, collapsed groups, the 操作中 marker, tile shape).
- ``a-multi-card-subject-opens-a-tray-under-its-row``:
  "the tray under the owner's row" (tray placement after the owner's row,
  one-card subjects, card then generate then official order, scroll on open).
- ``tray-tiles-carry-state-by-shape-and-text``:
  "tray tiles carry state by shape and text" (預設, 生成中, 生成失敗).
- ``the-wall-and-the-tray-are-two-roving-listboxes``:
  "two roving listboxes" (focus versus selection, Enter, Escape, focus loss).
- ``collapsible-group-headings-are-buttons``:
  "collapsible group headings are buttons" (a collapsed heading is a button
  with ``aria-expanded`` emitting ``expand-group`` once, the expanded one
  inert, and tier headings plain while every group is expanded).
- ``scene-tiles-are-landscape-and-open-no-tray``:
  "draws a scene category's tiles landscape and opens no tray for its
  one-card subject" (landscape tiles, no tray, no ``aria-expanded`` on the
  owner tile).
"""

from __future__ import annotations

import re
import unittest

from ._showcase_build import run_npm
from tools.spec_traceability import covers_requirement


def _run_vitest_group(group: str) -> None:
    """Run the ``gallery_wall`` describe block whose name contains ``group``."""
    result = run_npm(
        ["test", "--", "components/gallery_wall", "-t", re.escape(group)],
        timeout=600,
    )
    assert result.returncode == 0, (
        "Vitest suite failed:\n" + result.stdout + result.stderr
    )
    assert re.search(r"\d+ passed", result.stdout), (
        "No gallery wall test ran for " + group + ":\n" + result.stdout
    )


class GalleryWallEvidenceTests(unittest.TestCase):
    @covers_requirement(
        "webclient-gallery-wall::the-wall-renders-committed-groups-as-aspect-true-subject-tiles"
    )
    def test_committed_group_tiles_suite_passes(self):
        """Group headings, collapsed groups, the live marker and tile shapes hold under Vitest."""
        _run_vitest_group("committed groups as aspect-true subject tiles")

    @covers_requirement(
        "webclient-gallery-wall::a-multi-card-subject-opens-a-tray-under-its-row"
    )
    def test_tray_under_owner_row_suite_passes(self):
        """Tray placement, one-card subjects, item order and scrolling hold under Vitest."""
        _run_vitest_group("the tray under the owner")

    @covers_requirement(
        "webclient-gallery-wall::tray-tiles-carry-state-by-shape-and-text"
    )
    def test_tray_tile_state_suite_passes(self):
        """Default, pending and failed tray tiles carry shape and text under Vitest."""
        _run_vitest_group("tray tiles carry state by shape and text")

    @covers_requirement(
        "webclient-gallery-wall::the-wall-and-the-tray-are-two-roving-listboxes"
    )
    def test_two_roving_listboxes_suite_passes(self):
        """Roving focus, activation, Escape and focus loss hold under Vitest."""
        _run_vitest_group("two roving listboxes")

    @covers_requirement(
        "webclient-gallery-wall::collapsible-group-headings-are-buttons"
    )
    def test_collapsible_group_headings_suite_passes(self):
        """Collapsed place headings are buttons; tier headings stay plain under Vitest."""
        _run_vitest_group("collapsible group headings are buttons")

    @covers_requirement(
        "webclient-gallery-wall::scene-tiles-are-landscape-and-open-no-tray"
    )
    def test_scene_tiles_landscape_suite_passes(self):
        """Scene tiles are landscape and a selected scene opens no tray under Vitest."""
        _run_vitest_group("draws a scene category's tiles landscape and opens no tray")
