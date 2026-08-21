/*
 * Elosern WebClient state wiring.
 *
 * Bridges the DOM-independent reducer (`elosern/protocol.js`) to the Evennia
 * emitter: subscribes to the four server OOB messages, requests a full
 * snapshot on every `connection_open`, and exposes subscriptions plus bounded
 * one-sync renderer recovery so panel renderers never create a sync loop. A
 * bounded awaiting-snapshot resync re-requests `ui_sync` while a fresh
 * transport is stuck in `awaiting_initial_snapshot`, so a reconnect whose
 * first sync landed before the portal re-attached the puppet still recovers.
 *
 * Browser-only wiring that touches `window.Evennia`; the controller factory
 * itself is DOM-independent so the Node suite can exercise the bounded
 * recovery logic with a fake sync transport.
 */
(function (root, factory) {
  "use strict";
  if (typeof module !== "undefined" && module.exports) {
    module.exports = factory();
  } else {
    root.Elosern = root.Elosern || {};
    root.Elosern.State = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  // Bound one full resync per failure episode per panel. An episode ends only
  // when the panel renders successfully again; repeated failure stays silent,
  // so a malformed panel cannot trigger an automatic sync loop.
  function createOneSyncGuard() {
    var episodes = {}; // panelName -> { usedSync: boolean }
    return {
      // Returns true if this call issued a resync, false if the episode has
      // already used its single resync or the panel is unknown.
      request: function (panelName) {
        if (typeof panelName !== "string" || panelName === "") {
          return false;
        }
        var episode = episodes[panelName];
        if (episode && episode.usedSync) {
          return false;
        }
        episodes[panelName] = { usedSync: true };
        return true;
      },
      // A renderer calls this after successfully rendering the panel payload,
      // ending the failure episode and allowing one fresh resync later.
      resetEpisode: function (panelName) {
        delete episodes[panelName];
      },
      clearAll: function () {
        episodes = {};
      },
      isBlocked: function (panelName) {
        return !!(episodes[panelName] && episodes[panelName].usedSync);
      },
    };
  }

  // A reconnecting websocket can send the generation's first `ui_sync` before
  // the portal finishes re-attaching the account's puppet, so the snapshot is
  // silently dropped and the store stays in `awaiting_initial_snapshot`. This
  // scheduler re-requests the snapshot on a bounded budget: it disarms on
  // adoption, on disconnect, and once the attempt budget is spent (which sets
  // the exhausted flag so recovery can react without looping forever).
  var SYNC_RETRY_INTERVAL_MS = 1500;
  var SYNC_RETRY_MAX_ATTEMPTS = 8;

  function createAwaitingSyncRetry(getState, sendSync, maxAttempts) {
    var budget =
      typeof maxAttempts === "number" && maxAttempts > 0
        ? maxAttempts
        : SYNC_RETRY_MAX_ATTEMPTS;
    var attempts = 0;
    var armed = false;
    var exhausted = false;
    return {
      // Arm a fresh budget for a new transport generation.
      arm: function () {
        attempts = 0;
        exhausted = false;
        armed = true;
      },
      disarm: function () {
        armed = false;
      },
      tick: function () {
        if (!armed) {
          return "idle";
        }
        var state = getState();
        if (
          !state ||
          !state.connected ||
          state.phase !== "awaiting_initial_snapshot"
        ) {
          armed = false;
          return "idle";
        }
        if (attempts >= budget) {
          armed = false;
          exhausted = true;
          return "idle";
        }
        attempts += 1;
        sendSync();
        return "sent";
      },
      isArmed: function () {
        return armed;
      },
      attempts: function () {
        return attempts;
      },
      isExhausted: function () {
        return exhausted;
      },
    };
  }

  // A controller bound to a concrete transport store (`sendSync`). Kept pure
  // and DOM-independent so Node tests can verify sync counting.
  function createStateController(protocolFactory, sendSync) {
    var store = protocolFactory.createStore();
    var guard = createOneSyncGuard();

    return {
      store: store,
      getState: function () {
        return store.getState();
      },
      subscribe: function (listener) {
        return store.subscribe(listener);
      },
      beginTransport: function (generation) {
        guard.clearAll();
        return store.beginTransport(generation);
      },
      receive: function (generation, messageName, args, kwargs) {
        return store.receive(generation, messageName, args, kwargs);
      },
      // A renderer that cannot render a panel requests one full resync for
      // the same failure episode; repeated failure stays silent.
      requestResync: function (panelName) {
        if (!guard.request(panelName)) {
          return false;
        }
        sendSync();
        return true;
      },
      resetResyncEpisode: function (panelName) {
        guard.resetEpisode(panelName);
      },
      isResyncBlocked: function (panelName) {
        return guard.isBlocked(panelName);
      },
    };
  }

  // Browser wiring: attaches the store to the Evennia emitter.
  function createBrowserState(Protocol) {
    var store = Protocol.createStore();
    var guard = createOneSyncGuard();
    var generation = 0;
    var wired = false;
    var Evennia = null;
    var awaitingSyncRetry = createAwaitingSyncRetry(function () {
      return store.getState();
    }, sendSync, SYNC_RETRY_MAX_ATTEMPTS);

    function sendSync() {
      if (Evennia && Evennia.isConnected()) {
        Evennia.msg("ui_sync", [Protocol.syncEnvelope()], {});
      }
    }

    // Each receiver callback captures the generation active when it was
    // registered; a callback firing after a reconnect is tagged with an
    // older generation and the store discards it first. Because the Evennia
    // emitter keeps one listener per message name, re-registering on every
    // connection_open re-tags the active receivers with the new generation.
    function registerMessageListeners() {
      var taggedGeneration = generation;
      ["ui_snapshot", "ui_update", "ui_action_result", "ui_protocol_error"].forEach(
        function (name) {
          Evennia.emitter.on(name, function (args, kwargs) {
            store.receive(taggedGeneration, name, args, kwargs);
          });
        }
      );
    }

    function wire(evennia) {
      if (wired) {
        return;
      }
      wired = true;
      Evennia = evennia;
      registerMessageListeners();

      Evennia.emitter.on("connection_open", function (args, kwargs) {
        generation += 1;
        guard.clearAll();
        store.beginTransport(generation);
        store.setConnected(true);
        registerMessageListeners();
        sendSync();
        awaitingSyncRetry.arm();
      });

      Evennia.emitter.on("connection_close", function (args, kwargs) {
        store.setConnected(false);
        awaitingSyncRetry.disarm();
      });

      // A reconnecting websocket can emit `connection_open` and send its
      // `ui_sync` before the portal finishes re-attaching the account's
      // puppet, dropping that first sync. `logged_in` is emitted right before
      // the puppet attaches, so a short deferral that re-synchronizes only
      // while still awaiting the initial snapshot makes reconnect robust
      // without creating a sync loop. The stock per-plugin onLoggedIn
      // dispatch is preserved (the emitter holds one listener per event).
      Evennia.emitter.on("logged_in", function (args, kwargs) {
        if (
          typeof window.plugin_handler === "object" &&
          window.plugin_handler &&
          typeof window.plugin_handler.onLoggedIn === "function"
        ) {
          window.plugin_handler.onLoggedIn(args, kwargs);
        }
        window.setTimeout(function () {
          if (store.getState().phase === "awaiting_initial_snapshot") {
            sendSync();
          }
        }, 500);
      });
    }

    return {
      wire: wire,
      isWired: function () {
        return wired;
      },
      getState: function () {
        return store.getState();
      },
      subscribe: function (listener) {
        return store.subscribe(listener);
      },
      // Acceptance seam: drive the live reducer directly (see the browser
      // test suite), exactly like the emitter receivers do.
      receive: function (messageGeneration, messageName, args, kwargs) {
        return store.receive(messageGeneration, messageName, args, kwargs);
      },
      requestResync: function (panelName) {
        if (!guard.request(panelName)) {
          return false;
        }
        sendSync();
        return true;
      },
      resetResyncEpisode: function (panelName) {
        guard.resetEpisode(panelName);
      },
      isResyncBlocked: function (panelName) {
        return guard.isBlocked(panelName);
      },
      // Bounded awaiting-snapshot resync. The browser plugin drives `tick`
      // on a timer while armed; Node drives it directly.
      syncRetryTick: function () {
        return awaitingSyncRetry.tick();
      },
      isSyncRetryArmed: function () {
        return awaitingSyncRetry.isArmed();
      },
      syncRetryAttempts: function () {
        return awaitingSyncRetry.attempts();
      },
      isSyncRetryExhausted: function () {
        return awaitingSyncRetry.isExhausted();
      },
    };
  }

  return {
    createOneSyncGuard: createOneSyncGuard,
    createStateController: createStateController,
    createBrowserState: createBrowserState,
    createAwaitingSyncRetry: createAwaitingSyncRetry,
    SYNC_RETRY_INTERVAL_MS: SYNC_RETRY_INTERVAL_MS,
    SYNC_RETRY_MAX_ATTEMPTS: SYNC_RETRY_MAX_ATTEMPTS,
  };
});

// Register with Evennia's plugin handler so `init()` runs after the emitter
// exists. Skipped entirely under Node where `window` is absent.
if (
  typeof window !== "undefined" &&
  window.plugin_handler &&
  window.Elosern &&
  window.Elosern.Protocol
) {
  (function () {
    "use strict";
    var browserState = null;

    // When the awaiting-snapshot budget is spent the transport never reached
    // the active phase, usually because the browser's authenticated uid is
    // genuinely gone (the Django session expired or the portal restarted), so
    // no further `ui_sync` can ever succeed. One guarded page reload fires the
    // HTTP request the middleware needs to restore the uid. The reload is
    // strictly one-shot per tab session: the marker lasts until a fresh tab,
    // so a persistent failure never enters a reload loop. A plain abnormal
    // close does not reach this point: the portal protocol preserves the
    // shared-login uid for reconnects (server/conf/websocket_protocol.py).
    var RECOVERY_MARKER = "elosern.sync_recovery_reload";
    function attemptOneShotRecoveryReload() {
      if (
        typeof window.sessionStorage === "object" &&
        window.sessionStorage !== null
      ) {
        if (window.sessionStorage.getItem(RECOVERY_MARKER)) {
          return;
        }
        window.sessionStorage.setItem(RECOVERY_MARKER, "1");
      }
      window.location.reload();
    }

    var elosernStatePlugin = {
      init: function () {
        browserState = window.Elosern.State.createBrowserState(window.Elosern.Protocol);
        browserState.wire(window.Evennia);
        window.Elosern.StateController = browserState;
        // Drive the bounded awaiting-snapshot resync. The timer is inert while
        // the retry is disarmed (connected, active, or closed); retries stop
        // on adoption, disconnect, or budget exhaustion.
        window.setInterval(function () {
          if (!browserState.isSyncRetryArmed()) {
            return;
          }
          if (
            browserState.syncRetryTick() !== "sent" &&
            browserState.isSyncRetryExhausted()
          ) {
            attemptOneShotRecoveryReload();
          }
        }, window.Elosern.State.SYNC_RETRY_INTERVAL_MS);
      },
      getState: function () {
        return browserState ? browserState.getState() : null;
      },
    };
    window.plugin_handler.add("elosern_state", elosernStatePlugin);
  })();
}
