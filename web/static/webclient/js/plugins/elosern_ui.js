/*
 * Elosern browser UI wiring.
 *
 * Connects the DOM-independent KeyboardRouter and action client to the real
 * Evennia emitter and the GoldenLayout shell: global key handling for `/` and
 * arrows, the command drawer on the ordinary text transport, the
 * non-dismissible offline overlay, and connection-open synchronization.
 *
 * The drawer sends ordinary text through `plugin_handler.onSend` (the same
 * `text` inputfunc path as the normal input field). It never constructs a
 * `ui_action` envelope.
 */
(function () {
  "use strict";

  var drawerOpen = false;
  var pendingDrawerText = null;

  function el(id) {
    return document.getElementById(id);
  }

  function isEditable(target) {
    var node = target && target.tagName;
    return (
      node === "INPUT" ||
      node === "TEXTAREA" ||
      (target && target.isContentEditable)
    );
  }

  function getKeyboard() {
    return (
      window.Elosern &&
      window.Elosern.keyboard
    ) || null;
  }

  function getActions() {
    return (
      window.Elosern &&
      window.Elosern.actions
    ) || null;
  }

  function openDrawer() {
    var field = el("inputfield");
    if (!field) {
      return false;
    }
    drawerOpen = true;
    field.focus();
    return true;
  }

  function closeDrawer(restoreFocus) {
    drawerOpen = false;
    pendingDrawerText = null;
    if (restoreFocus) {
      var dock = el("action-dock");
      if (dock && dock.focus) {
        dock.focus();
      }
    }
  }

  function sendDrawerText() {
    var field = el("inputfield");
    if (!field) {
      return false;
    }
    var text = field.value;
    if (text.trim() === "") {
      return false;
    }
    // Ordinary text through Evennia's text transport; never ui_action.
    if (window.plugin_handler && typeof window.plugin_handler.onSend === "function") {
      window.plugin_handler.onSend(text);
    } else if (window.Evennia) {
      window.Evennia.msg("text", [text], {});
    }
    field.value = "";
    closeDrawer(true);
    return true;
  }

  function routeKeyboard(event) {
    var keyboard = getKeyboard();
    // `/` opens the drawer outside editable fields.
    if (event.key === "/" && !isEditable(event.target)) {
      event.preventDefault();
      if (keyboard) {
        keyboard.handle("/");
      } else {
        openDrawer();
      }
      return true;
    }
    if (!drawerOpen && isEditable(event.target)) {
      // Normal typing in the input field is untouched.
      return false;
    }
    if (drawerOpen) {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendDrawerText();
        return true;
      }
      if (event.key === "Escape") {
        event.preventDefault();
        closeDrawer(true);
        return true;
      }
      return false;
    }
    if (keyboard) {
      var repeat = event.repeat;
      var key = event.key || (event.which === 13 ? "Enter" : null);
      if (!key) {
        return false;
      }
      if (
        ["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Enter", "Escape", " "].indexOf(key) !== -1
      ) {
        event.preventDefault();
      }
      keyboard.handle(key, repeat);
      return true;
    }
    return false;
  }

  // -------------------------------------------------------------------------
  // Offline overlay (5.6): preserve the last view, suppress all mutations.
  // -------------------------------------------------------------------------

  function ensureOverlay() {
    var overlay = el("elosern-offline-overlay");
    if (overlay) {
      return overlay;
    }
    overlay = document.createElement("div");
    overlay.id = "elosern-offline-overlay";
    overlay.setAttribute("role", "alert");
    overlay.setAttribute("aria-live", "assertive");
    overlay.className = "elosern elosern-offline";
    var label = document.createElement("div");
    label.className = "offline-title";
    label.appendChild(document.createTextNode("連線中斷"));
    var note = document.createElement("div");
    note.className = "offline-note";
    note.appendChild(document.createTextNode("已暫停圖形化操作，等待重新連線。"));
    overlay.appendChild(label);
    overlay.appendChild(note);
    document.body.appendChild(overlay);
    return overlay;
  }

  function showOverlay(visible) {
    var overlay = ensureOverlay();
    overlay.style.display = visible ? "block" : "none";
    overlay.setAttribute("data-visible", visible ? "true" : "false");
  }

  // The overlay is removed only after a valid new-epoch snapshot is adopted.
  function updateOverlayFromState() {
    var controller = window.Elosern && window.Elosern.StateController;
    var state = controller ? controller.getState() : null;
    if (!state) {
      showOverlay(true);
      return;
    }
    var ready =
      state.connected &&
      state.phase === "active" &&
      state.activeEpoch &&
      !state.mutationsLocked;
    showOverlay(!ready);
  }

  // -------------------------------------------------------------------------
  // Plugin lifecycle.
  // -------------------------------------------------------------------------

  function wireKeyboardRouter() {
    if (window.Elosern && window.Elosern.KeyboardRouter) {
      var router = window.Elosern.KeyboardRouter.createRouter({
        onEvent: function (name, payload) {
          if (name === "open-drawer") {
            openDrawer();
          } else if (name === "submit") {
            // The action dock emits submit events for its menu items; the
            // concrete action-dock adapter wires specific action IDs.
            var actions = getActions();
            if (actions && payload && payload.item && payload.item.actionId) {
              actions.submit(payload.item.actionId, payload.item.payload || {});
            }
          }
        },
      });
      window.Elosern.keyboard = router;
    }
  }

  function wireActions() {
    if (!window.Elosern || !window.Elosern.Actions || !window.Evennia) {
      return;
    }
    var actions = window.Elosern.Actions.createBrowserActions({
      evennia: window.Evennia,
      controller: window.Elosern.StateController,
      liveRegion: el("elosern-action-live") || null,
    });
    window.Elosern.actions = actions;

    // Evennia's emitter keeps exactly one listener per event name, and the
    // state store owns the OOB receivers (ui_snapshot/ui_update/
    // ui_action_result/ui_protocol_error/connection_open/connection_close).
    // The action client is driven from store subscriptions instead of
    // re-registering those events, so both the store and the action client
    // observe every message.
    var controller = window.Elosern.StateController;
    var lastActionResult = null;
    var wasConnected = null;
    if (controller && typeof controller.subscribe === "function") {
      controller.subscribe(function (state) {
        if (wasConnected === null) {
          wasConnected = state.connected;
        }
        if (state.connected && !wasConnected) {
          // A reconnect must see a still-open in-flight request so it can
          // show the uncertain-result notice instead of retrying.
          actions.handleReconnect();
        }
        wasConnected = state.connected;
        if (state.lastActionResult !== lastActionResult) {
          lastActionResult = state.lastActionResult;
          actions.handleActionResult();
        }
        actions.handlePresentation();
        updateOverlayFromState();
      });
    }
  }

  function wireConnections() {
    // The state store already owns connection_open/connection_close and
    // re-synchronizes on every open; the overlay and action client react
    // through the subscription wired above.
    var controller = window.Elosern && window.Elosern.StateController;
    if (controller && typeof controller.subscribe === "function") {
      controller.subscribe(updateOverlayFromState);
    }
  }

  var plugin = {
    init: function () {
      wireKeyboardRouter();
      wireActions();
      wireConnections();
      document.addEventListener("keydown", routeKeyboard);
      showOverlay(true);
    },
    onSend: function (line) {
      // Ensure no drawer path ever builds a ui_action; text stays text.
      if (drawerOpen) {
        pendingDrawerText = line;
      }
      return null; // allow the stock text command to proceed unchanged
    },
    // Exposed for acceptance tests and focus restoration.
    openDrawer: openDrawer,
    closeDrawer: closeDrawer,
    isDrawerOpen: function () {
      return drawerOpen;
    },
    updateOverlayFromState: updateOverlayFromState,
  };

  window.Elosern = window.Elosern || {};
  window.Elosern.ui = plugin;
  if (window.plugin_handler) {
    window.plugin_handler.add("elosern_ui", plugin);
  }
})();
