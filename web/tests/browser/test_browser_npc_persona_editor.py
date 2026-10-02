"""Real initialized-NPC author editor journeys over the production Vue bundle."""

from playwright.sync_api import expect

from tools.spec_traceability import covers_requirement
from . import fixtures
from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    activate_overview_chip,
    install_outbound_recorder,
    narrative_log_text,
    sent_action_count,
    store_state,
    wait_for_store_state,
)
from .harness import ManagedServer, ManagedServerTearDownMixin
from .seed.npc_persona_fixture import NPC_NAME


class NpcPersonaEditorBrowserTest(ManagedServerTearDownMixin, BrowserAcceptanceTest):
    """Boot a fresh synthetic initialized NPC per journey."""

    @classmethod
    def setUpClass(cls):
        pass

    def setUp(self):
        runtime = fixtures.create_runtime()
        runtime.env["ELOSERN_BROWSER_NPC_PERSONA"] = "1"
        self.server = ManagedServer(runtime=runtime)
        self.server.start()
        self.base_url = f"http://127.0.0.1:{self.server.runtime.http_port}"
        self.webclient_url = self.server.runtime.webclient_url
        super().setUp()

    def _open(self, page):
        wait_for_store_state(page, lambda s: any(t.get("display_name") == NPC_NAME or t.get("name") == NPC_NAME for t in ((s.get("panels") or {}).get("exploration") or {}).get("interact", [])))
        target = next(t for t in store_state(page)["panels"]["exploration"]["interact"] if t.get("display_name") == NPC_NAME or t.get("name") == NPC_NAME)
        activate_overview_chip(page, f"target-{target['identity']}")
        activate_overview_chip(page, "service-npc_persona")
        expect(page.get_by_test_id("npc-persona-editor")).to_have_attribute("data-state", "ready_clean")
        return target["identity"]

    def _idle(self, page):
        wait_for_store_state(page, lambda s: s.get("phase") == "active" and not s.get("mutationsLocked") and not (s.get("dispatch") or {}).get("inFlight"))

    @covers_requirement("webclient-npc-persona-editor::the-author-editor-opens-from-the-selected-target-and-binds-to-it")
    @covers_requirement("webclient-npc-persona-editor::the-editor-presents-the-full-card-and-the-offline-greeting-with-notices-and-budgets")
    def test_save_reopen_and_offline_greeting(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        npc_id = self._open(page)
        self.assertEqual(sent_action_count(page, "npc.persona.read"), 1)
        expect(page.get_by_test_id("hud-drawer")).to_have_attribute("aria-labelledby", "npc-persona-editor-title")
        expect(page.get_by_test_id("npc-persona-editor-notice-spoiler")).to_be_visible()
        expect(page.get_by_test_id("npc-persona-editor-notice-static")).to_be_visible()
        speech = page.get_by_test_id("npc-persona-field-speech_style")
        greeting = page.get_by_test_id("npc-persona-field-offline_greeting")
        original_total = page.get_by_test_id("npc-persona-editor-total").inner_text()
        greeting.fill("問" * 301)
        expect(page.get_by_test_id("npc-persona-editor-save")).to_be_disabled()
        self.assertEqual(page.get_by_test_id("npc-persona-editor-total").inner_text(), original_total)
        greeting.fill("\ufeff\u0085「渡口今日風平浪靜。」\u0085\ufeff")
        speech.fill("\ufeff\u0085說話輕快，喜歡用渡船比喻。\u0085\ufeff")
        page.get_by_test_id("npc-persona-editor-save").click()
        expect(page.get_by_test_id("npc-persona-editor")).to_have_attribute("data-state", "ready_clean")
        expect(page.get_by_test_id("npc-persona-editor-version")).to_have_text("第 2 版")
        self.assertEqual(sent_action_count(page, "npc.persona.update"), 1)
        page.screenshot(path="/tmp/npc-editor-storyboard/app-saved.png")

        # Boundary-only edit: add \uFEFF and spaces to greeting
        greeting.fill("  \ufeff「渡口今日風平浪靜。」\u0085 ")
        # Normalized-clean: no dirty state and cancel closes without confirmation dialog
        expect(page.get_by_test_id("npc-persona-editor")).to_have_attribute("data-state", "ready_clean")
        page.get_by_test_id("npc-persona-editor-cancel").click()
        expect(page.get_by_test_id("npc-persona-editor")).to_have_count(0)
        expect(page.locator(".npe-confirm")).to_have_count(0)
        self._idle(page)
        # Closing restores the existing verb popover, not a new router frame.
        activate_overview_chip(page, "service-npc_persona")
        expect(speech).to_have_value("說話輕快，喜歡用渡船比喻。")
        expect(greeting).to_have_value("「渡口今日風平浪靜。」")
        page.get_by_test_id("npc-persona-editor-cancel").click()
        self._idle(page)
        page.evaluate("id => window.__elosernBridge.store.dispatchAction('explore.talk_open', {npc_id:id})", npc_id)
        wait_for_store_state(page, lambda s: "渡口今日風平浪靜" in narrative_log_text(page))
        self.assertIn("渡口今日風平浪靜", narrative_log_text(page))

    @covers_requirement("webclient-npc-persona-editor::editor-closing-and-accessibility-follow-the-shell-s-dialog-rules")
    @covers_requirement("webclient-npc-persona-editor::editor-state-transitions-are-correlated-and-never-fabricate-outcomes")
    def test_keyboard_dirty_close_and_field_rejection(self):
        page = self.logged_in_page((420, 860))
        install_outbound_recorder(page)
        self._open(page)
        speech = page.get_by_test_id("npc-persona-field-speech_style")
        speech.focus()
        before_move = sent_action_count(page, "explore.move")
        page.keyboard.press("ControlOrMeta+A")
        page.keyboard.type("wasd123\\")
        self.assertEqual(sent_action_count(page, "explore.move"), before_move)
        page.keyboard.press("Escape")
        expect(page.get_by_role("alertdialog")).to_be_visible()
        page.keyboard.press("Escape")
        expect(speech).to_be_focused()
        expect(speech).to_have_value("wasd123\\")
        # Exercise a genuine server rejection while retaining the submitted UI
        # draft: corrupt just this transport payload, never synthesize a result.
        page.evaluate("""() => {
            const original = Evennia.msg.bind(Evennia);
            Evennia.msg = function(cmd, args, kwargs, cb) {
                if (cmd === 'ui_action' && args[0].action_id === 'npc.persona.update') {
                    args = structuredClone(args); args[0].payload.persona.speech_style = '';
                    Evennia.msg = original;
                }
                return original(cmd,args,kwargs,cb);
            };
        }""")
        page.keyboard.press("ControlOrMeta+Enter")
        expect(page.get_by_test_id("npc-persona-editor")).to_have_attribute("data-state", "rejected")
        expect(speech).to_have_value("wasd123\\")
        expect(speech).to_be_focused()
        expect(speech).to_have_attribute("aria-invalid", "true")
        page.screenshot(path="/tmp/npc-editor-storyboard/app-narrow-rejected.png")
        # The scrim shares the same dirty guard as keyboard Escape.
        page.locator('[data-testid="hud-drawer-scrim"]').click(position={"x": 2, "y": 2})
        expect(page.get_by_role("alertdialog")).to_be_visible()
        page.get_by_test_id("npc-persona-editor-confirm-discard").focus()
        page.keyboard.press("Enter")
        expect(page.get_by_test_id("npc-persona-editor")).to_have_count(0)
        self.assertNotEqual(page.evaluate("document.activeElement.tagName"), "BODY")

    @covers_requirement("webclient-npc-persona-editor::conflicts-departures-and-session-changes-protect-the-draft")
    def test_single_page_conflict_reload_and_discard(self):
        page = self.logged_in_page()
        npc_id = self._open(page)
        data = store_state(page)["lastActionResult"]["data"]
        speech = page.get_by_test_id("npc-persona-field-speech_style")
        speech.fill("本地草稿")
        payload = {"npc_id": npc_id, "expected_persona_version": data["persona_version"], "persona": {**data["persona"], "speech_style": "他處已儲存"}, "offline_greeting": data["offline_greeting"]}
        page.evaluate("payload => window.__elosernBridge.store.dispatchAction('npc.persona.update', payload)", payload)
        self._idle(page)
        page.get_by_test_id("npc-persona-editor-save").click()
        expect(page.get_by_test_id("npc-persona-editor-conflict")).to_be_visible()
        expect(speech).to_have_value("本地草稿")
        page.screenshot(path="/tmp/npc-editor-storyboard/app-conflict.png")
        page.get_by_test_id("npc-persona-editor-reload").click()
        expect(page.get_by_test_id("npc-persona-editor-version")).to_have_text("第 2 版")
        expect(speech).to_have_value("本地草稿")
        # A second conflict makes explicit discard load the latest server card.
        payload["expected_persona_version"] = 2
        payload["persona"]["speech_style"] = "更新的他處內容"
        self._idle(page)
        page.evaluate("payload => window.__elosernBridge.store.dispatchAction('npc.persona.update', payload)", payload)
        self._idle(page)
        page.get_by_test_id("npc-persona-editor-save").click()
        expect(page.get_by_test_id("npc-persona-editor-conflict")).to_be_visible()
        page.get_by_test_id("npc-persona-editor-discard").click()
        expect(speech).to_have_value("更新的他處內容")
        expect(page.get_by_test_id("npc-persona-editor-version")).to_have_text("第 3 版")
        expect(page.get_by_test_id("npc-persona-editor")).to_have_attribute("data-state", "ready_clean")
