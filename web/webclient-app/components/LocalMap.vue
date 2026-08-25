<script setup>
// LocalMap (H2, webclient-hud-02-status-islands, design D9/D10): the
// `local_map` v1 panel renderer, re-chromed as the stage's right-anchor
// island. The root keeps the stable `.local-map` class that H1's
// combat-hide CSS and the shell's `HIDDEN_BY_MODE` focus-rescue map select
// on literally, so the re-chrome never silently un-hides the minimap in a
// mode whose matrix hides it. The canvas is sized from the reduced model's
// exported lattice (`cols`/`rows`), so the canvas reserves its own space
// within the island's bounded height. The meta line carries the payload's
// `title` and, on the coordinate-bearing `grid` / `wilderness` layers only,
// a renderer-axis orientation legend (北↑); coordinate-free `instance` /
// `interior` layers omit it. No bearing, no compass angle, no distance is
// rendered (node `x`/`y` are renderer-local presentation geometry). The
// full-map affordance is deferred to H5 (MapOverlay), so the island ships
// no full-map control; the per-node `explore.move` submission is unchanged.
import { computed, ref } from "vue";

const props = defineProps({
  // The committed `local_map` v1 panel payload (available form or the
  // registry-owned unavailable form).
  localMap: { type: Object, required: true },
});

const emit = defineEmits(["move"]);

// Legend entries follow the fixed visibility order: current, visible_unvisited,
// visible_visited, remembered. Extra entries cycle through the same glyphs.
const LEGEND_STATES = ["current", "visible_unvisited", "visible_visited", "remembered"];
function legendState(index) {
  return LEGEND_STATES[index % LEGEND_STATES.length];
}

const available = computed(() => props.localMap.available === true);
const reason = computed(() => props.localMap.reason?.message ?? "");
const title = computed(() => props.localMap.title ?? "");
const layer = computed(() => props.localMap.layer ?? null);
const nodes = computed(() => (Array.isArray(props.localMap.nodes) ? props.localMap.nodes : []));
const edges = computed(() => (Array.isArray(props.localMap.edges) ? props.localMap.edges : []));
const legend = computed(() => (Array.isArray(props.localMap.legend) ? props.localMap.legend : []));
const remembered = computed(() => (Array.isArray(props.localMap.remembered) ? props.localMap.remembered : []));
const cols = computed(() => props.localMap.cols ?? 0);
const rows = computed(() => props.localMap.rows ?? 0);

// The orientation legend states the renderer's own axis convention only
// (design D9): the wilderness adapter puts north at +y and the renderer
// inverts y so +y draws upward — a statement about the drawing, not about
// the world. Shown on the coordinate-bearing layers only.
const showsOrientation = computed(
  () => layer.value === "grid" || layer.value === "wilderness",
);

// The detail line localizes the raw visibility token: previously entered
// nodes (visible_visited / remembered) both read as 已探索.
const STATE_LABELS = {
  current: "目前所在",
  visible_unvisited: "未探索",
  visible_visited: "已探索",
  remembered: "已探索",
};

const nodeById = computed(() => {
  const byId = {};
  for (const node of nodes.value) byId[node.id] = node;
  return byId;
});

// Lattice-driven canvas geometry (design D9 + the local-map delta): the
// reduced model places in-view nodes on a bounded integer lattice and
// exports the lattice's column/row counts; the canvas sizes from that
// lattice so it reserves its own space inside the island instead of the
// island scrolling a required surface out of view. North (+y) draws
// upward, so a node's row is inverted against the row count. A reserved
// label band below the last row keeps node labels inside the canvas
// instead of overhanging it and colliding with the island's next surface.
const CELL = 24;
const LABEL_BAND = 14;
const canvasWidth = computed(() => Math.max(1, cols.value) * CELL);
const canvasHeight = computed(() => Math.max(1, rows.value) * CELL + LABEL_BAND);

// Node labels are bounded and truncated in the 24px cell; the full label
// stays reachable through the node's accessible name.
const LABEL_MAX = 6;
function truncatedLabel(label) {
  const value = String(label ?? "");
  return value.length > LABEL_MAX ? value.slice(0, LABEL_MAX) + "…" : value;
}

