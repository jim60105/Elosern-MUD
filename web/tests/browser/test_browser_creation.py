"""Keyboard-only character-creation browser acceptance (webclient-character-creation-ui).

These journeys drive the real Evennia server's creation surface through the
Vue creation overlay (CreationOverlay): preset selection → confirmation → activation →
exploration snapshot with the creation dock torn down, custom form via
keyboard-only finite controls and free-text fields, server rejection of both
underage fields despite bypassed client validation, the destructive reset
confirmation, stale and duplicate submission behavior, reconnect at a saved
draft stage that never auto-resubmits activation, and viewport verification at
1440x900 and 1280x720.

Each creation journey boots its own dedicated isolated server so the mutated
character state (activation, draft) never leaks into another journey. All
fixtures are deterministic; no remote, LLM, or image service is involved.
"""

from __future__ import annotations

import time

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    focus_creation_action_dock,
    install_outbound_recorder,
    inject_update,
    outbound_messages,
    sent_action_count,
    store_state,
    wait_for_store_state,
)
from .harness import ManagedServer
from . import fixtures
from .seed import CREATION_ACCOUNT_PASSWORD, CREATION_ACCOUNT_USERNAME


def _press(page, key, wait_ms=60):
    page.keyboard.press(key)
    page.wait_for_timeout(wait_ms)


