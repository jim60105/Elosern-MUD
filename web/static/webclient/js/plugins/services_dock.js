/*
 * Elosern services action-dock renderer (re-homed under the exploration dock).
 *
 * The services submenus (guild, shop, quest log, inventory) are reached only
 * from the exploration dock's Interact/Quests/Inventory roots -- there is no
 * standalone Services root. This dock is mounted by the exploration dock via
 * `enterService(root, panel, menuKey)` and unmounted via `leaveService()`; it
 * never owns the action-dock surface on its own. The `services` panel payload
 * and its seven `guild.*`/`shop.*` adapters are unchanged.
 *
 * When active it renders the bounded quantity form and the destructive-abandon
 * confirmation screen, driven through the DOM-independent service-menu model
 * and the KeyboardRouter. Every server string (labels, disabled reasons, quest
 * detail) is inserted through text APIs, never trusted HTML; focus is
 * distinguishable without color; quantity input accepts bounded integers via
 * keyboard only. A `combat`-mode adoption unloads this dock atomically and
 * never resets the keyboard router (the combat dock owns action-dock focus).
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
    _root: null,

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

    enterService: function (root, panel, menuKey) {
      var self = this;
      this._root = root;
      this._model = window.Elosern.ServiceMenu.buildMenus(panel);
      this._mounted = true;
      this._currentMenuKey = this._model.menus[menuKey] ? menuKey : "guild";
      this._renderDock(root, panel);

      var keyboard = getKeyboard();
      if (keyboard) {
        keyboard.pushMenu(this._model.menus[this._currentMenuKey]);
        this._ownsKeyboard = true;
      }
      this._renderFocusHint();
      if (!this._unsubscribe) {
        var controller = getController();
        if (controller && controller.subscribe) {
          this._unsubscribe = controller.subscribe(function (state) {
            var servicesPanel = state.panels && state.panels["services"];
            if (!dock._mounted || !servicesPanel || servicesPanel.available !== true) {
              return;
            }
            var signature = dock._panelSignature(servicesPanel);
            if (signature !== dock._lastSignature) {
              dock._model = window.Elosern.ServiceMenu.buildMenus(servicesPanel);
              dock._renderDock(root, servicesPanel);
              dock._lastSignature = signature;
            }
          });
        }
      }
      this._lastSignature = this._panelSignature(panel);
    },

    leaveService: function () {
      var root = this._root;
      this._unbindQuantityKeys();
      this._discardLocalState();
      if (this._unsubscribe) {
        this._unsubscribe();
        this._unsubscribe = null;
      }
      this._model = null;
      this._mounted = false;
      this._ownsKeyboard = false;
      this._lastSignature = null;
      this._root = null;
      // The exploration dock owns the action-dock DOM; never wipe its content.
      if (root && root.getAttribute("data-mode") !== "combat") {
        var menuEl = root.querySelector(".services-menu");
        if (menuEl) {
          while (menuEl.firstChild) {
            menuEl.removeChild(menuEl.firstChild);
          }
        }
      }
    },

    _renderDock: function (root, panel) {
      while (root.firstChild) {
        root.removeChild(root.firstChild);
      }
      if (window.Elosern && window.Elosern.DockSurface) {
        window.Elosern.DockSurface.renderGuidance(root, "服務");
      }
      var heading = makeElement("div", "services-heading");
      setText(heading, "服務");
      root.appendChild(heading);

      // The mockup split: item grid on the left, detail pane on the right.
      var layout = makeElement("div", "services-layout");
      var menu = makeElement("div", "services-menu");
      menu.setAttribute("role", "group");
      menu.setAttribute("aria-label", "服務選單");
      layout.appendChild(menu);
      layout.appendChild(this._buildDetailPane());
      root.appendChild(layout);

      var live = makeElement("div", "services-live elosern-live");
      live.id = "elosern-action-live";
      live.setAttribute("role", "status");
      live.setAttribute("aria-live", "polite");
      root.appendChild(live);

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

    _currentMenu: function () {
      if (!this._model) {
        return null;
      }
      return this._model.menus[this._currentMenuKey] || null;
    },

    _renderMenuItems: function (menu, panel) {
      if (!window.Elosern || !window.Elosern.DockSurface) {
        return;
      }
      window.Elosern.DockSurface.renderRows(menu, this._currentItems(), {
        focusKey: this._focusKey,
        idPrefix: "services-row",
        menu: this._currentMenu(),
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
          self._unbindQuantityKeys();
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
            actions.submit(
              item.actionId,
              { item_key: item.itemKey, quantity: value },
              item.commandDisplay || null
            );
          }
          self._quantity = null;
          self._quantityItem = null;
          self._unbindQuantityKeys();
          self._reenterMenu();
          return;
        }
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
        var dockMenu = dockRoot && dockRoot.querySelector(".services-menu");
        if (dockMenu) {
          this._renderMenuItems(dockMenu, this._model && this._model.panel);
        }
        this._renderFocusHint();
      }
    },

    _menuKeyFor: function (currentItem, model) {
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

    handleItem: function (item) {
      var keyboard = getKeyboard();
      if (!keyboard || !this._model) {
        return;
      }
      if (item.openSubmenu) {
        if (item.openSubmenu.indexOf("quest-") === 0) {
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
        this._pendingConfirm = null;
        this._refreshDock();
      }
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

  // The services dock no longer owns the action-dock surface by itself; it is
  // mounted by the exploration dock through `enterService`. Combat/creation
  // adoption unmounts it without ever resetting the keyboard router.
  var plugin = {
    init: function () {
      var controller = getController();
      if (!controller || !controller.subscribe) {
        return;
      }
      controller.subscribe(function (state) {
        if (state.mode === "combat" && dock._mounted) {
          dock.leaveService();
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
