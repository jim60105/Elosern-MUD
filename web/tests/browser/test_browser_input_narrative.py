"""Input echo and command-line browser acceptance (webclient-input-narrative).

These journeys verify the narrative input line contract: the command line is
permanently present (H5, webclient-hud-05-overlays-and-command-line, design
D1 — no open/closed state), `/` focuses the always-present field without
firing inside an editable control, typed command-line commands and
button-triggered mutations echo exactly one `.inp` line with a preceding
`.narrative-divider`, locked submissions never echo, and the display catalog
never alters the `ui_action` envelope.

The pure command-line/narrative journeys run on the shared foundation server
(they never mutate game state); the move/free-form journeys boot one
dedicated isolated exploration server each so their mutations never leak into
another journey. All fixtures are deterministic; no remote, LLM, or image
service is involved.
"""

from __future__ import annotations

import json
import time

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    focus_action_dock,
    install_outbound_recorder,
    outbound_messages,
    sent_action_count,
    store_state,
    wait_for_store_state,
)
from .harness import ManagedServer
from . import fixtures


def _press(page, key, wait_ms=80):
    page.keyboard.press(key)
    page.wait_for_timeout(wait_ms)


def _wait_field_focused(page, timeout=30000):
    """Gate on the command field ``#inputfield`` being focused (after ``/``)."""
    wait_for_store_state(
        page,
        lambda s: bool(s.get("connected")),
        dom_readiness={
            "selector": "#inputfield",
            "predicate": (
                "() => document.activeElement === "
                "document.getElementById('inputfield')"
            ),
            "description": "#inputfield focused",
        },
        timeout=timeout,
    )


def _wait_command_field_released(page, timeout=30000):
    """Gate on the action dock holding focus after Escape from the field.

    H5 (webclient-hud-05-overlays-and-command-line): the command line is
    permanently present — the release path is focus restoration to
    ``#action-dock`` (design D2); the field is never closed (design D1).
    """
    wait_for_store_state(
        page,
        lambda s: bool(s.get("connected")),
        dom_readiness={
            "selector": "#action-dock",
            "predicate": (
                "() => { const d = document.querySelector('[data-testid=\"command-line\"]');"
                " const dock = document.getElementById('action-dock');"
                " return d && dock && "
                "(document.activeElement === dock || "
                "(document.activeElement && dock.contains(document.activeElement))); }"
            ),
            "description": "command field released: #action-dock focused, command line still present",
        },
        timeout=timeout,
    )


def _wait_inp_line(page, count, text=None, exact=False, timeout=30000):
    """Gate on the narrative feed's player-input (``.inp``) line count (optionally matching text)."""
    if text is None:
        predicate_js = (
            "() => document.querySelectorAll("
            "'[data-testid=\"narrative-feed\"] .inp').length === %d" % count
        )
    else:
        js_text = json.dumps(text)
        if exact:
            cmp = "lines[lines.length - 1].innerText === %s" % js_text
        else:
            cmp = "lines[lines.length - 1].innerText.indexOf(%s) !== -1" % js_text
        predicate_js = (
            "() => { const lines = document.querySelectorAll("
            "'[data-testid=\"narrative-feed\"] .inp');"
            " return lines.length === %d && %s; }" % (count, cmp)
        )
    wait_for_store_state(
        page,
        lambda s: bool(s.get("connected")),
        dom_readiness={
            "selector": '[data-testid="narrative-feed"]',
            "predicate": predicate_js,
            "description": "narrative feed input lines",
        },
        timeout=timeout,
    )


def _clear_narrative(page):
    """Reset the store's narrative log so the next input line is the log's first line.

    The store is a Pinia store, so ``store.narrative`` is the unwrapped array;
    clear it in place (``.length = 0``) to keep the reactive reference intact.
    """
    page.evaluate("() => { window.__elosernBridge.store.narrative.length = 0; }")


def _append_narrative_fillers(page, count=80):
    """Seed the store's narrative with server-text filler lines (the scroll-keep test needs overflow)."""
    page.evaluate(
        "(count) => { const store = window.__elosernBridge.store;"
        " for (let i = 0; i < count; i++) { store.appendText('out', 'filler line ' + i); } }",
        count,
    )


