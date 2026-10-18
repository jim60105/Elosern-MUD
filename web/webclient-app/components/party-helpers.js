// party-helpers.js (webclient-align-05-party-hud)
// Shared display helpers for the standing lineup and companion drawer.
import { portraitGlyph } from "./character-identity.js";

/**
 * The companion rows of a committed party panel. Row 0 is the commander's own
 * row (the player's figure) and no lineup, drawer or catalog consumer may draw
 * it as a companion. Wire rows carry exactly `commander`/`companion`; a display
 * figure built from a companion row carries no role, so this predicate excludes
 * the commander row instead of requiring the companion literal — the protocol
 * validator already guarantees the closed set.
 */
export function companionRows(slots) {
  return (Array.isArray(slots) ? slots : []).filter(
    (row) => row && row.role !== "commander",
  );
}

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
 * Resolve the canonical artwork descriptor a row's catalog reference names.
 * Returns the descriptor or null when the reference is null/unadmitted or the
 * committed catalog does not carry it (a dangling admitted reference — the
 * figure renderer reports that as a local failure, never as invented art).
 */
export function portraitFor(artPanel, portraitRef) {
  if (portraitRef === null || portraitRef === undefined) {
    return null;
  }
  const catalog = (artPanel && artPanel.portrait_catalog) || {};
  const entry = catalog[portraitRef];
  return entry?.artwork ?? null;
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
