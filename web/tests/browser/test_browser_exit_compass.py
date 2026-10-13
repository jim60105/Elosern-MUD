"""Exit-compass acceptance (exploration-exit-compass, task 5.2).

The compass's continuous movement is commit-driven, so these journeys run in
a scripted wilderness: the room panels are injected through the store's own
``receive`` seam, and a responder installed on the live sender answers every
``explore.move`` with its action result and the destination room's committed
update (the same two messages a real move produces). Everything the player
does goes through the real keyboard and mouse.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement
from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    aim_compass_exit,
    compass_exit_point,
    focus_action_dock,
    inject_snapshot,
    install_outbound_recorder,
    snapshot_envelope,
    store_state,
    wait_for_store_state,
)
from ._journey_support import (
    _exploration_context_actions_panel,
    _exploration_panel,
    _move_row,
    _wait_mode,
)

REGION = "測試荒野區域"
DEAD_END = "這個方向沒有路了，停下腳步。"
LOCKED_REASON = "前方的吊橋已經收起。"


def _node(x: int, y: int, current: bool = False) -> dict:
    return {
        "id": "wild:plains:%d:%d" % (x, y),
        "label": REGION,
        "x": x,
        "y": y,
        "visibility": "current" if current else "visible_unvisited",
        "current": current,
        "anchor": current,
        "landmark": False,
        "action": None,
    }


def _room(index: int, exits: list) -> dict:
    """Room ``index`` of the scripted column at (0, index).

    ``exits`` are ``(exit_ref, label, (x, y), target_index, enabled)``.
    """
    exploration = _exploration_panel(
        [],
        move_rows=[
            _move_row(ref, label, "wild:plains:%d:%d" % xy, enabled=enabled)
            for ref, label, xy, _target, enabled in exits
        ],
    )
    exploration["look"]["room"] = {"identity": 9000 + index, "display_name": REGION, "room": True}
    for row, (_ref, _label, _xy, _target, enabled) in zip(exploration["move"], exits):
        if not enabled:
            row["disabled_reason"] = {"code": "blocked", "message": LOCKED_REASON}
    local_map = {
        "schema_version": 1,
        "available": True,
        "layer": "wilderness",
        "current_node": "wild:plains:0:%d" % index,
        "title": REGION,
        "nodes": [_node(0, index, current=True)] + [_node(*xy) for _ref, _label, xy, _t, _e in exits],
        "edges": [
            {
                "source": "wild:plains:0:%d" % index,
                "destination": "wild:plains:%d:%d" % xy,
                "label": label,
                "known": True,
                "traversable": True,
            }
            for _ref, label, xy, _t, _e in exits
        ],
        "legend": [],
    }
    return {
        "panels": {
            "exploration": exploration,
            "local_map": local_map,
            "context_actions": _exploration_context_actions_panel({"status": "unavailable"}),
        },
        "targets": {ref: target for ref, _label, _xy, target, _enabled in exits},
    }


def _scripted_column() -> list:
    """Four wilderness rooms stacked north; the fourth has no way north."""
    return [
        _room(0, [("n0", "north", (0, 1), 1, True), ("e0", "east", (1, 0), 0, True)]),
        _room(1, [("n1", "north", (0, 2), 2, True), ("s1", "south", (0, 0), 0, True)]),
        _room(2, [("n2", "north", (0, 3), 3, True), ("s2", "south", (0, 1), 1, True)]),
        _room(3, [("e3", "east", (1, 3), 3, True), ("s3", "south", (0, 2), 2, True)]),
    ]


class ExitCompassBrowserTest(BrowserAcceptanceTest):
    """Hold-to-walk and the disabled-exit readout in the live client."""

    def _enter_scripted_world(self, page, rooms: list) -> None:
        inject_snapshot(page, rooms[0]["panels"])
        _wait_mode(page, "exploration")
        wait_for_store_state(page, lambda s: (s.get("panels") or {}).get("exploration", {}).get("look", {}).get("room", {}).get("identity") == 9000)
        # The responder: every explore.move is answered, 150 ms later, by its
        # success result and the destination room's committed update.
        page.evaluate(
            """(rooms) => {
              const store = window.__elosernBridge.store;
              const sender = store.getSender();
              const original = sender.sendAction.bind(sender);
              let current = 0;
              window.__walk = { moves: [] };
              sender.sendAction = (env) => {
                if (!env || env.action_id !== 'explore.move') {
                  return original(env);
                }
                window.__walk.moves.push(env.payload);
                const next = rooms[current].targets[env.payload.exit_ref];
                setTimeout(() => {
                  const v = store.view;
                  const revision = v.revision + 1;
                  store.receive(v.generation, 'ui_action_result', [{
                    protocol_version: 1,
                    presentation_epoch: v.epoch,
                    request_id: env.request_id,
                    outcome: 'success',
                    code: 'completed',
                    message: '你繼續前進。',
                    presentation_revision: revision,
                  }], {});
                  current = next;
                  const update = JSON.parse(JSON.stringify(rooms[next].envelope));
                  update.presentation_epoch = v.epoch;
                  update.revision = revision;
                  store.receive(v.generation, 'ui_update', [update], {});
                }, 150);
                return undefined;
              };
            }""",
            [
                {"targets": room["targets"], "envelope": snapshot_envelope("", 0, room["panels"])}
                for room in rooms
            ],
        )

    def _readout(self, page) -> tuple:
        return (
            page.locator('[data-testid="exploration-readout-lead"]').inner_text().strip(),
            page.locator('[data-testid="exploration-readout-text"]').inner_text().strip(),
        )

    @covers_requirement(
        "webclient-presence-rail::the-exploration-dock-roots-at-the-compass-and-the-presence-rail-and-keeps-the-footer-overview"
    )
    @covers_requirement(
        "webclient-exit-compass::continuous-movement-is-commit-driven",
        "webclient-exit-compass::continuous-movement-stops-safely-with-a-reason",
        "webclient-exit-compass::holding-a-pointer-press-on-an-angled-target-starts-a-walk",
    )
    def test_holding_a_direction_walks_until_a_dead_end(self):
        """Holding ArrowUp on the compass walks north one committed room at a
        time — one move per arrival, never two in flight — and stops at the
        room with no way north, with the dead-end reason in the readout. A
        held mouse press walks the same way."""
        page = self.logged_in_page((1451, 790))
        install_outbound_recorder(page)
        rooms = _scripted_column()
        self._enter_scripted_world(page, rooms)

        focus_action_dock(page)
        compass = page.locator('#action-dock [data-testid="exit-compass"]')
        compass.focus()
        page.keyboard.down("ArrowUp")
        page.wait_for_function(
            "(text) => document.querySelector('[data-testid=\"exploration-readout-text\"]').textContent.includes(text)",
            arg=DEAD_END,
            timeout=15000,
        )
        page.keyboard.up("ArrowUp")
        moves = page.evaluate("() => window.__walk.moves")
        self.assertEqual(
            [m["exit_ref"] for m in moves],
            ["n0", "n1", "n2"],
            "one move per arrival, north until the dead end",
        )
        self.assertEqual(
            [m["current_node"] for m in moves],
            ["wild:plains:0:0", "wild:plains:0:1", "wild:plains:0:2"],
            "each step carries the committed room's current node",
        )
        self.assertEqual(store_state(page)["panels"]["local_map"]["current_node"], "wild:plains:0:3")
        self.assertEqual(compass.get_attribute("data-walking"), "false")
        page.wait_for_timeout(800)
        self.assertEqual(len(page.evaluate("() => window.__walk.moves")), 3, "the walk sent nothing after stopping")

        # A held mouse press on the south pip walks back down: the walk keeps
        # going while the button stays down, and the release stops it.
        x, y = compass_exit_point(page, "s3")
        page.mouse.move(x, y)
        page.mouse.down()
        page.wait_for_function("() => window.__walk.moves.length >= 5", timeout=15000)
        page.mouse.up()
        page.wait_for_timeout(800)
        moves = page.evaluate("() => window.__walk.moves")
        self.assertEqual([m["exit_ref"] for m in moves[3:5]], ["s3", "s2"])
        count = len(moves)
        page.wait_for_timeout(800)
        self.assertEqual(len(page.evaluate("() => window.__walk.moves")), count, "release stopped the walk")

    @covers_requirement(
        "webclient-presence-rail::the-exploration-dock-roots-at-the-compass-and-the-presence-rail-and-keeps-the-footer-overview"
    )
    @covers_requirement(
        "webclient-exit-compass::the-compass-never-loosens-the-server-s-gate",
    )
    def test_a_disabled_exit_reads_its_reason_from_the_readout(self):
        """A disabled exit stays aimable: hovering or aiming it shows 無法通行
        and the server-authored reason in the readout, and Enter or a click
        submits nothing (the readout keeps the reason)."""
        page = self.logged_in_page((1451, 790))
        install_outbound_recorder(page)
        rooms = [_room(0, [("n0", "north", (0, 1), 0, False), ("e0", "east", (1, 0), 0, True)])]
        self._enter_scripted_world(page, rooms)

        # Idle summary first.
        self.assertEqual(self._readout(page), ("", "出口 2 · 在場 0"))

        # Pointer hover.
        x, y = compass_exit_point(page, "n0")
        page.mouse.move(x, y)
        self.assertEqual(self._readout(page), ("無法通行", LOCKED_REASON))
        page.mouse.down()
        page.mouse.up()
        page.wait_for_timeout(200)
        self.assertEqual(page.evaluate("() => window.__walk.moves.length"), 0)
        self.assertEqual(self._readout(page)[1], LOCKED_REASON)

        # Keyboard aim and Enter.
        aim_compass_exit(page, "n0")
        self.assertEqual(self._readout(page), ("無法通行", LOCKED_REASON))
        page.keyboard.press("Enter")
        page.wait_for_timeout(200)
        self.assertEqual(page.evaluate("() => window.__walk.moves.length"), 0)
        self.assertEqual(self._readout(page)[1], LOCKED_REASON)
        self.assertEqual(
            page.locator('#action-dock [data-testid="exit-compass"] [data-exit-ref="n0"]').get_attribute("data-enabled"),
            "false",
        )
