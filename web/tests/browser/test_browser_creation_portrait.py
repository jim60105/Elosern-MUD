"""Creation portrait browser journeys (creation-draft-portrait).

Each journey drives the REAL path: the slot opens the shared generation
drawer, the drawer's submit dispatches ``creation.portrait.generate``, the
server admits it into the gallery queue, the harness worker drains it through
the controlled fake image client, and the completion push republishes the
creation panel (see ``creation_portrait_support``).
"""

from __future__ import annotations

import time

from tools.spec_traceability import covers_requirement

from .browser_base import ui_scale
from .browser_helpers import sent_action_count, store_state, wait_for_store_state
from .creation_portrait_support import (
    DRAWER,
    GENERATE,
    PROMPT,
    REFRESH_IN_DRAWER,
    SLOT,
    SUBMIT,
    CreationPortraitBrowserTest,
)


class CreationPortraitJourneys(CreationPortraitBrowserTest):
    # -- journeys -------------------------------------------------------------

    @covers_requirement("webclient-character-creation-ui::creation-portrait-controls-use-committed-state-and-the-shared-drawer")
    def test_generate_while_editing(self):
        page = self._open_custom()
        page.fill('[data-testid="creation-field-displayName"]', "編輯中的名字")
        page.fill('[data-testid="creation-field-apparentAge"]', "30")
        identity = page.evaluate(
            """() => {
              const v = (id) => { const el = document.querySelector(`[data-testid="${id}"]`); return el ? el.value : null; };
              return { race: v('creation-race'), subrace: v('creation-subrace'), sex: v('creation-sex') };
            }"""
        )
        self.assertEqual(self._portrait(page).get("status"), "empty")
        self._open_drawer(page)

        # The open drawer never scrolls the page sideways and keeps its submit
        # on screen at both reference viewports.
        for width, height in ((2560, 1440), (1451, 790)):
            with self.subTest(viewport=(width, height)):
                page.set_viewport_size({"width": width, "height": height})
                page.wait_for_function(
                    "(v) => getComputedStyle(document.documentElement)"
                    ".getPropertyValue('--ui-scale').trim() === v",
                    arg="%g" % ui_scale((width, height)),
                    timeout=15000,
                )
                self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), width)
                box = page.locator(f"{DRAWER} {SUBMIT}").bounding_box()
                self.assertIsNotNone(box)
                self.assertGreaterEqual(box["y"], 0)
                self.assertLessEqual(box["y"] + box["height"], height)
                self.assertLessEqual(box["x"] + box["width"], width)

        request = self._submit(page, "月光下回頭凝視")
        self.assertEqual(
            request["payload"],
            {
                "race": identity["race"],
                "subrace": identity["subrace"] or None,
                "sex": identity["sex"],
                "apparent_age": 30,
                "custom_prompt": "月光下回頭凝視",
            },
        )
        self.assertEqual(self._result_for(page, request)["outcome"], "success")
        self._wait_portrait(page, "pending")
        page.locator(DRAWER).wait_for(state="detached", timeout=15000)

        # Keep editing while the portrait is drawn.
        page.click('[data-testid="creation-steps-tab-story"]')
        page.fill('[data-testid="creation-background"]', "等待中寫下的背景")
        self._drain_once()
        self._wait_ready(page)
        page.locator('[data-testid="creation-portrait-artwork"]').wait_for(state="visible", timeout=15000)

        self.assertEqual(page.input_value('[data-testid="creation-field-displayName"]'), "編輯中的名字")
        self.assertEqual(page.input_value('[data-testid="creation-background"]'), "等待中寫下的背景")
        self.assertEqual(
            page.get_attribute('[aria-current="step"]', "data-testid"), "creation-steps-tab-story"
        )
        # Completion saved nothing, activated nothing and resent nothing.
        self.assertEqual(sent_action_count(page, "creation.custom"), 0)
        self.assertEqual(sent_action_count(page, "creation.activate"), 0)
        self.assertEqual(sent_action_count(page, GENERATE), 1)

    def test_reconnect_and_reset(self):
        page = self._open_custom()
        # Settle unrelated startup art first, so the held claim is ours alone.
        self.control.run("drain_sync")
        self.control.set(generate="hold")
        self._open_drawer(page)
        request = self._submit(page, "等待重新連線")
        self.assertEqual(self._result_for(page, request)["outcome"], "success")
        self._wait_portrait(page, "pending")
        # The worker claims the job and holds it in flight.
        self.assertEqual(self.control.run("drain").get("dispatched"), 1)

        generation_before = store_state(page)["generation"]
        page.evaluate("() => { if (window.__elosernWs) window.__elosernWs.close(4001); }")
        wait_for_store_state(page, lambda s: not s.get("connected"), timeout=30000)
        deadline = time.monotonic() + 30
        reconnected = False
        while time.monotonic() < deadline:
            if store_state(page)["generation"] > generation_before:
                break
            if not reconnected and time.monotonic() > deadline - 20:
                page.evaluate("Evennia.connect()")
                reconnected = True
            page.wait_for_timeout(500)
        wait_for_store_state(
            page, lambda s: s.get("connected") and s.get("phase") == "active", timeout=30000
        )
        self._wait_creation_available(page)
        # The server state is shown as it is; nothing was resubmitted.
        self.assertEqual(self._wait_portrait(page, "pending")["status"], "pending")
        self.assertEqual(sent_action_count(page, GENERATE), 1)

        # A confirmed reset cancels the in-flight request.
        page.click('[data-testid="creation-reset"]')
        page.locator('[data-testid="creation-confirm"]').wait_for(state="visible", timeout=15000)
        page.click('[data-testid="creation-confirm-ok"]')
        wait_for_store_state(
            page,
            lambda s: ((s.get("panels") or {}).get("creation") or {}).get("draft") is None
            and (((s.get("panels") or {}).get("creation") or {}).get("portrait") or {}).get("status") == "empty",
            timeout=30000,
        )

        # Release the held generation: its late output is rejected. A fresh
        # explicit request can only be claimed once that settlement freed the
        # worker, so its readiness proves the canceled image never landed.
        self.control.set(generate="ok")
        # The reset confirmation frame outlives its own success (existing
        # dock behaviour); leave it to return to the form.
        if page.locator('[data-testid="creation-confirm"]').count():
            page.click('[data-testid="creation-confirm-cancel"]')
            page.locator('[data-testid="creation-confirm"]').wait_for(state="detached", timeout=15000)
        if page.locator(SLOT).count() == 0:
            page.click('[data-testid="creation-mode-custom"]')
        page.locator(SLOT).wait_for(state="visible", timeout=15000)
        self._wait_portrait(page, "empty")
        self._open_drawer(page)
        retry = self._submit(page, "重設後的新肖像")
        self.assertEqual(self._result_for(page, retry)["outcome"], "success")
        self._wait_portrait(page, "pending")
        self._drain_when_worker_free()
        self._wait_portrait(page, "ready")
        self.assertEqual(len(self.control.run("cards")["image_ids"]), 1)
        self.assertEqual(sent_action_count(page, GENERATE), 2)

    @covers_requirement("webclient-character-creation-ui::creation-portrait-controls-use-committed-state-and-the-shared-drawer")
    def test_offline_refusal_and_explicit_retry(self):
        page = self._open_custom()
        self.control.set(probe="fail")
        self._open_drawer(page)
        refused = self._submit(page, "離線時寫下的提示")
        self.assertEqual(self._result_for(page, refused)["outcome"], "rejected")
        # The refusal's own publication projects the server signal.
        portrait = self._wait_portrait(page, "unavailable")
        self.assertTrue(portrait["reason"].strip())
        # Nothing durable was written: no job and no card.
        self.assertFalse(self._in_flight())
        self.assertEqual(self.control.run("cards")["image_ids"], [])
        # The drawer keeps the prompt editable, shows the reason, and disables
        # only submission.
        self.assertEqual(self._drawer_count(page), 1)
        self.assertEqual(page.input_value(PROMPT), "離線時寫下的提示")
        self.assertTrue(page.is_editable(PROMPT))
        self.assertTrue(page.is_disabled(f"{DRAWER} {SUBMIT}"))
        self.assertIn(portrait["reason"], page.inner_text(DRAWER))

        # The service recovers; the server's cached verdict is replaced, and
        # the player asks for the status explicitly.
        self.control.set(probe="ok")
        self.control.run("reset_probe_cache")
        syncs = self._syncs(page)
        page.click(f"{DRAWER} {REFRESH_IN_DRAWER}")
        self._wait_portrait(page, "empty")
        self.assertEqual(self._syncs(page), syncs + 1)
        # Refresh generated nothing and replayed nothing.
        self.assertEqual(sent_action_count(page, GENERATE), 1)
        self.assertFalse(self._in_flight())
        self.assertEqual(page.input_value(PROMPT), "離線時寫下的提示")
        self.assertTrue(page.is_enabled(f"{DRAWER} {SUBMIT}"))

        # One explicit retry goes through the real admission and worker.
        retry = self._submit(page)
        self.assertEqual(retry["payload"]["custom_prompt"], "離線時寫下的提示")
        self.assertEqual(self._result_for(page, retry)["outcome"], "success")
        self._wait_portrait(page, "pending")
        self._drain_once()
        self._wait_portrait(page, "ready")
        self.assertEqual(sent_action_count(page, GENERATE), 2)
