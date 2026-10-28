// Workbench arrangement and the tool registry (frontend design §2, §6).

// Minimum widths at --ui-scale 1, in CSS pixels.
export const NAV_MIN = 250;
export const INSPECTOR_MIN = 340;
export const CANVAS_MIN = 480;

// Both side columns become header-toggled drawers when the viewport cannot
// hold them beside a usable canvas, which is what 200 % browser zoom does to
// the 1451x790 reference (725 CSS px wide).
export function useDrawers({ width, scale = 1 }) {
  const factor = Number.isFinite(scale) && scale > 0 ? scale : 1;
  return width < (NAV_MIN + INSPECTOR_MIN + CANVAS_MIN) * factor;
}

// Tools per domain. This shell registers only selection; the domain tool
// slices add their own tools (node/room N, road/connection R, entrance E,
// control point A, ...) next to their commands.
export const TOOLS = Object.freeze({
  continent: [{ key: "select", label: "選取", glyph: "⌖", hotkey: "v" }],
  settlement: [{ key: "select", label: "選取", glyph: "⌖", hotkey: "v" }],
  interior: [{ key: "select", label: "選取", glyph: "⌖", hotkey: "v" }],
});

export function toolKeys(domain) {
  return Object.fromEntries((TOOLS[domain] ?? []).filter((tool) => tool.hotkey).map((tool) => [tool.hotkey, tool.key]));
}

export const DOMAIN_KEYS = Object.freeze({ 1: "continent", 2: "settlement", 3: "interior" });

// The return stack of cross-map navigation: capped, and an entry equal to
// the top is not pushed again, so Alt+← can never loop.
export const RETURN_LIMIT = 20;

function sameEntry(a, b) {
  return (
    a && b && a.domain === b.domain && a.mapId === b.mapId && JSON.stringify(a.selection ?? []) === JSON.stringify(b.selection ?? [])
  );
}

export function pushReturn(stack, entry) {
  if (sameEntry(stack.at(-1), entry)) return stack;
  return [...stack, entry].slice(-RETURN_LIMIT);
}
