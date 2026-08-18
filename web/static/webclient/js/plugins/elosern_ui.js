/*
 * Elosern browser UI wiring.
 *
 * Connects the DOM-independent KeyboardRouter and action client to the real
 * Evennia emitter and the GoldenLayout shell: plugin-contract key handling
 * for `/` and arrows, the command drawer on the ordinary text transport, the
 * non-dismissible offline overlay, and connection-open synchronization.
 *
 * The drawer component (goldenlayout.js) owns the single send path and sends
 * ordinary text through `plugin_handler.onSend` (the same `text` inputfunc
 * path as the normal input field). Nothing here ever constructs a `ui_action`
 * envelope.
 */
(function () {
  "use strict";

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

  // The drawer's own textarea (inside `.inputfieldwrapper`). Focusing it by
  // pointer never opens the drawer, so the routing gate must treat the field
  // itself as the open drawer: Enter sends, Escape restores dock focus.
  function isDrawerField(target) {
    return !!(
      target &&
      target.id === "inputfield" &&
      target.closest &&
      target.closest(".inputfieldwrapper")
    );
  }

  // A focused suggestion card or dismiss button is a native-button surface:
  // Enter/Space must reach the button's own activation (the card click path
  // is a direct listener, never the KeyboardRouter), so the routing gate
  // defers to the browser default for exactly those keys.
  function isSuggestionButton(target) {
    return !!(
      target &&
      target.closest &&
      (target.closest(".option-card") || target.closest(".suggestions-dismiss"))
    );
  }

  function getKeyboard() {
    return (
      window.Elosern &&
      window.Elosern.keyboard
    ) || null;
  }

  function getServices() {
    return (
      window.Elosern &&
      window.Elosern.serviceDock
    ) || null;
  }

  function getExploration() {
    return (
      window.Elosern &&
      window.Elosern.explorationDock
    ) || null;
  }

  function getCharacter() {
    return (
      window.Elosern &&
      window.Elosern.characterDock
    ) || null;
  }

  function getCreation() {
    return (
      window.Elosern &&
      window.Elosern.creationDock
    ) || null;
  }

  function getActions() {
    return (
      window.Elosern &&
      window.Elosern.actions
    ) || null;
  }

  function getDrawer() {
    return (
      window.Elosern &&
      window.Elosern.drawer
    ) || null;
  }

  function routeKeyboard(event) {
    var keyboard = getKeyboard();
    var drawer = getDrawer();
    // `/` toggles the drawer outside editable fields (D1): the routing gate
    // decides open vs close because only the browser knows the drawer's DOM
    // state; the router just re-emits the intent. While an editable control
    // is focused (the drawer field, a creation form, a rest form) the slash
    // stays ordinary text and never closes the drawer. The rest form is a
    // div-based keyboard surface, so the exploration dock reports its editing
    // state explicitly.
    var exploration = getExploration();
    var restFormEditing =
      !!exploration &&
      typeof exploration.isEditingRestForm === "function" &&
      exploration.isEditingRestForm();
    if (event.key === "/" && !isEditable(event.target) && !restFormEditing) {
      event.preventDefault();
      if (drawer && drawer.isOpen()) {
        drawer.close(true);
      } else if (keyboard) {
        keyboard.handle("/");
      } else if (drawer) {
        drawer.open();
      }
      return true;
    }
    if (restFormEditing && event.key === "/") {
      // The rest form owns the keyboard while it is open; the slash is
      // claimed (never a drawer toggle) and left un-prevented so nothing is
      // swallowed by the routing gate.
      return true;
    }
    if (drawer && (drawer.isOpen() || isDrawerField(event.target))) {
      // The open drawer (or the drawer field focused by any means -- a `/`
      // keystroke, a dock-borrowed free-form dialogue, or a direct pointer
      // click) owns its field. Enter without Shift sends and Escape cancels;
      // every other key typed into the field is claimed (without
      // preventDefault, so normal editing proceeds) so the plugin handler
      // reports no unhandled keydown while the player types. The stock
      // command-history recall keys are not claimed and keep their turn.
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        drawer.send();
        return true;
      }
      if (event.key === "Escape") {
        event.preventDefault();
        drawer.close(true);
        return true;
      }
      if (event.shiftKey && (event.key === "ArrowUp" || event.key === "ArrowDown")) {
        return false;
      }
      return true;
    }
    if (isEditable(event.target)) {
      // Normal typing in the input field is untouched.
      return false;
    }
    if (
      isSuggestionButton(event.target) &&
      (event.key === "Enter" || event.key === " ")
    ) {
      // Native-button activation for the suggestions surface: the key is
      // unclaimed so the browser dispatches the button's own click (the
      // direct card/dismiss listener), never the menu router.
      return false;
    }
    if (keyboard) {
      // jQuery (the vendored 3.2.1) drops the native `repeat` flag from its
      // synthesized event objects; the original event keeps it, so held-key
      // suppression must read through `originalEvent`.
      var repeat =
        !!event.repeat ||
        !!(event.originalEvent && event.originalEvent.repeat);
      var key = event.key || (event.which === 13 ? "Enter" : null);
      if (!key) {
        return false;
      }
      if (
        ["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Enter", "Escape", " "].indexOf(key) !== -1
      ) {
        event.preventDefault();
      }
      return keyboard.handle(key, repeat);
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

  // Set once the shell has rendered a real view at least once. Before that
  // point (a first visit, not yet logged in) there is nothing to preserve,
  // and `phase` never reaches "active" until after login and puppet, so
  // gating on it keeps the non-dismissible full-viewport overlay from
  // trapping every first-time visitor behind it before they can log in.
  var hasBeenActive = false;

  // The overlay is removed only after a valid new-epoch snapshot is adopted.
  function updateOverlayFromState() {
    var controller = window.Elosern && window.Elosern.StateController;
    var state = controller ? controller.getState() : null;
    if (!state) {
      showOverlay(hasBeenActive);
      return;
    }
    if (state.phase === "detached") {
      // The puppet detached (OOC): panels are cleared and mutations locked,
      // but the connection is fine and the drawer stays usable, so the
      // disconnect overlay must not appear.
      showOverlay(false);
      return;
    }
    var ready =
      state.connected &&
      state.phase === "active" &&
      state.activeEpoch &&
      !state.mutationsLocked;
    if (ready) {
      hasBeenActive = true;
    }
    showOverlay(hasBeenActive && !ready);
  }

  // -------------------------------------------------------------------------
  // Plugin lifecycle.
  // -------------------------------------------------------------------------

  // -------------------------------------------------------------------------
  // Combat detail pane: disabled entries stay focusable with an explanation.
  // -------------------------------------------------------------------------

  function setSafeText(element, text) {
    if (!element) {
      return;
    }
    while (element.firstChild) {
      element.removeChild(element.firstChild);
    }
    element.appendChild(document.createTextNode(text == null ? "" : String(text)));
  }

  // On focus or a disabled confirm, show the focused entry's explanation in
  // the combat detail pane (created by the combat dock) without any packet.
  // The pane names the focused item, its cost/availability, and the next key
  // action, matching the mockup's detail pane.
  function renderCombatDetail(payload) {
    var detail = document.getElementById("combat-detail");
    if (!detail) {
      return;
    }
    var item = payload && payload.item;
    if (!item) {
      return;
    }
    var text = "";
    if (item.enabled === false) {
      text =
        (item.disabledReason && item.disabledReason.message) ||
        item.description ||
        "";
    } else {
      text = item.description || "";
      if (item.costText) {
        text += (text ? "　" : "") + item.costText;
      }
      if (item.actionId === "toggle-target") {
        text += (text ? "　" : "") + "Space → 選擇目標";
      } else if (item.confirm || item.key === "area-confirm") {
        text += (text ? "　" : "") + "Enter → 確認施展";
      } else if (item.actionId === "open-skill") {
        text += (text ? "　" : "") + "Enter → 開啟";
      } else if (item.actionId) {
        text += (text ? "　" : "") + "Enter → 執行";
      }
    }
    setSafeText(detail, text);
  }

  function wireKeyboardRouter() {
    if (window.Elosern && window.Elosern.KeyboardRouter) {
      var router = window.Elosern.KeyboardRouter.createRouter({
        onEvent: function (name, payload) {
          if (name === "toggle-drawer") {
            // The routing gate already resolved the drawer's current state:
            // when this event fires, the drawer is closed and must open.
            var drawer = getDrawer();
            if (drawer) {
              drawer.open();
            }
          } else if (name === "submit") {
            handleSubmission(payload);
          } else if (name === "space") {
            handleSpace(payload);
          } else if (name === "focus" || name === "disabled") {
            renderCombatDetail(payload);
            // Arrow-key navigation over combat target descriptors updates the
            // client-local portrait focus; no packet is ever sent.
            var combatDock = window.Elosern && window.Elosern.combatDock;
            if (combatDock && combatDock.publishFocusForItem) {
              combatDock.publishFocusForItem(payload && payload.item);
            }
          }
          // Forward navigation events to the exploration dock so it can keep
          // its DOM rows and detail pane in sync without owning a second
          // router; the active sub-docks (services/character) update the same
          // way.
          var exploration = getExploration();
          if (exploration && exploration.isActive && exploration.isActive()) {
            exploration.onRouterEvent(name, payload);
          }
          var services = getServices();
          if (services && services.isActive && services.isActive()) {
            services.onRouterEvent(name, payload);
          }
          var character = getCharacter();
          if (character && character.isActive && character.isActive()) {
            character.onRouterEvent(name, payload);
          }
          // The creation dock keeps its preset list and detail pane in sync
          // the same way; only the active mode's dock owns the action dock.
          var creation = getCreation();
          if (creation && creation.isActive && creation.isActive()) {
            creation.onRouterEvent(name, payload);
          }
          // The combat dock renders the router's current frame; every frame
          // change re-renders its rows (root, skills, targets, shorthand,
          // forfeit).
          var combatDock = window.Elosern && window.Elosern.combatDock;
          if (combatDock && typeof combatDock.onRouterEvent === "function") {
            combatDock.onRouterEvent(name, payload);
          }
        },
      });
      window.Elosern.keyboard = router;
    }
  }

  // The one client-local art focus bus shared by the combat dock (publisher)
  // and the art renderer (subscriber). Created once so both sides always talk
  // to the same channel; it never sends a packet.
  function ensureArtFocusBus() {
    if (
      !window.Elosern.artFocusBus &&
      window.Elosern &&
      window.Elosern.ArtFocus
    ) {
      window.Elosern.artFocusBus = window.Elosern.ArtFocus.createBus();
    }
  }

  // Combat menu submission wiring (task 4.5): the combat-menu model owns the
  // exact payloads; the action client sends them once the store is unlocked.
  function getCombat() {
    return (window.Elosern && window.Elosern._combat) || null;
  }

  function handleSubmission(payload) {
    var actions = getActions();
    var combat = getCombat();
    var item = payload && payload.item;
    if (!item) {
      return;
    }
    // Service dock navigation events (submenus, quest detail, abandon
    // confirmation, quantity forms) are owned by the services dock; when it is
    // mounted (a re-homed service submenu) it must be consulted first.
    var services = getServices();
    if (services && services.isActive && services.isActive()) {
      if (
        item.openSubmenu ||
        item.openDetail ||
        item.confirmActionId ||
        item.quantity ||
        (item.key && item.key.indexOf("cancel-") === 0)
      ) {
        services.handleItem(item);
        return;
      }
    }
    // Exploration dock navigation events (submenus, targets, keyword buttons,
    // the final back row, character root, re-homed service submenus, free-form
    // dialogue) are owned by the exploration dock.
    var exploration = getExploration();
    if (exploration && exploration.isActive && exploration.isActive()) {
      if (
        item.openSubmenu ||
        item.openTarget ||
        item.openKeywords ||
        item.goBack ||
        item.openCharacter ||
        item.openServiceSubmenu ||
        item.openRestForm ||
        item.freeform
      ) {
        exploration.handleItem(item);
        return;
      }
    }
    // Creation dock navigation events (preset cards, custom form, activation
    // confirmation) are owned by the creation dock.
    var creation = getCreation();
    if (creation && creation.isActive && creation.isActive()) {
      if (
        item.openSubmenu ||
        item.presetKey ||
        item.actionId === "creation.activate" ||
        item.actionId === "creation.preset" ||
        item.actionId === "creation.custom" ||
        (item.key && item.key.indexOf("cancel-") === 0)
      ) {
        creation.handleItem(item);
        return;
      }
    }
    // Internal navigation events first; only real action IDs are sent.
    if (item.actionId === "open-skill" && item.payload && combat) {
      openCombatSkill(combat, item.payload.skillKey);
      return;
    }
    if (item.actionId === "choose-scale" && item.payload && combat) {
      // Freeform scale choice: keep the choice in the skill's client-local
      // selection state, then open the target flow.
      if (combat.focusSkillKey) {
        var scaleSkill = combat.skillByKey[combat.focusSkillKey];
        var chosen = window.Elosern.CombatMenu.chooseScale(
          combat,
          combat.focusSkillKey,
          item.payload.scale
        );
        if (chosen && scaleSkill) {
          var targetMenu = window.Elosern.CombatMenu.openSkillTargets(
            combat,
            combat.focusSkillKey
          );
          var router = getKeyboard();
          if (router && targetMenu) {
            router.pushMenu(targetMenu);
          }
        }
      }
      return;
    }
    if (item.actionId === "toggle-target") {
      // AREA candidates are toggled with Space, not Enter.
      return;
    }
    if (item.actionId === "choose-shorthand" && item.payload && combat) {
      if (combat.focusSkillKey) {
        window.Elosern.CombatMenu.chooseShorthand(
          combat,
          combat.focusSkillKey,
          item.payload.shorthand
        );
      }
      return;
    }
    if (item.key === "attack" && combat) {
      openCombatSkill(combat, window.Elosern.CombatMenu.BASIC_ATTACK_KEY);
      return;
    }
    if (item.key === "skills" && combat) {
      var router = getKeyboard();
      if (router) {
        router.pushMenu(combat.menus.skills);
      }
      return;
    }
    if (item.key === "forfeit" && combat) {
      var router = getKeyboard();
      if (router) {
        router.pushMenu(combat.menus.forfeit);
      }
      return;
    }
    if (item.key === "flee" && combat) {
      // The root flee item carries combat.flee; fall through to submit.
    }
    if (item.confirm && combat && combat.focusSkillKey) {
      // AREA confirmation payload is computed from the live selection state.
      var skill = combat.skillByKey[combat.focusSkillKey];
      if (skill && skill.targetSpec === "area") {
        var payload = window.Elosern.CombatMenu.areaPayload(skill);
        if (payload && actions) {
          // Compose the chosen shorthand (or none) into the display
          // descriptor so the echoed cast line names the actual target.
          var display = {
            skillLabel: skill.label,
            targetLabel: skill.shorthand || null,
          };
          var scaleLabel = window.Elosern.CombatMenu.scaleLabelFor(skill);
          if (scaleLabel !== null) {
            display.scaleLabel = scaleLabel;
          }
          actions.submit("combat.cast", payload, display);
        }
        return;
      }
    }
    if (item.actionId) {
      if (actions) {
        var finalDisplay = item.commandDisplay || null;
        if (
          finalDisplay &&
          finalDisplay.skillLabel &&
          combat &&
          combat.focusSkillKey
        ) {
          // Label the echoed cast line with the chosen freeform magnitude.
          var finalSkill = combat.skillByKey[combat.focusSkillKey];
          if (finalSkill) {
            var finalScale = window.Elosern.CombatMenu.scaleLabelFor(finalSkill);
            if (finalScale !== null) {
              finalDisplay = Object.assign({}, finalDisplay, {
                scaleLabel: finalScale,
              });
            }
          }
        }
        actions.submit(item.actionId, item.payload || {}, finalDisplay);
      }
    }
  }

  function openCombatSkill(combat, skillKey) {
    var router = getKeyboard();
    if (!router) {
      return;
    }
    combat.focusSkillKey = skillKey;
    var menu = window.Elosern.CombatMenu.openSkill(combat, skillKey);
    if (menu) {
      router.pushMenu(menu);
      // The freeform scale step preselects 威力×1 (the default behavior).
      if (menu.items.length > 0 && menu.items[0].scaleChoice) {
        router.focusItemByKey("scale-1");
      }
    }
  }

  function handleSpace(payload) {
    var combat = getCombat();
    var keyboard = getKeyboard();
    var item = payload && payload.item;
    if (!combat || !keyboard || !item) {
      return;
    }
    if (item.actionId === "toggle-target" && item.payload) {
      var skillKey = combat.focusSkillKey;
      if (!skillKey) {
        return;
      }
      window.Elosern.CombatMenu.toggleArea(combat, skillKey, item.payload.identity);
      // The toggle is client-local; re-render the current frame so the
      // selection marker updates without any router event.
      var combatDock = window.Elosern && window.Elosern.combatDock;
      if (combatDock && typeof combatDock.refreshRows === "function") {
        combatDock.refreshRows();
      }
    }
  }

  function wireActions() {
    if (!window.Elosern || !window.Elosern.Actions || !window.Evennia) {
      return;
    }
    var actions = window.Elosern.Actions.createBrowserActions({
      evennia: window.Evennia,
      controller: window.Elosern.StateController,
      keyboard: getKeyboard(),
      liveRegion: el("elosern-action-live") || null,
      // Every dispatched mutation echoes its resolved command line into the
      // narrative once (D4); the goldenlayout facade owns the append path.
      echo:
        window.Elosern && window.Elosern.narrativeInput
          ? window.Elosern.narrativeInput.appendInput
          : null,
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
      ensureArtFocusBus();
      wireKeyboardRouter();
      wireActions();
      wireConnections();
      // One delegated pointer listener on the stable action-dock element,
      // installed at shell init, survives every dock re-render.
      if (window.Elosern && window.Elosern.DockSurface) {
        window.Elosern.DockSurface.installPointerBridge();
      }
      // Not shown here: before the first successful activation the overlay
      // stays off (see hasBeenActive) so the stock login/creation flow under
      // it stays usable for a first-time visitor.
    },
    onSend: function (line) {
      // Ensure no drawer path ever builds a ui_action; text stays text.
      return null; // allow the stock text command to proceed unchanged
    },
    // Key handling runs through the plugin contract so the plugin handler
    // claims exactly the events the router (or the open drawer) consumed.
    onKeydown: routeKeyboard,
    // Exposed for acceptance tests and focus restoration.
    openDrawer: function () {
      var drawer = getDrawer();
      return drawer ? drawer.open() : false;
    },
    closeDrawer: function (restoreFocus) {
      var drawer = getDrawer();
      if (drawer) {
        drawer.close(!!restoreFocus);
      }
    },
    isDrawerOpen: function () {
      var drawer = getDrawer();
      return drawer ? drawer.isOpen() : false;
    },
    updateOverlayFromState: updateOverlayFromState,
  };

  window.Elosern = window.Elosern || {};
  window.Elosern.ui = plugin;
  if (window.plugin_handler) {
    window.plugin_handler.add("elosern_ui", plugin);
  }
})();
