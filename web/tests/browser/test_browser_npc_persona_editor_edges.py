"""Real-browser edge scenarios for the NPC author persona editor."""

from playwright.sync_api import expect

from tools.spec_traceability import covers_requirement
from . import fixtures
from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    activate_overview_chip,
    install_outbound_recorder,
    sent_action_count,
    store_state,
    wait_for_store_state,
)
from .harness import ManagedServer, ManagedServerTearDownMixin
from .seed.npc_persona_fixture import (
    HOLDING_ROOM_NAME,
    NPC_NAME,
    NPC_SECOND_NAME,
    SECONDARY_CHARACTER_NAME,
)
from .seed.identity import BROWSER_ROOM_NAME


class NpcPersonaEditorEdgesBrowserTest(ManagedServerTearDownMixin, BrowserAcceptanceTest):
    """Real-browser edge journeys covering correlation, departure, session, and conflicts."""

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

    def _open(self, page, target_name=NPC_NAME):
        page.evaluate("() => window.__elosernBridge.store.resetFramesToRoot()")
        wait_for_store_state(
            page,
            lambda s: any(
                t.get("display_name") == target_name or t.get("name") == target_name
                for t in ((s.get("panels") or {}).get("exploration") or {}).get("interact", [])
            ),
        )
        target = next(
            t
            for t in store_state(page)["panels"]["exploration"]["interact"]
            if t.get("display_name") == target_name or t.get("name") == target_name
        )
        activate_overview_chip(page, f"target-{target['identity']}")
        activate_overview_chip(page, "service-npc_persona")
        expect(page.get_by_test_id("npc-persona-editor")).to_have_attribute(
            "data-state", "ready_clean"
        )
        return target["identity"]

    def _idle(self, page):
        wait_for_store_state(
            page,
            lambda s: s.get("phase") == "active"
            and not s.get("mutationsLocked")
            and not (s.get("dispatch") or {}).get("inFlight"),
        )

    @covers_requirement(
        "webclient-npc-persona-editor::editor-state-transitions-are-correlated-and-never-fabricate-outcomes"
    )
    def test_late_read_does_not_seed_different_npc(self):
        """A late read for a closed editor does not seed the next editor for another NPC."""
        page = self.logged_in_page()
        install_outbound_recorder(page)

        wait_for_store_state(
            page,
            lambda s: any(
                t.get("display_name") == NPC_NAME
                for t in ((s.get("panels") or {}).get("exploration") or {}).get("interact", [])
            ),
        )
        target1 = next(
            t
            for t in store_state(page)["panels"]["exploration"]["interact"]
            if t.get("display_name") == NPC_NAME
        )
        npc1_id = target1["identity"]

        # Open editor for NPC 1
        activate_overview_chip(page, f"target-{npc1_id}")
        activate_overview_chip(page, "service-npc_persona")
        expect(page.get_by_test_id("npc-persona-editor")).to_have_attribute("data-state", "ready_clean")
        self.assertEqual(sent_action_count(page, "npc.persona.read"), 1)

        # Close editor for NPC 1
        page.get_by_test_id("npc-persona-editor-cancel").click()
        expect(page.get_by_test_id("npc-persona-editor")).to_have_count(0)
        page.evaluate("() => window.__elosernBridge.store.resetFramesToRoot()")
        self._idle(page)

        # Open editor for NPC 2 (settles to ready_clean with NPC 2's card)
        npc2_id = self._open(page, target_name=NPC_SECOND_NAME)
        expect(page.get_by_test_id("npc-persona-editor")).to_have_attribute("data-npc-id", str(npc2_id))
        speech2 = page.get_by_test_id("npc-persona-field-speech_style")
        expect(speech2).to_have_value("說話嚴肅而準確")

        # Deliver late result for NPC 1 while NPC 2's editor is open
        # Verify that the store actually received the frame (asserting non-vacuous execution)
        received = page.evaluate(
            """(id) => {
            const store = window.__elosernBridge.store;
            const v = store.view;
            const res = store.receive(v.generation, 'ui_action_result', [{
                protocol_version: 1,
                presentation_epoch: v.epoch,
                request_id: 'late-read-fake',
                outcome: 'success',
                code: 'success',
                message: '讀取成功',
                presentation_revision: v.revision,
                data: {
                    npc_id: id,
                    display_name: '已關閉的NPC',
                    npc_title: '',
                    persona_version: 1,
                    persona: {
                        identity: { public: '偽造', hidden: '' },
                        appearance: '偽造',
                        personality: '偽造',
                        speech_style: '被晚到的結果覆蓋了！',
                        life_story: '偽造',
                        habit: '偽造',
                        social_connection: '',
                    },
                    default_greeting: '',
                }
            }]);
            return res;
        }""",
            npc1_id,
        )
        self.assertTrue(received.get("accepted"), "Injected frame must be accepted by the store")
        page.wait_for_timeout(500)

        # Confirm NPC 2's editor is still open, bound to NPC 2, and retains NPC 2's card
        expect(page.get_by_test_id("npc-persona-editor")).to_have_attribute("data-state", "ready_clean")
        expect(page.get_by_test_id("npc-persona-editor")).to_have_attribute("data-npc-id", str(npc2_id))
        expect(speech2).to_have_value("說話嚴肅而準確")

    @covers_requirement(
        "webclient-npc-persona-editor::conflicts-departures-and-session-changes-protect-the-draft"
    )
    def test_npc_departure_and_return_protects_draft(self):
        """The bound NPC leaving the room keeps the dirty draft with save disabled and recovers when it returns."""
        page = self.logged_in_page()
        install_outbound_recorder(page)
        npc_id = self._open(page)

        speech = page.get_by_test_id("npc-persona-field-speech_style")
        speech.fill("修改後的本地草稿")
        expect(page.get_by_test_id("npc-persona-editor")).to_have_attribute("data-state", "ready_dirty")
        expect(page.get_by_test_id("npc-persona-editor-save")).to_be_enabled()

        # Relocate NPC using the superuser admin session
        from .browser_helpers import login_and_open
        admin_page = self.new_page()
        login_and_open(admin_page, self.webclient_url, self.base_url, account="admin_dummy", password="AdminDummyPassword!2026")
        admin_page.evaluate(
            "([npc, room]) => Evennia.msg('text', [`@tel #${npc} = ${room}`], {})",
            [npc_id, HOLDING_ROOM_NAME],
        )
        # Refresh player page view
        page.evaluate("Evennia.msg('text', ['look'], {})")

        # Wait until NPC departure is reflected in exploration panel and editor flips to unavailable
        wait_for_store_state(
            page,
            lambda s: not any(
                t.get("identity") == npc_id
                for t in ((s.get("panels") or {}).get("exploration") or {}).get("interact", [])
            ),
        )
        expect(page.get_by_test_id("npc-persona-editor")).to_have_attribute("data-state", "unavailable")
        expect(page.get_by_test_id("npc-persona-editor-unavailable")).to_be_visible()
        expect(page.get_by_test_id("npc-persona-editor-save")).to_be_disabled()
        # Draft text remains intact
        expect(speech).to_have_value("修改後的本地草稿")

        # Teleport bound NPC back into the player's room via admin page
        admin_page.evaluate(
            "([npc, room]) => Evennia.msg('text', [`@tel #${npc} = ${room}`], {})",
            [npc_id, BROWSER_ROOM_NAME],
        )
        page.evaluate("Evennia.msg('text', ['look'], {})")

        # Wait until NPC returns to room
        wait_for_store_state(
            page,
            lambda s: any(
                t.get("identity") == npc_id
                for t in ((s.get("panels") or {}).get("exploration") or {}).get("interact", [])
            ),
        )

        # Editor recovers to ready_dirty with draft preserved and save enabled
        expect(page.get_by_test_id("npc-persona-editor")).to_have_attribute("data-state", "ready_dirty")
        expect(speech).to_have_value("修改後的本地草稿")
        expect(page.get_by_test_id("npc-persona-editor-save")).to_be_enabled()

        # Save completes cleanly
        page.get_by_test_id("npc-persona-editor-save").click()
        expect(page.get_by_test_id("npc-persona-editor")).to_have_attribute("data-state", "ready_clean")
        expect(page.get_by_test_id("npc-persona-editor-version")).to_have_text("第 2 版")

    @covers_requirement(
        "webclient-npc-persona-editor::conflicts-departures-and-session-changes-protect-the-draft"
    )
    def test_puppet_switch_clears_editor(self):
        """Switching the puppet closes the editor and leaves no card text in the store or browser storage."""
        page = self.logged_in_page()
        self._open(page)

        speech = page.get_by_test_id("npc-persona-field-speech_style")
        unique_secret = "絕密草稿內容9876543210"
        speech.fill(unique_secret)
        expect(page.get_by_test_id("npc-persona-editor")).to_have_attribute("data-state", "ready_dirty")

        char2_row = next(
            c for c in store_state(page)["rosterCharacters"] if not c["current"]
        )
        char2_id = char2_row["identity"]
        initial_epoch = store_state(page)["epoch"]

        # Switch puppet to second character
        page.evaluate(
            "(id) => window.__elosernBridge.store.dispatchAction('account.character.switch', {character_id: id})",
            char2_id,
        )

        # Wait for puppet transition to complete: new epoch and current character changed
        wait_for_store_state(
            page,
            lambda s: s.get("epoch") != initial_epoch
            and any(c.get("identity") == char2_id and c.get("current") for c in s.get("rosterCharacters", [])),
        )

        # Editor is closed
        expect(page.get_by_test_id("npc-persona-editor")).to_have_count(0)

        # Verify no card text remains in the client store or any persistent browser storage
        store_dump = page.evaluate("() => JSON.stringify(window.__elosernBridge.store.view)")
        self.assertNotIn(unique_secret, store_dump)

        storage_dump = page.evaluate(
            """() => {
            let res = '';
            for (let i = 0; i < localStorage.length; i++) {
                res += localStorage.getItem(localStorage.key(i)) || '';
            }
            for (let i = 0; i < sessionStorage.length; i++) {
                res += sessionStorage.getItem(sessionStorage.key(i)) || '';
            }
            return res;
        }"""
        )
        self.assertNotIn(unique_secret, storage_dump)

    @covers_requirement(
        "webclient-npc-persona-editor::conflicts-departures-and-session-changes-protect-the-draft"
    )
    def test_cross_tab_conflict_reload_and_discard(self):
        """Two pages edit the same NPC, the second save shows conflict, reload keeps draft, discard adopts latest."""
        page1 = self.logged_in_page()
        npc_id1 = self._open(page1)

        # Tab 1 opens editor, edits speech_style and saves -> becomes version 2
        speech1 = page1.get_by_test_id("npc-persona-field-speech_style")
        speech1.fill("分頁一已儲存的內容")
        page1.get_by_test_id("npc-persona-editor-save").click()
        expect(page1.get_by_test_id("npc-persona-editor")).to_have_attribute("data-state", "ready_clean")
        expect(page1.get_by_test_id("npc-persona-editor-version")).to_have_text("第 2 版")

        # Open page2 in the SAME browser context (same tab group / cookies) as page1
        # (Under MULTISESSION_MODE 0, connecting page2 claims the active puppet/session from page1).
        context = page1.context
        page2 = context.new_page()
        page2.add_init_script("""
window.__elosernWs = null;
(function () {
  var Native = window.WebSocket;
  function Wrapped(url, protocols) {
    var ws = new Native(url, protocols);
    window.__elosernWs = ws;
    return ws;
  }
  Wrapped.prototype = Native.prototype;
  Wrapped.CONNECTING = Native.CONNECTING;
  Wrapped.OPEN = Native.OPEN;
  Wrapped.CLOSING = Native.CLOSING;
  Wrapped.CLOSED = Native.CLOSED;
  window.WebSocket = Wrapped;
})();
""")
        from .browser_helpers import guard_local_only, wait_for_shell_active
        guard_local_only(page2)
        page2.goto(self.webclient_url)
        wait_for_shell_active(page2)

        npc_id2 = self._open(page2)
        self.assertEqual(npc_id1, npc_id2)
        expect(page2.get_by_test_id("npc-persona-editor-version")).to_have_text("第 2 版")

        # Tab 2 edits speech_style with local draft based on version 2
        speech2 = page2.get_by_test_id("npc-persona-field-speech_style")
        speech2.fill("分頁二的本地草稿")

        # In the meantime, another session/tab saves version 3 via direct backend action
        data2 = store_state(page2)["lastActionResult"]["data"]
        payload_v3 = {
            "npc_id": npc_id2,
            "expected_persona_version": 2,
            "persona": {**data2["persona"], "speech_style": "其他分頁儲存的第三版內容"},
            "offline_greeting": data2.get("offline_greeting") or "",
        }
        # Dispatch update to version 3 in background
        page2.evaluate(
            "payload => window.__elosernBridge.store.dispatchAction('npc.persona.update', payload)",
            payload_v3,
        )
        self._idle(page2)

        # Tab 2 attempts to save against stale version 2 -> server rejects with version conflict
        page2.get_by_test_id("npc-persona-editor-save").click()
        expect(page2.get_by_test_id("npc-persona-editor")).to_have_attribute("data-state", "conflict")
        expect(page2.get_by_test_id("npc-persona-editor-conflict")).to_be_visible()
        # Draft text intact
        expect(speech2).to_have_value("分頁二的本地草稿")

        # Tab 2 clicks reload: baseline updates to v3, draft remains intact
        page2.get_by_test_id("npc-persona-editor-reload").click()
        expect(page2.get_by_test_id("npc-persona-editor-version")).to_have_text("第 3 版")
        expect(speech2).to_have_value("分頁二的本地草稿")
        expect(page2.get_by_test_id("npc-persona-editor")).to_have_attribute("data-state", "ready_dirty")

        # Another update creates version 4
        payload_v4 = {
            "npc_id": npc_id2,
            "expected_persona_version": 3,
            "persona": {**data2["persona"], "speech_style": "其他分頁儲存的第四版內容"},
            "offline_greeting": data2.get("offline_greeting") or "",
        }
        page2.evaluate(
            "payload => window.__elosernBridge.store.dispatchAction('npc.persona.update', payload)",
            payload_v4,
        )
        self._idle(page2)

        # Tab 2 attempts save again (expected v3 vs actual v4) -> conflict
        page2.get_by_test_id("npc-persona-editor-save").click()
        expect(page2.get_by_test_id("npc-persona-editor-conflict")).to_be_visible()

        # Tab 2 clicks discard: adopts latest saved card from server (v4)
        page2.get_by_test_id("npc-persona-editor-discard").click()
        expect(page2.get_by_test_id("npc-persona-editor-version")).to_have_text("第 4 版")
        expect(speech2).to_have_value("其他分頁儲存的第四版內容")
        expect(page2.get_by_test_id("npc-persona-editor")).to_have_attribute("data-state", "ready_clean")

