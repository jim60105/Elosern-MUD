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
// Since slim-minimap-island the island passes the renderer's legend switch
// off, so the state legend is an overlay-only presentation.
//
// The island chrome (webclient-minimap-04-island-single-affordance):
// - The single full-map affordance is a full-bleed transparent <button>
//   layered beneath the island's visual content. It is the island's first
//   DOM child so keyboard Tab reaches the primary action before the
//   remembered list's focusable items.
// - No hover or selection state is tracked; the readout is a pure function
//   of the committed payload's current node (design D3/D6).
// - The readout states only `座標 x,y` on coordinate-bearing layers
//   (grid/wilderness); nothing on coordinate-free layers.
import { computed, onMounted, onUpdated, ref } from "vue";
import LocalMap from "../lib/local_map.js";
import MapLattice from "./MapLattice.vue";

const props = defineProps({
  // The committed `local_map` v1 panel payload (available form or the
  // registry-owned unavailable form).
  localMap: { type: Object, required: true },
});

const emit = defineEmits(["move", "open-map"]);

const available = computed(() => props.localMap.available === true);
const reason = computed(() => props.localMap.reason?.message ?? "");
const title = computed(() => props.localMap.title ?? "");
const layer = computed(() => props.localMap.layer ?? null);
const nodes = computed(() => (Array.isArray(props.localMap.nodes) ? props.localMap.nodes : []));
const remembered = computed(() => (Array.isArray(props.localMap.remembered) ? props.localMap.remembered : []));

// The orientation legend states the renderer's own axis convention only
// (design D9): the lattice renderer puts north at +y and inverts y so +y
// draws upward — a statement about the drawing, not about the world. The
// radial graph variant has no axis convention to state, so the legend
// follows the resolved layout variant (map-02), not the payload layer.
const showsOrientation = computed(
  () => props.localMap.layoutVariant === "lattice",
);
const isGraph = computed(
  () => (props.localMap.layoutVariant || "lattice") === "graph",
);
const showsRememberedList = computed(
  () => isGraph.value && remembered.value.length > 0,
);

const OCTANT_WORDS = ["北", "東北", "東", "東南", "南", "西南", "西", "西北"];

const islandEdgeMarkers = computed(() => {
  if (isGraph.value || remembered.value.length === 0) {
    return { markers: [], gutter: 0, width: 0, height: 0 };
  }
  const current = nodes.value.find((node) => node.visibility === "current");
  if (!current || typeof current.x !== "number" || typeof current.y !== "number") {
    return { markers: [], gutter: 0, width: 0, height: 0 };
  }
  const cols = props.localMap.cols ?? 0;
  const rows = props.localMap.rows ?? 0;
  return LocalMap.edgeMarkersFor(nodes.value, remembered.value, {
    canvasWidth: Math.max(1, cols) * 40,
    canvasHeight: Math.max(1, rows) * 40 + 14,
    current: {
      x: (current.col ?? 0) * 40 + 20,
      y: (Math.max(1, rows) - 1 - (current.row ?? 0)) * 40 + 20,
    },
    markerHalf: 9,
    nameWidth: 0,
    nameHeight: 16,
  });
});

const markerMirrorList = computed(() => {
  if (isGraph.value || islandEdgeMarkers.value.markers.length === 0) return [];
  const payloadIndexById = new Map();
  remembered.value.forEach((node, idx) => {
    payloadIndexById.set(node.id, idx);
  });
  const items = islandEdgeMarkers.value.markers.map((marker) => ({
    id: marker.id,
    label: marker.name,
    octant: marker.octant,
    payloadIndex: payloadIndexById.get(marker.id) ?? 0,
    octantWord: OCTANT_WORDS[marker.octant] ?? "",
  }));
  items.sort((a, b) => a.octant - b.octant || a.payloadIndex - b.payloadIndex);
  return items;
});

