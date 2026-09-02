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

import json

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

    def _err_line_texts(self, page):
        """The rendered narrative err lines, in feed order."""
        return page.evaluate(
            """() => Array.from(
                 document.querySelectorAll(
                   '[data-testid="narrative-feed"] [data-line-kind="err"]'),
                 (n) => n.textContent)"""
        )

    def _tamper_sender(self, page, tamper):
        """Wrap the live transport sender so dispatched envelopes pass through
        ``tamper`` (shallow-cloned; the store's envelope is never mutated in
        place). The caller stores ``window.__elosernOriginalSender`` first and
        restores it with ``_restore_sender``."""
        page.evaluate(
            """(tamperSource) => {
              const store = window.__elosernBridge.store;
              const original = window.__elosernOriginalSender;
              if (!original || typeof original.sendAction !== "function") {
                throw new Error("no stashed original sender");
              }
              const tamper = new Function("return " + tamperSource)();
              store.setSender({
                sendText: (text) => original.sendText(text),
                sendSync: () => original.sendSync(),
                sendAction: (envelope) => original.sendAction(tamper(envelope)),
              });
            }""",
            tamper,
        )

    def _restore_sender(self, page):
        page.evaluate(
            "() => window.__elosernBridge.store.setSender(window.__elosernOriginalSender)"
        )

    def _dispatch_move(self, page):
        """Dispatch one explore.move for the first exit through the store."""
        return page.evaluate(
            """() => {
              const s = window.__elosernBridge.store.view;
              const row = s.panels.exploration.move[0];
              return window.__elosernBridge.store.dispatchAction('explore.move', {
                exit_ref: row.exit_ref,
                current_node: s.panels.local_map.current_node,
              });
            }"""
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

    def _dock_holds_focus(self, page):
        """True when #action-dock (or a focusable descendant) is the active
        element — element identity, not a text marker (duck finding)."""
        return page.evaluate(
            """() => { const dock = document.getElementById('action-dock');
                       const el = document.activeElement;
                       return !!dock && !!el
                         && (el === dock || dock.contains(el)); }"""
        )

    def _wait_non_success_line(self, page, message, baseline):
        """Wait until the err-line multiset grew by exactly [message] over
        ``baseline`` (baseline-relative counting: pre-existing lines, the
        dispatch's own in-kind echo, and mutation echoes are all excluded --
        only the recognized result may add an err line)."""
        page.wait_for_function(
            """([message, baselineJson]) => {
                 const baseline = JSON.parse(baselineJson);
                 const lines = Array.from(
                   document.querySelectorAll(
                     '[data-testid="narrative-feed"] [data-line-kind="err"]'),
                   (n) => n.textContent);
                 const counts = new Map();
                 for (const l of baseline) counts.set(l, (counts.get(l) || 0) + 1);
                 for (const l of lines) counts.set(l, (counts.get(l) || 0) - 1);
                 // added = actual-minus-baseline multiset diff (negative
                 // remaining count per occurrence of an unseen line).
                 const added = lines.filter((l) => (counts.get(l) || 0) < 0
                   && ((counts.set(l, counts.get(l) + 1), true)));
                 return added.length === 1 && added[0].includes(message);
               }""",
            arg=[message, json.dumps(baseline)],
        )

    @covers_requirement("webclient-action-dispatch::a-non-success-action-result-surfaces-its-message-exactly-once")
    def test_non_success_action_results_speak_once_in_the_narrative(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)
        # The stale admission needs a positive committed revision so the
        # decremented base_revision stays schema-valid (a negative one would
        # follow the malformed-envelope protocol-error path instead).
        wait_for_store_state(page, lambda s: (s.get("revision") or 0) > 0)
        node_before = store_state(page)["panels"]["local_map"]["current_node"]
        page.evaluate(
            "() => { window.__elosernOriginalSender = window.__elosernBridge.store.getSender(); }"
        )

        # (a) A real stale admission through the store's own dispatch path:
        # the sender wrapper sends the envelope with a superseded
        # base_revision; the dispatcher answers outcome `stale`.
        self._tamper_sender(
            page,
            "(e) => Object.assign({}, e, { base_revision: e.base_revision - 1 })",
        )
        dispatch_base = page.evaluate("() => window.__elosernBridge.store.view.revision")
        err_baseline = self._err_line_texts(page)
        request_id = page.evaluate(
            "() => window.__elosernBridge.store.dispatchAction('explore.wait', { daypart: 'dusk' })"
        )
        self.assertIsNotNone(request_id)
        # The wire envelope really carried the decremented revision.
        tampered = [
            args[0]
            for cmdname, args, _kw in page.evaluate("window.__elosernSent || []")
            if cmdname == "ui_action" and args and args[0].get("request_id") == request_id
        ]
        self.assertEqual(len(tampered), 1)
        self.assertEqual(tampered[0]["base_revision"], dispatch_base - 1)
        wait_for_store_state(
            page,
            lambda s: (s.get("lastActionResult") or {}).get("requestId") == request_id,
            timeout=20000,
        )
        self._restore_sender(page)
        result = store_state(page)["lastActionResult"]
        self.assertEqual(result["outcome"], "stale", f"expected stale, got {result}")
        message = result["message"]
        # The message renders verbatim and exactly once over the baseline err
        # multiset -- no second line, no accompanying mutation echo.
        self._wait_non_success_line(page, message, err_baseline)
        err_lines = [t for t in self._err_line_texts(page) if message in t]
        self.assertEqual(err_lines[0].strip(), message)
        self.assertEqual(page.locator('[role="dialog"]').count(), 0)
        self.assertEqual(sent_action_count(page, "explore.wait"), 1)
        self.assertEqual(
            store_state(page)["panels"]["local_map"]["current_node"],
            node_before,
            "the stale admission performed no traversal",
        )
        # The stale lock releases once the recovery revision commits.
        wait_for_store_state(page, lambda s: s["dispatch"]["inFlight"] is None)

        # (b) A real domain rejection: a genuine move commits the new room;
        # then a valid re-move whose sender wrapper replaces only
        # payload.current_node with the pre-move node reaches the exploration
        # adapter's stale-location rejection.
        self._wait_admitted_move(page, node_before)
        moved_node = store_state(page)["panels"]["local_map"]["current_node"]
        wait_for_store_state(page, lambda s: s["dispatch"]["inFlight"] is None)

        # Keyboard focus is held by the dock; a rendered result must not move
        # or steal it (no modal steals focus either).
        focus_action_dock(page)
        self.assertTrue(self._dock_holds_focus(page), "the dock did not take focus")
        self._tamper_sender(
            page,
            """(e) => Object.assign({}, e, {
                 payload: Object.assign({}, e.payload, { current_node: %r })
               })"""
            % node_before,
        )
        # Admission itself can race a revision advance (answered stale before
        # the adapter runs); retry the tampered dispatch until the adapter's
        # domain rejection lands, bounded. Stale retries append their own
        # (different) message, so the domain-message baseline is captured
        # right before the final accepted attempt.
        result = None
        for _attempt in range(3):
            err_baseline = self._err_line_texts(page)
            request_id = self._dispatch_move(page)
            self.assertIsNotNone(request_id)
            wait_for_store_state(
                page,
                lambda s: (s.get("lastActionResult") or {}).get("requestId") == request_id,
                timeout=20000,
            )
            result = store_state(page)["lastActionResult"]
            if result["outcome"] != "stale":
                self._wait_non_success_line(page, result.get("message", ""), err_baseline)
                break
            stale_message = result.get("message", "")
            wait_for_store_state(page, lambda s: s["dispatch"]["inFlight"] is None)
            # Settle the stale line's DOM append before re-capturing so the
            # next attempt's baseline multiset already contains it.
            page.wait_for_function(
                """(message) => message !== "" && Array.from(
                     document.querySelectorAll(
                       '[data-testid="narrative-feed"] [data-line-kind="err"]'),
                     (n) => n.textContent).some((t) => t.includes(message))""",
                arg=stale_message,
            )
            err_baseline = self._err_line_texts(page)
        self._restore_sender(page)
        self.assertIsNotNone(result)
        self.assertEqual(
            result["outcome"], "rejected", f"expected domain rejection, got {result}"
        )
        self.assertEqual(result["code"], "stale_location")
        message = "你的位置已經改變，請重新操作。"
        self.assertEqual(result["message"], message)
        err_lines = [t for t in self._err_line_texts(page) if message in t]
        self.assertEqual(len(err_lines), 1)
        self.assertEqual(err_lines[0].strip(), message)
        # The player keeps keyboard focus without any modal.
        self.assertEqual(page.locator('[role="dialog"]').count(), 0)
        self.assertTrue(
            self._dock_holds_focus(page),
            "the rendered result moved keyboard focus out of the dock",
        )
        # The rejected move relocated nobody.
        self.assertEqual(
            store_state(page)["panels"]["local_map"]["current_node"],
            moved_node,
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
        self._open_root(page, 0)  # Move
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
        self._open_root(page, 1)  # Look
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
        self._open_root(page, 2)  # Interact
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

        # Wait/rest (task 2.3 re-confirmation): the plain pane is not a grid
        # container, so this change is inert on the 等待/休息 frame.
        self._open_root(page, 6)  # Wait
        self.assertEqual(
            page.locator(".dock-menu__plain").evaluate("el => getComputedStyle(el).display"),
            "block",
            "the wait/rest pane stays a non-grid block container",
        )

    def test_outlet_partial_last_row_fills_the_pane_at_a_narrower_viewport(self):
        # fix-webclient-hud-dock-exploration-grid-width: at 400x720 the pane
        # content width is ~384px, so the `auto-fit` grid fits only 2 columns
        # (floor((384 + 8) / 158) = 2). The exploration fixture's 3-exit move
        # frame wraps the third exit onto a partial second row; the last tile
        # must span the remaining column so no horizontal space is left blank.
        page = self.logged_in_page((400, 720))
        install_outbound_recorder(page)
        self._wait_exploration_available(page)
        self._open_root(page, 0)  # Move
        pane_box = page.locator(".dock-menu__outlet").bounding_box()
        self.assertIsNotNone(pane_box, "the outlet pane must be visible at 400x720")
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
            "the partial second row's tile must end at the pane's right edge",
        )
        self.assertIn(
            "grid-column",
            tiles.last.get_attribute("style") or "",
            "the partial-row tile must carry the inline span style",
        )


if __name__ == "__main__":
    import unittest

    unittest.main()
