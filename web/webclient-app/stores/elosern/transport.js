// The transport + dispatch group of the composed Elosern store: the OOB
// receive/lifecycle seam over the preserved reducer, the narrative/command
// text path, and the single dispatch entry with the tested lock semantics.
//
// D5: the transport transport is an attachable `setSender` seam; a single
// dispatch entry routes every mutation (dispatch-only, one mutation in
// flight) with the tested lock semantics.

import stableStringify from "../../lib/stable_stringify.js";
import CreationMenu from "../../lib/creation_menu.js";
import CommandEcho from "../../lib/command_echo.js";
import NarrativeMarkup from "../../lib/narrative_markup.js";
import {
  NARRATIVE_KINDS,
  MAX_NARRATIVE_LINES,
  ACTION_RESULT_FALLBACK_MESSAGE,
  NON_SUCCESS_OUTCOMES,
  MAX_COMMAND_HISTORY,
  creationOverlayPresenting,
} from "./shared.js";

export function applyTransport(ctx) {
  ctx.handleTransportLifecycle = function handleTransportLifecycle(prev, rs) {
    if (rs.generation !== prev.generation) {
      ctx.inFlight = null;
      ctx.requestCounter = 0;
      // `uncertain` is intentionally NOT cleared here: a mutation whose result
      // was withheld by a mid-flight detach stays flagged across the
      // reconnect (the C3 transport's `clearUncertain` releases it only when
      // the result is observed).
    }
    if (prev.phase !== "detached" && rs.phase === "detached" && ctx.inFlight) {
      ctx.uncertain = true;
      ctx.inFlight = null;
    }
  };

  // D5: the in-flight lock releases with the tested legacy action-client
  // semantics. A matching `ui_action_result` (same request id, same epoch)
  // sets the declared presentation revision; the lock then releases only
  // when the committed revision reaches that revision (immediately when none
  // was declared, unconditionally for a `no_puppet` rejection; a `stale`
  // outcome keeps the lock until the recovery snapshot commits — the
  // `ui_sync` re-request itself is the C3 transport's job).
  ctx.handleActionResult = function handleActionResult(rs) {
    if (!ctx.inFlight) {
      return;
    }
    const result = rs.lastActionResult;
    if (!result || result.requestId !== ctx.inFlight.requestId) {
      return;
    }
    if (result.epoch !== rs.activeEpoch) {
      return;
    }
    // Recognition/dedup unit: the in-flight request plus its own
    // handled-result fingerprint (duck findings 2/3). The old global
    // "changed from previous" equality could both re-append (a foreign
    // result delivered between two observations of this request's result)
    // and silence a legitimate match (a result that was already sitting in
    // the reducer before this dispatch started). A recognized result is
    // recorded on the in-flight record, so re-delivery / re-observation is
    // idempotent and foreign results cannot interfere. A cached duplicate
    // for a foreign request still fails the request-id match above and
    // never unlocks.
    const fingerprint = stableStringify(result);
    if (ctx.inFlight.handledResult === fingerprint) {
      return;
    }
    ctx.inFlight.handledResult = fingerprint;
    ctx.inFlight.presentationRevision = result.presentationRevision;
    // webclient-action-result-feedback: a recognized non-success result
    // (rejected / stale / error) speaks exactly once as one narrative error
    // line carrying the server-authored message verbatim. The match guards
    // above (changed-from-previous, request id, epoch) are the dedup unit;
    // the creation overlay, when mounted, already presents the result and
    // suppresses the line. The lock/uncertain/revision mechanics below are
    // untouched by the append.
    if (
      NON_SUCCESS_OUTCOMES.indexOf(result.outcome) !== -1 &&
      !creationOverlayPresenting(rs)
    ) {
      const message =
        typeof result.message === "string" && result.message.trim() !== ""
          ? result.message
          : ACTION_RESULT_FALLBACK_MESSAGE;
      ctx.appendText("err", message);
    }
    // The action-feedback crit toast (webclient-action-feedback D3): a
    // recognized non-success `creation.concept` result ALSO speaks exactly
    // once, above the overlay. This branch shares the narrative line's
    // recognition/dedup unit and non-success outcome test above, but NOT its
    // `!creationOverlayPresenting` presentation gate — a concept failure
    // necessarily lands while the creation overlay is mounted, so applying
    // the overlay gate to the toast channel would silence it everywhere it
    // matters. The channel is action-scoped by the in-flight `actionId`
    // (custom/preset results, including their stale exception, never reach
    // it). The overlay result region and narrative behavior above are
    // unchanged (toasts are additive). A success result pushes NOTHING here:
    // the success-confirmation info toast's sole writer is the form layer
    // (`retool-concept-fill-navigation`'s `applyProposal` via `pushToast`).
    if (
      NON_SUCCESS_OUTCOMES.indexOf(result.outcome) !== -1 &&
      ctx.inFlight.actionId === CreationMenu.CONCEPT_ACTION
    ) {
      ctx.pushToast({
        title:
          typeof result.message === "string" && result.message.trim() !== ""
            ? result.message
            : ACTION_RESULT_FALLBACK_MESSAGE,
        tone: "crit",
      });
    }
    if (result.outcome === "rejected" && result.code === "no_puppet") {
      // The puppet is gone; no presentation will ever gate this rejection,
      // so the lock is released unconditionally.
      ctx.inFlight = null;
      // A no-puppet rejection is terminal: the mutation is resolved, so a later
      // transport loss must not re-flag it as uncertain.
      ctx.mutationSubmitted = false;
    }
  };

  // Read the legacy action client's in-flight gate. Returns true while a
  // submitted mutation is unconfirmed (its result has not been observed by the
  // client), false when confirmed (result observed, gate released), or null
  // when the client is unavailable (mid re-bootstrap).
  function clientInFlight() {
    const c =
      typeof window !== "undefined" &&
      window.Elosern &&
      window.Elosern.actions &&
      window.Elosern.actions.client;
    return c && c.isInFlight ? c.isInFlight() : null;
  }
  ctx.clientInFlight = clientInFlight;

  // The revision-gated release: the lock releases once the committed
  // revision reaches the in-flight request's declared presentation revision.
  // A not-yet-declared target (no result received yet) keeps the lock held,
  // exactly like the legacy action client's `releaseIfReady`/
  // `onPresentationAccepted` pair.
  ctx.releaseIfReady = function releaseIfReady(rs) {
    if (!ctx.inFlight) {
      return;
    }
    const target = ctx.inFlight.presentationRevision;
    if (target !== null && rs.revision !== null && rs.revision >= target) {
      ctx.inFlight = null;
      // The store's gate releasing means the committed revision reached the
      // declared presentation revision. If the client's gate is also released
      // (the client observed the result = confirmed), the mutation is resolved,
      // so a later transport loss must not re-flag it as uncertain.
      if (clientInFlight() === false) {
        ctx.mutationSubmitted = false;
      }
    }
  };

  // ---------------------------------------------------------------- actions

  ctx.receive = function receive(messageGeneration, messageName, args, kwargs) {
    const result = ctx.reducer.receive(messageGeneration, messageName, args || [], kwargs || {});
    // Track presentation receive results. A genuine "cannot render" rejection
    // — a malformed `ui_snapshot` / `ui_update` the reducer refused to commit
    // (`reason === "invalid"`), or a transport-corruption missing-envelope
    // rejection (`reason === "missing_envelope") — drives the C4 one-sync-
    // per-episode auto-resync. Ordering / lifecycle rejections
    // (stale_generation, not_newer, different_epoch, retired_epoch,
    // update_cannot_establish_epoch) and an accepted presentation do NOT set
    // the signal.
    if (messageName === "ui_snapshot" || messageName === "ui_update") {
      if (result && result.accepted) {
        ctx.lastPanelRejection.value = null;
      } else if (
        result &&
        !result.accepted &&
        (result.reason === "invalid" || result.reason === "missing_envelope")
      ) {
        ctx.lastPanelRejection.value = { messageName, reason: result.reason, detail: result.detail || null };
      }
    }
    return result;
  };

  ctx.beginTransport = function beginTransport(nextGeneration) {
    const res = ctx.reducer.beginTransport(nextGeneration);
    // A new transport generation is a fresh failure episode: clear the
    // presentation-rejection signal so the next generation's malformed initial
    // snapshot can auto-request one ui_sync.
    ctx.lastPanelRejection.value = null;
    return res;
  };

  ctx.setConnected = function setConnected(connected) {
    // A disconnect ends the authenticated session (mirrors the D10 console
    // model): the next socket starts waiting for login again. Reset before
    // the reducer commit so the synchronous publish sees the cleared flag.
    if (!connected) {
      ctx.loggedIn = false;
    }
    const res = ctx.reducer.setConnected(connected);
    // A transport disconnect (connection_close) while an OOB mutation was
    // submitted and the client's in-flight gate is still held (the result has
    // NOT been observed by the client): the outcome may or may not have been
    // applied server-side, so the mutation is marked uncertain (client-local;
    // released only when the result is observed or by `clearUncertain`).
    // The client's gate is held (true) or the client is unavailable mid
    // re-bootstrap (null): the mutation is unconfirmed, so a transport loss
    // marks it uncertain. Only a released gate (false, result observed)
    // means the mutation is confirmed and must not be re-flagged.
    if (!connected && ctx.mutationSubmitted && clientInFlight() !== false) {
      ctx.uncertain = true;
      ctx.inFlight = null;
      ctx.router.setMutationInFlight(false);
      ctx.router.setAwaitingRevision(null);
      ctx.publishView();
    }
    return res;
  };

  ctx.setSender = function setSender(next) {
    ctx.sender = next || null;
  };

  ctx.setLoggedIn = function setLoggedIn(value) {
    ctx.loggedIn = !!value;
    ctx.publishView();
  };

  ctx.setPrompt = function setPrompt(text) {
    ctx.prompt = typeof text === "string" ? text : "";
    ctx.publishView();
  };

  ctx.appendText = function appendText(kind, text) {
    if (NARRATIVE_KINDS.indexOf(kind) === -1) {
      throw new TypeError("narrative kind must be one of in/out/sys/err");
    }
    const normalized = String(text == null ? "" : text);
    // D1/D5 (webclient-message-pages): every retained line carries a monotonic
    // ordinal (`seq`) that survives retention trimming, and the allowlist
    // markup pipeline runs once at retain time for `out`, `sys`, and `err`
    // lines (`in` stays literal text with `tokens: null`).
    const line = {
      kind,
      seq: ++ctx.narrativeSeq,
      text: normalized,
      tokens: kind === "in" ? null : NarrativeMarkup.tokenize(normalized),
    };
    ctx.narrative.value.push(line);
    while (ctx.narrative.value.length > MAX_NARRATIVE_LINES) {
      ctx.narrative.value.shift();
    }
    if (ctx.narrative.value.length > 0 && ctx.responseMarks.value.length > 0) {
      const oldestSeq = ctx.narrative.value[0].seq;
      while (ctx.responseMarks.value.length > 0 && ctx.responseMarks.value[0] < oldestSeq) {
        ctx.responseMarks.value.shift();
      }
    }
    return line;
  };

  // Clear the pending freeform dialogue target (a cancelled drawer must not
  // capture later ordinary commands as dialogue speech).
  ctx.clearFreeformTarget = function clearFreeformTarget() {
    if (ctx.freeformTarget != null) {
      ctx.freeformTarget = null;
      ctx.publishView();
    }
  };

  ctx.sendText = function sendText(text) {
    if (!ctx.view.value.connected) {
      return false;
    }
    const value = String(text == null ? "" : text);
    ctx.commandHistory.value.push(value);
    while (ctx.commandHistory.value.length > MAX_COMMAND_HISTORY) {
      ctx.commandHistory.value.shift();
    }
    // An active freeform dialogue target routes the typed speech through the
    // guarded dialogue seam (explore.talk_freeform) with the target's npc_id,
    // never as ordinary narrative text. The NPC's server-authored display name
    // is read from the committed exploration panel and passed as the
    // `commandDisplay` descriptor so the CommandEcho catalog resolves the line.
    if (ctx.freeformTarget != null) {
      const rs = ctx.reducer.getState();
      const panel = (rs.panels && rs.panels.exploration) || {};
      let npcLabel = "";
      for (const target of panel.interact || []) {
        if (String(target.identity) === String(ctx.freeformTarget)) {
          npcLabel = target.display_name || "";
          break;
        }
      }
      const sent = ctx.dispatchAction("explore.talk_freeform", { npc_id: ctx.freeformTarget, speech: value }, { npcLabel });
      // A successful dock-borrowed send collapses the command line and
      // restores action-dock focus (webclient-desktop-shell; design D2/D3);
      // a rejected send leaves the command line expanded with its text.
      if (sent !== null) {
        ctx.drawerCloseRequest += 1;
      }
      ctx.freeformTarget = null;
      ctx.publishView();
      return true;
    }
    // Ordinary text command: the typed command line is part of the narrative
    // stream (a player input line), never a mutation echo.
    ctx.appendText("in", value);
    if (ctx.sender && typeof ctx.sender.sendText === "function") {
      ctx.sender.sendText(value);
    }
    return true;
  };

  ctx.dispatchAction = function dispatchAction(actionId, payload, display) {
    const v = ctx.view.value;
    if (!v.connected || v.mutationsLocked || v.phase !== "active" || ctx.inFlight) {
      return null;
    }
    const requestId = "session:" + (++ctx.requestCounter);
    const envelope = {
      protocol_version: 1,
      presentation_epoch: v.epoch,
      request_id: requestId,
      base_revision: v.revision,
      action_id: actionId,
      payload: payload === undefined || payload === null ? {} : payload,
    };
    ctx.inFlight = { requestId, actionId, presentationRevision: null, handledResult: null };
    // `handledResult` is the per-request dedup unit
    // (webclient-action-result-feedback): the fingerprint of the result this
    // in-flight dispatch has already recognized. Re-observation (publishView
    // re-runs, reducer replays of the identical result) never re-appends; a
    // foreign result cannot erase the record, so a re-delivery of THIS
    // request's result stays silent even after another request's result
    // passed through the reducer.
    // `actionId` (webclient-action-feedback D3): the local correlation the
    // concept crit trigger reads; the exposed `view.dispatch.inFlight` copy
    // keeps its frozen two-field shape.
    ctx.mutationSubmitted = true;
    ctx.lastSubmittedRequestId = requestId;
    // A custom save tracks its request so the result resolution opens the
    // confirmation for the just-saved draft (fix-creation-finalization-safety
    // D1); the preset path records the same markers on router submit.
    if (actionId === CreationMenu.CUSTOM_ACTION && ctx.creation) {
      ctx.creation.pendingSaveRequestId = requestId;
      ctx.creation.pendingActivate = "custom";
      ctx.creation.pendingActivateKey = null;
    }
    ctx.router.setMutationInFlight(true);
    try {
      if (ctx.sender && typeof ctx.sender.sendAction === "function") {
        ctx.sender.sendAction(envelope);
        // D1 (webclient-message-pages): record the response boundary at the
        // ordinal the next retained line will receive, right after the
        // transport send returns and before the optional echo line appends.
        // An echoing dispatch's `in` line receives this same ordinal (one
        // response, not two); a silent dispatch marks its first following
        // reply or error line as the start of a new response.
        ctx.responseMarks.value.push(ctx.narrativeSeq + 1);
        // The display command line (webclient-input-narrative): resolve exactly
        // one bounded echo line from the pure catalog and append it as a literal
        // text line; a rejected result leaves the line in place. Intent
        // surfaces get their missing labels filled from committed state first
        // (fillDisplayFor); the filled descriptor feeds the catalog ONLY — the
        // envelope above is already built and untouched.
        const echoDisplay = ctx.fillDisplayFor(actionId, envelope.payload, display);
        const line = CommandEcho.commandLine(actionId, envelope.payload, echoDisplay);
        if (line) {
          ctx.appendText("in", line);
        }
      }
    } catch (err) {
      // A synchronous transport failure (a closing WebSocket, a failed
      // adapter): mark the mutation uncertain, release the in-flight gate
      // (no declared presentation revision to await) so the dispatch lock
      // never sticks, and publish so the committed view reflects the failed
      // send (the C3 transport re-asserts or the `clearUncertain` path
      // recovers the flag).
      ctx.uncertain = true;
      ctx.inFlight = null;
      ctx.router.setMutationInFlight(false);
      ctx.router.setAwaitingRevision(null);
    } finally {
      ctx.publishView();
    }
    return requestId;
  };

  ctx.clearUncertain = function clearUncertain() {
    ctx.uncertain = false;
    ctx.mutationSubmitted = false;
    ctx.publishView();
  };

  // Expose the attached transport seam so the C2 browser-bridge can route the
  // OOB entry points (ui_sync requests, reconnect resync) through the same
  // sender C3 will later attach (the store's sender is the single transport
  // seam; the bridge never re-implements sending).
  ctx.getSender = function getSender() {
    return ctx.sender;
  };
}
