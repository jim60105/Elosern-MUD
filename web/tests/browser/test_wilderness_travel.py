"""Wilderness travel stage acceptance (wilderness-travel-interface, task 4.1).

The journeys run in the live client against injected committed state: the
room's panels arrive through the store's own ``receive`` seam, and a
responder on the live sender holds every ``map.view`` the travel stage sends
so the test answers it with its action result and a synthetic schema-2
wilderness ``area_map`` in either order. Nothing here names shipped content.
"""

from __future__ import annotations

import os
import tempfile

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    inject_snapshot,
    scene_block,
    store_state,
    valid_status_panel,
    wait_for_store_state,
)

WINDOW = 41
CX, CY = 60, 80
WILD = "wilderness:合成荒原:%d,%d" % (CX, CY)
TOWN = "grid:t_synth_map:2,0"
SHOTS = os.environ.get(
    "ELOSERN_TRAVEL_SHOTS", os.path.join(tempfile.gettempdir(), "wilderness-travel-shots")
)


def _art(subject: str) -> dict:
    return {
        "schema_version": 4,
        "available": True,
        "kind": "scene",
        "scene": scene_block("/art/scene/t_travel.png", subject, label="合成荒原", alt="合成荒原"),
        "portrait_catalog": {},
    }


def _area(cx: int = CX, cy: int = CY) -> dict:
    """A schema-2 wilderness window centred on ``(cx, cy)``: a 3 x 3 revealed
    open-ground block around the party, everything else unknown."""
    rows = []
    for row in range(WINDOW):
        y = cy - 20 + row
        if abs(y - cy) <= 1:
            rows.append(
                [
                    {"length": 19, "kind": "unknown"},
                    {
                        "length": 3, "kind": "terrain", "terrain": "open_ground", "passable": True,
                        "band": 3, "tier": 0, "road": False, "ford": False,
                    },
                    {"length": 19, "kind": "unknown"},
                ]
            )
        else:
            rows.append([{"length": WINDOW, "kind": "unknown"}])
    current = "wild:elosern:%d:%d" % (cx, cy)
    return {
        "schema_version": 2,
        "available": True,
        "layer": "wilderness",
        "map_id": "elosern",
        "frame": {"key": "elosern", "unit": "km"},
        "current_node": current,
        "title": "合成荒原",
        "nodes": [
            {
                "id": current, "label": "合成荒原", "x": cx + 0.5, "y": cy + 0.5,
                "visibility": "current", "visited": True, "gateway": None, "action": None,
            }
        ],
        "edges": [],
        "quest_markers": [],
        "district_name": "合成東麓",
        "cell_km": 1,
        "window": {"min_x": cx - 20, "min_y": cy - 20, "width": WINDOW, "height": WINDOW},
        "rows": rows,
        "light_phase": "day",
        "ground_radius": 1,
        "entities": [],
        "sightings": [],
    }


def _row(identity: str, name: str, reserve: int, stage: str = "normal", label: str = "合成充沛", asleep: bool = False) -> dict:
    return {
        "identity": identity, "name": name, "reserve_percent": reserve, "stage": stage, "label": label,
        "severity": "informational" if stage in ("normal", "sleeping") else "harmful",
        "restriction": "沉睡中，無法行動" if asleep else None, "asleep": asleep,
    }


def _party(companions: list[tuple[int, str]]) -> dict:
    def slot(identity, name, role):
        return {
            "identity": identity, "display_name": name, "portrait_ref": None,
            "hp_current": 100, "hp_maximum": 100, "mp_current": 50, "mp_maximum": 50,
            "sp_current": 40, "sp_maximum": 40, "role": role, "knocked_out": False, "unread": False,
            "bond_stage": None if role == "commander" else "初識",
            "membership": None if role == "commander" else {"general": True, "temporary_commissions": []},
        }

    return {
        "schema_version": 3,
        "available": True,
        "general_quota": {"used": len(companions), "limit": 4},
        "viewed_member_id": 1,
        "slots": [slot(1, "合成主角", "commander"), *[slot(i, n, "companion") for i, n in companions]],
    }


