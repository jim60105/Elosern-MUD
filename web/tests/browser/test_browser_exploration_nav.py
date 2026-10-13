"""Keyboard-only exploration browser acceptance (webclient-exploration-menu 4.2-4.6): navigation tile geometry, pointer back-cell, and escape/back navigation through the exploration dock.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement
from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    CARD_SELECTOR,
    WAIT_CARD_SELECTOR,
    activate_compass_exit,
    activate_overview_chip,
    card_row_keys,
    compass_target_refs,
    exploration_root_controls,
    fixture_home_node_id,
    focus_action_dock,
    install_outbound_recorder,
    open_verb_card,
    outbound_messages,
    presence_entry_keys,
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
        """Every rendered row identity inside the dock (the pane's
        rows carry the `data-item-key` seam; the legacy suggestion
        cards render without one)."""
        return page.evaluate(
            "() => Array.from("
            "document.querySelectorAll('#action-dock [data-item-key]'))"
            ".map((el) => el.getAttribute('data-item-key'))"
        )

    @covers_requirement("webclient-presence-rail::the-exploration-dock-roots-at-the-compass-and-the-presence-rail-and-keeps-the-footer-overview")
    def test_pointer_back_cell_returns_to_the_root_without_an_action(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        # Pointer: open a person's verb card from the presence rail, then
        # click its trailing ✕ 返回 row (exploration-presence-rail: the card
        # is client-local, never a router frame).
        panel = self._live_exploration_panel(page)
        targets = panel.get("interact") or []
        self.assertTrue(targets, "the fixture room must offer an interact target")
        chip_key = "target-%s" % targets[0]["identity"]
        medallion = '[data-anchor="presence"] [data-entry-key="%s"]' % chip_key
        wait_for_store_state(
            page,
            lambda s: ((s.get("panels") or {}).get("exploration") or {}).get("available") is True,
            dom_readiness={
                "selector": medallion,
                "predicate": "() => !!document.querySelector(%r)" % medallion,
                "description": "the person's medallion rendered on the presence rail",
            },
        )
        page.locator(medallion).click()
        back_row = '[data-anchor="choices"] [data-testid="presence-card"] [data-row-key="back"]'
        wait_for_store_state(
            page,
            lambda s: (s.get("presenceCard") or {}).get("kind") == "verbs",
            dom_readiness={
                "selector": back_row,
                "predicate": "() => !!document.querySelector(%r)" % back_row,
                "description": "the verb card's back row rendered",
            },
        )
        self.assertEqual(self._depth(page), 1, "opening the verb card pushes no router frame")
        page.locator(back_row).click()
        wait_for_store_state(
            page,
            lambda s: s.get("presenceCard") is None,
            dom_readiness={
                "selector": medallion,
                "predicate": "() => document.activeElement === document.querySelector(%r)"
                % '[data-anchor="presence"] [data-testid="presence-rail"]',
                "description": "focus back on the presence rail",
            },
        )
        # The room actions render again on the place card, the dock holds no
        # row (the exploration root is empty, exploration-room-actions), no
        # ui_action was sent, and the stack is at the root frame.
        controls = exploration_root_controls(page)
        self.assertEqual(controls["dockRows"], [], "the exploration root renders no dock row")
        self.assertIn(chip_key, presence_entry_keys(page), "the rail renders the person again")
        self.assertTrue(controls["look"], "the place card renders 查看房間 again")
        self.assertTrue(controls["wait"], "the place card renders 等待 again")
        self.assertEqual(sent_action_count(page), 0)
        self.assertEqual(
            page.evaluate("window.__elosernBridge.router.depth()"),
            1,
            "the card never pushed a router frame",
        )

    @covers_requirement("webclient-presence-rail::the-exploration-dock-roots-at-the-compass-and-the-presence-rail-and-keeps-the-footer-overview")
    def test_escape_at_intermediate_depth_keeps_cells_matched_to_the_frame(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        # The rail's host medallion -> the verb card: client-local, so the
        # router stays at the overview (exploration-presence-rail). 交談
        # dispatches explore.talk_open from the card itself.
        panel = self._live_exploration_panel(page)
        host_identity = panel["interact"][0]["identity"]
        open_verb_card(page, host_identity)
        self.assertEqual(page.evaluate("window.__elosernBridge.router.depth()"), 1)
        # The host's verb card: the 交談 conversation entry, the author
        # editor entry, 查看, and the trailing ✕ 返回 (the exploration
        # fixture carries no guild navigate entry), centred over the stage.
        self.assertEqual(
            card_row_keys(page),
            ["talk-open", "service-npc_persona", "look-target", "back"],
            "the verb card's rows",
        )
        _press(page, "Escape")  # closes the card
        page.wait_for_timeout(80)
        self.assertEqual(page.locator(CARD_SELECTOR).count(), 0)
        self.assertEqual(page.evaluate("window.__elosernBridge.router.depth()"), 1)
        # The exits are the exit compass's (exploration-exit-compass), the
        # people the presence rail's, and the room actions the place card's
        # and the 建議 pill's (exploration-room-actions): the dock has no row.
        controls = exploration_root_controls(page)
        self.assertEqual(controls["dockRows"], [], "the exploration root renders no dock row")
        self.assertTrue(controls["look"] and controls["wait"], "the place card's room actions")
        # The 建議 pill renders whenever the committed envelope's status is
        # not `unavailable`.
        suggestions = (
            ((store_state(page).get("panels") or {}).get("context_actions") or {})
            .get("suggestions")
            or {}
        )
        self.assertEqual(controls["pill"], suggestions.get("status") not in (None, "unavailable"))
        # Escape returned focus to the medallion that opened the card.
        self.assertEqual(
            page.evaluate(
                """() => {
                  const rail = document.querySelector('[data-anchor="presence"] [data-testid="presence-rail"]');
                  const el = rail && document.getElementById(rail.getAttribute('aria-activedescendant'));
                  return document.activeElement === rail && el ? el.getAttribute('data-entry-key') : null;
                }"""
            ),
            "target-" + str(host_identity),
        )
        self.assertEqual(sent_action_count(page), 0)

    @covers_requirement("webclient-presence-rail::the-exploration-dock-roots-at-the-compass-and-the-presence-rail-and-keeps-the-footer-overview")
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

        # The exploration root is empty (exploration-room-actions): the room
        # actions are the place card's, and the dock renders no row.
        controls = exploration_root_controls(page)
        self.assertEqual(controls["dockRows"], [], "no dock row renders after Escape from Quests")
        self.assertTrue(controls["look"] and controls["wait"], "the place card's room actions render after Escape from Quests")
        self.assertEqual(
            page.evaluate(
                "window.__elosernBridge.router.currentItem() && "
                "window.__elosernBridge.router.currentItem().key"
            ),
            focused_before,
            "router's focused item must be unchanged from before the open",
        )

    @covers_requirement(
        "webclient-presence-rail::the-exploration-dock-roots-at-the-compass-and-the-presence-rail-and-keeps-the-footer-overview"
    )
    def test_keyboard_only_journey_walks_the_overview(self):
        """A pure arrows-and-Enter journey at 1451x790: the exit compass
        moves, a rail medallion opens the verb card (Escape returns with that
        medallion focused), and a move from the minimap closes the open wait
        card and leaves the dock at the new room's exploration root
        (webclient-scene-overview-swap D2; exploration-presence-rail;
        exploration-room-actions)."""
        page = self.logged_in_page((1451, 790))
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

        # Arrows reach a medallion on the rail; Enter opens the verb card;
        # Escape closes it with that medallion focused.
        open_verb_card(page, person["identity"])
        self.assertEqual(
            (store_state(page).get("presenceCard") or {}).get("identity"),
            person["identity"],
            "the medallion must open the person's verb card",
        )
        _press(page, "Escape")
        wait_for_store_state(page, lambda s: s.get("presenceCard") is None)
        self.assertEqual(
            page.evaluate(
                """() => {
                  const rail = document.querySelector('[data-anchor="presence"] [data-testid="presence-rail"]');
                  const el = rail && document.getElementById(rail.getAttribute('aria-activedescendant'));
                  return document.activeElement === rail && el ? el.getAttribute('data-entry-key') : null;
                }"""
            ),
            "target-%s" % person["identity"],
            "Escape must restore the medallion that opened the card",
        )
        self.assertEqual(page.locator(CARD_SELECTOR).count(), 0)

        # The exits are on the exit compass (exploration-exit-compass): every
        # committed exit is a compass target, none is a dock row, and the
        # compass's keyboard cycle plus Enter submits explore.move for one.
        self.assertEqual(
            sorted(compass_target_refs(page)),
            sorted(str(row["exit_ref"]) for row in exits),
        )
        self.assertEqual(
            page.locator('#action-dock [data-item-key^="exit-"]').count(),
            0,
        )
        enabled_exit = next(row for row in exits if row.get("enabled"))
        activate_compass_exit(page, enabled_exit["exit_ref"])
        self._wait_panel(
            page,
            "local_map",
            lambda p: p.get("available") is True and p["current_node"] != fixture_home_node_id(),
        )
        self.assertEqual(sent_action_count(page, "explore.move"), 1)
        wait_for_store_state(page, _connected_active)
        page.wait_for_timeout(120)

        # The new room's exploration root is the dock's ONLY frame, and
        # nothing of the previous room stays activatable.
        self.assertEqual(page.evaluate("() => window.__elosernBridge.router.depth()"), 1)
        self.assertEqual(
            store_state(page)["dockSource"],
            "exploration.root",
            "the dock must be at the exploration root after a move",
        )
        self.assertEqual(page.locator(CARD_SELECTOR).count(), 0)

        # Opening the wait card from the place card's 等待 and then moving by
        # activating a minimap node closes the card in that commit
        # (exploration-room-actions: a minimap move bypasses the card).
        activate_overview_chip(page, "wait")
        page.wait_for_selector(WAIT_CARD_SELECTOR, timeout=15000)
        self.assertEqual(page.evaluate("() => window.__elosernBridge.router.depth()"), 1)

        # The minimap's own node control is the move path that bypasses the
        # dock entirely: a click on it submits the same explore.move the
        # exit compass would.
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
            lambda s: s.get("roomCard") is None and s.get("dockSource") == "exploration.root",
            timeout=30000,
        )
        self.assertEqual(page.locator(WAIT_CARD_SELECTOR).count(), 0)
        controls = exploration_root_controls(page)
        self.assertTrue(controls["look"] and controls["wait"])
        self.assertEqual(controls["dockRows"], [])
