/*
 * Elosern character-creation action-dock renderer.
 *
 * In creation mode the action dock presents preset cards and the custom form
 * (name, adult ages, race/subrace, six bounded allocations) driven through the
 * DOM-independent creation-menu model and the KeyboardRouter. Finite lists
 * (root, preset cards, confirmation screens) navigate with arrow keys and
 * Enter; the custom form uses native Tab/Shift+Tab field navigation, native
 * radio arrow selection for race/subrace, and bounded integer inputs. Escape
 * pops exactly one menu level without discarding the saved server draft.
 * Every server string is inserted through text APIs, never trusted HTML; focus
 * is distinguishable without color; validation messages are bound to their
 * field and announced through the accessible live region.
 *
 * Mode ownership is exclusive: when the client atomically adopts a non-creation
 * mode, this dock synchronously unloads, unregisters its keyboard handler and
 * form key listener, discards local state, and never resets the keyboard
 * router (the exploration/combat dock owns action-dock focus after activation).
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

  var dock = {
    _mounted: false,
    _ownsKeyboard: false,
    _model: null,
    _view: "root", // root | presets | custom | confirm
    _customState: null,
    _customDirty: false,
    _pendingActivate: null,
    _confirmItems: [],
    _keydownBound: null,
    _formKeyBound: null,
    _lastSignature: null,
    _lastEpoch: null,
    _focusKey: null,

    isActive: function () {
      return this._mounted;
    },

    _discardLocalState: function () {
      this._view = "root";
      this._customState = null;
      this._customDirty = false;
      this._pendingActivate = null;
      this._confirmItems = [];
      this._focusKey = null;
      this._unbindFormKeys();
    },

    _unbindFormKeys: function () {
      if (this._formKeyBound) {
        document.removeEventListener("keydown", this._formKeyBound, true);
        this._formKeyBound = null;
      }
    },

    _mount: function (root, panel) {
      var self = this;
      this._model = window.Elosern.CreationMenu.buildMenus(panel);
      this._mounted = true;
      root.setAttribute("data-mode", "creation");
      var keyboard = getKeyboard();
      // A saved server draft resumes at the saved stage: a preset draft opens
      // the confirmation screen, a custom draft opens the restored form. No
      // activation is ever auto-submitted.
      var draft = panel.draft;
      if (draft && draft.mode === "preset") {
        this._view = "confirm";
        this._pendingActivate = "preset";
        this._confirmItems = window.Elosern.CreationMenu.activateConfirm(
          draft.preset_key
        ).items;
        this._renderDock(root, panel);
        if (keyboard) {
          keyboard.reset({ items: this._confirmItems, focusKey: null });
          this._ownsKeyboard = true;
        }
      } else if (draft && draft.mode === "custom") {
        this._view = "custom";
        this._customState = window.Elosern.CreationMenu.stateFromDraft(panel, draft);
        this._renderDock(root, panel);
        if (keyboard) {
          keyboard.reset({ items: [], focusKey: null });
          this._ownsKeyboard = true;
        }
        var first = el("creation-field-displayName");
        if (first) {
          first.focus();
        }
      } else {
        this._view = "root";
        this._renderDock(root, panel);
        if (keyboard) {
          keyboard.reset(this._model.menus.root);
          this._ownsKeyboard = true;
        }
      }
      this._renderFocusHint();
    },

    _unmount: function (root) {
      this._unbindFormKeys();
      this._discardLocalState();
      this._model = null;
      this._mounted = false;
      this._ownsKeyboard = false;
      this._lastSignature = null;
      // The combat dock owns the action-dock DOM in combat mode; the services
      // dock restores guidance otherwise. This dock never resets the router.
      if (root && root.getAttribute("data-mode") !== "combat") {
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
      var heading = makeElement("div", "creation-heading");
      setText(heading, "建立你的角色");
      root.appendChild(heading);

      var body = makeElement("div", "creation-body");
      body.id = "creation-body";
      root.appendChild(body);

      var detail = makeElement("div", "creation-detail");
      detail.id = "creation-detail";
      detail.setAttribute("role", "region");
      detail.setAttribute("aria-label", "角色建立說明");
      root.appendChild(detail);

      var live = makeElement("div", "creation-live elosern-live");
      live.id = "elosern-action-live";
      live.setAttribute("role", "status");
      live.setAttribute("aria-live", "polite");
      live.setAttribute("aria-atomic", "true");
      root.appendChild(live);

      this._renderView(root, panel);
    },

    _renderView: function (root, panel) {
      var body = el("creation-body");
      if (!body) {
        return;
      }
      while (body.firstChild) {
        body.removeChild(body.firstChild);
      }
      this._unbindFormKeys();
      if (this._view === "presets") {
        this._renderPresetList(body, panel);
      } else if (this._view === "custom") {
        this._renderCustomForm(body, panel);
        this._bindFormKeys();
      } else if (this._view === "confirm") {
        this._renderConfirm(body, panel);
      } else {
        this._renderRootMenu(body, panel);
      }
    },

    _renderRootMenu: function (body, panel) {
      var self = this;
      this._currentItems().forEach(function (item, index) {
        var button = makeElement("button", "creation-control");
        button.type = "button";
        button.setAttribute("data-creation-key", item.key);
        button.classList.add("focused");
        setText(button, item.label);
        body.appendChild(button);
      });
    },

    _renderPresetList: function (body, panel) {
      var self = this;
      var items = this._currentItems();
      items.forEach(function (item, index) {
        var button = makeElement("button", "creation-control creation-preset");
        button.type = "button";
        button.setAttribute("data-preset-key", item.presetKey || "");
        if (self._focusKey === item.key) {
          button.classList.add("focused");
          button.setAttribute("aria-current", "true");
        }
        if (!item.enabled) {
          button.classList.add("disabled");
          button.setAttribute("aria-disabled", "true");
        }
        setText(button, item.label);
        body.appendChild(button);
      });
    },

    _renderConfirm: function (body, panel) {
      var screen = makeElement("div", "creation-confirm");
      var title = makeElement("div", "creation-confirm-title");
      var text =
        this._pendingActivate === "preset"
          ? "確認啟用此預設角色？此操作無法回復。"
          : this._pendingActivate === "reset"
            ? "確認清除角色草稿？此操作無法回復。"
            : "確認建立此角色？此操作無法回復。";
      setText(title, text);
      screen.appendChild(title);
      body.appendChild(screen);
      this._renderConfirmButtons(body);
    },

    _renderConfirmButtons: function (body) {
      var self = this;
      (this._currentConfirmItems()).forEach(function (item) {
        var button = makeElement("button", "creation-control");
        button.type = "button";
        button.setAttribute("data-creation-key", item.key);
        setText(button, item.label);
        body.appendChild(button);
      });
    },

    _renderCustomForm: function (body, panel) {
      var self = this;
      if (!this._customState) {
        this._customState = window.Elosern.CreationMenu.stateFromDraft(
          panel,
          panel.draft
        );
      }
      var state = this._customState;
      var custom = panel.custom;
      var form = makeElement("div", "creation-form");
      form.setAttribute("role", "form");
      form.setAttribute("aria-label", "自訂角色表單");
      body.appendChild(form);

      this._appendField(form, "姓名", "displayName", state.displayName, "text", 80, "角色姓名（1–80 字元）");
      this._appendField(form, "實際年齡", "age", state.age, "number", null, "實際年齡（至少 18）");
      this._appendField(form, "外表年齡", "apparentAge", state.apparentAge, "number", null, "外表年齡（至少 18）");

      var raceGroup = makeElement("div", "creation-race");
      var raceTitle = makeElement("div", "creation-field-label");
      setText(raceTitle, "種族");
      raceGroup.appendChild(raceTitle);
      window.Elosern.CreationMenu.raceOptions(panel).forEach(function (option, index) {
        var label = makeElement("label", "creation-radio");
        var input = document.createElement("input");
        input.type = "radio";
        input.name = "creation-race";
        input.value = option.key;
        input.id = "creation-race-" + index;
        input.checked = state.raceKey === option.key;
        input.addEventListener("change", function () {
          self._selectRace(option.key);
        });
        label.appendChild(input);
        var text = document.createTextNode(option.key);
        label.appendChild(text);
        raceGroup.appendChild(label);
      });
      form.appendChild(raceGroup);

      var subraces = window.Elosern.CreationMenu.subraceOptions(panel, state.raceKey);
      if (subraces !== null) {
        var subraceGroup = makeElement("div", "creation-subrace");
        var subraceTitle = makeElement("div", "creation-field-label");
        setText(subraceTitle, "子種族");
        subraceGroup.appendChild(subraceTitle);
        var noSub = makeElement("label", "creation-radio");
        var noInput = document.createElement("input");
        noInput.type = "radio";
        noInput.name = "creation-subrace";
        noInput.value = "";
        noInput.checked = state.subraceKey === null;
        noInput.addEventListener("change", function () {
          self._selectSubrace(null);
        });
        noSub.appendChild(noInput);
        noSub.appendChild(document.createTextNode("無子種族"));
        subraceGroup.appendChild(noSub);
        subraces.forEach(function (entry, index) {
          var label = makeElement("label", "creation-radio");
          var input = document.createElement("input");
          input.type = "radio";
          input.name = "creation-subrace";
          input.value = entry.key;
          input.checked = state.subraceKey === entry.key;
          input.addEventListener("change", function () {
            self._selectSubrace(entry.key);
          });
          label.appendChild(input);
          label.appendChild(document.createTextNode(entry.display_name_zh));
          subraceGroup.appendChild(label);
        });
        form.appendChild(subraceGroup);
      }

      var profile = window.Elosern.CreationMenu.profileFor(panel, state.raceKey, state.subraceKey);
      var budget = profile ? profile.budget : null;
      if (budget !== null) {
        var budgetLine = makeElement("div", "creation-budget");
        setText(budgetLine, "配點總和需等於 " + budget + "。");
        form.appendChild(budgetLine);
      }

      var axes = window.Elosern.CreationMenu.axisFields(panel, state);
      axes.forEach(function (field) {
        self._appendField(
          form,
          field.label,
          field.axis,
          state.allocations[field.axis] || "",
          "number",
          field.maximum,
          field.label + "（" + field.minimum + "–" + field.maximum + "）：" + field.explanation
        );
      });

      var actions = makeElement("div", "creation-form-actions");
      var submit = makeElement("button", "creation-control creation-submit");
      submit.type = "button";
      submit.id = "creation-submit";
      submit.setAttribute("data-creation-key", "submit-custom");
      setText(submit, "確認建立");
      actions.appendChild(submit);
      var reset = makeElement("button", "creation-control creation-reset");
      reset.type = "button";
      reset.id = "creation-reset";
      reset.setAttribute("data-creation-key", "reset-custom");
      setText(reset, "清除草稿");
      actions.appendChild(reset);
      var cancel = makeElement("button", "creation-control creation-cancel");
      cancel.type = "button";
      cancel.setAttribute("data-creation-key", "cancel-custom");
      setText(cancel, "返回");
      actions.appendChild(cancel);
      form.appendChild(actions);
    },

    _appendField: function (form, label, key, value, type, max, hint) {
      var field = makeElement("div", "creation-field");
      var fieldLabel = makeElement("label", "creation-field-label");
      fieldLabel.setAttribute("for", "creation-field-" + key);
      setText(fieldLabel, label);
      field.appendChild(fieldLabel);
      var input = document.createElement("input");
      input.type = type;
      input.id = "creation-field-" + key;
      input.setAttribute("data-creation-field", key);
      if (type === "number") {
        input.setAttribute("inputmode", "numeric");
        input.setAttribute("min", "0");
        input.setAttribute("step", "1");
        if (max !== null && max !== undefined) {
          input.setAttribute("max", String(max));
        }
      } else {
        input.setAttribute("maxlength", String(max || 80));
      }
      input.value = value || "";
      var self = this;
      input.addEventListener("input", function () {
        self._onFieldInput(key, input.value);
      });
      field.appendChild(input);
      var message = makeElement("div", "creation-field-message");
      message.id = "creation-field-message-" + key;
      message.setAttribute("aria-live", "polite");
      field.appendChild(message);
      form.appendChild(field);
    },

    _onFieldInput: function (key, value) {
      if (!this._customState) {
        return;
      }
      if (key === "displayName") {
        this._customState.displayName = value;
      } else if (key === "age") {
        this._customState.age = value;
      } else if (key === "apparentAge") {
        this._customState.apparentAge = value;
      } else if (this._customState.allocations[key] !== undefined) {
        this._customState.allocations[key] = value;
      }
      this._customDirty = true;
    },

    _selectRace: function (raceKey) {
      if (!this._customState) {
        return;
      }
      this._customState.raceKey = raceKey;
      this._customState.subraceKey = null;
      this._customState.allocations = window.Elosern.CreationMenu.emptyAllocations
        ? window.Elosern.CreationMenu.emptyAllocations()
        : this._customState.allocations;
      this._customDirty = true;
      this._refreshCustomForm();
      // Restore focus onto the newly selected race radio so a player can keep
      // arrowing through the finite list without the re-render stealing focus.
      var options = window.Elosern.CreationMenu.raceOptions(this._model.panel);
      for (var i = 0; i < options.length; i++) {
        if (options[i].key === raceKey) {
          var input = el("creation-race-" + i);
          if (input) {
            input.focus();
          }
          break;
        }
      }
    },

    _selectSubrace: function (subraceKey) {
      if (!this._customState) {
        return;
      }
      this._customState.subraceKey = subraceKey;
      this._customDirty = true;
      this._refreshCustomForm();
      var inputs = document.querySelectorAll("input[name=creation-subrace]");
      for (var i = 0; i < inputs.length; i++) {
        if (
          (inputs[i].value === "" && subraceKey === null) ||
          inputs[i].value === subraceKey
        ) {
          inputs[i].focus();
          break;
        }
      }
    },

    _refreshCustomForm: function () {
      var root = el("action-dock");
      if (root && this._mounted && this._view === "custom") {
        this._renderDock(root, this._model.panel);
      }
    },

    _bindFormKeys: function () {
      var self = this;
      this._unbindFormKeys();
      this._formKeyBound = function (event) {
        if (!self._mounted || self._view !== "custom") {
          return;
        }
        if (event.key === "Escape") {
          event.preventDefault();
          event.stopPropagation();
          self._leaveCustom();
          return;
        }
        if (event.key === "Enter") {
          var target = event.target;
          if (target && (target.id === "creation-submit" || target.id === "creation-reset" || target.id === "creation-field-age" || target.id === "creation-field-apparentAge")) {
            // The form owns these Enter keys; stop propagation so the same
            // keydown can never confirm a menu pushed by the handler itself.
            event.preventDefault();
            event.stopPropagation();
            if (target.id === "creation-submit") {
              self._submitCustom();
              return;
            }
            if (target.id === "creation-reset") {
              self._openResetConfirm();
              return;
            }
            if (target.id === "creation-field-age") {
              var next = el("creation-field-apparentAge");
              if (next) {
                next.focus();
              }
              return;
            }
            if (target.id === "creation-field-apparentAge") {
              self._submitCustom();
              return;
            }
          }
        }
      };
      document.addEventListener("keydown", this._formKeyBound, true);
    },

    _openResetConfirm: function () {
      this._pendingActivate = "reset";
      this._confirmItems = window.Elosern.CreationMenu.confirmMenu(
        "確認清除角色草稿？此操作無法回復。",
        window.Elosern.CreationMenu.RESET_ACTION,
        {},
        null
      ).items;
      this._view = "confirm";
      var keyboard = getKeyboard();
      if (keyboard) {
        keyboard.pushMenu({ items: this._confirmItems, focusKey: null });
      }
      var root = el("action-dock");
      if (root && this._mounted) {
        this._renderDock(root, this._model.panel);
      }
    },

    _leaveCustom: function () {
      var keyboard = getKeyboard();
      this._view = "root";
      this._customDirty = false;
      // Pop the custom marker menu; Escape returns to the root menu level.
      if (keyboard) {
        keyboard.popMenu();
        keyboard.replaceMenu(this._model.menus.root);
      }
      var root = el("action-dock");
      if (root && this._mounted) {
        this._renderDock(root, this._model.panel);
      }
    },

    _submitCustom: function () {
      var panel = this._model && this._model.panel;
      if (!panel) {
        return;
      }
      var state = this._customState;
      var result = window.Elosern.CreationMenu.validateCustom(panel, state);
      if (!result.valid) {
        var messages = Object.keys(result.errors).map(function (key) {
          return result.errors[key];
        });
        this._announce(messages.join(" "));
        var self = this;
        Object.keys(result.errors).forEach(function (key) {
          var messageEl = el("creation-field-message-" + key);
          if (messageEl) {
            setText(messageEl, result.errors[key]);
          }
        });
        return;
      }
      var actions = getActions();
      if (!actions) {
        return;
      }
      var payload = window.Elosern.CreationMenu.customPayload(state);
      actions.submit(window.Elosern.CreationMenu.CUSTOM_ACTION, payload);
      this._pendingActivate = "custom";
      this._confirmItems = window.Elosern.CreationMenu.activateConfirm(null).items;
      this._view = "confirm";
      var keyboard = getKeyboard();
      if (keyboard) {
        keyboard.pushMenu({ items: this._confirmItems, focusKey: null });
      }
      var root = el("action-dock");
      if (root) {
        this._renderDock(root, panel);
      }
    },

    _announce: function (text) {
      var live = el("elosern-action-live");
      if (live) {
        setText(live, text);
      }
    },

    _currentItems: function () {
      if (!this._model) {
        return [];
      }
      if (this._view === "presets") {
        return this._model.menus.presets.items;
      }
      return this._model.menus.root.items;
    },

    _currentConfirmItems: function () {
      return this._confirmItems || [];
    },

    _renderFocusHint: function () {
      var detail = el("creation-detail");
      if (!detail || !this._model) {
        return;
      }
      var items = this._currentItems();
      var focused = null;
      var self = this;
      items.forEach(function (item) {
        if (focused === null && item.key === self._focusKey) {
          focused = item;
        }
      });
      if (focused === null && items.length > 0) {
        focused = items[0];
      }
      setText(detail, (focused && focused.description) || "");
    },

    onRouterEvent: function (name, payload) {
      if (!this._mounted) {
        return;
      }
      if (name === "focus" || name === "disabled") {
        var item = payload && payload.item;
        this._focusKey = item ? item.key : this._focusKey;
        var root = el("action-dock");
        var body = root && root.querySelector(".creation-body");
        if (body && this._view !== "custom") {
          this._renderView(root, this._model && this._model.panel);
        }
        this._renderFocusHint();
      } else if (name === "menu-closed" || name === "escape-root") {
        if (this._view === "presets") {
          this._view = "root";
        } else if (this._view === "confirm") {
          // Escape pops exactly one menu level from a confirmation screen:
          // back to the preset list or the custom form, without activating or
          // clearing the saved server wizard draft.
          this._view = this._pendingActivate === "preset" ? "presets" : "custom";
          this._pendingActivate = null;
          this._confirmItems = [];
          this._customDirty = false;
        }
        if (name === "escape-root") {
          // escape-root does not pop a router level, so re-sync the router to
          // the menu matching the restored view (a resumed preset draft mounts
          // its confirmation items as the single router frame).
          var router = getKeyboard();
          if (router) {
            if (this._view === "presets") {
              router.replaceMenu(this._model.menus.presets);
            } else if (this._view === "custom") {
              router.replaceMenu({ items: [], focusKey: null });
            } else {
              router.replaceMenu(this._model.menus.root);
            }
          }
        }
        var dockRoot = el("action-dock");
        if (dockRoot && this._mounted) {
          this._renderView(dockRoot, this._model && this._model.panel);
        }
        this._renderFocusHint();
      }
    },

    handleItem: function (item) {
      var keyboard = getKeyboard();
      if (!keyboard || !this._model) {
        return;
      }
      if (item.openSubmenu === "presets") {
        this._view = "presets";
        keyboard.pushMenu(this._model.menus.presets);
        this._refreshDock();
        return;
      }
      if (item.openSubmenu === "custom") {
        this._view = "custom";
        // A marker menu gives Escape a level to pop without discarding values.
        keyboard.pushMenu({ items: [], focusKey: null });
        this._refreshDock();
        var first = el("creation-field-displayName");
        if (first) {
          first.focus();
        }
        return;
      }
      if (item.presetKey) {
        var actions = getActions();
        if (actions) {
          actions.submit(window.Elosern.CreationMenu.PRESET_ACTION, {
            preset_key: item.presetKey,
          });
        }
        this._pendingActivate = "preset";
        this._confirmItems = window.Elosern.CreationMenu.activateConfirm(
          item.presetKey
        ).items;
        this._view = "confirm";
        keyboard.pushMenu({ items: this._confirmItems, focusKey: null });
        this._refreshDock();
        return;
      }
      if (
        item.actionId === window.Elosern.CreationMenu.ACTIVATE_ACTION ||
        item.actionId === window.Elosern.CreationMenu.RESET_ACTION
      ) {
        var submitActions = getActions();
        if (submitActions) {
          submitActions.submit(item.actionId, item.payload || {});
        }
        return;
      }
      if (item.key && item.key.indexOf("cancel-") === 0) {
        keyboard.popMenu();
        this._view = this._pendingActivate === "preset" ? "presets" : "custom";
        this._pendingActivate = null;
        this._refreshDock();
        return;
      }
    },

    _refreshDock: function () {
      var root = el("action-dock");
      if (root && this._mounted && this._model) {
        this._renderDock(root, this._model.panel);
        this._renderFocusHint();
      }
    },

    _panelSignature: function (panel) {
      var custom = panel.custom;
      return (
        panel.presets.map(function (card) {
          return card.key;
        }).join(",") +
        "|" +
        custom.races.map(function (race) {
          return race.key;
        }).join(",") +
        "|" +
        (panel.draft
          ? window.Elosern.Protocol.canonicalJson
            ? window.Elosern.Protocol.canonicalJson(panel.draft)
            : JSON.stringify(panel.draft)
          : "none")
      );
    },
  };

  function panelAvailable(state) {
    var panel = state.panels && state.panels["creation"];
    return state.mode === "creation" && panel && panel.available === true;
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
          var panel = state.panels["creation"];
          var signature = dock._panelSignature(panel);
          if (!dock._mounted) {
            dock._mount(root, panel);
          } else if (epochChanged) {
            dock._model = window.Elosern.CreationMenu.buildMenus(panel);
            dock._renderDock(root, panel);
            var keyboard = getKeyboard();
            if (keyboard) {
              keyboard.reset(dock._model.menus.root);
              dock._ownsKeyboard = true;
              dock._view = "root";
              dock._focusKey = null;
            }
          } else if (signature !== dock._lastSignature) {
            // A newer snapshot refreshes server-declared choices. Typed unsent
            // custom values are preserved locally and never auto-resubmitted.
            var wasCustom = dock._view === "custom" && dock._customDirty;
            var priorCustom = dock._customState;
            dock._model = window.Elosern.CreationMenu.buildMenus(panel);
            dock._renderDock(root, panel);
            if (wasCustom && priorCustom) {
              dock._customState = priorCustom;
              dock._renderDock(root, panel);
              dock._announce("伺服器資料已更新，請重新確認你的輸入後再提交。");
            } else {
              var kb = getKeyboard();
              if (kb && dock._view === "root") {
                kb.replaceMenu(dock._model.menus.root);
              }
            }
          }
          dock._lastSignature = signature;
        } else if (dock._mounted) {
          // Exploration/combat mode: the owning dock manages the action-dock;
          // the creation dock only cleans up itself and never resets the
          // keyboard router here.
          dock._unmount(root);
        }
      });
    },
  };

  window.Elosern = window.Elosern || {};
  window.Elosern.creationDock = dock;
  if (window.plugin_handler) {
    window.plugin_handler.add("elosern_creation_dock", plugin);
  }
})();
