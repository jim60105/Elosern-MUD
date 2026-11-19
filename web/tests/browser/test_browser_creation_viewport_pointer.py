"""Character-creation viewport and pointer browser journeys.
"""

from __future__ import annotations

import copy

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
        # The finite controls are the Vue app's creation-field-* data-testid
        # hooks; the identity step opens first and shows its own.
        controls = page.locator(
            '[data-testid="creation-steps-panel-identity"] [data-testid^="creation-field-"]'
        )
        self.assertGreaterEqual(controls.count(), 1)
        for index in range(controls.count()):
            self.assertTrue(controls.nth(index).is_visible())
        # Every field is reachable on its step at all desktop acceptance
        # sizes: the portrait column and the steps sit side by side, each
        # step fits without internal scrolling, and focus reveals the whole
        # control above the footer actions.
        for width, height in ((1451, 790), (1741, 948), (2560, 1440)):
            with self.subTest(viewport=(width, height)):
                page.set_viewport_size({"width": width, "height": height})
                # The app writes its chrome factor from the resize listener, so
                # a read that straddles that write mixes two layouts. Wait for
                # the factor this viewport implies, then measure.
                page.wait_for_function(
                    "(v) => getComputedStyle(document.documentElement)"
                    ".getPropertyValue('--ui-scale').trim() === v",
                    arg="%g" % ui_scale((width, height)),
                    timeout=15000,
                )
                self.assertLessEqual(
                    page.evaluate("document.documentElement.scrollWidth"), width
                )
                columns = page.evaluate(
                    """() => ['creation-portrait-slot', 'creation-steps']
                      .map((id) => document.querySelector(`[data-testid="${id}"]`).getBoundingClientRect())
                      .map((r) => ({ x: r.x, width: r.width }))"""
                )
                self.assertLessEqual(columns[0]["x"] + columns[0]["width"], columns[1]["x"])
                self.assertLessEqual(columns[1]["x"] + columns[1]["width"], width)
                for step in ("identity", "story", "allocation"):
                    page.locator(f'[data-testid="creation-steps-tab-{step}"]').click()
                    panel = page.locator(f'[data-testid="creation-steps-panel-{step}"]')
                    panel.wait_for(state="visible", timeout=5000)
                    self.assertLessEqual(
                        page.evaluate(
                            "() => { const p = document.querySelector('.creation-steps__pages');"
                            " return p.scrollHeight - p.clientHeight; }"
                        ),
                        1,
                        step,
                    )
                    fields = panel.locator("input, select, textarea")
                    for index in range(fields.count()):
                        field = fields.nth(index)
                        if field.is_disabled():
                            continue
                        field.focus()
                        box = field.bounding_box()
                        footer = page.locator(".creation-overlay__footer").bounding_box()
                        self.assertGreaterEqual(box["y"], 0)
                        self.assertLessEqual(box["y"] + box["height"], footer["y"])
        page.locator('[data-testid="creation-steps-tab-identity"]').click()
        # Direct entry is never normalized by a decorative bar or a stepper.
        subrace = page.locator('[data-testid="creation-subrace"]')
        if subrace.count():
            subrace.select_option(index=0)
        page.locator('[data-testid="creation-steps-tab-allocation"]').click()
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


    @covers_requirement(
        "webclient-character-creation-ui::creation-controls-preserve-native-entry-and-existing-authority"
    )
    def test_allocation_slider_tilde_range_and_zero_cap_lock(self):
        page = self._login_creation((1451, 790))
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
        subrace = page.locator('[data-testid="creation-subrace"]')
        if subrace.count():
            subrace.select_option(index=0)
        page.locator('[data-testid="creation-steps-tab-allocation"]').click()
        page.locator('[data-testid="creation-steps-panel-allocation"]').wait_for(
            state="visible", timeout=5000
        )

        axes = ("hp", "mp", "sp", "atk_phys", "agility", "defense", "magic_power")
        open_axes = [
            axis
            for axis in axes
            if page.locator(f'[data-testid="creation-field-{axis}"]').count()
            and int(page.locator(f'[data-testid="creation-field-{axis}"]').get_attribute("max")) > 0
        ]
        self.assertGreaterEqual(len(open_axes), 2)
        axis_a, axis_b = open_axes[:2]

        # A: the slider spans the advertised range and mirrors the number field.
        number_a = page.locator(f'[data-testid="creation-field-{axis_a}"]')
        slider_a = page.locator(f'[data-testid="creation-slider-{axis_a}"]')
        max_a = int(number_a.get_attribute("max"))
        self.assertEqual(slider_a.get_attribute("min"), "0")
        self.assertEqual(slider_a.get_attribute("max"), str(max_a))
        self.assertEqual(slider_a.get_attribute("step"), "1")
        first, second = str(max_a), str(max_a - 1)
        slider_a.fill(first)
        self.assertEqual(number_a.input_value(), first)
        number_a.fill(second)
        self.assertEqual(slider_a.input_value(), second)
        self.assertIn(
            f"0~{max_a}", page.locator(f"#creation-axis-help-{axis_a}").inner_text()
        )

        # B: a panel that zero-caps the axis locks its controls once applied.
        number_b = page.locator(f'[data-testid="creation-field-{axis_b}"]')
        number_b.fill("0")
        # A focused number field never locks mid-edit; leave it first.
        number_b.blur()
        panel = copy.deepcopy(self._creation_panel(page))
        for profile in panel["custom"]["profiles"]:
            for axis in profile["axes"]:
                if axis["axis"] == axis_b:
                    axis["point_cap"] = 0
                    axis["value_at_cap"] = axis["minimum"]
        inject_update(page, {"creation": panel}, mode="creation")
        page.wait_for_function(
            "(axis) => document.querySelector(`[data-testid=\"creation-slider-${axis}\"]`)"
            "?.getAttribute('max') === '0'",
            arg=axis_b,
            timeout=15000,
        )
        for testid in (
            f"creation-field-{axis_b}",
            f"creation-slider-{axis_b}",
            f"creation-step-{axis_b}-up",
            f"creation-step-{axis_b}-down",
        ):
            self.assertTrue(page.locator(f'[data-testid="{testid}"]').is_disabled(), testid)
        self.assertEqual(
            page.locator(f'[data-testid="creation-field-{axis_b}"]').evaluate(
                "(el) => el.closest('.creation-allocation').dataset.locked"
            ),
            "true",
        )


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
        page.locator('[data-testid="creation-steps-tab-allocation"]').click()
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
