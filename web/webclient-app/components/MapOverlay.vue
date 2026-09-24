<script setup>
// MapOverlay (webclient-full-map-fit-view design D2/D3/D5/D7): the body
// content of the shared full-screen overlay surface (H5,
// webclient-hud-05-overlays-and-command-line). The modal chrome (position,
// z-index, close button, aria-modal) belongs to the OverlayHost surface;
// this component renders only the `local_map` payload's branch — the
// available map (reused MapLattice opened through its fitted view, so the
// whole drawing shows inside the body and the reader zooms instead of
// scrolling) or the registry-owned unavailable reason. The guide row is a
// text caption; the view toolbar (縮小 / 放大 / 置中) and the legend
// disclosure float over the map's top-right corner as one control pill, and
// the state legend lives only in that pill's `?` popover (design D5). The host's
// focus trap and the labelled close control own the surface's chrome; this
// root handles Escape-while-the-popover-is-open (the popover is the topmost
// Escape level, design D5) and the `+` / `-` zoom keys. Actionable adjacent
// nodes forward a `move` event so the C-wire store can consume the OOB
// `explore.move` intent.
import { computed, onBeforeUnmount, onMounted, ref, useId } from "vue";
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

// Root element, used to find the host overlay `<section>` to key-bind on.
const rootEl = ref(null);

// Root keyboard handling (design D3/D5): this handler runs before the
// OverlayHost section handler in dispatch order. Escape while the popover is
// open closes only the popover and stops propagation, so the overlay stays
// open and the document keyboard router never sees the key. `+` / `=` zoom
// in and `-` zoom out about the viewport centre; a modifier held means the
// reader is driving browser page zoom, so the key passes through untouched.
// It is bound in capture on the host `<section>` — not on this body root —
// because the delta states the keys while focus is anywhere *inside the
// overlay*: focus lands on the host's close button when the surface opens,
// and a keydown from the header never passes through this body root at all.
// The capture phase on the section precedes OverlayHost's own bubble handler,
// so `stopPropagation` here still keeps Escape out of the surface close.
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

// The section to bind on: the mounted host when present (every product
// mount), else this component's own root (the showcase/unit mounts, which
// have no host chrome around the body).
let boundSection = null;
onMounted(() => {
  boundSection = rootEl.value?.closest("[data-testid=\"overlay-host\"]") ?? rootEl.value;
  boundSection?.addEventListener("keydown", onKeydown, true);
});
onBeforeUnmount(() => {
  boundSection?.removeEventListener("keydown", onKeydown, true);
  boundSection = null;
});

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
    ref="rootEl"
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
        <!-- The view controls float over the map's top-right corner as one
             pill (zoom pair, 置中, legend), so they read as part of the map
             they drive; the legend popover drops from the pill. -->
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
          <span class="map-overlay__toolbar-sep" aria-hidden="true"></span>
          <button
            type="button"
            class="map-overlay__view-button"
            data-testid="map-overlay-recentre"
            :aria-disabled="!latticeRef?.canRecentre"
            @click="latticeRef?.recentre()"
          >置中</button>
          <span class="map-overlay__toolbar-sep" aria-hidden="true"></span>
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
            viewBox="-11 -11 22 22"
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
  grid-template-rows: auto minmax(240px, 1fr);
  /* The remembered list is an implicit third row, so a payload without it
     leaves no trailing gap under the viewport. */
  grid-auto-rows: auto;
  gap: var(--sp-3);
  height: 100%;
}

/* The caption row: the instruction in the serif voice on the left, the
   input hint as a quiet footnote at the right edge. The view controls live
   on the map itself (below), so this row carries text only. */
.map-overlay__guide {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--sp-1) var(--sp-4);
  padding: 0 var(--sp-1);
}

.map-overlay__guide p {
  margin: 0;
  color: var(--paper-100);
  font-family: var(--f-serif);
  font-size: var(--text-body);
  letter-spacing: 0.06em;
}

.map-overlay__guide span {
  color: var(--paper-500);
  font-size: var(--text-xs);
  letter-spacing: 0.04em;
}

/* The map frame: one hairline, the surface radius, and a soft inner shade.
   The SVG inside is borderless and clipped by this frame, so the fitted
   view spends exactly the frame's content box and no edge is ever cut. */
