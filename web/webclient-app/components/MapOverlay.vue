<script setup>
// MapOverlay (webclient-full-map-fit-view design D2/D3/D5/D7): the body
// content of the shared full-screen overlay surface (H5,
// webclient-hud-05-overlays-and-command-line). The modal chrome (position,
// z-index, close button, aria-modal) belongs to the OverlayHost surface;
// this component renders only the `local_map` payload's branch — the
// available map (reused MapLattice opened through its fitted view, so the
// whole drawing shows inside the body and the reader zooms instead of
// scrolling) or the registry-owned unavailable reason. The guide row carries
// the view toolbar (縮小 / 放大 / 置中) and the legend disclosure; the state
// legend lives only in this surface's `?` popover (design D5). The host's
// focus trap and the labelled close control own the surface's chrome; this
// root handles Escape-while-the-popover-is-open (the popover is the topmost
// Escape level, design D5) and the `+` / `-` zoom keys. Actionable adjacent
// nodes forward a `move` event so the C-wire store can consume the OOB
// `explore.move` intent.
import { computed, ref, useId } from "vue";
import MapLattice from "./MapLattice.vue";

const props = defineProps({
  // The committed `local_map` v1 panel payload (the available form or the
  // registry-owned unavailable form). A replaced payload re-renders the
  // matching branch live (the delta's read-model-update requirement).
  localMap: { type: Object, required: true },
});

const emit = defineEmits(["move", "open-map"]);

// Reactive to OOB read-model updates: when the `local_map` payload is
// replaced (e.g. the C-wire store publishes a new snapshot), the body
// re-renders the available/unavailable branch instead of showing a stale
// state.
const available = computed(() => props.localMap.available === true);
const reasonMessage = computed(() => props.localMap.reason?.message ?? "");
const remembered = computed(() => (Array.isArray(props.localMap.remembered) ? props.localMap.remembered : []));
const isGraph = computed(() => (props.localMap.layoutVariant || "lattice") === "graph");

// The shared lattice instance, source of the exposed view controls
// (zoomIn / zoomOut / recentre and their can-flags).
const latticeRef = ref(null);

// The legend popover (design D5): closed every time the overlay opens; the
// legend is this surface's only legend surface.
const legendOpen = ref(false);
const legendToggleEl = ref(null);
const legendPopoverEl = ref(null);
const legendPopoverId = useId();
const legend = computed(() =>
  Array.isArray(props.localMap.legend) ? props.localMap.legend : [],
);

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

// Root keyboard handling (design D3/D5): this handler runs before the
// OverlayHost section handler in bubble order. Escape while the popover is
// open closes only the popover and stops propagation, so the overlay stays
// open and the document keyboard router never sees the key. `+` / `=` zoom
// in and `-` zoom out about the viewport centre; a modifier held means the
// reader is driving browser page zoom, so the key passes through untouched.
function onKeydown(event) {
  if (event.key === "Escape") {
    if (legendOpen.value) {
      legendOpen.value = false;
      event.stopPropagation();
    }
    return;
  }
  if (event.ctrlKey || event.metaKey || event.altKey) return;
  if (event.key === "+" || event.key === "=" || event.key === "Add") {
    event.preventDefault();
    latticeRef.value?.zoomIn();
  } else if (event.key === "-" || event.key === "_" || event.key === "Subtract") {
    event.preventDefault();
    latticeRef.value?.zoomOut();
  }
}

// A pointer press inside the overlay but outside both the popover and its
// toggle closes the popover without consuming the event, so the press still
// reaches the map (a drag or a node click keeps working, design D5).
function onPointerDownOutside(event) {
  if (!legendOpen.value) return;
  const target = event.target;
  if (legendPopoverEl.value?.contains(target) || legendToggleEl.value?.contains(target)) {
    return;
  }
  legendOpen.value = false;
}

function toggleLegend() {
  legendOpen.value = !legendOpen.value;
}

