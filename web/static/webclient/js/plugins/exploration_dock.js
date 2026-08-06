/*
 * Elosern exploration action-dock renderer.
 *
 * In exploration mode this dock owns the action-dock surface: the stable
 * Move/Look/Interact/Character/Quests/Inventory root, per-category submenus,
 * scripted dialogue keyword buttons, free-form dialogue that opens the command
 * drawer with a server-held target reference, and the re-homed services
 * submenus. It is driven through the DOM-independent exploration-menu model
 * and the KeyboardRouter; every server string is inserted through text APIs,
 * never trusted HTML. No take/drop or generic object-mutation control is ever
 * rendered.
 *
 * Mode ownership is exclusive: when the client atomically adopts a `combat`
 * mode, this dock synchronously unloads, unregisters its keyboard handlers,
 * discards local selection/speech state, and only the combat dock owns
 * action-dock focus. When exploration mode returns it remounts from the
 * canonical snapshot.
 */
(function () {
  "use strict";

  function el(id) {
    return document.getElementById(id);
  }

  function setText(element, text) {
    if (!element) {
      return;
    }
    while (element.firstChild) {
      element.removeChild(element.firstChild);
    }
    element.appendChild(document.createTextNode(text == null ? "" : String(text)));
  }

  function makeElement(tag, className) {
    var element = document.createElement(tag);
    if (className) {
      element.className = className;
    }
    return element;
  }

  function getController() {
    return (
      (window.Elosern && window.Elosern.StateController) || null
    );
  }

  function getKeyboard() {
    return (window.Elosern && window.Elosern.keyboard) || null;
  }

  function getActions() {
    return (window.Elosern && window.Elosern.actions) || null;
  }

  function getServices() {
    return (window.Elosern && window.Elosern.serviceDock) || null;
  }

  function getCharacter() {
    return (window.Elosern && window.Elosern.characterDock) || null;
  }

  var dock = {
    _mounted: false,
    _ownsKeyboard: false,
    _model: null,
    _currentMenuKey: "root",
    _focusKey: null,
    _pendingFreeform: null,
    _characterActive: false,
    _restForm: null,
    _restKeydownBound: null,
    _unsubscribe: null,
    _lastSignature: null,

    isActive: function () {
      return this._mounted;
    },

    isCharacterActive: function () {
      return this._characterActive;
    },

    // Reset the keyboard to the exploration root with focus at index 0.
    resetToRoot: function () {
      var keyboard = getKeyboard();
      if (keyboard && this._model) {
        keyboard.reset(this._model.menus.root);
      }
      this._currentMenuKey = "root";
      this._focusKey = null;
      this._characterActive = false;
      var services = getServices();
      if (services && services.isActive && services.isActive()) {
        services.leaveService();
      }
      var character = getCharacter();
      if (character && character.isActive && character.isActive()) {
        character.hide();
      }
      this._refresh();
    },

    // Returns a keyboard menu key when the current router frame belongs to this
    // dock's model, or null.
    _menuKeyForFrame: function () {
      var keyboard = getKeyboard();
      var item = keyboard ? keyboard.currentItem() : null;
      if (!item) {
        return "root";
      }
      return this._currentMenuKey;
    },

    _discardLocalState: function () {
      this._currentMenuKey = "root";
      this._focusKey = null;
      this._pendingFreeform = null;
      this._characterActive = false;
      this._restForm = null;
      this._unbindRestKeys();
      this._clearFreeformState();
    },

    _unbindRestKeys: function () {
      if (this._restKeydownBound) {
        document.removeEventListener("keydown", this._restKeydownBound, true);
        this._restKeydownBound = null;
      }
    },

    _clearFreeformState: function () {
      this._pendingFreeform = null;
      var services = getServices();
      if (services && typeof services.leaveService === "function") {
        services.leaveService();
      }
      var character = getCharacter();
      if (character && typeof character.hide === "function") {
        character.hide();
      }
      this._characterActive = false;
    },

    _mount: function (root, panel, state) {
      var self = this;
      this._model = window.Elosern.ExplorationMenu.buildMenus(panel, {
        currentNode: this._currentNodeFrom(state),
      });
      this._mounted = true;
      root.setAttribute("data-mode", "exploration");
      this._currentMenuKey = "root";
      this._renderDock(root, panel);
      var keyboard = getKeyboard();
      if (keyboard) {
        keyboard.reset(this._model.menus.root);
        this._ownsKeyboard = true;
      }
      this._renderFocusHint();
    },

    _currentNodeFrom: function (state) {
      var localMap = state && state.panels && state.panels["local_map"];
      return localMap && localMap.available === true ? localMap.current_node : null;
    },

    _unmount: function (root) {
      this._discardLocalState();
      this._model = null;
      this._mounted = false;
      this._ownsKeyboard = false;
      this._lastSignature = null;
      // In combat or creation mode the owning dock controls the action-dock
      // DOM; this dock must never wipe it. Guidance is restored only when
      // exploration mode returns without an available exploration panel.
      var mode = root && root.getAttribute("data-mode");
      if (mode !== "combat" && mode !== "creation") {
        this._renderGuidance(root);
      }
    },

    _renderGuidance: function (root) {
      var guidance = el("action-dock-guidance");
      if (guidance) {
        var note = el("action-dock-description");
        if (note) {
          setText(note, "圖形化動作選單尚未開放。請使用底部指令輸入列輸入指令。");
        }
      } else if (root) {
        while (root.firstChild) {
          root.removeChild(root.firstChild);
        }
        var p = makeElement("p", "action-guidance");
        p.id = "action-dock-guidance";
        var span = makeElement("span", "action-guidance-note");
        span.id = "action-dock-description";
        setText(span, "圖形化動作選單尚未開放。請使用底部指令輸入列輸入指令。");
        p.appendChild(span);
        root.appendChild(p);
      }
      if (root && !el("elosern-action-live")) {
        var live = makeElement("div", "elosern-live");
        live.id = "elosern-action-live";
        live.setAttribute("role", "status");
        live.setAttribute("aria-live", "polite");
        live.setAttribute("aria-atomic", "true");
        root.appendChild(live);
      }
    },

    _renderDock: function (root, panel) {
      while (root.firstChild) {
        root.removeChild(root.firstChild);
      }
      var heading = makeElement("div", "exploration-heading");
      setText(heading, "探索");
      root.appendChild(heading);

      var menu = makeElement("div", "exploration-menu");
      menu.setAttribute("role", "group");
      menu.setAttribute("aria-label", "探索選單");
      root.appendChild(menu);
      root.appendChild(this._buildDetailPane());

      var live = makeElement("div", "exploration-live elosern-live");
      live.id = "elosern-action-live";
      live.setAttribute("role", "status");
      live.setAttribute("aria-live", "polite");
      root.appendChild(live);

      this._renderMenuItems(menu, panel);
    },

    _buildDetailPane: function () {
      var detail = makeElement("div", "exploration-detail");
      detail.id = "exploration-detail";
      detail.setAttribute("role", "region");
      detail.setAttribute("aria-label", "說明");
      return detail;
    },

    _currentItems: function () {
      if (!this._model) {
        return [];
      }
      var menu = this._model.menus[this._currentMenuKey];
      return (menu && menu.items) || [];
    },

    _renderMenuItems: function (menu, panel) {
      if (!window.Elosern || !window.Elosern.DockSurface) {
        return;
      }
      window.Elosern.DockSurface.renderRows(menu, this._currentItems(), {
        focusKey: this._focusKey,
        idPrefix: "exploration-row",
      });
    },

    _renderFocusHint: function () {
      var detail = el("exploration-detail");
      if (!detail || !this._model) {
        return;
      }
      var items = this._currentItems();
      var focused = null;
      items.forEach(function (item) {
        if (focused === null && item.key === dock._focusKey) {
          focused = item;
        }
      });
      if (focused === null && items.length > 0) {
        focused = items[0];
      }
      var text = "";
      if (focused) {
        if (focused.enabled === false) {
          text =
            (focused.disabledReason && focused.disabledReason.message) ||
            focused.description ||
            "";
        } else {
          text = focused.description || "";
        }
      }
      setText(detail, text);
    },

    _refresh: function () {
      var root = el("action-dock");
      if (!root || !this._model) {
        return;
      }
      var menuEl = root.querySelector(".exploration-menu");
      if (menuEl) {
        this._renderMenuItems(menuEl, this._model.panel);
      }
      this._renderFocusHint();
    },

    // Router event bridge called by elosern_ui.js.
    onRouterEvent: function (name, payload) {
      if (!this._mounted) {
        return;
      }
      if (name === "focus" || name === "disabled") {
        var item = payload && payload.item;
        this._focusKey = item ? item.key : this._focusKey;
        this._refresh();
      } else if (name === "menu-closed" || name === "escape-root") {
        // Returning to the exploration root (keyboard depth 1) tears down any
        // active service/character sub-view and re-renders the root.
        var keyboard = getKeyboard();
        var depth = keyboard ? keyboard.depth() : 0;
        if (depth <= 1) {
          var services = getServices();
          if (services && services.isActive && services.isActive()) {
            services.leaveService();
          }
          var character = getCharacter();
          if (character && character.isActive && character.isActive()) {
            character.hide();
          }
          this._characterActive = false;
          this._currentMenuKey = "root";
          this._focusKey =
            keyboard && keyboard.currentItem() ? keyboard.currentItem().key : null;
          var root = el("action-dock");
          var menuEl = root && root.querySelector(".exploration-menu");
          if (menuEl) {
            this._renderMenuItems(menuEl, this._model && this._model.panel);
          }
          this._renderFocusHint();
        }
      }
    },

    handleItem: function (item) {
      var keyboard = getKeyboard();
      var actions = getActions();
      if (!keyboard || !this._model) {
        return;
      }
      if (item.openSubmenu) {
        this._currentMenuKey = item.openSubmenu;
        keyboard.pushMenu(this._model.menus[item.openSubmenu]);
        this._refresh();
        return;
      }
      if (item.openTarget) {
        var target = window.Elosern.ExplorationMenu.targetById(this._model, item.openTarget);
        if (target) {
          var targetMenu = window.Elosern.ExplorationMenu.targetMenuFor(this._model, target);
          this._model.menus["target-" + target.identity] = targetMenu;
          this._currentMenuKey = "target-" + target.identity;
          keyboard.pushMenu(targetMenu);
          this._refresh();
        }
        return;
      }
      if (item.openKeywords) {
        var focusedTarget = this._focusedTarget();
        if (focusedTarget) {
          var scripted = window.Elosern.ExplorationMenu.scriptedAffordanceFor(focusedTarget);
          var keywordMenu = window.Elosern.ExplorationMenu.keywordMenuFor(
            this._model,
            focusedTarget,
            scripted
          );
          this._model.menus["keywords-" + focusedTarget.identity] = keywordMenu;
          this._currentMenuKey = "keywords-" + focusedTarget.identity;
          keyboard.pushMenu(keywordMenu);
          this._refresh();
        }
        return;
      }
      if (item.openCharacter) {
        this._openCharacter();
        return;
      }
      if (item.openServiceSubmenu) {
        this._openService(item.openServiceSubmenu);
        return;
      }
      if (item.freeform) {
        this._pendingFreeform = { npcId: item.npcId };
        this._openFreeformDrawer();
        return;
      }
      if (item.openRestForm) {
        this._openRestForm();
        return;
      }
      if (item.actionId && actions) {
        actions.submit(item.actionId, item.payload || {});
      }
    },

    // Bounded rest-duration form: the browser collects a seconds value and the
    // server parses/validates it; the browser never advances its own clock.
    _openRestForm: function () {
      this._restForm = { raw: "", max: 43200 };
      this._renderRestForm();
      this._bindRestKeys();
    },

    _renderRestForm: function () {
      var root = el("action-dock");
      if (!root || !this._restForm) {
        return;
      }
      var wrapper = root.querySelector(".exploration-rest-form");
      if (wrapper) {
        wrapper.parentNode.removeChild(wrapper);
      }
      var form = makeElement("div", "exploration-rest-form");
      form.id = "exploration-rest-form";
      var label = makeElement("div", "exploration-rest-label");
      setText(label, "休息秒數（1～" + this._restForm.max + "）：");
      var value = makeElement("div", "exploration-rest-value");
      value.id = "exploration-rest-value";
      setText(value, this._restForm.raw === "" ? "＿" : this._restForm.raw);
      form.appendChild(label);
      form.appendChild(value);
      root.appendChild(form);
    },

    _bindRestKeys: function () {
      var self = this;
      this._unbindRestKeys();
      this._restKeydownBound = function (event) {
        var form = self._restForm;
        if (!form) {
          return;
        }
        var key = event.key;
        if (key >= "0" && key <= "9") {
          event.preventDefault();
          event.stopPropagation();
          if (form.raw.length < 8) {
            form.raw += key;
          }
          self._renderRestForm();
          return;
        }
        if (key === "Backspace") {
          event.preventDefault();
          event.stopPropagation();
          form.raw = form.raw.slice(0, -1);
          self._renderRestForm();
          return;
        }
        if (key === "Escape") {
          event.preventDefault();
          event.stopPropagation();
          self._restForm = null;
          self._unbindRestKeys();
          self._reenterMenu();
          return;
        }
        if (key === "Enter") {
          event.preventDefault();
          event.stopPropagation();
          var seconds = parseInt(form.raw, 10);
          if (!form.raw || !Number.isInteger(seconds) || seconds < 1 || seconds > form.max) {
            var detail = el("exploration-detail");
            if (detail) {
              setText(detail, "請輸入 1～" + form.max + " 的有效秒數。");
            }
            return;
          }
          var actions = getActions();
          if (actions) {
            actions.submit("explore.wait", { seconds: seconds });
          }
          self._restForm = null;
          self._unbindRestKeys();
          self._reenterMenu();
          return;
        }
      };
      document.addEventListener("keydown", this._restKeydownBound, true);
    },

    _reenterMenu: function () {
      var keyboard = getKeyboard();
      if (keyboard && this._model) {
        var menu = this._model.menus[this._currentMenuKey] || this._model.menus.root;
        keyboard.replaceMenu(menu);
      }
      this._refresh();
    },

    _focusedTarget: function () {
      var keyboard = getKeyboard();
      var item = keyboard ? keyboard.currentItem() : null;
      var target = null;
      if (item && item.key && item.key.indexOf("talk-scripted") !== -1) {
        var targets = this._model.panel.interact || [];
        var currentTargetKey = null;
        for (var i = 0; i < targets.length; i++) {
          if (this._currentMenuKey === "target-" + targets[i].identity) {
            currentTargetKey = targets[i].identity;
            break;
          }
        }
        if (currentTargetKey !== null) {
          target = window.Elosern.ExplorationMenu.targetById(this._model, currentTargetKey);
        }
      }
      return target;
    },

    _openCharacter: function () {
      var root = el("action-dock");
      var character = getCharacter();
      if (root && character && typeof character.show === "function") {
        this._characterActive = true;
        character.show(root);
      }
    },

    _openService: function (surface) {
      var controller = getController();
      var state = controller ? controller.getState() : null;
      var servicesPanel = state && state.panels && state.panels["services"];
      var root = el("action-dock");
      var services = getServices();
      if (root && servicesPanel && servicesPanel.available === true && services) {
        var menuKey = surface === "guild" || surface === "shop" ? surface : surface;
        services.enterService(root, servicesPanel, menuKey);
      }
    },

    _openFreeformDrawer: function () {
      var drawer = window.Elosern && window.Elosern.drawer;
      if (drawer && typeof drawer.open === "function") {
        drawer.open();
      }
    },

    // Release the borrowed-drawer reference. Called by the drawer whenever it
    // closes for any reason other than this dock's own successful consume,
    // and whenever a send is routed as ordinary text, so a cancelled dialogue
    // can never capture a later command.
    clearPendingFreeform: function () {
      this._pendingFreeform = null;
    },

    // Called by elosern_ui when the drawer sends text; returns true when the
    // text was consumed as a free-form dialogue action.
    consumeFreeformText: function (text) {
      if (!this._pendingFreeform || !text || !text.trim()) {
        return false;
      }
      var actions = getActions();
      if (!actions) {
        return false;
      }
      var payload = { npc_id: this._pendingFreeform.npcId, speech: text };
      actions.submit("explore.talk_freeform", payload);
      this._pendingFreeform = null;
      return true;
    },

    hasPendingFreeform: function () {
      return this._pendingFreeform !== null;
    },

    _panelSignature: function (panel) {
      var move = (panel.move || []).map(function (row) {
        return row.exit_ref + ":" + (row.enabled ? "1" : "0");
      }).join(",");
      var look = (panel.look.entities || []).length + ":" + (panel.look.objects || []).length;
      var interact = (panel.interact || []).map(function (target) {
        return (
          target.identity +
          ":" +
          target.affordances.map(function (a) {
            return a.kind + ":" + (a.action_id || a.surface || "");
          }).join("+")
        );
      }).join(",");
      return (
        move +
        "|" +
        look +
        "|" +
        interact +
        "|" +
        panel.quests.available +
        ":" +
        panel.inventory.available
      );
    },
  };

  function panelAvailable(state) {
    var panel = state.panels && state.panels["exploration"];
    return state.mode === "exploration" && panel && panel.available === true;
  }

  var plugin = {
    init: function () {
      var controller = getController();
      if (!controller || !controller.subscribe) {
        return;
      }
      var lastEpoch = null;
      controller.subscribe(function (state) {
        var root = el("action-dock");
        if (!root) {
          return;
        }
        var epochChanged = state.activeEpoch && state.activeEpoch !== lastEpoch;
        if (epochChanged) {
          lastEpoch = state.activeEpoch;
        }
        if (epochChanged && dock._mounted) {
          dock._discardLocalState();
        }
        if (panelAvailable(state)) {
          var panel = state.panels["exploration"];
          var signature = dock._panelSignature(panel);
          if (!dock._mounted) {
            dock._mount(root, panel, state);
          } else if (epochChanged || signature !== dock._lastSignature) {
            dock._model = window.Elosern.ExplorationMenu.buildMenus(panel, {
              currentNode: dock._currentNodeFrom(state),
            });
            dock._currentMenuKey = "root";
            dock._renderDock(root, panel);
            var keyboard = getKeyboard();
            if (keyboard && epochChanged) {
              keyboard.reset(dock._model.menus.root);
              dock._ownsKeyboard = true;
              dock._focusKey = null;
            }
          }
          dock._lastSignature = signature;
        } else if (dock._mounted) {
          dock._unmount(root);
        }
      });
    },
  };

  window.Elosern = window.Elosern || {};
  window.Elosern.explorationDock = dock;
  if (window.plugin_handler) {
    window.plugin_handler.add("elosern_exploration_dock", plugin);
  }
})();
