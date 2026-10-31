// The travel group of the composed Elosern store (OpenSpec changes
// wilderness-travel-interface and wilderness-travel-walking-ui): the committed
// travel selection, the active stage's map state, and the neighbour aim and
// held-walk queue, published as `view.travel`.
//
// - The selection (`mode`, `layout`, `room`) is a pure projection of the
//   committed state (components/travel/travel-model.js); nothing selects it
//   from prose, a click or a cached scene.
// - The map state is written by the one refresh owner
//   (composables/use-travel-map.js) through `setTravelMap`: its status
//   (ready | refreshing | unavailable | invalid | retired) and the area body
//   it last adopted from a correlated complete response. `map` is that body's
//   decoded grid and `mapReady` is true only at `ready`.
// - The recovery signal records every accepted full snapshot (an external
//   server snapshot or an explicit sync's completion) at the transport
//   acceptance seam, so the refresh owner can ask for the area once even
//   when position and time did not change. On-demand maps always arrive on
//   `ui_update`, so the owner's own map completions never raise it.
//
// Walking (wilderness-travel-walking-ui, interface design §5/§6). The store
// is the one owner of the aim, the 400 ms hold, the single pending step and
// the dwell; components emit intents and never keep a second queue.
//
// - The aim is a canonical direction word. It persists until cleared and is
//   resolved on demand against the committed exit rows through the compass
//   model (components/travel/travel-walk-model.js): no exit, destination or
//   route is ever manufactured.
// - Every step leaves through `activateExit` with its unchanged
//   `{exit_ref, current_node}` payload, re-resolved at the moment it is sent.
// - One pending `explore.move`. It counts only once its own result (request
//   id, epoch) succeeded AND the committed revision reached the revision that
//   result declared, in the same epoch, AND the canonical current node
//   changed from the one the step was sent from. Result and publication may
//   arrive in either order; a foreign result, an unrelated revision, a
//   same-node republication or a free dispatch gate never acknowledges.
// - After each counted step the walk waits STEP_DWELL_MS (0 at motion off)
//   and a current map: the refresh owner's `ready` for the map of the
//   committed node. `refreshing` is ordinary waiting; `unavailable`,
//   `invalid` and `retired` stop the walk and never resume it.
// - A stop never sends and never resends: a step already sent is left to the
//   transport's single-flight gate, and its late commit only updates the
//   committed state.

import { getCurrentScope, onScopeDispose, ref } from "vue";
import { travelSelection } from "../../components/travel/travel-model.js";
import { directionOf, travelTarget } from "../../components/travel/travel-walk-model.js";
import { HOLD_MS, STEP_DWELL_MS } from "../../components/compass-model.js";
import { disabledRowReason } from "../../components/dock-exits.js";
import { decodeTravelGrid } from "../../lib/travel-grid.js";
import LocalMap from "../../lib/local_map.js";
import { NON_SUCCESS_OUTCOMES } from "./shared.js";

export const TRAVEL_MAP_STATUSES = Object.freeze(["ready", "refreshing", "unavailable", "invalid", "retired"]);

// A walk's closing line when the held bearing has no exit (the compass's
// dead-end wording).
export const DEAD_END_LINE = "這個方向沒有路了，停下腳步。";

const FAILED_MAP = new Set(["unavailable", "invalid", "retired"]);

