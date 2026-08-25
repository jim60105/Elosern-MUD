// Dock glyph table (H3 webclient-hud-03-action-dock, task 4.2): the fixed
// glyph map keyed by stable server keys — the exploration/combat root item
// keys, the look-entity `kind`, the canonical direction words, and the
// participant `team`. Unmapped keys render no icon (the tab bar's label
// carries the text). Every glyph is `aria-hidden` beside the real text
// label.
export const GLYPHS = {
  // Exploration root item keys (the G2 stable keys).
  move: "M12 2 7 9h4v6h-6v-6h4l-3-7z",
  look: "M12 4a8 8 0 1 0 0 16 8 8 0 0 0 0-16zm0 13a5 5 0 1 1 0-10 5 5 0 0 1 0 10z",
  interact: "M7 11v2h10v-2h2v2a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2v-2h2zm-4 0h18v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4z",
  character: "M12 2a5 5 0 1 1 0 10 5 5 0 0 1 0-10zm-7 22v-1c0-3.9 3.1-7 7-7s7 3.1 7 7v1h-14z",
  quests: "M6 3h12v2h2v5h-2v9a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2V5H5V3h1z",
  inventory: "M4 7h16v12H4V7zm2-2h12l-1 2H7L5 5z",
  wait: "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm1 4v7l5 3-1.5 2.4L11 14V7h2z",
  suggestions: "M12 2l2.4 4.9 5.4.8-3.9 3.8.9 5.4L12 14.5 7.2 16.9l.9-5.4L4.2 7.7l5.4-.8L12 2z",
  // Combat root item keys.
  attack: "M3 21l8-8 2 2 9-9-2-2-9 9-2-2-6 6 1 3 1-1z",
  skills: "M12 2l3 7 7 3-7 3-3 7-3-7-7-3 7-3 3-7z",
  items: "M12 2l10 6v8l-10 6-10-6V8l10-6z",
  defend: "M12 2l8 4v6c0 5-3.5 8.5-8 10-4.5-1.5-8-5-8-10V6l8-4z",
  flee: "M13 3l9 8-9 8v-5L6 21v-5L1 11l5-3 7-5z",
  forfeit: "M6 4h12v2h2v5h-2v7H6V4zm2 4h8v10H8V8z",
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
};

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
  return {
    tag: "svg",
    props: {
      width: size,
      height: size,
      viewBox: "0 0 24 24",
      fill: "none",
      "aria-hidden": "true",
    },
    children: [{ tag: "path", props: { d, stroke: "currentColor", "stroke-width": 1.8 } }, { tag: "circle", props: { cx: 12, cy: 12, r: 11, stroke: "currentColor", "stroke-width": 1.8, fill: "none" } }],
  };
}
