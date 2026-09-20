"""Concept-field character-creation browser journeys at both viewports.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement
from web.browser_support.browser_fixtures_data import (
    concept_placeholder_values,
    custom_draft_form_values,
)
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


class ConceptCreationJourneys(CreationBrowserTest):
    # retool-concept-transient-fill: keyboard-only concept -> transient
    # proposal fill -> complete form -> activate at both supported desktop
    # viewports with a deterministic placeholder. Each journey boots its own
    # isolated server (the activated character state of one journey must never
    # leak into the next login).
    # retool-concept-transient-fill: keyboard-only concept -> transient
    # proposal fill -> complete form -> activate at both supported desktop
    # viewports with a deterministic placeholder. Each journey boots its own
    # isolated server (the activated character state of one journey must never
    # leak into the next login).
    @covers_requirement("concept-transient-fill::the-browser-form-pre-fills-from-the-proposal-without-submitting")
    def test_concept_field_journey_to_activation_at_1440x900(self):
        self._concept_journey((1440, 900))

    @covers_requirement("concept-transient-fill::the-browser-form-pre-fills-from-the-proposal-without-submitting")
    def test_concept_field_journey_to_activation_at_1280x720(self):
        self._concept_journey((1280, 720))

    def _concept_journey(self, viewport):
        page = self._login_creation(viewport)
        install_outbound_recorder(page)
        self._wait_creation_available(page)
        self._focus_dock(page)
        _press(page, "ArrowDown")  # 自訂角色
        _press(page, "ArrowDown")  # 角色概念 (dedicated concept entry point)
        _press(page, "Enter")

        # Concept field: keyboard-first entry and apply (bounded text field).
        page.evaluate("document.querySelector('[data-testid=\"creation-field-concept\"]').focus()")
        page.keyboard.type("流浪的精靈劍士")
        page.evaluate("document.querySelector('[data-testid=\"creation-concept-submit\"]').focus()")
        _press(page, "Enter")
        self.assertEqual(sent_action_count(page, "creation.concept"), 1)
        payloads = self._sent_payloads(page, "creation.concept")
        self.assertEqual(payloads, [{"concept": "流浪的精靈劍士"}])

        # The proposal lands transiently on the panel: the draft stays absent
        # (zero persistent writes) and the panel carries the revisioned slot.
        def _proposal_panel(state):
            panel = (state.get("panels") or {}).get("creation") or {}
            return bool(panel.get("proposal")) and panel.get("draft") is None

        wait_for_store_state(page, _proposal_panel, timeout=30000)
        panel = self._creation_panel(page)
        self.assertIsNone(panel["draft"], "a concept apply never persists a draft")
        proposal = panel["proposal"]
        self.assertEqual(
            sorted(proposal),
            [
                "affinity_elements",
                "age",
                "allocations",
                "apparent_age",
                "background",
                "display_name",
                "persona",
                "race",
                "revision",
                "subrace",
            ],
        )
        self.assertEqual(proposal["revision"], 1)
        # The expected pre-filled identity follows the placeholder resolver
        # (shipped: the wizard snapshot; synthetic: the first live race pair
        # with a greedy budget spend and empty affinity), re-derived here
        # from the same panel — never a hardcoded shipped row. This journey's
        # runtime boots shipped catalogs (class docstring), so the resolver
        # forwards the wizard snapshot; the explicit mode keeps the helper in
        # step with the runtime regardless of the process-wide default.
        placeholder = concept_placeholder_values(panel, synth=False)
        self.assertEqual(proposal["race"], placeholder["race"])
        self.assertEqual(proposal["subrace"], placeholder["subrace"])
        # The form is only pre-filled, never auto-submitted.
        self.assertEqual(sent_action_count(page, "creation.custom"), 0)
        # retool-concept-fill-navigation: the loading state settled at the
        # completion moment, the form auto-landed on the custom tab (no
        # in-form notice, no confirmation click), and exactly one info toast
        # confirmed the apply through the action-feedback queue.
        self.assertEqual(page.locator('[data-testid="creation-concept-loading"]').count(), 0)
        info_toasts = page.locator(
            '[data-testid="feedback-toast-queue"] .toast[data-tone="info"]'
        )
        self.assertEqual(info_toasts.count(), 1)
        self.assertIn("概念提案已套用到自訂表單", info_toasts.first.inner_text())
        self.assertEqual(
            page.evaluate("() => document.querySelector('[data-testid=\"creation-overlay\"]').getAttribute('data-mode')"),
            "custom",
        )
        # The pre-filled race select and allocation fields come from the proposal.
        self.assertEqual(
            page.evaluate("document.querySelector('[data-testid=\"creation-race\"]').value"),
            placeholder["race"],
            "the proposal race must be pre-selected",
        )
        self.assertEqual(
            page.evaluate("document.querySelector('[data-testid=\"creation-subrace\"]').value"),
            placeholder["subrace"],
        )
        self.assertEqual(
            page.evaluate("document.querySelector('[data-testid=\"creation-field-hp\"]').value"),
            str(placeholder["allocations"]["hp"]),
        )
        # The three persona textareas carry the proposal prose, editable.
        self.assertEqual(
            page.evaluate("document.querySelector('[data-testid=\"creation-persona-personality\"]').value"),
            "沉穩",
        )
        # The five transient-fill fields land from the proposal (issue set
        # 3-6): name, both ages, background, and the affinity checkboxes.
        self.assertEqual(
            page.evaluate("document.querySelector('[data-testid=\"creation-field-displayName\"]').value"),
            "燈下學徒",
        )
        self.assertEqual(
            page.evaluate("document.querySelector('[data-testid=\"creation-field-age\"]').value"),
            "30",
        )
        self.assertEqual(
            page.evaluate("document.querySelector('[data-testid=\"creation-field-apparentAge\"]').value"),
            "27",
        )
        self.assertEqual(
            page.evaluate("document.querySelector('[data-testid=\"creation-background\"]').value"),
            "在燈下抄書長大的見習劍士。",
        )
        self.assertEqual(
            page.evaluate(
                "() => [...document.querySelectorAll('[data-testid^=\"creation-affinity-\"]')]"
                ".filter((el) => el.checked).map((el) => el.getAttribute('data-testid'))"
            ),
            sorted(placeholder["affinity_checked"]),
        )
        # The retired generated indicator never renders.
        self.assertEqual(page.locator('[data-testid="creation-concept-indicator"]').count(), 0)
        # The retired in-form proposal notice and its button are gone.
        self.assertEqual(page.locator('[data-testid="creation-proposal-notice"]').count(), 0)
        self.assertEqual(page.locator('[data-testid="creation-proposal-open"]').count(), 0)

        # Complete the form keyboard-only: the transient fields now arrive
        # pre-filled, so the journey only verifies the Tab order from the
        # name field onward (name -> name-roll button -> sex -> age, the
        # namegen-creation-ui contract shared with the custom journey) and
        # re-firms the ages before submitting.
        page.evaluate("document.querySelector('[data-testid=\"creation-field-displayName\"]').focus()")
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
        page.evaluate("document.querySelector('[data-testid=\"creation-submit\"]').focus()")
        _press(page, "Enter")
        self.assertEqual(sent_action_count(page, "creation.custom"), 1)
        payloads = self._sent_payloads(page, "creation.custom")
        self.assertEqual(len(payloads), 1)
        self.assertEqual(payloads[0]["race"], placeholder["race"])
        # The pre-filled transient values ride the custom payload unchanged.
        self.assertEqual(payloads[0]["display_name"], "燈下學徒")
        self.assertEqual(payloads[0]["age"], 30)
        self.assertEqual(payloads[0]["apparent_age"], 27)
        self.assertEqual(payloads[0]["background"], "在燈下抄書長大的見習劍士。")
        self.assertEqual(payloads[0]["affinity_elements"], placeholder["affinity_elements"])
        # The player-confirmed proposal prose rides the custom payload.
        self.assertEqual(
            payloads[0]["persona"],
            {
                "personality": "沉穩",
                "life_story": "來自邊境的小村，靠磨劍維生",
                "habit": "清晨練劍",
            },
        )

        # Confirmation screen, then activation hands off to exploration. The
        # confirmation appears only after the custom save result arrives.
        self._wait_confirm_ready(page)
        self.assertEqual(page.locator(".creation-confirm").count(), 1)
        _press(page, "Enter")
        self._wait_exploration(page)
        self.assertEqual(sent_action_count(page, "creation.activate"), 1)
        self.assertNotEqual(self._dock_mode(page), "creation")
        # The transient slot is dropped by the custom save: the activation
        # journey commits it and no stale proposal survives.
        serialized = __import__("json").dumps(store_state(page), ensure_ascii=False)
        self.assertNotIn('"proposal"', serialized)
