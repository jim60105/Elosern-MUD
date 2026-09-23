"""Character-creation reset-confirmation and draft-preservation browser journeys.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement
from .browser_helpers import (
    focus_creation_action_dock,
    install_outbound_recorder,
    inject_update,
    outbound_messages,
    sent_action_count,
    store_state,
    wait_for_store_state,
)
from .test_browser_creation_base import CreationBrowserTest


def _press(page, key, wait_ms=60):
    page.keyboard.press(key)
    page.wait_for_timeout(wait_ms)


class ResetAndDraftJourneys(CreationBrowserTest):
    CREATION_DRAFT = True
    @covers_requirement("webclient-character-creation-ui::the-creation-dock-is-keyboard-first-form-capable-and-confirmation-protected")
    def test_reset_requires_confirmation_and_clears_the_draft(self):
        page = self._login_creation()
        install_outbound_recorder(page)
        panel = self._wait_creation_available(page)
        self.assertEqual(panel["draft"]["mode"], "custom")
        self.assertEqual(panel["draft"]["display_name"], "草稿角色")

        self._focus_dock(page)
        _press(page, "ArrowDown")  # 自訂角色
        _press(page, "Enter")
        # The saved draft restored the form.
        self._wait_draft_name_restored(page)
        # Open the destructive reset confirmation; no mutation may be sent yet.
        page.evaluate("document.querySelector('[data-testid=\"creation-reset\"]').focus()")
        _press(page, "Enter")
        self.assertEqual(sent_action_count(page, "creation.reset"), 0)
        self.assertEqual(page.locator(".creation-confirm").count(), 1)
        _press(page, "Enter")  # 確認清除
        def _draft_cleared(state):
            panel = (state.get("panels") or {}).get("creation") or {}
            return panel.get("draft") is None

        wait_for_store_state(page, _draft_cleared, timeout=15000)
        self.assertIsNone(self._creation_panel(page)["draft"])
        self.assertEqual(sent_action_count(page, "creation.reset"), 1)
        self.assertEqual(sent_action_count(page, "creation.activate"), 0)
        self.assertEqual(self._dock_mode(page), "creation")

    @covers_requirement("webclient-frame-resolution::the-resolver-table-completes-with-the-combat-and-creation-families")
    def test_reset_confirm_shows_refreshed_server_text_when_withdrawn(self):
        """Declarative-frame degradation: the open confirm frame carries no
        copy — when the committed creation panel is withdrawn, the cascade
        pops the unresolvable frames and the surviving root presents the
        server-authored reason verbatim.

        The confirm frame is a descriptor (root + form marker + confirm =
        depth 3). A partial ``ui_update`` replaces only ``creation`` with its
        unavailable form (mode stays creation, so no teardown fires): the
        confirm and form-marker frames pop, the root itself is unresolvable,
        and the degraded root's marker row shows the server's message — not
        the local fallback — with no mutation dispatched.
        """
        page = self._login_creation()
        install_outbound_recorder(page)
        self._wait_creation_available(page)

        self._focus_dock(page)
        _press(page, "ArrowDown")  # 自訂角色
        _press(page, "Enter")  # form marker frame
        self._wait_draft_name_restored(page)
        page.evaluate("document.querySelector('[data-testid=\"creation-reset\"]').focus()")
        _press(page, "Enter")  # open the reset confirmation frame
        self.assertEqual(page.locator(".creation-confirm").count(), 1)
        depth_before = page.evaluate("() => window.__elosernBridge.router.depth()")
        self.assertEqual(depth_before, 3)

        reason = "角色建立服務暫時不可用。"
        inject_update(
            page,
            {
                "creation": {
                    "schema_version": 5,
                    "available": False,
                    "reason": {"code": "registry_unavailable", "message": reason},
                }
            },
            mode="creation",
        )

        def _degraded(state):
            degraded = state.get("degradedRoot")
            return bool(degraded) and degraded.get("reason") == reason

        wait_for_store_state(page, _degraded, timeout=15000)
        # The confirm frame is gone (never resurrected from a copy).
        self.assertEqual(page.locator(".creation-confirm").count(), 0)
        # Cascade: confirm + form marker popped; the root degrades in place.
        self.assertEqual(page.evaluate("() => window.__elosernBridge.router.depth()"), 1)
        # Unavailable does not change the mode — creation stays mounted.
        self.assertEqual(self._dock_mode(page), "creation")
        # Degradation dispatched nothing.
        self.assertEqual(sent_action_count(page, "creation.reset"), 0)

    @covers_requirement("webclient-character-creation-ui::the-creation-dock-is-keyboard-first-form-capable-and-confirmation-protected")
    def test_escape_from_reset_confirm_returns_to_form_without_mutation(self):
        page = self._login_creation()
        install_outbound_recorder(page)
        panel = self._wait_creation_available(page)
        self.assertEqual(panel["draft"]["mode"], "custom")

        self._focus_dock(page)
        _press(page, "ArrowDown")  # 自訂角色
        _press(page, "Enter")
        self._wait_draft_name_restored(page)
        # Open the destructive reset confirmation, then Escape instead of
        # confirming: exactly one menu level pops and the draft is preserved.
        page.evaluate("document.querySelector('[data-testid=\"creation-reset\"]').focus()")
        _press(page, "Enter")
        self.assertEqual(page.locator(".creation-confirm").count(), 1)
        self.assertEqual(sent_action_count(page, "creation.reset"), 0)
        _press(page, "Escape")
        def _back_on_form(state):
            panel = (state.get("panels") or {}).get("creation") or {}
            draft = panel.get("draft")
            return bool(draft and draft.get("mode") == "custom")

        wait_for_store_state(
            page,
            _back_on_form,
            dom_readiness={
                "selector": '[data-testid="creation-submit"]',
                "predicate": (
                    "() => { const s = document.querySelector('[data-testid=\"creation-submit\"]'); "
                    "const c = document.querySelector('[data-testid=\"creation-confirm\"]'); "
                    "return s !== null && c === null; }"
                ),
                "description": "creation submit control back on the form (confirm gone)",
            },
            timeout=30000,
        )
        # No reset or activation was sent; the saved draft is still intact.
        self.assertEqual(sent_action_count(page, "creation.reset"), 0)
        self.assertEqual(sent_action_count(page, "creation.activate"), 0)
        self.assertEqual(self._creation_panel(page)["draft"]["mode"], "custom")

    @covers_requirement("webclient-character-creation-ui::the-creation-dock-is-keyboard-first-form-capable-and-confirmation-protected")
    def test_escape_preserves_the_saved_draft(self):
        page = self._login_creation()
        install_outbound_recorder(page)
        panel = self._wait_creation_available(page)
        self.assertEqual(panel["draft"]["mode"], "custom")

        self._focus_dock(page)
        _press(page, "ArrowDown")
        _press(page, "Enter")  # 自訂角色
        self._wait_draft_name_restored(page)
        _press(page, "Escape")  # pop back to root; values stay on the server
        def _preset_list(state):
            panel = (state.get("panels") or {}).get("creation") or {}
            return len(panel.get("presets") or []) >= 2

        wait_for_store_state(
            page,
            _preset_list,
            dom_readiness={
                "selector": '[data-testid="creation-preset-card"]',
                "predicate": (
                    "() => document.querySelectorAll('[data-testid=\"creation-preset-card\"]').length >= 2"
                ),
                "description": "preset list rendered with at least two preset cards",
            },
            timeout=30000,
        )
        # The saved server draft was never cleared and no mutation was sent.
        self.assertEqual(sent_action_count(page, "creation.custom"), 0)
        self.assertEqual(sent_action_count(page, "creation.reset"), 0)
        self.assertEqual(self._creation_panel(page)["draft"]["mode"], "custom")
