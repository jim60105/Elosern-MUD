"""Keyboard-only exploration browser acceptance (webclient-exploration-menu 4.2-4.6).

These journeys drive the real Evennia server's exploration dock: movement
through ``explore.move`` with matching clock/map updates, look that preserves
the onboarding beat, scripted keyword dialogue, free-form dialogue with offline
degrade, engage-to-combat, wait/rest daypart and duration with safety
rejections, stale/duplicate/tampered rejections, the no-take/drop rule, and
reconnect retention.

Each exploration journey boots its own dedicated isolated server so the mutated
character state never leaks into another journey. All fixtures are
deterministic; no remote, LLM, or image service is involved.
"""

from __future__ import annotations

import time

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    install_outbound_recorder,
    sent_action_count,
    store_state,
)
from .harness import ManagedServer
from . import fixtures


def _press(page, key, wait_ms=80):
    page.keyboard.press(key)
    page.wait_for_timeout(wait_ms)


class ExplorationBrowserTest(BrowserAcceptanceTest):
    """Boots one dedicated isolated server per test with the exploration fixture."""

    @classmethod
    def setUpClass(cls) -> None:
        pass

    def setUp(self) -> None:
        runtime = fixtures.create_runtime()
        runtime.env["ELOSERN_BROWSER_EXPLORATION"] = "1"
        self.server = ManagedServer(runtime=runtime)
        self.server.start()
        self.base_url = f"http://127.0.0.1:{self.server.runtime.http_port}"
        self.webclient_url = self.server.runtime.webclient_url
        super().setUp()

    def tearDown(self) -> None:
        super().tearDown()
        if getattr(self, "server", None) is not None:
            try:
                self.server.stop()
            finally:
                self.server = None

    def _exploration_panel(self, page):
        return store_state(page)["panels"]["exploration"]

    def _wait_exploration_available(self, page, timeout=30000):
        deadline = time.monotonic() + timeout / 1000
        while time.monotonic() < deadline:
            panel = self._exploration_panel(page)
            if panel and panel.get("available") is True:
                return panel
            page.wait_for_timeout(250)
        raise AssertionError("exploration panel never became available")

    def _wait_panel(self, page, name, predicate, timeout=30000):
        deadline = time.monotonic() + timeout / 1000
        while time.monotonic() < deadline:
            try:
                panel = store_state(page)["panels"].get(name)
                if panel and predicate(panel):
                    return panel
            except Exception:
                pass
            page.wait_for_timeout(250)
        raise AssertionError(
            "panel %s predicate never became true; state=%r" % (name, store_state(page))
        )

    def _reset_root(self, page):
        page.evaluate("document.getElementById('action-dock').focus()")
        page.evaluate("Elosern.explorationDock.resetToRoot()")
        page.wait_for_timeout(60)

    def _open_root(self, page, index):
        self._reset_root(page)
        for _ in range(index):
            _press(page, "ArrowDown")
        _press(page, "Enter")

    @covers_requirement("webclient-exploration-menu::explore-move-traverses-a-re-resolved-exit-through-the-shared-movement-path")
    def test_keyboard_move_charges_time_and_refreshes_map(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)
        map_before = store_state(page)["panels"]["local_map"]
        self.assertEqual(map_before["current_node"], "grid:capital_altoria:2:0")
        time_before = store_state(page)["serverTime"]

        self._open_root(page, 0)  # Move
        _press(page, "Enter")  # first exit
        self._wait_panel(
            page,
            "local_map",
            lambda p: p.get("available") is True and p["current_node"] != "grid:capital_altoria:2:0",
        )
        self.assertEqual(sent_action_count(page, "explore.move"), 1)
        after = store_state(page)
        self.assertNotEqual(after["panels"]["local_map"]["current_node"], "grid:capital_altoria:2:0")
        self.assertNotEqual(
            after["serverTime"],
            time_before,
            "movement must charge the world clock (design D3)",
        )

    @covers_requirement("webclient-exploration-menu::the-exploration-dock-is-keyboard-first-and-re-homes-the-service-submenus")
    def test_escape_from_character_panel_returns_keyboard_to_the_exploration_root(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)
        self.assertIn("character", store_state(page)["panels"])

        self._open_root(page, 3)  # 角色狀態
        self.assertEqual(
            page.evaluate("Elosern.explorationDock.isCharacterActive()"),
            True,
            "the character panel must own the action dock",
        )
        _press(page, "Escape")
        page.wait_for_timeout(120)
        self.assertEqual(
            page.evaluate("Elosern.explorationDock.isCharacterActive()"),
            False,
            "Escape must leave the character panel",
        )

        self._open_root(page, 0)  # Move
        _press(page, "Enter")  # first exit
        self._wait_panel(
            page,
            "local_map",
            lambda p: p.get("available") is True and p["current_node"] != "grid:capital_altoria:2:0",
        )
        self.assertEqual(
            sent_action_count(page, "explore.move"),
            1,
            "after Character -> Escape the exploration root must accept keyboard input",
        )

    @covers_requirement("webclient-exploration-menu::explore-look-reuses-the-command-appearance-path-and-preserves-onboarding-look-hooks")
    def test_look_at_room_preserves_the_onboarding_beat(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        self._open_root(page, 1)  # Look
        _press(page, "Enter")  # look at the room
        self.assertEqual(sent_action_count(page, "explore.look"), 1)
        page.wait_for_function(
            "(s) => document.querySelector('.elosern-narrative').innerText.indexOf(s) !== -1",
            arg="南門",
        )

    @covers_requirement("webclient-exploration-menu::explore-talk-scripted-invokes-the-deterministic-dialogue-api-with-keyword-buttons")
    def test_scripted_keyword_dialogue_completes(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        self._open_root(page, 2)  # Interact
        _press(page, "Enter")  # the guard (first present target, synced in the seed)
        _press(page, "Enter")  # 交談 (scripted affordance)
        _press(page, "Enter")  # first keyword
        self._wait_panel(
            page,
            "exploration",
            lambda p: p.get("available") is True,
        )
        sent = page.evaluate("window.__elosernSent || []")
        talk = [
            args[0]
            for cmd, args, _kw in sent
            if cmd == "ui_action" and args[0]["action_id"] == "explore.talk_scripted"
        ]
        self.assertEqual(len(talk), 1)
        self.assertIn("keyword_id", talk[0]["payload"])
        self.assertIn("npc_id", talk[0]["payload"])
        page.wait_for_function(
            "(s) => document.querySelector('.elosern-narrative').innerText.indexOf(s) !== -1",
            arg="冒險者公會",
        )

    @covers_requirement("webclient-exploration-menu::explore-talk-freeform-runs-the-guarded-dialogue-seam-through-an-injected-client")
    def test_freeform_dialogue_degrades_offline_through_the_drawer(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        self._open_root(page, 2)  # Interact
        _press(page, "ArrowDown")  # the bard (LLMNPC)
        _press(page, "Enter")
        _press(page, "ArrowDown")  # 自由交談 (after the scripted affordance)
        _press(page, "Enter")
        page.wait_for_function(
            "() => document.activeElement === document.getElementById('inputfield')"
        )
        page.keyboard.type("你好，詩人")
        page.keyboard.press("Enter")
        self._wait_panel(
            page,
            "exploration",
            lambda p: p.get("available") is True,
        )
        self.assertEqual(sent_action_count(page, "explore.talk_freeform"), 1)
        # Offline degrade reaches the authored greeting/silence.
        page.wait_for_function(
            "(s) => document.querySelector('.elosern-narrative').innerText.indexOf(s) !== -1",
            arg="歡迎來到冒險者公會",
        )

    @covers_requirement("webclient-exploration-menu::explore-engage-delegates-to-the-existing-engage-contract")
    def test_engage_transitions_to_combat(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        self._open_root(page, 2)  # Interact
        _press(page, "ArrowDown")  # the bard
        _press(page, "ArrowDown")  # the goblin
        _press(page, "Enter")
        _press(page, "Enter")  # 戰鬥 (engage)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            state = store_state(page)
            if state["mode"] == "combat":
                break
            page.wait_for_timeout(250)
        self.assertEqual(store_state(page)["mode"], "combat")
        self.assertEqual(sent_action_count(page, "explore.engage"), 1)
        self.assertEqual(
            page.evaluate("document.getElementById('action-dock').getAttribute('data-mode')"),
            "combat",
        )

    @covers_requirement("webclient-exploration-menu::explore-wait-obeys-the-shared-skip-safety-and-clock-api")
    def test_unsafe_skip_rejects_before_any_clock_advance(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        # At the South Gate a living goblin makes every skip unsafe; the
        # daypart boundary rejects before any clock advance.
        time_before = store_state(page)["serverTime"]
        self._open_root(page, 6)  # Wait/休息
        _press(page, "ArrowDown")  # 等待至黎明
        _press(page, "Enter")
        deadline = time.monotonic() + 20
        result = None
        while time.monotonic() < deadline:
            result = store_state(page)["lastActionResult"]
            if result and result["code"] == "unsafe_skip":
                break
            page.wait_for_timeout(250)
        self.assertEqual(result["code"], "unsafe_skip")
        self.assertEqual(sent_action_count(page, "explore.wait"), 1)
        self.assertEqual(store_state(page)["serverTime"], time_before)

        # The bounded custom-duration form is parsed server-side and rejected
        # by the same safety gate.
        self._open_root(page, 6)  # Wait/休息
        _press(page, "ArrowDown")  # 等待至黎明
        _press(page, "ArrowDown")  # 等待至正午
        _press(page, "ArrowDown")  # 等待至黃昏
        _press(page, "ArrowDown")  # 休息一段時間
        _press(page, "Enter")
        page.wait_for_function(
            "() => document.getElementById('exploration-rest-form') !== null"
        )
        page.keyboard.type("3600")
        page.keyboard.press("Enter")
        deadline = time.monotonic() + 20
        result = None
        while time.monotonic() < deadline:
            result = store_state(page)["lastActionResult"]
            if result and result["code"] == "unsafe_skip":
                break
            page.wait_for_timeout(250)
        self.assertEqual(result["code"], "unsafe_skip")
        self.assertEqual(sent_action_count(page, "explore.wait"), 2)
        self.assertEqual(store_state(page)["serverTime"], time_before)

    @covers_requirement("webclient-exploration-menu::the-exploration-dock-is-keyboard-first-and-re-homes-the-service-submenus")
    @covers_requirement("webclient-exploration-menu::explore-wait-obeys-the-shared-skip-safety-and-clock-api")
    def test_safe_wait_until_dawn_advances_the_clock(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        # Move away from the goblin, then wait until dawn succeeds.
        self._open_root(page, 0)  # Move
        _press(page, "Enter")  # first exit
        self._wait_panel(
            page,
            "local_map",
            lambda p: p.get("available") is True and p["current_node"] != "grid:capital_altoria:2:0",
        )
        time_before = store_state(page)["serverTime"]
        self._open_root(page, 6)  # Wait/休息
        _press(page, "ArrowDown")  # 等待至黎明
        _press(page, "Enter")
        deadline = time.monotonic() + 20
        ok = None
        while time.monotonic() < deadline:
            result = store_state(page)["lastActionResult"]
            if result and result["code"] == "skipped":
                ok = result
                break
            page.wait_for_timeout(250)
        self.assertIsNotNone(ok, "a safe wait must succeed")
        time_after = store_state(page)["serverTime"]
        self.assertNotEqual(
            (time_after["hour"], time_after["minute"]),
            (time_before["hour"], time_before["minute"]),
            "a successful wait must advance the world clock",
        )

    @covers_requirement("webclient-exploration-menu::exploration-actions-reject-stale-duplicate-and-tampered-input-without-mutation")
    def test_stale_and_tampered_submissions_do_nothing(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)
        map_before = store_state(page)["panels"]["local_map"]["current_node"]

        # A raw ui_action with a stale base_revision returns the dispatcher's
        # stale outcome and performs no traversal.
        page.evaluate(
            """() => {
              const s = Elosern.StateController.getState();
              const moveRow = s.panels.exploration.move[0];
              Evennia.msg('ui_action', [{
                protocol_version: 1,
                presentation_epoch: s.activeEpoch,
                request_id: 'stale-move-1',
                base_revision: 0,
                action_id: 'explore.move',
                payload: { exit_ref: moveRow.exit_ref, current_node: s.panels.local_map.current_node },
              }], {});
            }"""
        )
        deadline = time.monotonic() + 20
        result = None
        while time.monotonic() < deadline:
            result = store_state(page)["lastActionResult"]
            if result and result["requestId"] == "stale-move-1":
                break
            page.wait_for_timeout(250)
        self.assertEqual(result["outcome"], "stale")
        self.assertEqual(
            store_state(page)["panels"]["local_map"]["current_node"],
            map_before,
            "a stale move must not relocate the actor",
        )

        # A tampered exit_ref fails commit-time revalidation.
        page.evaluate(
            """() => {
              const s = Elosern.StateController.getState();
              Evennia.msg('ui_action', [{
                protocol_version: 1,
                presentation_epoch: s.activeEpoch,
                request_id: 'tampered-move-1',
                base_revision: s.revision,
                action_id: 'explore.move',
                payload: { exit_ref: '999999', current_node: s.panels.local_map.current_node },
              }], {});
            }"""
        )
        deadline = time.monotonic() + 20
        result = None
        while time.monotonic() < deadline:
            result = store_state(page)["lastActionResult"]
            if result and result["requestId"] == "tampered-move-1":
                break
            page.wait_for_timeout(250)
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "no_exit")
        self.assertEqual(
            store_state(page)["panels"]["local_map"]["current_node"],
            map_before,
        )

    @covers_requirement("webclient-exploration-menu::exploration-browser-acceptance-is-keyboard-only-and-desktop-bounded")
    def test_no_take_or_drop_control_is_rendered(self):
        page = self.logged_in_page((1280, 720))
        install_outbound_recorder(page)
        self._wait_exploration_available(page)
        # The exploration dock renders no take/drop or generic object-mutation
        # control anywhere in the surface.
        body_text = page.locator("#action-dock").inner_text()
        self.assertNotIn("拾取", body_text)
        self.assertNotIn("丟棄", body_text)
        self.assertNotIn("explore.take", body_text)
        self.assertNotIn("explore.drop", body_text)
        sent = page.evaluate("window.__elosernSent || []")
        for cmdname, args, _kwargs in sent:
            if cmdname != "ui_action" or not args:
                continue
            self.assertFalse(
                args[0]["action_id"].startswith("explore.take"),
                "explore.take must never be submitted",
            )
            self.assertFalse(
                args[0]["action_id"].startswith("explore.drop"),
                "explore.drop must never be submitted",
            )

    @covers_requirement("webclient-exploration-menu::exploration-actions-reject-stale-duplicate-and-tampered-input-without-mutation")
    def test_reconnect_rebuilds_exploration_without_replay(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        page.evaluate(
            "() => { if (window.__elosernWs) window.__elosernWs.close(4001); }"
        )
        page.wait_for_function(
            "() => { const s = Elosern.StateController.getState(); return !s.connected; }"
        )
        page.evaluate("Evennia.connect()")
        self._wait_exploration_available(page)
        # The rebuilt dock derives from server-persisted state and no dialogue
        # or mutation is automatically replayed.
        self.assertEqual(sent_action_count(page, "explore.move"), 0)
        self.assertEqual(sent_action_count(page, "explore.talk_freeform"), 0)
        self.assertEqual(sent_action_count(page, "explore.talk_scripted"), 0)


if __name__ == "__main__":
    import unittest

    unittest.main()
