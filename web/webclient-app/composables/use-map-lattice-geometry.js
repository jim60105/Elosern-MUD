// MapLattice geometry group (improve-webclient-map-overlay-scale): the
// minimap island's placement math extracted from `MapLattice.vue` so the SFC
// stays a passive renderer. Owns the payload reads, the wilderness
// label-suppression rule, the model-sourced placement (the automatic island
// projection, or the radial graph on coordinate-free layers), the island's
// rim edge markers, labels and stubs, and every drawing position the
// template consumes. Pure computeds over explicit props — no watchers, no
// emit. The full-map overlay's lattice (cell divisor, pitch fit, gutter and
// fitted view) was removed with the overlay (redesign-map-drawer).
import { computed } from "vue";
import LocalMap from "../lib/local_map.js";
import { CELL_EM, charCells, textCells } from "../lib/mono_cells.js";
import { CANVAS_SIZE, CENTRE, R_MAX, projectIsland } from "../lib/minimap_projection.js";
import { ASCENT, DESCENT, placeIslandLabels } from "../lib/island_labels.js";
import { HALO_R, ISLAND_GLYPH_SCALE, paintedMarkerFootprint } from "../lib/map_marker_geometry.js";

export const MARKER_DIAMOND_HALF = 9;
// The graph variant's label baseline half-extent: the largest base footprint
// (the travel halo plus its 1-unit stroke), multiplied by the glyph scale.
export const LABEL_BASELINE_HALF = HALO_R + 1;
// The compass aim ring's radius (exploration-exit-compass D6): a thin ring
// concentric with the aimed node's marker, just outside the travel halo at
// the island glyph scale (its 1.6 px non-scaling stroke's inner edge clears
// the halo's outer edge, (HALO_R + 0.6) × the scale).
export const MARKER_CURRENT_RING_R = HALO_R * ISLAND_GLYPH_SCALE + 2;

// The island's remembered edge-direction diamonds (render-auto-scaled-minimap-
// island): the fixed square has no gutter outside its 240 units, and the
// projection's exit ring reaches R_MAX + HALO_R × s units from the centre (s
// the island glyph scale), so
// the diamonds stand on the square's rim band, one diamond half-extent
// smaller than the overlay's, at the point where the true bearing leaves the
// square. Their names are laid out whole on the rim (layoutRimNames) before
// any node label is placed.
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
// A gateway exit stub: an arrowhead on the exit ring (R_MAX) pointing along
// the cross-layer target's bearing, with this reserved radius.
export const STUB_RADIUS = R_MAX;
export const STUB_FOOTPRINT = 9;
const CONTEXT_FOOTPRINT = 3;

