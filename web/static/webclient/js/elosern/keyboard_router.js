/*
 * Elosern keyboard focus router.
 *
 * DOM-independent finite-menu focus model. The router works on a logical menu
 * model (items with enabled/disabled state and list or grid geometry) and
 * emits events; a browser plugin binds real key events to it. It never touches
 * `document` or `window` so the Node suite can exercise focus geometry,
 * submenu backtracking, disabled explanations, and repeated-submission
 * suppression deterministically.
 *
 * Mutation submission is suppressed while a mutation is in flight OR while the
 * active revision has not reached a declared presentation revision.
 */
(function (root, factory) {
  "use strict";
  if (typeof module !== "undefined" && module.exports) {
    module.exports = factory();
  } else {
    root.Elosern = root.Elosern || {};
    root.Elosern.KeyboardRouter = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var ARROW_UP = "ArrowUp";
  var ARROW_DOWN = "ArrowDown";
  var ARROW_LEFT = "ArrowLeft";
  var ARROW_RIGHT = "ArrowRight";
  var ENTER = "Enter";
  var ESCAPE = "Escape";
  var SPACE = " ";
  var SLASH = "/";

  // A menu item. `label` is display text; `enabled` controls submission;
  // `description` (optional) is shown for disabled items.
  function menuItem(label, enabled, description, geometry) {
    return {
      label: label == null ? "" : String(label),
      enabled: enabled !== false,
      description: description == null ? null : String(description),
      geometry: geometry || null,
    };
  }

  // Creates the focus-router controller bound to a callback channel.
  function createRouter(options) {
    options = options || {};
    var emit = options.onEvent || function () {};
    var stack = []; // each entry is {menu, focusRow, focusCol}
    var repeatGuard = null; // {itemKey, key} to suppress held Enter
    var mutationInFlight = false;
    var pendingRevision = null; // declared presentation_revision to await

    function current() {
      return stack.length > 0 ? stack[stack.length - 1] : null;
    }

    function currentMenu() {
      var frame = current();
      return frame ? frame.menu : null;
    }

    function itemAt(frame, row, col) {
      var menu = frame.menu;
      if (menu.grid && menu.gridCols > 0) {
        var index = row * menu.gridCols + col;
        return menu.items[index] || null;
      }
      return menu.items[row] || null;
    }

    function focusRowCol(frame) {
      if (!frame) {
        return null;
      }
      return { row: frame.focusRow, col: frame.focusCol };
    }

    function notifyFocus(frame) {
      var item = itemAt(frame, frame.focusRow, frame.focusCol);
      emit("focus", {
        row: frame.focusRow,
        col: frame.focusCol,
        item: item,
        itemKey: item ? itemKey(item) : null,
      });
    }

    function itemKey(item) {
      return item && item.key !== undefined ? item.key : item && item.label;
    }

    // Move the frame's focus onto the item carrying `key`, emitting `focus`.
    // Returns false without side effects when the key is not in the current
    // frame.
    function focusItemByKey(key) {
      var frame = current();
      if (!frame) {
        return false;
      }
      var menu = frame.menu;
      if (menu.grid && menu.gridCols > 0) {
        for (var row = 0; row < menu.items.length; row += 1) {
          var col = row % menu.gridCols;
          var index = row;
          var candidate = menu.items[index];
          if (candidate && itemKey(candidate) === key) {
            frame.focusRow = Math.floor(index / menu.gridCols);
            frame.focusCol = index % menu.gridCols;
            notifyFocus(frame);
            return true;
          }
        }
        return false;
      }
      for (var listIndex = 0; listIndex < menu.items.length; listIndex += 1) {
        var item = menu.items[listIndex];
        if (item && itemKey(item) === key) {
          frame.focusRow = listIndex;
          notifyFocus(frame);
          return true;
        }
      }
      return false;
    }

    // Move focus within the current menu geometry.
    function move(direction) {
      var frame = current();
      if (!frame) {
        return false;
      }
      var menu = frame.menu;
      if (menu.grid && menu.gridCols > 0) {
        var cols = menu.gridCols;
        var rows = Math.max(1, Math.ceil(menu.items.length / cols));
        var row = frame.focusRow;
        var col = frame.focusCol;
        if (direction === ARROW_UP) {
          row = (row - 1 + rows) % rows;
        } else if (direction === ARROW_DOWN) {
          row = (row + 1) % rows;
        } else if (direction === ARROW_LEFT) {
          col = (col - 1 + cols) % cols;
        } else if (direction === ARROW_RIGHT) {
          col = (col + 1) % cols;
        } else {
          return false;
        }
        // Skip cells that have no item by landing on the nearest previous item.
        var candidate = itemAt(frame, row, col);
        if (!candidate) {
          // fall back to the original focus
          return false;
        }
        frame.focusRow = row;
        frame.focusCol = col;
        notifyFocus(frame);
        return true;
      }

      var items = menu.items;
      if (items.length === 0) {
        return false;
      }
      var index = frame.focusRow;
      if (direction === ARROW_UP) {
        index = (index - 1 + items.length) % items.length;
      } else if (direction === ARROW_DOWN) {
        index = (index + 1) % items.length;
      } else if (direction === ARROW_LEFT || direction === ARROW_RIGHT) {
        // List menus treat horizontal arrows as no-ops (grids handle them).
        return false;
      } else {
        return false;
      }
      frame.focusRow = index;
      notifyFocus(frame);
      return true;
    }

    // Confirm the focused item. `options.source` distinguishes pointer
    // activation from the keyboard: a pointer confirm shares the disabled,
    // locked, and submit gates but neither consults nor sets the held-Enter
    // repeat guard, which exists to suppress key repeat and would otherwise
    // reject a legitimate second click on the same row.
    function confirm(options) {
      var source = (options && options.source) || "keyboard";
      var frame = current();
      if (!frame) {
        return false;
      }
      var item = itemAt(frame, frame.focusRow, frame.focusCol);
      if (!item) {
        return false;
      }
      // Disabled entries stay focusable for their explanation but never submit.
      if (!item.enabled) {
        emit("disabled", { item: item, itemKey: itemKey(item) });
        return false;
      }
      if (mutationInFlight || isAwaitingRevision()) {
        emit("locked", {});
        return false;
      }
      if (source !== "pointer") {
        if (repeatGuard && repeatGuard.key === ENTER && repeatGuard.itemKey === itemKey(item)) {
          emit("repeat-suppressed", { itemKey: itemKey(item) });
          return false;
        }
        repeatGuard = { key: ENTER, itemKey: itemKey(item) };
      }
      emit("submit", { item: item, itemKey: itemKey(item) });
      return true;
    }

    function escape() {
      var frame = current();
      if (!frame) {
        return false;
      }
      if (stack.length === 1) {
        emit("escape-root", {});
        return true;
      }
      var closed = stack.pop();
      var parent = current();
      emit("menu-closed", {
        closedIndex: stack.length,
        returnedItemKey: parent ? itemKey(itemAt(parent, parent.focusRow, parent.focusCol)) : null,
      });
      notifyFocus(parent);
      return true;
    }

    function isAwaitingRevision() {
      return pendingRevision !== null;
    }

    function press(key, repeat) {
      // Held or repeated Enter is suppressed regardless of the current item.
      if (key === ENTER && repeat) {
        emit("repeat-suppressed", { key: ENTER });
        return true;
      }
      if (key === ENTER) {
        return confirm();
      }
      if (key === ESCAPE) {
        return escape();
      }
      if (key === SPACE) {
        emit("space", { item: itemAt(current(), current() ? current().focusRow : 0, current() ? current().focusCol : 0) });
        return true;
      }
      if (key === SLASH) {
        emit("open-drawer", {});
        return true;
      }
      if (key === ARROW_UP || key === ARROW_DOWN || key === ARROW_LEFT || key === ARROW_RIGHT) {
        return move(key);
      }
      return false;
    }

    return {
      // Menu lifecycle.
      pushMenu: function (menu) {
        var frame = {
          menu: menu,
          focusRow: 0,
          focusCol: 0,
        };
        stack.push(frame);
        repeatGuard = null;
        notifyFocus(frame);
        return stack.length;
      },
      replaceMenu: function (menu) {
        if (stack.length === 0) {
          return this.pushMenu(menu);
        }
        stack[stack.length - 1].menu = menu;
        stack[stack.length - 1].focusRow = 0;
        stack[stack.length - 1].focusCol = 0;
        repeatGuard = null;
        notifyFocus(current());
        return stack.length;
      },
      popMenu: function () {
        if (stack.length <= 1) {
          return false;
        }
        var closed = stack.pop();
        notifyFocus(current());
        return true;
      },
      reset: function (menu) {
        stack = menu ? [{ menu: menu, focusRow: 0, focusCol: 0 }] : [];
        repeatGuard = null;
        if (stack.length > 0) {
          notifyFocus(current());
        }
        return stack.length;
      },
      depth: function () {
        return stack.length;
      },
      currentItem: function () {
        var frame = current();
        return frame ? itemAt(frame, frame.focusRow, frame.focusCol) : null;
      },
      // The current frame's menu (read-only); null when no frame is mounted.
      currentMenu: function () {
        return currentMenu();
      },

      // Submission gating.
      setMutationInFlight: function (value) {
        mutationInFlight = !!value;
        if (!mutationInFlight) {
          repeatGuard = null;
        }
      },
      isMutationInFlight: function () {
        return mutationInFlight;
      },
      setAwaitingRevision: function (value) {
        pendingRevision = value === null || value === undefined ? null : value;
      },
      isAwaitingRevision: isAwaitingRevision,
      clearRepeatGuard: function () {
        repeatGuard = null;
      },

      press: press,
      // Adapter helper for browser key handlers.
      handle: function (key, repeat) {
        return press(key, !!repeat);
      },
      focus: focusRowCol,
      focusItemByKey: focusItemByKey,
      confirm: confirm,
    };
  }

  return {
    ARROW_UP: ARROW_UP,
    ARROW_DOWN: ARROW_DOWN,
    ARROW_LEFT: ARROW_LEFT,
    ARROW_RIGHT: ARROW_RIGHT,
    ENTER: ENTER,
    ESCAPE: ESCAPE,
    SPACE: SPACE,
    SLASH: SLASH,
    menuItem: menuItem,
    createRouter: createRouter,
  };
});
