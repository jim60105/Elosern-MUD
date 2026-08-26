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
  // Fill-width layout variant: the overlay renders the canvas at the body's
  // available width instead of the island's natural auto width.
  fillWidth: { type: Boolean, default: false },
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

// Lattice-driven canvas geometry (design D9 + the local-map delta): the
// canvas sizes from the exported lattice (cols/rows), reserving its own
// space instead of the host scrolling. The column pitch and row pitch are
// decoupled (the crowding fix): the row pitch clears the marker height,
// the label line, and a strictly-positive gap before the next row's
// marker; the column pitch clears two truncated labels side by side.
const LABEL_BAND = 14;
const canvasWidth = computed(() => Math.max(1, cols.value) * props.colPitch);
const canvasHeight = computed(() => Math.max(1, rows.value) * props.rowPitch + LABEL_BAND);

// Every lattice marker's base geometry, multiplied by the `markerScale`
// prop so all states scale uniformly: the current 26×26 rect, the
// unvisited/visited r=12 circles (visual half-extent 13 including the 2px
// stroke), the rotated remembered diamond, and the actionable halo.
const MARKER_CURRENT_HALF = 13;
const MARKER_CIRCLE_R = 12;
const MARKER_DIAMOND_HALF = 9;
const HALO_R = 10;
// The label baseline sits `MARKER_CURRENT_HALF * markerScale + 13` below
// the node origin: at the island's scale 1 this is the crowding fix's
// 26px offset (13px marker half-extent + 13px of clearance that keeps the
// 11px monospace line box clear of the node's own marker and of the
// marker in the row below).
function labelY() {
  return MARKER_CURRENT_HALF * props.markerScale + 13;
}

// Node labels are bounded and truncated (the full label stays reachable
// through the node's accessible name); a truncated label appends "…"
// (labelMax + 1 glyphs at 11px monospace, full-width CJK).
function truncatedLabel(label) {
  const value = String(label ?? "");
  return value.length > props.labelMax ? value.slice(0, props.labelMax) + "…" : value;
}