function nodePos(node) {
  return {
    x: node.col * CELL + CELL / 2,
    y: (Math.max(1, rows.value) - 1 - node.row) * CELL + CELL / 2,
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

// Detail line: shows the hovered node when one is hovered, otherwise the
// selected node, defaulting to the current node on mount.
const selectedId = ref(props.localMap.current_node ?? null);
const hoveredId = ref(null);

const activeNode = computed(() => {
  const id = hoveredId.value ?? selectedId.value;
  // The active node may be an in-view lattice node or a remembered remote
  // node (the bounded focusable list), so search both collections.
  return (
    nodes.value.find((n) => n.id === id) ??
    remembered.value.find((n) => n.id === id) ??
    null
  );
});

const detailParts = computed(() => {
  const node = activeNode.value;
  if (!node) return [];
  const parts = [node.label, STATE_LABELS[node.visibility] ?? node.visibility];
  if (typeof node.x === "number" && typeof node.y === "number") {
    parts.push(`(${node.x}, ${node.y})`);
  }
  if (node.action) parts.push(`→ ${node.action.destination}`);
  return parts;
});

function selectNode(node) {
  selectedId.value = node.id;
  hoveredId.value = null;
}

function hoverNode(node) {
  hoveredId.value = node.id;
}

function clearHover() {
  hoveredId.value = null;
}

// Only an exact `move` action on the payload makes a node actionable.
function activateNode(node) {
  selectNode(node);
  if (node.action && node.action.kind === "move") {
    emit("move", {
      exit_ref: node.action.exit_ref,
      destination: node.action.destination,
    });
  }
}
</script>

<template>
  <aside class="local-map" data-testid="local-map">
    <p v-if="!available" class="local-map__unavailable" data-testid="local-map__unavailable">
      {{ reason }}
    </p>
    <template v-else>
      <!-- The island's top-meta line (design D9): the payload's title plus,
           on the coordinate-bearing layers only, the renderer's axis
           orientation legend. No bearing or distance is rendered. -->
      <div class="local-map__meta" data-testid="local-map__title">
        <span class="local-map__meta-title">{{ title }}</span>
        <span v-if="showsOrientation" class="local-map__orientation" data-testid="local-map__orientation">
          北↑
        </span>
      </div>

      <svg
        class="local-map__lattice"
        :width="canvasWidth"
        :height="canvasHeight"
        :viewBox="`0 0 ${canvasWidth} ${canvasHeight}`"
        role="img"
        aria-label="區域地圖縮圖"
        data-testid="local-map__lattice"
        @mouseleave="clearHover"
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
          @mouseenter="hoverNode(node)"
        >
          <rect
            v-if="node.visibility === 'current'"
            class="local-map__marker local-map__marker--current"
            data-testid="local-map__marker--current"
            x="-13"
            y="-13"
            width="26"
            height="26"
            aria-hidden="true"
          />
          <circle
            v-else-if="node.visibility === 'visible_unvisited'"
            class="local-map__marker local-map__marker--visible_unvisited"
            r="12"
            aria-hidden="true"
          />
          <circle
            v-else-if="node.visibility === 'visible_visited'"
            class="local-map__marker local-map__marker--visible_visited"
            r="12"
            aria-hidden="true"
          />
          <rect
            v-else-if="node.visibility === 'remembered'"
            class="local-map__marker local-map__marker--remembered"
            x="-9"
            y="-9"
            width="18"
            height="18"
            transform="rotate(45)"
            aria-hidden="true"
          />
          <circle
            v-if="node.action"
            class="local-map__actionable"
            data-testid="local-map__actionable"
            r="10"
            aria-hidden="true"
          />
          <text class="local-map__node-label" y="24" text-anchor="middle">
            <title>{{ node.label }}</title>{{ truncatedLabel(node.label) }}
          </text>
        </g>
      </svg>

      <!-- The spec's bounded, focusable remembered-remote-node list (outside
           the coordinate canvas): each entry keeps its non-color diamond
           state indicator and selects (focuses) the node without emitting a
           travel action. -->
      <ul v-if="remembered.length" class="local-map__remembered" data-testid="local-map-remembered">
        <li
          v-for="node in remembered"
          :key="node.id"
          class="local-map__node local-map__node--remembered"
          :data-testid="`local-map__node--${node.id}`"
          :data-node="node.id"
          :data-node-id="node.id"
          :data-visibility="node.visibility"
          tabindex="0"
          @click="selectNode(node)"
          @focus="selectNode(node)"
        >
          <svg
            class="local-map__marker local-map__marker--remembered"
            viewBox="-16 -16 32 32"
            width="14"
            height="14"
            aria-hidden="true"
          >
            <rect x="-7" y="-7" width="14" height="14" transform="rotate(45)" />
          </svg>
          <span class="local-map__node-label">{{ node.label }}</span>
        </li>
      </ul>

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

      <p class="local-map__detail" data-testid="local-map-detail">
        {{ detailParts.join(" · ") }}
      </p>
    </template>
  </aside>
</template>

<style scoped>
/* The island chrome (design D9): the shared tokens, so a token change or
   the reduced-motion block reaches it at once. The root keeps the
   load-bearing `.local-map` class that H1's mode-gate CSS selects on. */
.local-map {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  box-sizing: border-box;
  /* The island must be compressible inside the capped hud-right anchor
     (design D9/D10): when the island content outgrows the anchor's height
     budget, the root shrinks instead of overflowing into the action dock. */
  min-height: 0;
  padding: 9px;
  background: var(--panel);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border: var(--line);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  font-family: var(--f-sans);
}

.local-map__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 10px;
  letter-spacing: 0.12em;
  color: var(--paper-500);
  margin-bottom: 4px;
}

.local-map__meta-title {
  color: var(--paper-300);
}

/* The renderer-axis orientation legend (北↑): a statement about the
   drawing's axis convention, not about the world (design D9). */
.local-map__orientation {
  font-family: var(--f-mono);
  letter-spacing: 0;
  color: var(--gold-400);
}

.local-map__unavailable {
  margin: 0;
  padding: var(--sp-2) var(--sp-3);
  color: var(--paper-300);
  background: var(--panel-hi);
  border: 1px dashed var(--warn);
  border-radius: var(--radius-sm);
  font-size: 0.85em;
}

/* The canvas sizes from the model's exported lattice (cols × rows cells),
   bounded to the island's content width; the legend, remembered list, and
   detail line stay non-overlapping below it. */
.local-map__lattice {
  display: block;
  /* Natural pixel size from the lattice (cols × rows × 24px cells); the
     attribute width/height drive the render, capped by the island budget. */
  width: auto;
  max-width: 206px;
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

.local-map__detail {
  margin: 0;
  padding: var(--sp-1) var(--sp-3);
  color: var(--paper-300);
  border: var(--line);
  border-radius: var(--radius-sm);
  font-family: var(--f-mono);
  font-size: var(--text-sm);
}

.local-map__remembered {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.local-map__remembered .local-map__node {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-1);
  padding: 2px var(--sp-2);
  border: var(--line);
  border-radius: var(--radius-sm);
  color: var(--paper-300);
  font-size: var(--text-sm);
  cursor: pointer;
}

.local-map__remembered .local-map__marker--remembered rect {
  fill: var(--paper-500);
}
</style>
