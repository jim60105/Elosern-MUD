// C3 (webclient-vue-09-wire-transport-mount): unit coverage of the
// evennia.js OOB transport binding (`web/webclient-app/transport.js`).
// A single evennia.js emitter keeps ONE listener per event name and the
// wire shape is the `["cmdname", args, kwargs]` triple (args[0] is the
// OOB envelope). The coordinator registers the OOB listeners tagged with
// the transport generation and re-registers them on every connection_open;
// shared lifecycle events dispatch to BOTH the D10 console model and the
// store.

import { describe, expect, it, beforeAll, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import { wireTransport } from "../transport.js";
import { useElosernStore } from "../stores/elosern.js";
import * as fx from "./store/protocol_fixtures.js";

function makeStubStore() {
  const calls = [];
  let sender = null;
  const store = {
    calls,
    view: {
      phase: "awaiting_initial_snapshot",
      mode: "exploration",
      connected: false,
      mutationsLocked: true,
      protocolError: null,
      generation: 0,
      connectionStatus: "connecting",
      statusSlice: { connected: false, locationLabel: null, timeLabel: null },
      panels: {},
      suggestions: null,
      localMapModel: null,
      prompt: "",
    },
    narrative: [],
    commandHistory: [],
    receive(messageGeneration, name, args, kwargs) {
      calls.push(["receive", messageGeneration, name, args && args[0], kwargs]);
      return { accepted: true };
    },
    beginTransport(gen) {
      calls.push(["beginTransport", gen]);
      store.view.generation = gen;
      store.view.phase = "awaiting_initial_snapshot";
      return undefined;
    },
    setConnected(v) {
      calls.push(["setConnected", v]);
      store.view.connected = v;
      store.view.statusSlice.connected = v;
      store.view.mutationsLocked = !v;
      return undefined;
    },
    setLoggedIn(v) {
      calls.push(["setLoggedIn", v]);
      return undefined;
    },
    setSender(s) {
      sender = s;
      calls.push(["setSender", typeof s === "function" ? "fn" : "obj"]);
      return undefined;
    },
    getSender() {
      return sender;
    },
    appendText(kind, text) {
      calls.push(["appendText", kind, text]);
      store.narrative.push({ kind, text });
      return undefined;
    },
    setPrompt(p) {
      calls.push(["setPrompt", p]);
      store.view.prompt = p;
      return undefined;
    },
    dispatchAction(actionId, payload) {
      calls.push(["dispatchAction", actionId, payload]);
      const s = store.getSender();
      if (s && typeof s.sendAction === "function") {
        const envelope = {
          protocol_version: 1,
          presentation_epoch: "epoch_b",
          request_id: "session:test1",
          base_revision: 1,
          action_id: actionId,
          payload: payload || {},
        };
        s.sendAction(envelope);
      }
      return "session:test1";
    },
    refreshView() {
      calls.push(["refreshView"]);
      return undefined;
    },
  };
  return store;
}

function makeFakeEvennia() {
  const listeners = {};
  const sent = [];
  const evennia = {
    _connected: true,
    emitter: {
      // Single listener per name (the evennia.js DefaultEmitter contract).
      on(name, fn) {
        listeners[name] = fn;
      },
    },
    msg(name, args, kwargs) {
      sent.push([name, args || [], kwargs || {}]);
    },
    isConnected() {
      return evennia._connected;
    },
  };
  function emit(name, args, kwargs) {
    if (listeners[name]) {
      listeners[name](args, kwargs);
    }
  }
  return { evennia, listeners, sent, emit };
}

function makeConsoleHandle() {
  let connected = false;
  let loggedIn = false;
  let prompt = "";
  const lines = [];
  const consoleHandle = {
    model: {
      setConnected(v) {
        connected = !!v;
      },
      setLoggedIn(v) {
        loggedIn = !!v;
      },
      reset() {
        lines.length = 0;
        prompt = "";
      },
      appendOut(text) {
        lines.push(String(text));
      },
      setPrompt(text) {
        prompt = String(text);
      },
    },
    wrapper: { setAttribute: () => {}, getAttribute: () => "ready" },
    send: () => {},
    paint: () => {
      consoleHandle.lastStatus = connected ? (loggedIn ? "ready" : "waiting") : "offline";
    },
  };
  return consoleHandle;
}

describe("wireTransport", () => {
  it("binds the four OOB listeners to store.receive with the generation", () => {
    const { evennia, listeners, emit } = makeFakeEvennia();
    const store = makeStubStore();
    window.Evennia = evennia;

    const wired = wireTransport(store, makeConsoleHandle());

    expect(wired).toBe(true);
    // The four OOB names are registered (single listener per name).
    expect(Object.keys(listeners).sort()).toEqual(
      ["connection_close", "connection_open", "logged_in", "prompt", "text", "ui_action_result", "ui_protocol_error", "ui_snapshot", "ui_update"].sort()
    );

    // A delayed older-generation message is discarded by the generation gate.
    const snapshot = { protocol_version: 1, presentation_epoch: "epoch_a", revision: 1 };
    emit("ui_snapshot", [snapshot], {});
    expect(store.calls).toContainEqual(["receive", 0, "ui_snapshot", snapshot, {}]);
  });

  it("re-registers OOB listeners and bumps generation on connection_open, resyncs on logged_in", () => {
    const { evennia, emit } = makeFakeEvennia();
    const consoleHandle = makeConsoleHandle();
    const store = makeStubStore();
    window.Evennia = evennia;
    wireTransport(store, consoleHandle);

    // Open the connection: generation 0 -> 1, beginTransport(1), re-register, sync.
    emit("connection_open");
    expect(store.calls).toContainEqual(["beginTransport", 1]);
    expect(store.calls).toContainEqual(["setConnected", true]);

    // After open, the OOB listeners are re-tagged with the new (1) generation.
    const snapshot = { protocol_version: 1, presentation_epoch: "epoch_b", revision: 1 };
    emit("ui_snapshot", [snapshot], {});
    expect(store.calls).toContainEqual(["receive", 1, "ui_snapshot", snapshot, {}]);

    // connection_close locks the store's mutations, keeping the text path.
    emit("connection_close");
    expect(store.calls).toContainEqual(["setConnected", false]);
    // The coordinator still owns the shared names (emitter keeps one listener per name).
    const before = store.calls.filter((c) => c[0] === "beginTransport").length;
    emit("connection_open");
    const after = store.calls.filter((c) => c[0] === "beginTransport").length;
    expect(after).toBe(before + 1);
  });

  it("marks the session waiting-for-login on open and logged-in on the logged_in event", () => {
    const { evennia, emit } = makeFakeEvennia();
    const consoleHandle = makeConsoleHandle();
    const store = makeStubStore();
    window.Evennia = evennia;
    wireTransport(store, consoleHandle);

    // A fresh socket has not authenticated yet: the overlay must not present
    // "connecting" forever while the server never sends a snapshot to an
    // anonymous session.
    emit("connection_open");
    expect(store.calls).toContainEqual(["setLoggedIn", false]);

    // The server's `logged_in` OOB event marks the account attached; the
    // store then waits only for the in-flight snapshot ("connecting").
    emit("logged_in");
    expect(store.calls).toContainEqual(["setLoggedIn", true]);
  });

  it("drives the real store through the login and reconnect lifecycle", async () => {
    // The full wiring against the Pinia store (not the stub): the overlay
    // status slice must follow the real event order
    // connection_open -> logged_in -> ui_snapshot, and a reconnect must not
    // retain the prior authenticated session. Fake timers drive the bounded
    // post-login resync deferral.
    vi.useFakeTimers();
    try {
      const { evennia, emit, sent } = makeFakeEvennia();
      window.Evennia = evennia;
      const consoleHandle = makeConsoleHandle();
      setActivePinia(createPinia());
      const store = useElosernStore();
      wireTransport(store, consoleHandle);

      // Anonymous socket: waiting for login, never "connecting" forever.
      emit("connection_open");
      expect(store.view.connectionStatus).toBe("waiting");

      // Account attached: the overlay shows "connecting" only while the
      // initial snapshot is genuinely in flight.
      emit("logged_in");
      expect(store.view.connectionStatus).toBe("connecting");

      // A valid snapshot commits: ready.
      emit("ui_snapshot", [fx.snapshot()], {});
      expect(store.view.connectionStatus).toBe("ready");

      // Reconnect: the fresh socket starts unauthenticated again (waiting).
      emit("connection_close");
      expect(store.view.connectionStatus).toBe("offline");
      emit("connection_open");
      expect(store.view.connectionStatus).toBe("waiting");

      // A `no_puppet` detach around login stays "waiting"; the deferred
      // resync after `logged_in` still retries while detached (one shot).
      emit("ui_protocol_error", [fx.protocolError()], {});
      expect(store.view.connectionStatus).toBe("waiting");
      emit("logged_in");
      const before = sent.filter((m) => m[0] === "ui_sync").length;
      await vi.advanceTimersByTimeAsync(600);
      const after = sent.filter((m) => m[0] === "ui_sync").length;
      expect(after).toBeGreaterThan(before);
    } finally {
      vi.useRealTimers();
    }
  });

  it("routes text/prompt and dispatches actions through the single sender seam", () => {
    const { evennia, emit, sent } = makeFakeEvennia();
    const consoleHandle = makeConsoleHandle();
    const store = makeStubStore();
    window.Evennia = evennia;
    wireTransport(store, consoleHandle);

    emit("text", ["you look around."], {});
    expect(store.calls).toContainEqual(["appendText", "out", "you look around."]);

    emit("prompt", ["> "], {});
    expect(store.calls).toContainEqual(["setPrompt", "> "]);

    // dispatchAction -> sender.sendAction -> Evennia.msg("ui_action", [envelope]).
    store.dispatchAction("explore.look", {});
    expect(sent.some((m) => m[0] === "ui_action" && m[1] && m[1][0] && m[1][0].action_id === "explore.look")).toBe(true);
  });

  it("is idempotent (the sender seam is attached exactly once)", () => {
    const { evennia } = makeFakeEvennia();
    const store = makeStubStore();
    window.Evennia = evennia;
    const ch = makeConsoleHandle();
    expect(wireTransport(store, ch)).toBe(true);
    expect(wireTransport(store, makeConsoleHandle())).toBe(true);
    // Only one setSender call total (idempotent re-call does not re-attach).
    const setSenderCalls = store.calls.filter((c) => c[0] === "setSender");
    expect(setSenderCalls.length).toBe(1);
  });
});
