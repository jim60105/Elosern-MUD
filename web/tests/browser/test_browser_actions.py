"""UI action locking tests (section 6.6) driven through the real WebClient.

The production action registry is empty by design, so locking is demonstrated
client-side exactly as the task specifies: while disconnected or while
``mutationsLocked``, ``submit()`` is refused and no ``ui_action`` crosses the
wire; disabled controls do not send; HTML-like player text renders literally;
and ordinary text commands still work when structured OOB rendering fails.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    focus_action_dock,
    fresh_epoch,
    install_outbound_recorder,
    sent_action_count,
    snapshot_envelope,
    store_state,
    valid_status_panel,
    wait_for_store_state,
)


class ActionLockingTest(BrowserAcceptanceTest):
    """The action client refuses mutations whenever the store is not usable."""

    @covers_requirement(
        "webclient-desktop-shell::connection-loss-locks-stale-controls"
    )
    def test_submit_refused_while_disconnected(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self.assertEqual(sent_action_count(page), 0)

        page.evaluate("Evennia.connection.close()")
        wait_for_store_state(
            page,
            lambda s: not s.get("connected"),
            dom_readiness={
                "selector": "#elosern-offline-overlay",
                "predicate": (
                    "() => { const o = document.getElementById('elosern-offline-overlay'); "
                    "return !!o && o.getAttribute('data-visible') === 'true'; }"
                ),
                "description": "offline overlay visible while disconnected",
            },
            timeout=30000,
        )

        request_id = page.evaluate(
            "() => Elosern.actions.submit('proof.noop', {})"
        )
        self.assertIsNone(request_id, "submit must be refused while disconnected")
        self.assertEqual(sent_action_count(page), 0)

    def test_submit_refused_while_mutations_locked(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        generation = store_state(page)["generation"]

        # A reload-required protocol error locks all graphical mutations.
        accepted = page.evaluate(
            """(args) => window.__elosernBridge.store.receive(
              args.generation, 'ui_protocol_error', [{
                protocol_version: 1,
                code: 'unsupported_version',
                message: '不支援的協定版本',
                reload_required: true,
              }], {})""",
            {"generation": generation},
        )
        self.assertTrue(accepted["accepted"])
        self.assertTrue(store_state(page)["mutationsLocked"])

        request_id = page.evaluate(
            "() => Elosern.actions.submit('proof.noop', {})"
        )
        self.assertIsNone(request_id, "submit must be refused while locked")
        self.assertEqual(sent_action_count(page), 0)

    def test_disabled_controls_do_not_send(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        focus_action_dock(page)
        for key in ("ArrowDown", "Enter", " "):
            page.keyboard.press(key)
        page.wait_for_timeout(300)
        self.assertEqual(sent_action_count(page), 0)

        # H5 (webclient-hud-05-overlays-and-command-line): the command line
        # (the retired drawer's successor) sends ordinary text, never a
        # ui_action.
        page.keyboard.press("/")
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
            timeout=30000,
        )
        page.keyboard.type("look")
        page.keyboard.press("Enter")
        page.wait_for_timeout(500)
        sent = page.evaluate("window.__elosernSent")
        self.assertTrue(
            any(cmd == "text" for cmd, _args, _kw in sent),
            "the command line must send text commands",
        )
        self.assertEqual(
            sent_action_count(page), 0, "the command-line path must never build ui_action"
        )

    @covers_requirement(
        "webclient-desktop-shell::theme-and-controls-remain-accessible"
    )
    def test_html_like_player_text_renders_literal(self):
        page = self.logged_in_page()
        payload = (
            "<b onclick=\"window.__pwned=1\">bold</b>"
            "<script>window.__pwned=1</script>"
            "&amp; plain text"
        )
        page.evaluate(
            "(text) => window.__elosernBridge.store.appendText('in', text)", payload
        )
        narrative = page.locator('[data-testid="narrative-feed"]').inner_text()
        self.assertIn("plain text", narrative)
        self.assertIn("<b onclick=", narrative)
        self.assertEqual(
            page.evaluate("document.querySelector('[data-testid=\"narrative-feed\"]')"
                          ".querySelectorAll('b, script').length"),
            0,
            "server-authored text must be inserted as text, never HTML",
        )
        self.assertFalse(page.evaluate("'__pwned' in window"))

    @covers_requirement(
        "webclient-oob-protocol::protocol-failures-degrade-without-disabling-text-play",
        "webclient-desktop-shell::narrative-output-remains-the-authoritative-text-surface",
    )
    def test_ordinary_text_works_when_structured_oob_rendering_fails(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        generation = store_state(page)["generation"]
        revision_before = store_state(page)["revision"]

        # A malformed status panel is rejected atomically: no crash, no state
        # change, and the store stays active.
        malformed = snapshot_envelope(
            fresh_epoch(),
            99,
            {"status": {"schema_version": 1, "available": True}},
        )
        result = page.evaluate(
            "(args) => window.__elosernBridge.store.receive("
            "args.generation, 'ui_snapshot', [args.envelope], {})",
            {"generation": generation, "envelope": malformed},
        )
        self.assertFalse(result["accepted"])
        self.assertEqual(result["reason"], "invalid")
        state = store_state(page)
        self.assertEqual(state["phase"], "active")
        self.assertEqual(state["revision"], revision_before)

        # The one-sync renderer recovery guard fires exactly once per episode.
        # Both requests run in one page task: a server snapshot answering the
        # first resync would legitimately end the failure episode (a rendered
        # panel resets the guard), so the two calls must be atomic to observe
        # the blocked second request.
        first, second = page.evaluate(
            """() => {
                const controller = Elosern.actions;
                return [
                    controller.requestResync('status'),
                    controller.requestResync('status'),
                ];
            }"""
        )
        self.assertTrue(first, "first resync of an episode must be allowed")
        self.assertFalse(second, "a second resync in one episode must be blocked")
        syncs = [cmd for cmd, _a, _k in page.evaluate("window.__elosernSent")
                 if cmd == "ui_sync"]
        self.assertGreaterEqual(len(syncs), 1)

        # Ordinary text still works when structured rendering fails.
        narrative_before = page.locator('[data-testid="narrative-feed"]').inner_text()
        page.evaluate("Evennia.msg('text', ['look'], {})")
        wait_for_store_state(
            page,
            lambda s: bool(s.get("connected")),
            dom_readiness={
                "selector": '[data-testid="narrative-feed"]',
                "predicate": (
                    "() => { const n = document.querySelector('[data-testid=\"narrative-feed\"]'); "
                    "return !!n && n.innerText.length > %d; }" % len(narrative_before)
                ),
                "description": "narrative feed grew past the pre-look length",
            },
            timeout=30000,
        )
        narrative_after = page.locator('[data-testid="narrative-feed"]').inner_text()
        self.assertGreater(len(narrative_after), len(narrative_before))


if __name__ == "__main__":
    import unittest

    unittest.main()
