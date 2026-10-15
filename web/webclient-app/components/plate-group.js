// The figure plates' keyboard group (OpenSpec change
// webclient-combat-figure-plates, design D4): the stage's `plates` anchor is
// one tab stop (`role="group"`, 戰場) holding a roving focus over the plates
// and their condition glyphs.
//
// - Focusing the anchor forwards focus to the last focused plate or glyph
//   still inside it, else the leftmost plate. While focus is inside, the
//   anchor leaves the tab order (`tabindex="-1"`), so Tab and Shift+Tab leave
//   the group naturally; it rejoins when focus leaves.
// - ArrowLeft / ArrowRight move between plates in stage order (left to
//   right by `data-stage-x`, ties in DOM order), Home / End to the first /
//   last plate; ArrowDown moves from a plate to its first glyph and on to the
//   next, ArrowUp back to the previous glyph and then to the plate.
// - Escape returns focus to the escape target (`#action-dock`). An open
//   condition tooltip consumes the first Escape below this listener
//   (ConditionChips), so only a press with no tooltip open reaches it.
// - Every key the group handles is consumed (default prevented, propagation
//   stopped), so the document-level router in bridge.js never sees it.
//   Digits and every other key keep their global meaning.
//
// Pure DOM: no Vue import. `bindPlateGroup` returns its unbind function.

const PLATE = '[data-testid="figure-plate"]';
const GLYPH = ".figure-plate__glyphs button";

function usable(el) {
  return !!el && el.isConnected && !el.inert && !el.closest("[inert]");
}

// The plates in stage order: left to right by their slot centre, ties (and
// plates without a stage x) in DOM order.
export function platesInStageOrder(root) {
  return [...root.querySelectorAll(PLATE)]
    .filter(usable)
    .map((plate, index) => ({ plate, index, x: Number.parseFloat(plate.getAttribute("data-stage-x")) }))
    .sort((a, b) => {
      const ax = Number.isFinite(a.x) ? a.x : Number.POSITIVE_INFINITY;
      const bx = Number.isFinite(b.x) ? b.x : Number.POSITIVE_INFINITY;
      return ax === bx ? a.index - b.index : ax - bx;
    })
    .map((entry) => entry.plate);
}

function glyphsOf(plate) {
  return [...plate.querySelectorAll(GLYPH)].filter(usable);
}

function consume(event) {
  event.preventDefault();
  event.stopPropagation();
}

// `onInside(inside)` reports whether focus is inside the group, so the owner
// can take the anchor out of the tab order while it is (HudFrame binds the
// anchor's `tabindex` to it). Without one, the anchor's attribute is set here.
export function bindPlateGroup(
  root,
  {
    escapeTarget = () => document.getElementById("action-dock"),
    onInside = (inside) => {
      if (root.hasAttribute("tabindex")) root.setAttribute("tabindex", inside ? "-1" : "0");
    },
  } = {},
) {
  let remembered = null;
  // The identity of the plate holding (or last holding) focus: a plate
  // re-keyed on a roster change is found again by it.
  let rememberedIdentity = null;
  let inside = false;

  function setInside(value) {
    if (inside === value) return;
    inside = value;
    onInside(value);
  }

  function plateByIdentity(identity) {
    if (identity === null) return null;
    return platesInStageOrder(root).find((plate) => plate.getAttribute("data-identity") === identity) ?? null;
  }

  function enterFrom() {
    if (remembered && root.contains(remembered) && usable(remembered)) return remembered;
    return plateByIdentity(rememberedIdentity) ?? platesInStageOrder(root)[0] ?? null;
  }

  // Focus left the group without the user moving it: its element was removed
  // (a leaving or re-keyed plate, a glyph whose condition went away) or went
  // inert (a held round, the end of combat). It lands on the same figure's
  // plate if one still stands, else the leftmost plate, else the dock.
  function lost() {
    const active = document.activeElement;
    if (!active || active === document.body) return true;
    return root.contains(active) && !usable(active);
  }
  function rescue() {
    const target = usable(root) ? plateByIdentity(rememberedIdentity) ?? platesInStageOrder(root)[0] ?? null : null;
    if (target) {
      target.focus();
      return;
    }
    setInside(false);
    const fallback = escapeTarget();
    if (fallback) fallback.focus();
  }
  const observer =
    typeof MutationObserver === "function"
      ? new MutationObserver(() => {
          if (inside && lost()) rescue();
        })
      : null;
  observer?.observe(root, { childList: true, subtree: true, attributes: true, attributeFilter: ["inert"] });

  function onFocusIn(event) {
    if (event.target === root) {
      const target = enterFrom();
      if (target) {
        target.focus();
      }
      return;
    }
    setInside(true);
    // Only a plate or a glyph is remembered as the group's re-entry point.
    if (!event.target.matches?.(`${PLATE}, ${GLYPH}`)) return;
    remembered = event.target;
    rememberedIdentity = event.target.closest(PLATE)?.getAttribute("data-identity") ?? null;
  }

  function onFocusOut(event) {
    const next = event.relatedTarget;
    if (next && root.contains(next)) return;
    if (next) {
      setInside(false);
      return;
    }
    // No next element: the user clicked empty space, or the focused element
    // went away. Decide once the DOM has settled.
    const from = event.target;
    queueMicrotask(() => {
      if (!usable(from) && lost()) rescue();
      else if (!root.contains(document.activeElement)) setInside(false);
    });
  }

  function onKeydown(event) {
    if (event.ctrlKey || event.metaKey || event.altKey) return;
    const active = event.target;
    if (!(active instanceof Element) || !root.contains(active)) return;
    const plate = active.closest(PLATE);
    const onGlyph = !!plate && active !== plate && !!active.closest(".figure-plate__glyphs");
    const plates = platesInStageOrder(root);
    const at = plate ? plates.indexOf(plate) : -1;
    const focus = (el) => {
      if (el) el.focus();
    };
    switch (event.key) {
      case "ArrowLeft":
      case "ArrowRight": {
        consume(event);
        if (!plates.length) return;
        const step = event.key === "ArrowRight" ? 1 : -1;
        const index = at < 0 ? 0 : Math.min(plates.length - 1, Math.max(0, at + step));
        focus(plates[index]);
        return;
      }
      case "Home":
      case "End":
        consume(event);
        focus(event.key === "Home" ? plates[0] : plates[plates.length - 1]);
        return;
      case "ArrowDown":
      case "ArrowUp": {
        consume(event);
        if (!plate) return;
        const glyphs = glyphsOf(plate);
        const index = onGlyph ? glyphs.indexOf(active.closest("button")) : -1;
        if (event.key === "ArrowDown") {
          focus(glyphs[Math.min(glyphs.length - 1, index + 1)]);
        } else if (onGlyph) {
          focus(index > 0 ? glyphs[index - 1] : plate);
        }
        return;
      }
      case "Escape": {
        const target = escapeTarget();
        if (!target) return;
        consume(event);
        remembered = active;
        target.focus();
        return;
      }
      case "Enter":
      case " ":
        // A plate is no control: its Enter and Space never reach the dock.
        // A glyph keeps its native activation, but the key stops here.
        if (active === plate) consume(event);
        else if (onGlyph) event.stopPropagation();
        return;
      default:
    }
  }

  root.addEventListener("focusin", onFocusIn);
  root.addEventListener("focusout", onFocusOut);
  root.addEventListener("keydown", onKeydown);
  return function unbind() {
    observer?.disconnect();
    root.removeEventListener("focusin", onFocusIn);
    root.removeEventListener("focusout", onFocusOut);
    root.removeEventListener("keydown", onKeydown);
  };
}