class CreationBrowserTest(BrowserAcceptanceTest):
    """Boots one dedicated isolated server per test with a creation fixture."""

    CREATION_DRAFT = False
    CREATION_PRESET_DRAFT = False

    @classmethod
    def setUpClass(cls) -> None:
        # Each test boots its own isolated server; never the shared one.
        pass

    def setUp(self) -> None:
        runtime = fixtures.create_runtime()
        runtime.env["ELOSERN_BROWSER_CREATION"] = "1"
        if self.CREATION_DRAFT:
            runtime.env["ELOSERN_BROWSER_CREATION_DRAFT"] = "1"
        if self.CREATION_PRESET_DRAFT:
            runtime.env["ELOSERN_BROWSER_CREATION_PRESET_DRAFT"] = "1"
        self.server = ManagedServer(runtime=runtime)
        self.server.start()
        self.base_url = f"http://127.0.0.1:{self.server.runtime.http_port}"
        self.webclient_url = self.server.runtime.webclient_url
        super().setUp()

    def tearDown(self) -> None:
        server = getattr(self, "server", None)
        super().tearDown()
        if server is not None:
            try:
                server.stop()
            finally:
                self.server = None

    # -- navigation helpers ---------------------------------------------------

    def _login_creation(self, viewport=None):
        """Open a guarded page, log in as the pending account, wait for creation."""
        page = self.new_page(viewport if viewport else (1440, 900))
        login_url = f"{self.base_url}/auth/login/"
        attempts = 4
        for attempt in range(attempts):
            page.goto(login_url)
            try:
                page.wait_for_selector("#id_username", timeout=20000)
                break
            except Exception:
                if attempt == attempts - 1:
                    raise
                page.wait_for_timeout(1500)
        page.fill("#id_username", CREATION_ACCOUNT_USERNAME)
        page.fill("#id_password", CREATION_ACCOUNT_PASSWORD)
        page.click('input[type="submit"]')
        page.wait_for_load_state("networkidle")
        page.goto(self.webclient_url)
        self._wait_creation_available(page)
        return page

    def _creation_panel(self, page):
        panels = store_state(page)["panels"]
        return panels.get("creation")

    def _dock_mode(self, page):
        return page.locator("#action-dock").get_attribute("data-mode", timeout=5000)

    def _wait_creation_available(self, page, timeout=60000):
        captured = {}

        def _creation_ready(state):
            if not state.get("connected") or state.get("mode") != "creation":
                return False
            panel = (state.get("panels") or {}).get("creation")
            if panel and panel.get("available") is True:
                captured["panel"] = panel
                return True
            return False

        wait_for_store_state(
            page,
            _creation_ready,
            dom_readiness={
                "selector": '[data-testid="creation-overlay"]',
                "predicate": (
                    "() => { const o = document.querySelector('[data-testid=\"creation-overlay\"]'); "
                    "const d = document.querySelector('#action-dock'); "
                    "if (!o) { return false; } "
                    "if (!d || d.getAttribute('data-mode') !== 'creation') { return false; } "
                    "const r = d.getBoundingClientRect(); "
                    "return r.width > 0 && r.height > 0 && d.offsetParent !== null; }"
                ),
                "description": "creation overlay mounted and creation-mode action-dock visible",
            },
            timeout=timeout,
        )
        return captured["panel"]

    def _wait_exploration(self, page, timeout=60000):
        def _exploration_ready(state):
            return state.get("connected") and state.get("mode") == "exploration"

        wait_for_store_state(page, _exploration_ready, timeout=timeout)

    def _wait_confirm_ready(self, page, timeout=30000):
        """Wait until the confirmation frame is mounted and the router unlocked.

        The confirm screen renders synchronously with the submit, but the
        router rejects Enter while the just-sent mutation is still in flight
        (``confirm()`` emits ``locked``); on a loaded runner the server
        response can arrive after the test's fixed delay and swallow the
        confirmation. Polling for an unlocked router with the confirm frame
        mounted makes the confirmation deterministic. The store gate covers
        the deterministic side: connected, phase active, mutations unlocked,
        and the just-sent action result committed to ``lastActionResult``.
        """
        def _confirm_ready(state):
            if not state.get("connected") or state.get("phase") != "active":
                return False
            if state.get("mutationsLocked") is True:
                return False
            return state.get("lastActionResult") is not None

        wait_for_store_state(
            page,
            _confirm_ready,
            dom_readiness={
                "selector": '[data-testid="creation-confirm"]',
                "predicate": (
                    "() => { const c = document.querySelector('[data-testid=\"creation-confirm\"]'); "
                    "return c !== null; }"
                ),
                "description": "creation confirmation frame mounted",
            },
            timeout=timeout,
        )

    def _wait_result(self, page, predicate, timeout=30000):
        captured = {}

        def _result_ready(state):
            result = state.get("lastActionResult")
            if result is not None and predicate(result):
                captured["result"] = result
                return True
            return False

        wait_for_store_state(page, _result_ready, timeout=timeout)
        return captured["result"]

    def _focus_dock(self, page):
        focus_creation_action_dock(page)

    def _sent_payloads(self, page, action_id):
        payloads = []
        for cmd, args, _kw in outbound_messages(page):
            if cmd == "ui_action" and args and args[0].get("action_id") == action_id:
                payloads.append(args[0].get("payload"))
        return payloads

    def _wait_draft_name_restored(self, page, timeout=30000):
        def _draft_restored(state):
            panel = (state.get("panels") or {}).get("creation") or {}
            draft = panel.get("draft")
            return bool(draft and draft.get("display_name") == "草稿角色")

        wait_for_store_state(
            page,
            _draft_restored,
            dom_readiness={
                "selector": '[data-testid="creation-field-displayName"]',
                "predicate": (
                    "() => { const f = document.querySelector('[data-testid=\"creation-field-displayName\"]'); "
                    "return f && f.value === '草稿角色'; }"
                ),
                "description": "creation name field shows the restored draft",
            },
            timeout=timeout,
        )


