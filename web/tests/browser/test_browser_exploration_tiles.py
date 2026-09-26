"""Keyboard-only exploration browser acceptance (webclient-exploration-menu 4.2-4.6): the scene overview's chip wrapping and the fixed-column nav pane's track sizing at narrow viewports.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement
from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    install_outbound_recorder,
    sent_action_count,
    valid_local_map_panel,
    store_state,
    wait_for_store_state,
)
from ._journey_support import (
    _exploration_panel,
    _move_row,
    _exploration_context_actions_panel,
    _inject_snapshot,
    _wait_mode,
    _press,
)
from .harness import ManagedServer, ManagedServerTearDownMixin
from . import fixtures


def _keyword_target(identity: int, name: str, keywords: list) -> dict:
    """One schema-valid interact target carrying the scripted-talk affordance.

    The target's `keywords` are the rows the 交談 frame resolves (the
    scripted-keyword list), so the frame is a real pushed nav pane.
    """
    return {
        "identity": identity,
        "display_name": name,
        "portrait_ref": None,
        "affordances": [
            {
                "kind": "action",
                "action_id": "explore.talk_scripted",
                "label": "交談",
                "enabled": True,
                "disabled_reason": None,
            }
        ],
        "keywords": [{"keyword_id": key, "label": label} for key, label in keywords],
    }


class ExplorationBrowserTest(ManagedServerTearDownMixin, BrowserAcceptanceTest):
    """Boots one dedicated isolated server per test with the exploration fixture."""
    @classmethod
    def setUpClass(cls) -> None:
        pass

    def setUp(self) -> None:
        runtime = fixtures.create_runtime()
        self.server = ManagedServer(runtime)
        self.server.start()
        super().setUp()

    def _wait_exploration_available(self, page, timeout=30000):
        def _exploration_available(state: dict) -> bool:
            panel = (state.get("panels") or {}).get("exploration") or {}
            return panel.get("available") is True

        wait_for_store_state(page, _exploration_available, timeout=timeout)

    def _mount_overview(self, page, exploration: dict, suggestions: dict) -> None:
        """Commit one synthetic exploration panel and settle on the overview."""
        _inject_snapshot(
            page,
            {
                "exploration": exploration,
                "context_actions": _exploration_context_actions_panel(suggestions),
                "local_map": valid_local_map_panel(),
            },
            mode="exploration",
        )
        _wait_mode(page, "exploration")

    @covers_requirement("webclient-exploration-menu::the-exploration-dock-is-keyboard-first-and-roots-at-the-scene-overview")
    def test_overview_chips_wrap_inside_the_pane_at_a_narrow_viewport(self):
        """The scene overview's chips wrap by width inside the command region.

        At the minimum supported viewport a room with many exits renders its
        chips as wrapping rows inside the scrolling pane: no chip overflows the
        pane horizontally, the reading order is unchanged, and the last chip is
        reachable by scrolling (the dock pane is the single scrolling region).
        """
        page = self.logged_in_page((1280, 720))
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        labels = ["北", "南", "東", "西", "東北", "西北", "東南", "西南", "上", "下", "櫃檯門", "後院小徑"]
        exits = [
            _move_row("e%d" % index, label, "room:%d" % (100 + index))
            for index, label in enumerate(labels)
        ]
        self._mount_overview(
            page,
            _exploration_panel([], move_rows=exits),
            {"status": "unavailable"},
        )

        pane = page.locator("#action-dock .action-dock__pane")
        chips = page.locator("#action-dock .scene-chip")
        # Twelve exit chips plus the footer's 查看房間 and 等待／休息 chips.
        self.assertEqual(chips.count(), 14, "the overview renders one chip per entry")
        pane_box = pane.bounding_box()
        self.assertIsNotNone(pane_box, "the dock pane must be visible at 1280x720")

        # The reading order is unchanged: the exits lead, the footer closes.
        keys = page.evaluate(
            "() => Array.from(document.querySelectorAll('#action-dock .scene-chip'))"
            ".map((el) => el.getAttribute('data-item-key'))"
        )
        self.assertEqual(
            keys,
            ["exit-" + row["exit_ref"] for row in exits] + ["look-room", "wait"],
            "the overview's chips keep their reading order",
        )

        # No chip overflows the pane horizontally, and the chips wrap into more
        # than one row (the fixed 2-column grid is gone with the outlet).
        tops = set()
        for index in range(chips.count()):
            box = chips.nth(index).bounding_box()
            self.assertIsNotNone(box, "chip %d must have a bounding box" % index)
            self.assertLessEqual(
                box["x"] + box["width"],
                pane_box["x"] + pane_box["width"] + 1,
                "chip %d overflows the pane horizontally" % index,
            )
            self.assertGreaterEqual(
                box["x"], pane_box["x"] - 1, "chip %d starts left of the pane" % index
            )
            tops.add(round(box["y"]))
        self.assertGreater(
            len(tops), 1, "the chips must wrap into more than one row at 1280x720"
        )

        # The last chip is reachable by scrolling: focusing it (the real
        # keyboard path) scrolls it into the pane's visible box.
        last_key = "exit-" + exits[-1]["exit_ref"]
        self.assertTrue(
            page.evaluate(
                "(key) => window.__elosernBridge.store.focusItemByKey(key)", last_key
            ),
            "the last exit chip must be focusable by its key",
        )
        page.wait_for_timeout(150)
        last_box = chips.last.bounding_box()
        self.assertIsNotNone(last_box, "the last chip must have a bounding box")
        self.assertGreaterEqual(
            last_box["top"],
            pane_box["top"] - 1,
            "the focused last chip must be scrolled into the pane",
        )
        self.assertLessEqual(
            last_box["bottom"],
            pane_box["bottom"] + 1,
            "the focused last chip must be scrolled into the pane",
        )
        self.assertEqual(
            sent_action_count(page), 0, "focusing a chip submits nothing"
        )

    @covers_requirement("webclient-contextual-hud::a-fixed-column-dock-pane-sizes-its-columns-to-content")
    def test_fixed_column_nav_pane_sizes_its_tracks_to_content(self):
        """The fixed-column nav pane sizes its tracks to content.

        The scripted-keyword frame (the exploration family's remaining
        fixed-column pane) keeps the two-column keyboard mapping while its
        columns stay content-sized: no row stretches to half the pane, a long
        spaceless label wraps inside its row, and nothing overflows the pane at
        the minimum supported viewport.
        """
        page = self.logged_in_page((1280, 720))
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        target = _keyword_target(
            11,
            "小販",
            [("問路", "問路"), ("價錢", "價錢"), ("傳聞", "傳聞")],
        )
        self._mount_overview(
            page,
            _exploration_panel([target]),
            {"status": "unavailable"},
        )

        # The person chip -> the verb popover -> 交談: the scripted-keyword
        # frame, two levels deep (webclient-scene-overview-swap).
        page.evaluate(
            "() => window.__elosernBridge.store.focusItemByKey('target-11')"
        )
        page.keyboard.press("Enter")
        page.wait_for_selector('[data-testid="verb-popover"]', timeout=15000)
        page.keyboard.press("Enter")  # 交談
        page.wait_for_selector("#action-dock .dock-menu__nav", timeout=15000)
        self.assertEqual(
            page.evaluate("window.__elosernBridge.router.depth()"),
            3,
            "the scripted-keyword frame did not open",
        )

        def assert_within_pane(item_selector: str, pane_selector: str) -> None:
            items = page.locator(item_selector)
            self.assertGreater(
                items.count(), 0, item_selector + " must render at least one row"
            )
            pane_box = page.locator(pane_selector).bounding_box()
            self.assertIsNotNone(pane_box, pane_selector + " must be visible at 1280x720")
            pane_right_edge = pane_box["x"] + pane_box["width"]
            for i in range(items.count()):
                box = items.nth(i).bounding_box()
                self.assertIsNotNone(
                    box, item_selector + " row " + str(i) + " must have a bounding box"
                )
                self.assertLessEqual(
                    box["x"] + box["width"],
                    pane_right_edge + 1,
                    item_selector + " row " + str(i) + " overflows the pane horizontally",
                )
                self.assertGreaterEqual(
                    box["x"],
                    pane_box["x"] - 1,
                    item_selector + " row " + str(i) + " starts left of the pane",
                )

        def assert_not_stretched(item_selector: str, pane_selector: str) -> None:
            # The original visual regression: rows stretched to fill half the
            # panel (~450px at the 1280x720 viewport). Content-sized rows must
            # render well below the half-pane width.
            items = page.locator(item_selector)
            pane_box = page.locator(pane_selector).bounding_box()
            self.assertIsNotNone(pane_box, pane_selector + " must be visible at 1280x720")
            pane_half = pane_box["width"] / 2
            for i in range(items.count()):
                box = items.nth(i).bounding_box()
                self.assertLess(
                    box["width"],
                    pane_half,
                    item_selector
                    + " row "
                    + str(i)
                    + " must be content-sized, not stretched to half the pane",
                )

        def assert_long_label_wraps(item_selector: str, pane_selector: str, label_selector: str) -> None:
            # Override the label text with a long spaceless string and assert it
            # wraps (scrollWidth <= clientWidth, no horizontal scroll) and the
            # row stays within the pane's width.
            items = page.locator(item_selector)
            pane_box = page.locator(pane_selector).bounding_box()
            self.assertIsNotNone(pane_box, pane_selector + " must be visible at 1280x720")
            pane_right_edge = pane_box["x"] + pane_box["width"]
            for i in range(items.count()):
                el = items.nth(i)
                el.locator(label_selector).evaluate(
                    "(el, t) => { el.textContent = t; }", "北岸大道之" * 8
                )
                page.wait_for_timeout(50)
                metrics = el.evaluate("el => ({ sw: el.scrollWidth, cw: el.clientWidth })")
                self.assertLessEqual(
                    metrics["sw"],
                    metrics["cw"] + 1,
                    item_selector
                    + " row "
                    + str(i)
                    + ": long spaceless label must wrap (scrollWidth <= clientWidth)",
                )
                box = el.bounding_box()
                self.assertLessEqual(
                    box["x"] + box["width"],
                    pane_right_edge + 1,
                    item_selector + " row " + str(i) + " (long label) overflows the pane",
                )

        assert_within_pane(".dock-menu__nav-row", ".dock-menu__nav")
        assert_not_stretched(".dock-menu__nav-row", ".dock-menu__nav")
        assert_long_label_wraps(
            ".dock-menu__nav-row", ".dock-menu__nav", ".dock-menu__nav-text"
        )

        # The fixed two-column keyboard mapping still holds: ArrowRight moves
        # focus onto the second cell of the row (the second keyword).
        state = store_state(page)
        self.assertEqual((state.get("focus") or {}).get("key"), "kw-問路")
        _press(page, "ArrowRight")
        wait_for_store_state(
            page,
            lambda s: (s.get("focus") or {}).get("key") == "kw-價錢",
            timeout=15000,
        )
        self.assertEqual(
            sent_action_count(page), 0, "arrow-key navigation submits nothing"
        )
