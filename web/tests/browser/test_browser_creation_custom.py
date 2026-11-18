"""Custom character-creation browser journeys.
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
from .browser_base import ACCEPTANCE_VIEWPORTS, ui_scale
from .test_browser_creation_base import CreationBrowserTest


def _press(page, key, wait_ms=60):
    page.keyboard.press(key)
    page.wait_for_timeout(wait_ms)


def _active_testid(page):
    return page.evaluate(
        "document.activeElement && document.activeElement.getAttribute('data-testid')"
    )


def _open_step(page, step):
    """Open one custom-form step from the keyboard: focus its rail button and
    press Enter, then wait until that step's page is the one displayed."""
    page.evaluate(
        "(s) => document.querySelector(`[data-testid=\"creation-steps-tab-${s}\"]`).focus()",
        step,
    )
    _press(page, "Enter")
    page.wait_for_function(
        "(s) => { const p = document.querySelector(`[data-testid=\"creation-steps-panel-${s}\"]`);"
        " return p && p.offsetParent !== null; }",
        arg=step,
        timeout=5000,
    )


class CustomCreationJourneys(CreationBrowserTest):
    @covers_requirement("webclient-character-creation-ui::custom-step-navigation-preserves-unsent-form-authority")
    def test_stepped_form_keyboard_navigation_fits_both_viewports(self):
        page = self._login_creation()
        install_outbound_recorder(page)
        self._wait_creation_available(page)
        self._focus_dock(page)
        _press(page, "ArrowDown")  # 自訂角色
        _press(page, "Enter")
        page.wait_for_selector('[data-testid="creation-steps"]', timeout=30000)

        for width, height in ACCEPTANCE_VIEWPORTS:
            with self.subTest(viewport=(width, height)):
                page.set_viewport_size({"width": width, "height": height})
                page.wait_for_function(
                    "(v) => getComputedStyle(document.documentElement)"
                    ".getPropertyValue('--ui-scale').trim() === v",
                    arg="%g" % ui_scale((width, height)),
                    timeout=15000,
                )
                self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), width)
                for step in ("identity", "story", "allocation"):
                    _open_step(page, step)
                    metrics = page.evaluate(
                        """(s) => {
                          const pages = document.querySelector('.creation-steps__pages');
                          const footer = document.querySelector('.creation-overlay__footer').getBoundingClientRect();
                          const panel = document.querySelector(`[data-testid="creation-steps-panel-${s}"]`);
                          const controls = [...panel.querySelectorAll('input, select, textarea, button')]
                            .map((el) => el.getBoundingClientRect());
                          const remaining = document.querySelector('[data-testid="creation-steps-remaining"]');
                          return {
                            overflow: pages.scrollHeight - pages.clientHeight,
                            pageWidth: document.documentElement.scrollWidth,
                            lowest: Math.max(...controls.map((r) => r.bottom)),
                            highest: Math.min(...controls.map((r) => r.top)),
                            rightmost: Math.max(...controls.map((r) => r.right)),
                            footerTop: footer.top,
                            remainingShown: !!remaining && remaining.offsetParent !== null,
                          };
                        }""",
                        step,
                    )
                    # A normal step fits its page: no internal step scroll,
                    # every control above the footer and inside the viewport.
                    self.assertLessEqual(metrics["overflow"], 1, step)
                    self.assertLessEqual(metrics["pageWidth"], width, step)
                    self.assertGreaterEqual(metrics["highest"], 0, step)
                    self.assertLessEqual(metrics["lowest"], metrics["footerTop"], step)
                    self.assertLessEqual(metrics["rightmost"], width, step)
                    self.assertTrue(metrics["remainingShown"], step)

        # The rail is native buttons in Tab order, and previous/next moves
        # focus into the newly shown step.
        _open_step(page, "identity")
        _press(page, "Tab")
        self.assertEqual(_active_testid(page), "creation-steps-tab-story")
        page.evaluate("document.querySelector('[data-testid=\"creation-steps-next\"]').focus()")
        _press(page, "Enter", wait_ms=150)
        self.assertTrue(
            page.evaluate(
                "document.querySelector('[data-testid=\"creation-steps-panel-story\"]')"
                ".contains(document.activeElement)"
            )
        )
        page.evaluate("document.querySelector('[data-testid=\"creation-persona-personality\"]').focus()")
        page.keyboard.type("未送出的個性")

        # The fresh form has a subrace-bearing race and no subrace: confirming
        # from the allocation step sends nothing, reopens 身分 and focuses
        # the subrace select, while the typed story text survives.
        self.assertEqual(page.locator('[data-testid="creation-subrace"]').count(), 1)
        self.assertEqual(
            page.evaluate("document.querySelector('[data-testid=\"creation-subrace\"]').value"), ""
        )
        _open_step(page, "allocation")
        page.evaluate("document.querySelector('[data-testid=\"creation-submit\"]').focus()")
        _press(page, "Enter", wait_ms=150)
        self.assertEqual(sent_action_count(page, "creation.custom"), 0)
        self.assertEqual(_active_testid(page), "creation-subrace")
        self.assertEqual(
            page.evaluate(
                "document.querySelector('[data-testid=\"creation-steps-tab-identity\"]')"
                ".closest('li').getAttribute('data-state')"
            ),
            "error",
        )
        self.assertTrue(page.locator('[data-testid="creation-form-message"]').is_visible())
        self.assertEqual(
            page.evaluate("document.querySelector('[data-testid=\"creation-persona-personality\"]').value"),
            "未送出的個性",
        )

    @covers_requirement("webclient-character-creation-ui::the-creation-dock-is-keyboard-first-form-capable-and-confirmation-protected")
    @covers_requirement("creation-activation-gating::activation-confirmation-follows-a-successful-save")
    def test_custom_form_keyboard_journey_to_activation(self):
        page = self._login_creation()
        install_outbound_recorder(page)
        self._wait_creation_available(page)

        self._focus_dock(page)
        _press(page, "ArrowDown")  # 自訂角色
        _press(page, "Enter")

        # Name and age fields: focus the name field, then Tab/Shift+Tab
        # through the text/numeric fields exactly as a keyboard-only player does.
        page.evaluate("document.querySelector('[data-testid=\"creation-field-displayName\"]').focus()")
        page.keyboard.type("新冒險者")
        _press(page, "Tab")  # name -> name-roll button (namegen-creation-ui)
        self.assertEqual(
            page.evaluate("document.activeElement && document.activeElement.getAttribute('data-testid')"),
            "creation-roll-name",
            "Tab must move focus from the name field to the name-roll button",
        )
        _press(page, "Tab")  # roll button -> sex select
        self.assertEqual(
            page.evaluate("document.activeElement && document.activeElement.getAttribute('data-testid')"),
            "creation-sex",
            "Tab must move focus from the roll button to the sex select",
        )
        _press(page, "Tab")  # sex select -> actual age
        self.assertEqual(
            page.evaluate("document.activeElement && document.activeElement.getAttribute('data-testid')"),
            "creation-field-age",
            "Tab must move focus from the sex select to the age field",
        )
        page.keyboard.type("24")
        _press(page, "Tab")  # actual age -> apparent age
        self.assertEqual(
            page.evaluate("document.activeElement && document.activeElement.getAttribute('data-testid')"),
            "creation-field-apparentAge",
            "Tab must move focus to the apparent age field",
        )
        page.keyboard.type("24")
        _press(page, "Shift+Tab")  # apparent age -> actual age
        self.assertEqual(
            page.evaluate("document.activeElement && document.activeElement.getAttribute('data-testid')"),
            "creation-field-age",
            "Shift+Tab must move focus back to the age field",
        )
        _press(page, "Tab")  # back to apparent age, values preserved
        self.assertEqual(
            page.evaluate("document.activeElement && document.activeElement.getAttribute('data-testid')"),
            "creation-field-apparentAge",
        )

        # Select a race with keyboard arrows. One ArrowRight advances the
        # select from its first option to the next (and stays there when the
        # registry carries a single race). The Vue CreationOverlay renders
        # the race as a `<select data-testid="creation-race">`, and the
        # expected landing key is derived from the panel's advertised race
        # list, never a shipped key.
        draft = self._panel_driven_draft_values(page, race_index=1, last_subrace=True)
        page.evaluate("document.querySelector('[data-testid=\"creation-race\"]').focus()")
        _press(page, "ArrowRight")
        self.assertEqual(
            page.evaluate("document.querySelector('[data-testid=\"creation-race\"]').value"),
            draft["race"],
            "the derived race must be selected",
        )
        # Select the subrace with keyboard arrows. The select starts
        # unselected (the form opens fresh, without a draft), so Home anchors
        # the journey at the first subrace of the selected race; the journey
        # walks to the LAST one, so (count - 1) ArrowDown presses reach it.
        # Anchoring with Home keeps the count independent of draft state.
        page.evaluate("document.querySelector('[data-testid=\"creation-subrace\"]').focus()")
        _press(page, "Home")
        for _ in range(draft["subrace_presses"]):
            _press(page, "ArrowDown")
        page.wait_for_timeout(150)
        subrace_selected = page.evaluate(
            "() => document.querySelector('[data-testid=\"creation-subrace\"]').value"
        )
        self.assertEqual(
            subrace_selected, draft["subrace"], "the derived subrace must be selected"
        )

        # Fill the seven allocation inputs deterministically from the
        # advertised profile: one greedy span-fill that sums exactly to the
        # derived race/subrace budget. They live on the allocation step,
        # opened from the step rail by keyboard.
        _open_step(page, "allocation")
        for axis, value in draft["allocations"].items():
            page.evaluate(
                "document.querySelector('[data-testid=\"creation-field-%s\"]').focus()" % axis
            )
            page.keyboard.type(value)

        # Submit the custom form (keyboard-only Enter on the submit button).
        page.evaluate("document.querySelector('[data-testid=\"creation-submit\"]').focus()")
        _press(page, "Enter")
        self.assertEqual(sent_action_count(page, "creation.custom"), 1)
        payloads = self._sent_payloads(page, "creation.custom")
        self.assertEqual(len(payloads), 1)
        self.assertEqual(payloads[0]["race"], draft["race"])
        self.assertEqual(payloads[0]["subrace"], draft["subrace"])
        self.assertEqual(
            payloads[0]["allocations"],
            {axis: int(value) for axis, value in draft["allocations"].items()},
        )
        self.assertEqual(sum(payloads[0]["allocations"].values()), draft["budget"])

        # The confirmation screen appears only after the save result arrives;
        # Enter confirms activation.
        self._wait_confirm_ready(page)
        self.assertEqual(page.locator(".creation-confirm").count(), 1)
        _press(page, "Enter")
        self._wait_exploration(page)
        self.assertEqual(sent_action_count(page, "creation.activate"), 1)
        self.assertNotEqual(self._dock_mode(page), "creation")

    @covers_requirement("webclient-character-creation-ui::the-creation-dock-is-keyboard-first-form-capable-and-confirmation-protected")
    @covers_requirement("creation-activation-gating::activation-confirmation-follows-a-successful-save")
    def test_rejected_custom_save_stays_on_the_form_without_confirmation(self):
        page = self._login_creation()
        install_outbound_recorder(page)
        self._wait_creation_available(page)
        self._focus_dock(page)
        _press(page, "ArrowDown")
        _press(page, "Enter")  # 自訂角色

        # A name containing the Evennia markup delimiter passes the advisory
        # client validation but is rejected by the deterministic server gate.
        page.evaluate("document.querySelector('[data-testid=\"creation-field-displayName\"]').focus()")
        page.keyboard.type("壞|名字")
        _press(page, "Tab")
        page.keyboard.type("24")
        _press(page, "Tab")
        page.keyboard.type("24")
        # Select the default race's first subrace so the allocation fields
        # render; every race now requires a subrace. One ArrowDown from the
        # unselected select lands on the first advertised subrace.
        draft = self._panel_driven_draft_values(page)
        page.evaluate("document.querySelector('[data-testid=\"creation-subrace\"]').focus()")
        _press(page, "ArrowDown")
        page.wait_for_timeout(150)
        _open_step(page, "allocation")
        for axis, value in draft["allocations"].items():
            page.evaluate(
                "document.querySelector('[data-testid=\"creation-field-%s\"]').focus()" % axis
            )
            page.keyboard.type(value)
        page.evaluate("document.querySelector('[data-testid=\"creation-submit\"]').focus()")
        _press(page, "Enter")
        self.assertEqual(sent_action_count(page, "creation.custom"), 1)

        result = self._wait_result(
            page, lambda r: r["outcome"] == "rejected" and r["code"] == "markup_delimiter"
        )
        self.assertEqual(result["code"], "markup_delimiter")
        # The dock never entered the confirmation view and still shows the form
        # with the rejection rendered.
        self.assertEqual(page.locator(".creation-confirm").count(), 0)
        self.assertIsNotNone(page.locator('[data-testid="creation-submit"]'))
        # The overlay presents the server message verbatim in the result
        # region (webclient-action-result-feedback), never the bare code.
        self.assertIn(
            result["message"],
            page.evaluate("document.querySelector('[data-testid=\"creation-result-message\"]').textContent"),
        )
        self.assertEqual(sent_action_count(page, "creation.activate"), 0)
        self.assertEqual(self._dock_mode(page), "creation")
        self.assertIsNone(self._creation_panel(page)["draft"])

    @covers_requirement("webclient-character-creation-ui::the-age-range-gate-is-server-authoritative-for-both-age-fields")
    def test_out_of_range_actual_age_rejected_despite_disabled_client_validation(self):
        page = self._login_creation()
        install_outbound_recorder(page)
        self._wait_creation_available(page)
        self._focus_dock(page)
        _press(page, "ArrowDown")
        _press(page, "Enter")
        # Bypass client-side constraints entirely: remove the HTML minimums and
        # submit a raw ui_action (the dock's advisory check never sees it).
        page.evaluate(
            "() => { const f = document.querySelector('[data-testid=\"creation-field-age\"]'); "
            "f.min = ''; f.max = ''; }"
        )
        page.evaluate(
            """({payload}) => {
              const s = ((window.__elosernBridge && window.__elosernBridge.store.view) || null);
              Evennia.msg('ui_action', [{
                protocol_version: 1,
                presentation_epoch: s.epoch,
                request_id: 'out-of-range-age-1',
                base_revision: s.revision,
                action_id: 'creation.custom',
                payload,
              }], {});
            }""",
            {"payload": self._panel_valid_custom_payload(page, display_name="年輕冒險者", age=-1)},
        )
        result = self._wait_result(
            page,
            lambda r: r["outcome"] == "rejected" and r["code"] == "malformed_payload",
            timeout=15000,
        )
        self.assertEqual(result["outcome"], "rejected")
        # The wire mirrors the single 0..10000 authority exactly, so a below-
        # zero age is rejected structurally at the payload boundary before the
        # creation service ever sees it; the deterministic age_out_of_range
        # code stays reserved for drafts surfaced from other paths.
        self.assertEqual(result["code"], "malformed_payload")
        panel = self._creation_panel(page)
        self.assertTrue(panel["available"])
        self.assertIsNone(panel["draft"])
        self.assertEqual(sent_action_count(page, "creation.activate"), 0)
        # The dock remains the sole owner in creation mode.
        self.assertEqual(self._dock_mode(page), "creation")

    @covers_requirement("webclient-character-creation-ui::the-age-range-gate-is-server-authoritative-for-both-age-fields")
    def test_out_of_range_apparent_age_rejected_independently(self):
        page = self._login_creation()
        install_outbound_recorder(page)
        self._wait_creation_available(page)
        self._focus_dock(page)
        _press(page, "ArrowDown")
        _press(page, "Enter")
        page.evaluate(
            "() => { const f = document.querySelector('[data-testid=\"creation-field-apparentAge\"]'); "
            "f.min = ''; f.max = ''; }"
        )
        page.evaluate(
            """({payload}) => {
              const s = ((window.__elosernBridge && window.__elosernBridge.store.view) || null);
              Evennia.msg('ui_action', [{
                protocol_version: 1,
                presentation_epoch: s.epoch,
                request_id: 'out-of-range-apparent-1',
                base_revision: s.revision,
                action_id: 'creation.custom',
                payload,
              }], {});
            }""",
            {"payload": self._panel_valid_custom_payload(page, display_name="年輕冒險者", age=24, apparent_age=-1)},
        )
        result = self._wait_result(
            page,
            lambda r: r["outcome"] == "rejected" and r["code"] == "malformed_payload",
            timeout=15000,
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "malformed_payload")
        self.assertIsNone(self._creation_panel(page)["draft"])
