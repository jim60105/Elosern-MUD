/*
 * Elosern action-dispatch client plugin.
 *
 * Sends exact `ui_sync` / `ui_action` envelopes through Evennia's message
 * transport, keeps one in-flight request, gates mutation unlock on the store
 * accepting state at or above the declared presentation revision, never
 * retries after disconnection, and surfaces results and uncertain outcomes
 * through safe text APIs.
 *
 * The request sequencing logic is DOM-independent (`createActionClient`) so
 * the Node suite can verify exactly-once submission, revision gating, no
 * disconnect retry, stale recovery, and the uncertain-result notice. The
 * browser plugin wires it to `window.Evennia` and the store controller.
 */
(function (root, factory) {
  "use strict";
  if (typeof module !== "undefined" && module.exports) {
    module.exports = factory();
  } else {
    root.Elosern = root.Elosern || {};
    root.Elosern.Actions = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var PROTOCOL_VERSION = 1;
  var MAX_REQUEST_ID = 64;

  function validRequestId(value) {
    return (
      typeof value === "string" &&
      value.length >= 1 &&
      value.length <= MAX_REQUEST_ID &&
      /^[A-Za-z0-9:_-]+$/.test(value)
    );
  }

  // Bounded sequence-local request-ID generator.
  function createRequestId(prefix, limit) {
    var counter = 0;
    limit = limit || 1e9;
    return function () {
      counter = (counter % limit) + 1;
      var id = prefix + ":" + counter;
      if (!validRequestId(id)) {
        // Fall back to a bare counter-based id that always satisfies the shape.
        id = "s" + counter;
      }
      return id;
    };
  }

  // A DOM-independent action client bound to a message transport and a store
  // reader. `send(messageName, args)` delivers client->server messages;
  // `getStoreState()` returns the current store state snapshot.
  function createActionClient(options) {
    options = options || {};
    var send = options.send || function () {};
    var getStoreState = options.getStoreState || function () {
      return {};
    };
    var onNotice = options.onNotice || function () {};
    var prefix = options.prefix || "session";
    var newRequestId = createRequestId(prefix);

    var inFlight = null; // {requestId, actionId, presentationRevision}
    var lastResult = null;
    var uncertain = false; // an action result could not be confirmed

    function store() {
      return getStoreState();
    }

    function locked() {
      var state = store();
      if (!state || !state.connected || state.mutationsLocked) {
        return true;
      }
      if (
        state.awaitingInitialSnapshot ||
        state.phase === "awaiting_initial_snapshot" ||
        state.phase === "detached"
      ) {
        return true;
      }
      return false;
    }

    // Returns true when the store has accepted presentation state at or above
    // `revision`. This is the client-side release condition for a mutation.
    function acceptedAtOrAbove(revision) {
      var state = store();
      if (!state || state.revision === null || state.revision === undefined) {
        return false;
      }
      return state.revision >= revision;
    }

    function sync() {
      send("ui_sync", [{ protocol_version: PROTOCOL_VERSION }]);
    }

    // Submits one exact ui_action envelope. Returns the request ID or null
    // when the client is locked (offline, synchronizing, or another mutation
    // is in flight).
    function submit(actionId, payload) {
      var state = store();
      if (locked()) {
        return null;
      }
      if (inFlight) {
        return null;
      }
      var requestId = newRequestId();
      var envelope = {
        protocol_version: PROTOCOL_VERSION,
        presentation_epoch: state.activeEpoch,
        request_id: requestId,
        base_revision: state.revision,
        action_id: actionId,
        payload: payload === undefined ? {} : payload,
      };
      inFlight = { requestId: requestId, actionId: actionId, presentationRevision: null };
      uncertain = false;
      send("ui_action", [envelope]);
      return requestId;
    }

    // Handle one received `ui_action_result` envelope (already validated).
    function onActionResult(result) {
      lastResult = result;
      if (!inFlight || inFlight.requestId !== result.requestId) {
        // A cached duplicate or a result for a request this client no longer
        // tracks; record it without unlocking a foreign request.
        return;
      }
      // The reducer normalizes the wire field `presentation_revision` to
      // `presentationRevision`; accept either spelling.
      var targetRevision = result.presentationRevision;
      if (targetRevision === undefined) {
        targetRevision = result.presentation_revision;
      }
      if (result.epoch !== undefined && store().activeEpoch !== result.epoch) {
        // Result belongs to another epoch; do not unlock the current lock.
        return;
      }
      inFlight.presentationRevision = targetRevision;
      if (result.outcome === "stale") {
        // State changed under us: resynchronize to canonical state. The client
        // releases its lock only after the recovery snapshot is accepted.
        onNotice("stale", result.message);
        sync();
        releaseIfReady();
        return;
      }
      if (result.outcome === "rejected" && result.code === "no_puppet") {
        // The puppet is gone; no presentation will ever gate this rejection,
        // so the in-flight mutation lock is released unconditionally.
        onNotice("result", result.message);
        inFlight = null;
        return;
      }
      if (result.outcome === "error") {
        onNotice("error", result.message);
        releaseIfReady();
        return;
      }
      onNotice("result", result.message);
      releaseIfReady();
    }

    // Release the mutation lock only after the result AND accepted state at or
    // above the declared presentation revision. A malformed recovery snapshot
    // may advance the store beyond the target revision through its one sync;
    // otherwise the UI stays safely locked.
    function releaseIfReady() {
      if (!inFlight) {
        return;
      }
      var target = inFlight.presentationRevision;
      if (target === null || target === undefined) {
        // No revision was declared; nothing to gate on.
        inFlight = null;
        return;
      }
      if (acceptedAtOrAbove(target)) {
        inFlight = null;
      }
    }

    // Called when a new snapshot/update is accepted; reevaluate a pending
    // unlock.
    function onPresentationAccepted(state) {
      if (inFlight && inFlight.presentationRevision !== null && state.revision >= inFlight.presentationRevision) {
        inFlight = null;
      }
    }

    // On reconnect the client resynchronizes and never auto-retries a prior
    // request. If an action was submitted but no result was ever received, an
    // uncertain-result notice is shown after the new snapshot is adopted.
    function onReconnect() {
      var hadInFlight = !!inFlight;
      inFlight = null;
      uncertain = hadInFlight;
      if (uncertain) {
        onNotice("uncertain", "上一次操作的結果無法確認，請重新確認狀態。");
      }
      sync();
    }

    // The puppet detached (OOC): the server retired the dispatch sequence, so
    // an in-flight mutation can never confirm. Release the lock and warn;
    // nothing is retried.
    function onDetached() {
      var hadInFlight = !!inFlight;
      inFlight = null;
      uncertain = hadInFlight;
      if (hadInFlight) {
        onNotice("uncertain", "你已離開角色，前一個操作的結果無法確認。");
      }
    }

    // A new transport generation clears all in-flight state.
    function onTransportReset() {
      inFlight = null;
      uncertain = false;
      lastResult = null;
    }

    return {
      sync: sync,
      submit: submit,
      onActionResult: onActionResult,
      onPresentationAccepted: onPresentationAccepted,
      onReconnect: onReconnect,
      onDetached: onDetached,
      onTransportReset: onTransportReset,
      isLocked: locked,
      isInFlight: function () {
        return !!inFlight;
      },
      inFlightRequestId: function () {
        return inFlight ? inFlight.requestId : null;
      },
      uncertain: function () {
        return uncertain;
      },
      lastResult: function () {
        return lastResult;
      },
    };
  }

  // Browser wiring: binds the DOM-independent client to Evennia.msg and the
  // store controller, and updates the KeyboardRouter submission gate. The
  // optional `echo` callback (one text line per dispatched mutation) is
  // invoked exactly when `submit` dispatches a real request; locked and
  // duplicate submits never echo (design D4).
  function createBrowserActions(options) {
    options = options || {};
    var evennia = options.evennia;
    var controller = options.controller; // window.Elosern.StateController
    var router = options.router || null; // window.Elosern.KeyboardRouter instance
    var liveRegion = options.liveRegion || null; // element for notices
    var keyboard = options.keyboard || null; // keyboard_router bridge
    var echo = options.echo || null; // function(text) -> void

    function send(messageName, args) {
      evennia.msg(messageName, args, {});
    }

    function getStoreState() {
      return controller ? controller.getState() : { connected: false, mutationsLocked: true };
    }

    function setRouterLock() {
      if (keyboard) {
        keyboard.setMutationInFlight(client.isInFlight());
      }
    }

    // Resolve one display command line through the presentation-only catalog
    // and echo it exactly when the request dispatched. `display` is the
    // bounded descriptor attached to the menu item at build time; actions the
    // catalog can resolve without descriptors (wait daypart, forfeit, guild,
    // creation) echo too, while actions whose required label is missing
    // resolve to null and stay silent (D4).
    function echoIfDispatched(actionId, payload, display, requestId) {
      if (requestId === null || !echo) {
        return;
      }
      var line = null;
      if (window.Elosern && window.Elosern.CommandEcho) {
        line = window.Elosern.CommandEcho.commandLine(actionId, payload, display || {});
      }
      if (line) {
        echo(line);
      }
    }

    var client = createActionClient({
      send: send,
      getStoreState: getStoreState,
      prefix: options.prefix || "web",
      onNotice: function (kind, message) {
        // Resolve the live region by ID at notice time: the combat dock swaps
        // the action-dock subtree in and out, so a captured reference can go
        // stale. The fallback keeps the foundation live region working.
        var region = document.getElementById("elosern-action-live") || liveRegion;
        if (region) {
          while (region.firstChild) {
            region.removeChild(region.firstChild);
          }
          region.appendChild(document.createTextNode(message == null ? "" : String(message)));
        }
        if (kind === "uncertain") {
          var overlay = document.getElementById("elosern-offline-overlay");
          if (overlay) {
            overlay.setAttribute("data-uncertain", "true");
          }
        }
        setRouterLock();
      },
    });

    var lastPhase = null;
    return {
      client: client,
      sync: function () {
        client.sync();
      },
      submit: function (actionId, payload, display) {
        var requestId = client.submit(actionId, payload);
        echoIfDispatched(actionId, payload, display, requestId);
        setRouterLock();
        return requestId;
      },
      handleActionResult: function (args) {
        if (controller) {
          // The store already validated and stored the result; feed the client.
          var state = controller.getState();
          if (state && state.lastActionResult) {
            client.onActionResult(state.lastActionResult);
          }
        }
        setRouterLock();
      },
      handlePresentation: function () {
        var state = controller ? controller.getState() : {};
        if (lastPhase !== "detached" && state.phase === "detached") {
          // The puppet detached: an in-flight mutation can never confirm.
          client.onDetached();
        }
        lastPhase = state.phase;
        client.onPresentationAccepted(state);
        setRouterLock();
      },
      handleReconnect: function () {
        client.onReconnect();
        setRouterLock();
      },
      handleTransportReset: function () {
        client.onTransportReset();
        setRouterLock();
      },
    };
  }

  return {
    createRequestId: createRequestId,
    createActionClient: createActionClient,
    createBrowserActions: createBrowserActions,
  };
});
