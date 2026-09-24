// MapLattice geometry group (improve-webclient-map-overlay-scale): the
// lattice/graph placement math extracted verbatim from `MapLattice.vue` so
// the SFC stays a passive renderer. Owns the payload reads, the
// wilderness label-suppression rule with the crowding-fix pitch derivation it
// feeds, the model-sourced placement (rank-compressed lattice vs radial
// graph), the edge-marker gutter/canvas layout, and every drawing position
// the template consumes (canvas size, node/edge/pin positions, dot-pattern
// phase, cap-resolved inline style). Pure computeds over explicit props — no
// watchers, no emit.
import { computed } from "vue";
import LocalMap from "../lib/local_map.js";

// Every lattice marker's base geometry in pre-scale units, multiplied by
// the `markerScale` prop so all states scale uniformly (draft ladder,
// webclient-map-01-draft-chrome D2): the current seal circle r=8 (visual
// half-extent 9 with the 2px stroke), the visited/unvisited dots r=4.5
// (+0.5 stroke → 5), the gold landmark ring r=5, the rotated remembered
// diamond half-extent 9, and the actionable halo r=10. Every footprint is
// strictly smaller than the pre-draft 26px square / r=12 circles, so the
// crowding fix's pitch guarantee carries over unchanged.
export const MARKER_CURRENT_R = 8;
export const MARKER_DOT_R = 4.5;
export const MARKER_LANDMARK_R = 5;
export const MARKER_DIAMOND_HALF = 9;
export const HALO_R = 10;

const LABEL_BAND = 14;

