// Units, distance captions and the scale bar. The host states which unit its
// coordinates are in (metres, kilometres, or the provider's cell size); only
// the caption helpers convert to metres, so a scope's coordinates are never
// rewritten.

import { FREEZE, requireFinite, requirePositive } from "./values.js";
import { scaleOf } from "./projection.js";

export const UNITS = FREEZE({
  m: FREEZE({ key: "m", metres: 1 }),
  km: FREEZE({ key: "km", metres: 1000 }),
});

/** Wilderness cell unit from the provider panel's metres-per-cell scale. */
export function cellUnit(cellMetres) {
  return FREEZE({ key: "cell", metres: requirePositive(cellMetres, "cellMetres") });
}

export function toMetres(value, unit) {
  return requireFinite(value, "value") * requirePositive(unit?.metres, "unit.metres");
}

/**
 * `850 m`, `1.5 km`, `40 km`. Rounds to one decimal place first so a value
 * just under a unit switch shows as the next unit. A distance below that
 * display resolution keeps its exact finite value instead of collapsing to
 * `0 m`, so a synthetic sub-decimetre distance still states its own length.
 */
export function formatDistance(metres) {
  const value = requireFinite(metres, "metres");
  const rounded = value !== 0 && Math.abs(value) < 0.05 ? value : Number(value.toFixed(1));
  if (Math.abs(rounded) >= 1000) {
    return `${Number((rounded / 1000).toFixed(3))} km`;
  }
  return `${rounded} m`;
}

/**
 * Scale bar for a caption: the largest 1/2/5 x 10^n metre length whose
 * on-screen length is at most maxPx at the view's uniform scale.
 */
export function scaleBar(view, frame, unit, maxPx = 120) {
  requirePositive(maxPx, "maxPx");
  const metresPerPx = toMetres(1, unit) / scaleOf(view, frame);
  const budget = metresPerPx * maxPx;
  let metres = 10 ** Math.floor(Math.log10(budget));
  for (const step of [5, 2]) {
    if (metres * step <= budget * (1 + 1e-9)) {
      metres *= step;
      break;
    }
  }
  return FREEZE({ metres, px: metres / metresPerPx, text: formatDistance(metres) });
}
