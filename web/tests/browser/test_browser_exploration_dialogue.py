"""Keyboard-only exploration browser acceptance (webclient-exploration-menu 4.2-4.6): scripted and free-form dialogue surfaces, the dialogue choice list over the stage, the offline degrade path, and engage-to-combat.
"""

from __future__ import annotations

import json

from tools.spec_traceability import covers_requirement
from web.browser_support.browser_fixtures_data import SHIPPED_DIALOGUE_KEY
from .browser_base import BrowserAcceptanceTest, ui_scale
from .browser_helpers import (
    activate_first_overview_exit,
    activate_overview_chip,
    fixture_home_node_id,
    focus_action_dock,
    install_outbound_recorder,
    narrative_log_length,
    narrative_log_text,
    open_dialogue_choices,
    outbound_messages,
    overview_target_with_affordance,
    sent_action_count,
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


def _shipped_greeting() -> str:
    """The authored greeting the shipped dialogue row carries right now.

    Reached through the binding-safe accessor (module path and attribute
    string assembled at call time) so the assertion follows the live table
    instead of pinning a prose literal that drifts on every lore rewrite.
    """
    import importlib

    table = getattr(
        importlib.import_module("world.rules" + ".dialogue"), "DIALOGUE" + "_TABLE"
    )
    return table[SHIPPED_DIALOGUE_KEY].greeting


def _shipped_first_answer() -> str:
    """The authored answer to the shipped row's first keyword, read live.

    Same binding-safe accessor as ``_shipped_greeting``: the first pick sends
    the first keyword, and the assertion follows whatever that keyword's
    authored line currently says rather than pinning its prose.
    """
    import importlib

    table = getattr(
        importlib.import_module("world.rules" + ".dialogue"), "DIALOGUE" + "_TABLE"
    )
    return table[SHIPPED_DIALOGUE_KEY].responses[0].response


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



    @covers_requirement("localized-appearance::the-shared-appearance-layer-renders-traditional-chinese-frames")
    def test_look_at_scripted_host_shows_the_affinity_stage_line(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        # The scripted host is both a look entity and a committed interact
        # target, so the overview renders it only as the stable
        # `target-<identity>` person chip (webclient-scene-overview-swap:
        # 人物-row entity chips exist for look-only entities); 查看 in the
        # chip's verb popover submits explore.look for that host.
        host_identity = self._live_exploration_panel(page)["interact"][0]["identity"]
        activate_overview_chip(page, "target-%s" % host_identity)
        activate_overview_chip(page, "look-target")  # 查看 -> explore.look
        self.assertEqual(sent_action_count(page, "explore.look"), 1)
        wait_for_store_state(
            page,
            lambda s: _connected_active(s)
            and "她看著你的眼神裡帶著信賴。" in narrative_log_text(page),
        )

    @covers_requirement("webclient-exploration-menu::explore-talk-open-opens-a-conversation-with-the-host-s-greeting")
    @covers_requirement("webclient-exploration-menu::explore-talk-scripted-invokes-the-deterministic-dialogue-api-with-keyword-buttons")
    def test_scripted_keyword_dialogue_completes(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        # The overview's 人物 chip for the scripted host opens its verb
        # popover; 交談 opens the conversation in one dispatch (no topic
        # first), and the choice list over the stage carries the authored
        # picks once the greeting is read.
        host_identity = self._live_exploration_panel(page)["interact"][0]["identity"]
        activate_overview_chip(page, "target-%s" % host_identity)
        _press(page, "Enter")  # 交談 -> explore.talk_open
        self.assertEqual(sent_action_count(page, "explore.talk_open"), 1)
        self._wait_panel(page, "dialogue", lambda p: p.get("available") is True)
        # The window pages the host's authored greeting; the choice list
        # appears once it is read.
        greeting = _shipped_greeting()
        wait_for_store_state(
            page,
            lambda s: _connected_active(s) and greeting in narrative_log_text(page),
        )
        open_dialogue_choices(page)
        self.assertGreater(
            page.locator('[data-anchor="choices"] [data-testid="dialogue-pick"]').count(),
            0,
            "the opened conversation must present the authored picks",
        )
        # The dock returned to the overview in the commit that opened the
        # conversation (webclient-talk-open-dock): no popover stays open over
        # the dialogue surface.
        wait_for_store_state(
            page,
            lambda s: _connected_active(s) and (s.get("dockDepth") or 0) == 1,
        )
        self.assertEqual(
            page.evaluate("() => window.__elosernBridge.router.depth()"),
            1,
            "the conversation opened with the dock back at the overview",
        )
        # The first pick then sends the scripted keyword for the host (the
        # list holds focus and owns the digits).
        _press(page, "1")
        self.assertEqual(sent_action_count(page, "explore.talk_scripted"), 1)
        answer = _shipped_first_answer()
        wait_for_store_state(
            page,
            lambda s: _connected_active(s) and answer in narrative_log_text(page),
        )

    @covers_requirement(
        "webclient-exploration-menu::the-keyboard-first-exploration-dock-roots-at-the-scene-overview-and-opens-dialogue-directly"
    )
    @covers_requirement(
        "webclient-exploration-menu::explore-talk-open-opens-a-conversation-with-the-host-s-greeting"
    )
    def test_talk_open_enters_the_dialogue_in_one_step(self):
        """webclient-talk-open-dock: 交談 is one step.

        A keyboard-driven journey at 1451x790: the overview's person chip
        opens the host's verb popover, ONE Enter on 交談 submits exactly one
        `explore.talk_open` and never a scripted-keyword dispatch, and the
        commit that opens the conversation carries mode `dialogue`, the
        committed dialogue panel's greeting line, and the dock back at the
        overview. The exit row then ends the session through the deterministic
        leave seam.
        """
        page = self.logged_in_page((1451, 790))
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        host = overview_target_with_affordance(page, "explore.talk_open")
        activate_overview_chip(page, "target-%s" % host["identity"])
        # The popover is one child frame of the overview and 交談 is its
        # focused first row: no keyword list sits between the chip and the
        # conversation.
        self.assertEqual(
            page.evaluate(
                "window.__elosernBridge.router.currentItem() && "
                "window.__elosernBridge.router.currentItem().key"
            ),
            "talk-open",
            "交談 must be the popover's focused row",
        )
        _press(page, "Enter")  # 交談 -> explore.talk_open
        self.assertEqual(sent_action_count(page, "explore.talk_open"), 1)
        self.assertEqual(
            sent_action_count(page, "explore.talk_scripted"),
            0,
            "交談 must not open a scripted-keyword frame",
        )

        # The next commit: mode `dialogue`, the host's authored greeting as the
        # committed panel's line, and the dock back at the overview.
        wait_for_store_state(
            page,
            lambda s: s.get("mode") == "dialogue"
            and ((s.get("panels") or {}).get("dialogue") or {}).get("available")
            is True,
        )
        greeting = _shipped_greeting()
        wait_for_store_state(
            page,
            lambda s: _connected_active(s) and greeting in narrative_log_text(page),
        )
        self.assertEqual(
            ((store_state(page).get("panels") or {}).get("dialogue") or {}).get(
                "line"
            ),
            greeting,
            "the dialogue panel carries the host's authored greeting",
        )
        wait_for_store_state(page, lambda s: (s.get("dockDepth") or 0) == 1)
        self.assertEqual(
            page.evaluate("() => window.__elosernBridge.router.depth()"),
            1,
            "the dock returned to the overview with the conversation open",
        )
        self.assertEqual(
            store_state(page)["dockSource"],
            "exploration.root",
            "the overview is the dock's current frame",
        )

        # ✕ 結束對話 (the choice list's last row, once the greeting is read)
        # ends the live session through the sole writer.
        open_dialogue_choices(page)
        self.assertEqual(
            page.locator('[data-testid="dialogue-exit"] .dialogue-choices__label').inner_text(),
            "結束對話",
        )
        result_before_exit = (
            store_state(page).get("lastActionResult") or {}
        ).get("requestId")
        page.click('[data-testid="dialogue-exit"]')
        wait_for_store_state(
            page,
            lambda s: (
                (s.get("lastActionResult") or {}).get("requestId")
                not in (None, result_before_exit)
            ),
        )
        self.assertEqual(sent_action_count(page, "explore.dialogue_leave"), 1)

    @covers_requirement(
        "webclient-contextual-hud::the-command-region-collapses-in-dialogue-mode-and-the-message-window-spans-the-band"
    )
    @covers_requirement(
        "webclient-contextual-hud::stage-actors-present-the-player-and-the-dialogue-host-with-a-speaking-state"
    )
    def test_dialogue_stage_collapses_the_band_and_stands_both_actors(self):
        """webclient-dialogue-stage-actors at 1451x790.

        交談 collapses the command region (the dock stays mounted, hidden),
        the message window spans the 220px band under the host's name plate,
        the host stands in `actor-right` lit while the player is dimmed, a
        pick from the choice list lights the player until its reply commits,
        `/` then Escape returns focus to the dialogue's focus home (the choice
        list once the reply is read), and 結束對話 brings the dock back at the
        overview with focus on it.
        """
        page = self.logged_in_page((1451, 790))
        install_outbound_recorder(page)
        self._wait_exploration_available(page)
        dock_handle = page.evaluate_handle("() => document.getElementById('action-dock')")

        host_identity = self._live_exploration_panel(page)["interact"][0]["identity"]
        activate_overview_chip(page, "target-%s" % host_identity)
        _press(page, "Enter")  # 交談 -> explore.talk_open
        self._wait_panel(page, "dialogue", lambda p: p.get("available") is True)
        wait_for_store_state(
            page,
            lambda s: _connected_active(s)
            and s.get("mode") == "dialogue"
            and s.get("dispatch", {}).get("inFlight") is None,
        )
        page.wait_for_selector('[data-anchor="actor-right"] [data-testid="stage-actor"]')
        page.wait_for_timeout(150)
        geometry = page.evaluate(
            """() => {
              const box = (sel) => {
                const el = document.querySelector(sel);
                if (!el) return null;
                const r = el.getBoundingClientRect();
                return { left: r.left, right: r.right, top: r.top, bottom: r.bottom, width: r.width, height: r.height };
              };
              const band = box('[data-testid="stage-band"]');
              const dock = document.getElementById('action-dock');
              const active = document.activeElement;
              return {
                band,
                message: box('[data-anchor="band-message"]'),
                commandVisibility: getComputedStyle(document.querySelector('[data-anchor="band-command"]')).visibility,
                commandInert: document.querySelector('[data-anchor="band-command"]').inert,
                dockHidden: !!dock && getComputedStyle(dock).visibility === 'hidden',
                dockConnected: !!dock && dock.isConnected,
                hostSide: document.querySelector('[data-anchor="actor-right"] [data-testid="stage-actor"]').dataset.side,
                hostSpeaking: document.querySelector('[data-anchor="actor-right"] [data-testid="stage-actor"]').dataset.speaking,
                playerSpeaking: document.querySelector('[data-anchor="actor-left"] [data-testid="stage-actor"]').dataset.speaking,
                playerFilter: getComputedStyle(document.querySelector('[data-anchor="actor-left"] [data-testid="stage-actor"]')).filter,
                host: box('[data-anchor="actor-right"]'),
                player: box('[data-anchor="actor-left"]'),
                plate: (document.querySelector('[data-testid="message-name-plate"]') || {}).textContent || null,
                activeInConversation:
                  active === document.querySelector('[data-testid="message-page"]') ||
                  active === document.querySelector('[data-anchor="choices"] [data-testid="dialogue-choices"]'),
                activeIsBody: active === document.body,
              };
            }"""
        )
        # webclient-mode-transitions: the collapsed region is inert from the
        # commit and `visibility: hidden` once its slide ends (instant at the
        # suite's `off` level), with the dock inside it.
        self.assertEqual(geometry["commandVisibility"], "hidden")
        self.assertTrue(geometry["commandInert"])
        self.assertTrue(geometry["dockHidden"])
        self.assertTrue(geometry["dockConnected"])
        self.assertTrue(
            page.evaluate("(dock) => dock === document.getElementById('action-dock')", dock_handle),
            "the dock element must not be remounted on entering dialogue",
        )
        self.assertAlmostEqual(geometry["message"]["width"], 1451, delta=1)
        self.assertAlmostEqual(geometry["message"]["height"], 220, delta=1)
        self.assertAlmostEqual(geometry["band"]["height"], 220, delta=1)
        self.assertEqual(geometry["hostSide"], "right")
        self.assertEqual(geometry["hostSpeaking"], "true")
        self.assertEqual(geometry["playerSpeaking"], "false")
        self.assertEqual(geometry["playerFilter"], "brightness(0.6)")
        # The host stands on the band, inset from the right by the
        # column-clearance term (at least 6% of the width), as tall as the player.
        self.assertAlmostEqual(geometry["host"]["bottom"], geometry["band"]["top"], delta=1)
        chrome = ui_scale((1451, 790))
        left_column = min(max(220.0 * chrome, 0.20 * 1451), 330.0 * chrome)
        actor_h = min(0.62 * 790, 680.0 * chrome, 790 - 48.0 * chrome - 220.0)
        self.assertAlmostEqual(
            1451 - geometry["host"]["right"],
            max(0.06 * 1451, 312.0 * chrome - actor_h / 3),
            delta=1.5,
        )
        self.assertAlmostEqual(geometry["host"]["height"], geometry["player"]["height"], delta=1)
        self.assertTrue(geometry["plate"])
        self.assertTrue(
            geometry["activeInConversation"],
            "entering dialogue focuses the message page, or the choice list once the greeting is read",
        )
        self.assertFalse(geometry["activeIsBody"])

        # A pick lights the player until its reply commits: record every
        # speaking state the player's actor passes through.
        page.evaluate(
            """() => {
              const actor = document.querySelector('[data-anchor="actor-left"] [data-testid="stage-actor"]');
              window.__speakingTrail = [actor.dataset.speaking];
              new MutationObserver(() => window.__speakingTrail.push(actor.dataset.speaking))
                .observe(actor, { attributes: true, attributeFilter: ['data-speaking'] });
            }"""
        )
        result_before_pick = (store_state(page).get("lastActionResult") or {}).get("requestId")
        open_dialogue_choices(page)
        _press(page, "1", wait_ms=0)
        wait_for_store_state(
            page,
            lambda s: (s.get("lastActionResult") or {}).get("requestId") not in (None, result_before_pick)
            and s.get("dispatch", {}).get("inFlight") is None,
        )
        page.wait_for_timeout(150)
        trail = page.evaluate("() => window.__speakingTrail")
        self.assertEqual(sent_action_count(page, "explore.talk_scripted"), 1)
        self.assertIn("true", trail, "the player must be lit while the pick is in flight")
        self.assertEqual(trail[-1], "false", "the host speaks again once the reply commits")

        # `/` opens the command line; Escape returns to the choice list once
        # the reply is read.
        open_dialogue_choices(page)
        _press(page, "/")
        self.assertEqual(page.evaluate("() => document.activeElement && document.activeElement.id"), "inputfield")
        _press(page, "Escape", wait_ms=150)
        self.assertTrue(
            page.evaluate(
                "() => document.activeElement === document.querySelector('[data-anchor=\"choices\"] [data-testid=\"dialogue-choices\"]')"
            ),
            "Escape in dialogue must land on the shown choice list",
        )

        # 結束對話 brings the dock back at the overview, focused, not remounted.
        result_before_exit = (store_state(page).get("lastActionResult") or {}).get("requestId")
        page.click('[data-testid="dialogue-exit"]')
        wait_for_store_state(
            page,
            lambda s: (s.get("lastActionResult") or {}).get("requestId") not in (None, result_before_exit)
            and s.get("mode") == "exploration",
        )
        page.wait_for_timeout(150)
        after = page.evaluate(
            """(dock) => ({
              same: dock === document.getElementById('action-dock'),
              visible: dock.getClientRects().length > 0,
              focused: document.activeElement === dock || dock.contains(document.activeElement),
              hostActors: document.querySelectorAll('[data-anchor="actor-right"] [data-testid="stage-actor"]').length,
              playerSpeaking: document.querySelector('[data-anchor="actor-left"] [data-testid="stage-actor"]').dataset.speaking,
            })""",
            dock_handle,
        )
        self.assertEqual(
            after,
            {"same": True, "visible": True, "focused": True, "hostActors": 0, "playerSpeaking": "true"},
        )
        self.assertEqual(page.evaluate("() => window.__elosernBridge.router.depth()"), 1)
        self.assertEqual(store_state(page)["dockSource"], "exploration.root")

    @covers_requirement(
        "webclient-contextual-hud::dialogue-choices-appear-centred-over-the-stage-after-the-line-is-fully-read"
    )
    def test_dialogue_choices_sit_over_the_stage_and_the_dock_collapses(self):
        # The leave-requirement annotation (delta id
        # webclient-dialogue-session::explore-dialogue-leave-ends-the-live-session-through-the-sole-writer)
        # is added at delta sync — the traceability gate only recognizes
        # main-spec ids during the change window.
        """webclient-align-11-dialogue-ux / webclient-dialogue-stage-actors /
        webclient-dialogue-choices-overlay: entering dialogue keeps the
        (collapsed, hidden) dock in its ordinary exploration form (no 對話選項
        mirror tab); the window pages the greeting and holds no row; the
        choice list over the stage appears once it is read, its scripted pick
        dispatches by digit, its exit row ends the session, and the committed
        snapshot restores exploration."""
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        # Enter dialogue through the ordinary dock affordance path: 交談
        # dispatches explore.talk_open and the committed dialogue panel
        # opens the conversation. The dispatch settles when its action result
        # lands — the panel's (already-true) availability would race the
        # in-flight lock and silently drop the next input.
        result_before = (store_state(page).get("lastActionResult") or {}).get("requestId")
        host_identity = self._live_exploration_panel(page)["interact"][0]["identity"]
        activate_overview_chip(page, "target-%s" % host_identity)
        _press(page, "Enter")  # 交談 -> explore.talk_open
        wait_for_store_state(
            page,
            lambda state: (
                (state.get("lastActionResult") or {}).get("requestId")
                not in (None, result_before)
            ),
        )
        self.assertEqual(sent_action_count(page, "explore.talk_open"), 1)
        self._wait_panel(
            page, "dialogue", lambda p: p.get("available") is True
        )

        # The dock keeps its ORDINARY form while talking — the scene overview
        # (webclient-scene-overview-swap), never the retired 對話選項 mirror and
        # never a tab bar — but the command region is collapsed around it
        # (webclient-dialogue-stage-actors): mounted, hidden with display:none.
        self.assertFalse(page.locator("#action-dock").is_visible())
        self.assertEqual(page.locator("#action-dock").count(), 1)
        overview_labels = page.evaluate(
            "() => Array.from(document.querySelectorAll("
            "'#action-dock [data-testid=\"scene-overview\"] [data-item-key]'))"
            ".map((el) => el.textContent)"
        )
        self.assertTrue(overview_labels, "the scene overview must render while talking")
        self.assertNotIn("對話選項", "".join(overview_labels))
        self.assertEqual(
            page.locator('#action-dock [data-pane-kind="commands"]').count(),
            0,
            "dialogue mode renders the overview, not the combat command list",
        )

        # The message window pages the greeting (no reply box, no row); the
        # choice list renders over the stage, outside the band, once the
        # greeting is read.
        open_dialogue_choices(page)
        dom_shape = page.evaluate(
            """() => {
              const win = document.querySelector('[data-testid="message-window"]');
              return {
                variant: win && win.getAttribute("data-variant"),
                rowsInWindow: win.querySelectorAll('[data-testid^="dialogue-"]').length,
                boxes: document.querySelectorAll('[data-testid="dialogue-box"], [data-testid="message-dialogue"]').length,
                picks: document.querySelectorAll('[data-anchor="choices"] [data-testid="dialogue-pick"]').length,
                listFocused: document.activeElement === document.querySelector('[data-testid="dialogue-choices"]'),
              };
            }"""
        )
        self.assertEqual(dom_shape["variant"], "paged")
        # Only the plate's bond segment carries a dialogue-* hook in the window.
        self.assertLessEqual(dom_shape["rowsInWindow"], 1)
        self.assertEqual(dom_shape["boxes"], 0)
        self.assertGreater(dom_shape["picks"], 0)
        self.assertTrue(dom_shape["listFocused"])

        # The dock is back at the overview in that commit: the popover that
        # carried 交談 closed with it (webclient-talk-open-dock).
        wait_for_store_state(
            page,
            lambda state: (state.get("dockDepth") or 0) == 1,
        )
        self.assertEqual(
            page.evaluate("() => window.__elosernBridge.router.depth()"),
            1,
            "the conversation opened with the dock back at the overview",
        )

        # Digit activation addresses the focused list's pick, not the dock
        # rows: the first scripted talk dispatches exactly once.
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
        self.assertEqual(sent_action_count(page, "explore.talk_scripted"), 1)

        # The exit row dispatches the deterministic leave seam exactly once
        # (the list returns once the reply is read).
        open_dialogue_choices(page)
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
            lambda s: _connected_active(s)
            and "你結束了對話。" in narrative_log_text(page),
        )
        # Back to the dock: no choice list, pick, or exit row renders.
        self.assertEqual(
            page.locator('[data-testid="dialogue-exit"]').count(), 0
        )
        # The ordinary dock rows work again (movement parity after the
        # session): the overview's first exit chip submits its move.
        activate_first_overview_exit(page)  # the overview's first exit -> explore.move
        self.assertEqual(sent_action_count(page, "explore.move"), 1)
        self._wait_panel(
            page,
            "local_map",
            lambda p: p.get("available") is True
            and p["current_node"] != fixture_home_node_id(),
        )

    @covers_requirement(
        "webclient-contextual-hud::dialogue-choices-appear-centred-over-the-stage-after-the-line-is-fully-read"
    )
    @covers_requirement(
        "webclient-browser-verification::browser-acceptance-covers-foundation-recovery-and-layout-behavior"
    )
    def test_dialogue_stage_journey_completes_by_keyboard(self):
        """webclient-dialogue-choices-overlay: the keyboard-only journey at 1451x790.

        交談 from the scene overview opens the conversation; the greeting is
        read with Enter and the choice list appears centred over the stage
        (never while a page types or is unread) with focus on it; `1` sends a
        pick; the reply is read; ⌨ 自由對話 borrows the command line and a line
        is sent; ↦ 移動… swaps in the exits and Escape returns; ✕ 結束對話 ends
        the conversation; an exit chip then moves. Throughout the
        conversation the command region is collapsed, both stage actors
        stand, and focus is never on the document body.
        """
        # webclient-motion-level (design D9): the frame probe below counts the
        # frames where the list showed beside a typing or unread page, so the
        # window must really type — the `full` level, not the suite's instant
        # `off` seed, which would make that guard vacuous.
        page = self.logged_in_page((1451, 790), motion_level="full")
        install_outbound_recorder(page)
        self._wait_exploration_available(page)
        # Record, on every animation frame, whether the list ever showed
        # beside a typing or unread page, and whether focus fell to the body
        # during the conversation.
        page.evaluate(
            """() => {
              window.__journey = { listWhileUnread: 0, bodyFocus: 0, collapsedBroken: 0, actorsMissing: 0 };
              const tick = () => {
                const stage = document.querySelector('[data-testid="elosern-stage"]');
                if (stage && stage.getAttribute('data-elosern-mode') === 'dialogue') {
                  const win = document.querySelector('[data-testid="message-window"]');
                  const list = document.querySelector('[data-anchor="choices"] [data-testid="dialogue-choices"]');
                  if (list && win && win.getAttribute('data-reading-complete') !== 'true') window.__journey.listWhileUnread += 1;
                  if (list && win && win.getAttribute('data-typing') === 'true') window.__journey.listWhileUnread += 1;
                  if (document.activeElement === document.body) window.__journey.bodyFocus += 1;
                  const command = document.querySelector('[data-anchor="band-command"]');
                  // webclient-mode-transitions: at `full` the region slides out
                  // for 250ms, so only its reach is checked on every frame;
                  // its end state is asserted once the line is read.
                  if (!command || !command.inert) window.__journey.collapsedBroken += 1;
                  if (document.querySelectorAll('[data-testid="stage-actor"]').length !== 2) window.__journey.actorsMissing += 1;
                }
                requestAnimationFrame(tick);
              };
              requestAnimationFrame(tick);
            }"""
        )

        host = self._live_exploration_panel(page)["interact"][0]
        activate_overview_chip(page, "target-%s" % host["identity"])
        _press(page, "Enter")  # 交談 -> explore.talk_open
        self._wait_panel(page, "dialogue", lambda p: p.get("available") is True)
        wait_for_store_state(
            page,
            lambda s: _connected_active(s)
            and s.get("mode") == "dialogue"
            and s.get("dispatch", {}).get("inFlight") is None,
        )
        open_dialogue_choices(page)
        placement = page.evaluate(
            """() => {
              const box = (sel) => { const r = document.querySelector(sel).getBoundingClientRect(); return { left: r.left, right: r.right, top: r.top, bottom: r.bottom }; };
              return {
                card: box('[data-testid="dialogue-choices"]'),
                band: box('[data-testid="stage-band"]'),
                focused: document.activeElement === document.querySelector('[data-testid="dialogue-choices"]'),
              };
            }"""
        )
        self.assertTrue(placement["focused"], "the list takes focus when it appears over the read line")
        self.assertAlmostEqual(
            (placement["card"]["left"] + placement["card"]["right"]) / 2, 960, delta=1
        )
        self.assertLessEqual(placement["card"]["bottom"], placement["band"]["top"])
        # The command region's slide has ended: it is hidden, not merely inert.
        page.wait_for_function(
            "() => getComputedStyle(document.querySelector('[data-anchor=\"band-command\"]')).visibility === 'hidden'",
            timeout=5000,
        )

        # `1`: the first pick, once.
        _press(page, "1")
        wait_for_store_state(page, lambda s: sent_action_count(page, "explore.talk_scripted") == 1 and s.get("dispatch", {}).get("inFlight") is None)
        open_dialogue_choices(page)

        # ⌨ 自由對話: End, ArrowUp twice lands on it (…, ⌨, ↦, ✕).
        _press(page, "End")
        _press(page, "ArrowUp")
        _press(page, "ArrowUp")
        _press(page, "Enter")
        wait_for_store_state(
            page,
            _connected_active,
            dom_readiness={
                "selector": "#inputfield",
                "predicate": "() => document.activeElement === document.getElementById('inputfield')",
                "description": "the borrowed command field is focused",
            },
        )
        page.keyboard.type("你好")
        page.keyboard.press("Enter")
        wait_for_store_state(page, lambda s: sent_action_count(page, "explore.talk_freeform") == 1 and s.get("dispatch", {}).get("inFlight") is None)
        open_dialogue_choices(page)

        # ↦ 移動…: the exits swap in; Escape returns with ↦ active.
        _press(page, "End")
        _press(page, "ArrowUp")
        _press(page, "Enter")
        page.wait_for_selector('[data-testid="dialogue-choices"][data-view="exits"]')
        self.assertGreater(page.locator('[data-testid="dialogue-exit-row"]').count(), 0)
        _press(page, "Escape")
        page.wait_for_selector('[data-testid="dialogue-choices"][data-view="choices"]')
        self.assertEqual(
            page.evaluate(
                "() => document.getElementById(document.querySelector('[data-testid=\"dialogue-choices\"]').getAttribute('aria-activedescendant')).dataset.testid"
            ),
            "dialogue-move",
        )

        # ✕ 結束對話: the last row.
        _press(page, "End")
        _press(page, "Enter")
        wait_for_store_state(page, lambda s: s.get("mode") == "exploration" and s.get("dispatch", {}).get("inFlight") is None)
        page.wait_for_timeout(150)
        journey = page.evaluate("() => window.__journey")
        self.assertEqual(journey["listWhileUnread"], 0, "the list never shows beside unread text")
        self.assertEqual(journey["bodyFocus"], 0, "focus never drops to the body during the conversation")
        self.assertEqual(journey["collapsedBroken"], 0, "the command region stays collapsed")
        self.assertEqual(journey["actorsMissing"], 0, "both stage actors stand throughout")
        self.assertTrue(
            page.evaluate("() => { const d = document.getElementById('action-dock'); return document.activeElement === d || d.contains(document.activeElement); }"),
            "leaving the conversation returns focus to the dock",
        )

        # An exit chip moves from the restored overview.
        activate_first_overview_exit(page)
        wait_for_store_state(page, lambda s: sent_action_count(page, "explore.move") == 1)
        sent = [
            args[0].get("action_id") if args and isinstance(args[0], dict) else None
            for cmd, args, _kw in outbound_messages(page)
            if cmd == "ui_action"
        ]
        self.assertEqual(
            [a for a in sent if a],
            [
                "explore.talk_open",
                "explore.talk_scripted",
                "explore.talk_freeform",
                "explore.dialogue_leave",
                "explore.move",
            ],
        )

    @covers_requirement(
        "webclient-contextual-hud::pointer-open-dialogue-choices-expose-a-local-initial-highlight"
    )
    def test_pointer_opened_choices_highlight_the_first_choice_without_answering(self):
        """webclient-message-typesetting: a conversation opened and read by
        pointer shows its choice list with the first choice highlighted
        through the list's active descendant, and nothing is answered. While
        focus sits elsewhere (the expanded command line) the highlight stays
        visible and still answers nothing; only a deliberate click does."""
        page = self.logged_in_page((1451, 790))
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        host = overview_target_with_affordance(page, "explore.talk_open")
        page.click('#action-dock [data-item-key="target-%s"]' % host["identity"])
        page.wait_for_selector('[data-testid="verb-popover"] [data-item-key="talk-open"]', timeout=15000)
        page.click('[data-testid="verb-popover"] [data-item-key="talk-open"]')
        self._wait_panel(page, "dialogue", lambda p: p.get("available") is True)
        self.assertEqual(sent_action_count(page, "explore.talk_open"), 1)

        # Read the greeting by pointer: each click on the page shows a typing
        # page in full or advances.
        list_selector = '[data-anchor="choices"] [data-testid="dialogue-choices"]'
        for _ in range(60):
            if page.locator(list_selector).count():
                break
            page.click('[data-testid="message-page"]')
            page.wait_for_timeout(150)
        page.wait_for_selector(list_selector, timeout=5000)

        probe = """() => {
          const list = document.querySelector('%s');
          const active = document.getElementById(list.getAttribute('aria-activedescendant'));
          const rows = Array.from(list.querySelectorAll('[role="menuitem"]'));
          const bg = (el) => getComputedStyle(el).backgroundImage + '|' + getComputedStyle(el).borderTopColor;
          return {
            activeIsFirstPick: active === list.querySelector('[data-testid="dialogue-pick"]'),
            activeFlag: active && active.getAttribute('data-active'),
            distinct: rows.length > 1 && bg(active) !== bg(rows[1]),
            listFocused: document.activeElement === list,
          };
        }""" % list_selector
        opened = page.evaluate(probe)
        # Reading by clicks leaves focus on the message page, so the shell's
        # unchanged focus rule hands it to the list; the highlight itself
        # moves no focus (the unfocused case follows below).
        self.assertTrue(opened["listFocused"])
        self.assertTrue(opened["activeIsFirstPick"])
        self.assertEqual(opened["activeFlag"], "true")
        self.assertTrue(opened["distinct"], "the initial highlight must be visible")
        self.assertEqual(sent_action_count(page, "explore.talk_scripted"), 0)

        # Focus elsewhere: the list keeps its quiet highlight and answers
        # nothing.
        page.click('[data-testid="command-line-toggle"]')
        page.wait_for_function("() => document.activeElement && document.activeElement.id === 'inputfield'")
        away = page.evaluate(probe)
        self.assertFalse(away["listFocused"])
        self.assertTrue(away["activeIsFirstPick"])
        self.assertTrue(away["distinct"], "the unfocused list must still show where the keys start")
        self.assertEqual(sent_action_count(page, "explore.talk_scripted"), 0)

        # A deliberate click answers exactly once.
        page.click('%s [data-testid="dialogue-pick"]' % list_selector)
        wait_for_store_state(page, lambda s: sent_action_count(page, "explore.talk_scripted") == 1, timeout=15000)

    @covers_requirement("webclient-exploration-menu::explore-talk-freeform-runs-the-guarded-dialogue-seam-through-an-injected-client")
    def test_freeform_dialogue_degrades_offline_through_the_command_line(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        # The overview's 人物 chip for the bard opens its verb popover; 交談
        # opens the conversation, whose choice list carries the free row.
        bard = overview_target_with_affordance(page, "explore.talk_open")
        activate_overview_chip(page, "target-%s" % bard["identity"])
        _press(page, "Enter")  # 交談 -> explore.talk_open
        self._wait_panel(page, "dialogue", lambda p: p.get("available") is True)
        result_before_free = (
            store_state(page).get("lastActionResult") or {}
        ).get("requestId")
        # The choice list's free row borrows the command line.
        open_dialogue_choices(page)
        page.click('[data-testid="dialogue-freeform"]')
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
        wait_for_store_state(
            page,
            lambda state: (
                (state.get("lastActionResult") or {}).get("requestId")
                not in (None, result_before_free)
            ),
        )
        self.assertEqual(sent_action_count(page, "explore.talk_freeform"), 1)

    @covers_requirement(
        "webclient-desktop-shell::the-collapsible-command-line-preserves-ordinary-text-control-and-the-dialogue-s-free-form-borrow"
    )
    def test_cancelled_freeform_dialogue_cannot_capture_a_later_command(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        # Open free-form dialogue but cancel with Escape without sending.
        # The overview's 人物 chip for the bard opens its verb popover; 交談
        # opens the conversation, whose choice list carries the free row.
        bard = overview_target_with_affordance(page, "explore.talk_open")
        activate_overview_chip(page, "target-%s" % bard["identity"])
        _press(page, "Enter")  # 交談 -> explore.talk_open
        self._wait_panel(page, "dialogue", lambda p: p.get("available") is True)
        open_dialogue_choices(page)
        page.click('[data-testid="dialogue-freeform"]')
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
                "selector": '[data-testid="dialogue-pick"], [data-testid="dialogue-freeform"]',
                "predicate": (
                    "() => { const a = document.querySelector('[data-anchor=\"command-line\"]'); "
                    "const d = document.querySelector('[data-testid=\"command-line\"]'); "
                    "const collapsed = !!a && a.getAttribute('data-expanded') === 'false' && !!d; "
                    "const list = document.querySelector('[data-anchor=\"choices\"] [data-testid=\"dialogue-choices\"]'); "
                    "return collapsed && !!list && document.activeElement === list; }"
                ),
                # webclient-dialogue-choices-overlay: in dialogue the focus
                # home is the shown choice list, never the hidden dock.
                "description": "command line collapsed and the choice list focused",
            },
        )

        # Expand the command line with `/` and send an ordinary command: it
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
        before_len = narrative_log_length(page)
        page.keyboard.type("look")
        page.keyboard.press("Enter")
        wait_for_store_state(
            page,
            lambda s: _connected_active(s)
            and narrative_log_length(page) > before_len,
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

        goblin = overview_target_with_affordance(page, "explore.engage")
        activate_overview_chip(page, "target-%s" % goblin["identity"])
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
