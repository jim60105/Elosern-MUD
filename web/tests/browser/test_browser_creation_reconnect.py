"""Character-creation reconnect browser journeys: saved-stage restoration without auto-resubmission.
"""

from __future__ import annotations

import time
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