// Coordinate readout (design D6): the island's position statement is the
// current node's two payload integers on the closed coordinate-bearing set
// (grid/wilderness), and nothing else. No hover/selection state is tracked
// (D3): the readout is a pure function of the committed payload's current
// node, so it follows the payload by construction rather than by a watcher,
// making every staleness path structurally impossible.
const detail = computed(() => {
  const currentId = props.localMap.currentNode;
  if (!currentId) return "";
  const node = nodes.value.find((n) => n.id === currentId);
  if (!node) return "";
  if (layer.value === "grid" || layer.value === "wilderness") {
    return `座標 ${node.x},${node.y}`;
  }
  return "";
});

// Dynamic canvas height budget (the crowding fix): a fixed 296px cap would
// ignore the rendered height of the island's other sections, so a tall
// lattice combined with a long remembered list would push required content
// into the anchor's overflow-y scroll fallback. Instead the canvas's
// max-height shrinks to the space the hud-right anchor's height budget
// leaves after the meta row, remembered list, and readout line; the computed
// cap is passed down to MapLattice as its `maxHeight` prop, which resolves it
// into the canvas's single width bound. (Since slim-minimap-island the legend
// is overlay-only, so it left both the section list and the gap count.) The
// budget's SOURCE is the fix documented on `anchorHeightBudget` below — the
// formula itself is unchanged, and stays ResizeObserver-driven: nothing here
// runs per frame.
const rootEl = ref(null);
const metaEl = ref(null);
const rememberedEl = ref(null);
const detailEl = ref(null);
const canvasMaxHeight = ref(0);

function sectionHeight(el) {
  return el ? Math.ceil(el.getBoundingClientRect().height) : 0;
}

// The clearance the island keeps between its own bottom edge and the dock
// anchor's top edge. It is what makes the measured budget strictly smaller
// than the anchor's CSS cap (`max-height: calc(100% - var(--dock-h) - 110px)`
// leaves 46px there, of which the 46px command line claims all), so the
// island can never grow into the anchor's `overflow-y` fallback.
const ANCHOR_BOTTOM_CLEARANCE = 12;

// The anchor's height budget: the room the anchor is ALLOWED to occupy, NOT
// the room it currently occupies. Reading `anchor.clientHeight` measured the
// latter and made the whole formula degenerate: `[data-anchor="hud-right"]`
// is an absolutely positioned box with `top` + `max-height` and no `height`,
// so while its content fits it is sized BY the island — and the island's
// height is dominated by the very canvas this budget caps. Substituting the
// island's own box back into the formula collapses it to
// `available = renderedCanvasHeight - 1`, a strictly decreasing map: every
// ResizeObserver pass shrank the canvas by a pixel, which shrank the anchor,
// which re-fired the observer, ratcheting the minimap down onto the 40px
// floor. Measuring from the island's top edge to the dock anchor's top edge
// reads only positions that do not move with the canvas, so the measurement
// is a fixed point instead of a ratchet.
function anchorHeightBudget(anchor) {
  const dock = anchor.parentElement?.querySelector('[data-anchor="dock"]');
  if (dock) {
    const room = Math.floor(
      dock.getBoundingClientRect().top -
        anchor.getBoundingClientRect().top -
        ANCHOR_BOTTOM_CLEARANCE,
    );
    if (room > 0) return room;
  }
  // Bare mount outside the shell (component tests, Storybook): fall back to
  // the anchor's own box, which in that context is authored, not island-fed.
  return anchor.clientHeight;
}

