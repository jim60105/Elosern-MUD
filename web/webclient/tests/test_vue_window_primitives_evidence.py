"""Evidence that the shared window primitives satisfy their capability contract.

Each test executes the Vitest suite that pins one requirement of
``webclient-window-primitives`` and fails when that suite is red.

Test-to-requirement mapping (applied at archive):

- ``windowframe-carries-the-drawer-chrome-and-focus-contract``:
  ``window_frame.test.js`` (seal, title, tabs, extras, close; Escape and
  close restore focus to the opener; tab selection through ``IconTabs``).
- ``memberrail-is-a-roving-focus-member-list``: ``member_rail.test.js``
  (order, 倒地 shape-and-text marker, unread name, 空位 entry, arrow keys
  move focus while Enter or Space selects).
- ``listdetail-scrolls-its-columns-independently`` and
  ``actionbar-shows-a-committed-disabled-reason``:
  ``list_detail_action_bar.test.js``.
- ``holdingsstrip-renders-server-facts-only``: ``holdings_strip.test.js``.
- ``primitive-sizing-and-motion-use-tokens``:
  ``window_primitives_styles.test.js`` and ``dock_icons.test.js``.
"""

from __future__ import annotations

import unittest

from ._showcase_build import run_npm
from tools.spec_traceability import covers_requirement


def _run_vitest(*filters: str) -> None:
    result = run_npm(["test", "--", *filters], timeout=600)
    assert result.returncode == 0, (
        "Vitest suite failed:\n" + result.stdout + result.stderr
    )
    assert "passed" in result.stdout


class WindowPrimitivesEvidenceTests(unittest.TestCase):
    @covers_requirement(
        "webclient-window-primitives::windowframe-carries-the-drawer-chrome-and-focus-contract"
    )
    def test_window_frame_suite_passes(self):
        """WindowFrame chrome, Escape/close focus restoration and tabs hold under Vitest."""
        _run_vitest("components/window_frame")

    @covers_requirement(
        "webclient-window-primitives::memberrail-is-a-roving-focus-member-list"
    )
    def test_member_rail_suite_passes(self):
        """MemberRail order, markers and roving focus hold under Vitest."""
        _run_vitest("components/member_rail")

    @covers_requirement(
        "webclient-window-primitives::listdetail-scrolls-its-columns-independently",
        "webclient-window-primitives::actionbar-shows-a-committed-disabled-reason",
    )
    def test_list_detail_and_action_bar_suite_passes(self):
        """ListDetail scroll regions and the ActionBar disabled reason hold under Vitest."""
        _run_vitest("components/list_detail_action_bar")

    @covers_requirement(
        "webclient-window-primitives::holdingsstrip-renders-server-facts-only"
    )
    def test_holdings_strip_suite_passes(self):
        """HoldingsStrip renders only server counts, deltas and enabled gives."""
        _run_vitest("components/holdings_strip")

    @covers_requirement(
        "webclient-window-primitives::primitive-sizing-and-motion-use-tokens"
    )
    def test_style_token_and_glyph_suites_pass(self):
        """Primitive styles use scale and motion tokens and the new glyphs exist."""
        _run_vitest("components/window_primitives_styles", "dock_icons")
