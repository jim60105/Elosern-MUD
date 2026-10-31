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
//
// Route planning (wilderness-travel-planning-ui, interface design §5/§12).
// The store is the one owner of the destination preview: the hovered cell,
// the locked destination, the current `travel.plan` result, the one
// outstanding query token and the current query's error.
//
// - A hovered disclosed cell beyond the neighbours waits PLAN_DEBOUNCE_MS;
//   a lock asks at once. A newer intent forgets the older request at once
//   (its late result matches nothing) and only the latest desired request
//   is kept; it leaves through `dispatchAction`, the one single-flight
//   sender, when the gate, the layout and a map adopted at the committed
//   node and time admit it. Nothing superseded is ever replayed.
// - A token records the committed facts it was asked for (session, node,
//   party cell, window content, clock, member fatigue and capacity, pace
//   and nightfall stop). A change of any of them forgets the token, the
//   plan and the error; a surviving lock asks once from the new facts, a
//   hovered cell waits for the pointer. Only the token's own result (request
//   id, epoch, asked origin and destination) is adopted, success or error.
//   There is no retry after an error.
// - A lock survives pointer leave, an aim and a stop; it clears on Esc, on a
//   session or layout exit, when the current window no longer discloses it
//   or when the party stands on it. Departure is not inferred from anything
//   here (route-ui owns it).

import { getCurrentScope, onScopeDispose, ref } from "vue";
import { travelSelection } from "../../components/travel/travel-model.js";
import { directionOf, travelTarget } from "../../components/travel/travel-walk-model.js";
import { HOLD_MS, STEP_DWELL_MS } from "../../components/compass-model.js";
import { disabledRowReason } from "../../components/dock-exits.js";
import { decodeTravelGrid, travelCellAt } from "../../lib/travel-grid.js";
import LocalMap from "../../lib/local_map.js";
import { NON_SUCCESS_OUTCOMES } from "./shared.js";

export const TRAVEL_MAP_STATUSES = Object.freeze(["ready", "refreshing", "unavailable", "invalid", "retired"]);

// A walk's closing line when the held bearing has no exit (the compass's
// dead-end wording).
export const DEAD_END_LINE = "這個方向沒有路了，停下腳步。";

const FAILED_MAP = new Set(["unavailable", "invalid", "retired"]);

/** A hovered destination waits this long before its route is asked for. */
export const PLAN_DEBOUNCE_MS = 150;

/**
 * The intent line's stable words for the five planner refusals; every other
 * refusal keeps the server's own message. Nothing is parsed from prose.
 */
