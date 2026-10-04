// The narrative prose scale's numeric contract
// (retarget-desktop-viewport-contract D6; webclient-contextual-hud "Narrative
// prose scale is a client-local preference the settings surface owns").
//
// The scale is stored as the multiplier the prose targets multiply into
// `--prose-scale`; the three steps are the draft's A− / A / A+ segment. The
// token under them (`--message-text` / `--log-text`) is the 16 CSS px
// reference floor, so A− = 1 renders the prose at exactly 16px at the
// reference scale, and no step renders it smaller.
//
// One module owns the values because two places must agree on them: the
// settings surface builds its segment from them, and the presentation-
// preferences slice normalizes a stored value that matches none of them to the
// default step (a legacy multiplier such as 0.92 or 1.12 loads as A — no
// layout-version bump, because a stale presentation multiplier is exactly as
// harmless as a stale presentation key).
export const PROSE_SCALE_STEPS = [1, 1.125, 1.25];

// A (the middle step) is the default: the reference-scale page text reads at
// 18 CSS px at the default prose scale.
export const PROSE_SCALE_DEFAULT = 1.125;

export function normalizeProseScale(value) {
  return PROSE_SCALE_STEPS.includes(value) ? value : PROSE_SCALE_DEFAULT;
}
