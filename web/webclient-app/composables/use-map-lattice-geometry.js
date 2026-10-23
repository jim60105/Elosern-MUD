// MapLattice geometry group (improve-webclient-map-overlay-scale): the
// lattice/graph placement math extracted verbatim from `MapLattice.vue` so
// the SFC stays a passive renderer. Owns the payload reads, the
// wilderness label-suppression rule with the crowding-fix pitch derivation it
// feeds, the model-sourced placement (rank-compressed lattice vs radial
// graph), the edge-marker gutter/canvas layout, and every drawing position
// the template consumes (canvas size, node/edge/axis positions, dot-pattern
// phase, cap-resolved inline style). Pure computeds over explicit props — no
// watchers, no emit.
import { computed } from "vue";
import LocalMap from "../lib/local_map.js";
import { CELL_EM, textCells } from "../lib/mono_cells.js";
import { CANVAS_SIZE, CENTRE, DOT_SPACING, projectIsland } from "../lib/minimap_projection.js";

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
export const LABEL_BASELINE_HALF = 11;
// The full map's current-location ring (webclient-map-legibility): a thin
// seal ring concentric with the current marker, inside that node's own group,
// so the one place the player stands carries one footprint. Its radius is the
// current node's reserved footprint on the overlay (it exceeds HALO_R).
export const MARKER_CURRENT_RING_R = 10.5;

const LABEL_BAND = 14;

// The island's remembered edge-direction diamonds (render-auto-scaled-minimap-
// island): the fixed square has no gutter outside its 240 units, and the
// projection's exit ring reaches R_MAX + HALO_R = 98 units from the centre, so
// the diamonds stand on the square's rim band, one diamond half-extent
// smaller than the overlay's, at the point where the true bearing leaves the
// square. Their names stay on the assistive mirror (LocalMap owns it).
export const ISLAND_MARKER_HALF = 7;
const ISLAND_MARKER_REACH = Math.SQRT2 * ISLAND_MARKER_HALF;
const ISLAND_MARKER_INSET = ISLAND_MARKER_REACH + 1.5;
const ISLAND_MARKER_GAP = 2 * ISLAND_MARKER_REACH + 1;
// The world-anchored dot field covers the square plus the farthest FLIP pan
// travel (an exit at R_MAX re-centring, plus two dot steps of phase), so the
// sliding ground never shows a bare edge mid-glide.
const ISLAND_DOT_MARGIN = 140;
// Ring labels sit on one diagonal (the axis cross owns the cardinals): the
// one farthest in bearing from every drawn exit.
const RING_LABEL_BEARINGS = [45, 315, 135, 225];
// Canvas inset every island label keeps from the square's edge.
const ISLAND_LABEL_INSET = 3;

