<script setup>
// MapLattice (improve-webclient-map-overlay-scale): the shared `local_map`
// lattice renderer. Extracted from `LocalMap.vue` so the minimap island
// (`LocalMap.vue`) and the full-map overlay (`MapOverlay.vue`) share one
// node/marker/edge/label/legend rendering logic, parameterized by scale
// props rather than the island's fixed constants. The island keeps its
// selection state and detail line; this component owns only the stateless
// lattice rendering and emits `select`/`hover`/`leave`/`move` so each
// caller drives its own chrome.
import { computed } from "vue";
import LocalMap from "../lib/local_map.js";

const props = defineProps({
  // The committed `local_map` v1 panel payload (the available form or the
  // registry-owned unavailable form).
  localMap: { type: Object, required: true },
  // Lattice geometry. The defaults are the minimap's post-crowding-fix
  // values; the full-map overlay passes a larger set sized to the overlay
  // body's available width (900px host cap minus 52px of padding ≈ 848px).
  colPitch: { type: Number, default: 58 },
  rowPitch: { type: Number, default: 44 },
  labelMax: { type: Number, default: 4 },
  // Uniform multiplier over every lattice marker's base geometry, so all
  // visibility states scale together and inherit the crowding fix's
  // non-collision spacing at any scale.
  markerScale: { type: Number, default: 1 },
  // Canvas caps. `null` disables a cap (the overlay relies on its host's
  // `overflow-y: auto` fallback); the island passes its dynamically
  // measured height budget down from `LocalMap.vue`.
  maxWidth: { default: 206 },
  maxHeight: { default: 296 },
  // Fill-width layout variant: the canvas claims the caller's content width
  // instead of drawing at its natural pixel size. Both surfaces pass it —
  // the overlay to fill the overlay body, the minimap island to honour the
  // draft's `.mini svg { display:block; width:100%; max-width:172px }` rule
  // (REDESIGN §7: the lattice's geometry is its claim, so it must not be
  // invisible). Drawing at natural size left a sparse payload rendering a
  // ~111px canvas inside a ~210px island — the map was the smallest thing in
  // the island whose whole reason to exist is the map.
  fillWidth: { type: Boolean, default: false },
  // Upscale bound for `fillWidth` (island-only opt-in; `null` = unbounded, so
  // the overlay keeps filling its body width at its own larger scale). A
  // one-room payload's natural canvas is 58px wide, and letting it stretch to
  // the island's full width would blow the designed marker/label ramp up ~3.5x
  // — a 57px "you are here" seal and 39px labels. Bounding the uniform scale
  // keeps the drawn type ramp close to the draft's while every payload from
  // two columns (or one column plus the edge-marker gutter) up still claims
  // the whole island width.
  maxUpscale: { type: Number, default: null },
  // Draft overlay chrome (webclient-map-01-draft-chrome design D4): the
  // full-map surface paints its canvas in the `mapcanvas` treatment and
  // draws the teardrop location pin above the current marker. Off on the
  // minimap island; only the overlay passes it.
  overlayChrome: { type: Boolean, default: false },
  markerNames: { type: Boolean, default: false },
  edgeMarkers: { type: Object, default: null },
  // Layout variant (webclient-map-02-layout-variants D2/D3): "lattice" draws
  // the model's rank-compressed grid placement, "graph" draws the model's
  // radial (D1) placement. Both surfaces pass `model.layoutVariant` — the
  // variant is a renderer parameter sourced from the committed payload, and
  // it changes coordinate sourcing ONLY: markers, edges, labels, legend,
  // activation, focus, and accessible names stay the shared wave-1 renderer.
  variant: { type: String, default: "lattice" },
  // Legend-display switch (slim-minimap-island D1): the shared renderer
  // mounts the draft dot-chip state legend wherever this is on. It defaults
  // to on (the full-map overlay and every bare mount keep the legend); the
  // minimap island passes false so no legend element exists in its DOM for
  // any payload — v-if, not a CSS hide, so DOM assertions and the island's
  // budget measurement never see a stray legend.
  showLegend: { type: Boolean, default: true },
});

