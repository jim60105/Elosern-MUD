"""Narrative choice-point browser acceptance (webclient-options-choicepoints).

These journeys drive the real Evennia server's narrative stream placement of
AI action suggestions: the muted generating line appended at the stream end,
the in-place ready replacement, the movable end-block invariant (text appended
after a ready commit relocates the block to the new end), the shared card
component and click path (byte-identical envelopes with the dock), the stream
dismiss control clearing both surfaces, the degraded dock-only rule, the
action-client admission for stream clicks, and the transport-reset removal.

One server boots per test class (no combat sessions are started, so one server
is safe; every journey resets the character through the superuser ``@tel``
command). Every fixture is deterministic: the ``action_options`` client is the
same browser-settings replay double the options-surface journeys use (a fixed
plaza OptionSet after a short reactor delay so ``generating`` stays observable,
and a scripted empty-ground transport failure for the degraded path), and
journeys wait on the store's ``context_actions.suggestions.status`` and the
stream block DOM instead of timing sleeps.
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
    wait_for_store_state,
)
from .harness import ManagedServer
from . import fixtures

GENERATING_LINE = "AI 正在構思建議…"
DEGRADED_NOTE = "AI 建議目前不可用"
PLAZA_ROOM = "選項測試廣場"

EXPECTED_READY_LABELS = ("查看四周", "前往南門", "我們聊聊好嗎？", "試試身手")


def _narrative(page):
    return page.locator('[data-testid="narrative-feed"]')


class ChoicePointsBrowserTest(BrowserAcceptanceTest):
    """Boots one dedicated isolated server per class with the options-surface
    fixture (the deterministic plaza/empty-ground replay client).

    The fixture env lives on the runtime (never the process environment). No
    combat session is started on the server, so one server per class is safe;
    every journey resets the character to the seeded 選項測試廣場 room through
    the superuser ``@tel`` command.
    """

    @classmethod
    def setUpClass(cls) -> None:
        runtime = fixtures.create_runtime(prefix="elosern-choicepoints-")
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
        def _status_reached(state):
            suggestions = (state.get("panels") or {}).get("context_actions", {}).get("suggestions")
            return suggestions is not None and suggestions.get("status") == status

        wait_for_store_state(page, _status_reached, timeout=timeout)

    def _stream_block(self, page):
        return page.evaluate(
            "() => document.querySelectorAll("
            "'[data-testid=\"narrative-feed\"] .choicepoint-block').length"
        )

    def _wait_stream_block_count(self, page, expected, timeout=30000):
        if expected == 0:
            def _store_predicate(state):
                suggestions = (state.get("panels") or {}).get("context_actions", {}).get("suggestions")
                return suggestions is None or suggestions.get("status") == "unavailable"
        else:
            def _store_predicate(state):
                suggestions = (state.get("panels") or {}).get("context_actions", {}).get("suggestions")
                return suggestions is not None and suggestions.get("status") in ("generating", "ready")

        wait_for_store_state(
            page,
            _store_predicate,
            dom_readiness={
                "selector": '[data-testid="narrative-feed"] .choicepoint-block',
                "predicate": (
                    "() => document.querySelectorAll('[data-testid=\"narrative-feed\"] .choicepoint-block')"
                    ".length === %d" % expected
                ),
                "description": "the narrative stream-end choice-point block count is %d" % expected,
            },
            timeout=timeout,
        )

    def _stream_generating_text(self, page):
        return page.evaluate(
            """() => {
                const line = document.querySelector(
                    '[data-testid="narrative-feed"] .choicepoint-generating');
                return line ? line.innerText : null;
            }"""
        )

    def _stream_card_labels(self, page):
        return page.evaluate(
            """() => Array.from(
                document.querySelectorAll(
                    '[data-testid="narrative-feed"] .choicepoint-ready .option-card '
                    + '.option-card-label'))
                .map((el) => el.innerText)"""
        )

    def _stream_is_last_element(self, page):
        return page.evaluate(
            """() => {
                const narrative = document.querySelector('[data-testid="narrative-feed"]');
                const last = narrative && narrative.lastElementChild;
                return !!last && last.classList.contains('choicepoint-block');
            }"""
        )

    def _narrative_at_bottom(self, page):
        return page.evaluate(
            """() => {
                const n = document.querySelector('[data-testid="narrative-feed"]');
                return n.scrollHeight - n.scrollTop - n.clientHeight < 8;
            }"""
        )

    def _scroll_feed_to_bottom(self, page):
        """Pin the reader to the stream end so appended lines keep the end
        visible (the feed auto-scrolls only while the reader is at the
        bottom; a taller ready group would otherwise count as unread)."""
        page.evaluate(
            """() => {
                const n = document.querySelector('[data-testid="narrative-feed"]');
                if (n) { n.scrollTop = n.scrollHeight; }
            }"""
        )
        page.wait_for_timeout(100)

    def _section(self, page):
        return page.evaluate(
            "document.querySelector('[data-testid=\"suggestions-section\"]') !== null"
        )

    def _wait_section_gone(self, page, timeout=30000):
        def _section_hidden(state):
            suggestions = (state.get("panels") or {}).get("context_actions", {}).get("suggestions")
            return suggestions is None or suggestions.get("status") == "unavailable"

        wait_for_store_state(
            page,
            _section_hidden,
            dom_readiness={
                "selector": '[data-testid="suggestions-section"]',
                "predicate": (
                    "() => document.querySelector('[data-testid=\"suggestions-section\"]') === null"
                ),
                "description": "the suggestions section has disappeared from the action dock",
            },
            timeout=timeout,
        )

    def _sent_actions(self, page, action_id):
        sent = page.evaluate("window.__elosernSent || []")
        return [
            args[0].get("payload")
            for cmd, args, _kwargs in sent
            if cmd == "ui_action" and args and args[0].get("action_id") == action_id
        ]

    def _narrative_inp_count(self, page):
        return page.locator('[data-testid="narrative-feed"] .inp').count()

    # -- journey helpers -----------------------------------------------------

    def _teleport_to_plaza(self, page):
        """Return the character to the seeded plaza through the superuser
        ``@tel`` command; the ui_sync trigger then regenerates the plaza
        situation for the fresh session."""
        page.evaluate(
            "(room) => Evennia.msg('text', ['@tel ' + room], {})", PLAZA_ROOM
        )

    def _open_plaza_stream_page(self):
        """A logged-in page whose stream shows the ready plaza card group."""
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._teleport_to_plaza(page)
        self._wait_suggestions(page, "ready")
        self._wait_stream_block_count(page, 1)
        return page

    def _disconnect_transport(self, page):
        page.evaluate(
            "() => { if (window.__elosernWs) window.__elosernWs.close(4001); }"
        )

        def _disconnected(state):
            return not state.get("connected")

        wait_for_store_state(page, _disconnected)

    def _dismiss(self, page):
        page.locator('[data-testid="suggestions-section"] .suggestions-dismiss').click()

    def _move_to_empty_ground(self, page):
        """Walk through the dock from the plaza to the empty-ground room (the
        scripted transport-failure room, same journey as the surface file)."""
        focus_action_dock(page)
        page.evaluate("window.__elosernBridge.router.reset()")
        page.wait_for_timeout(60)
        page.keyboard.press("Enter")  # Move (the first root row)
        page.wait_for_timeout(80)
        page.keyboard.press("Enter")  # the first exit (前往測試空地)
        self._wait_suggestions(page, "degraded")

    # -- journeys ------------------------------------------------------------

    @covers_requirement(
        "webclient-action-choicepoints::the-choice-point-renders-generating-and-ready-states-at-the-stream-end"
    )
    def test_move_into_room_shows_generating_line_then_ready_cards_in_stream(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        # Settle the initial flow, then clear the session display so the
        # teleport below forces a fresh plaza generation whose delay keeps the
        # transient generating line observable.
        self._wait_suggestions(page, "ready")
        self._wait_stream_block_count(page, 1)
        self._dismiss(page)
        self._wait_suggestions(page, "unavailable")
        self._wait_stream_block_count(page, 0)

        self._teleport_to_plaza(page)
        # Pin the reader to the stream end: the generating line mount and
        # the taller ready replacement both auto-scroll only while the
        # reader is at the bottom (scroll-keep).
        self._scroll_feed_to_bottom(page)

        def _generating(state):
            suggestions = (state.get("panels") or {}).get("context_actions", {}).get("suggestions")
            return suggestions is not None and suggestions.get("status") == "generating"

        wait_for_store_state(
            page,
            _generating,
            dom_readiness={
                "selector": '[data-testid="narrative-feed"] .choicepoint-generating',
                "predicate": (
                    "() => document.querySelector('[data-testid=\"narrative-feed\"] .choicepoint-generating') !== null"
                ),
                "description": "the generating line has been appended at the narrative stream end",
            },
        )
        line = self._stream_generating_text(page)
        self.assertEqual(line, GENERATING_LINE)
        self.assertEqual(
            self._stream_block(page),
            1,
            "the generating commit appends exactly one stream-end line",
        )
        self.assertEqual(
            page.locator('[data-testid="narrative-feed"] .choicepoint-ready').count(),
            0,
            "no card group exists while generating",
        )

        self._wait_suggestions(page, "ready")
        self._wait_stream_block_count(page, 1)
        self.assertEqual(
            page.locator('[data-testid="narrative-feed"] .choicepoint-generating').count(),
            0,
            "the ready commit replaces the generating line in place",
        )
        self.assertEqual(
            self._stream_card_labels(page), list(EXPECTED_READY_LABELS)
        )
        self.assertEqual(
            page.locator(
                '[data-testid="narrative-feed"] .choicepoint-ready .suggestions-dismiss'
            ).count(),
            1,
            "the stream ready group carries the dismiss control",
        )
        # The player is tracking the stream end: the block mount and the
        # taller ready replacement both keep the end visible (scroll-keep).
        self.assertTrue(
            self._narrative_at_bottom(page),
            "the stream end stays visible while the generating line mounts "
            "and the ready group replaces it",
        )

    @covers_requirement(
        "webclient-action-choicepoints::the-choice-point-is-a-movable-stream-end-block-owned-by-the-narrative-facade"
    )
    def test_text_after_ready_moves_the_block_to_the_stream_end(self):
        page = self._open_plaza_stream_page()
        self.assertTrue(self._stream_is_last_element(page))
        # Pin the reader to the stream end so the appended look text and the
        # relocated block keep the end visible (scroll-keep).
        self._scroll_feed_to_bottom(page)

        # A look command lands narrative text after the ready commit; the
        # block must relocate to the new stream end (text between the older
        # content and the block). The look goes through the transport text
        # path (not a `ui_action`), so the deterministic gate is the result
        # text itself in the feed — `lastActionResult` stays null on this path.
        page.evaluate("Evennia.msg('text', ['look'], {})")

        def _connected(state):
            return bool(state.get("connected"))

        wait_for_store_state(
            page,
            _connected,
            dom_readiness={
                "selector": '[data-testid="narrative-feed"]',
                "predicate": (
                    "() => { const feed = document.querySelector('[data-testid=\"narrative-feed\"]'); "
                    "return feed && feed.innerText.indexOf('燈籠') !== -1; }"
                ),
                "description": "the look result text has settled into the narrative feed",
            },
        )
        self.assertTrue(
            self._stream_is_last_element(page),
            "text appended after the ready commit must keep the block last",
        )
        self.assertEqual(
            self._stream_block(page), 1, "the block is never duplicated"
        )
        self.assertEqual(self._stream_card_labels(page), list(EXPECTED_READY_LABELS))
        self.assertTrue(
            self._narrative_at_bottom(page),
            "the appended text and the relocated block keep the end visible",
        )

    @covers_requirement(
        "webclient-action-choicepoints::choice-point-cards-share-the-dock-card-component-and-click-path"
    )
    def test_stream_known_card_click_dispatches_the_exact_envelope(self):
        page = self._open_plaza_stream_page()
        inp_before = self._narrative_inp_count(page)

        # Keyboard activation works natively on the focused stream card button.
        page.locator(
            '[data-testid="narrative-feed"] .choicepoint-ready .option-card'
        ).nth(0).focus()
        page.keyboard.press("Enter")

        self.assertEqual(self._sent_actions(page, "explore.look"), [{"room": True}])
        self.assertEqual(sent_action_count(page, "explore.look"), 1)

        def _looked_result(state):
            result = state.get("lastActionResult")
            return result is not None and result.get("code") == "looked"

        wait_for_store_state(
            page,
            _looked_result,
            dom_readiness={
                "selector": '[data-testid="narrative-feed"]',
                "predicate": (
                    "() => { const feed = document.querySelector('[data-testid=\"narrative-feed\"]'); "
                    "return feed && feed.innerText.indexOf('燈籠') !== -1; }"
                ),
                "description": "the look result text has settled into the narrative feed",
            },
        )
        self.assertEqual(
            self._narrative_inp_count(page),
            inp_before,
            "a stream card dispatch must never echo a command line",
        )

    @covers_requirement(
        "webclient-action-choicepoints::choice-point-cards-share-the-dock-card-component-and-click-path"
    )
    def test_stream_freeform_card_sends_the_label_speech_once(self):
        page = self._open_plaza_stream_page()
        inp_before = self._narrative_inp_count(page)

        panel = store_state(page)["panels"]["context_actions"]
        freeform_entry = next(
            entry
            for entry in panel["affordances"]
            if entry["action_id"] == "explore.talk_freeform"
        )
        page.locator(
            '[data-testid="narrative-feed"] .choicepoint-ready .option-card',
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

        def _talked_result(state):
            result = state.get("lastActionResult")
            return result is not None and result.get("code") == "talked"

        # The Vue app keeps the OOB action result in the store (the legacy
        # `#elosern-action-live` announcer is an empty div nothing writes to),
        # so the deterministic gate is the store result itself.
        wait_for_store_state(page, _talked_result)
        result = store_state(page).get("lastActionResult") or {}
        self.assertEqual(result.get("message"), "對方回應了你的話。")
        self.assertEqual(
            self._narrative_inp_count(page),
            inp_before,
            "a freeform stream card dispatch must never echo a command line",
        )
        self.assertEqual(
            sent_action_count(page, "explore.talk_freeform"),
            1,
            "exactly one dispatch, no raw second echo",
        )

    @covers_requirement(
        "webclient-action-choicepoints::choice-point-cards-share-the-dock-card-component-and-click-path"
    )
    def test_stream_dismiss_clears_both_surfaces(self):
        page = self._open_plaza_stream_page()
        page.locator(
            '[data-testid="narrative-feed"] .choicepoint-ready .suggestions-dismiss'
        ).click()

        self._wait_suggestions(page, "unavailable")
        self._wait_stream_block_count(page, 0)
        self._wait_section_gone(page)
        self.assertEqual(self._sent_actions(page, "options.dismiss"), [{}])
        self.assertEqual(sent_action_count(page, "options.dismiss"), 1)

    @covers_requirement(
        "webclient-action-choicepoints::choice-point-cards-share-the-dock-card-component-and-click-path"
    )
    def test_locked_client_rejects_stream_card_clicks_without_side_effects(self):
        page = self._open_plaza_stream_page()
        # Lock through a real transport close; no server push can arrive, so
        # the store lock is stable for the whole click window.
        self._disconnect_transport(page)

        def _locked(state):
            return (not state.get("connected")) and bool(state.get("mutationsLocked"))

        wait_for_store_state(page, _locked)

        card = page.locator(
            '[data-testid="narrative-feed"] .choicepoint-ready .option-card'
        ).nth(0)
        card.scroll_into_view_if_needed()
        card.click(force=True)
        page.wait_for_timeout(300)
        self.assertEqual(
            sent_action_count(page),
            0,
            "a locked action client must reject stream card clicks",
        )
        # The committed-state invariant: the block remains exactly as the last
        # committed state until the next accepted commit.
        self.assertEqual(self._stream_block(page), 1)

    @covers_requirement(
        "webclient-action-choicepoints::degraded-rule-cards-never-enter-the-stream"
    )
    def test_degraded_rule_cards_render_in_dock_only(self):
        page = self._open_plaza_stream_page()
        # Walk through the dock into the scripted-transport-failure room.
        self._move_to_empty_ground(page)
        # The move leaves the router inside the 移動 submenu (depth 2). The
        # legacy suggestions section only renders at the root frame, so pop
        # one level: Escape returns focus to the root frame (design D2/D10).
        page.keyboard.press("Escape")
        page.wait_for_timeout(100)

        def _section_shown(state):
            suggestions = (state.get("panels") or {}).get("context_actions", {}).get("suggestions")
            return suggestions is not None and suggestions.get("status") in ("generating", "ready", "degraded")

        wait_for_store_state(
            page,
            _section_shown,
            dom_readiness={
                "selector": '[data-testid="suggestions-section"]',
                "predicate": (
                    "() => document.querySelector('[data-testid=\"suggestions-section\"]') !== null"
                ),
                "description": "the suggestions section is rendered in the action dock",
            },
        )
        note = page.locator('[data-testid="suggestions-section"] .suggestions-note').inner_text()
        self.assertEqual(note, DEGRADED_NOTE)
        self.assertGreaterEqual(
            page.locator('[data-testid="suggestions-section"] .option-card').count(),
            1,
            "the v1 exploration derivation always yields at least one rule card",
        )
        self.assertEqual(
            self._stream_block(page),
            0,
            "degraded rule cards must never enter the narrative stream",
        )
        self.assertEqual(
            page.locator('[data-testid="narrative-feed"] .option-card').count(),
            0,
            "no stream card DOM exists for the degraded state",
        )

    @covers_requirement(
        "webclient-action-choicepoints::the-choice-point-recovers-deterministically-across-sessions"
    )
    def test_reconnect_removes_the_block_on_the_transport_reset_itself(self):
        page = self._open_plaza_stream_page()
        generation_before = store_state(page)["generation"]

        # Observe the exact beginTransport notification: a store listener
        # registered now runs inside the same synchronous notify that clears
        # the panels. The block count is read on a microtask — after every
        # listener of that notify (including the choice-point layer, whatever
        # its registration order) and before any snapshot can arrive over the
        # socket (a later task) — so the observation is deterministic.
        page.evaluate(
            """() => {
                window.__resetBlockCount = null;
                window.__elosernBridge.store.subscribe((s) => {
                    if (window.__resetBlockCount === null
                        && s.activeEpoch === null
                        && Object.keys(s.panels).length === 0) {
                        window.__resetBlockCount = 'pending';
                        Promise.resolve().then(() => {
                            window.__resetBlockCount = document
                                .querySelectorAll('[data-testid="narrative-feed"] '
                                    + '.choicepoint-block').length;
                        });
                    }
                });
            }"""
        )

        # Transport close leaves the committed state untouched: the block
        # stays exactly as the last commit (the next accepted commit alone
        # decides removal; the locked client rejects any click meanwhile).
        self._disconnect_transport(page)
        self.assertEqual(
            self._stream_block(page),
            1,
            "the close itself never optimistically removes the block",
        )

        # The reconnect begins a new transport generation: beginTransport
        # clears the panels and the block is removed during that same store
        # notification, before any new snapshot is received.
        page.evaluate("Evennia.connect()")
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if page.evaluate(
                "typeof window.__resetBlockCount === 'number'"
            ):
                break
            page.wait_for_timeout(250)
        self.assertEqual(
            page.evaluate("window.__resetBlockCount"),
            0,
            "the block is removed on the reset notification itself, before "
            "the new snapshot",
        )

        # The fresh generation regenerates and mounts a fresh block.
        def _fresh_generation(state):
            return state.get("generation") is not None and state.get("generation") > generation_before

        wait_for_store_state(page, _fresh_generation, timeout=30000)
        self._wait_suggestions(page, "ready")
        self._wait_stream_block_count(page, 1)
        self.assertEqual(
            self._stream_card_labels(page), list(EXPECTED_READY_LABELS)
        )
        self.assertEqual(self._stream_block(page), 1, "exactly one fresh block")
