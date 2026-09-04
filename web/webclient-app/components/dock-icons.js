// Dock glyph table (H3 webclient-hud-03-action-dock, task 4.2): the fixed
// glyph map keyed by stable server keys — the exploration/combat root item
// keys, the look-entity `kind`, the canonical direction words, and the
// participant `team`. Unmapped keys render no icon (the tab bar's label
// carries the text). Every glyph is `aria-hidden` beside the real text
// label.
export const GLYPHS = {
  // Exploration root item keys (the G2 stable keys). The `d` values for
  // move/look/interact/suggestions are copied verbatim from
  // `docs/design/elosern-redesign/index.html` (the binding visual reference);
  // `look` folds the reference's eye outline plus pupil circle into one
  // multi-subpath string (the pupil as two arc subpaths).
  move: "M12 5v14M12 5 7 10M12 5l5 5",
  look: "M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z M9 12a3 3 0 1 0 6 0a3 3 0 1 0 -6 0",
  interact: "M4 5h16v11H8l-4 4V5Z",
  character: "M12 2a5 5 0 1 1 0 10 5 5 0 0 1 0-10zm-7 22v-1c0-3.9 3.1-7 7-7s7 3.1 7 7v1h-14z",
  quests: "M6 3h12v2h2v5h-2v9a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2V5H5V3h1z",
  // The reference's 背包 · 裝備 drawer-head backpack outline
  // (docs/design/elosern-redesign/index.html:958), the identical string the
  // combat `items` tab carries — one backpack glyph for 背包 semantics
  // across the dock tab and the drawer head (align-drawer-chrome-symbols).
  inventory: "M4 8h16v11H4zM8 8V6a4 4 0 0 1 8 0v2",
  // The reference's 同伴 · 隊伍 drawer head icon (index.html:1040).
  party: "M2 20c0-4 3.5-6 7-6M14 20c0-3 2-5 5-5 M9 4.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7z M16 6a3 3 0 1 0 0 6 3 3 0 0 0 0-6z",
  wait: "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm1 4v7l5 3-1.5 2.4L11 14V7h2z",
  suggestions: "M12 3l1.9 5.6L19.5 10l-5.6 1.9L12 17l-1.9-5.1L4.5 10l5.6-1.4L12 3Z",
  // The reference's own get-icon (the command line's 拿 chip,
  // docs/design/elosern-redesign/index.html:870).
  get: "M6 11V7a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v4M4 11h16v9H4z",
  // Combat root item keys (same reference source, combat-root section).
  attack: "M5 19 19 5M5 19h4M5 19v-4",
  skills: "M12 3l1.9 5.6L19.5 10l-5.6 1.9L12 17l-1.9-5.1L4.5 10l5.6-1.4L12 3Z",
  items: "M4 8h16v11H4zM8 8V6a4 4 0 0 1 8 0v2",
  defend: "M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6l-8-3Z",
  flee: "M13 5l7 7-7 7M4 12h16",
  forfeit: "M6 2h12l-5 8v6M9 2l1 7",
  // Look-entity kinds (the look panel's entity.kind values).
  npc: "M12 2a5 5 0 1 1 0 10 5 5 0 0 1 0-10zm-7 22v-1c0-3.9 3.1-7 7-7s7 3.1 7 7v1H5z",
  monster: "M12 2l4 4 4-1 1 4 4 4-4 3 1 4-4 1-3 4-3-4-4-1 1-4-4-3-4-4 1-4 4-1 3-4 3 4z",
  object: "M12 2l10 6v8l-10 6-10-6V8l10-6z",
  // Canonical direction words (H3 design D9: the exit outlet reads these
  // directly; the renderer never re-parses the label).
  north: "M12 2l5 8H7l5-8z",
  south: "M12 22l-5-8h10l-5 8z",
  east: "M2 12l8-5v10l-8-5z",
  west: "M22 12l-8 5V7l8 5z",
  northeast: "M21 3l-9.5 9.5M21 3v7M21 3h-7",
  northwest: "M3 3l9.5 9.5M3 3v7M3 3h7",
  southeast: "M21 21l-9.5-9.5M21 21v-7M21 21h-7",
  southwest: "M3 21l9.5-9.5M3 21v-7M3 21h7",
  up: "M12 4l7 14H5l7-14z",
  down: "M12 20L5 6h14l-7 14z",
  // Participant teams (the combat participant frame, task 6.1).
  allies: "M12 2l4 4 4-1 1 4 4 4-4 3 1 4-4 1-3 4-3-4-4-1 1-4-4-3-4-4 1-4 4-1 3-4 3 4z",
  foes: "M3 3l18 18M21 3L3 21",
  // The drawer chrome's close glyph (the reference's `.closebtn` X,
  // docs/design/elosern-redesign/index.html).
  close: "M6 6l12 12M18 6 6 18",
};

// Per-key stroke attributes copied selectively from the reference: `move`
// (cap+join), `interact` (join only), `attack`/`flee` (cap only); every
// other key keeps the SVG defaults (the star glyphs `suggestions`/`skills`
// must NOT be rounded, so the reference omits the attributes there).
const STROKE_ATTRS = {
  move: { "stroke-linecap": "round", "stroke-linejoin": "round" },
  interact: { "stroke-linejoin": "round" },
  attack: { "stroke-linecap": "round" },
  flee: { "stroke-linecap": "round" },
  // The close X must render with rounded caps, matching the reference.
  close: { "stroke-linecap": "round" },
};

// Return the reference's per-key stroke attributes for a stable key, or an
// empty object when the reference sets none for that glyph.
export function glyphAttrs(key) {
  if (typeof key !== "string") {
    return {};
  }
  return STROKE_ATTRS[key] || {};
}

// Return the SVG path `d` string for a stable key, or null when unmapped.
// Callers render the glyph `aria-hidden` beside the real text label.
export function glyphPath(key) {
  if (typeof key !== "string") {
    return null;
  }
  return GLYPHS[key] || null;
}

// A presentational glyph SVG element (the draft's `.ic` slot). `size` in
// pixels; the SVG carries no a11y role (the text label is the accessible
// name).
export function glyphSvg(key, size = 16) {
  const d = glyphPath(key);
  if (!d) {
    return null;
  }
  // The reference's tab-bar `.ic` icons all use `stroke-width="1.9"`.
  const pathProps = Object.assign(
    { d, stroke: "currentColor", "stroke-width": 1.9 },
    glyphAttrs(key),
  );
  return {
    tag: "svg",
    props: {
      width: size,
      height: size,
      viewBox: "0 0 24 24",
      fill: "none",
      "aria-hidden": "true",
    },
    children: [{ tag: "path", props: pathProps }, { tag: "circle", props: { cx: 12, cy: 12, r: 11, stroke: "currentColor", "stroke-width": 1.8, fill: "none" } }],
  };
}
