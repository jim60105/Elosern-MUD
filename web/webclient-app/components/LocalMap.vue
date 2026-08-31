<script setup>
// LocalMap (H2, webclient-hud-02-status-islands, design D9/D10): the
// `local_map` v1 panel renderer, re-chromed as the stage's right-anchor
// island. The root keeps the stable `.local-map` class that H1's
// combat-hide CSS and the shell's `HIDDEN_BY_MODE` focus-rescue map select
// on literally, so the re-chrome never silently un-hides the minimap in a
// mode whose matrix hides it. The lattice itself (nodes, markers,
// connector edges, labels, state legend) is rendered by the shared
// MapLattice component (improve-webclient-map-overlay-scale), so the
// full-map overlay can render the same lattice at its own larger scale.
// The island keeps its chrome: the meta row (title + orientation legend +
// "展開全地圖" expand button), the bounded focusable remembered-node list,
// and the hovered/selected-node detail line driven by the lattice's
// `select`/`hover`/`leave` events.
import { computed, onMounted, onUpdated, ref } from "vue";
import MapLattice from "./MapLattice.vue";

const props = defineProps({
  // The committed `local_map` v1 panel payload (available form or the
  // registry-owned unavailable form).
  localMap: { type: Object, required: true },
});

const emit = defineEmits(["move", "open-map"]);

// Legend entries follow the fixed visibility order: current, visible_unvisited,
// visible_visited, remembered. Extra entries cycle through the same glyphs.

const available = computed(() => props.localMap.available === true);
const reason = computed(() => props.localMap.reason?.message ?? "");
const title = computed(() => props.localMap.title ?? "");
const layer = computed(() => props.localMap.layer ?? null);
const nodes = computed(() => (Array.isArray(props.localMap.nodes) ? props.localMap.nodes : []));
const remembered = computed(() => (Array.isArray(props.localMap.remembered) ? props.localMap.remembered : []));

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

// Detail line: shows the hovered node when one is hovered, otherwise the
// selected node, defaulting to the current node on mount. The lattice's
// `select` event (emitted on every node activation) drives `selectedId`;
// the remembered list's own click/focus handlers still call `selectNode`
// directly — it never left the island's scope.
// The live store passes the reducer's `currentNode` (the raw payload's
// `current_node` is renamed by `reducePanel`); reading the raw field left the
// detail line unseeded in production (wave 0 design D1).
const selectedId = ref(props.localMap.currentNode ?? null);
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

// Dynamic canvas height budget (the crowding fix): a fixed 296px cap would
// ignore the rendered height of the island's other sections, so a tall
// lattice combined with a long remembered list would push required content
// into the anchor's overflow-y scroll fallback. Instead the canvas's
// max-height shrinks to the space the hud-right anchor's height budget
// leaves after the meta row, remembered list, legend, and detail line; the
// computed cap is passed down to MapLattice as its `maxHeight` prop.
const rootEl = ref(null);
const metaEl = ref(null);
const rememberedEl = ref(null);
const detailEl = ref(null);
const canvasMaxHeight = ref(0);

function sectionHeight(el) {
  return el ? Math.ceil(el.getBoundingClientRect().height) : 0;
}

function measureCanvasBudget() {
  const root = rootEl.value;
  if (!root) return;
  // Island context only: the full-map overlay renders the lattice outside
  // the hud-right anchor, so it keeps the prop caps.
  const anchor = root.closest('[data-anchor="hud-right"]');
  if (!anchor) return;
  const budget = anchor.clientHeight;
  if (!budget) return;
  // 5 island sections (meta, canvas, remembered list when non-empty,
  // legend, detail) separated by 8px (--sp-2) gaps; the meta row also
  // carries a 4px margin-bottom outside its own bounding box; 9px island
  // padding top and bottom; the canvas element's 2px border. The state
  // legend now renders inside MapLattice (this component's child), so the
  // lookup is scoped to the island root to measure its height without
  // picking up a legend from a sibling surface (the overlay may be mounted
  // at the same time).
  const legendEl = root.querySelector('[data-testid="local-map__legend"]');
  const gapCount = 3 + (remembered.value.length > 0 ? 1 : 0);
  const others =
    sectionHeight(metaEl.value) +
    sectionHeight(rememberedEl.value) +
    sectionHeight(legendEl) +
    sectionHeight(detailEl.value);
  // The extra 1px of slack absorbs the island's 1px border top/bottom
  // rounding so the island never needs to scroll a required surface.
  const available = budget - others - gapCount * 8 - 18 - 2 - 5;
  canvasMaxHeight.value = Math.max(40, Math.min(296, available));
}