class DrawerNarrativeBrowserTest(BrowserAcceptanceTest):
    """Command-line focus, toggle, and input-echo acceptance (no mutation).

    H5 (webclient-hud-05-overlays-and-command-line): the command drawer is
    replaced by the permanently-present command line (design D1) — the field
    is in the DOM, visible and focusable without any opening action.
    """

    def _open_command_line(self, page):
        # H5: no opening action — the field is already in the DOM; the dock's
        # free-form borrow (design D6) or the shell's `/` claim (design D2)
        # both focus the always-present field.
        focus_action_dock(page)
        page.keyboard.press("/")
        _wait_field_focused(page)

    @covers_requirement(
        "webclient-desktop-shell::the-command-drawer-preserves-ordinary-text-control"
    )
    @covers_requirement(
        "webclient-contextual-hud::the-command-line-is-a-permanently-present-bar-in-the-stage-s-command-line-anchor"
    )
    def test_command_line_is_permanently_present_and_focusable(self):
        page = self.logged_in_page()
        # H5 (webclient-hud-05-overlays-and-command-line, design D1): the
        # command line is permanently present — the field is in the DOM,
        # visible and focusable without any opening action. No entry control,
        # no open/closed state.
        self.assertEqual(
            page.locator('[data-testid="command-line"]').count(), 1,
            "the command line surface is present",
        )
        self.assertEqual(page.locator(".drawer-entry").count(), 0, "no drawer entry control")
        self.assertTrue(
            page.locator(".inputfieldwrapper").is_visible(),
            "the input row is visible by default",
        )
        self.assertTrue(
            page.locator('[data-testid="command-line-prompt"]').is_visible(),
            "the prompt chevron is visible by default",
        )
        self.assertTrue(
            page.evaluate("(() => { const d = document.querySelector('[data-testid=\"command-line\"]'); return d !== null; })()"),
            "the command line must be present",
        )

    @covers_requirement(
        "webclient-contextual-hud::quick-word-chips-prepare-a-command-without-submitting-it"
    )
    def test_quick_word_chip_prepares_a_command_without_sending(self):
        """A quick-word chip writes its verb plus a trailing space into the field
        and moves focus to the field; it prepares, it does not send (exactly one
        send path — the field's send)."""
        page = self.logged_in_page()
        install_outbound_recorder(page)
        # The committed mode is exploration: the exploration chip set renders.
        chip = page.locator('[data-testid="quick-word-chip-看"]')
        self.assertEqual(chip.count(), 1, "the 看 chip renders in exploration")
        chip.click()
        self.assertEqual(
            page.evaluate("() => document.getElementById('inputfield').value"),
            "看 ",
            "the chip wrote its verb plus a trailing space into the field",
        )
        self.assertTrue(
            page.evaluate("document.activeElement === document.getElementById('inputfield')"),
            "focus moved to the field",
        )
        # The chip prepares, it does not send: no client->server message crosses
        # the wire (the prepared command still travels through the field's single
        # send path only).
        self.assertEqual(
            outbound_messages(page),
            [],
            "the chip sent no client->server message (it prepares, it does not send)",
        )

    @covers_requirement(
        "webclient-contextual-hud::the-command-line-advertises-only-affordances-this-client-implements"
    )
    def test_command_line_hint_names_history_only_and_controls_share_the_walk(self):
        """The hint cluster states the command-history recall keys and no completion
        affordance; the history controls drive the same walk state the keys drive,
        and neither submits."""
        page = self.logged_in_page()
        install_outbound_recorder(page)
        # The hint cluster names only the history recall keys (no completion).
        self.assertEqual(
            page.locator(".hint").inner_text(),
            "↑↓ 歷史",
            "the hint states only the history recall keys, no completion affordance",
        )
        # Seed the command history deterministically by sending two distinct text
        # commands through the client's single send path (the field's send).
        self._open_command_line(page)
        page.keyboard.type("look")
        page.keyboard.press("Enter")
        self._open_command_line(page)
        page.keyboard.type("take sword")
        page.keyboard.press("Enter")
        page.wait_for_function(
            "() => window.__elosernBridge.store.commandHistory.length >= 2",
            timeout=15000,
        )
        # The two seeded sends are already on the wire; capture that baseline so
        # the walk is proven to add no new message.
        baseline = len(outbound_messages(page))
        # The history-up control and the ↑ recall key drive the same walk state:
        # the button walks to the most recent entry, the key walks to the one
        # before it, and the unsent draft is preserved across the walk. Neither
        # submits (the walk is display-only).
        page.locator('[data-testid="command-line-history-up"]').click()
        self.assertEqual(
            page.evaluate("() => document.getElementById('inputfield').value"),
            "take sword",
            "the history control walked to the most recent entry",
        )
        # The recall key only drives the walk while the field is focused.
        page.locator("#inputfield").focus()
        page.keyboard.press("ArrowUp")
        self.assertEqual(
            page.evaluate("() => document.getElementById('inputfield').value"),
            "look",
            "the recall key walked to the prior entry (same shared walk state)",
        )
        self.assertEqual(
            len(outbound_messages(page)),
            baseline,
            "neither the history control nor the recall key submitted (no new wire messages)",
        )

    @covers_requirement(
        "webclient-contextual-hud::narrative-prose-scale-is-a-client-local-preference-the-settings-surface-owns"
    )
    def test_settings_prose_scale_is_a_client_local_preference(self):
        """The settings surface owns the narrative prose scale as client-local
        presentation state: three steps with a non-colour current-step indicator,
        and no `ui_action` is dispatched for the change."""
        page = self.logged_in_page()
        install_outbound_recorder(page)
        # Open the settings overlay through the command line's utility control.
        page.locator('[data-testid="command-line-settings"]').click()
        page.wait_for_selector('[data-testid="settings-overlay"]', timeout=15000)
        # The three-step prose-scale selector renders; the current step is marked
        # by a non-colour indicator (aria-pressed / the `on` class).
        for testid in ("settings-overlay-scale-A−", "settings-overlay-scale-A", "settings-overlay-scale-A+"):
            self.assertEqual(
                page.locator('[data-testid="%s"]' % testid).count(),
                1,
                f"{testid} renders",
            )
        self.assertTrue(
            page.evaluate(
                "() => { const el = document.querySelector('[data-testid=\"settings-overlay-scale-A\"]');"
                " return el && (el.getAttribute('aria-pressed') === 'true' || el.classList.contains('on')); }"
            ),
            "the current prose-scale step is marked without colour alone",
        )
        # Changing the scale is client-local: it applies the value to the
        # ``--prose-scale`` presentation token, persists it through the versioned
        # layout store, and dispatches no ``ui_action``.
        page.locator('[data-testid="settings-overlay-scale-A+"]').click()
        page.wait_for_function(
            "() => { const s = window.__elosernBridge.store;"
            " return s && s.view && s.view.fontScale === 1.12; }",
            timeout=15000,
        )
        self.assertEqual(
            page.evaluate(
                "() => document.documentElement.style.getPropertyValue('--prose-scale')"
            ),
            "1.12",
            "the prose scale is applied to the presentation token",
        )
        self.assertEqual(
            page.evaluate(
                "() => { const raw = localStorage.getItem('elosern.layout');"
                " return raw ? JSON.parse(raw).preferences.fontScale : null; }"
            ),
            1.12,
            "the prose scale is persisted as client-local presentation state",
        )
        self.assertEqual(
            sent_action_count(page),
            0,
            "the prose-scale change is client-local presentation state, not a ui_action",
        )

    @covers_requirement(
        "webclient-desktop-shell::the-command-drawer-preserves-ordinary-text-control"
    )
    def test_field_is_focusable_without_an_opening_action(self):
        page = self.logged_in_page()
        # H5 (design D1/D2): the always-present field is focusable directly —
        # a pointer click on the field focuses it; no entry button, no open
        # state.
        page.locator("#inputfield").click()
        _wait_field_focused(page)
        self.assertTrue(
            page.evaluate("(() => { const d = document.querySelector('[data-testid=\"command-line\"]'); return d !== null; })()"),
            "the command line is present",
        )
        self.assertTrue(page.locator(".inputfieldwrapper").is_visible())

    @covers_requirement(
        "webclient-desktop-shell::keyboard-routing-is-menu-first-and-submission-safe"
    )
    def test_slash_focuses_the_always_present_field(self):
        page = self.logged_in_page()
        # H5 (design D2): `/` outside an editable control moves focus into
        # the always-present command-line field; the claim is unconditional
        # (a repeated `/` still prevents a literal slash and re-focuses the
        # field, idempotently).
        focus_action_dock(page)
        page.keyboard.press("/")
        _wait_field_focused(page)
        self.assertTrue(page.evaluate("(() => { const d = document.querySelector('[data-testid=\"command-line\"]'); return d !== null; })()"))
        # A second `/` while the field is focused types the slash (the shell's
        # claim is not made over an editable control).
        page.keyboard.press("/")
        page.wait_for_timeout(150)
        self.assertEqual(
            page.evaluate("document.getElementById('inputfield').value"),
            "/",
            "a repeated / while the field is focused types a literal slash",
        )
        # Returning to the dock and pressing `/` re-focuses the field.
        focus_action_dock(page)
        page.keyboard.press("/")
        _wait_field_focused(page)
        self.assertTrue(page.evaluate("(() => { const d = document.querySelector('[data-testid=\"command-line\"]'); return d !== null; })()"))

    @covers_requirement(
        "webclient-desktop-shell::keyboard-routing-is-menu-first-and-submission-safe"
    )
    def test_slash_typed_in_a_focused_editable_stays_ordinary_text(self):
        page = self.logged_in_page()
        self._open_command_line(page)
        page.keyboard.type("whisper ")
        page.keyboard.press("/")
        page.wait_for_timeout(120)
        # The slash is ordinary text inside the field; the command line is
        # permanently present (H5, design D1) — it never opens or closes.
        self.assertEqual(
            page.evaluate("document.getElementById('inputfield').value"),
            "whisper /",
        )
        self.assertTrue(page.evaluate("(() => { const d = document.querySelector('[data-testid=\"command-line\"]'); return d !== null; })()"))
        self.assertTrue(
            page.evaluate(
                "document.activeElement === document.getElementById('inputfield')"
            )
        )

    @covers_requirement(
        "webclient-desktop-shell::keyboard-routing-is-menu-first-and-submission-safe"
    )
    def test_slash_while_the_rest_form_is_open_never_toggles_the_command_line(self):
        page = self.logged_in_page()
        # Open the rest form (Wait/休息 → 休息一段時間).
        focus_action_dock(page)
        cell_count = page.evaluate(
            "document.querySelectorAll('#action-dock [data-item-key]').length"
        )
        for _ in range(cell_count - 1):
            _press(page, "ArrowRight")
        _press(page, "Enter")  # Wait/休息
        _press(page, "ArrowDown")  # 等待至正午
        _press(page, "ArrowDown")  # 休息一段時間
        _press(page, "Enter")
        wait_for_store_state(
            page,
            lambda s: bool(s.get("connected")),
            dom_readiness={
                "selector": '[data-testid="exploration-rest-form"]',
                "predicate": (
                    "() => document.querySelector('[data-testid=\"exploration-rest-form\"]') !== null"
                ),
                "description": "rest form rendered",
            },
        )
        # H5: the command line is permanently present — its presence is
        # unaffected by the rest form.
        self.assertTrue(page.evaluate("(() => { const d = document.querySelector('[data-testid=\"command-line\"]'); return d !== null; })()"))
        # A slash while the rest form owns the keyboard is claimed: the command
        # line is never toggled (it has no open/closed state).
        page.keyboard.press("/")
        page.wait_for_timeout(150)
        self.assertTrue(
            page.evaluate("(() => { const d = document.querySelector('[data-testid=\"command-line\"]'); return d !== null; })()"),
            "the command line stays present while the rest form owns the keyboard",
        )
        self.assertTrue(
            page.evaluate("document.querySelector('[data-testid=\"exploration-rest-form\"]') !== null")
        )

    @covers_requirement(
        "webclient-desktop-shell::player-input-lines-are-part-of-the-narrative-stream-with-a-divider"
    )
    def test_typed_command_echoes_one_input_line_with_a_divider(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._open_command_line(page)
        page.keyboard.type("look")
        page.keyboard.press("Enter")
        _wait_inp_line(page, 1)
        inp = page.locator('[data-testid="narrative-feed"] .inp').first
        self.assertEqual(inp.inner_text(), "look")
        # The echo line is preceded by exactly one divider hairline.
        self.assertEqual(page.locator('[data-testid="narrative-feed"] .narrative-divider').count(), 1)
        self.assertTrue(
            page.evaluate(
                "() => {"
                "  const line = document.querySelector('[data-testid=\"narrative-feed\"] .inp');"
                "  return line.previousElementSibling !== null && "
                "    line.previousElementSibling.classList.contains('narrative-divider');"
                "}"
            )
        )
        # The ordinary send keeps the always-present command line present,
        # the field cleared, and focus in it; the echoed line is display-only
        # (the command also travelled as text).
        self.assertTrue(
            page.evaluate("(() => { const d = document.querySelector('[data-testid=\"command-line\"]'); return d !== null; })()"),
            "the command line is present after an ordinary send (H5, design D1)",
        )
        self.assertEqual(
            page.evaluate("document.getElementById('inputfield').value"), ""
        )
        sends = [
            args[0]
            for cmd, args, _kw in page.evaluate("window.__elosernSent || []")
            if cmd == "text"
        ]
        self.assertTrue(any("look" in str(item) for item in sends))

    @covers_requirement(
        "webclient-desktop-shell::player-input-lines-are-part-of-the-narrative-stream-with-a-divider"
    )
    def test_scrolled_away_input_preserves_scroll_and_increments_unread_by_one(self):
        page = self.logged_in_page()
        # Guarantee overflow so the narrative can be scrolled up.
        _append_narrative_fillers(page, 80)
        # Gate on the 80 fillers having rendered (overflow established) and the
        # feed's auto-scroll having settled, so the reader position is
        # deterministic before we scroll to the top.
        wait_for_store_state(
            page,
            lambda s: bool(s.get("connected")),
            dom_readiness={
                "selector": '[data-testid="narrative-feed"]',
                "predicate": (
                    "() => { const f = document.querySelector('[data-testid=\"narrative-feed\"]');"
                    " const lines = f ? f.querySelectorAll('.narrative-line').length : 0;"
                    " return f && f.scrollHeight > f.clientHeight && lines >= 80; }"
                ),
                "description": "80 fillers rendered (overflow established)",
            },
            timeout=30000,
        )
        # Scroll to the top, then gate on the scroll actually reaching the top.
        # The feed stylesheet sets `scroll-behavior: smooth`, so a direct
        # `scrollTop = 0` triggers an animation that races the gate. Force an
        # instant scroll for this single assignment (the same override pattern
        # the feed's own `scrollToBottom` uses) so the reader is deterministically
        # at the top before the input line is appended.
        page.evaluate(
            "() => { const f = document.querySelector('[data-testid=\"narrative-feed\"]');"
            " const prev = f.style.scrollBehavior;"
            " f.style.scrollBehavior = 'auto';"
            " f.scrollTop = 0;"
            " f.style.scrollBehavior = prev; }"
        )
        wait_for_store_state(
            page,
            lambda s: bool(s.get("connected")),
            dom_readiness={
                "selector": '[data-testid="narrative-feed"]',
                "predicate": (
                    "() => { const f = document.querySelector('[data-testid=\"narrative-feed\"]'); "
                    "return f && f.scrollTop === 0 && f.scrollHeight - f.scrollTop - f.clientHeight >= 8; }"
                ),
                "description": "narrative feed scrolled to the top (and not at the bottom)",
            },
            timeout=30000,
        )
        # One input event (divider + line) is exactly one unread increment and
        # one scroll-keep event.
        page.evaluate(
            "() => {"
            "  window.__unreadBefore = parseInt("
            "    document.getElementById('narrative-unread').getAttribute('data-count') || '0');"
            "  Elosern.narrativeInput.appendInput('probe');"
            "}"
        )
        # Gate on the unread count rising past the captured baseline. The input
        # event contributes exactly one increment; a concurrent server narrative
        # line (the shared foundation server replies to the sent text) may add
        # further increments, so the assertion is load-robust as "at least one"
        # rather than a strict equality that a racing server line would break.
        wait_for_store_state(
            page,
            lambda s: bool(s.get("connected")),
            dom_readiness={
                "selector": "#narrative-unread",
                "predicate": (
                    "() => parseInt(document.getElementById('narrative-unread')"
                    ".getAttribute('data-count')) >= window.__unreadBefore + 1"
                ),
                "description": "narrative-unread count incremented (at least one)",
            },
        )
        self.assertEqual(
            page.evaluate(
                "() => document.querySelector('[data-testid=\"narrative-feed\"]').scrollTop"
            ),
            0,
            "an input line must never force the viewport to the bottom",
        )
        self.assertEqual(page.locator(".narrative-divider").count(), 1)
        # The marker still clears on activation.
        page.locator(".narrative-unread-button").click()
        wait_for_store_state(
            page,
            lambda s: bool(s.get("connected")),
            dom_readiness={
                "selector": "#narrative-unread",
                "predicate": (
                    "() => document.getElementById('narrative-unread')"
                    ".getAttribute('data-count') === '0'"
                ),
                "description": "narrative-unread count cleared to zero",
            },
        )

    @covers_requirement(
        "webclient-desktop-shell::player-input-lines-are-part-of-the-narrative-stream-with-a-divider"
    )
    def test_first_log_line_needs_no_divider(self):
        page = self.logged_in_page()
        # Reset the store's narrative log so the next input line is the log's
        # first line (no divider hairline before the very first line). The store is
        # a Pinia store: clear the unwrapped array in place; the clear and the
        # append run in ONE evaluate so no server update can interleave.
        page.evaluate(
            """() => {
              const store = window.__elosernBridge.store;
              store.narrative.length = 0;
              Elosern.narrativeInput.appendInput('first');
            }"""
        )
        _wait_inp_line(page, 1)
        self.assertEqual(
            page.locator('[data-testid="narrative-feed"] .narrative-divider').count(),
            0,
            "the first log line carries no divider",
        )
        page.evaluate("() => Elosern.narrativeInput.appendInput('second')")
        wait_for_store_state(
            page,
            lambda s: bool(s.get("connected")),
            dom_readiness={
                "selector": '[data-testid="narrative-feed"]',
                "predicate": (
                    "() => document.querySelectorAll("
                    "'[data-testid=\"narrative-feed\"] .narrative-divider').length === 1"
                ),
                "description": "narrative divider rendered",
            },
        )
        self.assertEqual(
            page.locator('[data-testid="narrative-feed"] .inp').count(), 2
        )
        self.assertTrue(
            page.evaluate(
                "() => {"
                "  const lines = document.querySelectorAll('[data-testid=\"narrative-feed\"] .inp');"
                "  const second = lines[lines.length - 1];"
                "  return second.previousElementSibling !== null && "
                "    second.previousElementSibling.classList.contains('narrative-divider');"
                "}"
            )
        )

    @covers_requirement(
        "webclient-input-narrative::every-deliberate-mutation-echo-appears-exactly-once-at-dispatch"
    )
    def test_catalog_echo_never_alters_the_ui_action_envelope(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        # A staged submit with a display descriptor echoes its resolved line,
        # while the wire envelope carries exactly the action payload. The clear
        # and the dispatch run in ONE evaluate (Pinia store: clear the unwrapped
        # array in place) so no server update interleaves.
        payload = {"skill_key": "fire_ball", "target_ids": [1]}
        page.evaluate(
            """(p) => {
              window.__elosernBridge.store.narrative.length = 0;
              return Elosern.actions.submit('combat.cast', p,
                { skillLabel: '火球術', targetLabel: '哥布林' });
            }""",
            payload,
        )
        _wait_inp_line(page, 1, "cast 火球術=哥布林")
        envelopes = [
            args[0]
            for cmd, args, _kw in page.evaluate("window.__elosernSent || []")
            if cmd == "ui_action"
        ]
        self.assertEqual(len(envelopes), 1)
        envelope = envelopes[0]
        self.assertEqual(envelope["action_id"], "combat.cast")
        self.assertEqual(
            json.dumps(envelope["payload"], sort_keys=True),
            json.dumps(payload, sort_keys=True),
            "the echo must never leak display data into the payload",
        )
        # The identical submission without a display descriptor dispatches the
        # byte-identical payload; the catalog cannot resolve a cast line
        # without the skill label, so nothing echoes.
        self._wait_action_idle(page)
        page.evaluate(
            "() => Elosern.actions.submit('combat.cast', "
            "{ skill_key: 'fire_ball', target_ids: [1] })"
        )
        self._wait_action_idle(page)
        envelopes = [
            args[0]
            for cmd, args, _kw in page.evaluate("window.__elosernSent || []")
            if cmd == "ui_action"
        ]
        self.assertEqual(len(envelopes), 2)
        self.assertEqual(
            json.dumps(envelopes[0]["payload"], sort_keys=True),
            json.dumps(envelopes[1]["payload"], sort_keys=True),
        )
        self.assertEqual(
            page.locator('[data-testid="narrative-feed"] .inp').count(),
            1,
            "a cast without a resolvable skill label must not echo",
        )
        # A mutation the catalog can resolve without any display descriptor
        # still echoes exactly once at dispatch (forfeit needs no label).
        page.evaluate("() => Elosern.actions.submit('combat.forfeit')")
        _wait_inp_line(page, 2, "combat forfeit", exact=True)

    def _wait_action_idle(self, page, timeout=20000):
        deadline = time.monotonic() + timeout / 1000
        while time.monotonic() < deadline:
            if not page.evaluate("Elosern.actions.client.isInFlight()"):
                return
            page.wait_for_timeout(250)
        raise AssertionError("action client never released its lock")

    @covers_requirement(
        "webclient-input-narrative::echoed-command-lines-never-affect-state"
    )
    def test_markup_like_labels_render_as_literal_text(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        # Clear the store's narrative and dispatch in one evaluate so no server
        # update interleaves. (Pinia store: clear the unwrapped array in place.)
        page.evaluate(
            """() => {
              window.__elosernBridge.store.narrative.length = 0;
              Elosern.actions.submit('explore.engage', { monster_id: 'no_such_monster' },
              { targetLabel: '<script>alert(1)</script>' });
            }"""
        )
        _wait_inp_line(page, 1, "<script>alert(1)</script>")
        # The line is a single literal text node: no element was created.
        self.assertEqual(
            page.evaluate(
                "() => {"
                "  const lines = document.querySelectorAll('[data-testid=\"narrative-feed\"] .inp');"
                "  return lines[lines.length - 1].childElementCount;"
                "}"
            ),
            0,
        )
        self.assertEqual(page.locator('[data-testid="narrative-feed"] .inp script').count(), 0)


class InputEchoExplorationTest(BrowserAcceptanceTest):
    """Move/free-form input-echo journeys on one isolated exploration server."""

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

    def _wait_exploration_available(self, page, timeout=30000):
        wait_for_store_state(
            page,
            lambda s: (s.get("panels") or {}).get("exploration", {}).get("available") is True,
            timeout=timeout,
        )
        return store_state(page)["panels"].get("exploration")

    def _wait_panel(self, page, name, predicate, timeout=30000):
        def _panel_ready(state):
            panel = (state.get("panels") or {}).get(name)
            return panel is not None and predicate(panel)
        wait_for_store_state(page, _panel_ready, timeout=timeout)
        return store_state(page)["panels"].get(name)

    def _reset_root(self, page):
        focus_action_dock(page)
        page.evaluate("window.__elosernBridge.store.resetFramesToRoot()")
        page.wait_for_timeout(60)

    def _open_root(self, page, index):
        self._reset_root(page)
        for _ in range(index):
            _press(page, "ArrowRight")
        _press(page, "Enter")

    @covers_requirement(
        "webclient-desktop-shell::player-input-lines-are-part-of-the-narrative-stream-with-a-divider"
    )
    @covers_requirement(
        "webclient-input-narrative::the-command-line-catalog-resolves-a-display-line-deterministically"
    )
    def test_button_action_echoes_its_resolved_command_line(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        panel = self._wait_exploration_available(page)
        move_rows = panel.get("move") or []
        self.assertTrue(move_rows, "the fixture must offer exits")
        first_exit_label = move_rows[0]["label"]

        self._open_root(page, 0)  # Move
        _press(page, "Enter")  # first exit
        self._wait_panel(
            page,
            "local_map",
            lambda p: p.get("available") is True
            and p["current_node"] != "grid:capital_altoria:2:0",
        )
        self.assertEqual(sent_action_count(page, "explore.move"), 1)
        _wait_inp_line(page, 1)
        inp = page.locator('[data-testid="narrative-feed"] .inp').first
        self.assertEqual(
            inp.inner_text(),
            first_exit_label,
            "exit traversal echoes the server-authored exit label, never a guessed command",
        )
        self.assertEqual(page.locator('[data-testid="narrative-feed"] .narrative-divider').count(), 1)

    @covers_requirement(
        "webclient-input-narrative::every-deliberate-mutation-echo-appears-exactly-once-at-dispatch"
    )
    def test_freeform_dialogue_echoes_exactly_one_line_at_dispatch(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        panel = self._wait_exploration_available(page)
        bard = None
        for target in panel.get("interact") or []:
            for affordance in target.get("affordances") or []:
                if affordance.get("action_id") == "explore.talk_freeform":
                    bard = target
                    break
            if bard:
                break
        self.assertIsNotNone(bard, "the fixture must offer free-form dialogue")

        self._open_root(page, 2)  # Interact
        _press(page, "ArrowRight")  # the bard (second grid column)
        _press(page, "Enter")
        _press(page, "ArrowRight")  # 自由交談 (second grid column)
        _press(page, "Enter")
        _wait_field_focused(page)
        speech = "你好，詩人"
        page.keyboard.type(speech)
        page.keyboard.press("Enter")
        _wait_inp_line(page, 1)
        inp = page.locator('[data-testid="narrative-feed"] .inp').first
        self.assertEqual(
            inp.inner_text(),
            "talk %s %s" % (bard["display_name"], speech),
            "the free-form send echoes exactly one resolved line",
        )
        # The interaction completed: focus back on the dock (H5, design D2)
        # and the command line is still present (it is never closed).
        _wait_command_field_released(page)
        self.assertEqual(sent_action_count(page, "explore.talk_freeform"), 1)
        self.assertEqual(
            page.locator('[data-testid="narrative-feed"] .inp').count(),
            1,
            "no second raw-text echo may appear",
        )

    @covers_requirement(
        "webclient-input-narrative::every-deliberate-mutation-echo-appears-exactly-once-at-dispatch"
    )
    @covers_requirement(
        "webclient-desktop-shell::the-command-drawer-preserves-ordinary-text-control"
    )
    def test_locked_borrowed_send_keeps_the_speech_and_never_echoes(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        self._open_root(page, 2)  # Interact
        _press(page, "ArrowRight")  # the bard (second grid column)
        _press(page, "Enter")
        _press(page, "ArrowRight")  # 自由交談
        _press(page, "Enter")
        _wait_field_focused(page)
        inp_before = page.locator('[data-testid="narrative-feed"] .inp').count()

        # Disconnect: the store locks all mutations while preserving the view.
        page.evaluate("Evennia.connection.close()")
        wait_for_store_state(
            page,
            lambda s: not s.get("connected"),
        )
        speech = "話到嘴邊又吞了回去"
        page.keyboard.type(speech)
        page.keyboard.press("Enter")
        page.wait_for_timeout(300)
        # Nothing dispatched, nothing echoed, and the speech is not lost.
        self.assertEqual(sent_action_count(page, "explore.talk_freeform"), 0)
        self.assertEqual(
            page.locator('[data-testid="narrative-feed"] .inp').count(),
            inp_before,
            "a locked borrowed send must never echo",
        )
        self.assertTrue(
            page.evaluate("(() => { const d = document.querySelector('[data-testid=\"command-line\"]'); return d !== null; })()"),
            "the command line is present while the borrowed field holds the speech",
        )
        self.assertEqual(
            page.evaluate("document.getElementById('inputfield').value"),
            speech,
            "the typed speech must remain in the field",
        )


if __name__ == "__main__":
    import unittest

    unittest.main()
