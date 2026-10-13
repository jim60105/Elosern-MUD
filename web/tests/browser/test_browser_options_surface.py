"""Suggestions-surface browser acceptance (webclient-options-surface).

These journeys drive the real Evennia server's exploration suggestions
surface — since exploration-room-actions the 建議 pill in the command panel
and the centred suggestions card it opens: the four status renders (the muted generating line, the ready card
set with the dismiss control, degraded rule cards with the muted note, and
unavailable after dismiss), exact card execution envelopes through the action
client, the section-only re-render without a dock rebuild, the sub-dock
ownership gate, and the deterministic per-test resets.

One server boots per test class (no combat sessions are started, so one server
is safe; every journey resets the character through the superuser ``@tel``
command). Every fixture is deterministic: the ``action_options`` client is the
browser-settings replay double (a fixed plaza OptionSet after a short reactor
delay so ``generating`` stays observable, and a scripted empty-ground
transport failure for the degraded path), and journeys wait on the store's
``context_actions.suggestions.status`` instead of timing sleeps.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    PILL_SELECTOR,
    SUGGESTIONS_CARD_SELECTOR,
    activate_first_compass_exit,
    install_outbound_recorder,
    open_suggestions_card,
    narrative_log_text,
    sent_action_count,
    store_state,
    wait_for_store_state,
)
from .harness import ManagedServer
from . import fixtures
from .test_browser_input_narrative import _wait_inp_line

GENERATING_LINE = "AI 正在構思建議…"
DEGRADED_NOTE = "AI 建議目前不可用"
EMPTY_STATE_LINE = "現在沒有什麼值得做的動作"
PLAZA_ROOM = "選項測試廣場"

EXPECTED_READY_LABELS = ("查看四周", "前往南門", "我們聊聊好嗎？", "試試身手")


def _press(page, key, wait_ms=80):
    page.keyboard.press(key)
    page.wait_for_timeout(wait_ms)


class OptionsSurfaceBrowserTest(BrowserAcceptanceTest):
    """Boots one dedicated isolated server per class with the options-surface fixture.

    The fixture env lives on the runtime (never the process environment), so a
    sibling test file in the same process is never affected. No combat session
    is started on the server, so one server per class is safe; every journey
    resets the character to the seeded 選項測試廣場 room through the superuser
    ``@tel`` command.
    """

    @classmethod
    def setUpClass(cls) -> None:
        runtime = fixtures.create_runtime(prefix="elosern-options-")
        runtime.env["ELOSERN_BROWSER_OPTIONS_SURFACE"] = "1"
        # Boot mode: SHIPPED catalogs (explicit override of the harness
        # synthetic default, per the creation/action-feedback precedent).
        # These journeys assert shipped fixture identity end to end and were
        # never migrated to kit seams.
        runtime.env["ELOSERN_BROWSER_SYNTH_CATALOGS"] = "0"

        cls.server = ManagedServer(runtime=runtime)
        cls.server.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.runtime.http_port}"
        cls.webclient_url = cls.server.runtime.webclient_url

    @classmethod
    def tearDownClass(cls) -> None:
        if getattr(cls, "server", None) is not None:
            try:
                cls.server.stop()
            finally:
                cls.server = None

    # -- store/DOM helpers ---------------------------------------------------

    def _suggestions(self, page):
        panel = store_state(page)["panels"].get("context_actions")
        return panel.get("suggestions") if panel else None

    def _wait_suggestions(self, page, status, timeout=30000):
        def _status_reached(state):
            suggestions = (state.get("panels") or {}).get("context_actions", {}).get("suggestions")
            return suggestions is not None and suggestions.get("status") == status

        wait_for_store_state(page, _status_reached, timeout=timeout)

    def _section(self, page):
        """The suggestions card is shown with its content (rows or notes)
        while no re-homed sub-dock owns the surface."""
        return page.evaluate(
            """(selector) => {
                const s = (window.__elosernBridge && window.__elosernBridge.store.view) || {};
                const card = document.querySelector(selector);
                const hasContent = card !== null && card.querySelector(
                    '[data-testid="suggestions-card-row"], [data-testid="choice-card-note"], [data-testid="suggestions-card-dismiss"]') !== null;
                return (s.activeSubDock || null) === null && hasContent;
            }""",
            SUGGESTIONS_CARD_SELECTOR,
        )

    def _open_suggestions_pane(self, page):
        open_suggestions_card(page)
        page.wait_for_timeout(60)

    def _wait_section(self, page, timeout=30000):
        def _section_shown(state):
            suggestions = (state.get("panels") or {}).get("context_actions", {}).get("suggestions")
            return suggestions is not None and suggestions.get("status") in ("generating", "ready", "degraded")

        wait_for_store_state(
            page,
            _section_shown,
            dom_readiness={
                "selector": '#action-dock',
                "predicate": (
                    "() => document.querySelector('%s') !== null "
                    "|| document.querySelector('%s') !== null" % (PILL_SELECTOR, SUGGESTIONS_CARD_SELECTOR)
                ),
                "description": "the suggestions surface is present: the 建議 pill, or the "
                "suggestions card when it is open",
            },
            timeout=timeout,
        )

    def _wait_section_gone(self, page, timeout=30000):
        def _section_hidden(state):
            suggestions = (state.get("panels") or {}).get("context_actions", {}).get("suggestions")
            return suggestions is None or suggestions.get("status") == "unavailable"

        wait_for_store_state(
            page,
            _section_hidden,
            dom_readiness={
                "selector": PILL_SELECTOR,
                "predicate": (
                    "() => document.querySelector('%s') === null && document.querySelector('%s') === null"
                    % (PILL_SELECTOR, SUGGESTIONS_CARD_SELECTOR)
                ),
                "description": "the 建議 pill and the suggestions card have disappeared",
            },
            timeout=timeout,
        )

    def _wait_generating_line(self, page, timeout=30000):
        def _generating(state):
            suggestions = (state.get("panels") or {}).get("context_actions", {}).get("suggestions")
            return suggestions is not None and suggestions.get("status") == "generating"

        wait_for_store_state(
            page,
            _generating,
            dom_readiness={
                "selector": PILL_SELECTOR,
                "predicate": "() => document.querySelector('%s') !== null" % PILL_SELECTOR,
                "description": "the 建議 pill is rendered before opening the generating card",
            },
            timeout=timeout,
        )
        self._open_suggestions_pane(page)
        note = SUGGESTIONS_CARD_SELECTOR + ' [data-testid="choice-card-note"]'
        wait_for_store_state(
            page,
            _generating,
            dom_readiness={
                "selector": note,
                "predicate": "() => document.querySelector('%s') !== null" % note,
                "description": "the generating note is rendered on the suggestions card",
            },
            timeout=timeout,
        )
        return page.locator(note).first.inner_text()

    def _ready_card_labels(self, page):
        self._open_suggestions_pane(page)
        return page.evaluate(
            """(selector) => Array.from(
                document.querySelectorAll(
                    selector + ' [data-testid="suggestions-card-row"] .choice-card__label'))
                .map((el) => el.innerText)""",
            SUGGESTIONS_CARD_SELECTOR,
        )

    def _card_rows(self, page):
        return page.locator(SUGGESTIONS_CARD_SELECTOR + ' [data-testid="suggestions-card-row"]')

    def _dismiss_rows(self, page):
        return page.locator(SUGGESTIONS_CARD_SELECTOR + ' [data-testid="suggestions-card-dismiss"]')

    def _sent_actions(self, page, action_id):
        sent = page.evaluate("window.__elosernSent || []")
        return [
            args[0].get("payload")
            for cmd, args, _kwargs in sent
            if cmd == "ui_action" and args and args[0].get("action_id") == action_id
        ]

    def _narrative_inp_count(self, page):
        page.locator('[data-testid="message-log-open"]').click()
        page.wait_for_selector('[data-testid="fulllog-overlay"]', timeout=15000)
        count = page.locator('[data-testid="fulllog-overlay"] .inp').count()
        page.locator('[data-testid="fulllog-close"]').click()
        page.wait_for_selector('[data-testid="fulllog-overlay"]', state="detached", timeout=15000)
        return count

    # -- journey helpers -----------------------------------------------------

    def _teleport_to_plaza(self, page):
        """Return the character to the seeded plaza through the superuser
        ``@tel`` command; the ui_sync trigger then regenerates the plaza
        situation for the fresh session."""
        page.evaluate(
            "(room) => Evennia.msg('text', ['@tel ' + room], {})", PLAZA_ROOM
        )

    def _dismiss(self, page):
        self._open_suggestions_pane(page)
        self._dismiss_rows(page).click()

    def _open_plaza_page(self):
        """A logged-in page whose session displays the ready plaza card set."""
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._teleport_to_plaza(page)
        self._wait_suggestions(page, "ready")
        self._wait_section(page)
        self._open_suggestions_pane(page)
        return page


    def _move_to_empty_ground(self, page):
        """Walk through the dock from the plaza to the empty-ground room (the
        scripted transport-failure room, same journey as the surface file).

        The room's first exit (前往測試空地, exit ``44``) is moved through on
        the exit compass, which dispatches ``explore.move`` into the empty
        ground.
        """
        # The compass's first exit IS 前往測試空地: moving through it
        # dispatches explore.move without pushing a frame
        # (exploration-exit-compass), so the router stays at depth 1 and the
        # suggestions section remains visible to the assertions.
        activate_first_compass_exit(page)
        self._wait_suggestions(page, "degraded")

    # -- journeys ------------------------------------------------------------

    @covers_requirement(
        "webclient-options-surface::the-exploration-dock-renders-the-suggestions-section-from-the-validated-v5-panel"
    )
    def test_login_shows_generating_line_then_ready_cards(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        # Settle the initial flow, then clear the session display so the
        # teleport below forces a fresh plaza generation whose 1.5s window
        # keeps the transient generating line observable.
        self._wait_suggestions(page, "ready")
        self._wait_section(page)
        self._dismiss(page)
        self._wait_suggestions(page, "unavailable")
        self._wait_section_gone(page)
        self._teleport_to_plaza(page)

        line = self._wait_generating_line(page)
        self.assertEqual(line, GENERATING_LINE)
        self.assertEqual(
            self._card_rows(page).count(),
            0,
            "the generating render carries no cards and no dismiss control",
        )
        self.assertEqual(self._dismiss_rows(page).count(), 0)
        self.assertEqual(page.locator(PILL_SELECTOR).inner_text().strip(), "建議")

        self._wait_suggestions(page, "ready")
        self._wait_section(page)
        self.assertEqual(self._ready_card_labels(page), list(EXPECTED_READY_LABELS))
        self.assertEqual(
            self._dismiss_rows(page).count(),
            1,
            "the ready render carries the dismiss control",
        )
        self.assertEqual(
            page.locator(PILL_SELECTOR).get_attribute("aria-label"),
            "建議 %d" % len(EXPECTED_READY_LABELS),
        )
        # Only the dismissal's own OOB action crossed the wire.
        self.assertEqual(sent_action_count(page, "options.dismiss"), 1)
        self.assertEqual(sent_action_count(page), 1)

    @covers_requirement(
        "webclient-options-surface::the-exploration-dock-renders-the-suggestions-section-from-the-validated-v5-panel"
    )
    def test_suggestions_only_update_rerenders_section_without_dock_rebuild(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        # The class run shares one ManagedServer across 10 tests; the plaza
        # suggestions "ready" generation can exceed the default 30s deadline
        # under load, so use a bounded, longer deadline.
        self._wait_suggestions(page, "ready", timeout=60000)
        self._wait_section(page)
        self._dismiss(page)
        self._wait_suggestions(page, "unavailable")
        self._teleport_to_plaza(page)
        self._wait_generating_line(page)

        # The generating push changed only the suggestions content: the open
        # suggestions card and the keyboard router must be untouched — the
        # ready cards replace the muted note in place on the same card.
        captured = page.evaluate(
            """(selector) => {
                window.__menuNode = document.querySelector(selector);
                return window.__menuNode !== null;
            }""",
            SUGGESTIONS_CARD_SELECTOR,
        )
        self.assertTrue(captured, "the suggestions card must be open")
        depth = page.evaluate("window.__elosernBridge.router.depth()")

        self._wait_suggestions(page, "ready", timeout=60000)
        stable = page.evaluate(
            """(selector) => {
                const menu = document.querySelector(selector);
                return window.__menuNode === menu && window.__menuNode.isConnected;
            }""",
            SUGGESTIONS_CARD_SELECTOR,
        )
        self.assertTrue(
            stable,
            "a suggestions-only update must re-render the section in place, "
            "never rebuild the dock",
        )
        self.assertEqual(
            page.evaluate("window.__elosernBridge.router.depth()"),
            depth,
            "the keyboard router must not be reset by a suggestions-only update",
        )
        self.assertEqual(self._ready_card_labels(page), list(EXPECTED_READY_LABELS))

    @covers_requirement(
        "webclient-options-surface::suggestion-cards-execute-exact-envelopes-through-the-action-client"
    )
    def test_known_card_click_dispatches_the_exact_envelope(self):
        page = self._open_plaza_page()
        inp_before = self._narrative_inp_count(page)

        # Keyboard activation on the focused card: its first row is active.
        page.locator(SUGGESTIONS_CARD_SELECTOR).focus()
        page.keyboard.press("Enter")

        self.assertEqual(self._sent_actions(page, "explore.look"), [{"room": True}])
        self.assertEqual(sent_action_count(page, "explore.look"), 1)
        # The look result settles into the narrative.
        def _looked_result(state):
            result = state.get("lastActionResult")
            return result is not None and result.get("code") == "looked"

        wait_for_store_state(
            page,
            lambda s: _looked_result(s) and "燈籠" in narrative_log_text(page),
        )
        self.assertEqual(
            self._narrative_inp_count(page),
            inp_before,
            "a card dispatch must never echo a command line",
        )

    @covers_requirement(
        "webclient-options-surface::suggestion-cards-execute-exact-envelopes-through-the-action-client"
    )
    def test_freeform_card_sends_speech_label(self):
        page = self._open_plaza_page()
        inp_before = self._narrative_inp_count(page)

        panel = store_state(page)["panels"]["context_actions"]
        freeform_entry = next(
            entry
            for entry in panel["affordances"]
            if entry["action_id"] == "explore.talk_freeform"
        )
        # The echoed line composes its NPC label verbatim from the committed
        # exploration panel (the store's central descriptor fill), so the
        # expected text is read from the same committed state, never invented.
        npc_name = next(
            target["display_name"]
            for target in store_state(page)["panels"]["exploration"]["interact"]
            if str(target["identity"]) == str(freeform_entry["params"]["npc_id"])
        )
        self._card_rows(page).filter(has_text="我們聊聊好嗎？").click()

        self.assertEqual(
            self._sent_actions(page, "explore.talk_freeform"),
            [
                {
                    "npc_id": freeform_entry["params"]["npc_id"],
                    "speech": "我們聊聊好嗎？",
                }
            ],
        )
        self.assertEqual(sent_action_count(page, "explore.talk_freeform"), 1)
        # The dialogue seam settles deterministically (the npc_dialogue
        # profile is disabled in the harness): the adapter's outcome lands in
        # the stable live region. The Vue app keeps the OOB result in the
        # store (the legacy `#elosern-action-live` announcer is an empty div
        # nothing writes to), so gate on the store result itself.
        def _talked_result(state):
            result = state.get("lastActionResult")
            return result is not None and result.get("code") == "talked"

        wait_for_store_state(page, _talked_result)
        result = store_state(page).get("lastActionResult") or {}
        self.assertEqual(result.get("message"), "對方回應了你的話。")
        # complete-ui-command-echo: a freeform card is a deliberate mutation,
        # so its dispatch echoes exactly one `talk <NPC> <speech>` line —
        # the central descriptor fill composing the committed display name —
        # and never a second raw echo.
        _wait_inp_line(
            page,
            inp_before + 1,
            "talk %s 我們聊聊好嗎？" % npc_name,
            exact=True,
        )
        page.wait_for_timeout(250)
        self.assertEqual(
            self._narrative_inp_count(page),
            inp_before + 1,
            "a freeform card dispatch echoes exactly one command line, never a second",
        )

    @covers_requirement(
        "webclient-options-surface::suggestion-cards-execute-exact-envelopes-through-the-action-client"
    )
    def test_dismiss_control_hides_the_section(self):
        page = self._open_plaza_page()
        self._dismiss(page)

        self._wait_suggestions(page, "unavailable")
        self._wait_section_gone(page)
        self.assertEqual(self._sent_actions(page, "options.dismiss"), [{}])
        self.assertEqual(sent_action_count(page, "options.dismiss"), 1)

    @covers_requirement(
        "webclient-options-surface::suggestion-cards-execute-exact-envelopes-through-the-action-client"
    )
    def test_locked_client_rejects_card_clicks_without_side_effects(self):
        page = self._open_plaza_page()
        # Lock through a real transport close: while disconnected no server
        # push can arrive, so the store lock is stable for the whole click
        # window (the protocol-error lock is racy against the trigger
        # service's async republishes, which re-commit presentation state).
        page.evaluate("Evennia.connection.close()")

        def _locked(state):
            return (not state.get("connected")) and bool(state.get("mutationsLocked"))

        wait_for_store_state(page, _locked)
        # The non-dismissible offline overlay covers the stage (the lock UX),
        # so the card opens through the store façade directly: opening it is
        # local, never connection-gated.
        opened = page.evaluate("() => window.__elosernBridge.store.openRoomCard('suggestions')")
        self.assertTrue(opened, "the suggestions card must open through the store while locked")
        page.wait_for_function(
            "(selector) => document.querySelectorAll(selector + ' [data-testid=\"suggestions-card-row\"]').length > 0",
            arg=SUGGESTIONS_CARD_SELECTOR,
            timeout=15000,
        )
        # Force the click so the card's own handler still runs and the action
        # client's lock gate is what rejects the submit.
        card = self._card_rows(page).nth(0)
        card.click(force=True)
        page.wait_for_timeout(300)
        self.assertEqual(
            sent_action_count(page),
            0,
            "a locked action client must reject card clicks without side effects",
        )

    @covers_requirement(
        "webclient-options-surface::a-degraded-payload-with-zero-cards-renders-the-defined-empty-state"
    )
    def test_zero_card_degraded_renders_the_defined_empty_state(self):
        page = self._open_plaza_page()
        # Reach the memoized degraded room first so no server push can
        # overwrite the injected panel during the assertions.
        self._move_to_empty_ground(page)
        self._wait_section(page)
        # Build the envelope from the store's fresh state inside the page so
        # no server push can slip a revision between the read and the receive.
        accepted = page.evaluate(
            """() => {
                const s = ((window.__elosernBridge && window.__elosernBridge.store.view) || null);
                const envelope = {
                    protocol_version: 1,
                    presentation_epoch: s.epoch,
                    revision: s.revision + 1,
                    mode: 'exploration',
                    layout_version: 1,
                    server_time: s.serverTime,
                    panels: {
                        context_actions: {
                            schema_version: 5,
                            available: true,
                            kind: 'exploration',
                            affordances: [],
                            suggestions: { status: 'degraded', cards: [] },
                        },
                    },
                };
                // `receive` lives on the store instance (exposed through the
                // bridge handle), not on the `Protocol` factory façade.
                return window.__elosernBridge.store.receive(
                    s.generation, 'ui_update', [envelope], {});
            }"""
        )
        self.assertTrue(
            accepted["accepted"],
            "the zero-card degraded update must be valid: %r" % (accepted,),
        )

        self._wait_section(page)
        self._open_suggestions_pane(page)
        notes = page.locator(SUGGESTIONS_CARD_SELECTOR + ' [data-testid="choice-card-note"]').all_inner_texts()
        self.assertEqual(notes, [DEGRADED_NOTE, EMPTY_STATE_LINE])
        self.assertEqual(
            self._card_rows(page).count(),
            0,
            "a zero-card degraded payload renders no card row",
        )
        self.assertEqual(
            self._dismiss_rows(page).count(),
            1,
            "the empty-state render keeps the dismiss control",
        )

    @covers_requirement(
        "webclient-options-surface::the-exploration-dock-renders-the-suggestions-section-from-the-validated-v5-panel"
    )
    def test_degraded_rule_cards_render_in_dock_only(self):
        page = self._open_plaza_page()
        self._move_to_empty_ground(page)

        self._wait_section(page)
        self._open_suggestions_pane(page)
        self.assertGreaterEqual(
            self._card_rows(page).count(),
            1,
            "the v1 exploration derivation always yields at least one rule card",
        )
        self.assertEqual(
            page.locator(SUGGESTIONS_CARD_SELECTOR + ' [data-testid="choice-card-note"]').first.inner_text(),
            DEGRADED_NOTE,
        )
        self.assertEqual(
            self._dismiss_rows(page).count(),
            1,
            "the degraded render carries the same dismiss control",
        )
        # Degraded cards live on the suggestions card only: the narrative
        # stream never renders suggestion cards.
        self.assertEqual(
            page.locator('[data-testid="message-window"] [data-testid="suggestions-card-row"]').count(),
            0,
            "degraded rule cards must never appear in the narrative stream",
        )

    @covers_requirement(
        "webclient-options-surface::the-exploration-dock-renders-the-suggestions-section-from-the-validated-v5-panel"
    )
    def test_move_into_room_shows_generating_then_ready(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        # The class shares one ManagedServer across all 10 tests; a prior test
        # may have left the character at the empty-ground room (degraded state).
        # Teleport back to the seeded plaza so the journey starts from the
        # ready card set.
        self._teleport_to_plaza(page)
        self._wait_suggestions(page, "ready")
        self._wait_section(page)
        self._dismiss(page)
        self._wait_suggestions(page, "unavailable")

        # A real dock traversal into the empty-ground room: the room-entry
        # hook triggers the new fingerprint, whose scripted transport failure
        # settles the degraded render.
        self._move_to_empty_ground(page)
        self.assertEqual(sent_action_count(page, "explore.move"), 1)
        self._wait_section(page)

        # Returning to the plaza through the dock regenerates: generating
        # line, then ready. The compass's first exit is 回到廣場: moving
        # through it dispatches the return move without pushing a frame, so
        # the transient generating line stays visible to the assertion.
        activate_first_compass_exit(page)
        line = self._wait_generating_line(page)
        self.assertEqual(line, GENERATING_LINE)
        self._wait_suggestions(page, "ready")
        self.assertEqual(self._ready_card_labels(page), list(EXPECTED_READY_LABELS))

    @covers_requirement(
        "webclient-options-surface::the-exploration-dock-renders-the-suggestions-section-from-the-validated-v5-panel"
    )
    def test_section_gated_while_the_character_sub_dock_owns_the_surface(self):
        page = self._open_plaza_page()

        # Activate the character sub-dock deterministically through the
        # store's `activeSubDock` state (the legacy `_open_root(page, 3)`
        # assumed a hierarchical root the Vue flat dock does not render).
        # While it is active, neither the suggestions card nor the 建議 pill
        # renders.
        page.evaluate("window.__elosernBridge.store.setActiveSubDock('character')")
        self.assertEqual(
            page.evaluate("(() => { const s = window.__elosernBridge.store.view; return s && s.mode === 'exploration'; })()"),
            True,
            "the character panel must own the action dock",
        )
        self.assertFalse(
            self._section(page),
            "the suggestions section must not render under the character "
            "sub-dock",
        )
        self.assertEqual(page.locator(PILL_SELECTOR).count(), 0)

        # Leaving the sub-dock (clearing `activeSubDock`) rebuilds the
        # exploration dock from the current snapshot: the ready card set
        # returns.
        page.evaluate("window.__elosernBridge.store.setActiveSubDock(null)")
        _press(page, "Escape")
        self._wait_section(page)
        self.assertEqual(self._ready_card_labels(page), list(EXPECTED_READY_LABELS))
