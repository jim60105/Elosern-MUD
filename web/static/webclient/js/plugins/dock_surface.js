/*
 * Elosern shared dock surface renderer and delegated pointer bridge.
 *
 * Every action-dock surface (exploration, services, creation, character,
 * combat) renders its rows through `DockSurface.renderRows`, so the row
 * markup, the focused marker, the disabled marker with its （無法使用）
 * suffix, the accessible disabled association, and the row identity
 * attribute are defined in exactly one place. Rows form one composite
 * widget: the row container carries `role="listbox"`, is the surface's
 * single tab stop, and names the focused row through
 * `aria-activedescendant`; rows carry `role="option"`, `tabindex="-1"` (so
 * no row is individually reachable by sequential keyboard navigation), and
 * `aria-selected`.
 *
 * `installPointerBridge` registers exactly one delegated `click` listener
 * and one delegated `mousedown` listener on the stable `#action-dock`
 * element, installed once at shell init. A click resolves the row through
 * `closest("[data-item-key]")`, is admitted only when it is a primary
 * single activation (`event.detail === 1`) whose resolved row is still
 * connected to the document, and then walks the identical path as Enter:
 * `focusItemByKey(key)` followed by a pointer-sourced `confirm`. The
 * `isConnected` check stops a second rapid activation on a navigation row
 * -- which pushes a frame instead of submitting and is therefore not
 * covered by the in-flight mutation lock -- from double-pushing after the
 * first activation's re-render detached the old rows. The bridge performs
 * no submission itself and knows nothing about any specific dock.
 */
