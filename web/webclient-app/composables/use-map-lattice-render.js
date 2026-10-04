// MapLattice render group (improve-webclient-map-overlay-scale): the
// marker/label/edge/legend presentational math extracted verbatim from
// `MapLattice.vue` so the SFC stays a passive renderer. Owns the edge-marker
// name fitting (map-02 D3b/D4 placement), the draft label ladder, the
// edge/legend state class derivations, and node activation. Consumes the
// geometry group's edge-marker set and name-box bound explicitly; emits are
// passed through from the SFC.
import { computed } from "vue";
import { MARKER_DIAMOND_HALF } from "./use-map-lattice-geometry.js";
import { CELL_EM, charCells } from "../lib/mono_cells.js";

// One line step per glyph: the island's left/right names stack one glyph per
// line, so each glyph costs one type step however wide it draws.
const oneStep = () => 1;

function measureOf(chars, measure) {
  let total = 0;
  for (const ch of chars) total += measure(ch);
  return total;
}

// Fit an edge-marker name into `budget` units of `measure` (monospace cells
// for a horizontal line, line steps for a vertical stack; "…" costs 1 in
// both). The whole name when it fits; else the head truncated before a kept
// `（qualifier）`; else one head glyph, "…", and the longest tail that fits,
// with any room left growing the head. Returns "" when no head-and-tail form
// fits, so the diamond and its title stand alone.
export function fitMarkerName(label, budget, measure = charCells) {
  if (!label || budget < 3) return "";
  const chars = Array.from(label);
  if (measureOf(chars, measure) <= budget) return label;
  const ellipsis = measure("…");
  const parenIdx = label.lastIndexOf("（");
  if (parenIdx > 0 && label.endsWith("）") && parenIdx < label.length - 1) {
    const qualifier = label.slice(parenIdx);
    let used = measureOf(Array.from(qualifier), measure) + ellipsis;
    let head = "";
    for (const ch of Array.from(label.slice(0, parenIdx))) {
      if (used + measure(ch) > budget) break;
      used += measure(ch);
      head += ch;
    }
    if (head) return head + "…" + qualifier;
  }
  let headLen = 1;
  let used = measure(chars[0]) + ellipsis;
  let tailLen = 0;
  while (tailLen < chars.length - 2 && used + measure(chars[chars.length - 1 - tailLen]) <= budget) {
    used += measure(chars[chars.length - 1 - tailLen]);
    tailLen += 1;
  }
  if (tailLen === 0) return "";
  while (headLen + tailLen < chars.length - 1 && used + measure(chars[headLen]) <= budget) {
    used += measure(chars[headLen]);
    headLen += 1;
  }
  return chars.slice(0, headLen).join("") + "…" + chars.slice(chars.length - tailLen).join("");
}

