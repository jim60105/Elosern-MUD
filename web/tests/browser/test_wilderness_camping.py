"""Wilderness camping acceptance (wilderness-camping, task 5.1).

The journeys run in the live client against injected committed state, on the
travel stage of ``test_wilderness_travel``: the room's panels arrive through
the store's own ``receive`` seam, and a responder on the live sender holds
every ``explore.camp_preview`` and ``explore.camp`` the card sends, so the
test answers each with a synthetic result through the real result validator.
Clock and reserve truth come from the synthetic fixtures; nothing here names
shipped content or pins copy.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement

from .test_wilderness_travel import (
    CX,
    CY,
    _COMMIT_MOVE,
    _HOLD_MOVES,
    _TravelStage,
    _leg_panels,
    _moves,
    _walk_area,
)

# Holds every camp request (recorded, never forwarded).
_HOLD_CAMP = """() => {
  const store = window.__elosernBridge.store;
  if (window.__campHeld) return;
  const sender = store.getSender();
  const original = sender.sendAction.bind(sender);
  window.__campHeld = [];
  sender.sendAction = (env) => {
    if (env && (env.action_id === 'explore.camp_preview' || env.action_id === 'explore.camp')) {
      window.__campHeld.push(env);
      return undefined;
    }
    return original(env);
  };
}"""

# Answers held request `index`: a success carrying `data` (optionally after an
# update with `panels` and `time`, the committed publication of a settled
# camp), or a refusal with `code`/`message`.
_ANSWER_CAMP = """([index, data, code, message, panels, time]) => {
  const store = window.__elosernBridge.store;
  const env = window.__campHeld[index];
  const v = store.view;
  let revision = v.revision;
  if (panels) {
    revision = v.revision + 1;
    const accepted = store.receive(v.generation, 'ui_update', [{
      protocol_version: 1, presentation_epoch: v.epoch, base_revision: revision - 1, revision,
      mode: v.mode, panels, removed_panels: [], layout_version: v.layoutVersion,
      server_time: time ? { ...v.serverTime, ...time } : v.serverTime,
    }], {}).accepted;
    if (!accepted) return false;
  }
  const body = data
    ? { outcome: 'success', code: env.action_id, message: message || '完成。', data }
    : { outcome: 'rejected', code, message };
  return !!store.receive(v.generation, 'ui_action_result', [{
    protocol_version: 1, presentation_epoch: v.epoch, request_id: env.request_id,
    presentation_revision: revision, ...body,
  }], {}).accepted;
}"""

_REFUSAL = {"code": "party_unavailable", "message": "在場成員都已入睡或已完全恢復"}


def _member(identity: str, current: int, predicted: int, wake: int) -> dict:
    return {
        "member_id": identity, "name": "合成主角", "current_reserve": current * 3600,
        "predicted_reserve": predicted * 3600, "reserve_max": 360000, "current_percent": current,
        "predicted_percent": predicted, "wake_tick": wake, "wake_time": "第 2 日 06:00",
    }


def _preview(*, recovered: bool = True, dawn_dream: bool = True) -> dict:
    dawn = {
        "mode": "until-dawn", "available": True, "refusal": None, "dream_offerable": dawn_dream,
        "wake_tick": 108000, "wake_time": "第 2 日 06:00", "members": [_member("42", 40, 100, 108000)],
    }
    if recovered:
        rest = {
            "mode": "until-recovered", "available": True, "refusal": None, "dream_offerable": False,
            "wake_tick": 86400, "wake_time": "第 2 日 00:00", "members": [_member("42", 40, 100, 86400)],
        }
    else:
        rest = {
            "mode": "until-recovered", "available": False, "refusal": dict(_REFUSAL), "dream_offerable": False,
            "wake_tick": None, "wake_time": None, "members": [],
        }
    return {
        "available": True, "refusal": None, "dream_offerable": dawn_dream, "default_mode": "until-dawn",
        "current_tick": 68400, "current_time": "第 1 日 19:00", "modes": [dawn, rest],
    }


def _camp_result(phase: str = "complete") -> dict:
    dream = phase == "dream"
    return {
        "camp_id": "a" * 64, "phase": phase,
        "timing": {
            "elapsed_seconds": 0 if dream else 39600,
            "result_tick": 68400 if dream else 108000,
            "result_time": "第 1 日 19:00" if dream else "第 2 日 06:00",
            "wake_tick": None if dream else 108000,
            "wake_time": None if dream else "第 2 日 06:00",
        },
        "members": [{
            "member_id": "42", "name": "合成主角", "reserve_before": 144000,
            "reserve_after": 144000 if dream else 360000, "reserve_max": 360000,
            "before_percent": 40, "after_percent": 40 if dream else 100,
            "sleeping": dream, "wake_tick": None if dream else 108000,
        }],
        "events": [], "interrupted": False, "interruption_reason": None,
    }


def _held(page) -> list:
    return page.evaluate("() => window.__campHeld.map((e) => [e.action_id, e.payload])")


def _camp(page) -> dict:
    return page.evaluate("() => JSON.parse(JSON.stringify(window.__elosernBridge.store.view.camp))")


class CampingTests(_TravelStage):
    """The camp card, its refusals and the forced-walking-sleep shortcut, and
    a dusk camp settling to the configured dawn with the campfire beat."""

    def _camp_stage(self, viewport=(1451, 790), motion_level: str = "off"):
        page = self.logged_in_page(viewport, motion_level)
        page.evaluate(_HOLD_MOVES)
        page.evaluate(_HOLD_CAMP)
        self._enter(page, _leg_panels(CX, CY))
        self._wait_views(page, 1)
        self._answer(page, 0, area=_walk_area(CX, CY))
        self._wait_ready(page)
        page.wait_for_selector('[data-testid="leg-panel"][data-gauge="capacity"]', timeout=15000)
        return page

    def _answer_camp(self, page, index, data=None, code=None, message=None, panels=None, time=None):
        page.wait_for_function("(n) => window.__campHeld.length > n", arg=index, timeout=15000)
        self.assertTrue(page.evaluate(_ANSWER_CAMP, [index, data, code, message, panels, time]))

    @covers_requirement("wilderness-camping::camp-card-selects-only-server-supplied-choices")
    def test_card_inputs_refusal_and_handoff(self):
        """The leg's 紮營 opens a focused card asking only for the preview;
        1/2/D/Enter/Esc act on server choices only, a refused mode disables
        confirmation, reopening resets the dream opt-in, Enter sends one camp,
        a refused camp shows its reason, and a walking collapse puts 全員紮營
        first in the handoff with the old rows intact."""
        page = self._camp_stage()
        page.locator('[data-testid="leg-camp"]').click()
        page.wait_for_selector('[data-testid="camp-card"]', timeout=15000)
        self._answer_camp(page, 0, data=_preview(recovered=False))
        page.wait_for_selector('[data-testid="camp-card"][data-phase="choosing"]', timeout=15000)
        self.assertEqual(_held(page), [["explore.camp_preview", {}]])
        # The card owns focus; the server default is selected.
        self.assertTrue(page.evaluate("() => !!document.activeElement.closest('[data-testid=\"camp-card\"]')"))
        self.assertEqual(_camp(page)["selected"], "until-dawn")
        page.keyboard.press("2")
        self.assertEqual(_camp(page)["selected"], "until-recovered")
        self.assertIsNotNone(page.locator('[data-testid="camp-card-confirm"]').get_attribute("disabled"))
        page.keyboard.press("Enter")
        page.keyboard.press("1")
        page.keyboard.press("d")
        self.assertTrue(_camp(page)["dream"])
        # The map underneath never saw a key.
        self.assertEqual(_moves(page), [])
        page.keyboard.press("Escape")
        page.wait_for_selector('[data-testid="camp-card"]', state="detached", timeout=15000)
        page.wait_for_function(
            "() => document.activeElement && document.activeElement.dataset.testid === 'leg-camp'", timeout=15000
        )
        self.assertEqual([action for action, _ in _held(page)], ["explore.camp_preview"])

        # Reopening resets the opt-in; Enter confirms exactly once.
        page.locator('[data-testid="leg-camp"]').click()
        self._answer_camp(page, 1, data=_preview())
        page.wait_for_selector('[data-testid="camp-card"][data-phase="choosing"]', timeout=15000)
        self.assertFalse(_camp(page)["dream"])
        page.keyboard.press("Enter")
        page.keyboard.press("Enter")
        page.wait_for_function("() => window.__campHeld.length >= 3", timeout=15000)
        self.assertEqual(_held(page)[2], ["explore.camp", {"mode": "until-dawn", "dream": False}])
        self._answer_camp(page, 2, code="hostile_present", message="附近有活著的怪物，這裡不安全。")
        page.wait_for_selector('[data-testid="camp-card-refusal"]', timeout=15000)
        self.assertEqual(len(_held(page)), 3)
        self._shoot(page, "camp-refusal-1451x790.png")
        page.keyboard.press("Escape")
        page.wait_for_selector('[data-testid="camp-card"]', state="detached", timeout=15000)

        # A walking collapse: the step commits with the sleep-control view.
        page.locator('[data-testid="travel-map"]').focus()
        page.keyboard.down("ArrowRight")
        page.wait_for_function("() => window.__travelMoves.length >= 1", timeout=15000)
        handoff = {
            "schema_version": 1, "available": True, "owner_id": 42, "controlled_body_id": 42,
            "transition_id": "42:forced:1",
            "selection": {"available": True, "rows": []},
            "party": {"label": "全員一起睡眠", "enabled": False, "reason": "在場成員都已入睡或已完全恢復"},
            "controlled_sleep": {"sleep_id": "forced:42:1", "revision": 0},
            "owner_sleep": {
                "sleep_id": "forced:42:1", "revision": 0, "generation": 1, "dream_pending": False,
                "continuation": "none", "continuation_available": True, "continuation_reason": None,
            },
        }
        collapsed = _leg_panels(CX + 1, CY)
        # The collapsed body cannot move on: every step row is disabled, so
        # the walk stops on this commit.
        collapsed["exploration"]["move"] = [
            {**row, "enabled": False, "disabled_reason": {"code": "member_asleep", "message": "沉睡中，無法行動"}} for row in collapsed["exploration"]["move"]
        ]
        self.assertEqual(
            page.evaluate(_COMMIT_MOVE, [0, {**collapsed, "sleep_handoff": handoff}]), [True, True]
        )
        page.keyboard.up("ArrowRight")
        page.wait_for_selector('[data-testid="sleep-handoff-card"]', timeout=15000)
        # The stage reads the new cell's map; the gate frees once it lands.
        self._wait_views(page, 2)
        self._answer(page, 1, area=_walk_area(CX + 1, CY))
        page.wait_for_function("() => window.__elosernBridge.store.view.dispatch.inFlight === null", timeout=15000)
        self.assertEqual(len(_moves(page)), 1)
        rows = page.locator('[data-testid="sleep-handoff-card"] [data-testid^="sleep-handoff-"]')
        ids = [rows.nth(i).get_attribute("data-testid") for i in range(rows.count())]
        self.assertEqual(ids[0], "sleep-handoff-camp")
        self.assertIn("sleep-handoff-party", ids[1:])
        page.locator('[data-testid="sleep-handoff-camp"]').click()
        page.wait_for_selector('[data-testid="camp-card"]', timeout=15000)
        page.keyboard.press("Escape")
        page.wait_for_selector('[data-testid="sleep-handoff-card"]', timeout=15000)
        after = [rows.nth(i).get_attribute("data-testid") for i in range(rows.count())]
        self.assertEqual(after, ids)
        page.close()

    @covers_requirement("wilderness-camping::campfire-beat-is-presentation-only-and-skippable")
    def test_dusk_camp_to_dawn_and_beat_controls(self):
        """A dusk camp to dawn: one camp request, the committed dawn clock and
        recovered reserve, the beat finishing early on a key without another
        action, Continue returning to the map; motion off renders the final
        beat at once and a dream entry replaces the beat."""
        page = self._camp_stage(motion_level="full")
        page.locator('[data-testid="leg-camp"]').click()
        self._answer_camp(page, 0, data=_preview())
        page.wait_for_selector('[data-testid="camp-card"][data-phase="choosing"]', timeout=15000)
        page.keyboard.press("Enter")
        page.wait_for_function("() => window.__campHeld.length >= 2", timeout=15000)
        status = _leg_panels(CX, CY)["status"]
        self._answer_camp(
            page, 1, data=_camp_result(), message="夜裡無事。", panels={"status": status},
            time={"hour": 6, "minute": 0, "second": 0},
        )
        page.wait_for_selector('[data-testid="campfire-card"][data-settled="false"]', timeout=15000)
        # The committed clock is the configured dawn of the fixture.
        self.assertEqual(page.evaluate("() => window.__elosernBridge.store.view.serverTime.hour"), 6)
        page.keyboard.press("x")
        page.wait_for_selector('[data-testid="campfire-card"][data-settled="true"]', timeout=15000)
        percents = page.locator('[data-testid="campfire-member"]').first.get_attribute("data-percent")
        self.assertEqual(percents, "100")
        self.assertEqual(len(_held(page)), 2)
        self._shoot(page, "campfire-1451x790.png")
        page.keyboard.press("Enter")
        page.wait_for_selector('[data-testid="campfire-card"]', state="detached", timeout=15000)
        self.assertTrue(page.evaluate("() => window.__elosernBridge.store.view.travel.layout"))
        self.assertEqual(len(_held(page)), 2)
        page.close()

        still = self._camp_stage(motion_level="off")
        still.locator('[data-testid="leg-camp"]').click()
        self._answer_camp(still, 0, data=_preview())
        still.wait_for_selector('[data-testid="camp-card"][data-phase="choosing"]', timeout=15000)
        still.keyboard.press("Enter")
        self._answer_camp(still, 1, data=_camp_result(), message="夜裡無事。")
        still.wait_for_selector('[data-testid="campfire-card"][data-settled="true"]', timeout=15000)
        still.keyboard.press("Enter")
        still.wait_for_selector('[data-testid="campfire-card"]', state="detached", timeout=15000)
        # A dream entry hands over to the dream stage: no beat.
        still.locator('[data-testid="leg-camp"]').click()
        self._answer_camp(still, 2, data=_preview())
        still.wait_for_selector('[data-testid="camp-card"][data-phase="choosing"]', timeout=15000)
        still.keyboard.press("d")
        still.keyboard.press("Enter")
        self._answer_camp(still, 3, data=_camp_result("dream"))
        still.wait_for_function("() => window.__elosernBridge.store.view.camp.phase === 'closed'", timeout=15000)
        self.assertEqual(_held(still)[3], ["explore.camp", {"mode": "until-dawn", "dream": True}])
        self.assertEqual(still.locator('[data-testid="campfire-card"]').count(), 0)
        still.close()