const emit = defineEmits(["select", "hover", "leave", "move"]);

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
    x: node.col * props.colPitch + props.colPitch / 2,
    y: (Math.max(1, rows.value) - 1 - node.row) * props.rowPitch + props.rowPitch / 2,
  };
}
const localEdgeMarkers = computed(() => {
  if (isGraph.value || rememberedList.value.length === 0) {
    return { markers: [], gutter: 0, width: 0, height: 0 };
  }
  const current = nodes.value.find((node) => node.visibility === "current");
  if (!current) {
    return { markers: [], gutter: 0, width: 0, height: 0 };
  }
  return LocalMap.edgeMarkersFor(nodes.value, rememberedList.value, {
    canvasWidth: Math.max(1, cols.value) * props.colPitch,
    canvasHeight: Math.max(1, rows.value) * props.rowPitch + LABEL_BAND,
    current: latticePos(current),
    // The drawn diamond: 9-half-extent rect rotated 45 degrees at the
    // active marker scale (the model's reach formula consumes it directly).
    markerHalf: MARKER_DIAMOND_HALF * props.markerScale,
    // Only the overlay draws marker names; the bound is the truncated
    // label's worst-case box (labelMax + 1 full-width glyphs at the 11px
    // canvas font, which does not scale with the markers).
    nameWidth: props.overlayChrome ? (props.labelMax + 1) * 11 : 0,
    nameHeight: props.markerNames ? 16 : 0,
  });
});

const activeEdgeMarkers = computed(() => props.edgeMarkers || localEdgeMarkers.value);

function fitMarkerName(label, budget) {
  if (!label || budget < 3) return "";
  const chars = Array.from(label);
  if (chars.length <= budget) return label;
  const parenIdx = label.lastIndexOf("（");
  if (parenIdx !== -1 && label.endsWith("）") && parenIdx < label.length - 1) {
    const qualifier = label.slice(parenIdx);
    const qualifierChars = Array.from(qualifier);
    if (budget >= 2 + qualifierChars.length) {
      const headBudget = budget - 1 - qualifierChars.length;
      const headChars = Array.from(label.slice(0, parenIdx)).slice(0, headBudget);
      return headChars.join("") + "…" + qualifier;
    }
  }
  const tailLen = Math.min(chars.length - 2, budget - 2);
  const headLen = Math.max(1, budget - 1 - tailLen);
  return chars.slice(0, headLen).join("") + "…" + chars.slice(chars.length - tailLen).join("");
}

