// Pure helpers of the travel walking slice (OpenSpec change
// wilderness-travel-walking-ui; interface design §5/§6). No Vue, no DOM and
// no rules: a direction is one of the eight canonical words, its target is
// the committed exit row the existing compass model resolves for that
// bearing, and nothing here invents an exit, a destination or a route.
import { aimFromKeys, octantIndex, resolveTargets, snapAngled } from "../compass-model.js";

/** The eight neighbour directions clockwise from north (map y grows north). */
export const DIRECTIONS = Object.freeze(
  [
    { key: "north", angle: 0, word: "北", dx: 0, dy: 1 },
    { key: "northeast", angle: 45, word: "東北", dx: 1, dy: 1 },
    { key: "east", angle: 90, word: "東", dx: 1, dy: 0 },
    { key: "southeast", angle: 135, word: "東南", dx: 1, dy: -1 },
    { key: "south", angle: 180, word: "南", dx: 0, dy: -1 },
    { key: "southwest", angle: 225, word: "西南", dx: -1, dy: -1 },
    { key: "west", angle: 270, word: "西", dx: -1, dy: 0 },
    { key: "northwest", angle: 315, word: "西北", dx: -1, dy: 1 },
  ].map((d) => Object.freeze(d)),
);

const BY_KEY = new Map(DIRECTIONS.map((d) => [d.key, d]));

export const ARROW_KEYS = Object.freeze(["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"]);

/** The direction record of a canonical word, or null. */
export function directionOf(key) {
  return BY_KEY.get(key) ?? null;
}

/** The held arrows' eight-way direction (the compass key combination), or null when they cancel. */
export function directionForKeys(keys) {
  const angle = aimFromKeys(keys);
  return angle === null ? null : DIRECTIONS[octantIndex(angle)].key;
}

/** The direction from the party cell to an adjacent cell, or null for any other cell. */
export function directionForCell(party, cell) {
  if (!party || !cell) return null;
  const dx = cell.x - party.x;
  const dy = cell.y - party.y;
  if ((dx === 0 && dy === 0) || Math.abs(dx) > 1 || Math.abs(dy) > 1) return null;
  return DIRECTIONS.find((d) => d.dx === dx && d.dy === dy)?.key ?? null;
}

/**
 * The committed exit target a direction aims at, through the existing compass
 * resolution: every committed row (including schema-6 rows whose destination
 * is withheld, which resolve by their direction word) becomes an angled or
 * portal target and the direction's bearing snaps within the compass
 * tolerance. Null when no angled exit answers that bearing.
 */
export function travelTarget(direction, rows, localMapModel, currentNode) {
  const d = directionOf(direction);
  if (!d) return null;
  const targets = resolveTargets(rows || [], localMapModel, { currentNode });
  return snapAngled(targets.angled, d.angle);
}