export function useMapLatticeGeometry(props) {
  const nodes = computed(() => (Array.isArray(props.localMap.nodes) ? props.localMap.nodes : []));
  const edges = computed(() => (Array.isArray(props.localMap.edges) ? props.localMap.edges : []));
  const legend = computed(() => (Array.isArray(props.localMap.legend) ? props.localMap.legend : []));
  const cols = computed(() => props.localMap.cols ?? 0);
  const rows = computed(() => props.localMap.rows ?? 0);

  const nodeById = computed(() => {
    const byId = {};
    for (const node of nodes.value) byId[node.id] = node;
    return byId;
  });

  // FLAGGED/STRIKEABLE (design D8b, ADDED requirement "The map surfaces state
  // a place name only where it adds information"): the wilderness 3x3
  // neighbourhood otherwise repeats one region name across every in-view cell
  // in it. Scoped to the `wilderness` layer only -- on `grid`/`instance`/
  // `interior`, a node's label is an individual room key, and two distinct
  // rooms coincidentally sharing a name are still two distinct places worth
  // naming, not the same shared-region repetition this rule exists to hide.
  const currentNodeLabel = computed(() => {
    const current = nodes.value.find((node) => node.visibility === "current");
    return current ? current.label : null;
  });

  function labelSuppressed(node) {
    return (
      props.localMap.layer === "wilderness" &&
      (node.visibility === "visible_unvisited" || node.visibility === "visible_visited") &&
      node.label === currentNodeLabel.value
    );
  }

  function truncatedLabel(label) {
    const value = String(label ?? "");
    return value.length > props.labelMax ? value.slice(0, props.labelMax) + "…" : value;
  }

  // Node labels are bounded and truncated (the full label stays reachable
  // through the node's accessible name); a truncated label appends "…"
  // (labelMax + 1 glyphs at 11px monospace, full-width CJK).
  function visibleNodeLabel(node) {
    if (labelSuppressed(node)) return "";
    return truncatedLabel(node.label);
  }

  // Effective pitch derivation (design D4): derived from what actually needs
  // clearing rather than a constant. Two horizontally adjacent drawn nodes both
  // showing visible labels trigger the label-cleared pitch ((labelMax + 1) * labelFont + 3).
  const adjacentDrawnLabelPair = computed(() => {
    const labeled = drawnNodes.value.filter((n) => visibleNodeLabel(n) !== "");
    for (let i = 0; i < labeled.length; i++) {
      for (let j = i + 1; j < labeled.length; j++) {
        const a = labeled[i];
        const b = labeled[j];
        if (a.row === b.row && Math.abs(a.col - b.col) === 1) {
          return true;
        }
      }
    }
    return false;
  });
  const labelClearancePitch = computed(() =>
    adjacentDrawnLabelPair.value ? (props.labelMax + 1) * props.labelFont + 3 : 0,
  );
  const isSquarePitch = computed(() => props.colPitch === props.rowPitch);
  // Placement sourcing (map-02 D2): the lattice variant draws the model's
  // rank-compressed `col`/`row` grid; the graph variant draws the model's
  // radial placement (design D1) at `markerScale`, so the D1 geometry
  // contract's footprints and the drawn footprints stay proportional and the
  // non-overlap invariant is scale-invariant under the caps. The canvas size
  // follows the active placement; `overflow: visible` lets the lattice
  // marker gutter (map-02 D3b) render outside the node canvas without
  // clipping. A graph payload with no radial placement renders empty (the
  // variant prop is only ever passed a model that carries one).
  const isGraph = computed(() => props.variant === "graph");
  const radial = computed(() =>
    isGraph.value && props.localMap.radial && Array.isArray(props.localMap.radial.nodes)
      ? props.localMap.radial
      : null,
  );
  const radialById = computed(() => {
    const byId = {};
    for (const node of radial.value ? radial.value.nodes : []) byId[node.id] = node;
    return byId;
  });

  // Edge direction markers (map-02 D3b): the lattice variant asks the model
  // for markers with its OWN drawing geometry — the natural node canvas
  // (before the gutter grows the SVG), the current node's in-canvas position,
  // the scaled diamond half-extent, and the outward name-box bound at the
  // overlay scale (the island's canonical reading path stays the remembered
  // list, so it passes a name-free geometry). The graph variant never marks:
  // a radial drawing has no canvas edge a bearing could point at.
  const rememberedList = computed(() =>
    Array.isArray(props.localMap.remembered) ? props.localMap.remembered : [],
  );
  function latticePos(node) {
    return {
      x: node.col * effectiveColPitch.value + effectiveColPitch.value / 2,
      y: (Math.max(1, rows.value) - 1 - node.row) * effectiveRowPitch.value + effectiveRowPitch.value / 2,
    };
  }

  const outwardNameBox = computed(() =>
    props.overlayChrome ? (props.labelMax + 1) * props.markerNameFont : 0,
  );

  const layoutGeometry = computed(() => {
    if (isGraph.value) {
      const L = graphCanvasWidth.value;
      if (props.canvasSize != null) {
        const PAD = LocalMap.RADIAL_GEOMETRY ? LocalMap.RADIAL_GEOMETRY.PAD : 24;
        const S = Math.max(Number(props.canvasSize), L - 2 * PAD + 16);
        const vx = L / 2 - S / 2;
        const vy = L / 2 - S / 2;
        return {
          fieldW: S,
          fieldH: S,
          marginX: 0,
          marginY: 0,
          gutter: 0,
          canvasWidth: S,
          canvasHeight: S,
          viewBoxX: vx,
          viewBoxY: vy,
          viewBoxWidth: S,
          viewBoxHeight: S,
          viewBox: `${vx} ${vy} ${S} ${S}`,
          markers: [],
          colPitch: props.colPitch,
          rowPitch: props.rowPitch,
        };
      }
      return {
        fieldW: L,
        fieldH: graphCanvasHeight.value,
        marginX: 0,
        marginY: 0,
        gutter: 0,
        canvasWidth: graphCanvasWidth.value,
        canvasHeight: graphCanvasHeight.value,
        viewBoxX: 0,
        viewBoxY: 0,
        viewBoxWidth: graphCanvasWidth.value,
        viewBoxHeight: graphCanvasHeight.value,
        viewBox: `0 0 ${graphCanvasWidth.value} ${graphCanvasHeight.value}`,
        markers: [],
        colPitch: props.colPitch,
        rowPitch: props.rowPitch,
      };
    }

    const current = nodes.value.find((node) => node.visibility === "current");
    const colsVal = Math.max(1, cols.value);
    const rowsVal = Math.max(1, rows.value);
    const hasRemembered = rememberedList.value.length > 0 && !!current;

    if (props.canvasSize != null) {
      const canvasSize = Number(props.canvasSize);
      const pMin = Math.max(props.colPitch, labelClearancePitch.value);
      const markerHalf = MARKER_DIAMOND_HALF * props.markerScale;
      const nameWidth = outwardNameBox.value;
      const nameHeight = props.markerNames ? 16 : 0;

      if (!hasRemembered) {
        const avail = canvasSize - 16;
        const pFit = Math.floor(Math.min(avail / colsVal, (avail - LABEL_BAND) / rowsVal));
        const p = Math.max(pMin, Math.min(pFit, Math.floor(1.5 * props.colPitch)));
        const cW = colsVal * p;
        const cH = rowsVal * p;
        const reqSide = Math.max(cW, cH + LABEL_BAND);
        const S = Math.max(canvasSize, reqSide);
        const fW = S;
        const fH = S;
        const mX = (fW - cW) / 2;
        const mY = (fH - (cH + LABEL_BAND)) / 2;
        return {
          fieldW: fW,
          fieldH: fH,
          marginX: mX,
          marginY: mY,
          gutter: 0,
          canvasWidth: S,
          canvasHeight: S,
          viewBoxX: 0,
          viewBoxY: 0,
          viewBoxWidth: S,
          viewBoxHeight: S,
          viewBox: `0 0 ${S} ${S}`,
          markers: [],
          colPitch: p,
          rowPitch: p,
        };
      }

      let g = 0;
      let p = pMin;
      let cW = colsVal * p;
      let cH = rowsVal * p;
      let S = canvasSize;
      let fW = S;
      let fH = S;
      let mX = 0;
      let mY = 0;
      let markersResult = null;

      for (let iter = 0; iter < 5; iter++) {
        const insetOrGutter = g > 0 ? g : 8;
        const avail = canvasSize - 2 * insetOrGutter;
        const pFit = Math.floor(Math.min(avail / colsVal, (avail - LABEL_BAND) / rowsVal));
        p = Math.max(pMin, Math.min(pFit, Math.floor(1.5 * props.colPitch)));
        cW = colsVal * p;
        cH = rowsVal * p;
        const reqSide = Math.max(cW + 2 * g, cH + LABEL_BAND + 2 * g);
        S = Math.max(canvasSize, reqSide);
        fW = S - 2 * g;
        fH = S - 2 * g;
        mX = (fW - cW) / 2;
        mY = (fH - (cH + LABEL_BAND)) / 2;

        const curX = current.col * p + p / 2 + mX;
        const curY = (rowsVal - 1 - current.row) * p + p / 2 + mY;

        markersResult = LocalMap.edgeMarkersFor(nodes.value, rememberedList.value, {
          canvasWidth: fW,
          canvasHeight: fH,
          current: { x: curX, y: curY },
          markerHalf,
          nameWidth,
          nameHeight,
        });

        const newG = markersResult.gutter;
        if (newG === g && iter > 0) {
          break;
        }
        g = newG;
      }

      const reqSide = Math.max(cW + 2 * g, cH + LABEL_BAND + 2 * g);
      S = Math.max(canvasSize, reqSide);
      fW = S - 2 * g;
      fH = S - 2 * g;
      mX = (fW - cW) / 2;
      mY = (fH - (cH + LABEL_BAND)) / 2;

      return {
        fieldW: fW,
        fieldH: fH,
        marginX: mX,
        marginY: mY,
        gutter: g,
        canvasWidth: S,
        canvasHeight: S,
        viewBoxX: 0,
        viewBoxY: 0,
        viewBoxWidth: S,
        viewBoxHeight: S,
        viewBox: `0 0 ${S} ${S}`,
        markers: markersResult ? markersResult.markers : [],
        colPitch: p,
        rowPitch: p,
      };
    }

    // canvasSize == null (overlay and bare mounts)
    const pCol = Math.max(props.colPitch, labelClearancePitch.value);
    const pRow = isSquarePitch.value
      ? Math.max(props.rowPitch, labelClearancePitch.value)
      : props.rowPitch;
    const cW = colsVal * pCol;
    const cH = rowsVal * pRow;

    if (!hasRemembered) {
      const fW = cW;
      const fH = cH + LABEL_BAND;
      return {
        fieldW: fW,
        fieldH: fH,
        marginX: 0,
        marginY: 0,
        gutter: 0,
        canvasWidth: fW,
        canvasHeight: fH,
        viewBoxX: 0,
        viewBoxY: 0,
        viewBoxWidth: fW,
        viewBoxHeight: fH,
        viewBox: `0 0 ${fW} ${fH}`,
        markers: [],
        colPitch: pCol,
        rowPitch: pRow,
      };
    }

    const markerHalf = MARKER_DIAMOND_HALF * props.markerScale;
    const nameWidth = outwardNameBox.value;
    const nameHeight = props.markerNames ? 16 : 0;
    let fW = cW;
    let fH = cH + LABEL_BAND;
    const curX = current.col * pCol + pCol / 2;
    const curY = (rowsVal - 1 - current.row) * pRow + pRow / 2;

    const markersResult = LocalMap.edgeMarkersFor(nodes.value, rememberedList.value, {
      canvasWidth: fW,
      canvasHeight: fH,
      current: { x: curX, y: curY },
      markerHalf,
      nameWidth,
      nameHeight,
    });

    const g = markersResult.gutter;
    const cWidth = fW + 2 * g;
    const cHeight = fH + 2 * g;

    return {
      fieldW: fW,
      fieldH: fH,
      marginX: 0,
      marginY: 0,
      gutter: g,
      canvasWidth: cWidth,
      canvasHeight: cHeight,
      viewBoxX: 0,
      viewBoxY: 0,
      viewBoxWidth: cWidth,
      viewBoxHeight: cHeight,
      viewBox: `0 0 ${cWidth} ${cHeight}`,
      markers: markersResult.markers,
      colPitch: pCol,
      rowPitch: pRow,
    };
  });

  const activeEdgeMarkers = computed(() => {
    if (props.edgeMarkers) return props.edgeMarkers;
    return {
      markers: layoutGeometry.value.markers,
      gutter: layoutGeometry.value.gutter,
      width: layoutGeometry.value.canvasWidth,
      height: layoutGeometry.value.canvasHeight,
    };
  });

  // The drawn placement follows the model: a graph payload whose nodes the
  // radial placement does not cover renders them not-at-all rather than at a
  // fabricated position (the shared omission contract of an absent edge
  // endpoint).
  const drawnNodes = computed(() =>
    radial.value
      ? nodes.value.filter((node) => radialById.value[node.id])
      : nodes.value,
  );

  const graphCanvasWidth = computed(() =>
    radial.value ? Math.max(1, radial.value.width * props.markerScale) : 1,
  );
  const graphCanvasHeight = computed(() =>
    radial.value ? Math.max(1, radial.value.height * props.markerScale) : 1,
  );
  // Lattice-driven canvas geometry (design D9 + the local-map delta + map-02
  // D2/D3b): the canvas sizes from the active placement. The lattice adds the
  // edge-marker gutter (0 without markers) to its natural size; the graph
  // sizes from the radial placement at the marker scale. `overflow: visible`
  // already lets the gutter content paint outside the node canvas.
  const canvasWidth = computed(() => layoutGeometry.value.canvasWidth);
  const canvasHeight = computed(() => layoutGeometry.value.canvasHeight);
  const viewBox = computed(() => layoutGeometry.value.viewBox);
  const viewBoxX = computed(() => layoutGeometry.value.viewBoxX);
  const viewBoxY = computed(() => layoutGeometry.value.viewBoxY);
  const effectiveColPitch = computed(() => layoutGeometry.value.colPitch);
  const effectiveRowPitch = computed(() => layoutGeometry.value.rowPitch);
  // The crowding fix decouples column pitch and row pitch: the row pitch
  // clears the marker height, the label line, and a strictly-positive gap
  // before the next row's marker; the column pitch clears two truncated
  // labels side by side.

  const dotCx = computed(() => {
    const { gutter, marginX } = layoutGeometry.value;
    const originOffsetX = gutter + marginX;
    const pitch = effectiveColPitch.value;
    return ((pitch / 2 + originOffsetX) % pitch + pitch) % pitch;
  });

  const dotCy = computed(() => {
    const { gutter, marginY } = layoutGeometry.value;
    const originOffsetY = gutter + marginY;
    const pitch = effectiveRowPitch.value;
    return ((pitch / 2 + originOffsetY) % pitch + pitch) % pitch;
  });

  function nodePos(node) {
    if (radial.value) {
      const placed = radialById.value[node.id];
      // A node the placement omits is not drawn (same omission contract as
      // an edge whose endpoint is absent).
      if (!placed) return null;
      return { x: placed.x * props.markerScale, y: placed.y * props.markerScale };
    }
    const core = latticePos(node);
    const { gutter, marginX, marginY } = layoutGeometry.value;
    return { x: core.x + gutter + marginX, y: core.y + gutter + marginY };
  }

  // The overlay pin's anchor (design D4): the CURRENT placement's current-node
  // position, in the same coordinate system as the node groups' translate.
  // Null (no pin) when the payload carries no on-canvas current node.
  const currentPos = computed(() => {
    const current = nodes.value.find((node) => node.visibility === "current");
    return current ? nodePos(current) : null;
  });

  // Edges are drawn between the centers of their endpoints; an edge whose
  // endpoint is not in the payload is omitted from the drawn layer.
  const edgeGeoms = computed(() =>
    edges.value
      .map((edge, i) => {
        const s = nodeById.value[edge.source];
        const d = nodeById.value[edge.destination];
        if (!s || !d) return null;
        const sp = nodePos(s);
        const dp = nodePos(d);
        if (!sp || !dp) return null;
        return {
          i,
          x1: sp.x,
          y1: sp.y,
          x2: dp.x,
          y2: dp.y,
        };
      })
      .filter(Boolean),
  );

  // Canvas cap: the caps come from the caller — the island passes its
  // dynamically measured height budget down, the overlay passes `null` for no
  // height cap and fills the body width — bound as inline styles so the
  // caller controls the layout variant.
  //
  // Every cap is resolved into ONE width bound, because under `fillWidth` the
  // element's width is definite (100% of the caller's content box) and a bare
  // `max-height` would then be an engine-dependent constraint: the replaced-
  // element constraint table is meant to shrink the width back to preserve the
  // intrinsic ratio, but the observable behaviour across engines ranges from
  // that, to a distorted box, to a `preserveAspectRatio` letterbox that leaves
  // the canvas's background/border painted around a thin drawing. The renderer
  // knows the exact canvas ratio, so it spends the height budget as its
  // equivalent width instead: the drawing then fills its box in every engine,
  // and the rendered height is exactly the budget. `max-height` is still bound
  // as the belt-and-braces cap it always was (it can no longer bind, since the
  // width bound is floored, never rounded up).
  function widthCaps() {
    const caps = [];
    if (props.maxWidth != null) caps.push(Number(props.maxWidth));
    if (props.maxHeight != null && canvasHeight.value > 0) {
      caps.push((Number(props.maxHeight) * canvasWidth.value) / canvasHeight.value);
    }
    return caps;
  }

  const latticeStyle = computed(() => {
    if (props.canvasSize != null) {
      return {
        width: props.canvasSize + "px",
        height: props.canvasSize + "px",
      };
    }
    const style = {};
    if (props.fillWidth) style.width = "100%";
    const caps = widthCaps();
    // Floored to 2 decimals: a bound rounded UP could re-cross the height
    // budget by a sub-pixel and hand the anchor a scrollbar.
    if (caps.length) style.maxWidth = Math.floor(Math.min(...caps) * 100) / 100 + "px";
    if (props.maxHeight != null) style.maxHeight = props.maxHeight + "px";
    return style;
  });

  return {
    legend,
    edges,
    drawnNodes,
    edgeGeoms,
    canvasWidth,
    canvasHeight,
    viewBox,
    viewBoxX,
    viewBoxY,
    effectiveColPitch,
    effectiveRowPitch,
    dotCx,
    dotCy,
    latticeStyle,
    currentPos,
    activeEdgeMarkers,
    outwardNameBox,
    isGraph,
    truncatedLabel,
    visibleNodeLabel,
    nodePos,
  };
}
