/*
 * Elosern services action-dock renderer.
 *
 * In exploration mode the Services root (Guild / Shop / Inventory), the
 * per-surface submenus, the bounded quantity form, the quest-detail pane, and
 * the destructive-abandon confirmation screen are rendered into the action
 * dock and driven through the DOM-independent service-menu model and the
 * KeyboardRouter. Every server string (labels, disabled reasons, quest detail)
 * is inserted through text APIs, never trusted HTML; focus is distinguishable
 * without color; quantity input accepts bounded integers via keyboard only.
 *
 * Mode ownership is exclusive: when the client atomically adopts a `combat`
 * mode, this dock synchronously unloads, unregisters its keyboard handler,
 * discards local quantity/selection/confirmation state, and never resets the
 * keyboard router (the combat dock owns action-dock focus). When exploration
 * mode returns it remounts from the canonical snapshot.
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
    _quantity: null,
    _quantityItem: null,
    _pendingConfirm: null,
    _model: null,
    _currentMenuKey: "root",
    _keydownBound: null,
    _unsubscribe: null,
    _lastSignature: null,
    _focusKey: null,

    isActive: function () {
      return this._mounted;
    },

    _discardLocalState: function () {
      this._quantity = null;
      this._quantityItem = null;
      this._pendingConfirm = null;
      this._currentMenuKey = "root";
      this._focusKey = null;
      this._unbindQuantityKeys();
    },

    _unbindQuantityKeys: function () {
      if (this._keydownBound) {
        document.removeEventListener("keydown", this._keydownBound, true);
        this._keydownBound = null;
      }
    },

    _mount: function (root, panel) {
      var self = this;
      this._model = window.Elosern.ServiceMenu.buildMenus(panel);
      this._mounted = true;
      root.setAttribute("data-mode", "exploration");
      this._renderDock(root, panel);

      var keyboard = getKeyboard();
      if (keyboard) {
        var rootMenu = this._model.menus.root;
        keyboard.reset(rootMenu);
        this._ownsKeyboard = true;
      }

      // Render the focused item's explanation into the detail pane.
      this._renderFocusHint();
    },

    _unmount: function (root) {
      this._unbindQuantityKeys();
      this._discardLocalState();
      this._model = null;
      this._mounted = false;
      this._ownsKeyboard = false;
      this._lastSignature = null;
      // In combat mode the combat dock owns the action-dock DOM; the services
      // dock must never wipe combat controls. Otherwise restore the foundation
      // guidance (including the stable live region).
      if (root && root.getAttribute("data-mode") !== "combat") {
        this._renderGuidance(root);
      }
    },

    _renderGuidance: function (root) {
      // Restore the full foundation action dock (guidance plus the stable
      // live-region element) so combat/reconnect notices keep working after
      // the services dock unloads.
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
      var heading = makeElement("div", "services-heading");
      setText(heading, "公會與商店服務");
      root.appendChild(heading);

      var menu = makeElement("div", "services-menu");
      menu.setAttribute("role", "group");
      menu.setAttribute("aria-label", "服務選單");
      root.appendChild(menu);
      root.appendChild(this._buildDetailPane());

      var live = makeElement("div", "services-live elosern-live");
      live.id = "elosern-action-live";
      live.setAttribute("role", "status");
      live.setAttribute("aria-live", "polite");
      root.appendChild(live);

      // Render the current keyboard menu's items into the DOM so the player
      // can see and operate them at the supported viewports.
      this._renderMenuItems(menu, panel);
      this._renderQuantityForm(root, panel);
      this._renderConfirmScreen(root, panel);
    },

    _buildDetailPane: function () {
      var detail = makeElement("div", "services-detail");
      detail.id = "services-detail";
      detail.setAttribute("role", "region");
      detail.setAttribute("aria-label", "服務說明");
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
      var self = this;
      while (menu.firstChild) {
        menu.removeChild(menu.firstChild);
      }
      this._currentItems().forEach(function (item, index) {
        var button = makeElement("button", "services-control");
        button.type = "button";
        button.setAttribute("data-service-key", item.key);
        if (self._focusKey === item.key) {
          button.classList.add("focused");
          button.setAttribute("aria-current", "true");
        }
        if (!item.enabled) {
          button.classList.add("disabled");
          button.setAttribute("aria-disabled", "true");
        }
        var label = item.label + (item.enabled ? "" : "（無法使用）");
        setText(button, label);
        menu.appendChild(button);
      });
    },

    _renderFocusHint: function () {
      var detail = el("services-detail");
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

    _renderQuantityForm: function (root, panel) {
      var self = this;
      var wrapper = el("services-quantity");
      if (wrapper) {
        wrapper.parentNode.removeChild(wrapper);
      }
      if (!this._quantity) {
        return;
      }
      var form = makeElement("div", "services-quantity");
      form.id = "services-quantity";
      var label = makeElement("div", "services-quantity-label");
      setText(label, "數量（" + this._quantity.min + "～" + this._quantity.max + "）：");
      var value = makeElement("div", "services-quantity-value");
      value.id = "services-quantity-value";
      setText(value, this._quantity.raw === "" ? "＿" : this._quantity.raw);
      form.appendChild(label);
      form.appendChild(value);
      root.appendChild(form);
      this._bindQuantityKeys();
    },

    _renderConfirmScreen: function (root, panel) {
      var wrapper = el("services-confirm");
      if (wrapper) {
        wrapper.parentNode.removeChild(wrapper);
      }
      if (!this._pendingConfirm) {
        return;
      }
      var screen = makeElement("div", "services-confirm");
      screen.id = "services-confirm";
      var title = makeElement("div", "services-confirm-title");
      setText(title, "確認放棄任務？此操作無法回復。");
      screen.appendChild(title);
      root.appendChild(screen);
    },

    _bindQuantityKeys: function () {
      var self = this;
      this._unbindQuantityKeys();
      this._keydownBound = function (event) {
        var quantity = self._quantity;
        if (!quantity) {
          return;
        }
        var key = event.key;
        if (key >= "0" && key <= "9") {
          event.preventDefault();
          event.stopPropagation();
          window.Elosern.ServiceMenu.quantityInput(quantity, key);
          self._refreshQuantityValue();
          return;
        }
        if (key === "Backspace") {
          event.preventDefault();
          event.stopPropagation();
          window.Elosern.ServiceMenu.quantityBackspace(quantity);
          self._refreshQuantityValue();
          return;
        }
        if (key === "Escape") {
          event.preventDefault();
          event.stopPropagation();
          self._quantity = null;
          self._quantityItem = null;
          self._reenterMenu();
          return;
        }
        if (key === "Enter") {
          event.preventDefault();
          event.stopPropagation();
          var value = window.Elosern.ServiceMenu.validateQuantity(quantity);
          if (value === null) {
            self._showQuantityHint("請輸入有效數量。");
            return;
          }
          var item = self._quantityItem;
          var actions = getActions();
          if (item && actions) {
            actions.submit(item.actionId, { item_key: item.itemKey, quantity: value });
          }
          self._quantity = null;
          self._quantityItem = null;
          self._reenterMenu();
          return;
        }
        // Any other key is left to the global router (navigation).
      };
      document.addEventListener("keydown", this._keydownBound, true);
    },

    _refreshQuantityValue: function () {
      var value = el("services-quantity-value");
      if (value && this._quantity) {
        setText(value, this._quantity.raw === "" ? "＿" : this._quantity.raw);
      }
    },

    _showQuantityHint: function (text) {
      var detail = el("services-detail");
      if (detail) {
        setText(detail, text);
      }
    },

    _reenterMenu: function () {
      var keyboard = getKeyboard();
      var root = el("action-dock");
      if (keyboard && this._model) {
        var menu = this._model.menus[this._currentMenuKey] || this._model.menus.root;
        keyboard.replaceMenu(menu);
      }
      if (root && this._model) {
        var menuEl = root.querySelector(".services-menu");
        if (menuEl) {
          this._renderMenuItems(menuEl, this._model.panel);
        }
        this._renderFocusHint();
      }
    },

    // Router event bridge called by elosern_ui.js.
    onRouterEvent: function (name, payload) {
      if (!this._mounted) {
        return;
      }
      if (name === "focus" || name === "disabled") {
        var item = payload && payload.item;
        this._focusKey = item ? item.key : this._focusKey;
        var root = el("action-dock");
        var menuEl = root && root.querySelector(".services-menu");
        if (menuEl) {
          this._renderMenuItems(menuEl, this._model && this._model.panel);
        }
        this._renderFocusHint();
      } else if (name === "menu-closed" || name === "escape-root") {
        var keyboard = getKeyboard();
        var frame = keyboard ? keyboard.currentItem() : null;
        this._currentMenuKey = this._menuKeyFor(frame, this._model);
        var dockRoot = el("action-dock");
        var menuEl = dockRoot && dockRoot.querySelector(".services-menu");
        if (menuEl) {
          this._renderMenuItems(menuEl, this._model && this._model.panel);
        }
        this._renderFocusHint();
      }
    },

    _menuKeyFor: function (currentItem, model) {
      // The current router menu's items let us infer which logical submenu we
      // are inside; fall back to root when no match is found.
      if (!model) {
        return "root";
      }
      var keys = ["root", "guild", "board", "quests", "shop", "stock", "sell", "inventory"];
      for (var i = 0; i < keys.length; i++) {
        var menu = model.menus[keys[i]];
        if (menu && currentItem && currentItem.key) {
          var match = menu.items.some(function (entry) {
            return entry.key === currentItem.key;
          });
          if (match) {
            return keys[i];
          }
        }
      }
      return "root";
    },

    _findQuestRow: function (questId) {
      var guild = this._model && this._model.panel && this._model.panel.guild;
      var rows = (guild && guild.quests) || [];
      for (var i = 0; i < rows.length; i++) {
        if (rows[i].quest_id === questId) {
          return rows[i];
        }
      }
      return null;
    },

    handleItem: function (item) {
      var keyboard = getKeyboard();
      if (!keyboard || !this._model) {
        return;
      }
      if (item.openSubmenu) {
        if (item.openSubmenu.indexOf("quest-") === 0) {
          // Quest rows open a dynamically built detail menu (詳情/放棄/回報).
          var questRow = this._findQuestRow(item.questId);
          if (questRow) {
            var detailMenu = window.Elosern.ServiceMenu.questMenuFor(
              this._model,
              questRow
            );
            keyboard.pushMenu(detailMenu);
            this._currentMenuKey = "quest-detail";
          }
        } else {
          this._currentMenuKey = item.openSubmenu;
          keyboard.pushMenu(this._model.menus[item.openSubmenu]);
        }
        this._refreshDock();
        return;
      }
      if (item.openDetail) {
        var detail = el("services-detail");
        if (detail) {
          setText(detail, item.detail || "");
        }
        return;
      }
      if (item.confirmActionId) {
        this._pendingConfirm = item;
        var confirmation = window.Elosern.ServiceMenu.confirmMenu(
          item.confirmLabel,
          item.confirmActionId,
          item.confirmPayload,
          item.label
        );
        keyboard.pushMenu({ items: confirmation.items, focusKey: null });
        this._refreshDock();
        return;
      }
      if (item.quantity) {
        this._quantity = window.Elosern.ServiceMenu.quantityState(
          item.quantity.min,
          item.quantity.max
        );
        this._quantityItem = item;
        this._refreshDock();
        return;
      }
      if (item.key && item.key.indexOf("cancel-") === 0) {
        keyboard.popMenu();
        this._refreshDock();
      }
    },

    _refreshDock: function () {
      var root = el("action-dock");
      if (!root || !this._model) {
        return;
      }
      var menuEl = root.querySelector(".services-menu");
      if (menuEl) {
        this._renderMenuItems(menuEl, this._model.panel);
      }
      this._renderQuantityForm(root, this._model.panel);
      this._renderConfirmScreen(root, this._model.panel);
      this._renderFocusHint();
    },

    _panelSignature: function (panel) {
      var guild = panel.guild;
      var shop = panel.shop;
      var stockSignature = "";
      var inventorySignature = "";
      if (shop) {
        stockSignature = shop.stock
          .map(function (row) {
            return row.item_key + ":" + row.stock + ":" + row.buy_copper;
          })
          .join(",");
        stockSignature += "|" + shop.sellable.length;
      }
      if (panel.inventory) {
        inventorySignature = panel.inventory.rows
          .map(function (row) {
            return row.item_key + ":" + row.held + ":" + row.equipped;
          })
          .join(",");
      }
      return (
        (guild ? guild.board.length + ":" + guild.quests.length : "0:0") +
        "|" +
        stockSignature +
        "|" +
        inventorySignature +
        "|" +
        panel.player.guild_registered +
        ":" +
        panel.player.wallet +
        ":" +
        panel.player.guild_merit
      );
    },
  };

  function panelAvailable(state) {
    var panel = state.panels && state.panels["services"];
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
        // A new transport epoch (reconnect) discards any unsubmitted local
        // quantity/selection/confirmation state.
        var epochChanged =
          state.activeEpoch && state.activeEpoch !== lastEpoch;
        if (epochChanged) {
          lastEpoch = state.activeEpoch;
        }
        if (epochChanged && dock._mounted) {
          dock._discardLocalState();
        }
        if (panelAvailable(state)) {
          var panel = state.panels["services"];
          var signature = dock._panelSignature(panel);
          if (!dock._mounted) {
            dock._mount(root, panel);
          } else if (epochChanged || signature !== dock._lastSignature) {
            // A newer snapshot refreshes the dock without tearing down an
            // in-progress interaction; only a fresh epoch resets the keyboard.
            dock._model = window.Elosern.ServiceMenu.buildMenus(panel);
            dock._renderDock(root, panel);
            var keyboard = getKeyboard();
            if (keyboard && epochChanged) {
              keyboard.reset(dock._model.menus.root);
              dock._ownsKeyboard = true;
              dock._currentMenuKey = "root";
              dock._focusKey = null;
            } else if (keyboard && dock._currentMenuKey === "root") {
              keyboard.replaceMenu(dock._model.menus.root);
            }
          }
          dock._lastSignature = signature;
        } else if (dock._mounted) {
          // Combat/creation or an unavailable services panel: the owning dock
          // manages the action-dock; the services dock only cleans up itself
          // and never resets the keyboard router here.
          dock._unmount(root);
        }
      });
    },
  };

  window.Elosern = window.Elosern || {};
  window.Elosern.serviceDock = dock;
  if (window.plugin_handler) {
    window.plugin_handler.add("elosern_services_dock", plugin);
  }
})();