# Holds every map.view on the live sender (recorded, never forwarded) and
# answers one held request in the requested order.
_HOLD_MAPS = """() => {
  const store = window.__elosernBridge.store;
  if (window.__travelHold) return;
  const sender = store.getSender();
  const original = sender.sendAction.bind(sender);
  window.__travelHold = { views: [] };
  sender.sendAction = (env) => {
    if (env && env.action_id === 'map.view') {
      window.__travelHold.views.push(env);
      return undefined;
    }
    return original(env);
  };
}"""

_ANSWER = """([area, order, requestIndex]) => {
  const store = window.__elosernBridge.store;
  const env = window.__travelHold.views[requestIndex];
  const v = store.view;
  const revision = v.revision + 1;
  const result = () => store.receive(v.generation, 'ui_action_result', [{
    protocol_version: 1, presentation_epoch: v.epoch, request_id: env.request_id,
    outcome: 'success', code: 'completed', message: '地圖已更新。', presentation_revision: revision,
  }], {});
  const body = () => store.receive(v.generation, 'ui_update', [{
    protocol_version: 1, presentation_epoch: v.epoch, base_revision: revision - 1, revision,
    mode: v.mode, panels: { area_map: area }, removed_panels: [], layout_version: v.layoutVersion,
    server_time: v.serverTime,
  }], {});
  const outcomes = order === 'result-first' ? [result(), body()] : [body(), result()];
  return outcomes.map((o) => !!o.accepted);
}"""


def _travel(page) -> dict:
    return page.evaluate("() => JSON.parse(JSON.stringify(window.__elosernBridge.store.view.travel))")


def _held(page) -> int:
    return page.evaluate("() => window.__travelHold.views.length")


