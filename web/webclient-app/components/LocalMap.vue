<script setup>
// LocalMap (B4 world family): the `local_map` v1 panel renderer for the Vue
// webclient. It renders the committed payload's title, the SVG lattice with
// not-color-only state markers (square / open circle / filled circle /
// diamond), the edge styles, the legend with state glyphs, and the detail
// line. Actionable adjacent nodes emit `move` with the payload's own
// exit_ref and destination — no field is invented.
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
const nodes = computed(() => (Array.isArray(props.localMap.nodes) ? props.localMap.nodes : []));
const edges = computed(() => (Array.isArray(props.localMap.edges) ? props.localMap.edges : []));
const legend = computed(() => (Array.isArray(props.localMap.legend) ? props.localMap.legend : []));
// The bounded, focusable remembered-remote-node list (spec: presented
// outside the coordinate canvas; focus-only, no travel action).
const remembered = computed(() => (Array.isArray(props.localMap.remembered) ? props.localMap.remembered : []));

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

// Renderer-local geometry: map the payload's x/y range into the 640x400
// viewBox with 40px padding. Node x/y are presentation coordinates.
const bbox = computed(() => {
  const xs = nodes.value.map((n) => n.x);
  const ys = nodes.value.map((n) => n.y);
  return {
    minX: xs.length ? Math.min(...xs) : 0,
    maxX: xs.length ? Math.max(...xs) : 1,
    minY: ys.length ? Math.min(...ys) : 0,
    maxY: ys.length ? Math.max(...ys) : 1,
  };
});
const PADDING = 40;

function nodePos(node) {
  const { minX, maxX, minY, maxY } = bbox.value;
  const scaleX = (640 - 2 * PADDING) / Math.max(1, maxX - minX);
  const scaleY = (400 - 2 * PADDING) / Math.max(1, maxY - minY);
  return {
    x: PADDING + (node.x - minX) * scaleX,
    y: 400 - PADDING - (node.y - minY) * scaleY,
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
      return {
        i,
        x1: nodePos(s).x,
        y1: nodePos(s).y,
        x2: nodePos(d).x,
        y2: nodePos(d).y,
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
  const parts = [node.label, STATE_LABELS[node.visibility] ?? node.visibility, `(${node.x}, ${node.y})`];
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
    <h3 v-if="available" class="local-map__title" data-testid="local-map__title">
      {{ title }}
    </h3>

    <p v-if="!available" class="local-map__unavailable" data-testid="local-map__unavailable">
      {{ reason }}
    </p>

    <template v-else>
      <svg
        class="local-map__lattice"
        viewBox="0 0 640 400"
        role="img"
        aria-label="區域地圖縮圖"
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
          @mouseenter="hoverNode(node)"
        >
          <rect
            v-if="node.visibility === 'current'"
            class="local-map__marker local-map__marker--current"
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
            r="18"
            aria-hidden="true"
          />
          <text class="local-map__node-label" y="24" text-anchor="middle">{{ node.label }}</text>
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
.local-map {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
  box-sizing: border-box;
  padding: var(--sp-3) var(--sp-4);
  background: var(--panel);
  border: var(--line);
  border-radius: var(--radius);
  font-family: var(--f-sans);
}

.local-map__title {
  margin: 0;
  color: var(--paper-100);
  font-family: var(--f-display);
  font-size: 1em;
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

.local-map__lattice {
  width: 100%;
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
