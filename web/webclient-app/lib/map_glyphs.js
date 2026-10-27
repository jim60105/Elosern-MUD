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
