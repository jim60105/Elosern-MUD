"""Input echo and drawer-toggle browser acceptance (webclient-input-narrative).

These journeys verify the narrative input line contract: the drawer defaults
to closed behind an actionable entry button, `/` toggles it without ever
firing inside an editable control, typed drawer commands and button-triggered
mutations echo exactly one `.inp` line with a preceding `.narrative-divider`,
locked submissions never echo, and the display catalog never alters the
`ui_action` envelope.

The pure drawer/narrative journeys run on the shared foundation server (they
never mutate game state); the move/free-form journeys boot one dedicated
isolated exploration server each so their mutations never leak into another
journey. All fixtures are deterministic; no remote, LLM, or image service is
involved.
"""

from __future__ import annotations

import json
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


def _press(page, key, wait_ms=80):
    page.keyboard.press(key)
    page.wait_for_timeout(wait_ms)


class DrawerNarrativeBrowserTest(BrowserAcceptanceTest):
    """Drawer default-close, toggle, and input-echo acceptance (no mutation)."""

    def _open_drawer(self, page):
        focus_action_dock(page)
        page.keyboard.press("/")
        page.wait_for_function(
            "() => document.activeElement === document.getElementById('inputfield')"
        )

    @covers_requirement(
        "webclient-desktop-shell::the-command-drawer-preserves-ordinary-text-control"
    )
    def test_drawer_defaults_closed_behind_an_actionable_entry_button(self):
        page = self.logged_in_page()
        entry = page.locator(".drawer-entry")
        self.assertEqual(entry.count(), 1)
        self.assertTrue(entry.is_visible(), "the entry button is the visible drawer element")
        self.assertEqual(entry.get_attribute("aria-expanded"), "false")
        self.assertEqual(
            page.evaluate("document.querySelector('.elosern-drawer').getAttribute('data-open')"),
            "false",
        )
        # The input row is hidden until the player opens the drawer.
        self.assertFalse(page.locator(".inputfieldwrapper").is_visible())
        self.assertFalse(page.locator(".prompt").is_visible())
        self.assertFalse(page.evaluate("(() => { const d = document.querySelector('[data-testid=\"command-drawer\"]'); return d && d.getAttribute('data-open') === 'true'; })()"))

    @covers_requirement(
        "webclient-desktop-shell::the-command-drawer-preserves-ordinary-text-control"
    )
    def test_entry_button_opens_and_focuses_the_field(self):
        page = self.logged_in_page()
        page.locator(".drawer-entry").click()
        page.wait_for_function(
            "() => document.activeElement === document.getElementById('inputfield')"
        )
        self.assertTrue(page.evaluate("(() => { const d = document.querySelector('[data-testid=\"command-drawer\"]'); return d && d.getAttribute('data-open') === 'true'; })()"))
        self.assertEqual(
            page.evaluate("document.querySelector('.drawer-entry').getAttribute('aria-expanded')"),
            "true",
        )
        self.assertTrue(page.locator(".inputfieldwrapper").is_visible())

    @covers_requirement(
        "webclient-desktop-shell::keyboard-routing-is-menu-first-and-submission-safe"
    )
    def test_slash_toggles_the_drawer_and_restores_dock_focus(self):
        page = self.logged_in_page()
        # `/` over the action dock opens and focuses the field.
        focus_action_dock(page)
        page.keyboard.press("/")
        page.wait_for_function(
            "() => document.activeElement === document.getElementById('inputfield')"
        )
        self.assertTrue(page.evaluate("(() => { const d = document.querySelector('[data-testid=\"command-drawer\"]'); return d && d.getAttribute('data-open') === 'true'; })()"))
        # With no editable control focused, `/` closes and restores dock focus.
        focus_action_dock(page)
        page.keyboard.press("/")
        page.wait_for_function(
            "() => !(() => { const d = document.querySelector('[data-testid=\"command-drawer\"]'); return d && d.getAttribute('data-open') === 'true'; })() && (() => {"
            "  const dock = document.getElementById('action-dock');"
            "  return document.activeElement === dock || "
            "    (document.activeElement && dock.contains(document.activeElement));"
            "})()"
        )
        # And `/` reopens it.
        page.keyboard.press("/")
        page.wait_for_function(
            "() => document.activeElement === document.getElementById('inputfield')"
        )
        self.assertTrue(page.evaluate("(() => { const d = document.querySelector('[data-testid=\"command-drawer\"]'); return d && d.getAttribute('data-open') === 'true'; })()"))

    @covers_requirement(
        "webclient-desktop-shell::keyboard-routing-is-menu-first-and-submission-safe"
    )
    def test_slash_typed_in_a_focused_editable_never_closes_the_drawer(self):
        page = self.logged_in_page()
        self._open_drawer(page)
        page.keyboard.type("whisper ")
        page.keyboard.press("/")
        page.wait_for_timeout(120)
        # The slash is ordinary text inside the field; the drawer never closes.
        self.assertEqual(
            page.evaluate("document.getElementById('inputfield').value"),
            "whisper /",
        )
        self.assertTrue(page.evaluate("(() => { const d = document.querySelector('[data-testid=\"command-drawer\"]'); return d && d.getAttribute('data-open') === 'true'; })()"))
        self.assertTrue(
            page.evaluate(
                "document.activeElement === document.getElementById('inputfield')"
            )
        )

    @covers_requirement(
        "webclient-desktop-shell::keyboard-routing-is-menu-first-and-submission-safe"
    )
    def test_slash_while_the_rest_form_is_open_never_toggles_the_drawer(self):
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
        page.wait_for_function(
            "() => document.querySelector('[data-testid=\"exploration-rest-form\"]') !== null"
        )
        self.assertFalse(page.evaluate("(() => { const d = document.querySelector('[data-testid=\"command-drawer\"]'); return d && d.getAttribute('data-open') === 'true'; })()"))
        # A slash while the rest form owns the keyboard is claimed: the drawer
        # never opens or closes.
        page.keyboard.press("/")
        page.wait_for_timeout(150)
        self.assertFalse(
            page.evaluate("(() => { const d = document.querySelector('[data-testid=\"command-drawer\"]'); return d && d.getAttribute('data-open') === 'true'; })()"),
            "a slash in the rest form must never open the drawer",
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
        self._open_drawer(page)
        page.keyboard.type("look")
        page.keyboard.press("Enter")
        page.wait_for_function(
            "() => document.querySelectorAll('.elosern-narrative .inp').length === 1"
        )
        inp = page.locator(".elosern-narrative .inp").first
        self.assertEqual(inp.inner_text(), "look")
        # The echo line is preceded by exactly one divider hairline.
        self.assertEqual(page.locator(".elosern-narrative .narrative-divider").count(), 1)
        self.assertTrue(
            page.evaluate(
                "() => {"
                "  const line = document.querySelector('.elosern-narrative .inp');"
                "  return line.previousElementSibling !== null && "
                "    line.previousElementSibling.classList.contains('narrative-divider');"
                "}"
            )
        )
        # The ordinary send keeps the field open, cleared, and focused; the
        # echoed line is display-only (the command also travelled as text).
        self.assertTrue(page.evaluate("(() => { const d = document.querySelector('[data-testid=\"command-drawer\"]'); return d && d.getAttribute('data-open') === 'true'; })()"))
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
        narrative = page.locator(".elosern-narrative")
        # Guarantee overflow so the narrative can be scrolled up.
        page.evaluate(
            "() => { for (let i = 0; i < 80; i++) { "
            "window.__elosernConsole.model.appendIn('filler line ' + i); } }"
        )
        page.wait_for_timeout(300)
        page.evaluate(
            "() => { const el = document.querySelector('.elosern-narrative'); "
            "el.scrollTop = 0; }"
        )
        page.wait_for_timeout(100)
        # One input event (divider + line) is exactly one unread increment and
        # one scroll-keep event.
        page.evaluate(
            "() => {"
            "  window.__unreadBefore = parseInt("
            "    document.getElementById('narrative-unread').getAttribute('data-count') || '0');"
            "  Elosern.narrativeInput.appendInput('probe');"
            "}"
        )
        page.wait_for_function(
            "() => parseInt(document.getElementById('narrative-unread')"
            ".getAttribute('data-count')) === window.__unreadBefore + 1"
        )
        self.assertEqual(
            page.evaluate(
                "() => document.querySelector('.elosern-narrative').scrollTop"
            ),
            0,
            "an input line must never force the viewport to the bottom",
        )
        self.assertEqual(page.locator(".narrative-divider").count(), 1)
        # The marker still clears on activation.
        page.locator(".narrative-unread-button").click()
        page.wait_for_function(
            "() => document.getElementById('narrative-unread')"
            ".getAttribute('data-count') === '0'"
        )

    @covers_requirement(
        "webclient-desktop-shell::player-input-lines-are-part-of-the-narrative-stream-with-a-divider"
    )
    def test_first_log_line_needs_no_divider(self):
        page = self.logged_in_page()
        # Wipe every narrative line (the unread marker stays); the next input
        # line is the log's first line.
        page.evaluate(
            "() => {"
            "  const n = document.querySelector('.elosern-narrative');"
            "  Array.from(n.children).forEach(function (child) {"
            "    if (!child.classList.contains('narrative-unread')) { n.removeChild(child); }"
            "  });"
            "  Elosern.narrativeInput.appendInput('first');"
            "}"
        )
        page.wait_for_function(
            "() => document.querySelectorAll('.elosern-narrative .inp').length === 1"
        )
        self.assertEqual(
            page.locator(".elosern-narrative .narrative-divider").count(),
            0,
            "the first log line carries no divider",
        )
        page.evaluate("() => Elosern.narrativeInput.appendInput('second')")
        page.wait_for_function(
            "() => document.querySelectorAll('.elosern-narrative .narrative-divider').length === 1"
        )
        self.assertEqual(
            page.locator(".elosern-narrative .inp").count(), 2
        )
        self.assertTrue(
            page.evaluate(
                "() => {"
                "  const lines = document.querySelectorAll('.elosern-narrative .inp');"
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
        # while the wire envelope carries exactly the action payload.
        payload = {"skill_key": "fire_ball", "target_ids": [1]}
        page.evaluate(
            "(p) => Elosern.actions.submit('combat.cast', p, "
            "{ skillLabel: '火球術', targetLabel: '哥布林' })",
            payload,
        )
        page.wait_for_function(
            "() => {"
            "  const lines = document.querySelectorAll('.elosern-narrative .inp');"
            "  return lines.length === 1 && "
            "    lines[lines.length - 1].innerText.indexOf('cast 火球術=哥布林') !== -1;"
            "}"
        )
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
            page.locator(".elosern-narrative .inp").count(),
            1,
            "a cast without a resolvable skill label must not echo",
        )
        # A mutation the catalog can resolve without any display descriptor
        # still echoes exactly once at dispatch (forfeit needs no label).
        page.evaluate("() => Elosern.actions.submit('combat.forfeit')")
        page.wait_for_function(
            "() => {"
            "  const lines = document.querySelectorAll('.elosern-narrative .inp');"
            "  return lines.length === 2 && "
            "    lines[lines.length - 1].innerText === 'combat forfeit';"
            "}"
        )

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
        page.evaluate(
            "() => Elosern.actions.submit('explore.engage', "
            "{ monster_id: 'no_such_monster' }, "
            "{ targetLabel: '<script>alert(1)</script>' })"
        )
        page.wait_for_function(
            "() => {"
            "  const lines = document.querySelectorAll('.elosern-narrative .inp');"
            "  return lines.length === 1 && "
            "    lines[lines.length - 1].innerText.indexOf('<script>alert(1)</script>') !== -1;"
            "}"
        )
        # The line is a single literal text node: no element was created.
        self.assertEqual(
            page.evaluate(
                "() => {"
                "  const lines = document.querySelectorAll('.elosern-narrative .inp');"
                "  return lines[lines.length - 1].childElementCount;"
                "}"
            ),
            0,
        )
        self.assertEqual(page.locator(".elosern-narrative .inp script").count(), 0)


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
        deadline = time.monotonic() + timeout / 1000
        while time.monotonic() < deadline:
            panel = store_state(page)["panels"].get("exploration")
            if panel and panel.get("available") is True:
                return panel
            page.wait_for_timeout(250)
        raise AssertionError("exploration panel never became available")

    def _wait_panel(self, page, name, predicate, timeout=30000):
        deadline = time.monotonic() + timeout / 1000
        while time.monotonic() < deadline:
            try:
                panel = store_state(page)["panels"].get(name)
                if panel and predicate(panel):
                    return panel
            except Exception:
                pass
            page.wait_for_timeout(250)
        raise AssertionError("panel %s predicate never became true" % name)

    def _reset_root(self, page):
        focus_action_dock(page)
        page.evaluate("window.__elosernBridge.router.reset()")
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
        page.wait_for_function(
            "() => document.querySelectorAll('.elosern-narrative .inp').length === 1"
        )
        inp = page.locator(".elosern-narrative .inp").first
        self.assertEqual(
            inp.inner_text(),
            first_exit_label,
            "exit traversal echoes the server-authored exit label, never a guessed command",
        )
        self.assertEqual(page.locator(".elosern-narrative .narrative-divider").count(), 1)

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
        page.wait_for_function(
            "() => document.activeElement === document.getElementById('inputfield')"
        )
        speech = "你好，詩人"
        page.keyboard.type(speech)
        page.keyboard.press("Enter")
        page.wait_for_function(
            "() => document.querySelectorAll('.elosern-narrative .inp').length === 1"
        )
        inp = page.locator(".elosern-narrative .inp").first
        self.assertEqual(
            inp.inner_text(),
            "talk %s %s" % (bard["display_name"], speech),
            "the free-form send echoes exactly one resolved line",
        )
        # The interaction completed: drawer closed, focus back on the dock.
        page.wait_for_function("() => !(() => { const d = document.querySelector('[data-testid=\"command-drawer\"]'); return d && d.getAttribute('data-open') === 'true'; })()")
        self.assertEqual(sent_action_count(page, "explore.talk_freeform"), 1)
        self.assertEqual(
            page.locator(".elosern-narrative .inp").count(),
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
        page.wait_for_function(
            "() => document.activeElement === document.getElementById('inputfield')"
        )
        inp_before = page.locator(".elosern-narrative .inp").count()

        # Disconnect: the store locks all mutations while preserving the view.
        page.evaluate("Evennia.connection.close()")
        page.wait_for_function(
            "() => { const s = ((window.__elosernBridge && window.__elosernBridge.store.view) || null); return !s.connected; }"
        )
        speech = "話到嘴邊又吞了回去"
        page.keyboard.type(speech)
        page.keyboard.press("Enter")
        page.wait_for_timeout(300)
        # Nothing dispatched, nothing echoed, and the speech is not lost.
        self.assertEqual(sent_action_count(page, "explore.talk_freeform"), 0)
        self.assertEqual(
            page.locator(".elosern-narrative .inp").count(),
            inp_before,
            "a locked borrowed send must never echo",
        )
        self.assertTrue(page.evaluate("(() => { const d = document.querySelector('[data-testid=\"command-drawer\"]'); return d && d.getAttribute('data-open') === 'true'; })()"))
        self.assertEqual(
            page.evaluate("document.getElementById('inputfield').value"),
            speech,
            "the typed speech must remain in the field",
        )


if __name__ == "__main__":
    import unittest

    unittest.main()
