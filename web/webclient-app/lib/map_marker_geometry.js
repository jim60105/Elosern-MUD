// Pure painted extents shared by island projection, label layout and drawing.
// Every node glyph is the full map's (the MapNodeGlyph component), drawn by
// the area map, the minimap island and the map legend alike, so a place reads
// the same on every map. Radii are pre-scale units; the lattice multiplies them
// by its `markerScale` prop so every state scales uniformly. A footprint is the
// radius of the whole painted mark, stroke included.
export const HERE_GLOW_R = 14;
export const HERE_RING_R = 10;
export const HERE_DOT_R = 6;
export const NODE_DOT_R = 5.5;
export const HALO_R = 15;
// The gate: a filled arch `GATE_HALF` wide either side, its springing line
// 2 units above the node centre and its base `GATE_HALF` below.
export const GATE_HALF = 8;
export const GATE_STROKE = 2;
// The rim edge markers' landmark ring (edge direction diamonds only).
export const MARKER_LANDMARK_R = 5;
// The mitred base corners are the farthest painted points of the arch.
export const GATE_FOOTPRINT = Math.hypot(GATE_HALF + GATE_STROKE / 2, GATE_HALF + GATE_STROKE / 2);

export function gatePath(scale = 1) {
  const h = GATE_HALF * scale;
  const spring = -2 * scale;
  return `M${-h} ${h} V${spring} A${h} ${h} 0 0 1 ${h} ${spring} V${h} Z`;
}

export function paintedMarkerFootprint(node) {
  const halo = node?.action ? HALO_R + 1 : 0;
  if (node?.visibility === "current") return Math.max(halo, HERE_GLOW_R);
  if (typeof node?.gateway?.leads_to === "string" && node.gateway.leads_to.length > 0) {
    return Math.max(halo, GATE_FOOTPRINT);
  }
  return Math.max(halo, NODE_DOT_R + GATE_STROKE / 2);
}
