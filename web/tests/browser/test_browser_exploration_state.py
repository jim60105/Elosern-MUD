"""Keyboard-only exploration browser acceptance (webclient-exploration-menu 4.2-4.6): focus and stack-loss resilience across committed re-resolution, the suggestions frame, and reconnect without replay.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement
from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    focus_action_dock,
    fixture_home_node_id,
    install_outbound_recorder,
    sent_action_count,
    outbound_messages,
    store_state,
    wait_for_store_state,
)
from .harness import ManagedServer, ManagedServerTearDownMixin
from . import fixtures


def _press(page, key, wait_ms=80):
    page.keyboard.press(key)
    page.wait_for_timeout(wait_ms)


class ExplorationBrowserTest(ManagedServerTearDownMixin, BrowserAcceptanceTest):
    """Boots one dedicated isolated server per test with the exploration fixture."""
    @classmethod
    def setUpClass(cls) -> None:
        pass

    def setUp(self) -> None:
        runtime = fixtures.create_runtime()
        runtime.env["ELOSERN_BROWSER_EXPLORATION"] = "1"
        # Boot mode: SHIPPED catalogs (explicit override of the harness
        # synthetic default, per the creation/action-feedback precedent).
        # These journeys assert shipped fixture identity end to end and were
        # never migrated to kit seams.
        runtime.env["ELOSERN_BROWSER_SYNTH_CATALOGS"] = "0"

        self.server = ManagedServer(runtime=runtime)
        self.server.start()
        self.base_url = f"http://127.0.0.1:{self.server.runtime.http_port}"
        self.webclient_url = self.server.runtime.webclient_url
        super().setUp()

    def _live_exploration_panel(self, page):
        # The panels mapping can be observed mid-snapshot-adoption without the
        # exploration key; callers poll, so a missing panel reads as None.
        return store_state(page)["panels"].get("exploration")

    def _wait_exploration_available(self, page, timeout=30000):
        def _exploration_available(state: dict) -> bool:
            panel = (state.get("panels") or {}).get("exploration") or {}
            return panel.get("available") is True

        wait_for_store_state(page, _exploration_available, timeout=timeout)

    def _wait_panel(self, page, name, predicate, timeout=30000):
        def _panel_ready(state: dict) -> bool:
            panel = (state.get("panels") or {}).get(name)
            return panel is not None and predicate(panel)

        wait_for_store_state(page, _panel_ready, timeout=timeout)

    def _reset_root(self, page):
        focus_action_dock(page)
        page.evaluate("window.__elosernBridge.store.resetFramesToRoot()")
        page.wait_for_timeout(60)

    def _open_root(self, page, index):
        self._reset_root(page)
        # The exploration root is a single seven-column row (mockup grid), so
        # horizontal arrows move across it; submenus are 2-column grids.
        for _ in range(index):
            _press(page, "ArrowRight")
        _press(page, "Enter")

    @covers_requirement("webclient-exploration-menu::the-exploration-dock-is-keyboard-first-and-re-homes-the-service-submenus")
    def test_escape_from_character_panel_returns_keyboard_to_the_exploration_root(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)
        self.assertIn("character", store_state(page)["panels"])

        # The desktop redesign re-homed the character surface into the top
        # navigation (webclient-desktop-shell, acd3790: the dock root is the
        # capability-driven [move, look, interact, wait, suggestions];
        # 角色狀態 opens from the DesktopNavigation entry — the nav click
        # routes the same store confirm the dock row carried).
        page.locator('.desktop-navigation button', has_text="角色狀態").click()
        self.assertEqual(
            page.evaluate("(() => { const s = window.__elosernBridge.store.view; return s && s.activeSubDock; })()"),
            "character",
            "the character panel must own the action dock",
        )
        _press(page, "Escape")
        page.wait_for_timeout(120)
        self.assertEqual(
            page.evaluate("(() => { const s = window.__elosernBridge.store.view; return s && s.activeSubDock; })()"),
            None,
            "Escape must leave the character panel",
        )

        self._open_root(page, 0)  # Move
        _press(page, "Enter")  # first exit
        self._wait_panel(
            page,
            "local_map",
            lambda p: p.get("available") is True and p["current_node"] != fixture_home_node_id(),
        )
        self.assertEqual(
            sent_action_count(page, "explore.move"),
            1,
            "after Character -> Escape the exploration root must accept keyboard input",
        )

    # --- declarative-frame-stack browser verification (task 5.1) -----------
    #
    # These methods verify the shipped stack (router + store + dock DOM)
    # against COMMITTED state the live fixture cannot arrange: a fabricated
    # `ui_update` through the bridge's `store.receive` is the same reducer
    # entry the real transport feeds (the options-surface file pioneered the
    # seam), so the stack settles exactly as it does after a server push —
    # identity loss, panel withdrawal, and suggestions status flips included.

    def _inject_panels(self, page, panels: dict) -> dict:
        """Commit one schema-valid ``ui_update`` for ``panels`` at the
        current revision + 1. The envelope is assembled IN-PAGE from the
        fresh view so no real push can slip a revision between read and
        receive; the injected revision then back-stops the next real push
        (``not_newer``) until the server's revision passes it."""
        return page.evaluate(
            """(panels) => {
              const s = window.__elosernBridge.store.view;
              const envelope = {
                protocol_version: 1,
                presentation_epoch: s.epoch,
                revision: s.revision + 1,
                mode: s.mode,
                layout_version: s.layoutVersion ?? 1,
                panels,
                server_time: s.serverTime,
              };
              return window.__elosernBridge.store.receive(
                s.generation, 'ui_update', [envelope], {});
            }""",
            panels,
        )

    @staticmethod
    def _fabricated_exploration_panel(*, move=(), interact=()) -> dict:
        """A schema-valid available exploration panel carrying exactly the
        named rows — the fabricated room a real commit would produce."""
        return {
            "schema_version": 2,
            "available": True,
            "kind": "exploration",
            "move": list(move),
            "look": {
                "room": {"identity": 94001, "display_name": "巡邏室", "room": True},
                "entities": [],
                "objects": [],
            },
            "interact": list(interact),
            "character": {"available": True},
            "quests": {"available": False},
            "inventory": {"available": False},
        }

    @staticmethod
    def _move_row(exit_ref: str, label: str) -> dict:
        return {
            "exit_ref": exit_ref,
            "label": label,
            "destination": "grid:altoria:3:3",
            "enabled": True,
            "disabled_reason": None,
        }

    @staticmethod
    def _target(identity: int, name: str) -> dict:
        return {
            "identity": identity,
            "display_name": name,
            "portrait_ref": None,
            "affordances": [
                {
                    "kind": "action",
                    "action_id": "explore.engage",
                    "label": "戰鬥",
                    "enabled": True,
                    "disabled_reason": None,
                }
            ],
        }

    def _depth(self, page) -> int:
        return page.evaluate("() => window.__elosernBridge.router.depth()")

    def _pane_keys(self, page) -> list[str]:
        """Every rendered row identity inside the dock (tab-bar tabs and
        pane rows share the `data-item-key` seam; the legacy suggestion
        cards render without one)."""
        return page.evaluate(
            "() => Array.from("
            "document.querySelectorAll('#action-dock [data-item-key]'))"
            ".map((el) => el.getAttribute('data-item-key'))"
        )

    @covers_requirement("webclient-frame-resolution::focus-tracks-the-item-key-across-re-resolution")
    def test_focus_follows_the_item_key_across_committed_re_resolution(self):
        """Focus tracks the item KEY (webclient-declarative-frame-stack):
        with the 移動 frame open, a commit that REORDERS the exits keeps the
        focus on the same key at its new index, and a commit that drops the
        focused exit lands focus on a surviving row — never on the frozen
        copy's old row. Activation then submits the NEW committed payload."""
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        accepted = self._inject_panels(page, {"exploration": self._fabricated_exploration_panel(
            move=[self._move_row("ex-a", "北門"), self._move_row("ex-b", "南門"),
                  self._move_row("ex-c", "東門")])})
        self.assertTrue(accepted["accepted"], accepted)

        self._open_root(page, 0)  # 移動 frame opens at depth 2.
        self.assertEqual(self._depth(page), 2)
        self.assertTrue(
            page.evaluate("() => window.__elosernBridge.store.focusItemByKey('exit-ex-b')")
        )
        self.assertEqual(store_state(page)["focus"]["key"], "exit-ex-b")

        # Reordered + extended commit: the same key survives at a new index.
        accepted = self._inject_panels(page, {"exploration": self._fabricated_exploration_panel(
            move=[self._move_row("ex-c", "東門"), self._move_row("ex-b", "南門"),
                  self._move_row("ex-a", "北門"), self._move_row("ex-d", "西門")])})
        self.assertTrue(accepted["accepted"], accepted)
        self.assertEqual(
            store_state(page)["focus"]["key"],
            "exit-ex-b",
            "the same-key focus did not survive the re-resolution",
        )

        # The focused key vanishes: focus lands on a SURVIVING row (the
        # nearest-row rule itself is pinned at store level; here it must land
        # somewhere real, never on the vanished key).
        accepted = self._inject_panels(page, {"exploration": self._fabricated_exploration_panel(
            move=[self._move_row("ex-c", "東門"), self._move_row("ex-d", "西門")])})
        self.assertTrue(accepted["accepted"], accepted)
        focused = store_state(page)["focus"]["key"]
        self.assertIn(
            focused,
            ("exit-ex-c", "exit-ex-d"),
            "the lost-key fallback did not land on a surviving row",
        )
        self.assertEqual(self._depth(page), 2, "the move frame did not stay open")

        # Activating the focused row submits the NEW committed row's payload.
        self.assertTrue(
            page.evaluate("() => window.__elosernBridge.store.focusConfirm('keyboard')")
        )
        # The proof is the OUTBOUND envelope only: the fabricated exit_ref
        # cannot be accepted by the server (its own result/lock behaviour is
        # covered elsewhere), so the recorder — written synchronously at
        # dispatch — is the assertion source, not the in-flight gate.
        page.wait_for_function(
            "() => window.__elosernSent.filter((m) => m[0] === 'ui_action'"
            " && m[1][0] && m[1][0].action_id === 'explore.move').length === 1",
            timeout=10000,
        )
        moves = [
            args[0]
            for cmdname, args, _kw in outbound_messages(page)
            if cmdname == "ui_action" and args and args[0].get("action_id") == "explore.move"
        ]
        self.assertEqual(len(moves), 1, "the activation dispatched exactly one move")
        self.assertEqual(
            (moves[0].get("payload") or {}).get("exit_ref"),
            focused[len("exit-"):],
            "the activation submitted a payload from a superseded row",
        )

    @covers_requirement("webclient-frame-resolution::unresolvable-frames-pop-one-level-only-the-root-frame-renders-a-degraded-reason-row")
    def test_identity_loss_pops_one_level_and_restores_opener_focus(self):
        """A target frame whose identity vanishes from the committed panel
        pops EXACTLY one level (never cascades past a surviving parent) and
        restores focus toward the vanished target's former row."""
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)
        accepted = self._inject_panels(page, {"exploration": self._fabricated_exploration_panel(
            interact=[self._target(9001, "哨衛士兵"), self._target(9002, "吟遊詩人")])})
        self.assertTrue(accepted["accepted"], accepted)

        self._open_root(page, 2)  # 互動 frame (depth 2)
        self.assertTrue(
            page.evaluate("() => window.__elosernBridge.store.focusItemByKey('target-9001')")
        )
        page.evaluate("() => window.__elosernBridge.store.focusConfirm('keyboard')")
        self.assertEqual(self._depth(page), 3, "the target frame did not open")
        self.assertEqual(
            page.evaluate("() => window.__elosernBridge.router.currentDescriptor()"),
            {"source": "exploration.target", "params": {"identity": 9001}},
        )

        # The committed panel no longer lists 9001: the target frame
        # degrades at the next access and pops exactly one level.
        accepted = self._inject_panels(page, {"exploration": self._fabricated_exploration_panel(
            interact=[self._target(9002, "吟遊詩人")])})
        self.assertTrue(accepted["accepted"], accepted)
        self.assertEqual(self._depth(page), 2)
        self.assertEqual(
            page.evaluate("() => window.__elosernBridge.router.currentDescriptor()"),
            {"source": "exploration.interact", "params": {}},
        )
        # Opener focus is restored toward the vanished row: the only
        # surviving target row carries the keyboard focus — committed view
        # AND the rendered pane's aria-selected cell.
        self.assertEqual(store_state(page)["focus"]["key"], "target-9002")
        self.assertEqual(
            page.locator(
                '#action-dock [data-item-key="target-9002"][aria-selected="true"]'
            ).count(),
            1,
            "the restored opener focus did not reach the rendered pane",
        )

    @covers_requirement("webclient-frame-resolution::unresolvable-frames-pop-one-level-only-the-root-frame-renders-a-degraded-reason-row")
    def test_whole_stack_loss_cascades_to_the_degraded_root_and_recovers(self):
        """A panel withdrawal makes EVERY open exploration frame unresolvable
        at once: the pop cascades in ONE access down to the root frame, the
        root degrades into the single disabled marker row with the
        server-authored reason verbatim, activating it submits nothing, and a
        returning panel re-resolves the SAME root frame back to content."""
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)
        # Pin the suggestions status to `generating` so the legacy section
        # renders no keyed rows and the pane-key assertions stay exact.
        pinned_context = {
            "context_actions": {
                "schema_version": 5,
                "available": True,
                "kind": "exploration",
                "affordances": [],
                "suggestions": {"status": "generating"},
            },
        }
        accepted = self._inject_panels(page, {
            "exploration": self._fabricated_exploration_panel(interact=[self._target(9001, "哨衛士兵")]),
            **pinned_context,
        })
        self.assertTrue(accepted["accepted"], accepted)

        self._open_root(page, 2)  # 互動 -> 對象 (depth 3)
        self.assertTrue(
            page.evaluate("() => window.__elosernBridge.store.focusItemByKey('target-9001')")
        )
        page.evaluate("() => window.__elosernBridge.store.focusConfirm('keyboard')")
        self.assertEqual(self._depth(page), 3)

        withdrawn = "這片區域暫時無法操作"
        accepted = self._inject_panels(page, {
            "exploration": {
                "schema_version": 2,
                "available": False,
                "reason": {"code": "exploration.unavailable", "message": withdrawn},
            },
            **pinned_context,
        })
        self.assertTrue(accepted["accepted"], accepted)

        # ONE access settles the WHOLE cascade: depth 1, degraded root.
        self.assertEqual(self._depth(page), 1)
        self.assertEqual(
            store_state(page)["degradedRoot"],
            {
                "key": "degraded-root",
                "reason": withdrawn,
                "fallback": "畫面狀態已更新，請返回上層",
            },
        )
        # The pane presents exactly the single disabled marker row with the
        # server message verbatim — no stale submenu row survives.
        self.assertEqual(self._pane_keys(page), ["degraded-root"])
        self.assertIn(
            withdrawn,
            page.locator('#action-dock [data-item-key="degraded-root"]').inner_text(),
        )
        # It submits nothing.
        sent_before = sent_action_count(page)
        self.assertFalse(
            page.evaluate("() => window.__elosernBridge.store.focusConfirm('keyboard')")
        )
        self.assertEqual(sent_action_count(page), sent_before)

        # The panel returns: the SAME root frame re-resolves to content and
        # the degraded presentation clears with the commit.
        accepted = self._inject_panels(page, {
            "exploration": self._fabricated_exploration_panel(move=[self._move_row("ex-a", "北門")]),
            **pinned_context,
        })
        self.assertTrue(accepted["accepted"], accepted)
        self.assertIsNone(store_state(page)["degradedRoot"])
        root_keys = self._pane_keys(page)
        # The desktop redesign (webclient-exploration-menu, synced
        # projection scenario) omits the character, quests, and inventory
        # entries the top navigation owns: the recovered root's dock
        # projection is the capability-driven [move, look, interact, wait,
        # suggestions].
        self.assertTrue(
            {"move", "look", "interact", "wait", "suggestions"} <= set(root_keys),
            f"the recovered root lost its entries: {root_keys}",
        )

    @covers_requirement("webclient-frame-resolution::suggestions-frames-are-status-driven-generating-never-pops-unavailable-exits-to-the-root")
    def test_suggestions_frame_is_status_driven(self):
        """The status split: `generating`/`degraded` commits keep the open 建議
        frame and its content follows the commit (no pop, no timer);
        `unavailable` — the options-surface no-pane rule — exits the WHOLE
        stack to the exploration root WITHOUT any reason row."""
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        def context_actions(suggestions: dict) -> dict:
            return {
                "context_actions": {
                    "schema_version": 5,
                    "available": True,
                    "kind": "exploration",
                    "affordances": [],
                    "suggestions": suggestions,
                },
            }

        # A known `generating` envelope, then the 建議 tab opens the frame.
        accepted = self._inject_panels(page, context_actions({"status": "generating"}))
        self.assertTrue(accepted["accepted"], accepted)
        self.assertIn("suggestions", self._pane_keys(page))
        page.locator('#action-dock [data-item-key="suggestions"]').click()
        self.assertEqual(self._depth(page), 2)
        self.assertEqual(
            page.evaluate("() => window.__elosernBridge.router.currentDescriptor()"),
            {"source": "exploration.suggestions", "params": {}},
        )
        self.assertEqual(
            page.locator('#action-dock [data-item-key="suggestions-generating"]').count(),
            1,
            "the generating muted row did not render",
        )

        # A fresh `generating` commit: the frame STAYS (generating never
        # pops), the muted row still carries the focus.
        accepted = self._inject_panels(page, context_actions({"status": "generating"}))
        self.assertTrue(accepted["accepted"], accepted)
        self.assertEqual(self._depth(page), 2)
        self.assertEqual(store_state(page)["focus"]["key"], "suggestions-generating")

        # `degraded` with zero cards is still resolvable: the frame stays and
        # its CONTENT follows the commit (the dismiss control appears).
        accepted = self._inject_panels(
            page, context_actions({"status": "degraded", "cards": []})
        )
        self.assertTrue(accepted["accepted"], accepted)
        self.assertEqual(self._depth(page), 2)
        self.assertIn(
            "action-options.dismiss",
            self._pane_keys(page),
            "the frame content did not follow the committed status change",
        )

        # `unavailable`: no pane may exist — the whole stack exits to the
        # root, and NO degraded marker/reason row is rendered.
        accepted = self._inject_panels(page, context_actions({"status": "unavailable"}))
        self.assertTrue(accepted["accepted"], accepted)
        self.assertEqual(self._depth(page), 1)
        state = store_state(page)
        self.assertIsNone(state["degradedRoot"], "the exit rendered a reason row")
        self.assertNotIn(
            "suggestions",
            self._pane_keys(page),
            "the unavailable root still lists the 建議 entry",
        )

    @covers_requirement("webclient-exploration-menu::exploration-actions-reject-stale-duplicate-and-tampered-input-without-mutation")
    def test_reconnect_rebuilds_exploration_without_replay(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        page.evaluate(
            "() => { if (window.__elosernWs) window.__elosernWs.close(4001); }"
        )
        wait_for_store_state(
            page,
            lambda s: not s.get("connected"),
        )
        page.evaluate("Evennia.connect()")
        self._wait_exploration_available(page)
        # The rebuilt dock derives from server-persisted state and no dialogue
        # or mutation is automatically replayed.
        self.assertEqual(sent_action_count(page, "explore.move"), 0)
        self.assertEqual(sent_action_count(page, "explore.talk_freeform"), 0)
        self.assertEqual(sent_action_count(page, "explore.talk_scripted"), 0)
