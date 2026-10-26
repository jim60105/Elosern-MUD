// C3 (webclient-vue-09-wire-transport-mount): bind the C1 store to the
// live evennia.js OOB transport. This is the single transport seam (design
// D5): the store only dispatches mutations (dispatch-only, one mutation in
// flight) and adopts server presentation (snapshot/update), exactly like the
// preserved `web/static/webclient/js/elosern/protocol.js` logic (re-exposed
// through `lib/protocol.js`) but driving the Pinia store instead of the
// legacy Protocol store.
//
// Wiring contract:
// - The `ui_snapshot` / `ui_update` / `ui_publication_part` /
//   `ui_action_result` / `ui_protocol_error` OOB listeners are tagged with the
//   transport generation and feed
//   `store.receive(generation, name, args, kwargs)`. Because the evennia.js
//   emitter keeps a single listener per message name, they are re-registered
//   on every `connection_open` with the new generation, so a delayed
//   old-generation message is discarded by `store.receive`.
// - The shared transport lifecycle events (`connection_open` / `connection_close`
//   / `logged_in` / `text` / `prompt`) are owned by this module *after* the
//   D10 text console has attached (base.html calls the bind hook after
//   `consoleApi.attach`), so the coordinator re-registers them last and
//   dispatches each to BOTH the D10 console model (re-painting its DOM) and
//   the store (narrative / prompt / connection state).
// - The sender seam wraps `Evennia.msg` so `store.dispatchAction` and
//   `store.sendText` route through the single transport (no second send path).

import Protocol from "./lib/protocol.js";
import { retireReplacedFallback } from "./fallback.js";

const OOB_MESSAGES = [
  "ui_snapshot",
  "ui_update",
  "ui_publication_part",
  "ui_action_result",
  "ui_protocol_error",
];

// One bounded recovery response deadline per request (webclient-sync-recovery):
// the complete repair this client asked for must land within 30 000 ms of the
// request, or the episode becomes terminal and only an explicit player
// synchronize (or a new transport generation) may ask again. The sibling
// assembly deadline of a multi-part repair starts at its own first part.
const RECOVERY_RESPONSE_TIMEOUT_MS = 30000;

export function wireTransport(store, consoleHandle) {
  const evennia = window.Evennia;
  if (!evennia || !evennia.emitter) {
    return false;
  }
  // Idempotent: the sender seam is attached exactly once.
  if (store.getSender()) {
    return true;
  }

  let generation = 0;
  let recoveryTimer = null;

  function isConnOpen() {
    return typeof evennia.isConnected === "function" ? evennia.isConnected() : true;
  }

  function clearRecoveryDeadline() {
    if (recoveryTimer === null) {
      return;
    }
    window.clearTimeout(recoveryTimer);
    recoveryTimer = null;
  }

  function startRecoveryDeadline() {
    clearRecoveryDeadline();
    recoveryTimer = window.setTimeout(function () {
      recoveryTimer = null;
      // Expiry of the bound is a failed repair: locked, no automatic retry.
      store.failRecovery("timeout");
    }, RECOVERY_RESPONSE_TIMEOUT_MS);
  }

  function sendSync() {
    if (isConnOpen()) {
      evennia.msg("ui_sync", [Protocol.syncEnvelope()], {});
      // The request just left as an episode's single repair attempt: the
      // bounded response deadline starts with it.
      if (store.recoveryStatus() === "requested") {
        startRecoveryDeadline();
      }
    }
  }

  function resyncIfAwaiting() {
    // A reconnect can emit `logged_in` before the portal re-attaches the
    // account's puppet: the bounded deferral re-synchronizes while still
    // awaiting the initial snapshot OR while detached (a `no_puppet` error
    // right after login) — one shot per `logged_in`, never a loop, and never
    // a retry of a failed repair (the gate declines that).
    if (
      store.view.phase === "awaiting_initial_snapshot" ||
      store.view.phase === "detached"
    ) {
      store.requestPresentationSync("lifecycle");
    }
  }

  function registerOobListeners() {
    const taggedGeneration = generation;
    for (const name of OOB_MESSAGES) {
      evennia.emitter.on(name, function (args, kwargs) {
        store.receive(taggedGeneration, name, args || [], kwargs || {});
      });
    }
  }

  function consolePaint() {
    if (consoleHandle && typeof consoleHandle.paint === "function") {
      consoleHandle.paint();
    }
  }

  // D5 single transport seam: dispatch-only sends.
  store.setSender({
    sendText: (text) => evennia.msg("text", [String(text)], {}),
    sendAction: (envelope) => evennia.msg("ui_action", [envelope], {}),
    sendSync: sendSync,
  });

  // The deadline belongs to the episode, not to the frame: any commit, failure
  // or generation reset that ends it cancels the pending expiry.
  store.subscribe(function () {
    if (store.recoveryStatus() !== "requested") {
      clearRecoveryDeadline();
    }
  });

  retireReplacedFallback();

  registerOobListeners();

  evennia.emitter.on("connection_open", function (args, kwargs) {
    // New transport generation: retire the prior epoch and adopt a fresh
    // initial snapshot.
    generation += 1;
    if (consoleHandle && consoleHandle.model) {
      consoleHandle.model.setConnected(true);
    }
    store.beginTransport(generation);
    store.setConnected(true);
    // A fresh socket has not authenticated yet: the overlay waits for login
    // until the server's `logged_in` event marks the account attached.
    store.setLoggedIn(false);
    registerOobListeners();
    sendSync();
    consolePaint();
  });

  evennia.emitter.on("connection_close", function (args, kwargs) {
    // A closed transport will never deliver the repair being waited for; the
    // need survives the reconnect's own initial-sync lifecycle instead.
    clearRecoveryDeadline();
    if (consoleHandle && consoleHandle.model) {
      consoleHandle.model.setConnected(false);
    }
    store.setConnected(false);
    consolePaint();
  });

  evennia.emitter.on("logged_in", function (args, kwargs) {
    if (consoleHandle && consoleHandle.model) {
      consoleHandle.model.reset();
      consoleHandle.model.setLoggedIn(true);
    }
    // The account is attached on this session: the transport status slice can
    // leave the "waiting for login" state (the snapshot may still be in
    // flight, shown as "connecting").
    store.setLoggedIn(true);
    // A reconnecting websocket can emit `logged_in` right before the portal
    // re-attaches the account's puppet; a bounded deferral re-synchronizes
    // only while still awaiting the initial snapshot (no sync loop).
    window.setTimeout(resyncIfAwaiting, 500);
    consolePaint();
  });

  evennia.emitter.on("text", function (args) {
    const line = args && args[0];
    if (consoleHandle && consoleHandle.model) {
      consoleHandle.model.appendOut(line);
    }
    store.appendText("out", line);
    consolePaint();
  });

  evennia.emitter.on("prompt", function (args) {
    const promptText = args && args[0];
    if (consoleHandle && consoleHandle.model) {
      consoleHandle.model.setPrompt(promptText);
    }
    store.setPrompt(promptText);
    consolePaint();
  });

  return true;
}
