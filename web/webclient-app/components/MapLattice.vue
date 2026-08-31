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
  // Draft overlay chrome (webclient-map-01-draft-chrome design D4): the
  // full-map surface paints its canvas in the `mapcanvas` treatment and
  // draws the teardrop location pin above the current marker. Off on the
  // minimap island; only the overlay passes it.
  overlayChrome: { type: Boolean, default: false },
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
  return {
    x: node.col * props.colPitch + props.colPitch / 2,
    y: (Math.max(1, rows.value) - 1 - node.row) * props.rowPitch + props.rowPitch / 2,
  };
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
  if (node.landmark) return "gold";
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
        <title>{{ node.label }}</title>{{ truncatedLabel(node.label) }}
      </text>
    </g>
  </svg>

  <!-- The draft dot-chip state legend (webclient-map-01-draft-chrome D6):
       an 11px radius-3 colour chip paired with its text label. The chip
       border style carries non-colour redundancy — the remembered chip's
       dashed border differs from the visited chip's solid border (delta
       scenario "Legend chips stay text-labelled at both scales"). -->
  <ul class="local-map__legend" data-testid="local-map__legend">
    <li
      v-for="(entry, i) in legend"
      :key="`legend-${i}`"
      class="local-map__legend-item"
      :data-testid="`local-map__legend-item--${i}`"
    >
      <span
        class="local-map__legend-chip"
        :class="`local-map__legend-chip--${legendState(i)}`"
        aria-hidden="true"
      />
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
</style>
