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
 *
 * Dual frame contract (webclient-declarative-frame-stack): the stack holds
 * declarative frames `{descriptor, focusKey}` beside the transitional legacy
 * `{menu, focusRow, focusCol}` frames (the legacy shape stays byte-for-byte
 * until its surface family migrates; an unknown shape throws at the push
 * site). A declarative frame's menu is resolved through the injected
 * `resolve(descriptor)` at the MOMENT of every read — render, arrow geometry,
 * trail, activation payload — never from data captured when the frame was
 * opened. An unresolvable declarative frame pops one level (cascading while
 * the next top frame is also unresolvable, or returning to the root when the
 * frame opted into `unresolvableAction: "root"`); only an unresolvable ROOT
 * frame degrades in place into the single disabled marker-reason row. Zero
 * timers: every degradation is a synchronous access-time settle.
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

  // The local fallback line for an unresolvable root frame carrying no
  // server-authored reason (webclient-frame-resolution).
  var DEGRADED_ROOT_FALLBACK = "畫面狀態已更新，請返回上層";

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
    // Each entry is a transitional legacy frame {menu, focusRow, focusCol}
    // or a declarative frame {descriptor, focusKey, ...router-private state}.
    var stack = [];
    var repeatGuard = null; // {itemKey, key} to suppress held Enter
    var mutationInFlight = false;
    var pendingRevision = null; // declared presentation_revision to await
    // Declarative-frame resolution (webclient-declarative-frame-stack D1):
    // the store injects the registry seam; every declarative read resolves
    // through it at the moment of the read. Without an injected resolver the
    // router keeps the transitional legacy shape only.
    var resolve = typeof options.resolve === "function" ? options.resolve : null;
    // Settle re-entrancy guard: the focus emit re-enters the store (which
    // reads the router again); the outer settle loop owns the cascade.
    var settling = false;

    // --- Dual frame contract helpers ---------------------------------------

    // Transitional legacy frame: {menu, focusRow, focusCol}, behaves exactly
    // as today until its surface family migrates. Declarative frame:
    // {descriptor: {source, params}, focusKey} plus router-private focus
    // geometry and the pop-policy fields the store sets at push time
    // (openerKey, unresolvableAction). Any other shape is a programming
    // error and throws at the push site rather than degrading silently.
    function isDeclarative(frame) {
      return !!(frame && frame.descriptor);
    }

    function assertFrameShape(shape) {
      var frame = shape.frame;
      if (frame && frame.descriptor) {
        if (typeof frame.descriptor.source !== "string" || frame.descriptor.source === "") {
          throw new TypeError("declarative frame descriptor requires a string source");
        }
        return;
      }
      if (frame && frame.menu) {
        return;
      }
      throw new TypeError(
        "unknown router frame shape: expected {descriptor, focusKey} or {menu, focusRow, focusCol}"
      );
    }

    function isMarker(value) {
      return !!(value && value.unresolvable === true);
    }

    // The frame's menu at the moment of the read. Legacy frames return their
    // stored copy; declarative frames resolve through the registry seam.
    // Resolution itself never pops — `settleTop` owns the pop policy so a
    // cascade runs exactly once per access with zero timers.
    function frameMenu(frame) {
      if (!frame) {
        return null;
      }
      if (!isDeclarative(frame)) {
        return frame.menu;
      }
      return resolve ? resolve(frame.descriptor) : null;
    }

    // The degraded-root presentation (webclient-frame-resolution): the
    // single disabled marker-reason row presented when the ROOT frame itself
    // is unresolvable and no parent remains to return to. Built fresh on
    // demand from the live resolution, never stored in the frame.
    function isDegradedRoot(frame) {
      return (
        stack.length === 1 &&
        !!frame &&
        stack[0] === frame &&
        isDeclarative(frame) &&
        isMarker(frameMenu(frame))
      );
    }

    function degradedMenu() {
      var frame = stack.length > 0 ? stack[0] : null;
      var marker = frame && isDeclarative(frame) ? frameMenu(frame) : null;
      var reason = marker && typeof marker.reason === "string" && marker.reason !== ""
        ? marker.reason
        : null;
      var item = menuItem(reason || DEGRADED_ROOT_FALLBACK, false, null);
      item.key = "degraded-root";
      return { items: [item], grid: false, title: "" };
    }

    // Geometry + focus-key projection for one declarative frame from its
    // resolved menu. Focus lands on the same key at its new index; a lost key
    // lands on the nearest surviving index to the router-private `_focusIndex`
    // cache (ties resolve to the earlier row); an empty menu focuses nothing.
    // The cache is an internal nearest-rule memory, never a retained menu copy.
    function projectFocus(frame, menu) {
      if (!frame || !isDeclarative(frame)) {
        return;
      }
      var items = menu && Array.isArray(menu.items) ? menu.items : [];
      if (items.length === 0) {
        frame.focusKey = null;
        frame._focusIndex = 0;
        frame.focusRow = 0;
        frame.focusCol = 0;
        return;
      }
      var index = -1;
      if (frame.focusKey !== null && frame.focusKey !== undefined) {
        for (var k = 0; k < items.length; k += 1) {
          if (items[k] && itemKey(items[k]) === frame.focusKey) {
            index = k;
            break;
          }
        }
      }
      if (index < 0) {
        var cached = typeof frame._focusIndex === "number" ? frame._focusIndex : 0;
        var best = 0;
        for (var i = 0; i < items.length; i += 1) {
          // Strictly-less comparison scanning left-to-right: equal distance
          // keeps the earlier row (the spec's earlier-row tie rule).
          if (Math.abs(i - cached) < Math.abs(best - cached)) {
            best = i;
          }
        }
        index = best;
      }
      frame._focusIndex = index;
      frame.focusKey = itemKey(items[index]);
      if (menu && menu.grid && menu.gridCols > 0) {
        frame.focusRow = Math.floor(index / menu.gridCols);
        frame.focusCol = index % menu.gridCols;
      } else {
        frame.focusRow = index;
        frame.focusCol = 0;
      }
    }

    // Access-time settle: while the top frame is a declarative frame whose
    // resolution is the unresolvable marker, pop per its policy — the default
    // `pop` restores the opener's focus key under the key rule, `root` exits
    // the whole navigation stack back to the root frame (the suggestions
    // status split) — cascading until a frame resolves. An unresolvable root
    // at depth 1 degrades in place (no parent to return to). Bounded by stack
    // depth; no timer, animation, or deferred check.
    function settleTop() {
      if (settling) {
        return;
      }
      settling = true;
      try {
        while (stack.length > 0) {
          var frame = stack[stack.length - 1];
          if (!isDeclarative(frame)) {
            return;
          }
          var menu = frameMenu(frame);
          if (!isMarker(menu)) {
            projectFocus(frame, menu);
            return;
          }
          if (stack.length === 1) {
            return; // degraded root: no parent to return to
          }
          if (frame.unresolvableAction === "root") {
            stack.splice(1);
            projectFocus(stack[0], frameMenu(stack[0]));
            emit("focus", {
              row: stack[0].focusRow,
              col: stack[0].focusCol,
              item: itemAt(stack[0], stack[0].focusRow, stack[0].focusCol),
              itemKey: stack[0].focusKey,
            });
            return;
          }
          stack.pop();
          var parent = stack[stack.length - 1];
          if (parent && isDeclarative(parent)) {
            if (frame.openerKey !== undefined && frame.openerKey !== null) {
              parent.focusKey = frame.openerKey;
            }
            projectFocus(parent, frameMenu(parent));
          }
        }
      } finally {
        settling = false;
      }
    }

    function settleGuard() {
      if (settling) {
        return;
      }
      settleTop();
    }

    function declarativeFrame(descriptor, pushOptions) {
      var frame = {
        descriptor: descriptor,
        focusKey: null,
        // Router-private nearest-rule memory (see projectFocus). NOT part of
        // the observable frame contract and never a retained menu copy.
        _focusIndex: 0,
        focusRow: 0,
        focusCol: 0,
        openerKey: pushOptions && pushOptions.openerKey !== undefined
          ? pushOptions.openerKey
          : null,
        unresolvableAction: (pushOptions && pushOptions.unresolvableAction) || "pop",
      };
      return frame;
    }

    function settleAndFocus() {
      // settleTop projects the new top frame's focus (first item from the
      // push-time resolve; null on an empty menu) or settles a cascade; one
      // focus event follows for the resulting top.
      settleTop();
      var top = current();
      if (top) {
        notifyFocus(top);
      }
    }

    // --- Legacy-shape internals (byte-for-byte preserved behavior) ----------

    function current() {
      return stack.length > 0 ? stack[stack.length - 1] : null;
    }

    function itemAt(frame, row, col) {
      if (!frame) {
        return null;
      }
      var menu = frameMenu(frame);
      if (isMarker(menu)) {
        // Only the degraded root presents a row for a marker resolution; any
        // other marker frame is settled away by `settleTop` before reads.
        return isDegradedRoot(frame) ? degradedMenu().items[0] : null;
      }
      menu = menu || { items: [] };
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
      settleGuard();
      var frame = current();
      if (!frame) {
        return false;
      }
      var menu = frameMenu(frame);
      if (isMarker(menu) || !menu) {
        return false;
      }
      if (menu.grid && menu.gridCols > 0) {
        for (var index = 0; index < menu.items.length; index += 1) {
          var candidate = menu.items[index];
          if (candidate && itemKey(candidate) === key) {
            frame.focusRow = Math.floor(index / menu.gridCols);
            frame.focusCol = index % menu.gridCols;
            if (isDeclarative(frame)) {
              frame.focusKey = key;
              frame._focusIndex = index;
            }
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
          if (isDeclarative(frame)) {
            frame.focusKey = key;
            frame._focusIndex = listIndex;
          }
          notifyFocus(frame);
          return true;
        }
      }
      return false;
    }

    // Move focus within the current menu geometry.
    function move(direction) {
      settleGuard();
      var frame = current();
      if (!frame) {
        return false;
      }
      var menu = frameMenu(frame);
      if (isMarker(menu)) {
        // A settled stack never leaves a marker on top except the degraded
        // root, whose single row makes every press a no-op.
        return false;
      }
      menu = menu || { items: [] };
      if (menu.grid && menu.gridCols > 0) {
        var cols = menu.gridCols;
        var rows = Math.max(1, Math.ceil(menu.items.length / cols));
        // H3 (task 2.7): the combat root is a single-row tab bar
        // (`gridCols == items.length` → `rows == 1`), so vertical presses are
        // no-ops; symmetrically, a single-column grid (`cols == 1`) makes
        // horizontal presses no-ops.
        if ((direction === ARROW_UP || direction === ARROW_DOWN) && rows === 1) {
          return false;
        }
        if ((direction === ARROW_LEFT || direction === ARROW_RIGHT) && cols === 1) {
          return false;
        }
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
        if (isDeclarative(frame)) {
          frame.focusKey = itemKey(candidate);
          frame._focusIndex = row * cols + col;
        }
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
      if (isDeclarative(frame)) {
        frame.focusKey = itemKey(items[index]);
        frame._focusIndex = index;
      }
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
      settleGuard();
      var frame = current();
      if (!frame) {
        return false;
      }
      var item = itemAt(frame, frame.focusRow, frame.focusCol);
      if (!item) {
        return false;
      }
      // Activation makes its row the frame's focus key BEFORE dispatching, so
      // the outcome commit (which may re-resolve the frame) restores focus
      // deterministically even when the dispatch itself changes the menu.
      if (isDeclarative(frame)) {
        frame.focusKey = itemKey(item);
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
      settleGuard();
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
      if (parent) {
        projectFocus(parent, frameMenu(parent));
      }
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
      // Held or repeated Space is suppressed too: with AREA candidate grids
      // now rendered, a held Space must not repeatedly toggle candidates.
      if (key === SPACE && repeat) {
        emit("repeat-suppressed", { key: SPACE });
        return true;
      }
      if (key === SPACE) {
        settleGuard();
        var frame = current();
        emit("space", { item: itemAt(frame, frame ? frame.focusRow : 0, frame ? frame.focusCol : 0) });
        return true;
      }
      if (key === SLASH) {
        emit("toggle-drawer", {});
        return true;
      }
      if (key === ARROW_UP || key === ARROW_DOWN || key === ARROW_LEFT || key === ARROW_RIGHT) {
        return move(key);
      }
      return false;
    }

    return {
      // Menu lifecycle (transitional legacy frames).
      pushMenu: function (menu) {
        assertFrameShape({ frame: { menu: menu } });
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
        assertFrameShape({ frame: { menu: menu } });
        if (stack.length === 0) {
          return this.pushMenu(menu);
        }
        // Transitional cross-family re-home: the top frame becomes a legacy
        // copy frame outright. Replacing only `.menu` on a declarative frame
        // would leave the descriptor authoritative (its reads resolve, never
        // read `.menu`), so the frame's shape flips here — the follow-up
        // change deletes this whole path with the legacy shape.
        stack[stack.length - 1] = { menu: menu, focusRow: 0, focusCol: 0 };
        repeatGuard = null;
        notifyFocus(current());
        return stack.length;
      },
      // Declarative lifecycle (the cutover path): the frame stores ONLY its
      // descriptor — never a resolved menu — and focuses its first item from
      // the resolve taken at push time.
      pushFrame: function (descriptor, pushOptions) {
        assertFrameShape({ frame: { descriptor: descriptor } });
        var frame = declarativeFrame(descriptor, pushOptions);
        stack.push(frame);
        repeatGuard = null;
        settleAndFocus();
        return stack.length;
      },
      // Replace (or create) the current frame with a declarative one — the
      // root re-home primitive.
      replaceFrame: function (descriptor, pushOptions) {
        assertFrameShape({ frame: { descriptor: descriptor } });
        if (stack.length === 0) {
          return this.pushFrame(descriptor, pushOptions);
        }
        var frame = declarativeFrame(descriptor, pushOptions);
        stack[stack.length - 1] = frame;
        repeatGuard = null;
        settleAndFocus();
        return stack.length;
      },
      // Replace the whole stack with one declarative frame (teardown).
      resetFrame: function (descriptor, pushOptions) {
        assertFrameShape({ frame: { descriptor: descriptor } });
        settling = true;
        var frame;
        try {
          frame = declarativeFrame(descriptor, pushOptions);
          stack = [frame];
        } finally {
          settling = false;
        }
        repeatGuard = null;
        settleTop();
        notifyFocus(frame);
        return stack.length;
      },
      popMenu: function () {
        settleGuard();
        if (stack.length <= 1) {
          return false;
        }
        stack.pop();
        var parent = current();
        if (parent) {
          projectFocus(parent, frameMenu(parent));
        }
        notifyFocus(current());
        return true;
      },
      reset: function (menu) {
        if (menu) {
          assertFrameShape({ frame: { menu: menu } });
          stack = [{ menu: menu, focusRow: 0, focusCol: 0 }];
        } else {
          stack = [];
        }
        repeatGuard = null;
        if (stack.length > 0) {
          notifyFocus(current());
        }
        return stack.length;
      },
      depth: function () {
        settleGuard();
        return stack.length;
      },
      currentItem: function () {
        settleGuard();
        var frame = current();
        return frame ? itemAt(frame, frame.focusRow, frame.focusCol) : null;
      },
      // The current frame's menu (read-only); null when no frame is mounted.
      // An unresolvable root frame presents the degraded single-row menu.
      currentMenu: function () {
        settleGuard();
        var frame = current();
        if (!frame) {
          return null;
        }
        var menu = frameMenu(frame);
        if (isMarker(menu)) {
          return isDegradedRoot(frame) ? degradedMenu() : null;
        }
        return menu;
      },
      // The current frame's descriptor (declarative frames only; null for a
      // transitional legacy frame) — the single source for opener-context
      // reads such as the scripted-keywords identity.
      currentDescriptor: function () {
        var frame = current();
        return frame && isDeclarative(frame) ? frame.descriptor : null;
      },
      // Read-only breadcrumb source (H3 webclient-hud-03-action-dock): each
      // stacked frame's menu title in read order, so the dock's crumb and
      // tab bar derive from the router's frame stack, never a second
      // navigation state. Declarative frames read their title from the
      // resolve taken at this access.
      trail: function () {
        settleGuard();
        return stack.map(function (frame) {
          var menu = isDegradedRoot(frame) ? degradedMenu() : frameMenu(frame);
          return menu && menu.title ? menu.title : "";
        });
      },
      // The root frame's menu (read-only): the tab bar renders the root
      // frame's items while the pane follows the current frame (H3 task 3.2).
      // Null when the root is degraded — the tab bar must never render the
      // synthetic marker-reason row as a tab; the pane host presents
      // `degradedRoot()` for that state.
      rootMenu: function () {
        settleGuard();
        if (stack.length === 0) {
          return null;
        }
        var frame = stack[0];
        var menu = frameMenu(frame);
        if (isMarker(menu)) {
          return null;
        }
        return menu;
      },
      // The degraded-root presentation contract (the store's
      // `view.degradedRoot`): the single disabled marker-reason row the pane
      // host renders while the root frame is unresolvable, or null.
      degradedRoot: function () {
        settleGuard();
        if (!isDegradedRoot(stack[0])) {
          return null;
        }
        var menu = frameMenu(stack[0]);
        return {
          key: "degraded-root",
          reason: typeof menu.reason === "string" && menu.reason !== "" ? menu.reason : null,
          fallback: DEGRADED_ROOT_FALLBACK,
        };
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
    DEGRADED_ROOT_FALLBACK: DEGRADED_ROOT_FALLBACK,
    menuItem: menuItem,
    createRouter: createRouter,
  };
});
