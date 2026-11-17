"""Preset character-creation browser journeys.
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
from .browser_base import ui_scale
from .test_browser_creation_base import CreationBrowserTest

_EXPANDED_KEY_JS = (
    "() => { const c = document.querySelector("
    "'[data-testid=\"creation-preset-card\"][data-expanded=\"true\"]'); "
    "return c ? c.getAttribute('data-preset-key') : null; }"
)


def _press(page, key, wait_ms=60):
    page.keyboard.press(key)
    page.wait_for_timeout(wait_ms)


class PresetCreationJourneys(CreationBrowserTest):
    @covers_requirement("webclient-character-creation-ui::creation-browser-acceptance-is-keyboard-only-and-desktop-bounded")
    @covers_requirement("webclient-character-creation-ui::preset-browsing-is-local-until-deliberate-selection")
    @covers_requirement("creation-activation-gating::activation-confirmation-follows-a-successful-save")
    def test_preset_selection_confirm_activate_reaches_exploration(self):
        page = self._login_creation()
        install_outbound_recorder(page)
        panel = self._wait_creation_available(page)
        # The card wall renders the registry's cards (card COUNT parity with the
        # registry is the presenter's own unit contract). Browsing is local:
        # opening another card sends nothing; only the deliberate Enter saves.
        presets = panel["presets"]
        self.assertGreaterEqual(len(presets), 1)
        self.assertEqual(self._dock_mode(page), "creation")
        self.assertEqual(
            page.locator('[data-testid="creation-preset-card"]').count(), len(presets)
        )

        # Neither reference viewport scrolls the page horizontally, and the
        # expanded card's primary action stays on screen above the footer.
        for width, height in ((2560, 1440), (1451, 790)):
            with self.subTest(viewport=(width, height)):
                page.set_viewport_size({"width": width, "height": height})
                page.wait_for_function(
                    "(v) => getComputedStyle(document.documentElement)"
                    ".getPropertyValue('--ui-scale').trim() === v",
                    arg="%g" % ui_scale((width, height)),
                    timeout=15000,
                )
                self.assertLessEqual(
                    page.evaluate("document.documentElement.scrollWidth"), width
                )
                choose = page.locator('[data-testid="creation-preset-choose"]').bounding_box()
                footer = page.locator(".creation-overlay__footer").bounding_box()
                self.assertIsNotNone(choose)
                self.assertGreaterEqual(choose["y"], 0)
                self.assertLessEqual(choose["y"] + choose["height"], footer["y"])
                self.assertLessEqual(choose["x"] + choose["width"], width)

        # Focus the action dock and open the preset frame (keyboard only).
        self._focus_dock(page)
        _press(page, "Enter")  # 預設角色
        expected_key = presets[0]["key"]
        if len(presets) >= 2:
            _press(page, "ArrowRight")  # local browse to the second card
            _press(page, "2")  # its ordinal digit: still local
            expected_key = presets[1]["key"]
        self.assertEqual(page.evaluate(_EXPANDED_KEY_JS), expected_key)
        self.assertEqual(sent_action_count(page, "creation.preset"), 0)

        _press(page, "Enter")  # choose the expanded card
        self.assertEqual(sent_action_count(page, "creation.preset"), 1)
        # The wire carries exactly the expanded card's key.
        self.assertEqual(self._sent_payloads(page, "creation.preset"), [{"preset_key": expected_key}])

        # The confirmation appears only after the preset save result arrives.
        self._wait_confirm_ready(page)
        self.assertEqual(page.locator(".creation-confirm").count(), 1)
        _press(page, "Enter")  # 確認啟用
        self._wait_exploration(page)
        self.assertEqual(sent_action_count(page, "creation.activate"), 1)
        self.assertNotEqual(self._dock_mode(page), "creation")
        creation = self._creation_panel(page)
        self.assertFalse(creation["available"])

    @covers_requirement("webclient-character-creation-ui::the-creation-dock-is-keyboard-first-form-capable-and-confirmation-protected")
    def test_escape_from_preset_confirm_returns_to_list_without_mutation(self):
        page = self._login_creation()
        install_outbound_recorder(page)
        self._wait_creation_available(page)
        self._focus_dock(page)
        _press(page, "Enter")  # 預設角色
        _press(page, "Enter")  # choose the expanded first card -> confirmation screen
        self._wait_confirm_ready(page)
        self.assertEqual(page.locator(".creation-confirm").count(), 1)
        _press(page, "Escape")  # pop exactly one level back to the preset list
        self.assertEqual(page.locator(".creation-confirm").count(), 0)
        self.assertGreaterEqual(page.locator('[data-testid="creation-body"] [data-testid="creation-preset-card"]').count(), 1)
        # No activation or reset was sent; only the earlier preset-selection save.
        self.assertEqual(sent_action_count(page, "creation.activate"), 0)
        self.assertEqual(sent_action_count(page, "creation.reset"), 0)

    @covers_requirement("creation-activation-gating::activation-confirmation-follows-a-successful-save")
    @covers_requirement("webclient-action-dispatch::a-non-success-action-result-surfaces-its-message-exactly-once")
    def test_rejected_preset_save_stays_on_the_list_without_confirmation(self):
        page = self._login_creation()
        install_outbound_recorder(page)
        self._wait_creation_available(page)
        self._focus_dock(page)
        _press(page, "Enter")  # 預設角色
        # Drive the preset-save dispatch the card wall uses with a key the deterministic
        # server gate rejects: the confirmation must stay off and the rejection
        # must be rendered on the preset list.
        page.evaluate(
            "window.__elosernBridge.store.dispatchAction('creation.preset', { preset_key: 'nonexistent_preset' })"
        )
        self.assertEqual(sent_action_count(page, "creation.preset"), 1)
        result = self._wait_result(
            page, lambda r: r["outcome"] == "rejected"
        )
        self.assertEqual(result["code"], "unknown_preset")
        # The dock never entered the confirmation view and still shows the list
        # with the rejection rendered.
        self.assertEqual(page.locator(".creation-confirm").count(), 0)
        self.assertGreaterEqual(page.locator('[data-testid="creation-body"] [data-testid="creation-preset-card"]').count(), 1)
        # The overlay is the presenting surface for a server result: the
        # message renders verbatim in the always-reachable result region
        # (webclient-action-result-feedback), never the bare code.
        self.assertIn(
            result["message"],
            page.evaluate("document.querySelector('[data-testid=\"creation-result-message\"]').textContent"),
        )
        self.assertEqual(sent_action_count(page, "creation.activate"), 0)
        self.assertEqual(self._dock_mode(page), "creation")