class PresetCreationJourneys(CreationBrowserTest):
    @covers_requirement("webclient-character-creation-ui::creation-browser-acceptance-is-keyboard-only-and-desktop-bounded")
    @covers_requirement("creation-activation-gating::activation-confirmation-follows-a-successful-save")
    def test_preset_selection_confirm_activate_reaches_exploration(self):
        page = self._login_creation()
        install_outbound_recorder(page)
        panel = self._wait_creation_available(page)
        self.assertEqual(len(panel["presets"]), 8)
        self.assertEqual(self._dock_mode(page), "creation")

        # Focus the action dock and open the preset list (keyboard only).
        self._focus_dock(page)
        _press(page, "Enter")  # 預設角色
        _press(page, "Enter")  # human_wanderer card (first preset)
        self.assertEqual(sent_action_count(page, "creation.preset"), 1)
        payloads = self._sent_payloads(page, "creation.preset")
        self.assertEqual(payloads, [{"preset_key": "human_wanderer"}])

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
        _press(page, "Enter")  # human_wanderer card -> confirmation screen
        self._wait_confirm_ready(page)
        self.assertEqual(page.locator(".creation-confirm").count(), 1)
        _press(page, "Escape")  # pop exactly one level back to the preset list
        self.assertEqual(page.locator(".creation-confirm").count(), 0)
        self.assertGreaterEqual(page.locator('[data-testid="creation-body"] .creation-preset-card').count(), 1)
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
        # Drive the dock's own preset-submit path with a key the deterministic
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
        self.assertGreaterEqual(page.locator('[data-testid="creation-body"] .creation-preset-card').count(), 1)
        # The overlay is the presenting surface for a server result: the
        # message renders verbatim in the always-reachable result region
        # (webclient-action-result-feedback), never the bare code.
        self.assertIn(
            result["message"],
            page.evaluate("document.querySelector('[data-testid=\"creation-result-message\"]').textContent"),
        )
        self.assertEqual(sent_action_count(page, "creation.activate"), 0)
        self.assertEqual(self._dock_mode(page), "creation")


