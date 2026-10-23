// Pure painted extents shared by island projection, label layout and drawing.
// Radii are pre-scale units, multiplied by the lattice's `markerScale` prop so
// every state scales uniformly (webclient-map-01-draft-chrome D2). A footprint
// is the radius of the whole painted mark, stroke included: the marker set
// stays below the pre-draft 26px square / r=12 circles, while a gateway's arch
// and feet reach further (label-minimap-exits-and-gateways).
export const MARKER_CURRENT_R = 8;
export const MARKER_DOT_R = 4.5;
export const MARKER_LANDMARK_R = 5;
export const HALO_R = 10;
export const GATE_ARCH_R = 12;
export const GATE_FOOT_REACH = 3;
export const GATE_STROKE = 1.6;
// The round stroke caps extend the feet past the arch on both axes, so the
// reserved radius is the farthest painted foot corner from the node centre.
export const GATE_FOOTPRINT = Math.hypot(
  GATE_ARCH_R + GATE_FOOT_REACH + GATE_STROKE / 2,
  GATE_ARCH_R - 2 + GATE_STROKE / 2,
);

export function paintedMarkerFootprint(node) {
  if (typeof node?.gateway?.leads_to === "string" && node.gateway.leads_to.length > 0) return GATE_FOOTPRINT;
  if (node?.action) return HALO_R + 1;
  if (node?.visibility === "current") return MARKER_CURRENT_R + 1;
  return Math.max(MARKER_DOT_R + (node?.visibility === "visible_unvisited" ? 1 : 0.5),
    node?.landmark ? MARKER_LANDMARK_R + 0.5 : 0);
}
