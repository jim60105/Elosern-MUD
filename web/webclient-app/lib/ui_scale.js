// The desktop chrome scale (webclient-proportional-ui-scale; AVG stage design
// §2 decision 2): one unitless factor,
// `S = clamp(1, min(viewportHeight / 790, viewportWidth / 1451), 1.4)`,
// written once to the root as `--ui-scale`. Stylesheets multiply their fixed
// CSS-pixel chrome literals by it (`calc(16px * var(--ui-scale))`), so above
// the reference the drawing grows once, and at 2560x1440 — where both raw
// ratios exceed the cap — chrome renders at the 1.4 cap. Every viewport at or
// below the reference, and every viewport narrower than its own height would
// imply, keeps S = 1. The reference is 1451x790 CSS px, the player's real
// browser viewport (retarget-desktop-viewport-contract): the drawn geometry is
// the geometry the player sees, and the 16px type floor holds at scale 1.
// Viewport-relative prose, band and stage-art terms (`vh`/`vw`) are never
// multiplied by it, so nothing scales twice. The reader's prose scale is a
// separate multiplier. The width term keeps a tall, narrow window — one whose
// width is narrower than the reference's own aspect ratio implies — from
// growing chrome past what its width breakpoints were drawn for.

export const UI_SCALE_REFERENCE_HEIGHT = 790;
export const UI_SCALE_REFERENCE_WIDTH = 1451;
export const UI_SCALE_MAX = 1.4;
export const UI_SCALE_PROPERTY = "--ui-scale";

// The factor for a viewport in CSS pixels. A dimension that is not a positive
// finite number (a zero-sized frame, a detached window) reads as the
// reference: chrome never shrinks below its reference readability floor. A
// missing or unusable width leaves the height alone in charge.
export function computeUiScale(height, width = Infinity) {
  const h = Number(height);
  if (!Number.isFinite(h) || h <= 0) return 1;
  const w = Number(width);
  const widthRatio = w > 0 ? w / UI_SCALE_REFERENCE_WIDTH : Infinity;
  const ratio = Math.min(h / UI_SCALE_REFERENCE_HEIGHT, widthRatio);
  const raw = Math.min(UI_SCALE_MAX, Math.max(1, ratio));
  return Math.round(raw * 10000) / 10000;
}

// The single resize owner: writes the factor to the root immediately, then
// only when a resize changes it (no per-frame layout reads). Returns a
// dispose that removes the listener and the root property.
export function installUiScale({
  win = typeof window === "undefined" ? null : window,
  root = typeof document === "undefined" ? null : document.documentElement,
} = {}) {
  if (!win || !root) return () => {};
  let current = null;
  const apply = () => {
    const next = computeUiScale(win.innerHeight, win.innerWidth);
    if (next === current) return;
    current = next;
    root.style.setProperty(UI_SCALE_PROPERTY, String(next));
  };
  apply();
  win.addEventListener("resize", apply, { passive: true });
  return () => {
    win.removeEventListener("resize", apply);
    root.style.removeProperty(UI_SCALE_PROPERTY);
  };
}
