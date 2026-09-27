"""Combat beats are choreographed on the stage (webclient-combat-beat-choreography, C13c).

Every journey plays one synthetic combat round through the live client's own
store: it commits a combat snapshot with its own participants and art
catalog, dispatches the player's `combat.cast` (the outbound `ui_action` is
swallowed, so the server never sees it), appends the round's narrative lines,
and commits the completing publication carrying the round's `combat_beats`
panel and the action's result. The store binds and plays the round exactly as
it does a live one (C13b's real-server journeys keep the end-to-end binding
covered); the synthetic round is what lets a journey defeat the last foe in
one attack.

Motion is read from computed styles on the element that carries each gesture,
polled on the store's own published stage, never from elapsed time, so a slow
runner can only lengthen a window, never skip one.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    snapshot_envelope,
    valid_local_map_panel,
    valid_status_panel,
    wait_for_store_state,
)
from ._journey_support import (
    _SCENE_PNG_BYTES,
    _art_panel,
    _combat_panel,
    _exploration_context_actions_panel,
    _exploration_panel,
    _interact_target,
    _participant,
)

REFERENCE = (1920, 1080)

# The player's committed catalog key: the fixture combat panel's first party
# member (identity 1, `portrait_ref` "1") is the status panel's actor.
PLAYER = "1"
FOE_A = "11"
FOE_B = "12"
ROUND_CLOSING_LINE = "行動完成，繼續戰鬥。"
VICTORY_LINE = "戰鬥勝利。"


def _foe(ref: str, hp: int, state: str = "active") -> dict:
    names = {FOE_A: "哥布林", FOE_B: "史萊姆"}
    return _participant(int(ref), "e" + ref, names[ref], "foes", state, hp, 30, ref)


def _combat_panels(foes: list) -> dict:
    panel = _combat_panel()
    party = [p for p in panel["participants"] if p["team"] == "party"]
    panel["participants"] = party + foes
    panel["skills"] = []
    refs = [p["portrait_ref"] for p in panel["participants"] if p["portrait_ref"] is not None]
    return {
        "status": valid_status_panel("勇者", PLAYER),
        "context_actions": panel,
        "art": _art_panel(refs),
    }


def _exploration_panels() -> dict:
    return {
        "status": valid_status_panel("勇者", PLAYER),
        "exploration": _exploration_panel([_interact_target(21, "小販")]),
        "context_actions": _exploration_context_actions_panel({"status": "unavailable"}),
        "local_map": valid_local_map_panel(),
        "art": _art_panel([]),
    }


def _beat(seq: int, action: int, kind: str, actor: str, target: str, amount=None, hp_after=None, text=None) -> dict:
    return {
        "seq": seq,
        "action": action,
        "kind": kind,
        "actor": actor,
        "target": target,
        "amount": amount,
        "hp_after": hp_after,
        "text": text or f"節拍 {seq}。",
    }


def _beats_panel(round_id: str, beats: list) -> dict:
    return {"schema_version": 1, "available": True, "round": round_id, "beats": beats}


# Swallows the outbound `ui_action` so the synthetic dispatch never reaches
# the server; every other message still travels.
_SWALLOW_ACTIONS = """() => {
  if (window.__c13cSwallow) { return; }
  window.__c13cSwallow = true;
  const original = Evennia.msg.bind(Evennia);
  Evennia.msg = function (cmdname, args, kwargs, callback) {
    if (cmdname === 'ui_action') { return undefined; }
    return original(cmdname, args, kwargs, callback);
  };
}"""

# These scripts hand-build `ui_snapshot` / `ui_update` / `ui_action_result`
# envelopes (the panel builders are the shared schema-valid ones). A change to
# the envelope or the panel contract must be mirrored here: nothing else in
# this file would fail as loudly as the reducer's rejection message.
#
# Commits one full snapshot, stamped from the live view, and waits a frame.
_COMMIT = """async ([env]) => {
  const store = window.__elosernBridge.store;
  const view = store.view;
  env.presentation_epoch = view.epoch;
  env.revision = view.revision + 1;
  const result = store.receive(view.generation, 'ui_snapshot', [env], {});
  if (!result.accepted) throw new Error('snapshot rejected: ' + JSON.stringify(result));
  await new Promise((resolve) => requestAnimationFrame(() => resolve()));
}"""

# The player's action and its round: dispatch, the round's lines, then the
# completing publication (a partial update in combat, a full snapshot for the
# round that ends the fight) and the action's result, in the wire order.
_PLAY_ROUND = """async ([env, kind, lines]) => {
  const store = window.__elosernBridge.store;
  const requestId = store.dispatchAction('combat.cast', { skill_key: 'basic_attack', targets: [] });
  if (requestId === null) throw new Error('the dispatch was refused');
  for (const line of lines) { store.appendText('out', line); }
  const view = store.view;
  env.presentation_epoch = view.epoch;
  env.revision = view.revision + 1;
  const result = store.receive(view.generation, kind, [env], {});
  if (!result.accepted) throw new Error('round publication rejected: ' + JSON.stringify(result));
  store.receive(view.generation, 'ui_action_result', [{
    protocol_version: 1,
    presentation_epoch: view.epoch,
    request_id: requestId,
    outcome: 'success',
    code: 'completed',
    message: '完成',
    presentation_revision: env.revision,
  }], {});
  await new Promise((resolve) => requestAnimationFrame(() => resolve()));
}"""

# One figure's gesture as the stage renders it: the gesture wrapper's
# attribute and running animation, and the rising number's.
_GESTURE_OF = """(sel) => {
  const actor = document.querySelector(sel);
  if (!actor) return null;
  const beat = actor.querySelector(':scope > .stage-actor__beat');
  const float = actor.querySelector(':scope > .stage-actor__float');
  const cs = beat ? getComputedStyle(beat) : null;
  const fs = float ? getComputedStyle(float) : null;
  return {
    beat: beat ? beat.getAttribute('data-beat') : null,
    name: cs ? cs.animationName : null,
    duration: cs ? cs.animationDuration : null,
    transform: cs ? cs.transform : null,
    float: float ? {
      text: float.textContent,
      name: fs.animationName,
      duration: fs.animationDuration,
      opacity: Number(fs.opacity),
      hidden: float.getAttribute('aria-hidden'),
    } : null,
  };
}"""

PLAYER_ACTOR = '[data-anchor="actor-left"] [data-testid="stage-actor"]'


def _foe_actor(ref: str) -> str:
    return f'[data-testid="foe-slot"][data-portrait-ref="{ref}"] [data-testid="stage-actor"]'


class CombatChoreographyBrowserTest(BrowserAcceptanceTest):
    """Design D4-D7: the beat gestures per level and the terminal-round hold."""

    def _page(self, motion_level):
        page = self.logged_in_page(REFERENCE, motion_level=motion_level)
        page.route(
            "**/art/*.png",
            lambda route: route.fulfill(status=200, content_type="image/png", body=_SCENE_PNG_BYTES),
        )
        page.wait_for_function(
            "() => !!(window.__elosernBridge && window.__elosernBridge.store.view.epoch)", timeout=15000
        )
        page.evaluate(_SWALLOW_ACTIONS)
        return page

    def _enter_combat(self, page, foes: list) -> None:
        page.evaluate(_COMMIT, [snapshot_envelope("", 0, _combat_panels(foes), mode="combat")])
        wait_for_store_state(page, lambda s: s.get("mode") == "combat")
        page.wait_for_function(
            "(n) => document.querySelectorAll('[data-testid=\"foe-slot\"]').length === n", arg=len(foes)
        )
        # The combat stage has settled: the veil's entrance fade is over.
        page.wait_for_function(
            "() => Number(getComputedStyle(document.querySelector('[data-testid=\"stage-combat-veil\"]')).opacity) === 1"
        )
        # The dock accepts the dispatch only once nothing is in flight.
        wait_for_store_state(page, lambda s: s["dispatch"]["inFlight"] is None and not s["dispatch"]["beatLocked"])

    def _play(self, page, beats: list, *, terminal: bool, foes_after: list, lines_after: list) -> None:
        panel = _beats_panel("s-9/1", beats)
        if terminal:
            panels = {**_exploration_panels(), "combat_beats": panel}
            env = snapshot_envelope("", 0, panels, mode="exploration")
            kind = "ui_snapshot"
        else:
            panels = {**_combat_panels(foes_after), "combat_beats": panel}
            env = snapshot_envelope("", 0, panels, mode="combat")
            kind = "ui_update"
        lines = [beat["text"] for beat in beats] + lines_after
        page.evaluate(_PLAY_ROUND, [env, kind, lines])

    def _wait_gesture(self, page, sel: str, gesture: str, timeout: int = 15000) -> dict:
        handle = page.wait_for_function(
            "([sel, g, read]) => { const r = (new Function('return ' + read))()(sel);"
            " return r && r.beat === g ? r : null; }",
            arg=[sel, gesture, _GESTURE_OF],
            timeout=timeout,
            polling="raf",
        )
        return handle.json_value()

    def _stage(self, page) -> dict:
        return page.evaluate(
            "() => { const q = (s) => document.querySelector(s);"
            " const stage = q('[data-testid=\"elosern-stage\"]');"
            " const veil = q('[data-testid=\"stage-combat-veil\"]');"
            " const lineup = q('[data-anchor=\"actor-right\"] > [data-testid=\"foe-lineup\"]');"
            " const map = q('[data-testid=\"local-map\"]');"
            " const view = window.__elosernBridge.store.view;"
            " return {"
            "  mode: stage.getAttribute('data-elosern-mode'),"
            "  hold: stage.getAttribute('data-beat-hold'),"
            "  veil: Number(getComputedStyle(veil).opacity),"
            "  lineup: lineup ? { inert: lineup.inert, hidden: lineup.getAttribute('aria-hidden'),"
            "    leaving: lineup.classList.contains('foes-enter-leave-active'),"
            "    refs: [...lineup.querySelectorAll('[data-testid=\"foe-slot\"]')].map((s) => s.getAttribute('data-portrait-ref')) } : null,"
            "  mapShown: !!map && getComputedStyle(map).display !== 'none' && map.getClientRects().length > 0,"
            "  viewMode: view.mode, viewHold: view.beatHold, phase: (view.beatPlayback || {}).phase || null,"
            " }; }"
        )

    @covers_requirement(
        "webclient-contextual-hud::combat-beats-are-choreographed-on-the-stage-at-the-motion-level",
        "webclient-contextual-hud::vitals-pair-an-icon-a-label-and-numerals-with-a-trailing-damage-bar",
        "webclient-contextual-hud::foes-stand-opposite-the-player-during-combat",
    )
    def test_beat_gestures_full_motion(self):
        """At `full` the player steps in, the foe shakes and flashes with a
        rising number, its gauge follows the displayed value, and the vitals'
        trailing bar waits 300ms."""
        page = self._page(None)
        self.assertEqual(page.evaluate("() => document.documentElement.getAttribute('data-motion')"), "full")
        self._enter_combat(page, [_foe(FOE_A, 30), _foe(FOE_B, 30)])
        self._play(
            page,
            [
                _beat(0, 0, "roll", PLAYER, FOE_A, text="勇者擲出了骰子。"),
                _beat(1, 0, "damage", PLAYER, FOE_A, 12, 18, "勇者擊中了哥布林，造成 12 點傷害。"),
            ],
            terminal=False,
            foes_after=[_foe(FOE_A, 18), _foe(FOE_B, 30)],
            lines_after=[ROUND_CLOSING_LINE],
        )

        lunge = self._wait_gesture(page, PLAYER_ACTOR, "lunge")
        self.assertEqual(lunge["name"], "elosern-beat-lunge-right")
        self.assertEqual(lunge["duration"], "0.24s")
        self.assertIsNone(lunge["float"])

        hit = self._wait_gesture(page, _foe_actor(FOE_A), "hit")
        self.assertEqual(hit["name"], "elosern-beat-hit")
        self.assertEqual(hit["duration"], "0.18s")
        self.assertIsNotNone(hit["float"], hit)
        self.assertEqual(hit["float"]["text"], "−12")
        self.assertEqual(hit["float"]["name"], "elosern-beat-float")
        self.assertEqual(hit["float"]["duration"], "0.6s")
        self.assertEqual(hit["float"]["hidden"], "true")
        # The foe's gauge follows the displayed value (18 of 30).
        width = page.evaluate(
            "(ref) => document.querySelector(`[data-testid=\"foe-slot\"][data-portrait-ref=\"${ref}\"]"
            " .foe-lineup__fill`).style.width",
            FOE_A,
        )
        self.assertEqual(width, "60%")
        # The vitals' trailing bar waits 300ms behind the fill.
        delay = page.evaluate(
            "() => getComputedStyle(document.querySelector("
            "'[data-testid=\"status-panel__gauge--hp\"] .track .ghost')).transitionDelay"
        )
        self.assertIn("0.3s", delay)
        # The round ends by itself and the stage returns to rest.
        wait_for_store_state(page, lambda s: (s.get("beatPlayback") or {}).get("phase") == "done")
        self.assertIsNone(page.evaluate("() => window.__elosernBridge.store.view.beatStage"))
        rest = page.evaluate(_GESTURE_OF, PLAYER_ACTOR)
        self.assertIsNone(rest["beat"])

    @covers_requirement(
        "webclient-contextual-hud::combat-beats-are-choreographed-on-the-stage-at-the-motion-level",
        "webclient-contextual-hud::foes-stand-opposite-the-player-during-combat",
    )
    def test_beat_gestures_reduced(self):
        """At `reduced` nothing steps, shakes, or brightens, no number shows,
        and a defeated foe only fades within 150ms on its own beat."""
        page = self._page("reduced")
        self._enter_combat(page, [_foe(FOE_A, 30), _foe(FOE_B, 30)])
        self._play(
            page,
            [
                _beat(0, 0, "roll", PLAYER, FOE_A, text="勇者擲出了骰子。"),
                _beat(1, 0, "damage", PLAYER, FOE_A, 30, 0, "勇者擊中了哥布林，造成 30 點傷害。"),
                _beat(2, 0, "target_defeated", PLAYER, FOE_A, text="哥布林倒下了。"),
            ],
            terminal=False,
            foes_after=[_foe(FOE_A, 0, "defeated"), _foe(FOE_B, 30)],
            lines_after=[ROUND_CLOSING_LINE],
        )

        lunge = self._wait_gesture(page, PLAYER_ACTOR, "lunge")
        self.assertEqual(lunge["duration"], "0s")
        hit = self._wait_gesture(page, _foe_actor(FOE_A), "hit")
        self.assertEqual(hit["duration"], "0s")
        self.assertIsNotNone(hit["float"], hit)
        self.assertEqual(hit["float"]["opacity"], 0.0, "no number shows at reduced")
        # The committed roster already lost the foe; it still stands until its
        # own defeat beat, which only fades it.
        defeat = self._wait_gesture(page, _foe_actor(FOE_A), "defeat")
        self.assertEqual(defeat["name"], "elosern-beat-defeat")
        self.assertEqual(defeat["duration"], "0.15s")
        self.assertIn(defeat["transform"], ("none", "matrix(1, 0, 0, 1, 0, 0)"))
        # Once the round ends only the committed foe stands.
        wait_for_store_state(page, lambda s: (s.get("beatPlayback") or {}).get("phase") == "done")
        page.wait_for_function(
            "(ref) => { const slots = [...document.querySelectorAll('[data-testid=\"foe-slot\"]')];"
            " return slots.length === 1 && slots[0].getAttribute('data-portrait-ref') === ref; }",
            arg=FOE_B,
        )

    @covers_requirement(
        "webclient-contextual-hud::combat-beats-are-choreographed-on-the-stage-at-the-motion-level",
        "webclient-contextual-hud::surface-visibility-is-gated-by-the-committed-game-mode",
        "webclient-combat-menu::a-combat-round-plays-beat-by-beat",
    )
    def test_terminal_round_holds_the_stage(self):
        """The round that ends the fight commits exploration at once while the
        veil and the inert foes stay until the round ends; a click ends it."""
        page = self._page("reduced")
        self._enter_combat(page, [_foe(FOE_A, 30)])
        self._play(
            page,
            [
                _beat(0, 0, "damage", PLAYER, FOE_A, 30, 0, "勇者擊中了哥布林，造成 30 點傷害。"),
                _beat(1, 0, "target_defeated", PLAYER, FOE_A, text="哥布林倒下了。"),
            ],
            terminal=True,
            foes_after=[],
            lines_after=[VICTORY_LINE],
        )
        s = self._stage(page)
        self.assertEqual(s["mode"], "exploration")
        self.assertEqual(s["viewMode"], "exploration")
        self.assertTrue(s["mapShown"], "the minimap returns at the commit")
        self.assertEqual(s["hold"], "combat")
        self.assertTrue(s["viewHold"])
        self.assertEqual(s["veil"], 1.0)
        self.assertIsNotNone(s["lineup"], "the foes stay on the stage while the round plays")
        self.assertTrue(s["lineup"]["inert"])
        self.assertEqual(s["lineup"]["hidden"], "true")
        self.assertEqual(s["lineup"]["refs"], [FOE_A])

        page.locator('[data-testid="message-window"]').click()
        wait_for_store_state(page, lambda st: (st.get("beatPlayback") or {}).get("phase") == "done")
        s = self._stage(page)
        self.assertIsNone(s["hold"])
        self.assertFalse(s["viewHold"])
        page.wait_for_function(
            "() => !document.querySelector('[data-anchor=\"actor-right\"] > [data-testid=\"foe-lineup\"]')"
        )
        page.wait_for_function(
            "() => Number(getComputedStyle(document.querySelector('[data-testid=\"stage-combat-veil\"]')).opacity) === 0"
        )

    @covers_requirement(
        "webclient-contextual-hud::combat-beats-are-choreographed-on-the-stage-at-the-motion-level",
        "webclient-contextual-hud::surface-visibility-is-gated-by-the-committed-game-mode",
        "webclient-combat-menu::a-combat-round-plays-beat-by-beat",
    )
    def test_terminal_round_at_off_holds_nothing(self):
        """At `off` no round plays by itself, so nothing is held: the veil and
        the foes are gone in the commit's frame."""
        page = self._page("off")
        self._enter_combat(page, [_foe(FOE_A, 30)])
        self._play(
            page,
            [
                _beat(0, 0, "damage", PLAYER, FOE_A, 30, 0, "勇者擊中了哥布林，造成 30 點傷害。"),
                _beat(1, 0, "target_defeated", PLAYER, FOE_A, text="哥布林倒下了。"),
            ],
            terminal=True,
            foes_after=[],
            lines_after=[VICTORY_LINE],
        )
        s = self._stage(page)
        self.assertEqual(s["mode"], "exploration")
        self.assertEqual(s["phase"], "done")
        self.assertIsNone(s["hold"])
        self.assertFalse(s["viewHold"])
        self.assertIsNone(s["lineup"])
        self.assertEqual(s["veil"], 0.0)
        self.assertIsNone(page.evaluate("() => window.__elosernBridge.store.view.beatStage"))