export function useMapLatticeGeometry(props) {
  const nodes = computed(() => (Array.isArray(props.localMap.nodes) ? props.localMap.nodes : []));
  const edges = computed(() => (Array.isArray(props.localMap.edges) ? props.localMap.edges : []));

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

  // Placement sourcing (map-02 D2): the lattice variant draws the island's
  // automatic projection of the payload's metric coordinates; the graph
  // variant draws the model's radial placement (design D1) at `markerScale`,
  // so the D1 geometry contract's footprints and the drawn footprints stay
  // proportional. A graph payload with no radial placement renders empty
  // (the variant prop is only ever passed a model that carries one).
  const isGraph = computed(() => props.variant === "graph");
  // The fixed-canvas lattice island consumes the automatic projection
  // (render-auto-scaled-minimap-island): LocalMap passes its hysteresis-held
  // projection; a bare mount projects statelessly (no previous level). The
  // graph island never projects.
  const isIsland = computed(() => !isGraph.value);
  // The node glyph's uniform scale: the island glyph scale on the lattice
  // (whose projected positions ignore markerScale), times markerScale on the
  // graph variant (whose radial positions scale by it).
  const glyphSize = computed(() => (isGraph.value ? ISLAND_GLYPH_SCALE * props.markerScale : ISLAND_GLYPH_SCALE));
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

  // Edge direction markers (map-02 D3b): the lattice island asks the model
  // for its remembered markers against its own square (islandEdgeMarkers).
  // The graph variant never marks: a radial drawing has no canvas edge a
  // bearing could point at.
  const rememberedList = computed(() =>
    Array.isArray(props.localMap.remembered) ? props.localMap.remembered : [],
  );
  // The island's drawing box (render-auto-scaled-minimap-island): the
  // lattice island is one fixed CANVAS_SIZE square in the projection's own
  // user units; the graph island windows its radial placement through the
  // same square, centred on the placement. The full-map overlay's pitch-fit,
  // gutter and fitted-view geometry were removed with the overlay
  // (redesign-map-drawer).
  const layoutGeometry = computed(() => {
    const S = Number(props.canvasSize);
    if (isGraph.value) {
      const vx = graphCanvasWidth.value / 2 - S / 2;
      const vy = graphCanvasWidth.value / 2 - S / 2;
      return { canvasWidth: S, canvasHeight: S, viewBox: `${vx} ${vy} ${S} ${S}`, markers: [] };
    }
    const current = nodes.value.find((node) => node.visibility === "current");
    return { canvasWidth: S, canvasHeight: S, viewBox: `0 0 ${S} ${S}`, markers: islandEdgeMarkers(current) };
  });

  const activeEdgeMarkers = computed(() => ({
    markers: layoutGeometry.value.markers,
    gutter: 0,
    width: layoutGeometry.value.canvasWidth,
    height: layoutGeometry.value.canvasHeight,
  }));

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
    return nodes.value.filter((node) => projectedById.value.has(String(node.id)));
  });

  const graphCanvasWidth = computed(() =>
    radial.value ? Math.max(1, radial.value.width * props.markerScale) : 1,
  );
  const canvasWidth = computed(() => layoutGeometry.value.canvasWidth);
  const canvasHeight = computed(() => layoutGeometry.value.canvasHeight);
  const viewBox = computed(() => layoutGeometry.value.viewBox);

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
    const placed = projectedById.value.get(String(node.id));
    // Thousandths of a unit: exact at any drawn scale, and free of
    // trigonometric noise in the DOM.
    const round = (v) => Math.round(v * 1000) / 1000;
    return placed ? { x: round(placed.x), y: round(placed.y) } : null;
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
  // The background states a distance mapping, so it exists only on the
  // coordinate-bearing layers (grid metres, wilderness kilometre cells); a
  // forced lattice mount of a coordinate-free payload keeps a bare canvas.
  const metricLayer = computed(() => props.localMap.layer === "grid" || props.localMap.layer === "wilderness");
  const islandDots = computed(() => {
    if (!metricLayer.value) return [];
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
    if (!metricLayer.value) return [];
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
      labelBearing,
      labelX: CENTRE + ring.radius * Math.sin(rad),
      labelY: CENTRE - ring.radius * Math.cos(rad),
    }));
  });

  const scaleLabel = computed(() => projection.value?.scaleLabel ?? "");
  const exitStubs = computed(() => projection.value?.exitStubs ?? []);

  // ---- gateways and navigation-priority labels (label-minimap-exits-and-gateways) ----

  // The leads_to text a node's gateway metadata names, or "".
  function leadsToOf(node) {
    const leads = node?.gateway?.leads_to;
    return typeof leads === "string" ? leads : "";
  }
  // A same-layer gateway node on the island draws the gate arch.
  function isGateway(node) {
    return isIsland.value && nodeTier(node) !== "context" && leadsToOf(node) !== "";
  }

  // The radius a drawn island marker reserves: the gate arch, the actionable
  // halo, the current seal circle (with its stroke), else the small dot and
  // its landmark ring.
  function nodeFootprint(node) {
    if (nodeTier(node) === "context") return CONTEXT_FOOTPRINT;
    return paintedMarkerFootprint(node, glyphSize.value);
  }

  // The projection's cross-layer exit stubs, each at its target bearing on
  // the exit ring, with the far side it leads to and the target's own
  // (nullable) action, untouched.
  const islandStubs = computed(() =>
    (projection.value?.exitStubs ?? []).map((stub, index) => {
      const rad = (stub.bearing * Math.PI) / 180;
      const leadsTo = String(stub.label ?? "").replace(/^通往 /, "");
      return {
        index,
        key: `${index}:${Math.round(stub.bearing * 1000)}:${stub.label}`,
        bearing: stub.bearing,
        label: stub.label,
        leadsTo,
        action: stub.action ?? null,
        actionable: !!stub.action && stub.action.kind === "move",
        x: Math.round((CENTRE + STUB_RADIUS * Math.sin(rad)) * 1000) / 1000,
        y: Math.round((CENTRE - STUB_RADIUS * Math.cos(rad)) * 1000) / 1000,
      };
    }),
  );

  // A distance-ring figure's box (centred text, dy 0.35em).
  function ringLabelBox(ring) {
    const font = props.labelFont;
    const width = textCells(ring.label) * CELL_EM * font;
    const baseline = ring.labelY + 0.35 * font;
    return {
      x0: ring.labelX - width / 2,
      x1: ring.labelX + width / 2,
      y0: baseline - ASCENT * font,
      y1: baseline + DESCENT * font,
    };
  }

  function truncateTo(text) {
    const glyphs = Array.from(String(text ?? ""));
    return glyphs.length > props.labelMax ? glyphs.slice(0, props.labelMax).join("") + "…" : glyphs.join("");
  }

  // Every island label block, placed in navigation priority around the
  // reserved marker footprints, the stub arrows, the ring figures and the
  // remembered rim names (lib/island_labels.js). Keyed by node id, or
  // `stub:<index>` for an exit stub.
  const islandLabelLayout = computed(() => {
    if (!isIsland.value) return { placements: new Map(), obstacles: [] };
    const requests = [];
    const obstacles = [];
    for (const node of drawnNodes.value) {
      const pos = nodePos(node);
      if (!pos) continue;
      const tier = nodeTier(node);
      const footprint = nodeFootprint(node);
      obstacles.push({ x: pos.x, y: pos.y, r: footprint, owner: String(node.id) });
      const name = visibleNodeLabel(node);
      const lines = [{ text: name, kind: "name" }];
      const fallbackLines = [{ text: name, kind: "name" }];
      const leads = isGateway(node) ? leadsToOf(node) : "";
      if (leads) {
        lines.push({ text: `通往 ${leads}`, kind: "via" });
        fallbackLines.push({ text: `通往 ${truncateTo(leads)}`, kind: "via" });
      }
      const dx = pos.x - CENTRE;
      const dy = pos.y - CENTRE;
      requests.push({
        id: String(node.id),
        tier,
        x: pos.x,
        y: pos.y,
        footprint,
        lines,
        fallbackLines,
        outward: Math.hypot(dx, dy) > 1e-6 ? ((Math.atan2(dx, -dy) * 180) / Math.PI + 360) % 360 : null,
      });
    }
    const current = requests.find((request) => request.tier === "current");
    if (current) {
      current.avoid = [
        ...requests.filter((request) => request.tier === "exit" && request.outward !== null).map((request) => request.outward),
        ...islandStubs.value.map((stub) => stub.bearing),
      ];
    }
    for (const stub of islandStubs.value) {
      const id = `stub:${stub.index}`;
      obstacles.push({ x: stub.x, y: stub.y, r: STUB_FOOTPRINT, owner: id });
      requests.push({
        id,
        tier: "exit",
        rank: 0,
        x: stub.x,
        y: stub.y,
        footprint: STUB_FOOTPRINT,
        lines: [{ text: stub.label, kind: "via" }],
        fallbackLines: [{ text: `通往 ${truncateTo(stub.leadsTo)}`, kind: "via" }],
        outward: stub.bearing,
      });
    }
    for (const marker of layoutGeometry.value.markers || []) {
      if (!marker.rim) continue;
      const reach = Math.SQRT2 * (marker.half ?? ISLAND_MARKER_HALF);
      obstacles.push({ x0: marker.x - reach, x1: marker.x + reach, y0: marker.y - reach, y1: marker.y + reach });
      for (const box of marker.rimName?.boxes ?? []) obstacles.push(box);
    }
    const placements = placeIslandLabels({
      requests,
      obstacles,
      size: CANVAS_SIZE,
      font: props.labelFont,
      inset: ISLAND_LABEL_INSET,
    });
    return { placements, obstacles };
  });
  const islandLabels = computed(() => islandLabelLayout.value.placements);

  // The distance-ring figures are the scale's key, below navigation in
  // priority: each keeps its ring and moves along it to the first bearing —
  // its preferred diagonal, the other diagonals, then the eight bearings
  // between them — whose figure clears every marker, stub, rim name, placed
  // label and earlier figure; with none, it keeps its preferred spot.
  const RING_LABEL_FALLBACK_BEARINGS = [22.5, 67.5, 112.5, 157.5, 202.5, 247.5, 292.5, 337.5];
  const islandRingLabels = computed(() => {
    const rings = islandRings.value;
    if (rings.length === 0) return rings;
    const { placements, obstacles } = islandLabelLayout.value;
    const taken = [...obstacles, ...[...placements.values()].map((placed) => placed.box)];
    const hits = (box) =>
      taken.some((o) => {
        if (o.r !== undefined) {
          const nx = Math.min(Math.max(o.x, box.x0), box.x1);
          const ny = Math.min(Math.max(o.y, box.y0), box.y1);
          return Math.hypot(o.x - nx, o.y - ny) < o.r + 2;
        }
        return !(box.x1 + 2 <= o.x0 || o.x1 + 2 <= box.x0 || box.y1 + 2 <= o.y0 || o.y1 + 2 <= box.y0);
      });
    const inSquare = (box) => box.x0 >= ISLAND_LABEL_INSET && box.y0 >= ISLAND_LABEL_INSET && box.x1 <= CANVAS_SIZE - ISLAND_LABEL_INSET && box.y1 <= CANVAS_SIZE - ISLAND_LABEL_INSET;
    return rings.map((ring) => {
      const preferred = ring.labelBearing;
      const bearings = [preferred, ...RING_LABEL_BEARINGS.filter((b) => b !== preferred), ...RING_LABEL_FALLBACK_BEARINGS];
      for (const bearing of bearings) {
        const rad = (bearing * Math.PI) / 180;
        const candidate = { ...ring, labelX: CENTRE + ring.radius * Math.sin(rad), labelY: CENTRE - ring.radius * Math.cos(rad) };
        const box = ringLabelBox(candidate);
        if (inSquare(box) && !hits(box)) {
          taken.push(box);
          return candidate;
        }
      }
      taken.push(ringLabelBox(ring));
      return ring;
    });
  });

  // Remembered edge-direction markers on the island rim: the marker set and
  // its bearings come from the shared model (`edgeMarkersFor`, eligibility
  // and octants unchanged); each diamond stands where its true bearing leaves
  // the rim square, and neighbours on one side are pushed apart to a clear
  // gap. Every name is drawn whole (never shortened) inside the square; see
  // layoutRimNames.
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
      // An unbounded span: the island never shortens a remembered name; the
      // rim layout below wraps it instead.
      return { ...marker, x: CENTRE + sx * t, y: CENTRE + sy * t, span: Infinity, half: ISLAND_MARKER_HALF, rim: true };
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
    // Corners: a top/bottom marker and a left/right marker can both crowd
    // one corner (bearings either side of a diagonal); the top/bottom one
    // steps back along its side until the diamonds clear.
    for (const across of placed.filter((m) => m.side === "top" || m.side === "bottom")) {
      for (const along of placed.filter((m) => m.side === "left" || m.side === "right")) {
        const dx = across.x - along.x;
        const dy = across.y - along.y;
        if (Math.abs(dx) + Math.abs(dy) >= ISLAND_MARKER_GAP) continue;
        const away = across.x < CENTRE ? 1 : -1;
        across.x = along.x + away * (ISLAND_MARKER_GAP - Math.abs(dy));
      }
    }
    layoutRimNames(placed);
    return placed;
  }

  // Whole-name layout for the island's rim markers. A name never shortens: it
  // reads along its own edge — horizontal on the top and bottom sides, a
  // glyph column on the left and right sides — first in the rim band beside
  // its diamond (after it, else before it), then across it (head before,
  // tail after, reading through the diamond), else on the next free row (or
  // column) inward, centred on the diamond and wrapped onto further rows when
  // longer than the side. Every line stays inside the square and clear of
  // every diamond and every other name, on any side; a search that finds no
  // free row keeps the nearest row (the 64-node bound's pathological case). The result is `marker.rimName.lines`, each
  // `{ text, x, y }` relative to the marker (start-anchored lines, or one
  // centred glyph per entry on a column).
  function layoutRimNames(placed) {
    const font = props.markerNameFont;
    const step = font + 7;
    const inset = ISLAND_LABEL_INSET;
    const sides = new Set(placed.map((marker) => marker.side));
    const glyphLength = (horizontal, ch) => (horizontal ? charCells(ch) * CELL_EM * font : font);
    // Every claimed box on the square (diamonds first, then names on every
    // side), so no name crosses a diamond or another side's name either.
    const taken = placed.map((marker) => ({
      x0: marker.x - ISLAND_MARKER_REACH - 1,
      x1: marker.x + ISLAND_MARKER_REACH + 1,
      y0: marker.y - ISLAND_MARKER_REACH - 1,
      y1: marker.y + ISLAND_MARKER_REACH + 1,
    }));
    // The drawn current and exit nodes' reserved footprints (a gate arch
    // included) and the gateway exit-stub arrows:
    // the rim names are laid out first (they are always whole), and the node
    // labels are then placed around them (lib/island_labels.js).
    for (const node of drawnNodes.value) {
      if (nodeTier(node) === "context") continue;
      const pos = nodePos(node);
      if (!pos) continue;
      const r = Math.max(HALO_R * glyphSize.value, nodeFootprint(node));
      taken.push({ x0: pos.x - r, x1: pos.x + r, y0: pos.y - r, y1: pos.y + r });
    }
    for (const stub of islandStubs.value) {
      taken.push({ x0: stub.x - STUB_FOOTPRINT, x1: stub.x + STUB_FOOTPRINT, y0: stub.y - STUB_FOOTPRINT, y1: stub.y + STUB_FOOTPRINT });
    }
    // A 3-unit clearance on both axes covers the face's real glyph boxes
    // (ascent and side bearings beyond the monospace cell estimate).
    const clear = (box) =>
      taken.every(
        (o) =>
          box.x1 + 3 <= o.x0 ||
          box.x0 >= o.x1 + 3 ||
          box.y1 + 3 <= o.y0 ||
          box.y0 >= o.y1 + 3,
      );
    for (const side of ["top", "bottom", "left", "right"]) {
      const horizontal = side === "top" || side === "bottom";
      const axis = horizontal ? "x" : "y";
      const lo = inset;
      const hi = CANVAS_SIZE - inset;
      const group = placed.filter((marker) => marker.side === side).sort((a, b) => a[axis] - b[axis]);
      const rows = [];
      const boxOf = (row, from, to) => {
        const cross = crossOf(row);
        return horizontal
          ? { x0: from, x1: to, y0: cross - 0.8 * font, y1: cross + 0.2 * font }
          : { x0: cross - font / 2, x1: cross + font / 2, y0: from, y1: to };
      };
      const inside = (box) => box.x0 >= -1e-9 && box.y0 >= -1e-9 && box.x1 <= CANVAS_SIZE + 1e-9 && box.y1 <= CANVAS_SIZE + 1e-9;
      const free = (row, from, to) =>
        from >= lo - 1e-9 && to <= hi + 1e-9 && inside(boxOf(row, from, to)) && clear(boxOf(row, from, to));
      const claim = (row, from, to) => {
        rows[row] = rows[row] || [];
        rows[row].push([from, to]);
        taken.push(boxOf(row, from, to));
      };
      // Row r's cross-axis position: the band at r = 0, one step inward each.
      const crossOf = (row) => {
        if (side === "top") return inset + 0.8 * font + row * step;
        if (side === "bottom") return CANVAS_SIZE - inset - 0.2 * font - row * step;
        if (side === "left") return inset + font / 2 + row * step;
        return CANVAS_SIZE - inset - font / 2 - row * step;
      };
      for (const marker of group) {
        const glyphs = Array.from(marker.name || "");
        if (glyphs.length === 0) {
          marker.rimName = { lines: [] };
          continue;
        }
        const lengthOf = (chunk) => chunk.reduce((sum, ch) => sum + glyphLength(horizontal, ch), 0);
        const p = marker[axis];
        const total = lengthOf(glyphs);
        const placedChunks = [];
        const beside = [
          [p + ISLAND_MARKER_REACH + 5, p + ISLAND_MARKER_REACH + 5 + total],
          [p - ISLAND_MARKER_REACH - 5 - total, p - ISLAND_MARKER_REACH - 5],
        ].find(([from, to]) => free(0, from, to));
        // Through the diamond: the name reads across it along the band, its
        // head before the diamond and its tail after it (the most balanced
        // split whose two halves are both free).
        let through = null;
        if (!beside) {
          const before = p - ISLAND_MARKER_REACH - 5;
          const after = p + ISLAND_MARKER_REACH + 5;
          for (let k = 1; k < glyphs.length; k += 1) {
            const head = lengthOf(glyphs.slice(0, k));
            const tail = lengthOf(glyphs.slice(k));
            if (!free(0, before - head, before) || !free(0, after, after + tail)) continue;
            if (!through || Math.abs(head - tail) < through.balance) {
              through = { k, head, tail, balance: Math.abs(head - tail) };
            }
          }
          if (through) {
            claim(0, before - through.head, before);
            claim(0, after, after + through.tail);
            placedChunks.push(
              { glyphs: glyphs.slice(0, through.k), from: before - through.head, row: 0 },
              { glyphs: glyphs.slice(through.k), from: after, row: 0 },
            );
          }
        }
        if (beside) {
          claim(0, beside[0], beside[1]);
          placedChunks.push({ glyphs, from: beside[0], row: 0 });
        } else if (!through) {
          // Wrap into chunks no longer than `limit` (one glyph at least) and
          // give each chunk, in reading order, the free spot nearest its
          // diamond on the first free inward row. When a chunk finds no free
          // spot, the claims are undone and the name wraps shorter; only a
          // single-glyph wrap that still finds none keeps the nearest row.
          const wrap = (limit) => {
            const chunks = [];
            let current = [];
            for (const ch of glyphs) {
              if (current.length > 0 && lengthOf([...current, ch]) > limit) {
                chunks.push(current);
                current = [];
              }
              current.push(ch);
            }
            chunks.push(current);
            return side === "bottom" ? chunks.reverse() : chunks;
          };
          // One name's chunks stay together: the first takes the free spot
          // nearest its diamond within the first inward rows (four, then
          // nine before the drawn places' names are given up), every
          // further chunk the next free row with nearly the same start, so a
          // wrapped name reads as one block.
          const attempt = (limit, forced, depth = 4) => {
            const mark = taken.length;
            const result = [];
            let row = 0;
            let anchor = null;
            for (const chunk of wrap(limit)) {
              const length = lengthOf(chunk);
              const centred = Math.min(Math.max(p - length / 2, lo), Math.max(lo, hi - length));
              const start = anchor === null ? centred : Math.min(Math.max(anchor, lo), Math.max(lo, hi - length));
              const reach = anchor === null ? CANVAS_SIZE : 3 * font;
              const window = anchor === null ? depth : 2;
              let spot = null;
              for (let r = row; r < row + window && !spot; r += 1) {
                const candidates = [start];
                for (let d = 4; d <= reach; d += 4) candidates.push(start - d, start + d);
                const from = candidates.find((at) => free(r, at, at + length));
                if (from !== undefined) spot = { from, row: r };
              }
              if (!spot) {
                if (!forced) {
                  taken.length = mark;
                  return null;
                }
                spot = { from: start, row };
              }
              claim(spot.row, spot.from, spot.from + length);
              result.push({ glyphs: chunk, from: spot.from, row: spot.row });
              row = spot.row + 1;
              anchor = spot.from;
            }
            return side === "bottom" ? result.reverse() : result;
          };
          // Through the diamond with an overflow line: the band carries as
          // much of the name as reads across the diamond, and the rest takes
          // one free row just inward, aligned with the band text — after the
          // band text on the top and side edges, before it on the bottom
          // edge (whose inward rows stand above the band).
          const throughWrap = () => {
            const before = p - ISLAND_MARKER_REACH - 5;
            const after = p + ISLAND_MARKER_REACH + 5;
            const rowFirst = side === "bottom";
            const n = glyphs.length;
            const qualifier = glyphs.lastIndexOf("（");
            let best = null;
            for (let cut = 1; cut < n; cut += 1) {
              // The overflow is the first `cut` glyphs (bottom) or the last.
              const overflow = rowFirst ? glyphs.slice(0, cut) : glyphs.slice(n - cut);
              const band = rowFirst ? glyphs.slice(cut) : glyphs.slice(0, n - cut);
              const boundary = rowFirst ? cut : n - cut;
              for (let k = 1; k < band.length; k += 1) {
                const head = band.slice(0, k);
                const tail = band.slice(k);
                const headFrom = before - lengthOf(head);
                if (!free(0, headFrom, before) || !free(0, after, after + lengthOf(tail))) continue;
                const mark = taken.length;
                claim(0, headFrom, before);
                claim(0, after, after + lengthOf(tail));
                const length = lengthOf(overflow);
                const align = rowFirst ? headFrom : after;
                const candidates = [align];
                for (let d = 4; d <= 3 * font; d += 4) candidates.push(align - d, align + d);
                let extra = null;
                for (const r of [1, 2]) {
                  const from = candidates.find((at) => free(r, at, at + length));
                  if (from !== undefined) {
                    extra = { glyphs: overflow, from, row: r };
                    break;
                  }
                }
                taken.length = mark;
                if (!extra) continue;
                // Readable splits first: a parenthesised qualifier kept whole
                // on its own line, no lone glyph on a line or beside the
                // diamond, then the most even line lengths.
                const score =
                  (boundary === qualifier ? -40 : 0) +
                  (qualifier >= 0 && rowFirst && cut + k > qualifier ? 60 : 0) +
                  (qualifier >= 0 && !rowFirst && k > qualifier ? 60 : 0) +
                  (overflow.length < 2 ? 100 : 0) +
                  (head.length < 2 || tail.length < 2 ? 30 : 0) +
                  Math.abs(lengthOf(head) - lengthOf(tail)) / font +
                  Math.abs(lengthOf(overflow) - lengthOf(band)) / (2 * font);
                if (!best || score < best.score) {
                  best = { score, head, tail, headFrom, extra };
                }
              }
            }
            if (!best) return null;
            claim(0, best.headFrom, before);
            claim(0, after, after + lengthOf(best.tail));
            claim(best.extra.row, best.extra.from, best.extra.from + lengthOf(best.extra.glyphs));
            const bandChunks = [
              { glyphs: best.head, from: best.headFrom, row: 0 },
              { glyphs: best.tail, from: after, row: 0 },
            ];
            return rowFirst ? [best.extra, ...bandChunks] : [...bandChunks, best.extra];
          };
          const room = hi - lo;
          let result = throughWrap();
          // The nearest four inward rows first, then nine.
          for (const depth of [4, 9]) {
            for (let parts = 1; !result && parts <= Math.min(glyphs.length, 6); parts += 1) {
              result = attempt(Math.max(room / parts, 1), false, depth);
            }
            if (result) break;
          }
          placedChunks.push(...(result ?? attempt(1, true)));
        }
        const lines = [];
        for (const chunk of placedChunks) {
          const cross = crossOf(chunk.row);
          if (horizontal) {
            lines.push({ text: chunk.glyphs.join(""), x: chunk.from - marker.x, y: cross - marker.y });
          } else {
            chunk.glyphs.forEach((ch, i) => {
              lines.push({ text: ch, x: cross - marker.x, y: chunk.from + i * font + 0.8 * font - marker.y });
            });
          }
        }
        marker.rimName = { horizontal, lines, boxes: placedChunks.map((chunk) => boxOf(chunk.row, chunk.from, chunk.from + lengthOf(chunk.glyphs))) };
      }
    }
  }

  // Canvas box: the island's fixed reference square (`canvasSize`, CSS px at
  // the 1451x790 reference), multiplied once by the desktop chrome factor
  // (webclient-proportional-ui-scale); the viewBox and every user-unit
  // coordinate stay as computed, so the drawing only magnifies uniformly.
  const latticeStyle = computed(() => {
    const side = `calc(${Number(props.canvasSize)}px * var(--ui-scale, 1))`;
    return { width: side, height: side };
  });

  return {
    isIsland,
    glyphSize,
    projection,
    nodeTier,
    islandDots,
    islandRings,
    islandRingLabels,
    scaleLabel,
    exitStubs,
    islandStubs,
    islandLabels,
    isGateway,
    leadsToOf,
    edges,
    drawnNodes,
    edgeGeoms,
    canvasWidth,
    canvasHeight,
    viewBox,
    latticeStyle,
    currentPos,
    activeEdgeMarkers,
    isGraph,
    truncatedLabel,
    visibleNodeLabel,
    nodePos,
  };
}