function measureCanvasBudget() {
  const root = rootEl.value;
  if (!root) return;
  // Island context only: the full-map overlay renders the lattice outside
  // the hud-right anchor, so it keeps the prop caps.
  const anchor = root.closest('[data-anchor="hud-right"]');
  if (!anchor) return;
  const budget = anchorHeightBudget(anchor);
  if (!budget) return;
  // Sections actually laid out (design D6): meta and canvas are always laid
  // out; at most one of {graph-variant remembered list, coordinate readout}
  // is laid out.
  let laidOutSections = 2;
  if (showsRememberedList.value) laidOutSections += 1;
  if (detail.value !== "") laidOutSections += 1;
  const gapCount = laidOutSections - 1;
  const others =
    sectionHeight(metaEl.value) +
    sectionHeight(rememberedEl.value) +
    sectionHeight(detailEl.value);
  const available = budget - others - gapCount * 8 - 18 - 2 - 4 - 1;
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

// Pointer-click convenience (webclient-map-01-draft-chrome D5): clicking the
// island's non-interactive body opens the full map. A click that originated
// in an interactive descendant — the full-bleed affordance button (a <button>),
// a lattice node group (carrying `data-node`), its actionable halo, or a
// remembered-list item (`[tabindex]`) — runs only that control's own behavior.
// The root deliberately gains no role or tabindex: the full-bleed button is
// the only keyboard path, and the focus-restore contract captures it as the
// opener (design D2).
function onIslandClick(event) {
  if (!available.value) return;
  if (event.target?.closest?.("button, a, [tabindex], [data-node]")) return;
  emit("open-map");
}
</script>

<template>
  <aside class="local-map" data-testid="local-map" ref="rootEl" @click="onIslandClick">
    <p v-if="!available" class="local-map__unavailable" data-testid="local-map__unavailable">
      {{ reason }}
    </p>
    <template v-else>
      <!-- Single full-map affordance (webclient-minimap-04-island-single-affordance
           D1): a content-free <button> spanning the island's whole box,
           transparent and layered beneath the island's visual content so the
           button element itself contains no focusable descendant. It is a real
           <button> (Enter/Space via the platform, never a key handler on a
           div), carries 展開全地圖 as its accessible name, and is the island's
           FIRST DOM child so Tab reaches the primary action before the
           remembered list's focusable items.

           Pointer behaviour is unchanged and stays single-emit: content sits
           above this button, so a click on visible content targets that
           content and reaches onIslandClick, which emits open-map. A click on
           genuinely empty island area lands on this button, which emits
           open-map itself — and onIslandClick, which also sees that bubbling
           click, skips it because event.target.closest("button, …") matches
           this button. Keyboard activation produces the same bubbling click
           and is skipped by the same guard. So every path emits exactly one
           open-map, and a click originating in a lattice node group
           ([data-node]) or a remembered item ([tabindex]) still emits none. -->
      <button
        type="button"
        class="local-map__affordance"
        data-testid="local-map__expand"
        aria-label="展開全地圖"
        title="展開全地圖"
        @click="emit('open-map')"
      ></button>

      <!-- The island's top-meta line (design D9): the payload's title plus,
           on the coordinate-bearing layers only, the renderer's axis
           orientation marks in the draft's header treatment (`北↑ 東→`,
           webclient-map-01-draft-chrome). No bearing or distance is
           rendered.

           Header budget (the redesign review's first finding): the header
           carries no full-map control of its own — the single full-bleed
           affordance above is the island's only full-map affordance (D1),
           so the elastic title now owns the space the control occupied. -->
      <div class="local-map__meta" data-testid="local-map__title" ref="metaEl">
        <span class="local-map__meta-title" :title="title">{{ title }}</span>
        <span v-if="showsOrientation" class="local-map__orientation" data-testid="local-map__orientation">
          北↑ 東→
        </span>
      </div>

      <!-- Shared lattice renderer (improve-webclient-map-overlay-scale): the
           minimap composes MapLattice at its default (post-crowding-fix)
           scale; the dynamically measured height budget (the crowding fix)
           is passed down as the canvas cap.

           `fill-width` is the draft's `.mini svg { width: 100% }` rule: the
           canvas claims the island's whole content width instead of drawing
           at natural pixel size (REDESIGN §7 — the lattice's geometry IS its
           claim, so it must not be the smallest thing in the island). The
           scale is uniform through the viewBox, so the crowding fix's marker,
           label and gutter geometry stays proportional; coordinate-margin
           padding (`field-fill`) spends the width slack on coordinate space
           rather than magnification, keeping uniform scale <= 1.

           The island no longer listens to select/hover/leave (D3): the shared
           renderer keeps its event surface for the overlay and future changes
           to consume. -->
      <MapLattice
        :local-map="localMap"
        :variant="localMap.layoutVariant || 'lattice'"
        :max-height="canvasMaxHeight || 296"
        :fill-width="true"
        :col-pitch="40"
        :row-pitch="40"
        :label-font="9"
        :field-fill="true"
        :show-axis="true"
        :fog-vignette="true"
        :show-legend="false"
        :marker-names="true"
        @move="(p) => emit('move', p)"
      />

      <!-- Assistive technology mirror for edge direction markers (design D1):
           visually-hidden, non-focusable list ordered by octant then payload index,
           one entry per drawn marker. -->
      <ul
        v-if="markerMirrorList.length"
        class="visually-hidden"
        aria-label="已知的地圖出入口"
        data-testid="local-map-edge-markers-mirror"
      >
        <li v-for="marker in markerMirrorList" :key="marker.id">
          {{ marker.label }}，{{ marker.octantWord }}
        </li>
      </ul>

      <!-- The graph variant's bounded remembered list (design D4): scoped to
           coordinate-free layers (interior/instance), plain non-focusable text,
           no tabindex, no activation. Clicks bubble to onIslandClick. -->
      <ul v-if="showsRememberedList" class="local-map__remembered" data-testid="local-map-remembered" ref="rememberedEl">
        <li
          v-for="node in remembered"
          :key="node.id"
          class="local-map__node local-map__node--remembered"
          :data-testid="`local-map__node--${node.id}`"
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

      <!-- The island's closing readout line, in the draft `.mini .compass`
           treatment (design D7): the island's smallest type step, monospace,
           centred, de-emphasised (--paper-500, 4.98:1 on --panel), with no
           border, background, or padded box. The element itself stays
           unconditionally mounted — `local-map-detail` is a committed testid
           and the island's plain-text body click target. On coordinate-free
           layers (interior/instance) there is no coordinate figure, so the
           readout states nothing and paints no box (the --empty modifier). -->
      <p
        class="local-map__detail"
        :class="{ 'local-map__detail--empty': detail === '' }"
        data-testid="local-map-detail"
        ref="detailEl"
      >
        {{ detail }}
      </p>
    </template>
  </aside>
</template>

<style scoped>
/* The island chrome (design D9): the shared tokens, so a token change or
   the reduced-motion block reaches it at once. The root keeps the
   load-bearing `.local-map` class that H1's mode-gate CSS selects on.

   `position: relative` (webclient-minimap-04-island-single-affordance D1):
   the full-bleed affordance is `position: absolute; inset: 0`, so the
   island must establish a positioning context. */
.local-map {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  box-sizing: border-box;
  /* The island keeps its natural content height (design D9/D10): a flex item
     with min-height:0 + flex-shrink:1 let the capped hud-right anchor
     compress it to the meta row, pushing the canvas/remembered/detail below the
     island's box. min-height:auto makes the island size to its content; when
     the content outgrows the anchor's height budget, the anchor scrolls
     (overflow-y:auto) instead of the island being crushed. */
  min-height: auto;
  /* The island claims the anchor's full 230px column. The hud-right anchor is
     `align-items: flex-end`, so without this the island is shrink-to-fit and
     its width is decided by whichever row happens to be widest — the map card
     changed width with the authored title's length, and a short title left the
     canvas even less room to fill. A minimap is a fixed station in the HUD
     (hud-systems: anchor to the corner, keep positions stable), so its card
     width is a constant, not a function of the payload. */
  width: 100%;
  padding: 9px;
  background: var(--panel);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border: var(--line);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  font-family: var(--f-sans);
  /* Draft `.mini` affordance (webclient-map-01-draft-chrome D5): the whole
     island reads as clickable because the body click opens the full map;
     the interactive descendants keep their own cursors. */
  cursor: pointer;
}

.local-map:hover {
  border-color: var(--ink-600);
}

/* Single full-map affordance (D1): a content-free transparent button
   spanning the island's whole box, layered beneath the island's visual
   content at z-index 0. Every other direct child is raised to z-index 1 so
   a future island child is elevated by construction rather than by opt-in. */
.local-map__affordance {
  position: absolute;
  inset: 0;
  z-index: 0;
  padding: 0;
  border: 0;
  background: transparent;
  cursor: pointer;
  border-radius: var(--radius);
}

/* Focus indication on the whole island (D1): the affordance IS the island's
   box, so :focus-visible draws a ring around the entire island. A box-shadow
   renders in the paint phase and is not affected by the z-index stack, so it
   is always visible above the island's content layers. The inset offset keeps
   the ring inside the card's border-radius without clipping. */
.local-map__affordance:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px var(--gold-400) inset;
}

