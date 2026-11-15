// The rite group of the composed Elosern store (OpenSpec change
// landmark-rite-store; design §12.2): the client-local presentation state of
// a landmark rite, published as `view.rite`.
//
// Phases: closed -> card -> stage -> closed, with the card reopened from the
// return entry as a revisit.
//
// - The card opens when the committed `rite` panel becomes available for a
//   district not seen available in this session (`generation|epoch`). The
//   first snapshot of a session never opens it: a reconnect on a landmark
//   shows the return entry instead.
// - Opening, approaching and leaving are local and send nothing. Performing
//   sends exactly one `explore.landmark_rite {option, member_id}` and adopts
//   only that request's own result.
// - The performer (landmark-rite-performer-picking D1) is one row of the
//   panel's `performers`, picked on the stage. It is the controlled
//   character (`"self"`) on every entry to the stage, and returns to it when
//   the picked row leaves the panel or picking stops being offered.
// - An open card or stage is one more centred card: it stops walking and the
//   compass as the camp card does.
// - The state resets when the panel becomes unavailable, the mode leaves
//   exploration or the session changes.

import { ritePerformers } from "../../components/rite/rite-model.js";

function closedPresentation() {
  return {
    phase: "closed",
    revisit: false,
    pending: null, // { requestId, epoch, generation }
    delivery: null,
    playing: false,
    performerId: "self", // the `id` of one ritePerformers(panel) row
  };
}

// Picking is offered only when there is someone else to pick and something
// a companion may perform.
function switchable(panel) {
  return (
    panel !== null &&
    panel.performers.length > 1 &&
    panel.options.some((option) => option.companion === true)
  );
}

export function applyRite(ctx) {
  let state = closedPresentation();
  let panel = null; // the committed, available `rite` panel
  let seenKey = null; // the district key last seen available in this session
  let hydrated = false; // the session's first committed state was processed
  let session = null; // `generation|epoch`, or null before any snapshot

  function committed() {
    return ctx.reducer.getCommittedState();
  }

  function resetPresentation() {
    state = closedPresentation();
  }

  // The previous predicate keeps owning the presence, room and camp cards;
  // an open rite card or stage is one more centred card.
  const centred = ctx.centredCardOpen;
  ctx.centredCardOpen = function centredCardOpen() {
    return centred() || state.phase !== "closed";
  };

  function adopt(rs) {
    const pending = state.pending;
    const result = rs.lastActionResult;
    if (!pending || !result || result.requestId !== pending.requestId || result.epoch !== pending.epoch) return;
    state.pending = null;
    const delivery = result.data?.delivery;
    if (result.outcome === "success" && delivery !== null && typeof delivery === "object" && !Array.isArray(delivery)) {
      state.delivery = delivery;
      state.playing = true;
    }
    // Any other outcome plays nothing: the recognized-result handler already
    // wrote the server's message to the log.
  }

  /** Run inside publishView, before the view is built. */
  ctx.settleRite = function settleRite(rs) {
    const key = rs.activeEpoch == null ? null : `${rs.generation}|${rs.activeEpoch}`;
    if (key !== session) {
      session = key;
      hydrated = false;
      seenKey = null;
      panel = null;
      resetPresentation();
    }
    if (key === null) return;
    const candidate = rs.panels?.rite;
    panel = candidate && candidate.available === true ? candidate : null;
    if (panel === null || rs.mode !== "exploration") {
      resetPresentation();
      if (panel === null) {
        seenKey = null;
      } else if (!hydrated) {
        // A session that begins outside exploration on a landmark is a
        // reconnect too: its later return to exploration opens nothing.
        seenKey = panel.district.key;
      }
      hydrated = true;
      return;
    }
    if (panel.district.key !== seenKey) {
      seenKey = panel.district.key;
      if (hydrated && state.phase === "closed") {
        state.phase = "card";
        state.revisit = false;
      }
    }
    hydrated = true;
    adopt(rs);
    if (!switchable(panel) || !ritePerformers(panel).some((row) => row.id === state.performerId)) {
      state.performerId = "self";
    }
  };

  ctx.riteView = function riteView() {
    return Object.freeze({
      panel,
      phase: state.phase,
      revisit: state.revisit,
      pending: state.pending !== null,
      delivery: state.delivery,
      playing: state.playing,
      performerId: state.performerId,
      canSwitch: switchable(panel),
    });
  };

  // The rows a pick may land on, or null while picking is not open: only on
  // the stage, with picking offered, and while nothing is pending or playing.
  function pickableRows() {
    if (state.phase !== "stage" || state.pending || state.playing || !switchable(panel)) return null;
    return ritePerformers(panel);
  }

  function setPerformer(id) {
    if (id === state.performerId) return true;
    state.performerId = id;
    ctx.publishView();
    return true;
  }

  /** Pick a listed performer by its row id. Sends nothing. */
  ctx.pickRitePerformer = function pickRitePerformer(id) {
    const rows = pickableRows();
    if (rows === null || !rows.some((row) => row.id === id)) return false;
    return setPerformer(id);
  };

  /** Step to the next (delta > 0) or previous listed performer, wrapping. */
  ctx.stepRitePerformer = function stepRitePerformer(delta) {
    const rows = pickableRows();
    if (rows === null || !Number.isFinite(delta) || delta === 0) return false;
    const index = Math.max(0, rows.findIndex((row) => row.id === state.performerId));
    const next = (index + Math.sign(delta) + rows.length) % rows.length;
    return setPerformer(rows[next].id);
  };

  /** Reopen the card from the return entry. Sends nothing. */
  ctx.openRiteCard = function openRiteCard() {
    if (panel === null || state.phase !== "closed") return false;
    state.phase = "card";
    state.revisit = true;
    ctx.publishView();
    return true;
  };

  /** 走近: enter the rite stage. Sends nothing. */
  ctx.approachRite = function approachRite() {
    if (state.phase !== "card") return false;
    state.phase = "stage";
    state.performerId = "self";
    ctx.publishView();
    return true;
  };

  /** 退開: close the card or the stage. Sends nothing. */
  ctx.leaveRite = function leaveRite() {
    if (state.phase === "closed" || state.playing || state.pending) return false;
    resetPresentation();
    ctx.publishView();
    return true;
  };

  /**
   * Perform one listed option as the picked performer: exactly one
   * `explore.landmark_rite`. A companion never sends an option that does not
   * admit one.
   */
  ctx.performRite = function performRite(optionKey) {
    if (state.phase !== "stage" || state.pending || state.playing || panel === null) return false;
    const option = panel.options.find((candidate) => candidate.key === optionKey);
    if (!option) return false;
    const performer = ritePerformers(panel).find((row) => row.id === state.performerId);
    if (!performer || (!performer.self && option.companion !== true)) return false;
    const rs = committed();
    if (!rs.connected || rs.phase !== "active" || ctx.inFlight || rs.mutationsLocked) return false;
    const requestId = ctx.dispatchAction(
      "explore.landmark_rite",
      { option: optionKey, member_id: performer.memberId ?? null },
      null,
    );
    if (!requestId) return false;
    state.pending = Object.freeze({ requestId, epoch: rs.activeEpoch, generation: rs.generation });
    ctx.publishView();
    return true;
  };

  /** The delivery's scene finished: back to the stage's options. */
  ctx.finishRiteScene = function finishRiteScene() {
    if (!state.playing) return false;
    state.playing = false;
    state.delivery = null;
    ctx.publishView();
    return true;
  };
}
