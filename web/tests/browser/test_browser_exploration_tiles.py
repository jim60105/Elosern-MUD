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


class ExplorationBrowserTest(ManagedServerTearDownMixin, BrowserAcceptanceTest):
    """Boots one dedicated isolated server per test with the exploration fixture."""
    @classmethod
    def setUpClass(cls) -> None:
        pass

    def setUp(self) -> None:
        runtime = fixtures.create_runtime()
        runtime.env["ELOSERN_BROWSER_EXPLORATION"] = "1"
        # Boot mode: SHIPPED catalogs (explicit override of the harness
        # synthetic default, per the creation/action-feedback precedent).
        # These journeys assert shipped fixture identity end to end and were
        # never migrated to kit seams.
        runtime.env["ELOSERN_BROWSER_SYNTH_CATALOGS"] = "0"

        self.server = ManagedServer(runtime=runtime)
        self.server.start()
        self.base_url = f"http://127.0.0.1:{self.server.runtime.http_port}"
        self.webclient_url = self.server.runtime.webclient_url
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

    @covers_requirement("webclient-exploration-menu::the-keyboard-first-exploration-dock-roots-at-the-scene-overview-and-opens-dialogue-directly")
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
            last_box["y"],
            pane_box["y"] - 1,
            "the focused last chip must be scrolled into the pane",
        )
        self.assertLessEqual(
            last_box["y"] + last_box["height"],
            pane_box["y"] + pane_box["height"] + 1,
            "the focused last chip must be scrolled into the pane",
        )
        self.assertEqual(
            sent_action_count(page), 0, "focusing a chip submits nothing"
        )