/* Every direct child except the affordance is raised above it, so
   their clicks target the visible content and reach onIslandClick, and the
   affordance only receives clicks on genuinely empty island area (padding,
   the flex gaps between sections). */
.local-map > *:not(.local-map__affordance) {
  position: relative;
  z-index: 1;
}

/* The draft `.mini .mt` header row, re-budgeted for authored payload titles.
   `justify-content: space-between` is gone: with three items that all want to
   be wider than the row, "space between" only decides where the wrapping
   happens. An explicit gap plus one elastic item does the real job. */
.local-map__meta {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  font-size: 10px;
  letter-spacing: 0.12em;
  color: var(--paper-500);
  margin-bottom: 4px;
}

/* The one elastic item in the row, and the only localization-safe container
   it needs: any authored title (`{room.key}街道圖`, `{room.key}空間平面圖`, a
   longer translation) stays on one line and ellipsizes rather than reflowing
   the header. `min-width: 0` is what actually permits the shrink — a flex
   item's default `min-width: auto` floors it at its own max-content width,
   which is precisely how a 9-glyph title used to push the row into a wrap.
   The full string stays available through the element's `title`. */
.local-map__meta-title {
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  color: var(--paper-300);
}

/* The renderer-axis orientation legend (北↑): a statement about the
   drawing's axis convention, not about the world (design D9). Fixed-size:
   the marks are a two-token convention, never a wrapping phrase. */
