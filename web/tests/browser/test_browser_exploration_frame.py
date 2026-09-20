"""Keyboard-only exploration browser acceptance (webclient-exploration-menu 4.2-4.6): keyboard movement charging time and refreshing the map, and the move frame/frame resolver following committed state across a real move.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement
from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    focus_action_dock,
    install_outbound_recorder,
    sent_action_count,
    outbound_messages,
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

    def _open_root(self, page, index):
        self._reset_root(page)
        # The exploration root is a single seven-column row (mockup grid), so
        # horizontal arrows move across it; submenus are 2-column grids.
        for _ in range(index):
            _press(page, "ArrowRight")
        _press(page, "Enter")

    @covers_requirement("webclient-exploration-menu::explore-move-traverses-a-re-resolved-exit-through-the-shared-movement-path")
    @covers_requirement("webclient-desktop-shell::the-dock-s-row-region-and-detail-panes-are-direct-children-of-their-host")
    def test_keyboard_move_charges_time_and_refreshes_map(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)
        map_before = store_state(page)["panels"]["local_map"]
        self.assertEqual(map_before["current_node"], "grid:capital_altoria:2:0")
        time_before = store_state(page)["serverTime"]

        self._open_root(page, 0)  # Move
        # remove-redundant-dock-menu-layout: the exit-outlet frame shows no
        # detail pane, so the row region (`.dock-menu`) is the pane host's only
        # dock-menu child — no anonymous layout wrapper, no detail aside.
        self.assertEqual(page.locator(".dock-menu-layout").count(), 0)
        self.assertEqual(
            page.evaluate(
                "() => { const host = document.querySelector('.dock-pane-host');"
                " if (!host) return false;"
                " const kids = Array.from(host.children);"
                " return kids.length === 1 && kids[0].classList.contains('dock-menu'); }"
            ),
            True,
            "the outlet frame renders the row region as the pane host's only child",
        )
        _press(page, "Enter")  # first exit
        try:
            self._wait_panel(
                page,
                "local_map",
                lambda p: p.get("available") is True and p["current_node"] != "grid:capital_altoria:2:0",
                timeout=10000,
            )
            moves_sent = 1
        except AssertionError:
            state = store_state(page)
            last = state.get("lastActionResult")
            self.assertIsNotNone(
                last,
                "no action result was recorded before the map could refresh",
            )
            self.assertEqual(
                last["outcome"],
                "stale",
                "the move did not land and the last result is not a stale rejection",
            )
            # A presentation revision advanced between the client building the
            # action and the server admitting it, so the dispatcher rejected
            # the move as stale (no state change). The client re-synchronizes
            # and asks the user to re-operate; the test emulates that retry
            # by re-selecting the same exit.
            self._open_root(page, 0)
            _press(page, "Enter")
            self._wait_panel(
                page,
                "local_map",
                lambda p: p.get("available") is True and p["current_node"] != "grid:capital_altoria:2:0",
            )
            moves_sent = 2
        self.assertEqual(sent_action_count(page, "explore.move"), moves_sent)
        after = store_state(page)
        self.assertNotEqual(after["panels"]["local_map"]["current_node"], "grid:capital_altoria:2:0")
        self.assertNotEqual(
            after["serverTime"],
            time_before,
            "movement must charge the world clock (design D3)",
        )

    def _wait_admitted_move(self, page, node_before):
        """Dispatch real moves until one is admitted (a presentation revision
        can advance between the view read and admission; the dispatcher then
        answers stale — the same bounded retry the move journey uses)."""
        for _attempt in range(3):
            request_id = self._dispatch_move(page)
            self.assertIsNotNone(request_id)
            try:
                wait_for_store_state(
                    page,
                    lambda s: (s.get("panels") or {}).get("local_map", {}).get("current_node")
                    != node_before,
                    timeout=10000,
                )
                return
            except AssertionError:
                last = store_state(page).get("lastActionResult") or {}
                self.assertEqual(
                    last.get("outcome"),
                    "stale",
                    "the move was neither admitted nor rejected as stale",
                )
                wait_for_store_state(page, lambda s: s["dispatch"]["inFlight"] is None)
        self.fail("three consecutive move dispatches were all answered stale")

    @covers_requirement("webclient-frame-resolution::router-frames-store-descriptors-and-a-focus-key-and-resolve-at-access-time")
    @covers_requirement("webclient-frame-resolution::activation-payloads-read-committed-state-at-dispatch-time")
    def test_open_move_frame_follows_a_committed_move(self):
        """The shipped dock path (the user-visible bug, design doc §2): with
        the 移動 frame open, a committed move must make the RENDERED dock pane
        list the NEW room's exits, and activating a rendered row must submit
        the new `exit_ref`/`current_node`. Against the copy-based router this
        fails red: the open frame keeps the previous room's rows and payloads,
        so the second activation is answered `stale` and the player sees
        nothing."""
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)
        node_before = store_state(page)["panels"]["local_map"]["current_node"]

        self._open_root(page, 0)  # Move — the submenu frame is now current.
        self.assertEqual(
            page.evaluate("() => window.__elosernBridge.router.depth()"),
            2,
            "the move frame did not open",
        )

        def rendered_exit_rows():
            # The REAL pane: the dock row region's rendered rows, in DOM
            # order — not a store copy.
            return page.evaluate(
                "() => Array.from("
                "document.querySelectorAll('#action-dock [data-item-key]'))"
                ".map((el) => el.getAttribute('data-item-key'))"
                ".filter((key) => key.startsWith('exit-'))"
            )

        panel_before = store_state(page)["panels"]["exploration"]
        self.assertEqual(
            rendered_exit_rows(),
            ["exit-" + row["exit_ref"] for row in panel_before["move"]],
            "the freshly opened pane must match the committed room",
        )

        # A real admitted move commits a newer snapshot for the whole room.
        self._wait_admitted_move(page, node_before)
        wait_for_store_state(page, lambda s: s["dispatch"]["inFlight"] is None)
        panel_after = store_state(page)["panels"]["exploration"]
        node_after = store_state(page)["panels"]["local_map"]["current_node"]
        self.assertNotEqual(node_after, node_before)

        # The rendered pane follows the commit on its next render (there is
        # no refresh call on the commit path).
        after_rows = rendered_exit_rows()
        self.assertEqual(
            after_rows,
            ["exit-" + row["exit_ref"] for row in panel_after["move"]],
            "the open move pane still renders the superseded room's exits",
        )

        # Activating a rendered row through the pointer path submits the NEW
        # state's payload.
        moves_before = sent_action_count(page, "explore.move")
        first_key = after_rows[0]
        page.locator(f"#action-dock [data-item-key=\"{first_key}\"]").click()
        page.wait_for_function(
            f"() => window.__elosernSent.filter((m) => m[0] === 'ui_action'"
            " && m[1][0] && m[1][0].action_id === 'explore.move').length"
            f" > {moves_before}",
            timeout=10000,
        )
        envelopes = [
            args[0]
            for cmdname, args, _kw in outbound_messages(page)
            if cmdname == "ui_action" and args and args[0].get("action_id") == "explore.move"
        ]
        self.assertEqual(len(envelopes), moves_before + 1, "the click did not dispatch exactly one move")
        self.assertEqual(
            (envelopes[-1].get("payload") or {}).get("current_node"),
            node_after,
            "the activation submitted the superseded room's current_node",
        )
        self.assertEqual(
            (envelopes[-1].get("payload") or {}).get("exit_ref"),
            panel_after["move"][0]["exit_ref"],
            "the activation submitted the superseded room's exit_ref",
        )

    @covers_requirement("webclient-frame-resolution::frame-descriptors-resolve-to-committed-state-menus-at-access-time")
    @covers_requirement("webclient-frame-resolution::the-descriptor-registry-implements-the-exploration-family-as-a-finite-table")
    @covers_requirement("webclient-frame-resolution::dynamic-rows-and-payloads-are-verbatim-from-the-panel-while-client-owned-navigation-rows-are-reproduced")
    @covers_requirement("webclient-frame-resolution::an-unresolvable-descriptor-yields-the-shared-degradation-marker-with-the-server-authored-reason")
    def test_frame_resolver_follows_committed_state_across_a_real_move(self):
        """The frame resolver registry derives menus at access time (design
        doc D1): a move frame resolved before a real move names the old room;
        re-resolving after the committed snapshot names the new room's exits
        with the new current_node and no stale row."""
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)
        node_before = store_state(page)["panels"]["local_map"]["current_node"]

        def resolve_move_menu():
            return page.evaluate(
                "() => window.__elosernBridge.resolveFrame({ source: 'exploration.move' })"
            )

        before = resolve_move_menu()
        self.assertFalse(before.get("unresolvable", False), f"move frame did not resolve: {before}")
        panel_before = store_state(page)["panels"]["exploration"]
        before_keys = [item["key"] for item in before["items"] if item["key"].startswith("exit-")]
        self.assertEqual(
            before_keys,
            ["exit-" + row["exit_ref"] for row in panel_before["move"]],
            "the resolved frame is exactly the committed room's exit rows",
        )
        self.assertTrue(
            all(
                (item.get("payload") or {}).get("current_node") == node_before
                for item in before["items"]
                if item.get("actionId") == "explore.move"
            ),
            "every enabled row carries the committed current_node",
        )

        # A real move commits a newer snapshot (bounded admission retry).
        self._wait_admitted_move(page, node_before)
        wait_for_store_state(page, lambda s: s["dispatch"]["inFlight"] is None)
        node_after = store_state(page)["panels"]["local_map"]["current_node"]
        self.assertNotEqual(node_after, node_before)

        after = resolve_move_menu()
        self.assertFalse(after.get("unresolvable", False), f"move frame did not re-resolve: {after}")
        panel_after = store_state(page)["panels"]["exploration"]
        after_keys = [item["key"] for item in after["items"] if item["key"].startswith("exit-")]
        self.assertEqual(
            after_keys,
            ["exit-" + row["exit_ref"] for row in panel_after["move"]],
            "the re-resolved frame names the NEW room's exits",
        )
        after_labels = {item["label"] for item in after["items"] if item["key"].startswith("exit-")}
        before_labels = {item["label"] for item in before["items"] if item["key"].startswith("exit-")}
        self.assertNotEqual(
            after_labels,
            before_labels,
            "no row of the superseded room survived the re-resolve",
        )
        self.assertTrue(
            all(
                (item.get("payload") or {}).get("current_node") == node_after
                for item in after["items"]
                if item.get("actionId") == "explore.move"
            ),
            "the re-resolved payloads carry the new committed current_node",
        )

        # The finite table: every exploration source resolves against the live
        # committed snapshot (suggestions degrade iff its envelope status is
        # `unavailable`, the no-pane rule), and resolution is pure: two calls
        # agree deeply and nothing else in the committed state moved. The
        # status read and every resolve must share ONE evaluate round-trip: a
        # ui_update committing between separate CDP calls can flip the
        # suggestions envelope to `unavailable` after its status was sampled,
        # routing the iff below through the wrong branch (the same transport
        # race the purity check documents underneath). Inside one synchronous
        # evaluate the store cannot commit, so each verdict pairs with the
        # exact committed state its resolver saw.
        table = page.evaluate(
            """() => {
              const bridge = window.__elosernBridge;
              const state = bridge.store.view;
              const suggestions =
                ((state.panels.context_actions || {}).suggestions) || {};
              return {
                status: suggestions.status,
                explorationAvailable: Boolean(
                  (state.panels.exploration || {}).available
                ),
                identities: ((state.panels.exploration || {}).interact) || [],
                menus: [
                  "exploration.root",
                  "exploration.move",
                  "exploration.look",
                  "exploration.interact",
                  "exploration.wait",
                  "exploration.suggestions",
                ].map(
                  (source) =>
                    [source, bridge.resolveFrame({ source })]
                ),
              };
            }"""
        )
        status = table["status"]
        for source, menu in table["menus"]:
            if source == "exploration.suggestions" and (
                status == "unavailable" or not table["explorationAvailable"]
            ):
                self.assertTrue(
                    menu.get("unresolvable", False),
                    f"{source} resolved despite the no-pane condition",
                )
            else:
                self.assertFalse(
                    menu.get("unresolvable", False),
                    f"{source} (status {status}) did not resolve: {menu}",
                )
                self.assertTrue(isinstance(menu.get("items"), list) and menu["items"])
        identities = [row["identity"] for row in table["identities"]]
        if identities:
            target_menu = page.evaluate(
                "(id) => window.__elosernBridge.resolveFrame("
                "{ source: 'exploration.target', params: { identity: id } })",
                identities[0],
            )
            self.assertFalse(target_menu.get("unresolvable", False))
        # Purity: a second resolve deep-equals the first, and the committed
        # state is byte-identical across the resolution storm. The capture and
        # both resolutions must share ONE evaluate round-trip: the live server
        # pushes legitimate ui_update snapshots between separate CDP calls, so
        # any before/after pair taken across round-trips races the transport
        # itself. Inside one synchronous evaluate the store cannot commit an
        # unrelated update, so a byte diff here can only be resolver mutation.
        purity = page.evaluate(
            """() => {
              const bridge = window.__elosernBridge;
              const before = JSON.stringify(bridge.store.view);
              const first = bridge.resolveFrame({ source: 'exploration.root' });
              const second = bridge.resolveFrame({ source: 'exploration.root' });
              const after = JSON.stringify(bridge.store.view);
              return { before, first, second, after };
            }"""
        )
        self.assertEqual(
            purity["first"], purity["second"],
            "double resolution against one committed state differs",
        )
        self.assertEqual(
            purity["after"], purity["before"],
            "resolution mutated committed state",
        )
        # Degradation is data: an unregistered source and a lost identity
        # return the shared marker (null reason; no authored message here).
        # (services.board is a REGISTERED source since the services/combat/
        # creation family completed the table — it resolves to the
        # board-empty frame here; the unregistered-source leg names a
        # descriptor the table genuinely does not carry.)
        self.assertEqual(
            {"unresolvable": True, "reason": None},
            page.evaluate("() => window.__elosernBridge.resolveFrame({ source: 'nope.unregistered' })"),
        )
        self.assertEqual(
            {"unresolvable": True, "reason": None},
            page.evaluate(
                "() => window.__elosernBridge.resolveFrame("
                "{ source: 'exploration.target', params: { identity: 'nonexistent-identity' } })"
            ),
        )