export function useMapLatticeRender(props, emit, geometry) {
  const { activeEdgeMarkers, outwardNameCells } = geometry;

  const fittedEdgeMarkers = computed(() => {
    const markers = activeEdgeMarkers.value.markers || [];
    if (!props.markerNames || markers.length === 0) {
      return markers.map((m) => ({
        ...m,
        visibleName: "",
        glyphs: [],
      }));
    }

    const fittedList = markers.map((m) => {
      const span = m.span || 0;
      const sideways = m.side === "left" || m.side === "right";
      // The island stacks left/right names one glyph per line, so their
      // budget is in type steps; every other name is one horizontal line
      // budgeted in whole monospace cells (the epsilon keeps an exact fit
      // from flooring one cell short).
      const stacked = sideways && !props.overlayChrome;
      const drawsOutward = outwardNameCells.value > 0 && sideways;
      const budget = stacked
        ? Math.floor(span / props.markerNameFont)
        : Math.min(
            Math.floor(span / (CELL_EM * props.markerNameFont) + 1e-9),
            drawsOutward ? outwardNameCells.value : Infinity,
          );
      const fitted = fitMarkerName(m.name, budget, stacked ? oneStep : charCells);
      return {
        ...m,
        visibleName: fitted,
        glyphs: Array.from(fitted),
      };
    });

    const nameCounts = new Map();
    fittedList.forEach((m) => {
      if (m.visibleName) {
        nameCounts.set(m.visibleName, (nameCounts.get(m.visibleName) || 0) + 1);
      }
    });

    const ambiguousNames = new Set();
    nameCounts.forEach((count, name) => {
      if (count > 1) {
        const collisions = fittedList.filter((m) => m.visibleName === name);
        const distinctOriginals = new Set(collisions.map((c) => c.name));
        if (distinctOriginals.size > 1) {
          ambiguousNames.add(name);
        }
      }
    });

    fittedList.forEach((m) => {
      if (ambiguousNames.has(m.visibleName)) {
        m.visibleName = "";
        m.glyphs = [];
      }
    });

    return fittedList;
  });

  // The label baseline sits below the node origin: the marker footprint's
  // reserved half at this scale (the actionable halo's 10-unit radius plus a
  // 1-unit gap), the 2-unit model margin, then a full type step — so the
  // label's box starts clear of its own node's widest drawn footprint and
  // grows with the declared label size. One rule for every surface: the
  // `labelFont === 11` branch that used to sit here existed only because the
  // bare mount's default step was 11, and the default is the shared 16-unit
  // floor now (retarget-desktop-viewport-contract D7), so the sentinel is
  // gone.
  const LABEL_BASELINE_HALF = 11;
  function labelY() {
    return LABEL_BASELINE_HALF * props.markerScale + 2 + props.labelFont;
  }

  // Label tiers (draft label palette, webclient-map-01-draft-chrome): the
  // current node reads brightest, a landmark is gold, a visited node reads
  // seen, an unvisited node reads far (faintest). Remembered nodes live in the
  // island's list, which keeps the plain paper label.
  function labelTier(node) {
    if (node.visibility === "current") return "here";
    // A remembered gateway also carries `landmark: true` now (local-map-
    // remembered-are-map-gateways design D2), but a remembered node is never
    // drawn through this ladder -- it lives in the island's list/edge-marker
    // presentation instead (`rememberedList`/`edgeMarkers`, not `drawnNodes`).
    // The check mirrors the existing landmark-ring guard below so the
    // "remembered never gets the gold in-lattice treatment" invariant is
    // enforced here too, not only by the reducer's current node/remembered
    // split staying in sync (rubber-duck run 2).
    if (node.landmark && node.visibility !== "remembered") return "gold";
    if (node.visibility === "visible_visited") return "seen";
    return "far";
  }

  function edgeClass(edge) {
    if (edge.known === false) return "local-map__edge--unknown";
    return edge.traversable ? "local-map__edge--traversable" : "local-map__edge--blocked";
  }

  // Node activation: every click first emits `select` (the island's selection
  // state updates its detail line) and only emits `move` when the node
  // carries an exact `move` action.
  function activateNode(node) {
    emit("select", node);
    if (node.action && node.action.kind === "move") {
      emit("move", {
        exit_ref: node.action.exit_ref,
        destination: node.action.destination,
      });
    }
  }

  // Edge-marker name placement (map-02 D4 wording): the name box is drawn
  // OUTWARD from the diamond's outer tip — never toward the canvas. The
  // name's monospace glyph line does not scale with the markers (same policy
  // as the node labels), so the offset is the scaled rotated-diamond axial
  // reach plus the 2-unit model margin and one ascent to the baseline at the
  // surface's declared 16-unit name step (retarget-desktop-viewport-contract
  // D7; the old 11 was that step's 11px ascent).
  const MARKER_NAME_ASCENT = 16;
  function markerOutset() {
    return Math.SQRT2 * MARKER_DIAMOND_HALF * props.markerScale + 2;
  }
  function markerNameX(marker) {
    if (props.overlayChrome) {
      if (marker.side === "left") return -markerOutset();
      if (marker.side === "right") return markerOutset();
      return 0;
    }
    if (marker.side === "top" || marker.side === "bottom") return 0;
    const reach = Math.SQRT2 * MARKER_DIAMOND_HALF * props.markerScale;
    const bandCenter = reach + 9;
    return marker.side === "left" ? -bandCenter : bandCenter;
  }
  function markerNameY(marker) {
    if (props.overlayChrome) {
      if (marker.side === "top") return -(markerOutset() + MARKER_NAME_ASCENT);
      if (marker.side === "bottom") return markerOutset() + MARKER_NAME_ASCENT;
      return 4;
    }
    const reach = Math.SQRT2 * MARKER_DIAMOND_HALF * props.markerScale;
    // The name sits in the band, clear of the diamond's axial reach by the same
    // 4-unit gap on either horizontal edge: above the marker on `top` (the
    // baseline, so the ascent grows outward), below it on `bottom` (one type
    // step past the gap, so the whole line clears the diamond).
    if (marker.side === "top") return -(reach + 4);
    if (marker.side === "bottom") return reach + 4 + props.markerNameFont;
    // Vertical edges stack one glyph per line, so the column is centred on the
    // marker by lifting it half its own height and dropping the first baseline
    // by roughly half a glyph's ascent.
    const k = marker.glyphs?.length || 1;
    return -((k - 1) * props.markerNameFont) / 2 + props.markerNameFont * 0.36;
  }
  function markerNameAnchor(marker) {
    if (props.overlayChrome) {
      if (marker.side === "left") return "end";
      if (marker.side === "right") return "start";
      return "middle";
    }
    return "middle";
  }

  return {
    fittedEdgeMarkers,
    labelY,
    labelTier,
    edgeClass,
    activateNode,
    markerNameX,
    markerNameY,
    markerNameAnchor,
  };
}
