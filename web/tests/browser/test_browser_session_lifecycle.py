"""WebClient session-lifecycle browser acceptance (fix-webclient-session-lifecycle 1.x/2.x).

These journeys drive the real Evennia server's puppet lifecycle through the
WebClient: OOC clears character panels and blocks mutations without any stale
action click, a no-puppet ``ui_action`` receives the bounded rejection through
the real wire chain, and repuppeting the same character adopts a fresh epoch
with fresh state. No combat session is started, so the foundation shared
server is used.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import store_state, wait_for_store_state


class SessionLifecycleBrowserTest(BrowserAcceptanceTest):
    """Drives OOC/IC through the real server and asserts client lifecycle state."""

    def _wait_active(self, page, timeout=30000):
        wait_for_store_state(
            page,
            lambda s: (
                bool(s.get("connected"))
                and s.get("phase") == "active"
                and s.get("mutationsLocked") is not True
            ),
            timeout=timeout,
        )
        return store_state(page)

    def _wait_detached(self, page, timeout=30000):
        wait_for_store_state(
            page,
            lambda s: s.get("phase") == "detached",
            timeout=timeout,
        )
        return store_state(page)

    @covers_requirement(
        "webclient-oob-protocol::unpuppet-retires-the-active-presentation-and-dispatch-sequence"
    )
    def test_ooc_clears_ui_and_blocks_mutations_without_stale_click(self):
        page = self.logged_in_page()
        self._wait_active(page)
        self.assertGreaterEqual(len(store_state(page)["panels"]), 1)

        page.evaluate("Evennia.msg('text', ['ooc'], {})")
        state = self._wait_detached(page)

        # Character panels are cleared and mutations are locked.
        self.assertEqual(state["panels"], {})
        self.assertTrue(state["mutationsLocked"])
        # The retained epoch allows a late bounded rejection to be accepted.
        self.assertIsNotNone(state["activeEpoch"])
        # The disconnect overlay must not appear: the connection is fine and
        # the drawer stays usable for repuppeting.
        visible = page.evaluate(
            "document.getElementById('elosern-offline-overlay')"
            ".getAttribute('data-visible') === 'true'"
        )
        self.assertFalse(visible, "OOC must not show the disconnect overlay")
        # New mutation submissions are refused client-side.
        request_id = page.evaluate(
            "() => Elosern.actions.submit('explore.wait', { seconds: 1 })"
        )
        self.assertIsNone(request_id)

    @covers_requirement(
        "webclient-action-dispatch::dispatch-rejects-no-puppet-actions-with-a-bounded-response",
        "webclient-oob-protocol::no-puppet-actions-receive-a-bounded-rejection",
    )
    def test_no_puppet_action_gets_bounded_rejection_through_real_wire(self):
        page = self.logged_in_page()
        self._wait_active(page)
        page.evaluate("Evennia.msg('text', ['ooc'], {})")
        self._wait_detached(page)

        # A stale click sent while the client still held the pre-OOC view.
        page.evaluate(
            "() => {"
            "  const s = ((window.__elosernBridge && window.__elosernBridge.store.view) || null);"
            "  Evennia.msg('ui_action', [{"
            "    protocol_version: 1,"
            "    presentation_epoch: s.epoch,"
            "    request_id: 'web:stale:1',"
            "    base_revision: s.revision,"
            "    action_id: 'explore.wait',"
            "    payload: { seconds: 1 }"
            "  }], {});"
            "}"
        )
        wait_for_store_state(
            page,
            lambda s: (s.get("lastActionResult") or {}).get("code") == "no_puppet",
            timeout=15000,
        )
        result = store_state(page)["lastActionResult"]
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "no_puppet")
        self.assertNotIn("panels", result)
        # The store stayed detached; the panels were never restored.
        self.assertEqual(store_state(page)["phase"], "detached")
        self.assertEqual(store_state(page)["panels"], {})

    @covers_requirement(
        "webclient-oob-protocol::unpuppet-retires-the-active-presentation-and-dispatch-sequence"
    )
    def test_repuppet_of_same_character_adopts_fresh_state(self):
        page = self.logged_in_page()
        active = self._wait_active(page)
        epoch_before = active["activeEpoch"]
        revision_before = active["revision"]

        page.evaluate("Evennia.msg('text', ['ooc'], {})")
        self._wait_detached(page)

        # Repuppet the same character through the ordinary drawer transport.
        page.evaluate("Evennia.msg('text', ['進入世界'], {})")
        wait_for_store_state(
            page,
            lambda s: (
                bool(s.get("connected"))
                and s.get("phase") == "active"
                and s.get("activeEpoch") is not None
                and s.get("activeEpoch") != epoch_before
                and s.get("mutationsLocked") is not True
            ),
            timeout=30000,
        )
        adopted = store_state(page)
        self.assertIsNotNone(adopted, "repuppet never adopted a fresh snapshot")
        self.assertNotEqual(adopted["activeEpoch"], epoch_before)
        self.assertNotEqual(adopted["revision"], revision_before)
        panels = adopted["panels"]
        # The exploration-mode panels re-render from canonical state; local_map
        # availability depends on the character's map knowledge, so only the
        # guaranteed panels are asserted as available.
        for name in ("exploration", "character", "services", "status"):
            self.assertIn(name, panels)
            self.assertTrue(panels[name]["available"], f"{name} panel must be fresh")
        self.assertEqual(store_state(page)["phase"], "active")

    @covers_requirement(
        "webclient-oob-protocol::unpuppet-retires-the-active-presentation-and-dispatch-sequence"
    )
    def test_second_ooc_without_puppet_keeps_detached_state(self):
        page = self.logged_in_page()
        self._wait_active(page)
        page.evaluate("Evennia.msg('text', ['ooc'], {})")
        self._wait_detached(page)

        # OOC again while already detached: the server answers in the text
        # channel and the client state is unchanged (no new transition noise).
        page.evaluate("Evennia.msg('text', ['ooc'], {})")
        page.wait_for_timeout(1000)
        state = store_state(page)
        self.assertEqual(state["phase"], "detached")
        self.assertEqual(state["panels"], {})
        self.assertTrue(state["mutationsLocked"])