class CustomCreationJourneys(CreationBrowserTest):
    @covers_requirement("webclient-character-creation-ui::the-creation-dock-is-keyboard-first-form-capable-and-confirmation-protected")
    @covers_requirement("creation-activation-gating::activation-confirmation-follows-a-successful-save")
    def test_custom_form_keyboard_journey_to_activation(self):
        page = self._login_creation()
        install_outbound_recorder(page)
        self._wait_creation_available(page)

        self._focus_dock(page)
        _press(page, "ArrowDown")  # 自訂角色
        _press(page, "Enter")

        # Name and adult age fields: focus the name field, then Tab/Shift+Tab
        # through the text/numeric fields exactly as a keyboard-only player does.
        page.evaluate("document.querySelector('[data-testid=\"creation-field-displayName\"]').focus()")
        page.keyboard.type("新冒險者")
        _press(page, "Tab")  # name -> actual age
        self.assertEqual(
            page.evaluate("document.activeElement && document.activeElement.getAttribute('data-testid')"),
            "creation-field-age",
            "Tab must move focus from the name field to the age field",
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

        # Select the beastfolk race with keyboard arrows (human -> beastfolk).
        # The Vue CreationOverlay renders the race as a `<select data-testid="creation-race">`.
        page.evaluate("document.querySelector('[data-testid=\"creation-race\"]').focus()")
        _press(page, "ArrowRight")
        self.assertEqual(
            page.evaluate("document.querySelector('[data-testid=\"creation-race\"]').value"),
            "beastfolk",
            "beastfolk race must be selected",
        )
        # Select the foxkin subrace with keyboard arrows. The select starts
        # unselected (the form opens fresh, without a draft), so Home anchors
        # the journey at the first beastfolk subrace; beastfolk has seven
        # subraces, foxkin is the last, so six ArrowDown presses reach it.
        # Anchoring with Home keeps the count independent of draft state.
        page.evaluate("document.querySelector('[data-testid=\"creation-subrace\"]').focus()")
        _press(page, "Home")
        for _ in range(6):
            _press(page, "ArrowDown")
        page.wait_for_timeout(150)
        foxkin_selected = page.evaluate(
            "() => document.querySelector('[data-testid=\"creation-subrace\"]').value"
        )
        self.assertEqual(foxkin_selected, "foxkin", "foxkin subrace must be selected")

        # Fill the seven allocation inputs deterministically for
        # beastfolk/foxkin: 25+10+25+15+15+15+14 == the 119-point budget.
        page.evaluate("document.querySelector('[data-testid=\"creation-field-hp\"]').focus()")
        page.keyboard.type("25")
        page.evaluate("document.querySelector('[data-testid=\"creation-field-mp\"]').focus()")
        page.keyboard.type("10")
        page.evaluate("document.querySelector('[data-testid=\"creation-field-sp\"]').focus()")
        page.keyboard.type("25")
        page.evaluate("document.querySelector('[data-testid=\"creation-field-atk_phys\"]').focus()")
        page.keyboard.type("15")
        page.evaluate("document.querySelector('[data-testid=\"creation-field-agility\"]').focus()")
        page.keyboard.type("15")
        page.evaluate("document.querySelector('[data-testid=\"creation-field-defense\"]').focus()")
        page.keyboard.type("15")
        page.evaluate("document.querySelector('[data-testid=\"creation-field-magic_power\"]').focus()")
        page.keyboard.type("14")

        # Submit the custom form (keyboard-only Enter on the submit button).
        page.evaluate("document.querySelector('[data-testid=\"creation-submit\"]').focus()")
        _press(page, "Enter")
        self.assertEqual(sent_action_count(page, "creation.custom"), 1)
        payloads = self._sent_payloads(page, "creation.custom")
        self.assertEqual(len(payloads), 1)
        self.assertEqual(payloads[0]["race"], "beastfolk")
        self.assertEqual(payloads[0]["subrace"], "foxkin")
        self.assertEqual(payloads[0]["allocations"]["hp"], 25)

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
        # Select the default race's first subrace (human_commoner) so the
        # allocation fields render; every race now requires a subrace.
        page.evaluate("document.querySelector('[data-testid=\"creation-subrace\"]').focus()")
        _press(page, "ArrowDown")
        page.wait_for_timeout(150)
        for axis, value in (
            ("hp", "50"), ("mp", "50"), ("sp", "50"),
            ("atk_phys", "10"), ("agility", "10"), ("defense", "11"),
            ("magic_power", "43"),
        ):
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

    @covers_requirement("webclient-character-creation-ui::the-adult-gate-is-server-authoritative-for-both-age-fields")
    def test_underage_actual_age_rejected_despite_disabled_client_validation(self):
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
            """() => {
              const s = ((window.__elosernBridge && window.__elosernBridge.store.view) || null);
              Evennia.msg('ui_action', [{
                protocol_version: 1,
                presentation_epoch: s.epoch,
                request_id: 'underage-age-1',
                base_revision: s.revision,
                action_id: 'creation.custom',
                payload: {
                  display_name: '年輕冒險者',
                  age: 17,
                  apparent_age: 24,
                  race: 'human',
                  subrace: "human_commoner",
                  background: null,
                  affinity_elements: null,
                  persona: null,
                  allocations: { hp: 50, mp: 50, sp: 50, atk_phys: 10, agility: 10, defense: 11, magic_power: 43 },
                },
              }], {});
            }"""
        )
        result = self._wait_result(
            page,
            lambda r: r["outcome"] == "rejected" and r["code"] in ("underage_age", "malformed_payload"),
            timeout=15000,
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "underage_age")
        panel = self._creation_panel(page)
        self.assertTrue(panel["available"])
        self.assertIsNone(panel["draft"])
        self.assertEqual(sent_action_count(page, "creation.activate"), 0)
        # The dock remains the sole owner in creation mode.
        self.assertEqual(self._dock_mode(page), "creation")

    @covers_requirement("webclient-character-creation-ui::the-adult-gate-is-server-authoritative-for-both-age-fields")
    def test_underage_apparent_age_rejected_independently(self):
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
            """() => {
              const s = ((window.__elosernBridge && window.__elosernBridge.store.view) || null);
              Evennia.msg('ui_action', [{
                protocol_version: 1,
                presentation_epoch: s.epoch,
                request_id: 'underage-apparent-1',
                base_revision: s.revision,
                action_id: 'creation.custom',
                payload: {
                  display_name: '年輕冒險者',
                  age: 24,
                  apparent_age: 17,
                  race: 'human',
                  subrace: "human_commoner",
                  background: null,
                  affinity_elements: null,
                  persona: null,
                  allocations: { hp: 50, mp: 50, sp: 50, atk_phys: 10, agility: 10, defense: 11, magic_power: 43 },
                },
              }], {});
            }"""
        )
        result = self._wait_result(
            page,
            lambda r: r["outcome"] == "rejected" and r["code"] in ("underage_apparent_age", "malformed_payload"),
            timeout=15000,
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "underage_apparent_age")
        self.assertIsNone(self._creation_panel(page)["draft"])