// The label term for two horizontally adjacent drawn labels (see
// `labelClearancePitch`): half of each centred label box, measured in
// monospace cells, plus a half-em word gap.
export function labelPairPitch(labelA, labelB, labelFont) {
  return ((textCells(labelA) + textCells(labelB)) / 2 * CELL_EM + 0.5) * labelFont;
}

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
    const glyphs = Array.from(String(label ?? ""));
    return glyphs.length > props.labelMax ? glyphs.slice(0, props.labelMax).join("") + "…" : glyphs.join("");
  }

  // Node labels are bounded and truncated (the full label stays reachable
  // through the node's accessible name); a truncated label appends the
  // one-cell "…", so it spans at most 2 × labelMax + 1 monospace cells.
  function visibleNodeLabel(node) {
    if (labelSuppressed(node)) return "";
    return truncatedLabel(node.label);
  }

  // Effective pitch derivation (design D4, webclient-map-legibility): the
  // label term clears the labels actually drawn, not a worst case. Every
  // pair of drawn nodes on one lattice row that BOTH show label text needs
  // half of each centred label box plus a half-em word gap, so two names read
  // as two names rather than one run-on phrase:
  // `(cells(a) + cells(b)) / 2 * CELL_EM * labelFont + labelFont / 2`, the
  // visible (truncated) label measured in monospace cells (lib/mono_cells.js):
  // one cell for a code point the bundled monospace face draws narrow, two
  // for every other code point, whether the face draws it two cells wide or
  // it falls back to a roughly 1em face. Two maximal labels (`labelMax` wide
  // glyphs plus the narrow "…") need at least the old worst-case term
  // `(labelMax + 1) * labelFont + 3`, so the bound never loosens for them.
  //
  // Metric projection (project-metric-local-maps): lattice `col`/`row` are
  // cell units, and a cell is the smallest in-view coordinate delta, not one
  // payload unit. A same-row pair can therefore sit more than one cell apart,
  // so the term divides each pair's label need by its own cell separation:
  // the binding value is the pitch at which the closest drawn pair clears.
  const labelClearancePitch = computed(() => {
    const labeled = drawnNodes.value
      .map((node) => ({ node, label: visibleNodeLabel(node) }))
      .filter((entry) => entry.label.length > 0);
    let need = 0;
    for (let i = 0; i < labeled.length; i++) {
      for (let j = i + 1; j < labeled.length; j++) {
        const a = labeled[i];
        const b = labeled[j];
        const separation = Math.abs(a.node.col - b.node.col);
        if (a.node.row === b.node.row && separation > 0) {
          need = Math.max(
            need,
            labelPairPitch(a.label, b.label, props.labelFont) / separation,
          );
        }
      }
    }
    return Math.ceil(need);
  });
  // Rows increase northward. An upper label must clear the lower marker even
  // when that lower node suppresses its own label (shared wilderness names).
  // The baseline reserves 11 * markerScale + 2 + labelFont; allow a quarter
  // type step below it for the bundled face's descent and three units of gap.
  // As with the label term, a vertically aligned pair may be more than one
  // cell apart under the metric projection, so the need is divided by that
  // pair's own cell separation.
  const verticalClearancePitch = computed(() => {
    const need = 2 * LABEL_BASELINE_HALF * props.markerScale + 2 + 1.25 * props.labelFont + 3;
    let binding = 0;
    for (const upper of drawnNodes.value) {
      if (!visibleNodeLabel(upper)) continue;
      for (const lower of drawnNodes.value) {
        const separation = upper.row - lower.row;
        if (upper.col === lower.col && separation > 0) {
          binding = Math.max(binding, need / separation);
        }
      }
    }
    return Math.ceil(binding);
  });
  // Placement sourcing (map-02 D2): the lattice variant draws the model's
  // metric `col`/`row` grid (one uniform cell = the smallest in-view
  // coordinate delta, project-metric-local-maps); the graph variant draws the
  // model's radial placement (design D1) at `markerScale`, so the D1 geometry
  // contract's footprints and the drawn footprints stay proportional and the
  // non-overlap invariant is scale-invariant under the caps. The canvas size
  // follows the active placement; `overflow: visible` lets the lattice
  // marker gutter (map-02 D3b) render outside the node canvas without
  // clipping. A graph payload with no radial placement renders empty (the
  // variant prop is only ever passed a model that carries one).
  const isGraph = computed(() => props.variant === "graph");
  // The fixed-canvas lattice island consumes the automatic projection
  // (render-auto-scaled-minimap-island): LocalMap passes its hysteresis-held
  // projection; a bare mount projects statelessly (no previous level). The
  // graph island and the overlay (`canvasSize == null`) never project.
  const isIsland = computed(() => props.canvasSize != null && !isGraph.value);
  const projection = computed(() => {
    if (!isIsland.value) return null;
    return props.islandProjection ?? projectIsland(props.localMap, null);
  });
  const projectedById = computed(() => {
    const byId = new Map();
    for (const placed of projection.value ? projection.value.nodes : []) byId.set(String(placed.id), placed);
    return byId;
  });
  function nodeTier(node) {
    if (!isIsland.value || !node) return null;
    return projectedById.value.get(String(node.id))?.tier ?? null;
  }
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

  // The overlay's outward name box is declared in whole monospace cells, room
  // for `labelMax + 1` wide glyphs; the fit budget reads the cell count
  // directly, and the model receives its width in user units.
  const outwardNameCells = computed(() =>
    props.overlayChrome ? (props.labelMax + 1) * 2 : 0,
  );
  const outwardNameBox = computed(() => outwardNameCells.value * CELL_EM * props.markerNameFont);

  const layoutGeometry = computed(() => {
    if (isGraph.value) {
      const L = graphCanvasWidth.value;
      if (props.canvasSize != null) {
        const S = Number(props.canvasSize);
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

    if (isIsland.value) {
      // The fixed island (render-auto-scaled-minimap-island): one 240-unit
      // square in the projection's own user units, current at its centre. No
      // pitch fit, no gutter growth and no window: the projection already
      // fits every same-layer exit inside R_MAX, and the remembered
      // edge-direction markers stand on the square's own rim band.
      const S = CANVAS_SIZE;
      return {
        fieldW: S,
        fieldH: S,
        marginX: 0,
        marginY: 0,
        gutter: 0,
        canvasWidth: S,
        canvasHeight: S,
        viewBoxX: 0,
        viewBoxY: 0,
        viewBoxWidth: S,
        viewBoxHeight: S,
        viewBox: `0 0 ${S} ${S}`,
        markers: islandEdgeMarkers(current),
        colPitch: DOT_SPACING,
        rowPitch: DOT_SPACING,
      };
    }

    // canvasSize == null (overlay and bare mounts). One uniform physical scale
    // serves both axes (project-metric-local-maps): the drawn cell is square,
    // so an eastward and a northward delta of one coordinate cell draw the
    // same length and every compass bearing stays true. The declared pitches
    // are minimums; the larger one (and every derived clearance) binds both
    // axes.
    const pCol = Math.max(
      props.colPitch,
      props.rowPitch,
      labelClearancePitch.value,
      verticalClearancePitch.value,
    );
    const pRow = pCol;
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
    // As above: the marker name's line box, a fixed 16 units.
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
  //
  // The island draws only what its projection placed (current, every
  // same-layer exit, context that lands on the canvas), joined back to the
  // original node models so full names, visibility and actions stay the
  // payload's own; a cross-layer target and off-canvas context have no group.
  const drawnNodes = computed(() => {
    if (radial.value) return nodes.value.filter((node) => radialById.value[node.id]);
    if (isIsland.value) return nodes.value.filter((node) => projectedById.value.has(String(node.id)));
    return nodes.value;
  });

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

  function nodePos(nodeOrId) {
    const node =
      typeof nodeOrId === "object" && nodeOrId !== null
        ? nodeOrId
        : nodeById.value[nodeOrId] || nodes.value.find((n) => n.id === nodeOrId);
    if (!node) return null;
    if (radial.value) {
      const placed = radialById.value[node.id];
      // A node the placement omits is not drawn (same omission contract as
      // an edge whose endpoint is absent).
      if (!placed) return null;
      return { x: placed.x * props.markerScale, y: placed.y * props.markerScale };
    }
    if (isIsland.value) {
      const placed = projectedById.value.get(String(node.id));
      // Thousandths of a unit: exact at any drawn scale, and free of
      // trigonometric noise in the DOM.
      const round = (v) => Math.round(v * 1000) / 1000;
      return placed ? { x: round(placed.x), y: round(placed.y) } : null;
    }
    const core = latticePos(node);
    const { gutter, marginX, marginY } = layoutGeometry.value;
    return { x: core.x + gutter + marginX, y: core.y + gutter + marginY };
  }

  // The axis anchor: the CURRENT placement's current-node
  // position, in the same coordinate system as the node groups' translate.
  // Null (no axis) when the payload carries no on-canvas current node.
  const currentPos = computed(() => {
    const current = nodes.value.find((node) => node.visibility === "current");
    return current ? nodePos(current) : null;
  });

  // Edges are drawn between the centers of their endpoints; an edge whose
  // endpoint is not in the payload is omitted from the drawn layer.
  //
  // The island draws routes only: an edge with a non-empty label joining the
  // current node to a drawn exit (a locked exit included). The presenter's
  // empty-label star edges to two-hop context never draw, so no line suggests
  // a road that does not exist.
  function islandRoute(edge) {
    const source = nodeById.value[edge.source];
    const destination = nodeById.value[edge.destination];
    if (typeof edge.label !== "string" || edge.label.length === 0) return false;
    const tiers = [nodeTier(source), nodeTier(destination)];
    return tiers.includes("current") && tiers.includes("exit");
  }
  const edgeGeoms = computed(() =>
    edges.value
      .map((edge, i) => {
        const s = nodeById.value[edge.source];
        const d = nodeById.value[edge.destination];
        if (!s || !d) return null;
        if (isIsland.value && !islandRoute(edge)) return null;
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

  // ---- the island's scale-true background (design §5) ----

  // Uniform mode: dots `spacing` units apart on every integer world multiple of
  // the projection's dot step, so they belong to the ground and slide with it
  // under the pan. A bounded list (the square plus the pan margin), never one
  // dot per metre.
  const islandDots = computed(() => {
    const grid = projection.value?.grid;
    if (!grid || grid.kind !== "dots" || !(grid.spacing > 0)) return [];
    const step = grid.spacing;
    const from = -ISLAND_DOT_MARGIN;
    const to = CANVAS_SIZE + ISLAND_DOT_MARGIN;
    const first = (offset) => offset + Math.ceil((from - offset) / step) * step;
    const xs = [];
    const ys = [];
    for (let x = first(grid.offsetX); x <= to + 1e-9; x += step) xs.push(x);
    for (let y = first(grid.offsetY); y <= to + 1e-9; y += step) ys.push(y);
    const dots = [];
    for (const y of ys) for (const x of xs) dots.push({ x, y });
    return dots;
  });

  // Compressed mode: concentric distance rings at the projection's radii,
  // each labelled where no exit stands. The labels share the diagonal whose
  // bearing is farthest from every drawn exit (the axis cross owns the
  // cardinals); ties keep the first candidate, north-east.
  const islandRings = computed(() => {
    const grid = projection.value?.grid;
    if (!grid || grid.kind !== "rings") return [];
    const exits = (projection.value.nodes || []).filter((placed) => placed.tier === "exit");
    const exitBearings = exits.map(
      (placed) => ((Math.atan2(placed.x - CENTRE, CENTRE - placed.y) * 180) / Math.PI + 360) % 360,
    );
    const clearance = (bearing) =>
      exitBearings.reduce((least, other) => {
        const d = Math.abs(((bearing - other + 540) % 360) - 180);
        return Math.min(least, d);
      }, 360);
    let labelBearing = RING_LABEL_BEARINGS[0];
    for (const candidate of RING_LABEL_BEARINGS) {
      if (clearance(candidate) > clearance(labelBearing) + 1e-9) labelBearing = candidate;
    }
    const rad = (labelBearing * Math.PI) / 180;
    return grid.rings.map((ring) => ({
      ...ring,
      labelX: CENTRE + ring.radius * Math.sin(rad),
      labelY: CENTRE - ring.radius * Math.cos(rad),
    }));
  });

  const scaleLabel = computed(() => projection.value?.scaleLabel ?? "");
  const exitStubs = computed(() => projection.value?.exitStubs ?? []);

  // Remembered edge-direction markers on the island rim: the marker set and
  // its bearings come from the shared model (`edgeMarkersFor`, eligibility
  // and octants unchanged); each diamond stands where its true bearing leaves
  // the rim square, and neighbours on one side are pushed apart to a clear
  // gap. Each keeps its visible name inside the rim band: beside the diamond
  // on the top and bottom sides, as a glyph column below it on the left and
  // right sides; `span` is the free run up to the next marker or the square's
  // edge, which the shared fit-to-span and ambiguity rules then honour.
  function islandEdgeMarkers(current) {
    if (!current || rememberedList.value.length === 0) return [];
    const result = LocalMap.edgeMarkersFor(nodes.value, rememberedList.value, {
      canvasWidth: CANVAS_SIZE,
      canvasHeight: CANVAS_SIZE,
      current: { x: CENTRE, y: CENTRE },
      markerHalf: ISLAND_MARKER_HALF,
      nameWidth: 0,
      nameHeight: 0,
    });
    const half = CENTRE - ISLAND_MARKER_INSET;
    const lo = ISLAND_MARKER_INSET;
    const hi = CANVAS_SIZE - ISLAND_MARKER_INSET;
    const placed = result.markers.map((marker) => {
      const sx = marker.dx;
      const sy = -marker.dy;
      const t = half / Math.max(Math.abs(sx), Math.abs(sy));
      return { ...marker, x: CENTRE + sx * t, y: CENTRE + sy * t, span: 0, half: ISLAND_MARKER_HALF, rim: true };
    });
    for (const side of ["top", "bottom", "left", "right"]) {
      const horizontal = side === "top" || side === "bottom";
      const axis = horizontal ? "x" : "y";
      const group = placed.filter((marker) => marker.side === side).sort((a, b) => a[axis] - b[axis]);
      if (group.length > 1 && (group.length - 1) * ISLAND_MARKER_GAP > hi - lo) {
        // More markers than the side holds at the clear gap (the 64-node
        // bound allows it): spread them evenly along the whole side, in
        // bearing order, rather than piling them on its end.
        group.forEach((marker, i) => {
          marker[axis] = lo + ((hi - lo) * i) / (group.length - 1);
        });
        continue;
      }
      for (let i = 1; i < group.length; i += 1) {
        group[i][axis] = Math.max(group[i][axis], group[i - 1][axis] + ISLAND_MARKER_GAP);
      }
      if (group.length > 0 && group[group.length - 1][axis] > hi) {
        group[group.length - 1][axis] = hi;
        for (let i = group.length - 2; i >= 0; i -= 1) {
          group[i][axis] = Math.min(group[i][axis], group[i + 1][axis] - ISLAND_MARKER_GAP);
        }
      }
      for (const marker of group) marker[axis] = Math.min(Math.max(marker[axis], lo), hi);
    }
    const sides = new Set(placed.map((marker) => marker.side));
    for (const side of ["top", "bottom", "left", "right"]) {
      const horizontal = side === "top" || side === "bottom";
      const axis = horizontal ? "x" : "y";
      // A name runs toward +x (beside) or +y (below); the far corner is held
      // back by a marker's own inset when the adjacent side carries markers.
      const corner = horizontal ? "right" : side === "left" || side === "right" ? "bottom" : null;
      const end = CANVAS_SIZE - ISLAND_LABEL_INSET - (sides.has(corner) ? 2 * ISLAND_MARKER_INSET : 0);
      const group = placed.filter((marker) => marker.side === side).sort((a, b) => a[axis] - b[axis]);
      group.forEach((marker, i) => {
        const start = marker[axis] + ISLAND_MARKER_REACH + (horizontal ? 3 : 2);
        const limit = i + 1 < group.length ? group[i + 1][axis] - ISLAND_MARKER_REACH - 2 : end;
        marker.span = Math.max(0, limit - start);
      });
    }
    return placed;
  }

  // Island label offset (x, y) relative to its node: the shared below-marker
  // baseline, kept inside the square — shifted along x when the centred label
  // would leave a side, lifted above the marker when the baseline would leave
  // the bottom. One small, replaceable rule; collision placement belongs to
  // the label change (label-minimap-exits-and-gateways).
  function islandLabelOffset(node, text, baseline) {
    const pos = nodePos(node);
    if (!isIsland.value || !pos) return { dx: 0, y: baseline };
    const width = textCells(text) * CELL_EM * props.labelFont;
    const left = pos.x - width / 2;
    const clampedLeft = Math.min(
      Math.max(left, ISLAND_LABEL_INSET),
      Math.max(ISLAND_LABEL_INSET, CANVAS_SIZE - ISLAND_LABEL_INSET - width),
    );
    const descent = 0.25 * props.labelFont;
    const y =
      pos.y + baseline + descent > CANVAS_SIZE - ISLAND_LABEL_INSET
        ? -(LABEL_BASELINE_HALF * props.markerScale + 2 + descent)
        : baseline;
    return { dx: clampedLeft - left, y };
  }

  // Canvas box: the island passes its fixed reference square (`canvasSize`,
  // CSS px at the 1451x790 reference), the overlay passes `null` and fills its
  // body — bound as inline styles so the caller controls the layout variant.
  // The square's outward box is multiplied once by the desktop chrome factor
  // (webclient-proportional-ui-scale); the viewBox and every user-unit
  // coordinate stay as computed, so the drawing only magnifies uniformly.
  const latticeStyle = computed(() => {
    if (props.canvasSize != null) {
      const side = `calc(${Number(props.canvasSize)}px * var(--ui-scale, 1))`;
      return {
        width: side,
        height: side,
      };
    }
    if (props.fitView) {
      return {
        width: "100%",
        height: "100%",
      };
    }
    return {};
  });

  return {
    isIsland,
    projection,
    nodeTier,
    islandDots,
    islandRings,
    scaleLabel,
    exitStubs,
    islandLabelOffset,
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
    outwardNameCells,
    outwardNameBox,
    isGraph,
    truncatedLabel,
    visibleNodeLabel,
    nodePos,
  };
}
