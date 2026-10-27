// The game map's scope policy for named zoom stops. The spans, the Chinese
// stop labels and the stop families are this game's, not the shared
// primitives': `@elosern/map-view` owns the ordering, dedupe, stepping and
// limit rules, this module owns what each game surface offers.
//
// Units: the world tab is in kilometres (UNITS.km), settlement grids in
// metres (UNITS.m), and the wilderness area view in provider cells whose size
// comes from the panel's own cell_km scale.

import { DEFAULT_MARGIN_PX, createStop, fitBounds, orderedStops } from "@elosern/map-view";

/** Fixed world stop spans in kilometres (design §6.3). */
export const WORLD_COUNTRY_SPAN_KM = 800;
export const WORLD_DISTRICT_SPAN_KM = 200;
export const WORLD_NEARBY_SPAN_KM = 40;
/** Wilderness surroundings stop: the provider's 15 x 15 cell window. */
export const WILDERNESS_WINDOW_CELLS = 15;
/** Wilderness nearby stop: the eight neighbours plus one ring of context. */
export const WILDERNESS_NEARBY_CELLS = 5;
/** Floor for the settlement nearby stop so a lone node never zooms forever. */
export const MIN_NEARBY_SPAN_M = 400;

/**
 * World stops in km: 大陸 fits the actual continent bounds for this frame's
 * aspect ratio (never narrower than 國), then 國 800, 地區 200, 近郊 40.
 */
export function worldStops(continentBounds, frame, { marginPx = DEFAULT_MARGIN_PX } = {}) {
  const continent = fitBounds(continentBounds, frame, { marginPx }).span;
  return orderedStops([
    createStop("continent", "大陸", Math.max(continent, WORLD_COUNTRY_SPAN_KM)),
    createStop("country", "國", WORLD_COUNTRY_SPAN_KM),
    createStop("district", "地區", WORLD_DISTRICT_SPAN_KM),
    createStop("nearby", "近郊", WORLD_NEARBY_SPAN_KM),
  ]);
}

/**
 * Settlement stops in metres, derived from known geometry: 全城 fits every
 * known node, 近處 fits the current node and its adjacent nodes (floored at
 * minNearbySpan, capped at 全城), and 街區 is their geometric mean.
 */
export function settlementStops(wholeBounds, nearbyBounds, frame, {
  marginPx = DEFAULT_MARGIN_PX,
  minNearbySpan = MIN_NEARBY_SPAN_M,
} = {}) {
  const whole = fitBounds(wholeBounds, frame, { marginPx, minSpan: minNearbySpan }).span;
  const nearby = Math.min(whole, fitBounds(nearbyBounds, frame, { marginPx, minSpan: minNearbySpan }).span);
  return orderedStops([
    createStop("whole", "全城", whole),
    createStop("district", "街區", Math.sqrt(whole * nearby)),
    createStop("nearby", "近處", nearby),
  ]);
}

function cellWindow(cells) {
  const half = cells / 2;
  return { minX: -half, minY: -half, maxX: half, maxY: half };
}

/** Wilderness stops in cell units: 周邊 (the 15-cell window) and 近處. */
export function wildernessStops(frame, { marginPx = DEFAULT_MARGIN_PX } = {}) {
  return orderedStops([
    createStop("surroundings", "周邊", fitBounds(cellWindow(WILDERNESS_WINDOW_CELLS), frame, { marginPx }).span),
    createStop("nearby", "近處", fitBounds(cellWindow(WILDERNESS_NEARBY_CELLS), frame, { marginPx }).span),
  ]);
}
