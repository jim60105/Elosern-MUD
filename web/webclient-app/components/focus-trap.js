// Shared focus-trap utility (H4, webclient-hud-04-reference-drawers, design
// D5): a general focusable-query trap with a documented selector list. The
// `FullLogOverlay`'s hard-coded two-element cycle and the drawer's
// arbitrary control set (tabs, search fields, quantity steppers, action
// buttons) all consume this one contract: on open, focus moves into the
// surface; Tab cycles forward and backward within it (hidden and disabled
// nodes are ignored); and on close, focus is restored to the opener. The
// surface owns its own Escape handling; this module owns the focus routing.
// Motion stays token-gated by the surface's CSS; this module is pure DOM
// logic with no style dependencies.

// The documented focusable-selector list: native interactive elements that
// keyboard users can reach by sequential navigation. Hidden nodes are
// excluded by a visibility/bounding-rect check so a `display:none` branch
// leaves the accessibility tree and the tab order.
export const FOCUSABLE_SELECTOR = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  '[contenteditable="true"]',
  "[tabindex]:not([tabindex='-1'])",
].join(", ");

// Query the focusable elements inside `containerEl`, excluding hidden nodes.
// Disabled nodes are excluded by the selector (`:not([disabled])`); hidden
// nodes are excluded by a computed-style check (`display:none` /
// `visibility:hidden`), so a `display:none` branch leaves the accessibility
// tree and the tab order. The check reads computed styles, which jsdom
// reflects for inline `style` overrides, so the unit gate stays deterministic.
export function focusableElements(containerEl) {
  if (!containerEl || typeof containerEl.querySelectorAll !== "function") {
    return [];
  }
  const nodes = Array.from(containerEl.querySelectorAll(FOCUSABLE_SELECTOR));
  return nodes.filter((el) => {
    if (el.hasAttribute && el.hasAttribute("disabled")) {
      return false;
    }
    if (typeof getComputedStyle === "function") {
      const style = getComputedStyle(el);
      if (style.display === "none" || style.visibility === "hidden") {
        return false;
      }
    }
    return true;
  });
}

// Create a focus trap for `containerEl`.
//
// Options:
// - `initialFocusEl`: the element to focus when the surface opens (defaults
//   to the first focusable element).
// - `openerEl`: the control that opened the surface; `restore()` returns
//   focus to it.
//
// The returned handle:
// - `enter()`: move focus into the surface (the initial-focus target).
// - `onKeydown(event)`: forward/backward Tab cycling within the surface.
// - `restore()`: restore focus to the opener (falling back to the surface's
//   first focusable element when the opener node was re-rendered or
//   detached by a router frame replacement — focus never lands on <body>).
export function createFocusTrap(containerEl, options = {}) {
  const { initialFocusEl = null, openerEl = null } = options;
  let opener = openerEl;

  function enter() {
    if (initialFocusEl && typeof initialFocusEl.focus === "function") {
      initialFocusEl.focus();
      return;
    }
    const focusables = focusableElements(containerEl);
    if (focusables.length > 0) {
      focusables[0].focus();
    }
  }

  function onKeydown(event) {
    if (event.key !== "Tab") {
      return;
    }
    const focusables = focusableElements(containerEl);
    event.preventDefault();
    if (focusables.length === 0) {
      return;
    }
    if (focusables.length === 1) {
      focusables[0].focus();
      return;
    }
    const activeIndex = focusables.indexOf(document.activeElement);
    const next = event.shiftKey
      ? focusables[(activeIndex - 1 + focusables.length) % focusables.length]
      : focusables[(activeIndex + 1) % focusables.length];
    next.focus();
  }

  function restore() {
    if (opener && opener instanceof HTMLElement && document.contains(opener)) {
      opener.focus();
      return;
    }
    // The opener node may have been re-rendered or detached (a hosted service
    // frame replacement re-renders the dock rows); re-resolve by the opener's
    // stable identity, else fall back to the surface's first focusable element.
    if (opener && opener.dataset && opener.dataset.itemKey) {
      const reresolved = document.querySelector(
        `[data-item-key="${opener.dataset.itemKey}"]`,
      );
      if (reresolved) {
        reresolved.focus();
        return;
      }
    }
    const focusables = focusableElements(containerEl);
    if (focusables.length > 0) {
      focusables[0].focus();
    }
  }

  return { enter, onKeydown, restore };
}