class ConceptCreationJourneys(CreationBrowserTest):
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
            ["allocations", "persona", "race", "revision", "subrace"],
        )
        self.assertEqual(proposal["revision"], 1)
        self.assertEqual(proposal["race"], "human")
        # The form is only pre-filled, never auto-submitted.
        self.assertEqual(sent_action_count(page, "creation.custom"), 0)
        # The player confirms the notice and the custom form shows the
        # proposal's finite values pre-filled.
        page.evaluate("document.querySelector('[data-testid=\"creation-proposal-open\"]').focus()")
        _press(page, "Enter")
        self.assertEqual(
            page.evaluate("() => document.querySelector('[data-testid=\"creation-overlay\"]').getAttribute('data-mode')"),
            "custom",
        )
        # The pre-filled race select and allocation fields come from the proposal.
        self.assertEqual(
            page.evaluate("document.querySelector('[data-testid=\"creation-race\"]').value"),
            "human",
            "the proposal race must be pre-selected",
        )
        self.assertEqual(
            page.evaluate("document.querySelector('[data-testid=\"creation-subrace\"]').value"),
            "human_commoner",
        )
        self.assertEqual(
            page.evaluate("document.querySelector('[data-testid=\"creation-field-hp\"]').value"),
            "50",
        )
        # The three persona textareas carry the proposal prose, editable.
        self.assertEqual(
            page.evaluate("document.querySelector('[data-testid=\"creation-persona-personality\"]').value"),
            "沉穩",
        )
        # The retired generated indicator never renders.
        self.assertEqual(page.locator('[data-testid="creation-concept-indicator"]').count(), 0)

        # Complete the form keyboard-only: name and both adult ages only; the
        # finite controls and persona prose are already filled from the proposal.
        page.evaluate("document.querySelector('[data-testid=\"creation-field-displayName\"]').focus()")
        page.keyboard.type("新冒險者")
        _press(page, "Tab")  # name -> actual age
        self.assertEqual(
            page.evaluate("document.activeElement && document.activeElement.getAttribute('data-testid')"),
            "creation-field-age",
            "Tab must move focus from the name field to the age field",
        )
        page.keyboard.type("24")
        _press(page, "Tab")  # actual age -> apparent age
        page.keyboard.type("24")
        page.evaluate("document.querySelector('[data-testid=\"creation-submit\"]').focus()")
        _press(page, "Enter")
        self.assertEqual(sent_action_count(page, "creation.custom"), 1)
        payloads = self._sent_payloads(page, "creation.custom")
        self.assertEqual(len(payloads), 1)
        self.assertEqual(payloads[0]["race"], "human")
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

    @covers_requirement("webclient-frame-resolution::the-resolver-table-completes-with-the-services-combat-and-creation-families")
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
                    "schema_version": 2,
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


