"""Keyboard-only exploration browser acceptance (webclient-exploration-menu 4.2-4.6): navigation tile geometry, pointer back-cell, and escape/back navigation through the exploration dock.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement
from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    activate_overview_chip,
    fixture_home_node_id,
    focus_action_dock,
    install_outbound_recorder,
    outbound_messages,
    sent_action_count,
    store_state,
    wait_for_store_state,
)
from .harness import ManagedServer, ManagedServerTearDownMixin
from . import fixtures


def _press(page, key, wait_ms=80):
    page.keyboard.press(key)
    page.wait_for_timeout(wait_ms)


def _connected_active(state: dict) -> bool:
    """Gate on the client being connected and in the active presentation phase."""
    return bool(state.get("connected")) and state.get("phase") == "active"


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
            "schema_version": 3,
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

    @covers_requirement("webclient-exploration-menu::the-keyboard-first-exploration-dock-roots-at-the-scene-overview-and-opens-dialogue-directly")
    def test_pointer_back_cell_returns_to_the_root_without_an_action(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        # Pointer: open a person chip's verb popover, then click its final
        # back cell (webclient-scene-overview-swap: the popover is the
        # overview's one child frame; the retired Look submenu is gone).
        panel = self._live_exploration_panel(page)
        targets = panel.get("interact") or []
        self.assertTrue(targets, "the fixture room must offer an interact target")
        chip_key = "target-%s" % targets[0]["identity"]
        wait_for_store_state(
            page,
            lambda s: ((s.get("panels") or {}).get("exploration") or {}).get("available") is True,
            dom_readiness={
                "selector": '#action-dock [data-item-key="%s"]' % chip_key,
                "predicate": (
                    "() => !!document.querySelector("
                    "'#action-dock [data-item-key=\"%s\"]')" % chip_key
                ),
                "description": "the person chip rendered in the exploration dock",
            },
        )
        page.locator('#action-dock [data-item-key="%s"]' % chip_key).click()
        wait_for_store_state(
            page,
            lambda s: s.get("dockSource") == "exploration.target",
            dom_readiness={
                "selector": '[data-testid="verb-popover"] [data-item-key="back"]',
                "predicate": (
                    "() => !!document.querySelector("
                    "'[data-testid=\"verb-popover\"] [data-item-key=\"back\"]')"
                ),
                "description": "the popover's back cell rendered",
            },
        )
        page.locator('[data-testid="verb-popover"] [data-item-key="back"]').click()
        wait_for_store_state(
            page,
            lambda s: s.get("dockSource") == "exploration.root",
            dom_readiness={
                "selector": "#action-dock [data-testid=\"scene-overview\"]",
                "predicate": (
                    "() => !!document.querySelector("
                    "'#action-dock [data-testid=\"scene-overview\"]')"
                ),
                "description": "the scene overview rendered in the dock",
            },
        )
        # The overview's chips render again, no ui_action was sent, and the
        # stack is back at the root frame.
        keys = page.evaluate(
            "() => Array.from(document.querySelectorAll("
            "'#action-dock [data-testid=\"scene-overview\"] [data-item-key]'))"
            ".map((el) => el.getAttribute('data-item-key'))"
        )
        self.assertIn(chip_key, keys, "the overview renders the person chip again")
        self.assertIn("look-room", keys, "the overview renders its footer again")
        self.assertIn("wait", keys, "the overview renders its footer again")
        for gone in ("move", "look", "interact"):
            self.assertNotIn(gone, keys, "the retired tab-root entry must not render")
        self.assertEqual(sent_action_count(page), 0)
        self.assertEqual(
            page.evaluate("window.__elosernBridge.router.depth()"),
            1,
            "the back cell pops exactly one router frame",
        )

    @covers_requirement("webclient-exploration-menu::the-keyboard-first-exploration-dock-roots-at-the-scene-overview-and-opens-dialogue-directly")
    def test_escape_at_intermediate_depth_keeps_cells_matched_to_the_frame(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        # The overview's host chip -> the verb popover: two levels deep
        # (webclient-scene-overview-swap). 交談 dispatches explore.talk_open
        # from the popover itself, so the popover is the deepest frame.
        panel = self._live_exploration_panel(page)
        host_identity = panel["interact"][0]["identity"]
        activate_overview_chip(page, "target-%s" % host_identity)
        self.assertEqual(page.evaluate("window.__elosernBridge.router.depth()"), 2)
        # H3 (design D2): at depth >= 2 the dock renders both the root tab
        # bar (8 root tabs) and the scrolling pane (the active frame's rows).
        # The test's cell assertions target the pane's rows only.
        target_keys = page.evaluate(
            "() => Array.from(document.querySelectorAll("
            "'[data-testid=\"verb-popover\"] [data-item-key]'))"
            ".map((el) => el.getAttribute('data-item-key'))"
        )
        # The host's verb popover: the 交談 conversation entry plus 查看 and
        # the final back cell (the exploration fixture carries no guild
        # navigate entry). The card renders in the dock's overlay layer, over
        # the inert overview (webclient-scene-overview-swap).
        self.assertEqual(
            target_keys,
            ["talk-open", "look-target", "back"],
            "the popover's cells must render at depth 2",
        )
        self.assertEqual(
            page.evaluate(
                "window.__elosernBridge.router.currentItem() && "
                "window.__elosernBridge.router.currentItem().key"
            ),
            "talk-open",
        )
        _press(page, "Escape")  # back to the scene overview
        page.wait_for_timeout(80)
        self.assertEqual(page.evaluate("window.__elosernBridge.router.depth()"), 1)
        root_keys = page.evaluate(
            "() => Array.from(document.querySelectorAll("
            "'#action-dock [data-testid=\"scene-overview\"] [data-item-key]'))"
            ".map((el) => el.getAttribute('data-item-key'))"
        )
        expected_root = [
            "exit-" + str(row["exit_ref"]) for row in panel.get("move") or []
        ]
        expected_root += [
            "target-" + str(target["identity"]) for target in panel["interact"]
        ]
        expected_root += ["look-room", "wait"]
        # The footer's 建議 chip renders whenever the committed envelope's
        # status is not `unavailable`.
        suggestions = (
            ((store_state(page).get("panels") or {}).get("context_actions") or {})
            .get("suggestions")
            or {}
        )
        if suggestions.get("status") not in (None, "unavailable"):
            expected_root.append("suggestions")
        self.assertEqual(
            root_keys,
            expected_root,
            "the overview's chips must render after the second Escape",
        )
        self.assertEqual(
            page.evaluate(
                "window.__elosernBridge.router.currentItem() && "
                "window.__elosernBridge.router.currentItem().key"
            ),
            "target-" + str(host_identity),
        )
        self.assertEqual(sent_action_count(page), 0)

    @covers_requirement("webclient-exploration-menu::the-keyboard-first-exploration-dock-roots-at-the-scene-overview-and-opens-dialogue-directly")
    def test_escape_from_quests_drawer_leaves_root_clean(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        focused_before = page.evaluate(
            "window.__elosernBridge.router.currentItem() && "
            "window.__elosernBridge.router.currentItem().key"
        )

        # Top-navigation 任務 click opens the quest drawer frameless
        page.locator('.desktop-navigation button', has_text="任務").click()
        wait_for_store_state(page, lambda s: s.get("hudDrawer") == "quest")
        self.assertEqual(
            page.evaluate("(() => { const s = window.__elosernBridge.store.view; return s && s.activeSubDock; })()"),
            None,
            "activeSubDock must stay null",
        )
        self.assertEqual(
            page.evaluate("() => window.__elosernBridge.router.depth()"),
            1,
            "router depth must remain 1",
        )
        _press(page, "Escape")
        wait_for_store_state(page, lambda s: s.get("hudDrawer") is None)
        self.assertEqual(sent_action_count(page), 0)

        keys = page.evaluate(
            "() => Array.from(document.querySelectorAll("
            "'#action-dock [data-testid=\"scene-overview\"] [data-item-key]'))"
            ".map((el) => el.getAttribute('data-item-key'))"
        )
        # The exploration root is the scene overview (webclient-scene-
        # overview-swap): the exits lead its reading order, then the people,
        # the objects, and the footer.
        self.assertIn("look-room", keys, "the overview's footer renders after Escape from Quests")
        self.assertIn("wait", keys, "the overview's footer renders after Escape from Quests")
        for gone in ("move", "look", "interact"):
            self.assertNotIn(gone, keys, "the retired tab-root entry must not render")
        self.assertEqual(
            page.evaluate(
                "window.__elosernBridge.router.currentItem() && "
                "window.__elosernBridge.router.currentItem().key"
            ),
            focused_before,
            "router's focused item must be unchanged from before the open",
        )

    @covers_requirement(
        "webclient-exploration-menu::the-keyboard-first-exploration-dock-roots-at-the-scene-overview-and-opens-dialogue-directly"
    )
    def test_keyboard_only_journey_walks_the_overview(self):
        """A pure arrows-and-Enter journey at 1920x1080: the overview's chips
        are reachable, an exit chip moves, a person chip opens the verb
        popover (Escape returns with that chip focused), and a move from the
        minimap returns the dock to the new room's overview
        (webclient-scene-overview-swap, design D2/D6)."""
        page = self.logged_in_page((1920, 1080))
        install_outbound_recorder(page)
        self._wait_exploration_available(page)
        focus_action_dock(page)
        page.evaluate("window.__elosernBridge.store.resetFramesToRoot()")
        page.wait_for_timeout(60)

        panel = self._live_exploration_panel(page)
        exits = panel.get("move") or []
        self.assertTrue(exits, "the fixture room must offer exits")
        targets = panel.get("interact") or []
        self.assertTrue(targets, "the fixture room must offer an interact target")
        person = targets[0]

        # Arrows reach a person chip; Enter opens the popover; Escape returns
        # with that chip focused.
        activate_overview_chip(page, "target-%s" % person["identity"])
        page.wait_for_selector('[data-testid="verb-popover"]', timeout=15000)
        self.assertEqual(
            store_state(page)["dockSource"],
            "exploration.target",
            "the person chip must open the verb popover",
        )
        _press(page, "Escape")
        wait_for_store_state(page, lambda s: s.get("dockSource") == "exploration.root")
        self.assertEqual(
            store_state(page)["focus"]["key"],
            "target-%s" % person["identity"],
            "Escape must restore the chip that opened the popover",
        )
        self.assertEqual(page.locator('[data-testid="verb-popover"]').count(), 0)

        # Arrows reach an exit chip — the 出口 row leads the reading order, so
        # walking left from the restored person chip wraps onto an exit — and
        # Enter submits explore.move for it.
        for _ in range(12):
            if str(store_state(page)["focus"]["key"]).startswith("exit-"):
                break
            _press(page, "ArrowLeft")
        focused = store_state(page)["focus"]["key"]
        self.assertTrue(
            str(focused).startswith("exit-"),
            "arrows must reach an exit chip (focus was %r)" % (focused,),
        )
        _press(page, "Enter")
        self._wait_panel(
            page,
            "local_map",
            lambda p: p.get("available") is True and p["current_node"] != fixture_home_node_id(),
        )
        self.assertEqual(sent_action_count(page, "explore.move"), 1)
        wait_for_store_state(page, _connected_active)
        page.wait_for_timeout(120)

        # The new room's overview is the dock's ONLY frame: the move reset the
        # stack to the committed root, and nothing of the previous room stays
        # activatable.
        self.assertEqual(page.evaluate("() => window.__elosernBridge.router.depth()"), 1)
        self.assertEqual(
            store_state(page)["dockSource"],
            "exploration.root",
            "the dock must be back at the overview after a move",
        )
        self.assertEqual(page.locator('[data-testid="verb-popover"]').count(), 0)

        # Opening 等待／休息 and then moving by activating a minimap node
        # returns the dock to the overview (design D2: a minimap move
        # bypasses the dock's own push sites).
        activate_overview_chip(page, "wait")
        page.wait_for_selector(".waiting-screen", timeout=15000)
        self.assertEqual(page.evaluate("() => window.__elosernBridge.router.depth()"), 2)

        # The minimap's own node control is the move path that bypasses the
        # dock entirely: a click on it submits the same explore.move the
        # overview's exit chip would.
        node_id = page.evaluate(
            """() => {
              const lm = window.__elosernBridge.store.view.localMapModel;
              if (!lm || !Array.isArray(lm.nodes)) return null;
              const n = lm.nodes.find((n) => n.action && n.action.kind === "move");
              return n ? n.id : null;
            }"""
        )
        self.assertIsNotNone(node_id, "the minimap must offer a move-capable node")
        node_control = page.locator(
            '[data-testid="local-map"] [data-node="%s"]' % node_id
        )
        self.assertGreater(node_control.count(), 0, "the minimap node must render")
        node_control.first.click()
        wait_for_store_state(
            page,
            lambda s: (s.get("dockDepth") or 0) == 1 and s.get("dockSource") == "exploration.root",
            timeout=30000,
        )
        self.assertEqual(page.locator(".waiting-screen").count(), 0)
        self.assertEqual(page.locator('[data-testid="scene-overview"]').count(), 1)