function nodePos(node) {
  return {
    x: node.col * props.colPitch + props.colPitch / 2,
    y: (Math.max(1, rows.value) - 1 - node.row) * props.rowPitch + props.rowPitch / 2,
  };
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
// visible_visited, remembered. Extra entries cycle through the same glyphs.
const LEGEND_STATES = ["current", "visible_unvisited", "visible_visited", "remembered"];
function legendState(index) {
  return LEGEND_STATES[index % LEGEND_STATES.length];
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
const latticeStyle = computed(() => {
  const style = {};
  if (props.fillWidth) style.width = "100%";
  if (props.maxWidth != null) style.maxWidth = props.maxWidth + "px";
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
    <g
      v-for="node in nodes"
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
      <rect
        v-if="node.visibility === 'current'"
        class="local-map__marker local-map__marker--current"
        data-testid="local-map__marker--current"
        :x="-MARKER_CURRENT_HALF * markerScale"
        :y="-MARKER_CURRENT_HALF * markerScale"
        :width="MARKER_CURRENT_HALF * 2 * markerScale"
        :height="MARKER_CURRENT_HALF * 2 * markerScale"
        aria-hidden="true"
      />
      <circle
        v-else-if="node.visibility === 'visible_unvisited'"
        class="local-map__marker local-map__marker--visible_unvisited"
        :r="MARKER_CIRCLE_R * markerScale"
        aria-hidden="true"
      />
      <circle
        v-else-if="node.visibility === 'visible_visited'"
        class="local-map__marker local-map__marker--visible_visited"
        :r="MARKER_CIRCLE_R * markerScale"
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
      <circle
        v-if="node.action"
        class="local-map__actionable"
        data-testid="local-map__actionable"
        :r="HALO_R * markerScale"
        aria-hidden="true"
      />
      <text class="local-map__node-label" :y="labelY()" text-anchor="middle">
        <title>{{ node.label }}</title>{{ truncatedLabel(node.label) }}
      </text>
    </g>
  </svg>

  <!-- The stateless state legend (moved out of the island chrome): each
       entry is a legend text label paired with its state glyph. -->
  <ul class="local-map__legend" data-testid="local-map__legend">
    <li
      v-for="(entry, i) in legend"
      :key="`legend-${i}`"
      class="local-map__legend-item"
      :data-testid="`local-map__legend-item--${i}`"
    >
      <svg
        class="local-map__legend-glyph"
        :class="`local-map__legend-glyph--${legendState(i)}`"
        viewBox="-16 -16 32 32"
        width="14"
        height="14"
        aria-hidden="true"
      >
        <rect v-if="legendState(i) === 'current'" x="-10" y="-10" width="20" height="20" />
        <rect v-else-if="legendState(i) === 'remembered'" x="-7" y="-7" width="14" height="14" transform="rotate(45)" />
        <circle v-else-if="legendState(i) === 'visible_visited'" r="9" />
        <circle v-else r="9" />
      </svg>
      {{ entry }}
    </li>
  </ul>
</template>

<style scoped>
/* The lattice canvas sizes from the model's exported lattice (cols × rows
   cells) and scales down proportionally under the caller-supplied caps
   (the island passes its measured height budget; the overlay passes no
   height cap and fills the body width). */
.local-map__lattice {
  display: block;
  /* The parent surfaces are flex columns (the island, the overlay body's
     centering wrapper), so without this the SVG would stretch to the
     parent's content width, *enlarging* small lattices and pushing the
     label offset back onto the marker below. `align-self: center` keeps
     the canvas at its natural (or uniformly capped) size, centered. */
  align-self: center;
  width: auto;
  height: auto;
  background: var(--ink-860);
  border: var(--line);
  border-radius: var(--radius-sm);
  overflow: visible;
}

.local-map__node {
  cursor: pointer;
}

.local-map__node-label {
  fill: var(--paper-300);
  font-family: var(--f-mono);
  font-size: 11px;
  /* Decorative label: must never intercept pointer events intended for the
     node's actionable circle (the label sits in the cell below its node). */
  pointer-events: none;
}

.local-map__marker--current {
  fill: var(--gold-400);
}

.local-map__marker--visible_unvisited {
  fill: transparent;
  stroke: var(--vit-sp);
  stroke-width: 2;
}

.local-map__marker--visible_visited {
  fill: var(--vit-sp);
}

.local-map__marker--remembered {
  fill: var(--paper-500);
}

.local-map__actionable {
  fill: var(--seal-glow);
  stroke: var(--seal-400);
  stroke-width: 2;
}

/* Edges form a non-interactive connector layer: they never intercept the
   pointer events intended for a node's actionable circle. */
.local-map__edge {
  pointer-events: none;
}

.local-map__edge--traversable {
  stroke: var(--paper-300);
  stroke-width: 1.5;
}

.local-map__edge--blocked {
  stroke: var(--paper-500);
  stroke-width: 1.5;
  stroke-dasharray: 6 4;
}

.local-map__edge--unknown {
  stroke: var(--paper-700);
  stroke-width: 1.5;
  stroke-opacity: 0.45;
  stroke-dasharray: 2 5;
}

.local-map__legend {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.local-map__legend-item {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-1);
  padding: 2px var(--sp-2);
  border: var(--line);
  border-radius: var(--radius-sm);
  color: var(--paper-300);
  font-size: var(--text-sm);
}

.local-map__legend-glyph {
  flex: none;
}

.local-map__legend-glyph--current rect {
  fill: var(--gold-400);
}

.local-map__legend-glyph--visible_unvisited circle {
  fill: transparent;
  stroke: var(--vit-sp);
  stroke-width: 2;
}

.local-map__legend-glyph--visible_visited circle {
  fill: var(--vit-sp);
}

.local-map__legend-glyph--remembered rect {
  fill: var(--paper-500);
}
</style>