class CreationDispatchJourneys(CreationBrowserTest):
    @covers_requirement("webclient-character-creation-ui::creation-actions-reject-stale-duplicate-and-tampered-input-without-mutation")
    def test_stale_revision_returns_stale_without_mutation(self):
        page = self._login_creation()
        install_outbound_recorder(page)
        panel = self._wait_creation_available(page)
        stale_revision = store_state(page)["revision"] - 1

        page.evaluate(
            """({stale_revision}) => {
              const s = ((window.__elosernBridge && window.__elosernBridge.store.view) || null);
              Evennia.msg('ui_action', [{
                protocol_version: 1,
                presentation_epoch: s.epoch,
                request_id: 'stale-custom-1',
                base_revision: stale_revision,
                action_id: 'creation.custom',
                payload: {
                  display_name: '不應儲存',
                  age: 20,
                  apparent_age: 20,
                  race: 'human',
                  subrace: "human_commoner",
                  background: null,
                  affinity_elements: null,
                  persona: null,
                  allocations: { hp: 50, mp: 50, sp: 50, atk_phys: 10, agility: 10, defense: 11, magic_power: 43 },
                },
              }], {});
            }""",
            {"stale_revision": stale_revision},
        )
        result = self._wait_result(page, lambda r: r["requestId"] == "stale-custom-1")
        self.assertEqual(result["outcome"], "stale")
        self.assertEqual(result["code"], "stale")
        self.assertIsNone(self._creation_panel(page)["draft"])

    @covers_requirement("webclient-character-creation-ui::creation-actions-reject-stale-duplicate-and-tampered-input-without-mutation")
    def test_duplicate_request_executes_custom_once(self):
        page = self._login_creation()
        install_outbound_recorder(page)
        panel = self._wait_creation_available(page)
        revision = store_state(page)["revision"]

        def send_custom(request_id):
            page.evaluate(
                """({revision, request_id}) => {
                  const s = ((window.__elosernBridge && window.__elosernBridge.store.view) || null);
                  Evennia.msg('ui_action', [{
                    protocol_version: 1,
                    presentation_epoch: s.epoch,
                    request_id,
                    base_revision: revision,
                    action_id: 'creation.custom',
                    payload: {
                      display_name: '重複角色',
                      age: 20,
                      apparent_age: 20,
                  race: 'human',
                  subrace: 'human_commoner',
                  background: null,
                  affinity_elements: null,
                  persona: null,
                  allocations: { hp: 50, mp: 50, sp: 50, atk_phys: 10, agility: 10, defense: 11, magic_power: 43 },
                    },
                  }], {});
                }""",
                {"revision": revision, "request_id": request_id},
            )

        send_custom("dup-custom-1")
        first = self._wait_result(
            page, lambda r: r["requestId"] == "dup-custom-1" and r["outcome"] == "success"
        )
        self.assertEqual(first["outcome"], "success")
        def _draft_present(state):
            panel = (state.get("panels") or {}).get("creation") or {}
            return panel.get("draft") is not None

        wait_for_store_state(page, _draft_present, timeout=30000)
        self.assertEqual(self._creation_panel(page)["draft"]["display_name"], "重複角色")
        self.assertEqual(sent_action_count(page, "creation.custom"), 1)

        send_custom("dup-custom-1")
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if sent_action_count(page, "creation.custom") >= 2:
                break
            page.wait_for_timeout(250)
        self.assertEqual(sent_action_count(page, "creation.custom"), 2)
        page.wait_for_timeout(600)
        self.assertEqual(self._creation_panel(page)["draft"]["display_name"], "重複角色")

    @covers_requirement("webclient-character-creation-ui::the-creation-dock-is-keyboard-first-form-capable-and-confirmation-protected")
    def test_stale_custom_preserves_typed_values_and_asks_for_review(self):
        page = self._login_creation()
        install_outbound_recorder(page)
        self._wait_creation_available(page)
        self._focus_dock(page)
        _press(page, "ArrowDown")
        _press(page, "Enter")  # 自訂角色
        page.evaluate("document.querySelector('[data-testid=\"creation-field-displayName\"]').focus()")
        page.keyboard.type("尚未送出")

        # A stale custom save cannot resubmit automatically: the server returns
        # stale and emits a fresh snapshot, so the dock keeps the typed value.
        stale_revision = store_state(page)["revision"] - 1
        page.evaluate(
            """({stale_revision}) => {
              const s = ((window.__elosernBridge && window.__elosernBridge.store.view) || null);
              Evennia.msg('ui_action', [{
                protocol_version: 1,
                presentation_epoch: s.epoch,
                request_id: 'stale-typed-1',
                base_revision: stale_revision,
                action_id: 'creation.custom',
                payload: {
                  display_name: '不應儲存',
                  age: 20,
                  apparent_age: 20,
                  race: 'human',
                  subrace: "human_commoner",
                  background: null,
                  affinity_elements: null,
                  persona: null,
                  allocations: { hp: 50, mp: 50, sp: 50, atk_phys: 10, agility: 10, defense: 11, magic_power: 43 },
                },
              }], {});
            }""",
            {"stale_revision": stale_revision},
        )
        result = self._wait_result(page, lambda r: r["requestId"] == "stale-typed-1")
        self.assertEqual(result["outcome"], "stale")
        # The typed unsent value was preserved and no action was auto-submitted.
        self.assertEqual(
            page.evaluate("document.querySelector('[data-testid=\"creation-field-displayName\"]').value"),
            "尚未送出",
        )
        self.assertEqual(sent_action_count(page, "creation.custom"), 1)
        self.assertEqual(sent_action_count(page, "creation.activate"), 0)
        self.assertIsNone(self._creation_panel(page)["draft"])