onMounted(() => {
  measureCanvasBudget();
  const anchor = rootEl.value?.closest('[data-anchor="hud-right"]');
  if (anchor && typeof ResizeObserver !== "undefined") {
    new ResizeObserver(() => measureCanvasBudget()).observe(anchor);
  }
});
onUpdated(() => {
  measureCanvasBudget();
});
</script>

<template>
  <aside class="local-map" data-testid="local-map" ref="rootEl">
    <p v-if="!available" class="local-map__unavailable" data-testid="local-map__unavailable">
      {{ reason }}
    </p>
    <template v-else>
      <!-- The island's top-meta line (design D9): the payload's title plus,
           on the coordinate-bearing layers only, the renderer's axis
           orientation legend. No bearing or distance is rendered. -->
      <div class="local-map__meta" data-testid="local-map__title" ref="metaEl">
        <span class="local-map__meta-title">{{ title }}</span>
        <span v-if="showsOrientation" class="local-map__orientation" data-testid="local-map__orientation">
          北↑
        </span>
        <!-- H5 (task 6.2): the island's labelled full-map trigger, a sibling
             of the lattice on the island's header row (H2's deferred affordance
             now that the full-map surface is reachable). Opening the map
             overlay routes through the parent's overlay slice. -->
        <button
          type="button"
          class="local-map__expand"
          data-testid="local-map__expand"
          aria-label="展開全地圖"
          @click="emit('open-map')"
        >
          展開全地圖
        </button>
      </div>

      <!-- Shared lattice renderer (improve-webclient-map-overlay-scale): the
           minimap composes MapLattice at its default (post-crowding-fix)
           scale; the dynamically measured height budget (the crowding fix)
           is passed down as the canvas cap. -->
      <MapLattice
        :local-map="localMap"
        :max-height="canvasMaxHeight || 296"
        @select="selectNode"
        @hover="hoverNode"
        @leave="clearHover"
        @move="(p) => emit('move', p)"
      />

      <!-- The spec's bounded, focusable remembered-remote-node list (outside
           the coordinate canvas): each entry keeps its non-color diamond
           state indicator and selects (focuses) the node without emitting a
           travel action. -->
      <ul v-if="remembered.length" class="local-map__remembered" data-testid="local-map-remembered" ref="rememberedEl">
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

      <p class="local-map__detail" data-testid="local-map-detail" ref="detailEl">
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
  /* The island keeps its natural content height (design D9/D10): a flex item
     with min-height:0 + flex-shrink:1 let the capped hud-right anchor
     compress it to the meta row, pushing the canvas/legend/detail below the
     island's box. min-height:auto makes the island size to its content; when
     the content outgrows the anchor's height budget, the anchor scrolls
     (overflow-y:auto) instead of the island being crushed. */
  min-height: auto;
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

/* The full-map trigger (H5, task 6.2): a small labelled control right-aligned
   in the island's meta row, sibling of the lattice — never a wrapper around
   the actionable move nodes. */
.local-map__expand {
  margin-left: auto;
  padding: 2px var(--sp-2);
  color: var(--gold-400);
  background: transparent;
  border: var(--line);
  border-radius: var(--radius-sm);
  font-family: var(--f-mono);
  font-size: 10px;
  letter-spacing: 0.06em;
  cursor: pointer;
}

.local-map__expand:hover {
  color: var(--paper-50);
  border-color: var(--gold-400);
}

.local-map__expand:focus-visible {
  color: var(--paper-50);
  border-color: var(--gold-400);
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

/* The remembered list's plain-text label spans keep the lattice label
   metrics (the extraction moved this rule into MapLattice's scoped CSS,
   which no longer reaches the island's own list items): without it the
   spans inherit the item's 13px font and grow every list row by 3px,
   breaking the crowding fix's no-scroll guarantee at small viewports. */
.local-map__node-label {
  fill: var(--paper-300);
  font-family: var(--f-mono);
  font-size: 11px;
  pointer-events: none;
}
</style>