class TravelLayoutTests(BrowserAcceptanceTest):
    """The travel layout, its own area refresh and the party medallions."""

    def _enter(self, page, panels: dict) -> None:
        page.evaluate(_HOLD_MAPS)
        inject_snapshot(page, panels)
        wait_for_store_state(page, lambda s: (s.get("panels") or {}).get("art", {}).get("available") is True)

    def _wait_views(self, page, count: int) -> None:
        page.wait_for_function("(n) => window.__travelHold.views.length >= n", arg=count, timeout=15000)

    def _answer(self, page, index: int, order: str = "body-first", area: dict | None = None) -> None:
        accepted = page.evaluate(_ANSWER, [area or _area(), order, index])
        self.assertEqual(accepted, [True, True])

    def _wait_ready(self, page) -> None:
        try:
            page.wait_for_selector('[data-testid="travel-map"][data-map-status="ready"]', timeout=15000)
        except Exception as error:  # observability: ignore R2: test diagnostics re-raised with the live state
            state = page.evaluate(
                "() => { const v = window.__elosernBridge.store.view; return JSON.stringify({"
                " status: v.travel.mapStatus, layout: v.travel.layout, revision: v.revision,"
                " pub: v.mapPublications, inFlight: v.dispatch.inFlight, result: v.lastActionResult,"
                " held: window.__travelHold.views.map((e) => e.request_id) }); }"
            )
            raise AssertionError(f"travel map not ready: {state}") from error

    def _shoot(self, page, name: str) -> None:
        os.makedirs(SHOTS, exist_ok=True)
        page.screenshot(path=os.path.join(SHOTS, name))

    @covers_requirement("webclient-travel-layout::wilderness-presentation-follows-committed-room-identity")
    def test_settlement_gate_layout(self):
        """A committed wilderness identity selects travel and a settlement
        identity restores the ordinary stage, at both acceptance viewports."""
        for viewport in ((1451, 790), (2560, 1440)):
            page = self.logged_in_page(viewport)
            self._enter(page, {"status": valid_status_panel("合成主角", "42"), "art": _art(WILD)})
            page.wait_for_selector('[data-testid="travel-map"]', timeout=15000)
            self._wait_views(page, 1)
            self._answer(page, 0)
            self._wait_ready(page)
            stage = page.locator('[data-testid="elosern-stage"]')
            self.assertEqual(stage.get_attribute("data-travel"), "true")
            # Both portrait anchors are empty and out of the layout.
            for anchor in ("anchor-actor-left", "anchor-actor-right"):
                self.assertEqual(page.locator(f'[data-testid="{anchor}"] [data-testid="stage-actor"]').count(), 0)
                self.assertFalse(page.locator(f'[data-testid="{anchor}"]').is_visible())
            # The medallions stand in the vitals column, inside the stage, above
            # the band; the place card stands alone in the map column.
            medallions = page.locator('[data-testid="party-medallions"]').bounding_box()
            band = page.locator('[data-testid="stage-band"]').bounding_box()
            self.assertIsNotNone(medallions)
            self.assertLessEqual(medallions["y"] + medallions["height"], band["y"] + 1)
            self.assertEqual(page.locator('[data-testid="anchor-map"] .local-map').count(), 0)
            self.assertTrue(page.locator('[data-testid="place-card"]').is_visible())
            # A visible focus ring survives in the travel stage.
            page.locator('[data-testid="area-map"] [tabindex="0"]').first.focus()
            self._shoot(page, "travel-%dx%d.png" % viewport)

            # Through the gate: the settlement's identity restores the stage.
            inject_snapshot(page, {"status": valid_status_panel("合成主角", "42"), "art": _art(TOWN)})
            page.wait_for_selector('[data-testid="travel-map"]', state="detached", timeout=15000)
            self.assertIsNone(stage.get_attribute("data-travel"))
            self.assertEqual(page.locator('[data-testid="party-medallions"]').count(), 0)
            self.assertFalse(_travel(page)["layout"])
            page.close()

    @covers_requirement("webclient-travel-layout::travel-area-refresh-follows-committed-state")
    def test_refresh_adoption(self):
        """Only the current request's own result and body make the stage
        ready, in either order; a same-position snapshot recovers once."""
        page = self.logged_in_page((1451, 790))
        self._enter(page, {"status": valid_status_panel("合成主角", "42"), "art": _art(WILD)})
        self._wait_views(page, 1)
        held = page.evaluate("() => window.__travelHold.views.map((e) => e.payload)")
        self.assertEqual(held, [{"scope": "area"}])
        self.assertEqual(_travel(page)["mapStatus"], "refreshing")
        self._answer(page, 0, "result-first")
        self._wait_ready(page)
        self.assertEqual(_travel(page)["map"]["party"], {"x": CX, "y": CY})

        # An external full snapshot at the same position and time asks once.
        inject_snapshot(page, {"status": valid_status_panel("合成主角", "42"), "art": _art(WILD)})
        self._wait_views(page, 2)
        self.assertEqual(_travel(page)["mapStatus"], "refreshing")
        self._answer(page, 1, "body-first")
        self._wait_ready(page)
        # The owner's own completion never asks again.
        page.wait_for_timeout(600)
        self.assertEqual(_held(page), 2)
        state = store_state(page)
        self.assertIsNone((state.get("dispatch") or {}).get("inFlight"))

    @covers_requirement("webclient-travel-layout::medallions-identify-committed-physiological-subjects")
    def test_medallion_subjects(self):
        """Each present member joins its own body-keyed reserve and posture;
        a member with no committed row is not with the party."""
        status = valid_status_panel("合成主角", "42")
        status["fatigue"] = [
            _row("42", "合成主角", 73),
            _row("101", "合成甲", 2, "forced_sleep", "合成昏睡", asleep=True),
            _row("102", "合成乙", 38, "moderate", "合成疲勞"),
        ]
        page = self.logged_in_page((1451, 790))
        self._enter(page, {"status": status, "art": _art(WILD), "party": _party([(101, "合成甲"), (102, "合成乙"), (103, "合成丙")])})
        page.wait_for_selector('[data-testid="party-medallions"]', timeout=15000)
        medallions = page.locator('[data-testid="party-medallion"]')
        identities = medallions.evaluate_all("(els) => els.map((el) => el.dataset.identity)")
        self.assertEqual(identities, ["42", "101", "102"])
        facts = medallions.evaluate_all(
            "(els) => els.map((el) => [el.dataset.controlled, el.dataset.asleep,"
            " el.querySelector('[data-testid=\"party-medallion__bar\"]').dataset.reserve])"
        )
        self.assertEqual(facts, [["true", "false", "73"], ["false", "true", "2"], ["false", "false", "38"]])
        self.assertEqual(
            medallions.nth(2).locator('[data-testid="party-medallion__sr"]').text_content(),
            "合成乙：精力 38%（合成疲勞）",
        )
        self.assertEqual(page.locator('[data-testid="party-medallion__moon"]').count(), 1)
        # The dock never repeats the medallions' fatigue lines.
        self.assertEqual(page.locator('[data-testid="status-panel__fatigue"]').count(), 0)