class ReconnectCreationJourney(CreationBrowserTest):
    CREATION_DRAFT = True

    @covers_requirement("webclient-character-creation-ui::creation-browser-acceptance-is-keyboard-only-and-desktop-bounded")
    def test_reconnect_restores_saved_stage_and_never_auto_resubmits(self):
        page = self._login_creation()
        install_outbound_recorder(page)
        panel = self._wait_creation_available(page)
        self.assertEqual(panel["draft"]["display_name"], "草稿角色")
        generation_before = store_state(page)["generation"]

        page.evaluate(
            "() => { if (window.__elosernWs) window.__elosernWs.close(4001); }"
        )
        wait_for_store_state(page, lambda s: not s.get("connected"), timeout=30000)
        deadline = time.monotonic() + 30
        reconnects = 0
        while time.monotonic() < deadline:
            state = store_state(page)
            if state["generation"] > generation_before:
                break
            if reconnects == 0 and time.monotonic() > deadline - 20:
                page.evaluate("Evennia.connect()")
                reconnects += 1
            page.wait_for_timeout(500)
        wait_for_store_state(
            page, lambda s: s.get("connected") and s.get("phase") == "active", timeout=30000
        )
        self._wait_creation_available(page)
        panel = self._creation_panel(page)
        self.assertTrue(panel["available"])
        # The draft stage was restored and no activation was auto-submitted.
        self.assertEqual(panel["draft"]["display_name"], "草稿角色")
        self.assertEqual(sent_action_count(page, "creation.activate"), 0)


class ReconnectPresetCreationJourney(CreationBrowserTest):
    CREATION_PRESET_DRAFT = True

    @covers_requirement("webclient-character-creation-ui::creation-browser-acceptance-is-keyboard-only-and-desktop-bounded")
    def test_reconnect_restores_preset_stage_and_never_auto_activates(self):
        page = self._login_creation()
        install_outbound_recorder(page)
        panel = self._wait_creation_available(page)
        self.assertEqual(panel["draft"]["mode"], "preset")
        self.assertEqual(panel["draft"]["stage"], "preset_selected")
        generation_before = store_state(page)["generation"]

        page.evaluate(
            "() => { if (window.__elosernWs) window.__elosernWs.close(4001); }"
        )
        wait_for_store_state(page, lambda s: not s.get("connected"), timeout=30000)
        deadline = time.monotonic() + 30
        reconnects = 0
        while time.monotonic() < deadline:
            state = store_state(page)
            if state["generation"] > generation_before:
                break
            if reconnects == 0 and time.monotonic() > deadline - 20:
                page.evaluate("Evennia.connect()")
                reconnects += 1
            page.wait_for_timeout(500)
        wait_for_store_state(
            page, lambda s: s.get("connected") and s.get("phase") == "active", timeout=30000
        )
        self._wait_creation_available(page)
        panel = self._creation_panel(page)
        self.assertTrue(panel["available"])
        # The preset_selected stage survived the reconnect and no activation was
        # auto-submitted; the dock resumes at the preset confirmation screen.
        self.assertEqual(panel["draft"]["mode"], "preset")
        self.assertEqual(panel["draft"]["stage"], "preset_selected")
        self.assertEqual(sent_action_count(page, "creation.activate"), 0)


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
            page.locator('[data-testid="narrative-feed"]').is_visible(),
            "the narrative feed is display:none in creation mode",
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


if __name__ == "__main__":
    import unittest

    unittest.main()