.map-overlay__viewport {
  position: relative;
  min-height: 0;
  overflow: hidden;
  border: var(--line);
  border-radius: var(--radius);
  background: var(--map-canvas-lo);
  box-shadow: inset 0 0 80px #0006;
}

.map-overlay__viewport :deep(.local-map__lattice--canvas) {
  border: 0;
  border-radius: 0;
}

/* The view controls: one floating glass pill in the map's top-right corner,
   grouped as zoom pair · 置中 · legend with hairline separators. */
.map-overlay__toolbar {
  position: absolute;
  top: var(--sp-3);
  right: var(--sp-3);
  z-index: 2;
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 3px;
  border: var(--line);
  border-radius: 999px;
  background: var(--panel);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  box-shadow: var(--shadow);
}

.map-overlay__toolbar-sep {
  width: 1px;
  height: 16px;
  margin: 0 3px;
  background: var(--ink-700);
}

/* View buttons never use the `disabled` attribute (design D3): a bound
   control carries aria-disabled and keeps focus inside the trap. */
.map-overlay__view-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  min-width: 30px;
  height: 30px;
  padding: 0 var(--sp-2);
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: var(--paper-200);
  font-family: var(--f-sans);
  font-size: var(--text-sm);
  letter-spacing: 0.08em;
  line-height: 1;
  cursor: pointer;
  transition:
    background-color var(--motion-fast) var(--ease-standard),
    color var(--motion-fast) var(--ease-standard);
}

/* The two zoom glyphs are drawn a step larger than the label text so the
   pair reads as symbols rather than punctuation. */
.map-overlay__view-button[data-testid="map-overlay-zoom-out"],
.map-overlay__view-button[data-testid="map-overlay-zoom-in"] {
  font-size: 17px;
  letter-spacing: 0;
}

.map-overlay__view-button:hover:not([aria-disabled="true"]) {
  background: var(--panel-hi);
  color: var(--gold-300);
}

.map-overlay__view-button[aria-expanded="true"] {
  background: var(--gold-glow);
  color: var(--gold-400);
}

.map-overlay__view-button:focus-visible {
  outline: 2px solid var(--gold-400);
  outline-offset: -2px;
}

.map-overlay__view-button[aria-disabled="true"] {
  color: var(--paper-700);
  cursor: default;
}

/* The legend popover (design D5): drops from the control pill's right edge,
   floats over the map inside this cell's stacking context, and takes no
   layout space. */
.map-overlay__legend-popover {
  position: absolute;
  top: calc(var(--sp-3) + 44px);
  right: var(--sp-3);
  z-index: 2;
  max-width: calc(100% - 2 * var(--sp-3));
  box-sizing: border-box;
  padding: var(--sp-3) var(--sp-4);
  border: var(--line);
  border-radius: var(--radius);
  background: var(--panel);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  box-shadow: var(--shadow-lg);
}

/* The draft dot-chip legend (webclient-map-01-draft-chrome D6): an 11px
   radius-3 chip + 11px text label, 14px gap, no bordered pill. The text
   labels stay the non-colour indicator; remembered (dashed) vs visited
   (solid) chip borders add a non-colour distinction between those two
   entries. Moved here from map-lattice.css with the popover (task 4.2);
   this surface is the legend's only renderer. */
.local-map__legend {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.local-map__legend-item {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-2);
  color: var(--paper-300);
  font-size: 12px;
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

/* The graph variant's remembered rooms (C1 D5): a quiet caption row under
   the map — a small-caps style lead-in, then each room as a dashed diamond
   (the legend's remembered glyph) and its full name. Plain text, no boxes:
   the entries are not controls. */
.map-overlay__remembered {
  width: 100%;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--sp-2) var(--sp-4);
  margin: 0;
  padding: 0 var(--sp-1);
  list-style: none;
  box-sizing: border-box;
}

.map-overlay__remembered::before {
  /* Visible lead-in only; the list's aria-label already names it. */
  content: "記得的地點" / "";
  color: var(--paper-500);
  font-size: var(--text-xs);
  letter-spacing: 0.12em;
}

.map-overlay__remembered-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.map-overlay__remembered-marker rect {
  fill: var(--map-canvas-hi);
  stroke: var(--gold-500);
  stroke-width: 1.5;
  stroke-dasharray: 3 2;
}

.map-overlay__remembered-label {
  color: var(--paper-300);
  font-family: var(--f-sans);
  font-size: var(--text-sm);
  letter-spacing: 0.04em;
}
</style>
