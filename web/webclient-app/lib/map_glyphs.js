// This game's glyph policy: the uniform scale each surface draws the shared
// node glyph at, and the mapping from a committed local_map/area_map node to
// the explicit glyph input the shared primitives take. The glyph shapes and
// their painted extents live in `@elosern/map-view`; the node's own fields
// (visibility, gateway, action) are this game's knowledge and stop here.
//
// Every surface draws MapNodeGlyph's whole group at one uniform scale, and its
// footprints, label clearance, stub start and aim ring all follow it.

import { glyphFootprint } from "@elosern/map-view";

/** The minimap island's one glyph scale: the single place it is set. */
export const ISLAND_GLYPH_SCALE = 0.75;
/** The area map's wilderness cells draw the shared glyphs at this scale. */
export const AREA_CELL_GLYPH_SCALE = 0.875;

/**
 * The travel party seal (MapNodeGlyph state "party"; wilderness-travel-map-ui)
 * in base units: a seal-red disc with a gold rim and core under a breathing
 * halo ring. The travel stage draws it at `cellPx / TRAVEL_GLYPH_CELL`.
 */
export const PARTY_GLYPH = Object.freeze({ haloR: 16, bodyR: 10.5, rim: 2, coreR: 3.4 });
/** The cell size, in CSS px, at which the travel glyphs draw at scale 1. */
export const TRAVEL_GLYPH_CELL = 30;

/**
 * The shared glyph input for one payload node: which shape it draws and
 * whether a travel halo sits under it.
 */
export function markerGlyphInput(node) {
  return {
    state: node?.visibility === "current" ? "current" : "node",
    gateway: typeof node?.gateway?.leads_to === "string" && node.gateway.leads_to.length > 0,
    haloTarget: !!node?.action,
  };
}

/** The painted footprint of a node's glyph drawn at `size`. */
export function paintedMarkerFootprint(node, size = 1) {
  return glyphFootprint(markerGlyphInput(node), size);
}

/**
 * The travel ornaments' base geometry (the travel TravelGlyph component),
 * one source per concept and state, drawn at the same uniform scale rule as
 * the party seal:
 *
 * - `landmark` is the HUD band ornament's diamond (`--band-ornament` in
 *   styles/tokens.css: half-diagonal 4.7, centre dot 1.3, stroke 1);
 * - `neighbour` is one of the eight targets around the party (open, aimed,
 *   blocked, unknown);
 * - `hostile` is a live-sight hostile's seal with its soft halo;
 * - `route` is one predicted step mark per stage (normal, light, moderate,
 *   severe), for the route preview a later slice draws.
 */
export const TRAVEL_GLYPHS = Object.freeze({
  landmark: Object.freeze({ half: 4.7, dotR: 1.3, stroke: 1 }),
  neighbour: Object.freeze({ openR: 3.2, aimedR: 4.6, blockedR: 3.2, unknownR: 2.4 }),
  hostile: Object.freeze({ haloR: 12, sealR: 8.4, chevron: 3.9 }),
  route: Object.freeze({ dotR: 3.3, diamond: 3.2, ringR: 3.1, innerR: 1.3 }),
});
