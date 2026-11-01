// The camp group of the composed Elosern store (OpenSpec change
// wilderness-camping; design §5): the one client-local camp card and its
// campfire beat, published as `view.camp`.
//
// State machine: closed -> previewPending -> choosing | refused ->
// submitting -> dream | beat -> closed.
//
// - Opening stops any walk through the travel store's public stop and asks
//   for the read-only `explore.camp_preview` once the single-flight gate is
//   free, so a move already admitted commits first. Opening and cancelling
//   never send `explore.camp`.
// - Only the token's own result (request id, epoch and the session it was
//   asked in) is adopted. A disconnect, an epoch or generation change, or
//   leaving exploration discards the card and never re-submits.
// - Every value the card shows is the server's: modes, refusals, wake times,
//   reserves and dream eligibility. The dream checkbox is unchecked on every
//   opening and cleared whenever the selected mode cannot offer it.
// - Confirmation sends exactly one `explore.camp {mode, dream}`; a refusal
//   returns to the card with the server reason, a dream entry hands over to
//   the existing dream stage, and a settled camp becomes the beat.
// - The forced-walking-sleep handoff shortcut: a sleep-control view that
//   first appears while a walk is active is remembered by its transition id,
//   so the handoff menu can prepend 全員紮營 for exactly that view.

const OPEN_PHASES = new Set(["previewPending", "choosing", "refused", "submitting", "beat"]);

function closedState() {
  return {
    phase: "closed",
    opener: null,
    preview: null,
    selected: null,
    dream: false,
    refusal: null,
    result: null,
    message: null,
    pending: null, // { kind: "preview" | "camp", requestId, epoch, generation }
    wantPreview: false,
    session: null,
    openCount: 0,
  };
}

