/*
 * Elosern character action-dock renderer.
 *
 * Renders the read-only version-1 `character` panel (traits, passives,
 * equipment, disguise, guild, wallet) into the action dock when the
 * exploration dock's Character root is open. It is driven through the
 * DOM-independent character-menu model and the KeyboardRouter; every value is
 * true state and the disguise section never substitutes a disguised value for
 * a true trait. The panel is display-only: rows are focusable for scrolling
 * but never submit.
 *
 * Every server string is inserted through text APIs, never trusted HTML, and
 * focus is distinguishable without color.
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

  var dock = {
    _active: false,
    _root: null,
    _focusKey: null,
    _pushedMenu: null,
    _unsubscribe: null,

    isActive: function () {
      return this._active;
    },

    show: function (root) {
      var self = this;
      this._root = root;
      this._active = true;
      this._focusKey = null;
      if (this._unsubscribe) {
        this._unsubscribe();
        this._unsubscribe = null;
      }
      var controller = getController();
      if (controller && controller.subscribe) {
        this._unsubscribe = controller.subscribe(function (state) {
          self._renderFromState(state);
        });
      }
      var state = controller ? controller.getState() : null;
      this._renderFromState(state);
    },

    hide: function () {
      this._active = false;
      this._root = null;
      this._focusKey = null;
      // Return keyboard focus to the exploration root when this dock pushed its
      // menu; the router refuses to pop the last frame, so a stale reference
      // left by the router's own Escape pop is a harmless no-op.
      if (this._pushedMenu) {
        var keyboard = getKeyboard();
        if (keyboard && keyboard.popMenu) {
          keyboard.popMenu();
        }
        this._pushedMenu = null;
      }
      if (this._unsubscribe) {
        this._unsubscribe();
        this._unsubscribe = null;
      }
    },

    _renderFromState: function (state) {
      if (!this._active || !this._root) {
        return;
      }
      var panel = state && state.panels && state.panels["character"];
      if (!panel || panel.available !== true) {
        return;
      }
      var model = window.Elosern.CharacterMenu.buildMenu(panel);
      this._model = model;
      this._renderDock(this._root, panel, model);
      // Stack the read-only menu on top of the exploration root (never
      // `reset`): Escape then pops back to the exploration root instead of
      // leaving the router pointed at display-only rows.
      if (!this._pushedMenu) {
        var keyboard = getKeyboard();
        if (keyboard) {
          // The router frame carries the model's grid geometry so keyboard
          // navigation matches the rendered 2-column cell grid.
          this._pushedMenu = {
            items: model.items,
            grid: model.grid || null,
            gridCols: model.gridCols || null,
          };
          keyboard.pushMenu(this._pushedMenu);
        }
      }
      this._renderFocusHint();
    },

    _renderDock: function (root, panel, model) {
      while (root.firstChild) {
        root.removeChild(root.firstChild);
      }
      if (window.Elosern && window.Elosern.DockSurface) {
        window.Elosern.DockSurface.renderGuidance(root, "角色");
      }
      var heading = makeElement("div", "character-heading");
      setText(heading, "角色狀態");
      root.appendChild(heading);

      // The mockup split: display-only item grid on the left, detail pane on
      // the right.
      var layout = makeElement("div", "character-layout");
      var menu = makeElement("div", "character-menu");
      menu.setAttribute("aria-label", "角色狀態");
      layout.appendChild(menu);

      var detail = makeElement("div", "character-detail");
      detail.id = "character-detail";
      detail.setAttribute("role", "region");
      detail.setAttribute("aria-label", "說明");
      layout.appendChild(detail);
      root.appendChild(layout);

      var live = makeElement("div", "character-live elosern-live");
      live.id = "elosern-action-live";
      live.setAttribute("role", "status");
      live.setAttribute("aria-live", "polite");
      root.appendChild(live);

      // Display-only rows: focusable through the shared surface (a click moves
      // router focus and updates the detail pane) but marked non-submitting,
      // so no row carries an action and nothing is ever submitted. They render
      // as grid cells (character-menu model carries the grid geometry).
      if (window.Elosern && window.Elosern.DockSurface) {
        window.Elosern.DockSurface.renderRows(menu, model.items, {
          focusKey: this._focusKey,
          idPrefix: "character-row",
          nonSubmitting: true,
          menu: model,
        });
      }
    },

    _renderFocusHint: function () {
      var detail = el("character-detail");
      if (!detail || !this._model) {
        return;
      }
      var items = this._model.items;
      var focused = null;
      items.forEach(function (item) {
        if (focused === null && item.key === dock._focusKey) {
          focused = item;
        }
      });
      if (focused === null && items.length > 0) {
        focused = items[0];
      }
      setText(detail, (focused && focused.description) || "");
    },

    onRouterEvent: function (name, payload) {
      if (!this._active) {
        return;
      }
      if (name === "focus") {
        var item = payload && payload.item;
        this._focusKey = item ? item.key : this._focusKey;
        this._renderFocusHint();
      }
    },
  };

  window.Elosern = window.Elosern || {};
  window.Elosern.characterDock = dock;
})();