// Re-emit LocalMap's move intent ({ exit_ref, destination }) so the C-wire
// store can consume the OOB explore.move action.
function handleMove(payload) {
  emit("move", payload);
}

// The `open-map` emit is kept for the parent's overlay slice (AppClient's
// `onMapExpand`); the expand trigger now lives only in the island's chrome
// (`LocalMap.vue`), so the overlay body itself no longer re-emits it.
</script>

<template>
  <div
    class="map-overlay-body"
    data-testid="map-overlay"
    @keydown="onKeydown"
    @pointerdown.capture="onPointerDownOutside"
  >
    <p
      v-if="!available"
      class="map-overlay__unavailable"
      data-testid="map-overlay-unavailable"
    >
      {{ reasonMessage }}
    </p>
    <div v-else class="map-overlay__content" data-testid="map-overlay-content">
      <div class="map-overlay__guide">
        <p>點選可通行的相鄰節點，繼續探索。</p>
        <span>Tab 切換路徑 · Enter 確認移動 · 滾輪或 +／− 縮放 · 拖曳平移</span>
        <div class="map-overlay__toolbar" role="group" aria-label="地圖檢視">
          <button
            type="button"
            class="map-overlay__view-button"
            data-testid="map-overlay-zoom-out"
            aria-label="縮小"
            :aria-disabled="!latticeRef?.canZoomOut"
            @click="latticeRef?.zoomOut()"
          >−</button>
          <button
            type="button"
            class="map-overlay__view-button"
            data-testid="map-overlay-zoom-in"
            aria-label="放大"
            :aria-disabled="!latticeRef?.canZoomIn"
            @click="latticeRef?.zoomIn()"
          >+</button>
          <button
            type="button"
            class="map-overlay__view-button"
            data-testid="map-overlay-recentre"
            :aria-disabled="!latticeRef?.canRecentre"
            @click="latticeRef?.recentre()"
          >置中</button>
          <button
            ref="legendToggleEl"
            type="button"
            class="map-overlay__view-button"
            data-testid="map-overlay-legend-toggle"
            aria-label="圖例"
            :aria-expanded="legendOpen"
            :aria-controls="legendPopoverId"
            @click="toggleLegend"
          >?</button>
        </div>
      </div>
      <!-- The viewport cell takes every row the guide and the remembered
           list leave (design D7), and the lattice fills it through its
           fitted view (design D1): the whole drawing opens inside this box,
           clipped, and zoom windows it. The legend popover floats over the
           top-right corner here, inside this cell's stacking context, and
           takes no layout space (design D5). -->
      <div class="map-overlay__viewport">
        <MapLattice
          ref="latticeRef"
          :local-map="localMap"
          :variant="localMap.layoutVariant || 'lattice'"
          :col-pitch="280"
          :row-pitch="212"
          :label-max="10"
          :label-font="14"
          :marker-scale="2.2"
          :fit-view="true"
          :overlay-chrome="true"
          :marker-names="true"
          :marker-name-font="11"
          @move="handleMove"
        />
        <div
          v-if="legendOpen"
          ref="legendPopoverEl"
          :id="legendPopoverId"
          class="map-overlay__legend-popover"
          data-testid="map-overlay-legend-popover"
          role="group"
          aria-label="圖例"
        >
          <!-- The draft dot-chip state legend (webclient-map-01-draft-chrome
               D6, moved here by webclient-full-map-fit-view D5): an 11px
               radius-3 colour chip paired with its text label. The chip
               border style carries non-colour redundancy — the remembered
               chip's dashed border differs from the visited chip's solid
               border (delta scenario "Legend chips stay text-labelled at
               both scales"). -->
          <ul class="local-map__legend" data-testid="local-map__legend">
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
        </div>
      </div>
      <!-- Graph variant remembered nodes list (design D5): the grid's third
           row, full width, wrapping, never scrolling on its own (D7). -->
      <ul
        v-if="isGraph && remembered.length"
        class="map-overlay__remembered"
        data-testid="map-overlay-remembered"
        aria-label="記得的地點"
      >
        <li
          v-for="node in remembered"
          :key="node.id"
          class="map-overlay__remembered-item"
        >
          <svg
            class="map-overlay__remembered-marker"
            viewBox="-16 -16 32 32"
            width="14"
            height="14"
            aria-hidden="true"
          >
            <rect x="-7" y="-7" width="14" height="14" transform="rotate(45)" />
          </svg>
          <span class="map-overlay__remembered-label">{{ node.label }}</span>
        </li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.map-overlay-body {
  height: 100%;
  min-height: 360px;
}

.map-overlay__unavailable {
  margin: 0;
  padding: var(--sp-2) var(--sp-3);
  color: var(--paper-300);
  background: var(--panel-hi);
  border: 1px dashed var(--warn);
  border-radius: var(--radius-sm);
  font-family: var(--f-mono);
  font-size: var(--text-sm);
}

/* The fitted-view body layout (design D7): guide row, the viewport taking
   every remaining pixel (floored at 240px), then the remembered list. A
   long remembered list shrinks the fitted scale instead of pushing the map
   below the fold. */
.map-overlay__content {
  display: grid;
  grid-template-rows: auto minmax(240px, 1fr) auto;
  gap: 20px;
  height: 100%;
}

.map-overlay__guide {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px 20px;
}

.map-overlay__guide p {
  margin: 0;
  color: var(--paper-100);
  font-family: var(--f-serif);
}

.map-overlay__guide span {
  color: var(--paper-300);
  font-size: 12px;
}

.map-overlay__toolbar {
  display: flex;
  align-items: center;
  gap: var(--sp-1);
}

/* View buttons never use the `disabled` attribute (design D3): a bound
   control carries aria-disabled and keeps focus inside the trap. */
.map-overlay__view-button {
  min-width: 28px;
  padding: 2px var(--sp-2);
  border: var(--line);
  border-radius: var(--radius-sm);
  background: var(--panel-hi);
  color: var(--paper-100);
  font-family: var(--f-mono);
  font-size: var(--text-sm);
  line-height: 1.4;
  cursor: pointer;
}

.map-overlay__view-button[aria-disabled="true"] {
  color: var(--paper-500);
  cursor: default;
}

.map-overlay__viewport {
  position: relative;
  min-height: 0;
}

/* The legend popover (design D5): floats over the top-right of the map
   viewport inside this cell's stacking context and takes no layout space.
   Its z-index is local to the cell. */
.map-overlay__legend-popover {
  position: absolute;
  top: var(--sp-2);
  right: var(--sp-2);
  z-index: 1;
  max-width: min(100%, 480px);
  box-sizing: border-box;
  padding: var(--sp-2) var(--sp-3);
  border: var(--line);
  border-radius: var(--radius);
  background: var(--ink-900);
  box-shadow: 0 4px 16px #0006;
}

/* The draft dot-chip legend (webclient-map-01-draft-chrome D6): an 11px
   radius-3 chip + 11px text label, 14px gap, no bordered pill. The text
   labels stay the non-colour indicator; remembered (dashed) vs visited
   (solid) chip borders add a non-colour distinction between those two
   entries. Moved here from map-lattice.css with the popover (task 4.2);
   this surface is the legend's only renderer. */
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

.map-overlay__content :deep(.local-map__lattice--canvas) {
  border-color: var(--gold-500);
  box-shadow: inset 0 0 60px #0005;
}

.map-overlay__remembered {
  width: 100%;
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-2);
  margin: 0;
  padding: 0;
  list-style: none;
  box-sizing: border-box;
}

.map-overlay__remembered-item {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-1);
  padding: 2px var(--sp-2);
  border: var(--line);
  border-radius: var(--radius-sm);
  color: var(--paper-300);
  font-size: var(--text-sm);
}

.map-overlay__remembered-marker rect {
  fill: var(--paper-500);
}

.map-overlay__remembered-label {
  color: var(--paper-300);
  font-family: var(--f-mono);
  font-size: 11px;
}
</style>