const fittedEdgeMarkers = computed(() => {
  const markers = activeEdgeMarkers.value.markers || [];
  if (!props.markerNames || markers.length === 0) {
    return markers.map((m) => ({
      ...m,
      visibleName: "",
      glyphs: [],
    }));
  }
  if (props.overlayChrome) {
    return markers.map((m) => ({
      ...m,
      visibleName: m.name,
      glyphs: [],
    }));
  }

  const reach = Math.SQRT2 * MARKER_DIAMOND_HALF * props.markerScale;
  const namePad = 18;
  const inset = Math.max(19, 2 * reach + namePad + 1);
  const slotMinH = 2 * reach + 1;
  const slotMinV = 2 * reach + 1 + 16;
  const outerWidth = activeEdgeMarkers.value.width;
  const outerHeight = activeEdgeMarkers.value.height;

  const bySide = { top: [], bottom: [], left: [], right: [] };
  markers.forEach((m) => {
    if (bySide[m.side]) bySide[m.side].push(m);
  });

  const spanBySide = {};
  for (const side of ["top", "bottom", "left", "right"]) {
    const group = bySide[side];
    if (group.length === 0) continue;
    const horizontal = side === "top" || side === "bottom";
    const outerLength = horizontal ? outerWidth : outerHeight;
    const slotMin = horizontal ? slotMinH : slotMinV;
    const usable = Math.max(outerLength - 2 * inset, group.length * slotMin);
    spanBySide[side] = usable / group.length;
  }

  const fittedList = markers.map((m) => {
    const span = spanBySide[m.side] || 0;
    const budget = Math.floor(span / 13);
    const fitted = fitMarkerName(m.name, budget);
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

// The drawn placement follows the model: a graph payload whose nodes the
// radial placement does not cover renders them not-at-all rather than at a
// fabricated position (the shared omission contract of an absent edge
// endpoint).
const drawnNodes = computed(() =>
  radial.value
    ? nodes.value.filter((node) => radialById.value[node.id])
    : nodes.value,
);

const LABEL_BAND = 14;
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
const canvasWidth = computed(() =>
  radial.value
    ? graphCanvasWidth.value
    : Math.max(1, cols.value) * props.colPitch + 2 * activeEdgeMarkers.value.gutter,
);
const canvasHeight = computed(() =>
  radial.value
    ? graphCanvasHeight.value
    : Math.max(1, rows.value) * props.rowPitch + LABEL_BAND + 2 * activeEdgeMarkers.value.gutter,
);
// The crowding fix decouples column pitch and row pitch: the row pitch
// clears the marker height, the label line, and a strictly-positive gap
// before the next row's marker; the column pitch clears two truncated
// labels side by side.

// Every lattice marker's base geometry in pre-scale units, multiplied by
// the `markerScale` prop so all states scale uniformly (draft ladder,
// webclient-map-01-draft-chrome D2): the current seal circle r=8 (visual
// half-extent 9 with the 2px stroke), the visited/unvisited dots r=4.5
// (+0.5 stroke → 5), the gold landmark ring r=5, the rotated remembered
// diamond half-extent 9, and the actionable halo r=10. Every footprint is
// strictly smaller than the pre-draft 26px square / r=12 circles, so the
// crowding fix's pitch guarantee carries over unchanged.
const MARKER_CURRENT_R = 8;
const MARKER_DOT_R = 4.5;
const MARKER_LANDMARK_R = 5;
const MARKER_DIAMOND_HALF = 9;
const HALO_R = 10;
// The label baseline sits 26px below the node origin at scale 1, scaled
// with the markers: the crowding fix's offset (LABEL_ANCHOR_HALF 13 +
// 13px clearance), deliberately kept after the re-skin — it clears the
// draft ladder's smaller footprints with strictly more room, so the
// non-overlap invariant holds a fortiori.
const LABEL_ANCHOR_HALF = 13;
function labelY() {
  return LABEL_ANCHOR_HALF * props.markerScale + 13;
}

// Node labels are bounded and truncated (the full label stays reachable
// through the node's accessible name); a truncated label appends "…"
// (labelMax + 1 glyphs at 11px monospace, full-width CJK).
function truncatedLabel(label) {
  const value = String(label ?? "");
  return value.length > props.labelMax ? value.slice(0, props.labelMax) + "…" : value;
}

function nodePos(node) {
  if (radial.value) {
    const placed = radialById.value[node.id];
    // A node the placement omits is not drawn (same omission contract as
    // an edge whose endpoint is absent).
    if (!placed) return null;
    return { x: placed.x * props.markerScale, y: placed.y * props.markerScale };
  }
  const core = latticePos(node);
  const gutter = activeEdgeMarkers.value.gutter;
  return { x: core.x + gutter, y: core.y + gutter };
}

// Edge-marker name placement (map-02 D4 wording): the name box is drawn
// OUTWARD from the diamond's outer tip — never toward the canvas. The
// 11px monospace glyph line does not scale with the markers (same policy
// as the node labels), so the offset is the scaled rotated-diamond axial
// reach plus the 2-unit model margin and an 11px ascent to the baseline.
const MARKER_NAME_ASCENT = 11;
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
  if (marker.side === "top") return -(reach + 4);
  if (marker.side === "bottom") return reach + 14;
  const k = marker.glyphs?.length || 1;
  return -((k - 1) * 13) / 2 + 4;
}
function markerNameAnchor(marker) {
  if (props.overlayChrome) {
    if (marker.side === "left") return "end";
    if (marker.side === "right") return "start";
    return "middle";
  }
  return "middle";
}
// The overlay pin's anchor (design D4): the CURRENT placement's current-node
// position, in the same coordinate system as the node groups' translate.
// Null (no pin) when the payload carries no on-canvas current node.
const currentPos = computed(() => {
  const current = nodes.value.find((node) => node.visibility === "current");
  return current ? nodePos(current) : null;
});

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

function edgeClass(edge) {
  if (edge.known === false) return "local-map__edge--unknown";
  return edge.traversable ? "local-map__edge--traversable" : "local-map__edge--blocked";
}

// Legend entries follow the fixed visibility order: current, visible_unvisited,
// visible_visited, remembered. Entries beyond the four states are explanatory
// notes (e.g. the wilderness scale line), never visibility states: they get a
// dedicated neutral info treatment instead of cycling the state glyphs, so a
// note can never masquerade as a fifth node state (webclient-map-scale-legend
// D3). `null` marks the beyond-state range.
const LEGEND_STATES = ["current", "visible_unvisited", "visible_visited", "remembered"];
function legendState(index) {
  return index < LEGEND_STATES.length ? LEGEND_STATES[index] : null;
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
  if (props.maxUpscale != null) caps.push(canvasWidth.value * props.maxUpscale);
  return caps;
}

const latticeStyle = computed(() => {
  const style = {};
  if (props.fillWidth) style.width = "100%";
  const caps = widthCaps();
  // Floored to 2 decimals: a bound rounded UP could re-cross the height
  // budget by a sub-pixel and hand the anchor a scrollbar.
  if (caps.length) style.maxWidth = Math.floor(Math.min(...caps) * 100) / 100 + "px";
  if (props.maxHeight != null) style.maxHeight = props.maxHeight + "px";
  return style;
});
</script>

<template>
  <!-- The stateless lattice surface: connector edges, state-distinguished
       node markers, single-line truncated labels, and the state legend.
       The root is a fragment (svg + legend) so both callers' surrounding
       chrome stays the only structural difference between the minimap and
       the overlay. -->
  <svg
    class="local-map__lattice"
    :class="{ 'local-map__lattice--canvas': overlayChrome }"
    :width="canvasWidth"
    :height="canvasHeight"
    :viewBox="`0 0 ${canvasWidth} ${canvasHeight}`"
    :style="latticeStyle"
    role="img"
    aria-label="區域地圖縮圖"
    data-testid="local-map__lattice"
    @mouseleave="emit('leave')"
  >
    <line
      v-for="edge in edgeGeoms"
      :key="`edge-${edge.i}`"
      class="local-map__edge"
      :class="edgeClass(edges[edge.i])"
      :data-testid="`local-map__edge--${edge.i}`"
      :x1="edge.x1"
      :y1="edge.y1"
      :x2="edge.x2"
      :y2="edge.y2"
      :aria-label="edges[edge.i].label"
    />
    <!-- The draft location pin (webclient-map-01-draft-chrome design D4):
         rendered inside this SVG (not positioned by the overlay wrapper) so
         it shares the current marker's coordinate system. Anchored to the
         CURRENT placement's current-node position and scaled with the
         markers, its tip sits directly above the current circle. A pure
         adornment: fixed path, non-interactive, aria-hidden, no label. -->
    <path
      v-if="overlayChrome && currentPos"
      class="local-map__pin"
      data-testid="local-map__pin"
      :transform="`translate(${currentPos.x}, ${currentPos.y}) scale(${markerScale})`"
      d="M0 -16 l-7 24 6 -5 5 7 5 -7 6 5 z"
      aria-hidden="true"
    />
    <!-- Edge direction markers (map-02 D3b): remembered places outside the
         in-view extent, claimed by the true current→remote bearing, drawn in
         the gutter OUTSIDE the node canvas. A pure decoration layer:
         deliberately NOT the `local-map__marker` class (the browser geometry
         audit pairs every `.local-map__marker` box; these are not node
         placements), no activation, pointer-events none. The island keeps
         its focusable remembered list as the canonical reading path and
         renders the layer aria-hidden without names; at the overlay scale
         each marker shows its (truncated) place name and carries it as the
         accessible name. -->
    <g
      v-for="marker in fittedEdgeMarkers"
      :key="`edge-marker-${marker.id}`"
      class="local-map__edge-marker"
      :data-testid="`local-map__edge-marker--${marker.id}`"
      :transform="`translate(${marker.x}, ${marker.y})`"
      :role="overlayChrome ? 'img' : null"
      :aria-label="overlayChrome ? marker.name : null"
      :aria-hidden="overlayChrome ? null : 'true'"
    >
      <title>{{ marker.name }}</title>
      <rect
        class="local-map__edge-marker-diamond"
        :x="-MARKER_DIAMOND_HALF * markerScale"
        :y="-MARKER_DIAMOND_HALF * markerScale"
        :width="MARKER_DIAMOND_HALF * 2 * markerScale"
        :height="MARKER_DIAMOND_HALF * 2 * markerScale"
        transform="rotate(45)"
      />
      <circle
        v-if="marker.landmark"
        class="local-map__edge-marker-landmark"
        :r="MARKER_LANDMARK_R * markerScale"
      />
      <template v-if="markerNames">
        <text
          v-if="overlayChrome"
          class="local-map__edge-marker-name"
          :x="markerNameX(marker)"
          :y="markerNameY(marker)"
          :text-anchor="markerNameAnchor(marker)"
        >{{ marker.visibleName }}</text>
        <text
          v-else-if="marker.visibleName && (marker.side === 'top' || marker.side === 'bottom')"
          class="local-map__edge-marker-name--island"
          :x="markerNameX(marker)"
          :y="markerNameY(marker)"
          :text-anchor="markerNameAnchor(marker)"
        >{{ marker.visibleName }}</text>
        <text
          v-else-if="marker.visibleName && (marker.side === 'left' || marker.side === 'right')"
          class="local-map__edge-marker-name--island"
          :x="markerNameX(marker)"
          :y="markerNameY(marker)"
          :text-anchor="markerNameAnchor(marker)"
        >
          <tspan
            v-for="(glyph, i) in marker.glyphs"
            :key="i"
            :x="markerNameX(marker)"
            :dy="i === 0 ? 0 : 13"
          >{{ glyph }}</tspan>
        </text>
      </template>
    </g>
    <g
      v-for="node in drawnNodes"
      :key="node.id"
      class="local-map__node"
      :class="`local-map__node--${node.visibility}`"
      :data-testid="`local-map__node--${node.id}`"
      :data-node="node.id"
      :data-node-id="node.id"
      :data-visibility="node.visibility"
      :transform="`translate(${nodePos(node).x}, ${nodePos(node).y})`"
      @click="activateNode(node)"
      @mouseenter="emit('hover', node)"
    >
      <!-- The draft marker ladder (webclient-map-01-draft-chrome D2): the
           current node is the large seal-stroked circle; visited is a small
           ink-filled circle; unvisited is a small hollow circle (keeps the
           未探索 rule); remembered keeps the rotated diamond. Shape/size
           distinguish the states without colour. -->
      <circle
        v-if="node.visibility === 'current'"
        class="local-map__marker local-map__marker--current"
        data-testid="local-map__marker--current"
        :r="MARKER_CURRENT_R * markerScale"
        aria-hidden="true"
      />
      <circle
        v-else-if="node.visibility === 'visible_unvisited'"
        class="local-map__marker local-map__marker--visible_unvisited"
        :r="MARKER_DOT_R * markerScale"
        aria-hidden="true"
      />
      <circle
        v-else-if="node.visibility === 'visible_visited'"
        class="local-map__marker local-map__marker--visible_visited"
        :r="MARKER_DOT_R * markerScale"
        aria-hidden="true"
      />
      <rect
        v-else-if="node.visibility === 'remembered'"
        class="local-map__marker local-map__marker--remembered"
        :x="-MARKER_DIAMOND_HALF * markerScale"
        :y="-MARKER_DIAMOND_HALF * markerScale"
        :width="MARKER_DIAMOND_HALF * 2 * markerScale"
        :height="MARKER_DIAMOND_HALF * 2 * markerScale"
        transform="rotate(45)"
        aria-hidden="true"
      />
      <!-- The gold landmark treatment (draft `.mini` gold dots): an extra
           gold ring drawn over (never replacing) the node's visibility
           marker. Deliberately OUTSIDE the `local-map__marker` class: the
           browser geometry audit pairs every `.local-map__marker` box, and a
           same-node decoration is not a node marker. -->
      <circle
        v-if="node.landmark && node.visibility !== 'remembered'"
        class="local-map__landmark"
        data-testid="local-map__landmark"
        :r="MARKER_LANDMARK_R * markerScale"
        aria-hidden="true"
      />
      <circle
        v-if="node.action"
        class="local-map__actionable"
        data-testid="local-map__actionable"
        :r="HALO_R * markerScale"
        aria-hidden="true"
      />
      <text
        class="local-map__node-label"
        :class="`local-map__node-label--${labelTier(node)}`"
        :y="labelY()"
        text-anchor="middle"
      >
        <title>{{ node.label }}</title>{{ labelSuppressed(node) ? "" : truncatedLabel(node.label) }}
      </text>
    </g>
  </svg>

  <!-- The draft dot-chip state legend (webclient-map-01-draft-chrome D6):
       an 11px radius-3 colour chip paired with its text label. The chip
       border style carries non-colour redundancy — the remembered chip's
       dashed border differs from the visited chip's solid border (delta
       scenario "Legend chips stay text-labelled at both scales"). Mounted
       wherever the `showLegend` switch is on (slim-minimap-island D1): the
       overlay keeps it, the minimap island passes false and mounts no
       legend element at all. -->
  <ul v-if="showLegend" class="local-map__legend" data-testid="local-map__legend">
    <li
      v-for="(entry, i) in legend"
      :key="`legend-${i}`"
      class="local-map__legend-item"
      :data-testid="`local-map__legend-item--${i}`"
    >
      <span
        class="local-map__legend-chip"
        :class="
          legendState(i) === null
            ? 'local-map__legend-chip--info'
            : `local-map__legend-chip--${legendState(i)}`
        "
        aria-hidden="true"
      />
      {{ entry }}
    </li>
  </ul>
</template>

<style scoped>
/* The lattice canvas sizes from the model's exported lattice (cols × rows
   cells) and scales proportionally under the caller-supplied caps, which
   both callers resolve into the single `max-width` bound computed in
   `latticeStyle` (the island passes its measured height budget and an
   upscale bound; the overlay passes no height cap and fills the body
   width). */
.local-map__lattice {
  display: block;
  /* `align-self: center` centres the canvas whenever a cap makes it narrower
     than the surface (a tall payload trades width for the island's height
     budget). It no longer defends a natural-size rendering: an earlier
     revision used it plus `width: auto` to stop the flex column from
     *enlarging* small lattices, which is exactly what the draft's
     `.mini svg { width: 100% }` asks for and what `fillWidth` now does —
     uniformly, through the viewBox, so every marker/label/gutter offset in
     the geometry contract stays proportional and scale-invariant. */
  align-self: center;
  width: auto;
  height: auto;
  background: var(--ink-860);
  border: var(--line);
  border-radius: var(--radius-sm);
  overflow: visible;
}

.local-map__edge-marker-name--island {
  font-family: var(--f-mono);
  font-size: var(--text-sm);
  fill: var(--paper-500);
}

/* The draft mapcanvas framing (webclient-map-01-draft-chrome D4): the
   overlay surface paints the dark radial-gradient terrain and the rounded
   ink frame as pure CSS — no fabricated terrain geometry. */
.local-map__lattice--canvas {
  background: radial-gradient(70% 60% at 40% 30%, var(--map-canvas-hi), var(--map-canvas-lo));
  border: 1px solid var(--ink-600);
  border-radius: var(--radius);
}

.local-map__node {
  cursor: pointer;
}

.local-map__node-label {
  font-family: var(--f-mono);
  font-size: 11px;
  /* Decorative label: must never intercept pointer events intended for the
     node's actionable circle (the label sits in the cell below its node). */
  pointer-events: none;
}

/* Draft label tiers (D3 tokens): current brightest, landmark gold,
   visited seen, unvisited far. */
.local-map__node-label--here {
  fill: var(--map-label-here);
}

.local-map__node-label--gold {
  fill: var(--map-label-gold);
}

.local-map__node-label--seen {
  fill: var(--map-label-seen);
}

.local-map__node-label--far {
  fill: var(--map-label-far);
}

/* The draft marker ladder (D2): the large seal-stroked current circle, the
   small ink-filled visited dot, the small hollow unvisited dot (keeps the
   未探索 rule), the remembered diamond. Shape/size distinguish the states
   without colour. */
.local-map__marker--current {
  fill: var(--seal-deep);
  stroke: var(--seal-light);
  stroke-width: 2;
}

.local-map__marker--visible_unvisited {
  fill: transparent;
  stroke: var(--vit-sp);
  stroke-width: 2;
}

.local-map__marker--visible_visited {
  fill: var(--ink-700);
  stroke: var(--ink-edge);
  stroke-width: 1;
}

.local-map__marker--remembered {
  fill: var(--paper-500);
}

/* The gold landmark ring (draft `.mini` 金環): a decoration over the node's
   own visibility marker, never a second position claim. */
.local-map__landmark {
  fill: none;
  stroke: var(--gold-500);
  stroke-width: 1;
  pointer-events: none;
}

.local-map__actionable {
  fill: var(--seal-glow);
  stroke: var(--seal-light);
  stroke-width: 2;
}

/* The draft location pin (D4): the teardrop ornament above the current
   marker — non-interactive, unlabelled, no activation of its own. The path
   geometry scales with the marker ladder via the element transform, but
   `vector-effect: non-scaling-stroke` keeps the draft's 1.4px outline at
   any `markerScale` (an SVG transform would otherwise thicken the stroke
   proportionally — the draft pairs a hairline pin with a 2px marker ring). */
.local-map__pin {
  fill: var(--map-canvas-lo);
  stroke: var(--seal-light);
  stroke-width: 1.4;
  vector-effect: non-scaling-stroke;
  pointer-events: none;
}

/* Edge direction markers (map-02 D3b): a non-interactive decoration layer
   in the gutter. The diamond reuses the remembered-node fill so the off-
   canvas place reads with the same state identity; the landmark ring and
   the 11px monospace name follow the node-label/pin precedents (glyphs
   never scale with markerScale). */
.local-map__edge-marker {
  pointer-events: none;
}

.local-map__edge-marker-diamond {
  fill: var(--paper-500);
}

.local-map__edge-marker-landmark {
  fill: none;
  stroke: var(--gold-500);
  stroke-width: 1;
}

.local-map__edge-marker-name {
  font-family: var(--f-mono);
  font-size: 11px;
  fill: var(--paper-500);
}

/* Edges form a non-interactive connector layer: they never intercept the
   pointer events intended for a node's actionable circle. Draft strokes
   (D2 language): solid ink for traversable, dashed for blocked, faint for
   unknown — all through the ink-edge token. */
.local-map__edge {
  pointer-events: none;
}

.local-map__edge--traversable {
  stroke: var(--ink-edge);
  stroke-width: 2;
}

.local-map__edge--blocked {
  stroke: var(--ink-edge);
  stroke-width: 2;
  stroke-dasharray: 3 4;
}

.local-map__edge--unknown {
  stroke: var(--ink-edge);
  stroke-width: 1.5;
  stroke-opacity: 0.45;
  stroke-dasharray: 2 5;
}

/* The draft dot-chip legend (D6): an 11px radius-3 chip + 11px text label,
   14px gap, no bordered pill. The text labels stay the non-colour
   indicator; remembered (dashed) vs visited (solid) chip borders add a
   non-colour distinction between those two entries. */
.local-map__legend {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.local-map__legend-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--paper-500);
  font-size: 11px;
}

.local-map__legend-chip {
  flex: none;
  width: 11px;
  height: 11px;
  border-radius: 3px;
}

.local-map__legend-chip--current {
  background: var(--seal-deep);
}

.local-map__legend-chip--visible_unvisited {
  background: transparent;
  border: 1px solid var(--ink-edge);
}

.local-map__legend-chip--visible_visited {
  background: var(--map-canvas-hi);
  border: 1px solid var(--gold-500);
}

.local-map__legend-chip--remembered {
  background: var(--map-canvas-hi);
  border: 1px dashed var(--gold-500);
}

/* Beyond-state note entries (webclient-map-scale-legend D3): a neutral
   design-token chip whose dotted border is a shape distinction no state
   chip uses (current: solid fill, unvisited: solid border, visited: solid
   border, remembered: dashed border), so the info entry never relies on
   colour alone and can never be mistaken for a visibility state. */
.local-map__legend-chip--info {
  background: transparent;
  border: 1px dotted var(--ink-edge);
}
</style>
