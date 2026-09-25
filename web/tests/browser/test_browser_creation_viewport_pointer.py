"""Character-creation viewport and pointer browser journeys.
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


class ViewportCreationJourney(CreationBrowserTest):
    @covers_requirement("webclient-character-creation-ui::creation-browser-acceptance-is-keyboard-only-and-desktop-bounded")
    def test_1280x720_keeps_creation_essentials_visible_and_literal(self):
        page = self._login_creation((1280, 720))
        install_outbound_recorder(page)
        self._wait_creation_available(page)
        self.assertEqual(self._dock_mode(page), "creation")

        self._focus_dock(page)
        _press(page, "ArrowDown")
        _press(page, "Enter")  # 自訂角色
        def _custom_form_ready(state):
            if not state.get("connected") or state.get("mode") != "creation":
                return False
            panel = (state.get("panels") or {}).get("creation")
            return bool(panel and panel.get("available") is True)

        wait_for_store_state(
            page,
            _custom_form_ready,
            dom_readiness={
                "selector": '[data-testid="creation-submit"]',
                "predicate": (
                    "() => { const s = document.querySelector('[data-testid=\"creation-submit\"]'); "
                    "return s !== null; }"
                ),
                "description": "creation submit control rendered",
            },
            timeout=30000,
        )
        # The finite controls are the Vue app's creation-field-* data-testid hooks.
        controls = page.locator('[data-testid^="creation-field-"]')
        self.assertGreaterEqual(controls.count(), 1)
        for index in range(controls.count()):
            self.assertTrue(controls.nth(index).is_visible())
        # H1 mode-gate: the narrative feed is display:none in creation mode
        # (HudFrame's CSS-only visibility gate), not merely dimmed.
        self.assertFalse(
            page.locator('[data-testid="message-window"]').is_visible(),
            "the message window is display:none in creation mode",
        )
        placeholder_texts = page.locator(".elosern-placeholder").all_inner_texts()
        self.assertTrue(
            all("尚未開放" in text for text in placeholder_texts),
            "status-unavailable placeholder remains",
        )
        # Literal-text safety: no control label is rendered as trusted HTML.
        for cmd, args, _kw in outbound_messages(page):
            if cmd == "ui_action":
                self.assertNotIn("</", str(args))
        # The creation dock is the sole action-dock owner in creation mode.
        self.assertEqual(self._dock_mode(page), "creation")
        creation = self._creation_panel(page)
        for forbidden in ("persona", "skills", "equipment", "inventory", "magic_level"):
            self.assertNotIn(forbidden, creation)


class PointerCreationJourneys(CreationBrowserTest):
    """Pointer activation for the creation form action buttons (design D6).

    Each click must traverse the router's in-flight / awaiting-revision gate,
    emit exactly one mutation, and never log an unclaimed keydown while the
    form owns focus.
    """
    @covers_requirement("webclient-character-creation-ui::the-creation-dock-is-keyboard-first-form-capable-and-confirmation-protected")
    def test_pointer_click_on_submit_emits_exactly_one_custom_save(self):
        page = self._login_creation()
        install_outbound_recorder(page)
        self._wait_creation_available(page)
        self._focus_dock(page)
        _press(page, "ArrowDown")
        _press(page, "Enter")  # 自訂角色
        def _custom_form_ready(state):
            if not state.get("connected") or state.get("mode") != "creation":
                return False
            panel = (state.get("panels") or {}).get("creation")
            return bool(panel and panel.get("available") is True)

        wait_for_store_state(
            page,
            _custom_form_ready,
            dom_readiness={
                "selector": '[data-testid="creation-submit"]',
                "predicate": (
                    "() => { const s = document.querySelector('[data-testid=\"creation-submit\"]'); "
                    "return s !== null; }"
                ),
                "description": "creation submit control rendered",
            },
            timeout=30000,
        )
        page.evaluate("document.querySelector('[data-testid=\"creation-field-displayName\"]').focus()")
        page.keyboard.type("滑鼠角色")
        _press(page, "Tab")
        page.keyboard.type("20")
        _press(page, "Tab")
        page.keyboard.type("20")
        # Select a subrace so the allocation fields render (required now).
        page.evaluate("document.querySelector('[data-testid=\"creation-subrace\"]').focus()")
        _press(page, "ArrowDown")
        page.wait_for_timeout(150)
        for axis, value in (
            ("hp", "100"), ("mp", "50"), ("sp", "31"),
            ("atk_phys", "21"), ("agility", "21"), ("defense", "1"),
            ("magic_power", "0"),
        ):
            page.evaluate(
                "document.querySelector('[data-testid=\"creation-field-%s\"]').focus()" % axis
            )
            page.keyboard.type(value)
        # Pointer click (not keyboard Enter) on the submit button; the gate above
        # already proved the control is rendered, so the click auto-wait is bounded.
        page.locator('[data-testid="creation-submit"]').click(timeout=5000)
        page.wait_for_timeout(200)
        self.assertEqual(
            sent_action_count(page, "creation.custom"), 1,
            "a pointer click must submit exactly one creation.custom",
        )
        # No unclaimed keydown reached the stock handler while the form lived.
        for cmd, args, _kw in outbound_messages(page):
            self.assertNotIn("NO plugin handled this Keydown", str(args))

    @covers_requirement("webclient-character-creation-ui::the-creation-dock-is-keyboard-first-form-capable-and-confirmation-protected")
    def test_pointer_click_on_reset_opens_the_destructive_confirm(self):
        page = self._login_creation()
        install_outbound_recorder(page)
        self._wait_creation_available(page)
        self._focus_dock(page)
        _press(page, "ArrowDown")
        _press(page, "Enter")  # 自訂角色
        def _custom_form_ready(state):
            if not state.get("connected") or state.get("mode") != "creation":
                return False
            panel = (state.get("panels") or {}).get("creation")
            return bool(panel and panel.get("available") is True)

        wait_for_store_state(
            page,
            _custom_form_ready,
            dom_readiness={
                "selector": '[data-testid="creation-reset"]',
                "predicate": (
                    "() => { const r = document.querySelector('[data-testid=\"creation-reset\"]'); "
                    "return r !== null; }"
                ),
                "description": "creation reset control rendered",
            },
            timeout=30000,
        )
        page.locator('[data-testid="creation-reset"]').click(timeout=5000)
        page.wait_for_timeout(200)
        self.assertEqual(
            page.locator(".creation-confirm").count(), 1,
            "a pointer click on reset must open the confirmation",
        )
        self.assertEqual(sent_action_count(page, "creation.reset"), 0)
        self.assertEqual(sent_action_count(page, "creation.activate"), 0)
