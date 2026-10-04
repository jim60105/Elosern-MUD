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
    @covers_requirement(
        "webclient-character-creation-ui::creation-browser-acceptance-is-keyboard-only-and-desktop-bounded",
        "webclient-character-creation-ui::creation-presents-a-bounded-desktop-identity-form-and-allocation-workspace",
        "webclient-character-creation-ui::creation-controls-preserve-native-entry-and-existing-authority",
        "webclient-character-creation-ui::creation-resource-and-offense-labels-are-distinguishable",
    )
    def test_reference_viewport_keeps_creation_essentials_visible_and_literal(self):
        page = self._login_creation((1451, 790))
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
        # Reach every field through the bounded scroll regions at all desktop
        # acceptance sizes. Focus must reveal the entire control above actions.
        for width, height in ((1451, 790), (1741, 948), (2560, 1440)):
            with self.subTest(viewport=(width, height)):
                page.set_viewport_size({"width": width, "height": height})
                self.assertLessEqual(
                    page.evaluate("document.documentElement.scrollWidth"), width
                )
                regions = page.locator(".creation-region")
                boxes = [regions.nth(i).bounding_box() for i in range(3)]
                self.assertLessEqual(boxes[0]["x"] + boxes[0]["width"], boxes[1]["x"])
                self.assertLessEqual(boxes[1]["width"], 640)
                self.assertLessEqual(boxes[1]["x"] + boxes[1]["width"], boxes[2]["x"])
                fields = page.locator(
                    '[data-testid="creation-body"] input, '
                    '[data-testid="creation-body"] select, '
                    '[data-testid="creation-body"] textarea'
                )
                for index in range(fields.count()):
                    field = fields.nth(index)
                    if field.is_disabled():
                        continue
                    field.focus()
                    field.scroll_into_view_if_needed()
                    box = field.bounding_box()
                    footer = page.locator(".creation-overlay__footer").bounding_box()
                    self.assertGreaterEqual(box["y"], 0)
                    self.assertLessEqual(box["y"] + box["height"], footer["y"])
        # Direct entry is never normalized by a decorative bar or a stepper.
        subrace = page.locator('[data-testid="creation-subrace"]')
        if subrace.count():
            subrace.select_option(index=0)
        mana = page.locator('[data-testid="creation-field-mp"]')
        offense = page.locator('[data-testid="creation-field-magic_power"]')
        self.assertNotEqual(
            page.locator('label[for="creation-allocation-mp"]').inner_text(),
            page.locator('label[for="creation-allocation-magic_power"]').inner_text(),
        )
        original_mana, original_offense = mana.input_value(), offense.input_value()
        mana.fill(str(int(mana.get_attribute("min")) + 1))
        self.assertEqual(offense.input_value(), original_offense)
        new_mana = mana.input_value()
        offense.fill(str(int(offense.get_attribute("min")) + 1))
        self.assertEqual(mana.input_value(), new_mana)
        mana.fill(original_mana)
        offense.fill(original_offense)
        axis = page.locator('[data-testid="creation-field-hp"]')
        maximum = int(axis.get_attribute("max"))
        axis.fill(str(maximum + 1))
        self.assertTrue(page.locator('[data-testid="creation-step-hp-up"]').is_disabled())
        self.assertTrue(page.locator('[data-testid="creation-step-hp-down"]').is_disabled())
        page.locator('[data-testid="creation-submit"]').click()
        self.assertEqual(axis.input_value(), str(maximum + 1))
        self.assertTrue(page.locator('[data-testid="creation-form-message"]').is_visible())
        self.assertEqual(sent_action_count(page, "creation.custom"), 0)
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
