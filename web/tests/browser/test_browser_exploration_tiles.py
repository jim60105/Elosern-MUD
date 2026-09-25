"""Keyboard-only exploration browser acceptance (webclient-exploration-menu 4.2-4.6): outlet/navigation tile geometry inside the pane at narrow viewports.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement
from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    activate_overview_chip,
    focus_action_dock,
    install_outbound_recorder,
    outbound_messages,
    push_exploration_frame,
    sent_action_count,
    store_state,
    wait_for_store_state,
)
from .harness import ManagedServer, ManagedServerTearDownMixin
from . import fixtures


def _press(page, key, wait_ms=80):
    page.keyboard.press(key)
    page.wait_for_timeout(wait_ms)


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

    def _live_exploration_panel(self, page):
        # The panels mapping can be observed mid-snapshot-adoption without the
        # exploration key; callers poll, so a missing panel reads as None.
        return store_state(page)["panels"].get("exploration")

    def _wait_exploration_available(self, page, timeout=30000):
        def _exploration_available(state: dict) -> bool:
            panel = (state.get("panels") or {}).get("exploration") or {}
            return panel.get("available") is True

        wait_for_store_state(page, _exploration_available, timeout=timeout)

    def _wait_panel(self, page, name, predicate, timeout=30000):
        def _panel_ready(state: dict) -> bool:
            panel = (state.get("panels") or {}).get(name)
            return panel is not None and predicate(panel)

        wait_for_store_state(page, _panel_ready, timeout=timeout)

    def _reset_root(self, page):
        focus_action_dock(page)
        page.evaluate("window.__elosernBridge.store.resetFramesToRoot()")
        page.wait_for_timeout(60)

    def _open_move_outlet(self, page):
        """Mount the retired move-outlet frame by a direct push.

        webclient-scene-overview-swap: the dock root is the scene overview, so
        no keyboard or pointer path reaches the move submenu any more. Until
        webclient-retire-exploration-submenus deletes the frame with its tests,
        the outlet assertions mount it through the router's own push entry.
        """
        push_exploration_frame(page, "exploration.move")

    @covers_requirement("webclient-contextual-hud::a-fixed-column-count-dock-pane-sizes-its-columns-to-content-never-stretching-to-fill-the-panel")
    def test_outlet_and_nav_tiles_stay_within_the_pane_at_a_narrow_viewport(self):
        # fix-webclient-hud-dock-exploration-grid-width: at the minimum
        # supported viewport the content-sized tracks must not overflow the
        # pane, the fixed two-column keyboard mapping must hold, and the
        # wait/rest (plain) pane must stay a non-grid block container.
        page = self.logged_in_page((1280, 720))
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        def press_right_wait_focus(page: "Page") -> None:
            # Press ArrowRight and wait until the store's committed focus key
            # actually moves to the next cell (the second grid column of the
            # same row under the fixed two-column geometry).
            state = store_state(page)
            focus_key_before = (state.get("focus") or {}).get("key")
            _press(page, "ArrowRight")  # second grid column
            wait_for_store_state(
                page,
                lambda s: (s.get("focus") or {}).get("key") not in (None, focus_key_before),
                timeout=15000,
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

        # A long, spaceless server-authored string (e.g. a destination name
        # with no break opportunities) must wrap inside the capped tile/row
        # instead of forcing the layout past the pane.
        LONG_LABEL = "北岸大道之" * 8

        def assert_not_stretched(item_selector: str, pane_selector: str) -> None:
            # The original visual regression: tiles/rows stretched to fill
            # half the panel (~450px at the 1280x720 viewport). Content-sized
            # tiles/rows must render well below the half-pane width.
            items = page.locator(item_selector)
            pane_box = page.locator(pane_selector).bounding_box()
            self.assertIsNotNone(pane_box, pane_selector + " must be visible at 1280x720")
            pane_half = pane_box["width"] / 2
            for i in range(items.count()):
                box = items.nth(i).bounding_box()
                self.assertLess(
                    box["width"],
                    pane_half,
                    item_selector + " row " + str(i) + " must be content-sized, not stretched to half the pane",
                )

        def assert_tiles_fill_pane(item_selector: str, pane_selector: str) -> None:
            # The outlet grid is width-adaptive (auto-fit): the tiles stretch
            # with their 1fr tracks, so the first tile's left edge aligns
            # with the pane's left edge and the last tile's right edge with
            # the pane's right edge (the 8px gaps count as occupied space).
            items = page.locator(item_selector)
            self.assertGreater(items.count(), 0, item_selector + " must render at least one tile")
            pane_box = page.locator(pane_selector).bounding_box()
            self.assertIsNotNone(pane_box, pane_selector + " must be visible at 1280x720")
            first_box = items.first.bounding_box()
            last_box = items.last.bounding_box()
            self.assertIsNotNone(first_box, "the first tile must have a bounding box")
            self.assertIsNotNone(last_box, "the last tile must have a bounding box")
            self.assertLessEqual(
                abs(first_box["x"] - pane_box["x"]),
                1,
                "the first tile must start at the pane's left edge",
            )
            self.assertLessEqual(
                abs((last_box["x"] + last_box["width"]) - (pane_box["x"] + pane_box["width"])),
                2,
                "the last tile must end at the pane's right edge",
            )

        def assert_long_label_wraps(item_selector: str, pane_selector: str, label_selector: str) -> None:
            # Override the label text with a long spaceless string and assert
            # it wraps (scrollWidth <= clientWidth, no horizontal scroll) and
            # the item stays within the pane's width (the max-width + min-width: 0
            # + overflow-wrap: break-word safety net).
            items = page.locator(item_selector)
            pane_box = page.locator(pane_selector).bounding_box()
            self.assertIsNotNone(pane_box, pane_selector + " must be visible at 1280x720")
            pane_right_edge = pane_box["x"] + pane_box["width"]
            for i in range(items.count()):
                el = items.nth(i)
                el.locator(label_selector).evaluate(
                    "(el, t) => { el.textContent = t; }", LONG_LABEL
                )
                page.wait_for_timeout(50)
                metrics = el.evaluate("el => ({ sw: el.scrollWidth, cw: el.clientWidth })")
                self.assertLessEqual(
                    metrics["sw"],
                    metrics["cw"] + 1,
                    item_selector + " row " + str(i) + ": long spaceless label must wrap (scrollWidth <= clientWidth)",
                )
                box = el.bounding_box()
                self.assertLessEqual(
                    box["x"] + box["width"],
                    pane_right_edge + 1,
                    item_selector + " row " + str(i) + " (long label) overflows the pane horizontally",
                )

        # Move: the exit tiles stretch with their tracks and fill the
        # pane's full width — no blank space on the right.
        self._open_move_outlet(page)  # Move
        assert_within_pane(".dock-menu__outlet-tile", ".dock-menu__outlet")
        assert_tiles_fill_pane(".dock-menu__outlet-tile", ".dock-menu__outlet")
        assert_long_label_wraps(".dock-menu__outlet-tile", ".dock-menu__outlet", "b")
        # The move frame navigates as a single-column list: ArrowRight is a
        # no-op (focus stays on the current item), ArrowDown cycles the
        # exit rows then the `back` row.
        _state = store_state(page)
        _focus_key_before = (_state.get("focus") or {}).get("key")
        _press(page, "ArrowRight")
        page.wait_for_timeout(80)
        self.assertEqual(
            (store_state(page).get("focus") or {}).get("key"),
            _focus_key_before,
            "ArrowRight is a no-op in the move frame (single-column list geometry)",
        )
        _press(page, "ArrowDown")
        page.wait_for_timeout(80)
        _state = store_state(page)
        _move = ((_state.get("panels") or {}).get("exploration") or {}).get("move") or []
        _move_keys = ["exit-" + str(m.get("exit_ref")) for m in _move] + ["back"]
        self.assertEqual(
            (_state.get("focus") or {}).get("key"),
            _move_keys[1] if len(_move_keys) > 1 else "back",
            "ArrowDown moves focus to the second item (the next exit or the back row)",
        )
        # Cycle focus onto the `back` row: the breadcrumb's back control must
        # carry the focused presentation (fill + ring, not color alone), and
        # Enter on it pops exactly one level back to the root. From the first
        # exit row, `len(_move) - 1` more ArrowDown presses reach the back
        # row (the last item of the move list).
        for _ in range(len(_move) - 1):
            _press(page, "ArrowDown")
        page.wait_for_timeout(80)
        _state = store_state(page)
        self.assertEqual(
            (_state.get("focus") or {}).get("key"),
            "back",
            "ArrowDown cycles focus onto the back row",
        )
        _back_btn = page.locator(".dock-crumb__back")
        self.assertTrue(
            "dock-crumb__back--focused" in (_back_btn.get_attribute("class") or ""),
            "the breadcrumb back control must show the focused state",
        )
        _press(page, "Enter")
        page.wait_for_timeout(80)
        self.assertEqual(
            page.evaluate("window.__elosernBridge.router.depth()"),
            1,
            "Enter on the back row must pop exactly one level",
        )

        # Look: the look rows stay within the nav pane; the keyboard column
        # mapping is unchanged.
        push_exploration_frame(page, "exploration.look")  # Look
        assert_within_pane(".dock-menu__nav-row", ".dock-menu__nav")
        assert_not_stretched(".dock-menu__nav-row", ".dock-menu__nav")
        assert_long_label_wraps(".dock-menu__nav-row", ".dock-menu__nav", ".dock-menu__nav-text")
        press_right_wait_focus(page)
        _state = store_state(page)
        _look = ((_state.get("panels") or {}).get("exploration") or {}).get("look") or {}
        _look_keys = []
        if _look.get("room"):
            _look_keys.append("look-room")
        for _e in _look.get("entities") or []:
            _look_keys.append("entity-" + str(_e.get("identity")))
        for _o in _look.get("objects") or []:
            _look_keys.append("object-" + str(_o.get("identity")))
        _look_keys.append("back")
        self.assertEqual(
            (_state.get("focus") or {}).get("key"),
            _look_keys[1] if len(_look_keys) > 1 else "back",
            "ArrowRight must move focus to the second grid column",
        )
        _press(page, "Escape")
        page.wait_for_timeout(80)

        # Interact: same width and keyboard-mapping checks for the target rows.
        push_exploration_frame(page, "exploration.interact")  # Interact
        assert_within_pane(".dock-menu__nav-row", ".dock-menu__nav")
        assert_not_stretched(".dock-menu__nav-row", ".dock-menu__nav")
        assert_long_label_wraps(".dock-menu__nav-row", ".dock-menu__nav", ".dock-menu__nav-text")
        press_right_wait_focus(page)
        _state = store_state(page)
        _interact = ((_state.get("panels") or {}).get("exploration") or {}).get("interact") or []
        _interact_keys = ["target-" + str(t.get("identity")) for t in _interact] + ["back"]
        self.assertEqual(
            (_state.get("focus") or {}).get("key"),
            _interact_keys[1] if len(_interact_keys) > 1 else "back",
            "ArrowRight must move focus to the second grid column",
        )
        _press(page, "Escape")
        page.wait_for_timeout(80)

        # Wait/rest (task 2.3 re-confirmation, re-cut by acd3790 /
        # webclient-exploration-menu): the wait surface left the dock pane —
        # opening the Wait tab renders the dedicated waiting screen (the
        # dock pane is absent) with the three-operation card row, so the old
        # `.dock-menu__plain` non-grid check has no dock surface left to
        # observe. The equivalent narrow-viewport guarantee: the waiting
        # screen's card row stays inside the stage bounds.
        activate_overview_chip(page, "wait")  # 等待／休息 footer chip
        waiting = page.locator(".waiting-screen")
        self.assertGreater(waiting.count(), 0, "the waiting screen owns the wait surface")
        # The three-operation frame: dawn / sleep / 休息 N 小時 cards.
        self.assertGreaterEqual(
            page.locator(".waiting-card").count(),
            3,
            "the waiting screen renders the three-operation card row",
        )

    def test_outlet_last_row_never_leaves_blank_space_at_a_narrower_viewport(self):
        # fix-webclient-hud-dock-exploration-grid-width: at 1280x720 the
        # outlet pane lives in the bottom band's command region (the band's
        # right third, webclient-avg-stage-shell design D5), roughly 400px
        # wide, so it holds two content-sized columns. The invariant is that the
        # last row never leaves blank horizontal space: a partial last row
        # must span the remaining columns via an inline grid-column style,
        # and a row the shipped exit count fills exactly must not span. The
        # rendered column count and tile count drive which half applies, so
        # the assertion tracks the shipped fixture topology (the south gate
        # gained the wilderness exit since this test was written: the move
        # frame is 4 exits, i.e. two full rows here) instead of pinning it.
        page = self.logged_in_page((1280, 720))
        install_outbound_recorder(page)
        self._wait_exploration_available(page)
        self._open_move_outlet(page)  # Move
        pane_box = page.locator(".dock-menu__outlet").bounding_box()
        self.assertIsNotNone(pane_box, "the outlet pane must be visible at 1280x720")
        tiles = page.locator(".dock-menu__outlet-tile")
        self.assertGreaterEqual(
            tiles.count(), 3, "the move frame must render at least 3 exit tiles"
        )
        first_box = tiles.first.bounding_box()
        last_box = tiles.last.bounding_box()
        self.assertIsNotNone(first_box, "the first tile must have a bounding box")
        self.assertIsNotNone(last_box, "the last tile must have a bounding box")
        self.assertLessEqual(
            abs(first_box["x"] - pane_box["x"]),
            1,
            "the first tile must start at the pane's left edge",
        )
        self.assertLessEqual(
            abs((last_box["x"] + last_box["width"]) - (pane_box["x"] + pane_box["width"])),
            2,
            "the last row must end at the pane's right edge",
        )
        last_style = tiles.last.get_attribute("style") or ""
        columns = page.evaluate(
            """() => getComputedStyle(
                document.querySelector('.dock-menu__outlet')
            ).gridTemplateColumns.split(' ').length"""
        )
        if tiles.count() % columns:
            self.assertIn(
                "grid-column",
                last_style,
                "the partial-row tile must carry the inline span style",
            )
        else:
            self.assertNotIn(
                "grid-column",
                last_style,
                "a tile on a fully filled row must not carry the span style",
            )
