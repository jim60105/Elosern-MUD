"""Dock suggestions-surface browser acceptance (webclient-options-surface).

These journeys drive the real Evennia server's exploration dock suggestions
section: the four status renders (the muted generating line, the ready card
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

import time

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    focus_action_dock,
    install_outbound_recorder,
    sent_action_count,
    store_state,
)
from .harness import ManagedServer
from . import fixtures

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
        deadline = time.monotonic() + timeout / 1000
        while time.monotonic() < deadline:
            suggestions = self._suggestions(page)
            if suggestions and suggestions.get("status") == status:
                return suggestions
            page.wait_for_timeout(250)
        raise AssertionError(
            "suggestions status never became %r; state=%r"
            % (status, store_state(page))
        )

    def _section(self, page):
        return page.evaluate(
            "document.querySelector('[data-testid=\"suggestions-section\"]')) !== null"
        )

    def _wait_section(self, page, timeout=30000):
        deadline = time.monotonic() + timeout / 1000
        while time.monotonic() < deadline:
            if self._section(page):
                return
            page.wait_for_timeout(250)
        raise AssertionError("the suggestions section never rendered")

    def _wait_section_gone(self, page, timeout=30000):
        deadline = time.monotonic() + timeout / 1000
        while time.monotonic() < deadline:
            if not self._section(page):
                return
            page.wait_for_timeout(250)
        raise AssertionError("the suggestions section never disappeared")

    def _wait_generating_line(self, page, timeout=30000):
        deadline = time.monotonic() + timeout / 1000
        while time.monotonic() < deadline:
            text = page.evaluate(
                """() => {
                    const line = document.querySelector(
                        '[data-testid="suggestions-section"] .suggestions-generating');
                    return line ? line.innerText : null;
                }"""
            )
            if text:
                return text
            page.wait_for_timeout(150)
        raise AssertionError("the generating line never rendered")

    def _ready_card_labels(self, page):
        return page.evaluate(
            """() => Array.from(
                document.querySelectorAll(
                    '[data-testid="suggestions-section"] .option-card .option-card-label'))
                .map((el) => el.innerText)"""
        )

    def _sent_actions(self, page, action_id):
        sent = page.evaluate("window.__elosernSent || []")
        return [
            args[0].get("payload")
            for cmd, args, _kwargs in sent
            if cmd == "ui_action" and args and args[0].get("action_id") == action_id
        ]

    def _narrative_inp_count(self, page):
        return page.locator(".elosern-narrative .inp").count()

    # -- journey helpers -----------------------------------------------------

    def _teleport_to_plaza(self, page):
        """Return the character to the seeded plaza through the superuser
        ``@tel`` command; the ui_sync trigger then regenerates the plaza
        situation for the fresh session."""
        page.evaluate(
            "(room) => Evennia.msg('text', ['@tel ' + room], {})", PLAZA_ROOM
        )

    def _dismiss(self, page):
        page.locator('[data-testid="suggestions-section"] .suggestions-dismiss').click()

    def _open_plaza_page(self):
        """A logged-in page whose session displays the ready plaza card set."""
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._teleport_to_plaza(page)
        self._wait_suggestions(page, "ready")
        self._wait_section(page)
        return page

    def _open_root(self, page, index):
        focus_action_dock(page)
        page.evaluate("window.__elosernBridge.router.reset()")
        page.wait_for_timeout(60)
        for _ in range(index):
            _press(page, "ArrowRight")
        _press(page, "Enter")

    def _move_to_empty_ground(self, page):
        """Walk through the dock from the plaza to the empty-ground room."""
        self._open_root(page, 0)  # Move
        _press(page, "Enter")  # the first exit (前往測試空地)
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
            page.locator('[data-testid="suggestions-section"] .option-card').count(),
            0,
            "the generating render carries no cards and no dismiss control",
        )
        self.assertEqual(
            page.locator('[data-testid="suggestions-section"] .suggestions-dismiss').count(),
            0,
        )

        self._wait_suggestions(page, "ready")
        self._wait_section(page)
        self.assertEqual(self._ready_card_labels(page), list(EXPECTED_READY_LABELS))
        self.assertEqual(
            page.locator('[data-testid="suggestions-section"] .suggestions-dismiss').count(),
            1,
            "the ready render carries the section-corner dismiss control",
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
        self._wait_suggestions(page, "ready")
        self._wait_section(page)
        self._dismiss(page)
        self._wait_suggestions(page, "unavailable")
        self._teleport_to_plaza(page)
        self._wait_generating_line(page)

        # The generating push changed only the suggestions content: the
        # exploration menu subtree and the keyboard router must be untouched.
        captured = page.evaluate(
            """() => {
                window.__menuNode = document.querySelector(
                    '#action-dock .exploration-menu');
                return window.__menuNode !== null;
            }"""
        )
        self.assertTrue(captured, "the exploration menu must be mounted")
        depth = page.evaluate("window.__elosernBridge.router.depth()")

        self._wait_suggestions(page, "ready")
        stable = page.evaluate(
            """() => {
                const menu = document.querySelector(
                    '#action-dock .exploration-menu');
                return window.__menuNode === menu && window.__menuNode.isConnected;
            }"""
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

        # Keyboard activation works natively on the focused card button.
        page.locator('[data-testid="suggestions-section"] .option-card').nth(0).focus()
        page.keyboard.press("Enter")

        self.assertEqual(self._sent_actions(page, "explore.look"), [{"room": True}])
        self.assertEqual(sent_action_count(page, "explore.look"), 1)
        # The look result settles into the narrative.
        page.wait_for_function(
            "(s) => document.querySelector('.elosern-narrative')"
            ".innerText.indexOf(s) !== -1",
            arg="燈籠",
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
        page.locator(
            "[data-testid=\"suggestions-section\"] .option-card",
            has_text="我們聊聊好嗎？",
        ).click()

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
        # the stable live region.
        deadline = time.monotonic() + 30
        live = ""
        while time.monotonic() < deadline:
            live = page.locator("#elosern-action-live").inner_text()
            if live == "對方回應了你的話。":
                break
            page.wait_for_timeout(250)
        self.assertEqual(live, "對方回應了你的話。")
        self.assertEqual(
            self._narrative_inp_count(page),
            inp_before,
            "a freeform card dispatch must never echo a command line",
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
        page.wait_for_function(
            "() => { const s = ((window.__elosernBridge && window.__elosernBridge.store.view) || null); "
            "return !s.connected && s.mutationsLocked; }"
        )
        # The non-dismissible offline overlay covers the dock (the lock UX);
        # scroll the card into view, then force the click so the card's direct
        # listener still runs and the action client's own lock gate is what
        # rejects the submit.
        card = page.locator('[data-testid="suggestions-section"] .option-card').nth(0)
        card.scroll_into_view_if_needed()
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
                return Elosern.Protocol.receive(
                    s.generation, 'ui_update', [envelope], {});
            }"""
        )
        self.assertTrue(
            accepted["accepted"],
            "the zero-card degraded update must be valid: %r" % (accepted,),
        )

        self._wait_section(page)
        self.assertEqual(
            page.locator('[data-testid="suggestions-section"] .suggestions-empty').inner_text(),
            EMPTY_STATE_LINE,
        )
        self.assertEqual(
            page.locator('[data-testid="suggestions-section"] .suggestions-note').inner_text(),
            DEGRADED_NOTE,
        )
        self.assertEqual(
            page.locator('[data-testid="suggestions-section"] .option-card').count(),
            0,
            "a zero-card degraded payload renders no card container",
        )
        self.assertEqual(
            page.locator('[data-testid="suggestions-section"] .suggestions-dismiss').count(),
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
        note = page.locator('[data-testid="suggestions-section"] .suggestions-note').inner_text()
        self.assertEqual(note, DEGRADED_NOTE)
        self.assertGreaterEqual(
            page.locator('[data-testid="suggestions-section"] .option-card').count(),
            1,
            "the v1 exploration derivation always yields at least one rule card",
        )
        self.assertEqual(
            page.locator('[data-testid="suggestions-section"] .suggestions-dismiss').count(),
            1,
            "the degraded render carries the same dismiss control",
        )
        # Degraded cards live in the dock only: the narrative stream never
        # renders suggestion cards (choice-points are the later slice).
        self.assertEqual(
            page.locator(".elosern-narrative .option-card").count(),
            0,
            "degraded rule cards must never appear in the narrative stream",
        )

    @covers_requirement(
        "webclient-options-surface::the-exploration-dock-renders-the-suggestions-section-from-the-validated-v5-panel"
    )
    def test_move_into_room_shows_generating_then_ready(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
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
        # line, then ready.
        self._open_root(page, 0)  # Move
        _press(page, "Enter")  # the single exit (回到廣場)
        line = self._wait_generating_line(page)
        self.assertEqual(line, GENERATING_LINE)
        self._wait_suggestions(page, "ready")
        self.assertEqual(self._ready_card_labels(page), list(EXPECTED_READY_LABELS))

    @covers_requirement(
        "webclient-options-surface::the-exploration-dock-renders-the-suggestions-section-from-the-validated-v5-panel"
    )
    def test_section_gated_while_the_character_sub_dock_owns_the_surface(self):
        page = self._open_plaza_page()

        # The character sub-dock wipes the action-dock subtree; the section
        # must never render under it.
        self._open_root(page, 3)  # 角色狀態
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

        # Leaving the sub-dock rebuilds the exploration dock from the current
        # snapshot: the ready card set returns.
        _press(page, "Escape")
        self._wait_section(page)
        self.assertEqual(self._ready_card_labels(page), list(EXPECTED_READY_LABELS))