export function applyTravel(ctx) {
  ctx.travelMap = { status: "refreshing", area: null, grid: null };
  ctx.travelRecovery = ref(null);

  ctx.travelAim = null;
  ctx.travelHold = null; // { direction, timer, generation, epoch }
  ctx.travelWalk = null; // see `startWalk`
  ctx.travelSingle = null; // { requestId, epoch } of a discrete step
  ctx.travelNotice = null; // { kind, message }
  let dwellTimer = null;
  let aimSession = null;
  let pumping = false;
  let settling = false;

  ctx.setTravelMap = function setTravelMap({ status, area }) {
    if (!TRAVEL_MAP_STATUSES.includes(status)) return;
    const body = area ?? null;
    if (ctx.travelMap.status === status && ctx.travelMap.area === body) return;
    // The grid is decoded once per adopted body, not once per publication.
    const grid = body === ctx.travelMap.area ? ctx.travelMap.grid : decodeTravelGrid(body);
    ctx.travelMap = { status, area: body, grid };
    ctx.publishView();
  };

  ctx.noteRecoveryPublication = function noteRecoveryPublication(generation, epoch, revision) {
    ctx.travelRecovery.value = Object.freeze({ generation, epoch, revision });
  };

  // ── committed facts ────────────────────────────────────────────────────

  function committed() {
    return ctx.reducer.getCommittedState();
  }

  function sessionKey(rs) {
    return `${rs.generation}|${rs.activeEpoch}`;
  }

  // Every aim belongs to the session it was taken in.
  function setAim(key) {
    ctx.travelAim = key;
    aimSession = key === null ? null : sessionKey(committed());
  }

  function localMapNode(rs) {
    const node = rs.panels?.local_map?.current_node;
    return typeof node === "string" && node ? node : null;
  }

  function layoutShown(rs) {
    return travelSelection({ mode: rs.mode, panels: rs.panels || {}, creation: ctx.creation != null }).layout;
  }

  // The committed target the direction aims at, re-resolved now.
  function targetFor(direction, rs = committed()) {
    const { rows, currentNode } = ctx.frameResolver.explorationExits();
    const panel = rs.panels?.local_map;
    const model = panel ? LocalMap.reducePanel(panel) : null;
    return travelTarget(direction, rows, model, currentNode);
  }

  // The map is current: the owner reports `ready` and, where both sides name
  // a node, the adopted window is the committed node's.
  function mapCurrent(rs) {
    if (ctx.travelMap.status !== "ready") return false;
    const shown = ctx.travelMap.grid?.currentNode ?? null;
    const here = localMapNode(rs);
    return shown === null || here === null || shown === here;
  }

  function gateFree(rs) {
    return (
      rs.connected &&
      rs.phase === "active" &&
      !rs.mutationsLocked &&
      !ctx.inFlight &&
      !ctx.beatLocked() &&
      !ctx.explorationSubmitLocked()
    );
  }

  function ready(rs) {
    return rs.mode === "exploration" && layoutShown(rs) && mapCurrent(rs) && gateFree(rs);
  }

  // A surface that owns input over the stage: any of these stops a walk.
  function surfaceOpen() {
    return (
      ctx.hudDrawer.value != null ||
      ctx.hudOverlay.value != null ||
      ctx.presenceCard != null ||
      ctx.centredCardOpen?.() === true ||
      ctx.partyExitPrompt != null ||
      ctx.crossSideConfirm != null
    );
  }

  // The reason the current state cannot carry a walk, or null.
  function cancelReason(rs, session) {
    if (!rs.connected) return "disconnect";
    if (session && (rs.generation !== session.generation || rs.activeEpoch !== session.epoch)) return "epoch";
    // A recovery episode that failed (or a detached phase) never resumes;
    // an ordinary pending repair (a result that named its publication before
    // it arrived) only locks the gate until that publication commits.
    if (rs.phase !== "active" || rs.recovery?.status === "failed") return "locked";
    if (rs.mode !== "exploration" || !layoutShown(rs)) return "layout";
    if (surfaceOpen()) return "surface";
    if (FAILED_MAP.has(ctx.travelMap.status)) return "map";
    return null;
  }

  // ── timers ─────────────────────────────────────────────────────────────

  function clearHold() {
    if (ctx.travelHold) clearTimeout(ctx.travelHold.timer);
    ctx.travelHold = null;
  }

  function clearDwell() {
    clearTimeout(dwellTimer);
    dwellTimer = null;
  }

  function clearTimers() {
    clearHold();
    clearDwell();
  }

  if (getCurrentScope()) onScopeDispose(clearTimers);

  // ── the queue ──────────────────────────────────────────────────────────

  function stop(reason, notice = null) {
    const had = ctx.travelWalk !== null || ctx.travelHold !== null;
    clearTimers();
    ctx.travelWalk = null;
    if (notice) ctx.travelNotice = notice;
    return had || notice !== null;
  }

  function startWalk(direction, rs) {
    ctx.travelWalk = {
      kind: "direction",
      direction,
      departedPlan: null,
      progress: 0,
      pending: null, // { requestId, sentNode, epoch, declared, ok }
      commitSeen: false,
      dwellUntil: null,
      generation: rs.generation,
      epoch: rs.activeEpoch,
    };
  }

  function dwellMs() {
    return ctx.effectiveMotionLevel() === "off" ? 0 : STEP_DWELL_MS;
  }

  // Send the next step when nothing waits; returns true when state changed.
  function pump() {
    const walk = ctx.travelWalk;
    if (!walk || walk.pending || pumping) return false;
    if (walk.dwellUntil !== null) {
      const left = walk.dwellUntil - Date.now();
      if (left > 0) {
        if (!dwellTimer) {
          dwellTimer = setTimeout(() => {
            dwellTimer = null;
            ctx.publishView();
          }, left);
        }
        return false;
      }
    }
    const rs = committed();
    if (!ready(rs)) return false;
    const target = targetFor(walk.direction, rs);
    if (!target) return stop("blocked", { kind: "blocked", message: DEAD_END_LINE });
    if (!target.enabled) {
      return stop("blocked", { kind: "blocked", message: target.reason || disabledRowReason(target.item) || DEAD_END_LINE });
    }
    const sentNode = localMapNode(rs) ?? ctx.frameResolver.explorationExits().currentNode;
    // The dispatch publishes synchronously; the step is marked as being sent
    // first, so that nested settle neither sends again nor mistakes the
    // missing request id for an absent step.
    walk.pending = { requestId: null, sentNode, epoch: rs.activeEpoch, declared: null, ok: false };
    pumping = true;
    let outcome;
    try {
      outcome = ctx.activateExit(target.exitRef);
    } finally {
      pumping = false;
    }
    if (ctx.travelWalk !== walk) return true;
    if (outcome.sent) {
      walk.pending.requestId = outcome.requestId;
      walk.dwellUntil = null;
      return true;
    }
    walk.pending = null;
    if (outcome.reason === "locked") return false;
    return stop("refused", outcome.reason === "disabled" ? { kind: "blocked", message: disabledRowReason(outcome.item) || DEAD_END_LINE } : null);
  }

  // Match the pending step against the committed state; true on a change.
  function settlePending(rs) {
    const walk = ctx.travelWalk;
    const pending = walk?.pending;
    if (!pending || pending.requestId === null) return false;
    const result = rs.lastActionResult;
    if (!pending.ok && result && result.requestId === pending.requestId && result.epoch === pending.epoch) {
      if (NON_SUCCESS_OUTCOMES.includes(result.outcome)) {
        return stop("refused", { kind: "refused", message: result.message || null });
      }
      if (result.outcome === "success") {
        pending.ok = true;
        pending.declared = typeof result.presentationRevision === "number" ? result.presentationRevision : null;
      }
    }
    if (!pending.ok || rs.activeEpoch !== pending.epoch) return false;
    if (pending.declared !== null && (rs.revision === null || rs.revision < pending.declared)) return false;
    const now = localMapNode(rs);
    if (now === null || now === pending.sentNode) {
      // The step's own publication committed and the party did not move.
      return stop("unchanged", { kind: "blocked", message: DEAD_END_LINE });
    }
    walk.progress += 1;
    walk.pending = null;
    walk.commitSeen = true;
    walk.dwellUntil = Date.now() + dwellMs();
    return true;
  }

  function settleSingle(rs) {
    const single = ctx.travelSingle;
    if (!single) return false;
    const result = rs.lastActionResult;
    if (!result || result.requestId !== single.requestId || result.epoch !== single.epoch) return false;
    ctx.travelSingle = null;
    if (NON_SUCCESS_OUTCOMES.includes(result.outcome)) {
      ctx.travelNotice = { kind: "refused", message: result.message || null };
    }
    return true;
  }

  // Run at the end of every publication (and by the actions): cancel,
  // match, then send. Returns true when the travel projection must be
  // republished.
  function settle() {
    if (settling) return false;
    settling = true;
    try {
      const rs = committed();
      let changed = false;
      const session = ctx.travelWalk ?? ctx.travelHold;
      if (session) {
        const reason = cancelReason(rs, session);
        if (reason) changed = stop(reason) || changed;
      }
      if (
        ctx.travelAim !== null &&
        (!rs.connected || rs.mode !== "exploration" || !layoutShown(rs) || aimSession !== sessionKey(rs))
      ) {
        ctx.travelAim = null;
        changed = true;
      }
      changed = settleSingle(rs) || changed;
      changed = settlePending(rs) || changed;
      if (pump()) {
        changed = true;
        // A result delivered while the step was being sent (a synchronous
        // transport) was skipped by the nested pass; match it now.
        settlePending(committed());
      }
      return changed;
    } finally {
      settling = false;
    }
  }

  // Called by publishView after the view is built: republish once when the
  // queue changed what the projection shows.
  ctx.settleTravel = function settleTravel() {
    if (settle()) ctx.view.value = { ...ctx.view.value, travel: ctx.travelView(committed()) };
  };

  // ── actions ────────────────────────────────────────────────────────────

  // publishView settles the queue after it builds the view.
  function after() {
    ctx.publishView();
  }

  /** Aim at a neighbour direction (null clears); never sends. */
  ctx.aimTravel = function aimTravel(direction) {
    const next = direction === null || direction === undefined ? null : directionOf(direction)?.key ?? null;
    if (direction != null && next === null) return false;
    setAim(next);
    ctx.travelNotice = null;
    ctx.publishView();
    return true;
  };

  /** One guarded neighbour step toward `direction` (default: the aim). */
  ctx.stepTravel = function stepTravel(direction) {
    if (ctx.travelWalk || ctx.travelHold) return { sent: false, reason: "walking" };
    const key = direction == null ? ctx.travelAim : directionOf(direction)?.key ?? null;
    if (!key) return { sent: false, reason: "no-aim" };
    setAim(key);
    ctx.travelNotice = null;
    const rs = committed();
    if (!ready(rs) || surfaceOpen()) {
      ctx.publishView();
      return { sent: false, reason: "waiting" };
    }
    const target = targetFor(key, rs);
    if (!target || !target.enabled) {
      ctx.travelNotice = { kind: "blocked", message: target ? target.reason || DEAD_END_LINE : DEAD_END_LINE };
      ctx.publishView();
      return { sent: false, reason: "blocked" };
    }
    const outcome = ctx.activateExit(target.exitRef);
    if (outcome.sent) {
      ctx.travelSingle = { requestId: outcome.requestId, epoch: rs.activeEpoch };
      after();
      return { sent: true, requestId: outcome.requestId };
    }
    ctx.publishView();
    return { sent: false, reason: outcome.reason };
  };

  /** Arm (or keep arming) a held walk toward `direction`. */
  ctx.holdTravel = function holdTravel(direction) {
    const key = directionOf(direction)?.key ?? null;
    if (!key) return false;
    setAim(key);
    ctx.travelNotice = null;
    if (ctx.travelWalk) {
      ctx.publishView();
      return false;
    }
    const rs = committed();
    if (ctx.travelHold) {
      ctx.travelHold.direction = key;
    } else {
      const hold = { direction: key, timer: null, generation: rs.generation, epoch: rs.activeEpoch };
      hold.timer = setTimeout(() => {
        if (ctx.travelHold !== hold) return;
        ctx.travelHold = null;
        const now = committed();
        if (cancelReason(now, hold)) {
          ctx.publishView();
          return;
        }
        startWalk(hold.direction, now);
        after();
      }, HOLD_MS);
      ctx.travelHold = hold;
    }
    ctx.publishView();
    return true;
  };

  /** Release the held input: a short press only aimed; a walk stops. */
  ctx.releaseTravel = function releaseTravel() {
    if (stop("release")) ctx.publishView();
  };

  /** Stop the walk (停步, a key, blur, an opened surface). */
  ctx.stopTravel = function stopTravel(reason = "stop") {
    if (stop(reason)) ctx.publishView();
  };

  // ── projection ─────────────────────────────────────────────────────────

  function aimTargetView(rs) {
    const key = ctx.travelAim;
    if (!key) return null;
    const d = directionOf(key);
    const target = targetFor(key, rs);
    return Object.freeze({
      direction: key,
      word: d.word,
      exists: !!target,
      enabled: !!target && target.enabled,
      reason: target && !target.enabled ? target.reason || null : null,
    });
  }

  function walkingView() {
    const walk = ctx.travelWalk;
    if (!walk) return null;
    let waiting = "gate";
    if (walk.pending) waiting = "commit";
    else if (walk.dwellUntil !== null && walk.dwellUntil > Date.now()) waiting = "dwell";
    else if (ctx.travelMap.status !== "ready") waiting = "map";
    return Object.freeze({
      kind: walk.kind,
      direction: walk.direction,
      word: directionOf(walk.direction)?.word ?? "",
      progress: walk.progress,
      waiting,
    });
  }

  ctx.travelView = function travelView(rs) {
    const selection = travelSelection({
      mode: rs.mode,
      panels: rs.panels || {},
      creation: ctx.creation != null,
    });
    return Object.freeze({
      ...selection,
      map: ctx.travelMap.grid,
      mapReady: ctx.travelMap.status === "ready",
      mapStatus: ctx.travelMap.status,
      area: ctx.travelMap.area,
      aim: ctx.travelAim,
      aimTarget: selection.layout ? aimTargetView(rs) : null,
      walking: walkingView(),
      holding: ctx.travelHold !== null,
      notice: ctx.travelNotice ? Object.freeze({ ...ctx.travelNotice }) : null,
    });
  };
}
