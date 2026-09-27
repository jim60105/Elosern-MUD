// The combat beat playback group of the composed Elosern store
// (docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md
// §10.2; OpenSpec change webclient-combat-beat-queue, design D5/D8).
//
// The store — not a composable — owns the playback, because the lock it holds
// must gate `dispatchAction` and the keyboard router (both live here), while
// three components read the projected slice (MessageWindow, VitalsTrack,
// ParticipantFrame). The window reports only "this beat is fully shown":
// typing speed and the fit test are its own.
//
// One round binds per (epoch, round id), and only to the dispatch that
// produced it: the response mark recorded on the in-flight record is the one
// thing that links a request, its response, and its panel (the text arrives
// before the panel, so timing cannot bind it). A round seen in any other way
// — a reconnect, a retained panel, another player's action — is never
// presented, and no round is presented twice.
import {
  actMs,
  beatHoldFor,
  beatReducer,
  displayHpFor,
  planRound,
  stageFor,
} from "../../lib/beat_queue.js";
import { readMotionMs } from "../../lib/motion_tokens.js";

// The player's own actions a completed round can belong to (C12 D3).
const BEAT_ACTIONS = new Set(["combat.cast", "combat.flee", "inventory.use"]);

export function applyBeats(ctx) {
  // The live playback: null, or `beatReducer`'s {plan, index, phase}.
  ctx.beatState = null;
  // The last (epoch, round) this client has seen, so a retained panel or a
  // replay never plays a round twice. Recorded even when nothing binds.
  ctx.lastBeatRound = { epoch: null, round: null };
  // The single pending timer: the current step's act (its stage gesture,
  // webclient-combat-beat-choreography D2) or its beat pause.
  let beatTimer = null;

  function clearBeatTimer() {
    if (beatTimer !== null) {
      clearTimeout(beatTimer);
      beatTimer = null;
    }
  }

  // The playback lock: true exactly while a round plays by itself.
  ctx.beatLocked = function beatLocked() {
    return !!ctx.beatState && ctx.beatState.phase !== "done";
  };

  // The published slice (design D5). `texts` carries the beat texts, so the
  // window never needs the plan's server-side fields.
  ctx.beatPlaybackView = function beatPlaybackView() {
    const state = ctx.beatState;
    if (!state) {
      return null;
    }
    const { plan } = state;
    return {
      round: plan.round,
      startSeq: plan.startSeq,
      auto: plan.auto,
      index: state.index,
      count: plan.steps.length,
      phase: state.phase,
      texts: plan.steps.map((step) => step.text),
      coveredLines: plan.coveredLines,
      terminal: plan.terminal,
    };
  };

  // The hit points the playback displays, or null whenever nothing plays (the
  // surfaces then read the committed values).
  ctx.displayHpView = function displayHpView() {
    return displayHpFor(ctx.beatState);
  };

  // The stage while a round plays (webclient-combat-beat-choreography D3):
  // the gestures, the pre-round foes, and the defeated keys, or null.
  ctx.beatStageView = function beatStageView() {
    return stageFor(ctx.beatState);
  };

  // The terminal-round hold (D6): true while a round whose publication
  // already committed another mode plays by itself.
  ctx.beatHoldView = function beatHoldView() {
    return beatHoldFor(ctx.beatState);
  };

  // A new transport generation or a detach ends the round without presenting
  // the rest. Called from `handleTransportLifecycle`, inside a publish: it
  // mutates state only, and that publish projects the cleared slice.
  ctx.resetBeats = function resetBeats() {
    clearBeatTimer();
    ctx.beatState = null;
    ctx.lastBeatRound = { epoch: null, round: null };
  };

  // Runs in `publishView` right after `releaseIfReady`. `prev` is the previous
  // committed view (the pre-round roster and status — a terminal round's
  // `context_actions` is already the exploration kind), `rs` the committed
  // reducer state, and `flight` the in-flight record captured before the
  // release, because the result can land in the same tick.
  ctx.syncBeatRound = function syncBeatRound(prev, rs, flight) {
    const panel = rs.panels && rs.panels.combat_beats;
    if (!panel || panel.available !== true || typeof panel.round !== "string") {
      return;
    }
    const epoch = rs.activeEpoch;
    if (ctx.lastBeatRound.epoch === epoch && ctx.lastBeatRound.round === panel.round) {
      return;
    }
    // Recorded either way: a round the client cannot bind now is never
    // presented later.
    ctx.lastBeatRound = { epoch, round: panel.round };
    if (!flight || !BEAT_ACTIONS.has(flight.actionId)) {
      return;
    }
    if (typeof flight.responseMark !== "number") {
      return;
    }
    const statusPanel = prev && prev.panels ? prev.panels.status : null;
    const resources = statusPanel && statusPanel.resources;
    const actor = statusPanel && statusPanel.actor;
    const plan = planRound({
      panel,
      roster: prev ? prev.combatParticipants : [],
      statusHp: resources && resources.hp ? resources.hp.current : null,
      playerKey: actor ? actor.identity : null,
      level: ctx.effectiveMotionLevel(),
      startSeq: flight.responseMark,
      terminal: rs.mode !== "combat",
    });
    if (!plan) {
      return;
    }
    clearBeatTimer();
    ctx.beatState = beatReducer(null, { type: "start", plan });
  };

  // The window's "the current beat's page is fully shown" report: the beat's
  // hit points apply, then the round advances after the beat pause.
  ctx.beatShown = function beatShown(index) {
    if (!ctx.beatState) {
      return;
    }
    const next = beatReducer(ctx.beatState, { type: "shown", index });
    if (next === ctx.beatState) {
      return;
    }
    ctx.beatState = next;
    clearBeatTimer();
    if (next.phase === "act") {
      // The step's gesture plays; the pause starts once the longest one has
      // played (D2). A step that plays none goes straight to its pause.
      const wait = actMs(next, readMotionMs);
      if (wait > 0) {
        beatTimer = setTimeout(() => {
          beatTimer = null;
          ctx.beatState = beatReducer(ctx.beatState, { type: "acted" });
          armPause();
          ctx.publishView();
        }, wait);
      } else {
        ctx.beatState = beatReducer(ctx.beatState, { type: "acted" });
        armPause();
      }
    }
    ctx.publishView();
  };

  // Arms the beat pause once the state is in its pause phase. The wait is
  // read when it starts, so a level change applies from the next wait, and a
  // missing token resolves to 0 (never holds the lock).
  function armPause() {
    if (!ctx.beatState || ctx.beatState.phase !== "pause") {
      return;
    }
    beatTimer = setTimeout(() => {
      beatTimer = null;
      ctx.beatState = beatReducer(ctx.beatState, { type: "paused" });
      ctx.publishView();
    }, readMotionMs("--motion-beat"));
  }

  function endRound(type) {
    if (!ctx.beatState) {
      return;
    }
    clearBeatTimer();
    const next = beatReducer(ctx.beatState, { type });
    if (next === ctx.beatState) {
      return;
    }
    ctx.beatState = next;
    ctx.publishView();
  }

  // The player ended the round (a click or a key on the message window).
  ctx.skipBeats = function skipBeats() {
    endRound("skip");
  };

  // A new player action flushes the round's queued steps before its own
  // response starts (a typed command, and anything else that must not wait).
  ctx.flushBeats = function flushBeats() {
    endRound("flush");
  };
}
