"""Keyboard-only exploration browser acceptance (webclient-exploration-menu 4.2-4.6).

These journeys drive the real Evennia server's exploration dock: movement
through ``explore.move`` with matching clock/map updates, look that preserves
the onboarding beat, scripted keyword dialogue, free-form dialogue with offline
degrade, engage-to-combat, wait/rest daypart and duration with safety
rejections, stale/duplicate/tampered rejections, the no-take/drop rule, and
reconnect retention.

Each exploration journey boots its own dedicated isolated server so the mutated
character state never leaks into another journey. All fixtures are
deterministic; no remote, LLM, or image service is involved.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    focus_action_dock,
    install_outbound_recorder,
    sent_action_count,
    store_state,
    wait_for_store_state,
)
from .harness import ManagedServer
from . import fixtures


def _press(page, key, wait_ms=80):
    page.keyboard.press(key)
    page.wait_for_timeout(wait_ms)


def _connected_active(state: dict) -> bool:
    """Gate on the client being connected and in the active presentation phase."""
    return bool(state.get("connected")) and state.get("phase") == "active"


class ExplorationBrowserTest(BrowserAcceptanceTest):
    """Boots one dedicated isolated server per test with the exploration fixture."""

    @classmethod
    def setUpClass(cls) -> None:
        pass

    def setUp(self) -> None:
        runtime = fixtures.create_runtime()
        runtime.env["ELOSERN_BROWSER_EXPLORATION"] = "1"
        self.server = ManagedServer(runtime=runtime)
        self.server.start()
        self.base_url = f"http://127.0.0.1:{self.server.runtime.http_port}"
        self.webclient_url = self.server.runtime.webclient_url
        super().setUp()

    def tearDown(self) -> None:
        super().tearDown()
        if getattr(self, "server", None) is not None:
            try:
                self.server.stop()
            finally:
                self.server = None

    def _exploration_panel(self, page):
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
        page.evaluate("window.__elosernBridge.router.reset()")
        page.wait_for_timeout(60)

    def _open_root(self, page, index):
        self._reset_root(page)
        # The exploration root is a single seven-column row (mockup grid), so
        # horizontal arrows move across it; submenus are 2-column grids.
        for _ in range(index):
            _press(page, "ArrowRight")
        _press(page, "Enter")

    @covers_requirement("webclient-exploration-menu::explore-move-traverses-a-re-resolved-exit-through-the-shared-movement-path")
    def test_keyboard_move_charges_time_and_refreshes_map(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)
        map_before = store_state(page)["panels"]["local_map"]
        self.assertEqual(map_before["current_node"], "grid:capital_altoria:2:0")
        time_before = store_state(page)["serverTime"]

        self._open_root(page, 0)  # Move
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

    @covers_requirement("webclient-exploration-menu::the-exploration-dock-is-keyboard-first-and-re-homes-the-service-submenus")
    def test_escape_from_character_panel_returns_keyboard_to_the_exploration_root(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)
        self.assertIn("character", store_state(page)["panels"])

        self._open_root(page, 3)  # 角色狀態
        self.assertEqual(
            page.evaluate("(() => { const s = window.__elosernBridge.store.view; return s && s.activeSubDock; })()"),
            "character",
            "the character panel must own the action dock",
        )
        _press(page, "Escape")
        page.wait_for_timeout(120)
        self.assertEqual(
            page.evaluate("(() => { const s = window.__elosernBridge.store.view; return s && s.activeSubDock; })()"),
            None,
            "Escape must leave the character panel",
        )

        self._open_root(page, 0)  # Move
        _press(page, "Enter")  # first exit
        self._wait_panel(
            page,
            "local_map",
            lambda p: p.get("available") is True and p["current_node"] != "grid:capital_altoria:2:0",
        )
        self.assertEqual(
            sent_action_count(page, "explore.move"),
            1,
            "after Character -> Escape the exploration root must accept keyboard input",
        )

    @covers_requirement("webclient-exploration-menu::explore-look-reuses-the-command-appearance-path-and-preserves-onboarding-look-hooks")
    def test_look_at_room_preserves_the_onboarding_beat(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        self._open_root(page, 1)  # Look
        _press(page, "Enter")  # look at the room
        self.assertEqual(sent_action_count(page, "explore.look"), 1)
        wait_for_store_state(
            page,
            _connected_active,
            dom_readiness={
                "selector": '[data-testid="narrative-feed"]',
                "predicate": (
                    "() => { const el = document.querySelector('[data-testid=\"narrative-feed\"]'); "
                    "return !!el && el.innerText.indexOf('南門') !== -1; }"
                ),
                "description": "narrative feed shows the South Gate room",
            },
        )

    @covers_requirement("localized-appearance::the-shared-appearance-layer-renders-traditional-chinese-frames")
    def test_look_at_guard_shows_the_affinity_stage_line(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        self._open_root(page, 1)  # Look
        _press(page, "ArrowRight")  # the guard (first present entity)
        _press(page, "Enter")
        self.assertEqual(sent_action_count(page, "explore.look"), 1)
        wait_for_store_state(
            page,
            _connected_active,
            dom_readiness={
                "selector": '[data-testid="narrative-feed"]',
                "predicate": (
                    "() => { const el = document.querySelector('[data-testid=\"narrative-feed\"]'); "
                    "return !!el && el.innerText.indexOf('她看著你的眼神裡帶著信賴。') !== -1; }"
                ),
                "description": "narrative feed shows the guard's trust line",
            },
        )

    @covers_requirement("webclient-exploration-menu::explore-talk-scripted-invokes-the-deterministic-dialogue-api-with-keyword-buttons")
    def test_scripted_keyword_dialogue_completes(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        self._open_root(page, 2)  # Interact
        _press(page, "Enter")  # the guard (first present target, synced in the seed)
        _press(page, "Enter")  # 交談 (scripted affordance)
        _press(page, "Enter")  # first keyword
        self._wait_panel(
            page,
            "exploration",
            lambda p: p.get("available") is True,
        )
        sent = page.evaluate("window.__elosernSent || []")
        talk = [
            args[0]
            for cmd, args, _kw in sent
            if cmd == "ui_action" and args[0]["action_id"] == "explore.talk_scripted"
        ]
        self.assertEqual(len(talk), 1)
        self.assertIn("keyword_id", talk[0]["payload"])
        self.assertIn("npc_id", talk[0]["payload"])
        wait_for_store_state(
            page,
            _connected_active,
            dom_readiness={
                "selector": '[data-testid="narrative-feed"]',
                "predicate": (
                    "() => { const el = document.querySelector('[data-testid=\"narrative-feed\"]'); "
                    "return !!el && el.innerText.indexOf('冒險者公會') !== -1; }"
                ),
                "description": "narrative feed shows the adventurers' guild",
            },
        )

    @covers_requirement("webclient-exploration-menu::explore-talk-freeform-runs-the-guarded-dialogue-seam-through-an-injected-client")
    def test_freeform_dialogue_degrades_offline_through_the_command_line(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        self._open_root(page, 2)  # Interact
        _press(page, "ArrowRight")  # the bard (second grid column)
        _press(page, "Enter")
        _press(page, "ArrowRight")  # 自由交談 (second grid column)
        _press(page, "Enter")
        wait_for_store_state(
            page,
            _connected_active,
            dom_readiness={
                "selector": "#inputfield",
                "predicate": (
                    "() => { const f = document.getElementById('inputfield'); "
                    "const a = document.activeElement; "
                    "return !!f && a === f; }"
                ),
                "description": "command-line input field is focused",
            },
        )
        page.keyboard.type("你好，詩人")
        page.keyboard.press("Enter")
        self._wait_panel(
            page,
            "exploration",
            lambda p: p.get("available") is True,
        )
        self.assertEqual(sent_action_count(page, "explore.talk_freeform"), 1)
        # Offline degrade reaches the authored greeting/silence.
        wait_for_store_state(
            page,
            _connected_active,
            dom_readiness={
                "selector": '[data-testid="narrative-feed"]',
                "predicate": (
                    "() => { const el = document.querySelector('[data-testid=\"narrative-feed\"]'); "
                    "return !!el && el.innerText.indexOf('歡迎來到冒險者公會') !== -1; }"
                ),
                "description": "narrative feed shows the offline greeting",
            },
        )

    @covers_requirement(
        "webclient-desktop-shell::the-command-drawer-preserves-ordinary-text-control"
    )
    def test_cancelled_freeform_dialogue_cannot_capture_a_later_command(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        # Open free-form dialogue but cancel with Escape without sending.
        self._open_root(page, 2)  # Interact
        _press(page, "ArrowRight")  # the bard (second grid column)
        _press(page, "Enter")
        _press(page, "ArrowRight")  # 自由交談 (second grid column)
        _press(page, "Enter")
        wait_for_store_state(
            page,
            _connected_active,
            dom_readiness={
                "selector": "#inputfield",
                "predicate": (
                    "() => { const f = document.getElementById('inputfield'); "
                    "const a = document.activeElement; "
                    "return !!f && a === f; }"
                ),
                "description": "command-line input field is focused",
            },
        )
        page.keyboard.type("話到嘴邊又吞了回去")
        page.keyboard.press("Escape")
        wait_for_store_state(
            page,
            _connected_active,
            dom_readiness={
                "selector": "#action-dock",
                "predicate": (
                    "() => { const d = document.querySelector('[data-testid=\"command-line\"]'); "
                    "const linePresent = !!d; "
                    "const dock = document.getElementById('action-dock'); "
                    "const a = document.activeElement; "
                    "return linePresent && !!dock && (a === dock || (a && dock.contains(a))); }"
                ),
                "description": "command line present and action dock focused",
            },
        )

        # Send an ordinary command through the always-present command line: it
        # must travel as text, never as explore.talk_freeform speech to the
        # previously selected NPC.
        page.keyboard.press("/")
        wait_for_store_state(
            page,
            _connected_active,
            dom_readiness={
                "selector": "#inputfield",
                "predicate": (
                    "() => { const f = document.getElementById('inputfield'); "
                    "const a = document.activeElement; "
                    "return !!f && a === f; }"
                ),
                "description": "command-line input field is focused",
            },
        )
        narrative_before = page.locator('[data-testid="narrative-feed"]').inner_text()
        page.keyboard.type("look")
        page.keyboard.press("Enter")
        before_len = len(narrative_before)
        wait_for_store_state(
            page,
            _connected_active,
            dom_readiness={
                "selector": '[data-testid="narrative-feed"]',
                "predicate": (
                    "() => { const el = document.querySelector('[data-testid=\"narrative-feed\"]'); "
                    "return !!el && el.innerText.length > %d; }" % before_len
                ),
                "description": "narrative feed grew past the pre-command length",
            },
        )
        self.assertEqual(sent_action_count(page, "explore.talk_freeform"), 0)
        # The command was sent through the text path.
        text_sends = [
            args[0]
            for cmd, args, _kw in page.evaluate("window.__elosernSent || []")
            if cmd == "text"
        ]
        self.assertTrue(
            any("look" in str(item) for item in text_sends),
            "the ordinary command must travel through the text transport",
        )

    @covers_requirement("webclient-exploration-menu::explore-engage-delegates-to-the-existing-engage-contract")
    def test_engage_transitions_to_combat(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        self._open_root(page, 2)  # Interact
        _press(page, "ArrowDown")  # the goblin (second grid row, first column)
        _press(page, "Enter")
        _press(page, "Enter")  # 戰鬥 (engage)
        wait_for_store_state(
            page,
            lambda s: s.get("mode") == "combat",
            timeout=30000,
        )
        self.assertEqual(store_state(page)["mode"], "combat")
        self.assertEqual(sent_action_count(page, "explore.engage"), 1)
        self.assertEqual(
            page.locator("#action-dock").get_attribute("data-mode"),
            "combat",
        )

    @covers_requirement("webclient-exploration-menu::explore-wait-obeys-the-shared-skip-safety-and-clock-api")
    def test_unsafe_skip_rejects_before_any_clock_advance(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        # At the South Gate a living goblin makes every skip unsafe; the
        # daypart boundary rejects before any clock advance.
        time_before = store_state(page)["serverTime"]
        self._open_root(page, 6)  # Wait/休息
        _press(page, "ArrowRight")  # 等待至黎明 (second grid column)
        _press(page, "Enter")
        wait_for_store_state(
            page,
            lambda s: (s.get("lastActionResult") or {}).get("code") == "unsafe_skip",
            timeout=20000,
        )
        self.assertEqual(store_state(page)["lastActionResult"]["code"], "unsafe_skip")
        self.assertEqual(sent_action_count(page, "explore.wait"), 1)
        self.assertEqual(store_state(page)["serverTime"], time_before)

        # The bounded custom-duration form is parsed server-side and rejected
        # by the same safety gate.
        self._open_root(page, 6)  # Wait/休息
        _press(page, "ArrowDown")  # 等待至正午 (second grid row)
        _press(page, "ArrowDown")  # 休息一段時間 (third grid row)
        _press(page, "Enter")
        wait_for_store_state(
            page,
            _connected_active,
            dom_readiness={
                "selector": '[data-testid="exploration-rest-form"]',
                "predicate": (
                    "() => !!document.querySelector('[data-testid=\"exploration-rest-form\"]')"
                ),
                "description": "exploration rest duration form rendered",
            },
        )
        page.keyboard.type("3600")
        page.keyboard.press("Enter")
        wait_for_store_state(
            page,
            lambda s: (s.get("lastActionResult") or {}).get("code") == "unsafe_skip",
            timeout=20000,
        )
        self.assertEqual(store_state(page)["lastActionResult"]["code"], "unsafe_skip")
        self.assertEqual(sent_action_count(page, "explore.wait"), 2)
        self.assertEqual(store_state(page)["serverTime"], time_before)

    @covers_requirement("webclient-exploration-menu::the-exploration-dock-is-keyboard-first-and-re-homes-the-service-submenus")
    @covers_requirement("webclient-exploration-menu::explore-wait-obeys-the-shared-skip-safety-and-clock-api")
    def test_safe_wait_until_dawn_advances_the_clock(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        # Move away from the goblin, then wait until dawn succeeds.
        self._open_root(page, 0)  # Move
        _press(page, "Enter")  # first exit
        self._wait_panel(
            page,
            "local_map",
            lambda p: p.get("available") is True and p["current_node"] != "grid:capital_altoria:2:0",
        )
        time_before = store_state(page)["serverTime"]
        self._open_root(page, 6)  # Wait/休息
        _press(page, "ArrowRight")  # 等待至黎明 (second grid column)
        _press(page, "Enter")
        wait_for_store_state(
            page,
            lambda s: (s.get("lastActionResult") or {}).get("code") == "skipped",
            timeout=20000,
        )
        ok = store_state(page)["lastActionResult"]
        self.assertIsNotNone(ok, "a safe wait must succeed")
        time_after = store_state(page)["serverTime"]
        self.assertNotEqual(
            (time_after["hour"], time_after["minute"]),
            (time_before["hour"], time_before["minute"]),
            "a successful wait must advance the world clock",
        )

    @covers_requirement("webclient-exploration-menu::exploration-actions-reject-stale-duplicate-and-tampered-input-without-mutation")
    def test_stale_and_tampered_submissions_do_nothing(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)
        map_before = store_state(page)["panels"]["local_map"]["current_node"]

        # A raw ui_action with a stale base_revision returns the dispatcher's
        # stale outcome and performs no traversal.
        page.evaluate(
            """() => {
              const s = ((window.__elosernBridge && window.__elosernBridge.store.view) || null);
              const moveRow = s.panels.exploration.move[0];
              Evennia.msg('ui_action', [{
                protocol_version: 1,
                presentation_epoch: s.epoch,
                request_id: 'stale-move-1',
                base_revision: 0,
                action_id: 'explore.move',
                payload: { exit_ref: moveRow.exit_ref, current_node: s.panels.local_map.current_node },
              }], {});
            }"""
        )
        wait_for_store_state(
            page,
            lambda s: (s.get("lastActionResult") or {}).get("requestId") == "stale-move-1",
            timeout=20000,
        )
        self.assertEqual(store_state(page)["lastActionResult"]["outcome"], "stale")
        self.assertEqual(
            store_state(page)["panels"]["local_map"]["current_node"],
            map_before,
            "a stale move must not relocate the actor",
        )

        # A tampered exit_ref fails commit-time revalidation.
        page.evaluate(
            """() => {
              const s = ((window.__elosernBridge && window.__elosernBridge.store.view) || null);
              Evennia.msg('ui_action', [{
                protocol_version: 1,
                presentation_epoch: s.epoch,
                request_id: 'tampered-move-1',
                base_revision: s.revision,
                action_id: 'explore.move',
                payload: { exit_ref: '999999', current_node: s.panels.local_map.current_node },
              }], {});
            }"""
        )
        wait_for_store_state(
            page,
            lambda s: (s.get("lastActionResult") or {}).get("requestId") == "tampered-move-1",
            timeout=20000,
        )
        last = store_state(page)["lastActionResult"]
        self.assertEqual(last["outcome"], "rejected")
        self.assertEqual(last["code"], "no_exit")
        self.assertEqual(
            store_state(page)["panels"]["local_map"]["current_node"],
            map_before,
        )

    @covers_requirement("webclient-exploration-menu::exploration-browser-acceptance-is-keyboard-only-and-desktop-bounded")
    def test_no_take_or_drop_control_is_rendered(self):
        page = self.logged_in_page((1280, 720))
        install_outbound_recorder(page)
        self._wait_exploration_available(page)
        # The exploration dock renders no take/drop or generic object-mutation
        # control anywhere in the surface.
        body_text = page.locator("#action-dock").inner_text()
        self.assertNotIn("拾取", body_text)
        self.assertNotIn("丟棄", body_text)
        self.assertNotIn("explore.take", body_text)
        self.assertNotIn("explore.drop", body_text)
        sent = page.evaluate("window.__elosernSent || []")
        for cmdname, args, _kwargs in sent:
            if cmdname != "ui_action" or not args:
                continue
            self.assertFalse(
                args[0]["action_id"].startswith("explore.take"),
                "explore.take must never be submitted",
            )
            self.assertFalse(
                args[0]["action_id"].startswith("explore.drop"),
                "explore.drop must never be submitted",
            )

    @covers_requirement("webclient-exploration-menu::exploration-actions-reject-stale-duplicate-and-tampered-input-without-mutation")
    def test_reconnect_rebuilds_exploration_without_replay(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        page.evaluate(
            "() => { if (window.__elosernWs) window.__elosernWs.close(4001); }"
        )
        wait_for_store_state(
            page,
            lambda s: not s.get("connected"),
        )
        page.evaluate("Evennia.connect()")
        self._wait_exploration_available(page)
        # The rebuilt dock derives from server-persisted state and no dialogue
        # or mutation is automatically replayed.
        self.assertEqual(sent_action_count(page, "explore.move"), 0)
        self.assertEqual(sent_action_count(page, "explore.talk_freeform"), 0)
        self.assertEqual(sent_action_count(page, "explore.talk_scripted"), 0)

    @covers_requirement("webclient-exploration-menu::the-exploration-dock-is-keyboard-first-and-re-homes-the-service-submenus")
    def test_pointer_back_cell_returns_to_the_root_without_an_action(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        # Pointer: open Look, then click its final back cell.
        wait_for_store_state(
            page,
            lambda s: ((s.get("panels") or {}).get("exploration") or {}).get("available") is True,
            dom_readiness={
                "selector": '#action-dock [data-item-key="look"]',
                "predicate": (
                    "() => !!document.querySelector('#action-dock [data-item-key=\"look\"]')"
                ),
                "description": "Look cell rendered in the exploration dock",
            },
        )
        page.locator('[data-item-key="look"]').click()
        wait_for_store_state(
            page,
            _connected_active,
            dom_readiness={
                "selector": '[data-testid="exploration-detail"]',
                "predicate": (
                    "() => !!document.querySelector('[data-testid=\"exploration-detail\"]')"
                ),
                "description": "exploration detail panel rendered",
            },
        )
        wait_for_store_state(
            page,
            lambda s: ((s.get("panels") or {}).get("exploration") or {}).get("available") is True,
            dom_readiness={
                "selector": '#action-dock [data-item-key="back"]',
                "predicate": (
                    "() => !!document.querySelector('#action-dock [data-item-key=\"back\"]')"
                ),
                "description": "back cell rendered in the detail dock",
            },
        )
        page.locator('[data-item-key="back"]').click()
        wait_for_store_state(
            page,
            lambda s: ((s.get("panels") or {}).get("exploration") or {}).get("available") is True,
            dom_readiness={
                "selector": "#action-dock",
                "predicate": (
                    "() => { const keys = Array.from("
                    "document.querySelectorAll('#action-dock [data-item-key]'))"
                    ".map((el) => el.getAttribute('data-item-key'));"
                    "return keys.indexOf('move') !== -1 && keys.indexOf('look') !== -1; }"
                ),
                "description": "exploration root cells (move/look) rendered in the dock",
            },
        )
        # The root cells render again, no ui_action was sent, and no
        # command-line text was submitted.
        keys = page.evaluate(
            "() => Array.from(document.querySelectorAll("
            "'#action-dock [data-item-key]')).map((el) => el.getAttribute('data-item-key'))"
        )
        self.assertEqual(
            keys,
            ["move", "look", "interact", "character", "quests", "inventory", "wait"],
        )
        self.assertEqual(sent_action_count(page), 0)
        self.assertEqual(
            page.evaluate("window.__elosernBridge.router.depth()"),
            1,
            "the back cell pops exactly one router frame",
        )

    @covers_requirement("webclient-exploration-menu::the-exploration-dock-is-keyboard-first-and-re-homes-the-service-submenus")
    def test_escape_at_intermediate_depth_keeps_cells_matched_to_the_frame(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        # Interact -> the guard -> 交談 (scripted keywords): two levels deep.
        panel = self._exploration_panel(page)
        guard_identity = panel["interact"][0]["identity"]
        self._open_root(page, 2)  # Interact
        _press(page, "Enter")  # the guard (first present target)
        _press(page, "Enter")  # 交談 (first affordance)
        self.assertEqual(page.evaluate("window.__elosernBridge.router.depth()"), 4)
        _press(page, "Escape")  # back to the target-affordance menu
        page.wait_for_timeout(80)
        self.assertEqual(page.evaluate("window.__elosernBridge.router.depth()"), 3)
        # H3 (design D2): at depth >= 2 the dock renders both the root tab
        # bar (8 root tabs) and the scrolling pane (the active frame's rows).
        # The test's cell assertions target the pane's rows only.
        target_keys = page.evaluate(
            "() => Array.from(document.querySelectorAll("
            "'.action-dock__pane [data-item-key]')).map((el) => el.getAttribute('data-item-key'))"
        )
        # The guard's affordance menu: the scripted-talk entry plus the final
        # back cell (the exploration fixture carries no guild navigate entry).
        self.assertEqual(
            target_keys,
            ["talk-scripted", "back"],
            "the target-affordance cells must render after one Escape",
        )
        self.assertEqual(
            page.evaluate(
                "window.__elosernBridge.router.currentItem() && "
                "window.__elosernBridge.router.currentItem().key"
            ),
            "talk-scripted",
        )
        _press(page, "Escape")  # back to the Interact target list
        page.wait_for_timeout(80)
        self.assertEqual(page.evaluate("window.__elosernBridge.router.depth()"), 2)
        interact_keys = page.evaluate(
            "() => Array.from(document.querySelectorAll("
            "'.action-dock__pane [data-item-key]')).map((el) => el.getAttribute('data-item-key'))"
        )
        expected_interact = [
            "target-" + str(target["identity"]) for target in panel["interact"]
        ]
        expected_interact.append("back")
        self.assertEqual(
            interact_keys,
            expected_interact,
            "the Interact list cells must render after the second Escape",
        )
        self.assertEqual(
            page.evaluate(
                "window.__elosernBridge.router.currentItem() && "
                "window.__elosernBridge.router.currentItem().key"
            ),
            "target-" + str(guard_identity),
        )
        self.assertEqual(sent_action_count(page), 0)

    @covers_requirement("webclient-exploration-menu::the-exploration-dock-is-keyboard-first-and-re-homes-the-service-submenus")
    def test_escape_from_quests_service_submenu_leaves_root_clean(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        # Quests opens a re-homed services submenu; Escape must return to the
        # exploration root without corrupting or re-rendering exploration
        # cells (the shared-router regression).
        self._open_root(page, 4)  # Quests
        self.assertEqual(
            page.evaluate("(() => { const s = window.__elosernBridge.store.view; return s && s.activeSubDock; })()"),
            "services",
            "the services dock must own the surface inside Quests",
        )
        _press(page, "Escape")
        page.wait_for_timeout(120)
        self.assertEqual(
            page.evaluate("(() => { const s = window.__elosernBridge.store.view; return s && s.activeSubDock; })()"),
            None,
            "Escape must leave the services sub-dock",
        )
        keys = page.evaluate(
            "() => Array.from(document.querySelectorAll("
            "'#action-dock [data-item-key]')).map((el) => el.getAttribute('data-item-key'))"
        )
        # H3 (design D5): the exploration root now includes the 建議 (suggestions)
        # tab, so the root has 8 cells, not 7.
        self.assertEqual(
            keys,
            ["move", "look", "interact", "character", "quests", "inventory", "wait", "suggestions"],
            "the exploration root cells must render after Escape from Quests",
        )
        self.assertEqual(
            page.evaluate(
                "window.__elosernBridge.router.currentItem() && "
                "window.__elosernBridge.router.currentItem().key"
            ),
            "move",
        )


if __name__ == "__main__":
    import unittest

    unittest.main()
