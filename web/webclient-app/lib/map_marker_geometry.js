// Pure painted extents shared by island projection, label layout and drawing.
// Every node glyph is the full map's (the MapNodeGlyph component), drawn by
// the area map, the minimap island and the map legend alike, so a place reads
// the same on every map. Radii are base units: a surface draws the whole
// glyph group at one uniform scale (strokes and dashes included), so surfaces
// differ only by that scale. A footprint is the radius of the whole painted
// mark, stroke included, at a given scale.
export const HERE_GLOW_R = 14;
export const HERE_RING_R = 10;
export const HERE_DOT_R = 6;
export const NODE_DOT_R = 5.5;
export const HALO_R = 15;
// The minimap island's one glyph scale: the island draws every node glyph at
// this uniform size, and its footprints, label clearance, stub start and aim
// ring all follow it. The single place the island glyph size is set.
export const ISLAND_GLYPH_SCALE = 0.75;
// The area map's wilderness cells draw the shared glyphs at this scale, so the
// arch keeps a 7-unit half-width inside the smallest cell.
export const AREA_CELL_GLYPH_SCALE = 0.875;
// The gate: a filled arch `GATE_HALF` wide either side, its springing line
// 2 units above the node centre and its base `GATE_HALF` below.
export const GATE_HALF = 8;
export const GATE_STROKE = 2;
// The rim edge markers' landmark ring (edge direction diamonds only).
export const MARKER_LANDMARK_R = 5;
// The mitred base corners are the farthest painted points of the arch.
export const GATE_FOOTPRINT = Math.hypot(GATE_HALF + GATE_STROKE / 2, GATE_HALF + GATE_STROKE / 2);

// The gate arch's base path; a surface scales the whole glyph group instead.
export function gatePath() {
  const h = GATE_HALF;
  return `M${-h} ${h} V-2 A${h} ${h} 0 0 1 ${h} -2 V${h} Z`;
}

function baseFootprint(node) {
  const halo = node?.action ? HALO_R + 1 : 0;
  if (node?.visibility === "current") return Math.max(halo, HERE_GLOW_R);
  if (typeof node?.gateway?.leads_to === "string" && node.gateway.leads_to.length > 0) {
    return Math.max(halo, GATE_FOOTPRINT);
  }
  return Math.max(halo, NODE_DOT_R + GATE_STROKE / 2);
}

// The painted footprint of a node's glyph drawn at `size`.
export function paintedMarkerFootprint(node, size = 1) {
  return baseFootprint(node) * size;
}
