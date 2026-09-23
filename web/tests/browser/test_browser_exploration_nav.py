"""Keyboard-only exploration browser acceptance (webclient-exploration-menu 4.2-4.6): outlet/navigation tile geometry, pointer back-cell, and escape/back navigation through the exploration dock.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement
from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    focus_action_dock,
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

    def _open_root(self, page, index):
        self._reset_root(page)
        # The exploration root is a single seven-column row (mockup grid), so
        # horizontal arrows move across it; submenus are 2-column grids.
        for _ in range(index):
            _press(page, "ArrowRight")
        _press(page, "Enter")

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

    @covers_requirement("webclient-exploration-menu::the-exploration-dock-is-keyboard-first-and-re-homes-the-service-submenus")
    def test_pointer_back_cell_returns_to_the_root_without_an_action(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        # Pointer: open Look, then click its final back cell.
        wait_for_store_state(
            page,
            lambda s: ((s.get("panels") or {}).get("exploration") or {}).get("available") is True,
            dom_readiness={
                "selector": '#action-dock [data-item-key="look"]',
                "predicate": (
                    "() => !!document.querySelector('#action-dock [data-item-key=\"look\"]')"
                ),
                "description": "Look cell rendered in the exploration dock",
            },
        )
        page.locator('[data-item-key="look"]').click()
        wait_for_store_state(
            page,
            _connected_active,
            dom_readiness={
                "selector": '[data-testid="exploration-detail"]',
                "predicate": (
                    "() => !!document.querySelector('[data-testid=\"exploration-detail\"]')"
                ),
                "description": "exploration detail panel rendered",
            },
        )
        wait_for_store_state(
            page,
            lambda s: ((s.get("panels") or {}).get("exploration") or {}).get("available") is True,
            dom_readiness={
                "selector": '#action-dock [data-item-key="back"]',
                "predicate": (
                    "() => !!document.querySelector('#action-dock [data-item-key=\"back\"]')"
                ),
                "description": "back cell rendered in the detail dock",
            },
        )
        page.locator('[data-item-key="back"]').click()
        wait_for_store_state(
            page,
            lambda s: ((s.get("panels") or {}).get("exploration") or {}).get("available") is True,
            dom_readiness={
                "selector": "#action-dock",
                "predicate": (
                    "() => { const keys = Array.from("
                    "document.querySelectorAll('#action-dock [data-item-key]'))"
                    ".map((el) => el.getAttribute('data-item-key'));"
                    "return keys.indexOf('move') !== -1 && keys.indexOf('look') !== -1; }"
                ),
                "description": "exploration root cells (move/look) rendered in the dock",
            },
        )
        # The root cells render again, no ui_action was sent, and no
        # command-line text was submitted.
        keys = page.evaluate(
            "() => Array.from(document.querySelectorAll("
            "'#action-dock [data-item-key]')).map((el) => el.getAttribute('data-item-key'))"
        )
        # H3 (design D5): the exploration root includes the 建議 (suggestions)
        # tab; the desktop redesign (webclient-exploration-menu, synced
        # projection scenario) omits the character, quests, and inventory
        # entries the top navigation owns, so the root renders the
        # capability-driven five-tab set.
        self.assertEqual(
            keys,
            ["move", "look", "interact", "wait", "suggestions"],
        )
        self.assertEqual(sent_action_count(page), 0)
        self.assertEqual(
            page.evaluate("window.__elosernBridge.router.depth()"),
            1,
            "the back cell pops exactly one router frame",
        )

    @covers_requirement("webclient-exploration-menu::the-exploration-dock-is-keyboard-first-and-re-homes-the-service-submenus")
    def test_escape_at_intermediate_depth_keeps_cells_matched_to_the_frame(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        # Interact -> the scripted host -> 交談 (scripted keywords): two levels deep.
        panel = self._live_exploration_panel(page)
        host_identity = panel["interact"][0]["identity"]
        self._open_root(page, 2)  # Interact
        _press(page, "Enter")  # the scripted host (first present target)
        _press(page, "Enter")  # 交談 (first affordance)
        self.assertEqual(page.evaluate("window.__elosernBridge.router.depth()"), 4)
        _press(page, "Escape")  # back to the target-affordance menu
        page.wait_for_timeout(80)
        self.assertEqual(page.evaluate("window.__elosernBridge.router.depth()"), 3)
        # H3 (design D2): at depth >= 2 the dock renders both the root tab
        # bar (8 root tabs) and the scrolling pane (the active frame's rows).
        # The test's cell assertions target the pane's rows only.
        target_keys = page.evaluate(
            "() => Array.from(document.querySelectorAll("
            "'.action-dock__pane [data-item-key]')).map((el) => el.getAttribute('data-item-key'))"
        )
        # The host's affordance menu: the scripted-talk entry plus the final
        # back cell (the exploration fixture carries no guild navigate entry).
        self.assertEqual(
            target_keys,
            ["talk-scripted", "back"],
            "the target-affordance cells must render after one Escape",
        )
        self.assertEqual(
            page.evaluate(
                "window.__elosernBridge.router.currentItem() && "
                "window.__elosernBridge.router.currentItem().key"
            ),
            "talk-scripted",
        )
        _press(page, "Escape")  # back to the Interact target list
        page.wait_for_timeout(80)
        self.assertEqual(page.evaluate("window.__elosernBridge.router.depth()"), 2)
        interact_keys = page.evaluate(
            "() => Array.from(document.querySelectorAll("
            "'.action-dock__pane [data-item-key]')).map((el) => el.getAttribute('data-item-key'))"
        )
        expected_interact = [
            "target-" + str(target["identity"]) for target in panel["interact"]
        ]
        expected_interact.append("back")
        self.assertEqual(
            interact_keys,
            expected_interact,
            "the Interact list cells must render after the second Escape",
        )
        self.assertEqual(
            page.evaluate(
                "window.__elosernBridge.router.currentItem() && "
                "window.__elosernBridge.router.currentItem().key"
            ),
            "target-" + str(host_identity),
        )
        self.assertEqual(sent_action_count(page), 0)

    @covers_requirement("webclient-exploration-menu::the-exploration-dock-is-keyboard-first-and-re-homes-the-service-submenus")
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
            "'#action-dock [data-item-key]')).map((el) => el.getAttribute('data-item-key'))"
        )
        self.assertEqual(
            keys,
            ["move", "look", "interact", "wait", "suggestions"],
            "the exploration root cells must render after Escape from Quests",
        )
        self.assertEqual(
            page.evaluate(
                "window.__elosernBridge.router.currentItem() && "
                "window.__elosernBridge.router.currentItem().key"
            ),
            focused_before,
            "router's focused item must be unchanged from before the open",
        )