export const PLAN_ERROR_TEXT = Object.freeze({
  plan_destination_outside_window: "目的地不在視野範圍內",
  plan_destination_unrevealed: "目的地尚未探明",
  plan_unreachable: "無法抵達那裡",
  plan_too_long: "路線超過 60 步",
  plan_party_cannot_travel: "隊伍目前無法出發",
});
const PLAN_FALLBACK_ERROR = "無法規劃這段路線";

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
    if (body !== ctx.travelMap.area && grid) notePlanningMap(body);
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

  // The canonical current node: the local map's, else the exploration
  // resolver's own fallback. Sent and committed nodes compare like with like.
  function canonicalNode(rs) {
    return localMapNode(rs) ?? ctx.frameResolver.explorationExits().currentNode ?? null;
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

  if (getCurrentScope()) {
    onScopeDispose(() => {
      clearTimers();
      clearTimeout(planTimer);
      planTimer = null;
    });
  }

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
    const sentNode = canonicalNode(rs);
    // The dispatch publishes synchronously; the step is marked as being sent
    // first, so that nested settle neither sends again nor mistakes the
    // missing request id for an absent step.
    walk.pending = { requestId: null, sentNode, epoch: rs.activeEpoch, declared: null, ok: false };
    pumping = true;
    let outcome;
    try {
      outcome = ctx.activateExit(target.exitRef);
    } catch (error) {
      // A failed send never leaves a half-marked step behind.
      walk.pending = null;
      stop("refused");
      return true;
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
    const now = canonicalNode(rs);
    if (now === null || now === pending.sentNode) {
      // Without a declared revision nothing says the step's publication has
      // committed yet: keep waiting for the node.
      if (pending.declared === null) return false;
      // The step's own publication committed and the party did not move: the
      // walk ends quietly (the step was accepted; there is no reason to show).
      return stop("unchanged");
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
      if (ctx.travelSingle && (!rs.connected || ctx.travelSingle.epoch !== rs.activeEpoch)) {
        ctx.travelSingle = null;
      }
      changed = settleSingle(rs) || changed;
      changed = settlePending(rs) || changed;
      if (pump()) {
        changed = true;
        // A result delivered while the step was being sent (a synchronous
        // transport) was skipped by the nested pass; match it now.
        settlePending(committed());
      }
      // The route preview settles after the walk: a walk owns the gate first.
      changed = settlePlan(committed()) || changed;
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
    // A newer aim supersedes an unlocked hover preview; a lock survives it
    // (the aim keeps the intent line and Enter's single step).
    if (next !== null) dropHover();
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

  // ── route planning (wilderness-travel-planning-ui) ─────────────────────

  // The adopted map's identity for planning: a counter that moves only when
  // the window's content (its current node, bounds and runs) changes, so an
  // identical re-adoption (a look, a recovery snapshot) keeps a preview, and
  // the committed time it was adopted at, so a query waits for the map the
  // refresh owner fetches after a time change instead of racing it.
  let mapSerial = 0;
  let mapDigest = null;
  let mapTime = null;
  function notePlanningMap(body) {
    const digest = JSON.stringify([body.current_node, body.window, body.rows]);
    if (digest !== mapDigest) {
      mapDigest = digest;
      mapSerial += 1;
    }
    mapTime = timeKey(committed().serverTime);
  }

  function timeKey(t) {
    return t ? `${t.year}|${t.season_index}|${t.day_in_season}|${t.hour}|${t.minute}|${t.second}` : "";
  }

  // The committed member facts a prediction reads: each traveller's stage,
  // reserve and posture, and the supplied foot capacity.
  function membersKey(status) {
    if (!status || status.available === false) return "";
    const rows = (status.fatigue ?? []).map((r) => `${r.identity}:${r.stage}:${r.reserve_percent}:${r.asleep}`);
    const cap = status.travel_capacity?.capacity;
    const counts = cap ? `${cap.normal},${cap.light},${cap.moderate},${cap.severe}` : "-";
    return `${rows.join(",")}/${counts}`;
  }

  /**
   * The committed facts one query is answered for. Every planner input maps
   * to one field: the session (generation, epoch), the party's position
   * (canonical node and the window's party cell), the revealed window
   * (content serial), the world clock (nightfall), the travellers' fatigue
   * and capacity, and the two preferences. The revision is recorded in the
   * token for diagnostics only: an unrelated publication changes none of
   * these and keeps the preview.
   */
  function planFacts(rs) {
    const party = ctx.travelMap.grid?.party ?? null;
    return {
      generation: rs.generation,
      epoch: rs.activeEpoch,
      node: canonicalNode(rs),
      origin: party ? { x: party.x, y: party.y } : null,
      map: mapSerial,
      time: timeKey(rs.serverTime),
      members: membersKey(rs.panels?.status),
      pace: ctx.prefs.travelPace,
      stopAtNight: ctx.prefs.travelStopAtNight,
    };
  }

  function factsKey(f) {
    const origin = f.origin ? `${f.origin.x},${f.origin.y}` : "";
    return [f.generation, f.epoch, f.node, origin, f.map, f.time, f.members, f.pace, f.stopAtNight].join("|");
  }

  ctx.travelRoute = { hover: null, lockedDestination: null, plan: null, pendingToken: null, error: null };
  const route = ctx.travelRoute;
  // The one latest desired request: `armed` once its debounce elapsed (a
  // lock is armed at once). `basis` is the facts key it was asked at.
  let desired = null;
  let planTimer = null;
  let planSerial = 0;
  // The facts key the current token, plan or error belongs to.
  let planBasis = null;
  // The destination the current token, plan or error answers.
  let planDestination = null;
  let planSession = null;
  let planning = false;

  function sameCell(a, b) {
    return a === b || (!!a && !!b && a.x === b.x && a.y === b.y);
  }

  function clearPlanTimer() {
    clearTimeout(planTimer);
    planTimer = null;
  }

  // A cell of the current window that the window discloses (revealed).
  function disclosed(cell) {
    const found = cell ? travelCellAt(ctx.travelMap.grid, cell.x, cell.y) : null;
    return !!found && found.known;
  }

  // A destination: disclosed and not the party's own cell.
  function lockable(cell) {
    if (!disclosed(cell)) return false;
    const party = ctx.travelMap.grid.party;
    return !sameCell(party, cell);
  }

  // A pointer preview: a lockable cell beyond the eight neighbours.
  function previewable(cell) {
    if (!lockable(cell)) return false;
    const party = ctx.travelMap.grid.party;
    return !party || Math.max(Math.abs(cell.x - party.x), Math.abs(cell.y - party.y)) > 1;
  }

  // Forget the current token, plan and error: a late result of the
  // forgotten request no longer matches anything.
  function dropPreview() {
    planSerial += 1;
    route.pendingToken = null;
    route.plan = null;
    route.error = null;
    planBasis = null;
    planDestination = null;
  }

  function resetPlanning() {
    clearPlanTimer();
    dropPreview();
    desired = null;
    route.hover = null;
    route.lockedDestination = null;
    planSession = null;
  }

  // Drop an unlocked pointer preview (an aim, a walk or a moved party
  // supersedes it; the pointer must move again).
  function dropHover() {
    if (route.lockedDestination) return false;
    const had = route.hover !== null || desired !== null || route.pendingToken !== null || route.plan !== null || route.error !== null;
    clearPlanTimer();
    desired = null;
    route.hover = null;
    dropPreview();
    return had;
  }

  function want(destination, armed) {
    desired = { destination: { x: destination.x, y: destination.y }, armed, basis: factsKey(planFacts(committed())) };
    planSession = sessionKey(committed());
  }

  function planningMapCurrent(rs) {
    return mapCurrent(rs) && mapTime === timeKey(rs.serverTime);
  }

  // Match the outstanding token's own result; true on a change.
  function settlePlanResult(rs) {
    const token = route.pendingToken;
    const result = rs.lastActionResult;
    if (!token || !result || result.requestId !== token.requestId || result.epoch !== token.epoch) return false;
    route.pendingToken = null;
    if (result.outcome === "success") {
      const data = result.data ?? null;
      // Only the answer for the asked origin and destination is this one.
      const own = !!data && sameCell(data.origin, token.origin) && sameCell(data.destination, token.destination);
      route.plan = own ? Object.freeze(data) : null;
      route.error = null;
    } else {
      route.plan = null;
      const stable = PLAN_ERROR_TEXT[result.code];
      route.error = Object.freeze({
        code: result.code,
        message: stable ?? (typeof result.message === "string" && result.message.trim() ? result.message : PLAN_FALLBACK_ERROR),
      });
    }
    return true;
  }

  // Send the latest desired request once everything admits it.
  function flushPlan(rs) {
    if (!desired || !desired.armed || route.pendingToken || planning) return false;
    if (ctx.travelWalk || ctx.travelHold) return false;
    if (rs.mode !== "exploration" || !layoutShown(rs) || !planningMapCurrent(rs) || !gateFree(rs) || surfaceOpen()) return false;
    const destination = desired.destination;
    if (!lockable(destination)) {
      desired = null;
      if (sameCell(route.lockedDestination, destination)) route.lockedDestination = null;
      route.hover = null;
      return true;
    }
    const facts = planFacts(rs);
    const payload = { destination: { x: destination.x, y: destination.y }, pace: facts.pace, stop_at_night: facts.stopAtNight };
    planning = true;
    let requestId = null;
    try {
      requestId = ctx.dispatchAction("travel.plan", payload, null);
    } finally {
      planning = false;
    }
    if (!requestId) return false;
    route.pendingToken = Object.freeze({
      ...facts,
      revision: rs.revision,
      destination: Object.freeze({ ...destination }),
      serial: planSerial,
      requestId,
    });
    planBasis = factsKey(facts);
    planDestination = destination;
    desired = null;
    // A result delivered inside the send (a synchronous transport).
    settlePlanResult(committed());
    return true;
  }

  // Run inside settle(): invalidate, match, then send. True on a change.
  function settlePlan(rs) {
    const anything = route.hover || route.lockedDestination || desired || route.pendingToken || route.plan || route.error;
    if (!anything) return false;
    if (rs.mode !== "exploration" || !layoutShown(rs) || (planSession !== null && planSession !== sessionKey(rs))) {
      resetPlanning();
      return true;
    }
    let changed = false;
    if (!rs.connected) {
      // A reconnect is a new session, which clears the lock as well.
      if (route.pendingToken || route.plan || route.error) changed = true;
      dropPreview();
      changed = dropHover() || changed;
      if (route.lockedDestination) desired = { destination: route.lockedDestination, armed: true, basis: null };
      return changed;
    }
    if ((ctx.travelWalk || ctx.travelHold) && !route.lockedDestination) changed = dropHover() || changed;
    // A lock leaves when the current window no longer discloses it (or the
    // party stands on it); the stale window of a refresh decides nothing.
    if (route.lockedDestination && mapCurrent(rs) && !lockable(route.lockedDestination)) {
      route.lockedDestination = null;
      changed = dropHover() || true;
    }
    const key = factsKey(planFacts(rs));
    if (planBasis !== null && planBasis !== key) {
      dropPreview();
      changed = true;
      if (route.lockedDestination) want(route.lockedDestination, true);
      else changed = dropHover() || changed;
    } else if (desired && desired.basis !== null && desired.basis !== key) {
      // The facts moved while a request waited: a lock asks from the new
      // origin; a hovered cell is no longer under the pointer.
      if (route.lockedDestination) want(route.lockedDestination, true);
      else changed = dropHover() || changed;
    }
    changed = settlePlanResult(rs) || changed;
    changed = flushPlan(rs) || changed;
    return changed;
  }

  function publishPlanning() {
    ctx.publishView();
  }

  /**
   * Preview the route to a hovered cell (null: the pointer left). Only a
   * disclosed cell beyond the neighbours is previewed, after
   * PLAN_DEBOUNCE_MS; a newer cell supersedes the older one at once. While a
   * destination is locked, the lock owns the preview.
   */
  ctx.hoverTravelCell = function hoverTravelCell(cell) {
    if (ctx.travelWalk || ctx.travelHold) return false;
    const next = cell && ctx.travelMap.grid && previewable(cell) ? Object.freeze({ x: cell.x, y: cell.y }) : null;
    if (sameCell(next, route.hover)) return false;
    if (route.lockedDestination) {
      route.hover = next;
      publishPlanning();
      return true;
    }
    clearPlanTimer();
    dropPreview();
    desired = null;
    route.hover = next;
    if (next) {
      // A newer target supersedes the neighbour aim.
      if (ctx.travelAim !== null) setAim(null);
      want(next, false);
      const wanted = desired;
      planTimer = setTimeout(() => {
        planTimer = null;
        if (desired !== wanted) return;
        wanted.armed = true;
        publishPlanning();
      }, PLAN_DEBOUNCE_MS);
    }
    publishPlanning();
    return true;
  };

  /** Lock a disclosed destination and ask for its plan at once. */
  ctx.lockTravelDestination = function lockTravelDestination(cell) {
    if (ctx.travelWalk || ctx.travelHold) return false;
    if (!cell || !ctx.travelMap.grid || !lockable(cell)) return false;
    const destination = Object.freeze({ x: cell.x, y: cell.y });
    route.lockedDestination = destination;
    route.hover = null;
    clearPlanTimer();
    if (ctx.travelAim !== null) setAim(null);
    const answered = sameCell(planDestination, destination) && (route.pendingToken || route.plan || route.error);
    if (answered) {
      // The preview already answers this destination: keep it.
      desired = null;
    } else if (desired && sameCell(desired.destination, destination)) {
      desired.armed = true;
    } else {
      dropPreview();
      want(destination, true);
    }
    planSession = sessionKey(committed());
    publishPlanning();
    return true;
  };

  /** Clear the hover, the lock and the preview (Esc). */
  ctx.clearTravelTarget = function clearTravelTarget() {
    const had = route.hover || route.lockedDestination || desired || route.pendingToken || route.plan || route.error;
    resetPlanning();
    if (had) publishPlanning();
    return !!had;
  };

  function planTargetView() {
    const cell = route.lockedDestination ?? desired?.destination ?? planDestination ?? route.hover;
    if (!cell) return null;
    const found = travelCellAt(ctx.travelMap.grid, cell.x, cell.y);
    const label = found?.known ? found.node?.landmark?.name || found.display?.terrain_label || null : null;
    return Object.freeze({ x: cell.x, y: cell.y, label, locked: sameCell(route.lockedDestination, cell) });
  }

  // ── projection ─────────────────────────────────────────────────────────

  function aimTargetView(rs) {
    const key = ctx.travelAim;
    if (!key) return null;
    const d = directionOf(key);
    const target = targetFor(key, rs);
    return Object.freeze({
      direction: key,
      word: d.word,
      // The committed row's opaque reference: the leg panel looks up the
      // server's duration quote for exactly this row.
      exitRef: target ? target.exitRef : null,
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

  function travelCapacity(status) {
    if (!status) return undefined;
    if (status.available === false) return null;
    return status.travel_capacity ?? null;
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
      // The typed travel band log (wilderness-travel-log-ui).
      entries: ctx.travelLogEntries(),
      // The leg panel (wilderness-travel-leg-ui): the persisted travel
      // preferences and the status v6 travel capacity — the object, null
      // when the server supplies none or the status panel is unavailable,
      // undefined while no status is committed.
      preferences: Object.freeze({ pace: ctx.prefs.travelPace, stopAtNight: ctx.prefs.travelStopAtNight }),
      capacity: travelCapacity(rs.panels?.status),
      // The route preview (wilderness-travel-planning-ui): the hovered and
      // locked destinations, the current plan exactly as the server sent
      // it, whether a query waits or flies, and the current query's error.
      hover: route.hover,
      lockedDestination: route.lockedDestination,
      planTarget: selection.layout ? planTargetView() : null,
      plan: route.plan,
      planPending: route.pendingToken !== null || desired !== null,
      planError: route.error,
    });
  };
}