(function () {
  "use strict";

  var DISABLED_SUFFIX = "（無法使用）";

  function makeElement(tag, className) {
    var element = document.createElement(tag);
    if (className) {
      element.className = className;
    }
    return element;
  }

  function setText(element, text) {
    while (element.firstChild) {
      element.removeChild(element.firstChild);
    }
    element.appendChild(document.createTextNode(text == null ? "" : String(text)));
  }

  function getKeyboard() {
    return (
      window.Elosern &&
      window.Elosern.keyboard
    ) || null;
  }

  // Render `items` as rows inside `container`. The container becomes the
  // listbox composite widget; `idPrefix` produces stable row ids
  // `<idPrefix>-<index>` that `aria-activedescendant` references.
  // `options.nonSubmitting` renders display-only rows (e.g. the character
  // panel): focusable, without the disabled marker, and carrying no action.
  // When the menu carries grid geometry (`grid` + `gridCols`), the container
  // becomes a CSS grid whose column count matches the menu, so router
  // geometry and the visible cells agree; `gridCols` must equal the CSS
  // `repeat()` count.
  function renderRows(container, items, options) {
    options = options || {};
    var focusKey = options.focusKey == null ? null : options.focusKey;
    var idPrefix = options.idPrefix || "row";
    var nonSubmitting = !!options.nonSubmitting;
    var menu = options.menu || null;
    while (container.firstChild) {
      container.removeChild(container.firstChild);
    }
    container.setAttribute("role", "listbox");
    container.setAttribute("tabindex", "0");
    if (menu && menu.grid && menu.gridCols > 0) {
      if (container.style) {
        container.style.display = "grid";
        container.style.gridTemplateColumns = "repeat(" + menu.gridCols + ", 1fr)";
      }
      container.classList.add("dock-grid");
    } else {
      if (container.style) {
        container.style.display = "";
        container.style.gridTemplateColumns = "";
      }
      container.classList.remove("dock-grid");
    }

    var focusedId = null;
    var rows = [];
    for (var i = 0; i < items.length; i += 1) {
      var item = items[i];
      var key = item && item.key !== undefined ? item.key : item && item.label;
      var row = makeElement("button", "dock-row");
      row.type = "button";
      row.setAttribute("data-item-key", key);
      row.id = idPrefix + "-" + i;
      row.setAttribute("role", "option");
      row.setAttribute("tabindex", "-1");
      row.setAttribute("aria-selected", "false");
      if (nonSubmitting) {
        setText(row, item.label);
      } else {
        var disabled = !item.enabled;
        if (disabled) {
          row.classList.add("disabled");
          row.setAttribute("aria-disabled", "true");
          setText(row, item.label + DISABLED_SUFFIX);
          // The disabled reason stays programmatically associated with the
          // cell at every navigation depth (a visible detail pane mirrors it
          // where one exists; the element itself is visually hidden so the
          // association holds even at the exploration root, which draws no
          // detail pane).
          var reason =
            (item.disabledReason && item.disabledReason.message) ||
            item.description;
          if (reason) {
            var desc = makeElement("span", "dock-row-reason");
            desc.id = idPrefix + "-desc-" + i;
            desc.classList.add("visually-hidden");
            setText(desc, reason);
            row.appendChild(desc);
            row.setAttribute("aria-describedby", desc.id);
          }
        } else {
          // AREA candidate rows carry a live selection marker (the combat
          // dock refreshes the frame after a client-local toggle).
          if (item.selected) {
            row.classList.add("selected");
            setText(row, "✓ " + item.label);
          } else {
            setText(row, item.label);
          }
        }
      }
      if (key === focusKey) {
        row.classList.add("focused");
        row.setAttribute("aria-selected", "true");
        focusedId = row.id;
      }
      container.appendChild(row);
      rows.push(row);
    }
    if (focusedId !== null) {
      container.setAttribute("aria-activedescendant", focusedId);
    } else if (rows.length > 0) {
      // A router frame always has a focused item, but a fallback keeps the
      // composite widget well-formed for display-only surfaces.
      rows[0].classList.add("focused");
      rows[0].setAttribute("aria-selected", "true");
      container.setAttribute("aria-activedescendant", rows[0].id);
    } else {
      container.removeAttribute("aria-activedescendant");
    }
  }

  // Render the dock's shortcut guidance line (mockup chrome): a per-surface
  // prefix plus the shared shortcut legend. Docks that own the action-dock
  // DOM rebuild it, so each dock renders its own guidance through this helper
  // (the foundation paragraph survives only until the first dock mounts).
  function renderGuidance(root, prefix) {
    var existing = document.getElementById("action-dock-guidance");
    if (existing && existing.parentNode) {
      existing.parentNode.removeChild(existing);
    }
    var guidance = makeElement("p", "action-guidance");
    guidance.id = "action-dock-guidance";
    var note = makeElement("span", "action-guidance-note");
    note.id = "action-dock-description";
    setText(note, (prefix ? prefix + "　" : "") + "方向鍵選擇・Enter 確認・Esc 返回・/ 開啟指令");
    guidance.appendChild(note);
    root.insertBefore(guidance, root.firstChild);
    return guidance;
  }

  // The single delegated pointer bridge on #action-dock.
  function installPointerBridge() {
    var dock = document.getElementById("action-dock");
    if (!dock) {
      return;
    }
    dock.addEventListener("mousedown", function (event) {
      var row = event.target && event.target.closest
        ? event.target.closest("[data-item-key]")
        : null;
      if (!row || !row.isConnected) {
        return;
      }
      // Keep DOM focus on the composite widget so the visible focus ring
      // stays where the router says it is. `preventScroll` stops the browser
      // from scrolling the (possibly clipped) listbox into view between
      // mousedown and mouseup -- that scroll would move the row under the
      // cursor and the resulting click would resolve to the container.
      event.preventDefault();
      var container = row.parentNode;
      if (container && typeof container.focus === "function") {
        container.focus({ preventScroll: true });
      }
    });

    dock.addEventListener("click", function (event) {
      // A keyboard-synthesized click on a focused control fires with
      // detail === 0; the repeat events of a multi-click have detail > 1.
      if (event.detail !== 1) {
        return;
      }
      var row = event.target && event.target.closest
        ? event.target.closest("[data-item-key]")
        : null;
      // The stale-row guard: a dock that re-rendered in response to the
      // first activation detached its old rows, so a second activation
      // whose row is no longer connected is rejected regardless of timing.
      if (!row || !row.isConnected) {
        return;
      }
      var key = row.getAttribute("data-item-key");
      var keyboard = getKeyboard();
      if (!keyboard) {
        return;
      }
      keyboard.focusItemByKey(key);
      keyboard.confirm({ source: "pointer" });
    });
  }

  window.Elosern = window.Elosern || {};
  window.Elosern.DockSurface = {
    renderRows: renderRows,
    renderGuidance: renderGuidance,
    installPointerBridge: installPointerBridge,
    DISABLED_SUFFIX: DISABLED_SUFFIX,
  };
})();
