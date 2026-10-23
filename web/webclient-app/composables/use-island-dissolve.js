// The island's scale-change dissolve (animate-minimap-scale-transitions;
// approved minimap auto-scale design §6.5).
//
// When a move (or a replacement payload) changes the island projection's mode
// or level at the effective `full` motion level, the drawing cannot pan: the
// FLIP offset assumes one scale before and after. Instead the previous drawing
// dissolves into the new one. Just before Vue patches the svg, `snapshot`
// copies it as it stands on screen (any pan still in flight frozen in place);
// after the patch, `play` lays the copy over the committed drawing and fades
// it out over the `--motion-base` token. The copy carries the svg's own opaque
// canvas, so the pixels both frames share — the centred current marker, the
// axis cross, the corner brackets — hold perfectly still while only what
// changed dissolves: a true crossfade with no mid-fade dip, no animated
// scale and no tweened node.
//
// The copy is decoration only: its host is `aria-hidden` and `inert`, the copy
// itself is inert, and every identity a test, an assistive technology or a
// stylesheet hook could confuse with the live drawing (`id`, `data-testid`,
// `data-node*`, roles, tab stops, names, titles) is removed or renamed. The
// island's actionable controls (the stub buttons) live outside the svg, so a
// copy never duplicates one. The copy keeps its descendants' class names (its
// painting depends on them), so for one `--motion-base` at `full` a class- or
// text-based query over the whole island can match a node twice: scope such
// queries to `[data-testid="local-map__lattice"]` (the copy carries
// `local-map__leaving` instead). Each copy removes itself when its own fade ends
// (with a token-derived fallback timer), so an interrupted sequence always
// settles on the latest committed projection.

import { readMotionMs } from "../lib/motion_tokens.js";

// Older copies stay on top while they finish, so a quick second scale change
// fades through each frame in order; beyond this many the oldest goes at once.
const MAX_LEAVING = 3;
// Fallback slack past the token duration, for a fade whose `animationend`
// never arrives (a detached host, a backgrounded tab).
const CLEANUP_SLACK_MS = 100;

const IDENTITY_ATTRIBUTES = [
  "data-testid",
  "data-node",
  "data-node-id",
  "data-visibility",
  "role",
  "tabindex",
  "aria-label",
  "aria-labelledby",
  "aria-describedby",
];
const REFERENCE_ATTRIBUTES = ["fill", "stroke", "filter", "clip-path", "mask", "marker-start", "marker-mid", "marker-end"];

let sequence = 0;

// Rename every `id` in the copy (and every `url(#…)`/`href="#…"` pointing at
// one), so the copy's defs stay its own: the old fog and pattern keep painting
// the old frame, and the document never holds a duplicate id.
function renameIds(root) {
  const suffix = `-leaving-${(sequence += 1)}`;
  const renamed = new Map();
  for (const el of root.querySelectorAll("[id]")) {
    const id = el.getAttribute("id");
    renamed.set(id, `${id}${suffix}`);
    el.setAttribute("id", `${id}${suffix}`);
  }
  if (root.hasAttribute("id")) root.removeAttribute("id");
  if (renamed.size === 0) return;
  const rewrite = (value) =>
    value.replace(/url\(\s*(['"]?)#([^'")\s]+)\1\s*\)/g, (match, quote, id) =>
      renamed.has(id) ? `url(${quote}#${renamed.get(id)}${quote})` : match,
    );
  for (const el of [root, ...root.querySelectorAll("*")]) {
    for (const name of REFERENCE_ATTRIBUTES) {
      const value = el.getAttribute(name);
      if (value && value.includes("url(")) el.setAttribute(name, rewrite(value));
    }
    const style = el.getAttribute("style");
    if (style && style.includes("url(")) el.setAttribute("style", rewrite(style));
    for (const name of ["href", "xlink:href"]) {
      const value = el.getAttribute(name);
      if (value && value.startsWith("#") && renamed.has(value.slice(1))) {
        el.setAttribute(name, `#${renamed.get(value.slice(1))}`);
      }
    }
  }
}

// Freeze every element that may be mid-transition (the pan groups, the
// gliding current marker) at the transform and opacity it shows right now.
function freezeInFlight(live, copy) {
  const selector = ".map-lattice__pan, .map-lattice__pan .local-map__marker--current";
  const liveEls = [...live.querySelectorAll(selector)];
  const copyEls = [...copy.querySelectorAll(selector)];
  liveEls.forEach((el, i) => {
    const target = copyEls[i];
    if (!target) return;
    const style = getComputedStyle(el);
    target.style.transition = "none";
    target.style.transform = style.transform && style.transform !== "none" ? style.transform : "none";
    if (style.opacity && style.opacity !== "1") target.style.opacity = style.opacity;
  });
}

export function useIslandDissolve(hostRef) {
  const leaving = new Map(); // copy element -> fallback timer
  let pending = null;

  function remove(copy) {
    const timer = leaving.get(copy);
    if (timer !== undefined) clearTimeout(timer);
    leaving.delete(copy);
    copy.remove();
  }

  // Every previous frame goes now (a reduced/off scale switch, unmount, a
  // level change away from `full`).
  function clear() {
    pending = null;
    for (const copy of [...leaving.keys()]) remove(copy);
  }

  // Before the patch: copy the drawing as it stands. Returns false when the
  // dissolve cannot play (no svg, or the token resolves to no time at all).
  function snapshot(svg) {
    pending = null;
    const duration = readMotionMs("--motion-base");
    if (!svg || !(duration > 0)) return false;
    const copy = svg.cloneNode(true);
    freezeInFlight(svg, copy);
    renameIds(copy);
    for (const el of [copy, ...copy.querySelectorAll("*")]) {
      for (const name of IDENTITY_ATTRIBUTES) el.removeAttribute(name);
    }
    for (const el of copy.querySelectorAll("title, desc")) el.remove();
    copy.setAttribute("aria-hidden", "true");
    copy.setAttribute("focusable", "false");
    copy.setAttribute("inert", "");
    copy.setAttribute("data-testid", "local-map__leaving");
    copy.classList.add("local-map__lattice--leaving");
    // One duration for the CSS fade and the fallback timer.
    copy.style.animationDuration = `${duration}ms`;
    pending = { copy, duration };
    return true;
  }

  // After the patch: lay the copy over the committed drawing and fade it.
  function play() {
    const host = hostRef.value;
    const next = pending;
    pending = null;
    if (!next || !host) return;
    const { copy, duration } = next;
    // Older copies keep fading above the newer one.
    host.prepend(copy);
    while (host.children.length > MAX_LEAVING) {
      const oldest = host.lastElementChild;
      if (leaving.has(oldest)) remove(oldest);
      else oldest.remove();
    }
    copy.addEventListener("animationend", (event) => {
      if (event.target === copy) remove(copy);
    });
    leaving.set(
      copy,
      setTimeout(() => remove(copy), duration + CLEANUP_SLACK_MS),
    );
  }

  return { snapshot, play, clear, leavingCount: () => leaving.size };
}
