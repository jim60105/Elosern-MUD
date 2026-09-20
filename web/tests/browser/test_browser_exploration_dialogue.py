"""Keyboard-only exploration browser acceptance (webclient-exploration-menu 4.2-4.6): scripted and free-form dialogue surfaces, the dialogue caption, the offline degrade path, and engage-to-combat.
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


def _connected_active(state: dict) -> bool:
    """Gate on the client being connected and in the active presentation phase."""
    return bool(state.get("connected")) and state.get("phase") == "active"


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

    @covers_requirement("localized-appearance::the-shared-appearance-layer-renders-traditional-chinese-frames")
    def test_look_at_scripted_host_shows_the_affinity_stage_line(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        self._open_root(page, 1)  # Look
        _press(page, "ArrowRight")  # the scripted host (first present entity)
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
                "description": "narrative feed shows the host's trust line",
            },
        )

    @covers_requirement("webclient-exploration-menu::explore-talk-scripted-invokes-the-deterministic-dialogue-api-with-keyword-buttons")
    def test_scripted_keyword_dialogue_completes(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        self._open_root(page, 2)  # Interact
        _press(page, "Enter")  # the scripted host (first present target, synced in the seed)
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
                    "return !!el && el.innerText.indexOf('先在櫃檯註冊成為冒險者') !== -1; }"
                ),
                "description": "narrative feed shows the registration dialogue line",
            },
        )

    @covers_requirement(
        "webclient-contextual-hud::the-feed-presents-the-dialogue-variant-from-the-committed-panel"
    )
    def test_dialogue_surface_is_the_caption_and_the_dock_stays_ordinary(self):
        # The leave-requirement annotation (delta id
        # webclient-dialogue-session::explore-dialogue-leave-ends-the-live-session-through-the-sole-writer)
        # is added at delta sync — the traceability gate only recognizes
        # main-spec ids during the change window.
        """webclient-align-11-dialogue-ux: entering dialogue keeps the dock in
        its ordinary exploration form (no 對話選項 mirror tab); the caption's
        scripted pick dispatches by digit; the caption's exit row ends the
        session and the committed snapshot restores exploration."""
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        # Enter dialogue through the ordinary dock affordance path: the
        # affordance opens the keywords frame, and the first scripted pick
        # still rides the dock (the caption retarget only exists once the
        # panel commits). The dispatch settles when its action result lands
        # — the panel's (already-true) availability would race the in-flight
        # lock and silently drop the next input.
        result_before = (store_state(page).get("lastActionResult") or {}).get("requestId")
        self._open_root(page, 2)  # Interact
        _press(page, "Enter")  # the scripted host
        _press(page, "Enter")  # 交談 (scripted affordance -> keywords frame)
        _press(page, "Enter")  # first scripted keyword -> talk_scripted
        wait_for_store_state(
            page,
            lambda state: (
                (state.get("lastActionResult") or {}).get("requestId")
                not in (None, result_before)
            ),
        )
        self.assertEqual(sent_action_count(page, "explore.talk_scripted"), 1)
        self._wait_panel(
            page, "dialogue", lambda p: p.get("available") is True
        )

        # The dock keeps its ORDINARY form while talking: the tab bar shows
        # the usual exploration tabs, never the retired 對話選項 mirror.
        tabs = page.evaluate(
            "() => Array.from(document.querySelectorAll('.dock-tab-bar__tab'))"
            ".map((t) => t.textContent)"
        )
        self.assertTrue(tabs, "the dock tab bar must render while talking")
        self.assertNotIn("對話選項", "".join(tabs))

        # The caption presents the pick grid and the trailing exit row, and
        # the head is the sibling ABOVE the scroll viewport (the DOM contract
        # the managed suites depend on).
        page.wait_for_selector('[data-testid="dialogue-exit"]')
        dom_shape = page.evaluate(
            """() => {
              const feed = document.querySelector('[data-testid="narrative-feed"]');
              const head = document.querySelector('[data-testid="narrative-head"]');
              return {
                feedIsScroll: !!feed && feed.classList.contains("narrative-scroll"),
                headAboveScroll: !!head && !!feed && head.nextElementSibling === feed,
                picks: document.querySelectorAll('[data-testid="dialogue-pick"]').length,
              };
            }"""
        )
        self.assertTrue(dom_shape["feedIsScroll"])
        self.assertTrue(dom_shape["headAboveScroll"])
        self.assertGreater(dom_shape["picks"], 0)

        # Digit activation addresses the caption pick, not the dock rows.
        # A digit now addresses the caption's pick grid, NOT the dock rows:
        # a second scripted talk dispatches through the caption exactly once.
        result_before_pick = (
            store_state(page).get("lastActionResult") or {}
        ).get("requestId")
        _press(page, "1")
        wait_for_store_state(
            page,
            lambda state: (
                (state.get("lastActionResult") or {}).get("requestId")
                not in (None, result_before_pick)
            ),
        )
        self.assertEqual(sent_action_count(page, "explore.talk_scripted"), 2)

        # The exit row dispatches the deterministic leave seam exactly once.
        result_before_exit = (
            store_state(page).get("lastActionResult") or {}
        ).get("requestId")
        page.click('[data-testid="dialogue-exit"]')
        wait_for_store_state(
            page,
            lambda state: (
                (state.get("lastActionResult") or {}).get("requestId")
                not in (None, result_before_exit)
            ),
        )
        self.assertEqual(sent_action_count(page, "explore.dialogue_leave"), 1)
        self._wait_panel(
            page, "dialogue", lambda p: p.get("available") is not True
        )
        after = store_state(page)
        self.assertEqual(after["mode"], "exploration")
        wait_for_store_state(
            page,
            _connected_active,
            dom_readiness={
                "selector": '[data-testid="narrative-feed"]',
                "predicate": (
                    "() => { const el = document.querySelector('[data-testid=\"narrative-feed\"]'); "
                    "return !!el && el.innerText.indexOf('你結束了對話。') !== -1; }"
                ),
                "description": "the server success line lands as narrative",
            },
        )
        # Back to the caption-free dock: no pick or exit row renders.
        self.assertEqual(
            page.locator('[data-testid="dialogue-exit"]').count(), 0
        )
        # The ordinary dock rows work again (movement parity after the
        # session): open the Move outlet and press its first exit row.
        self._open_root(page, 0)  # Move -> exit-outlet frame
        _press(page, "Enter")  # first exit -> explore.move
        self.assertEqual(sent_action_count(page, "explore.move"), 1)
        self._wait_panel(
            page,
            "local_map",
            lambda p: p.get("available") is True
            and p["current_node"] != "grid:capital_altoria:2:0",
        )

    @covers_requirement("webclient-exploration-menu::explore-talk-freeform-runs-the-guarded-dialogue-seam-through-an-injected-client")
    def test_freeform_dialogue_degrades_offline_through_the_command_line(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        self._open_root(page, 2)  # Interact
        _press(page, "ArrowRight")  # the bard (second grid column)
        _press(page, "Enter")
        # Vertical affordance navigation (webclient-exploration-menu:
        # "the selected target's heading and its single-column affordance
        # rows hold the second column ... vertical affordance navigation").
        _press(page, "ArrowDown")  # 自由交談 (second affordance row)
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
        # Vertical affordance navigation (webclient-exploration-menu:
        # "single-column affordance rows ... vertical affordance
        # navigation").
        _press(page, "ArrowDown")  # 自由交談 (second affordance row)
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
    @covers_requirement("webclient-frame-resolution::teardown-resets-the-stack-to-the-mode-root-from-one-decision-point")
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
        # Teardown (webclient-declarative-frame-stack): the mode switch
        # replaced the whole exploration stack (root -> interact -> target)
        # with exactly one combat root frame.
        self.assertEqual(
            page.evaluate("() => window.__elosernBridge.router.depth()"),
            1,
            "the combat adoption did not collapse the frame stack to one root",
        )