export function applyCamp(ctx) {
  ctx.campState = closedState();
  let openings = 0;
  let walkHandoff = null; // the sleep-control transition id a walk ran into
  let lastHandoffId = null;

  function committed() {
    return ctx.reducer.getCommittedState();
  }

  function sessionOf(rs) {
    return `${rs.generation}|${rs.activeEpoch}`;
  }

  function modeEntry(mode) {
    const modes = ctx.campState.preview?.modes ?? [];
    return modes.find((entry) => entry.mode === mode) ?? null;
  }

  // The previous predicate stays the owner of the presence and room cards;
  // an open camp card is one more centred card (it hides the rail, stops the
  // compass and walk, and claims the digits).
  const centred = ctx.centredCardOpen;
  ctx.centredCardOpen = function centredCardOpen() {
    return centred() || OPEN_PHASES.has(ctx.campState.phase);
  };

  function reset() {
    ctx.campState = { ...closedState(), openCount: openings };
  }

  function sendPreview(rs) {
    const state = ctx.campState;
    if (state.phase !== "previewPending" || !state.wantPreview || state.pending) return false;
    if (!rs.connected || rs.phase !== "active" || ctx.inFlight || rs.mutationsLocked) return false;
    const requestId = ctx.dispatchAction("explore.camp_preview", {}, null);
    if (!requestId) return false;
    state.wantPreview = false;
    state.pending = Object.freeze({ kind: "preview", requestId, epoch: rs.activeEpoch, generation: rs.generation });
    return true;
  }

  /**
   * Open the camp card (from the leg's 紮營 or the forced-walking-sleep
   * handoff row). Returns false when it cannot open now.
   */
  ctx.openTravelCamp = function openTravelCamp(opener = "leg") {
    const rs = committed();
    if (ctx.campState.phase !== "closed" || rs.mode !== "exploration" || !rs.connected) return false;
    // Stop any walk first; an already-admitted step commits before the
    // preview leaves (the single-flight gate holds the preview until then).
    ctx.stopTravel?.("camp");
    ctx.presenceCard = null;
    ctx.roomCard = null;
    openings += 1;
    ctx.campState = {
      ...closedState(),
      phase: "previewPending",
      opener: opener === "handoff" ? "handoff" : "leg",
      wantPreview: true,
      session: sessionOf(rs),
      openCount: openings,
    };
    sendPreview(rs);
    ctx.publishView();
    return true;
  };

  /** Close the card without sending anything (cancel, Esc). */
  ctx.closeCamp = function closeCamp() {
    const phase = ctx.campState.phase;
    if (phase === "closed" || phase === "submitting") return false;
    reset();
    ctx.publishView();
    return true;
  };

  /** Select one of the two supplied modes (keys 1 and 2, or a tile click). */
  ctx.selectCampMode = function selectCampMode(mode) {
    const state = ctx.campState;
    if (state.phase !== "choosing") return false;
    const entry = modeEntry(mode);
    if (!entry) return false;
    state.selected = entry.mode;
    if (!entry.dream_offerable) state.dream = false;
    ctx.publishView();
    return true;
  };

  /** Toggle the dream opt-in, only while the selected mode offers it. */
  ctx.toggleCampDream = function toggleCampDream(value) {
    const state = ctx.campState;
    const entry = modeEntry(state.selected);
    if (state.phase !== "choosing" || !entry || !entry.dream_offerable) return false;
    state.dream = typeof value === "boolean" ? value : !state.dream;
    ctx.publishView();
    return true;
  };

  /** Confirm once: exactly one `explore.camp` for an available mode. */
  ctx.confirmCamp = function confirmCamp() {
    const state = ctx.campState;
    const entry = modeEntry(state.selected);
    if (state.phase !== "choosing" || !entry || !entry.available || state.pending) return false;
    const rs = committed();
    const dream = state.dream === true && entry.dream_offerable === true;
    const requestId = ctx.dispatchAction(
      "explore.camp",
      { mode: entry.mode, dream },
      null,
    );
    if (!requestId) return false;
    state.phase = "submitting";
    state.pending = Object.freeze({ kind: "camp", requestId, epoch: rs.activeEpoch, generation: rs.generation });
    ctx.publishView();
    return true;
  };

  /** The beat's Continue: back to the authoritative travel surface. */
  ctx.continueCampTravel = function continueCampTravel() {
    if (ctx.campState.phase !== "beat") return false;
    reset();
    ctx.publishView();
    return true;
  };

  function adopt(rs) {
    const state = ctx.campState;
    const pending = state.pending;
    const result = rs.lastActionResult;
    if (!pending || !result || result.requestId !== pending.requestId || result.epoch !== pending.epoch) return false;
    state.pending = null;
    if (pending.kind === "preview") {
      if (result.outcome === "success" && result.data) {
        const preview = Object.freeze(result.data);
        state.preview = preview;
        state.selected = preview.default_mode;
        state.dream = false;
        state.refusal = preview.available ? null : preview.refusal;
        state.phase = preview.available ? "choosing" : "refused";
      } else {
        state.phase = "refused";
        state.refusal = Object.freeze({ code: result.code ?? "camp_unavailable", message: result.message || "目前無法紮營。" });
      }
      return true;
    }
    if (result.outcome === "success" && result.data) {
      if (result.data.phase === "dream") {
        // The existing dream stage replaces the beat.
        reset();
        return true;
      }
      state.phase = "beat";
      state.result = Object.freeze(result.data);
      state.message = result.message || null;
      return true;
    }
    // A refused camp wrote nothing: the card shows the server reason with
    // only its cancellation (the preview it chose from is stale now).
    state.phase = "refused";
    state.refusal = Object.freeze({ code: result.code ?? "camp_refused", message: result.message || "目前無法紮營。" });
    return true;
  }

  function noteWalkHandoff(rs) {
    const panel = rs.panels?.sleep_handoff;
    const id = panel && panel.available === true ? String(panel.transition_id) : null;
    if (id !== lastHandoffId) {
      // A sleep-control view that appears while a walk or hold is active is
      // the forced-walking-sleep handoff (a walk never enters voluntary sleep).
      walkHandoff = id !== null && (ctx.travelWalk !== null || ctx.travelHold !== null) ? id : null;
      lastHandoffId = id;
    }
  }

  /** Run inside publishView, before the view is built. */
  ctx.settleCamp = function settleCamp(rs) {
    noteWalkHandoff(rs);
    const state = ctx.campState;
    if (state.phase === "closed") return;
    if (!rs.connected || rs.mode !== "exploration" || (state.session !== null && state.session !== sessionOf(rs))) {
      reset();
      return;
    }
    if (state.pending && (state.pending.epoch !== rs.activeEpoch || state.pending.generation !== rs.generation)) {
      reset();
      return;
    }
    adopt(rs);
    sendPreview(rs);
  };

  ctx.campView = function campView(rs) {
    const state = ctx.campState;
    const panel = rs?.panels?.sleep_handoff;
    const shortcut =
      walkHandoff !== null && panel && panel.available === true && String(panel.transition_id) === walkHandoff;
    const entry = modeEntry(state.selected);
    return Object.freeze({
      phase: state.phase,
      open: OPEN_PHASES.has(state.phase),
      opener: state.opener,
      openCount: state.openCount,
      preview: state.preview,
      selected: state.selected,
      selectedMode: entry,
      dream: state.dream,
      dreamOffered: !!entry && entry.dream_offerable === true,
      canConfirm: state.phase === "choosing" && !!entry && entry.available === true && !state.pending,
      refusal: state.refusal,
      result: state.result,
      message: state.message,
      handoffShortcut: !!shortcut,
    });
  };
}
