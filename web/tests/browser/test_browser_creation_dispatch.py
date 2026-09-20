"""Character-creation dispatch browser journeys: stale revisions and duplicate custom submissions.
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


def _press(page, key, wait_ms=60):
    page.keyboard.press(key)
    page.wait_for_timeout(wait_ms)


class CreationDispatchJourneys(CreationBrowserTest):
    @covers_requirement("webclient-character-creation-ui::creation-actions-reject-stale-duplicate-and-tampered-input-without-mutation")
    def test_stale_revision_returns_stale_without_mutation(self):
        page = self._login_creation()
        install_outbound_recorder(page)
        panel = self._wait_creation_available(page)
        stale_revision = store_state(page)["revision"] - 1

        page.evaluate(
            """({stale_revision, payload}) => {
              const s = ((window.__elosernBridge && window.__elosernBridge.store.view) || null);
              Evennia.msg('ui_action', [{
                protocol_version: 1,
                presentation_epoch: s.epoch,
                request_id: 'stale-custom-1',
                base_revision: stale_revision,
                action_id: 'creation.custom',
                payload,
              }], {});
            }""",
            {
                "stale_revision": stale_revision,
                "payload": self._panel_valid_custom_payload(page, display_name="不應儲存"),
            },
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
                """({revision, request_id, payload}) => {
                  const s = ((window.__elosernBridge && window.__elosernBridge.store.view) || null);
                  Evennia.msg('ui_action', [{
                    protocol_version: 1,
                    presentation_epoch: s.epoch,
                    request_id,
                    base_revision: revision,
                    action_id: 'creation.custom',
                    payload,
                  }], {});
                }""",
                {
                    "revision": revision,
                    "request_id": request_id,
                    "payload": self._panel_valid_custom_payload(page, display_name="重複角色"),
                },
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
            """({stale_revision, payload}) => {
              const s = ((window.__elosernBridge && window.__elosernBridge.store.view) || null);
              Evennia.msg('ui_action', [{
                protocol_version: 1,
                presentation_epoch: s.epoch,
                request_id: 'stale-typed-1',
                base_revision: stale_revision,
                action_id: 'creation.custom',
                payload,
              }], {});
            }""",
            {
                "stale_revision": stale_revision,
                "payload": self._panel_valid_custom_payload(page, display_name="不應儲存"),
            },
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