.local-map__orientation {
  flex: none;
  white-space: nowrap;
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

/* The draft `.mini .compass` readout treatment (design D7): the island's
   smallest type step, monospace from the shared font token, centred, at the
   de-emphasised paper tier (--paper-500, 4.98:1 on --panel — WCAG AA for
   body text), separated from the canvas by a step from the shared spacing
   scale (padding-top: --sp-1, so the measured height includes the gap),
   with no border, background fill, or padded box. No draft hex value and no
   draft-canvas pixel literal are hardcoded. The line states the current
   node's two payload integers only; nothing for a hovered or selected node. */
.local-map__detail {
  margin: 0;
  padding-top: var(--sp-1);
  color: var(--paper-500);
  font-family: var(--f-mono);
  font-size: 11px;
  line-height: 1.45;
  text-align: center;
  overflow-wrap: anywhere;
}

/* An island with no coordinate figure on the current layer states nothing
   rather than reserving a blank line (and, with it, a blank slot in the
   height budget — `sectionHeight` reads 0 for a display:none section). */
.local-map__detail--empty {
  display: none;
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

.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  margin: -1px;
  padding: 0;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
  border: 0;
}

.local-map :deep(.local-map__lattice) {
  pointer-events: none;
}

.local-map :deep(.local-map__node) {
  pointer-events: auto;
}

</style>
