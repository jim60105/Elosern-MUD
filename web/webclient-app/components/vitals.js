// Vitals presentation derivations (H2, webclient-hud-02-status-islands,
// design D4/D5): the per-gauge ratio math, the low-HP predicate at the
// pinned 25% display-only threshold, and the trailing (ghost) bar rule.
// Pure functions; nothing is interpolated, extrapolated, or derived from
// narrative text or an action result.

// The low-HP threshold is a presentation constant: no server field, trait,
// or condition expresses "low health", so the client derives it locally and
// keeps it non-load-bearing (the numerals and the 危險 marker carry the
// same information at every value).
export const LOW_HP_THRESHOLD = 0.25;

// A gauge's ratio in percent. A missing gauge or non-numeric fields yield
// null (no value is invented); a non-positive maximum yields 0.
export function gaugeRatio(gauge) {
  if (!gauge || typeof gauge.current !== "number" || typeof gauge.maximum !== "number") {
    return null;
  }
  if (gauge.maximum <= 0) {
    return 0;
  }
  return (gauge.current / gauge.maximum) * 100;
}

// The low-HP presentation state, derived from the committed hp ratio alone
// against the single display-only threshold. An unavailable or absent
// resources object yields false rather than true-by-default.
export function isLowHp(resources) {
  const hp = gaugeRatio(resources && resources.hp);
  return hp !== null && hp <= LOW_HP_THRESHOLD * 100;
}
