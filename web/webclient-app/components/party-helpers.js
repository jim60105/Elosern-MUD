// party-helpers.js (webclient-align-05-party-hud)
// Shared display helpers for the party quickbar (.comps) and the
// companions drawer (dr-party).
import { portraitGlyph } from "./character-identity.js";

/**
 * Display-only finite normalization helper for the HP hairline bar.
 * Returns an integer percentage clamped to [0, 100].
 * Returns 0 when maximum is not a positive finite number.
 */
export function hpFillRatio(hpCurrent, hpMaximum) {
  const max = Number(hpMaximum);
  const cur = Number(hpCurrent);
  if (!Number.isFinite(max) || max <= 0 || !Number.isFinite(cur)) {
    return 0;
  }
  const ratio = cur / max;
  return Math.max(0, Math.min(100, Math.round(ratio * 100)));
}

/**
 * Resolve an art catalog entry for a companion row.
 * Returns the catalog entry (with url) or null when unresolvable / null ref.
 */
export function portraitFor(artPanel, portraitRef) {
  if (portraitRef === null || portraitRef === undefined) {
    return null;
  }
  const catalog = (artPanel && artPanel.portrait_catalog) || {};
  const entry = catalog[portraitRef];
  return (entry && entry.url) ? entry : null;
}

/**
 * Build a lookup Map from companion identity string to combat participant token.
 */
export function buildCombatTokenMap(combatParticipants) {
  const map = new Map();
  if (Array.isArray(combatParticipants)) {
    for (const p of combatParticipants) {
      if (p && p.identity != null && p.token) {
        map.set(String(p.identity), p.token);
      }
    }
  }
  return map;
}

export { portraitGlyph };
