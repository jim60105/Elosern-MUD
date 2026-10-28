// The keyboard contract (frontend design §6) as one pure resolver. The page
// passes the event and a small context; the resolver returns the action or
// null. Single-key shortcuts never act in a text input, select or the
// qualified-object selector, during IME composition, or with a modifier.
// Inside a text field the field's own undo, delete and copy apply.

const NON_TEXT_INPUTS = new Set(["checkbox", "radio", "button", "submit", "reset", "range", "color", "file", "image"]);

export function isTextTarget(element) {
  if (!element || typeof element.closest !== "function") return false;
  if (element.closest("[data-object-selector]")) return true;
  const tag = String(element.tagName ?? "").toLowerCase();
  if (tag === "textarea" || tag === "select") return true;
  if (tag === "input") return !NON_TEXT_INPUTS.has(String(element.type ?? "text").toLowerCase());
  return Boolean(element.isContentEditable);
}

export function isMacPlatform(nav = globalThis.navigator) {
  const platform = nav?.userAgentData?.platform ?? nav?.platform ?? "";
  return /mac|iphone|ipad/i.test(platform);
}

// The primary command modifier: ⌘ on macOS, Ctrl elsewhere.
export function primaryModifier(event, mac) {
  return mac ? event.metaKey && !event.ctrlKey : event.ctrlKey && !event.metaKey;
}

export function shortcutLabel(mac) {
  return mac ? "⌘" : "Ctrl+";
}

const NUDGES = { ArrowUp: [0, -1], ArrowDown: [0, 1], ArrowLeft: [-1, 0], ArrowRight: [1, 0] };

function composing(event) {
  return Boolean(event.isComposing) || event.keyCode === 229;
}

// ctx: { mac, text, drawerOpen, toolActive, refusalShown, hasSelection,
//        nudgeScope, canReturn, domains: {key: domain}, tools: {key: tool} }
export function resolveKey(event, ctx = {}) {
  if (composing(event)) return null;
  const mac = Boolean(ctx.mac);
  const primary = primaryModifier(event, mac);
  // Autofill and some synthetic events carry no key.
  const key = String(event.key ?? "");
  if (key === "F6" && !event.ctrlKey && !event.metaKey && !event.altKey) {
    return ctx.drawerOpen ? { type: "trap" } : { type: "region", step: event.shiftKey ? -1 : 1 };
  }
  if (key === "Escape") {
    if (ctx.drawerOpen) return { type: "escape", target: "drawer" };
    if (ctx.text) return null;
    if (ctx.toolActive) return { type: "escape", target: "tool" };
    if (ctx.refusalShown) return { type: "escape", target: "refusal" };
    if (ctx.hasSelection) return { type: "escape", target: "selection" };
    return null;
  }
  if (primary && !event.altKey && key.toLowerCase() === "s") return { type: "save" };
  if (primary && !event.altKey && key.toLowerCase() === "k") return { type: "search" };
  if (event.altKey && !event.ctrlKey && !event.metaKey && !event.shiftKey && key === "ArrowLeft") {
    return ctx.canReturn ? { type: "return" } : null;
  }
  if (ctx.text) return null;
  if (primary && !event.altKey && key.toLowerCase() === "z") return { type: event.shiftKey ? "redo" : "undo" };
  if (!mac && primary && !event.altKey && !event.shiftKey && key.toLowerCase() === "y") return { type: "redo" };
  if (event.shiftKey && !event.ctrlKey && !event.metaKey && !event.altKey && NUDGES[key]) {
    return ctx.nudgeScope ? { type: "nudge", delta: NUDGES[key] } : null;
  }
  if (event.ctrlKey || event.metaKey || event.altKey) return null;
  if (key === "Delete") return ctx.hasSelection ? { type: "delete" } : null;
  if (key === "/") return { type: "search" };
  if (event.shiftKey) return null;
  if (ctx.domains?.[key]) return { type: "domain", domain: ctx.domains[key] };
  const tool = ctx.tools?.[key.toLowerCase()];
  if (tool) return { type: "tool", tool };
  return null;
}

// The next region index for F6 / Shift+F6 among the available regions.
export function cycleRegion(count, current, step) {
  if (count <= 0) return -1;
  if (current < 0) return step > 0 ? 0 : count - 1;
  return (current + step + count) % count;
}

// The nearest mark in the arrow's direction (scene coordinates, north up).
// Marks well off the direction's axis cost more; null when none lies ahead.
export function nearestInDirection(marks, fromId, key) {
  const from = marks.find((mark) => mark.id === fromId);
  const direction = { ArrowRight: [1, 0], ArrowLeft: [-1, 0], ArrowUp: [0, 1], ArrowDown: [0, -1] }[key];
  if (!from || !direction) return null;
  let best = null;
  for (const mark of marks) {
    if (mark.id === fromId) continue;
    const dx = mark.x - from.x;
    const dy = mark.y - from.y;
    const along = dx * direction[0] + dy * direction[1];
    if (along <= 0) continue;
    const across = Math.abs(dx * direction[1] - dy * direction[0]);
    const cost = along + 2 * across;
    if (!best || cost < best.cost) best = { id: mark.id, cost };
  }
  return best?.id ?? null;
}
