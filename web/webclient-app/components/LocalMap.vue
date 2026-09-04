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
// off, so the state legend is an overlay-only presentation. The island
// keeps its chrome: the meta row (title + orientation marks + the compact
// "展開全地圖" expand button), the bounded focusable remembered-node list, and
// the hovered/selected-node readout line driven by the lattice's
// `select`/`hover`/`leave` events.
import { computed, onMounted, onUpdated, ref, watch } from "vue";
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

function nodeWithId(id) {
  if (id == null) return null;
  // The active node may be an in-view lattice node or a remembered remote
  // node (the bounded focusable list), so search both collections.
  return (
    nodes.value.find((n) => n.id === id) ??
    remembered.value.find((n) => n.id === id) ??
    null
  );
}

// Re-seed the selection when the player moves. `selectedId` was seeded once
// at setup, but the island is re-rendered with a REPLACED payload on every
// move (the store swaps `localMapModel` wholesale), so after one move the
// held id named the previous room — a node the new payload frequently no
// longer carries at all. The readout then resolved to nothing and the island
// showed an empty line, which is the "empty detail bar" the redesign review
// caught. Following the payload's own `currentNode` restores the documented
// default (the readout describes where you are) without touching the manual
// selection made inside one payload.
watch(
  () => props.localMap.currentNode,
  (id) => {
    selectedId.value = id ?? null;
    hoveredId.value = null;
  },
);

const activeNode = computed(() => {
  const id = hoveredId.value ?? selectedId.value;
  // Second guard for the same class of staleness: a targeted panel update can
  // drop the selected node while `currentNode` itself is unchanged (the room
  // is the same, its visible neighbours are not). Falling back to the current
  // node keeps the readout truthful instead of blank.
  return nodeWithId(id) ?? nodeWithId(props.localMap.currentNode) ?? null;
});

const detailParts = computed(() => {
  const node = activeNode.value;
  if (!node) return [];
  const parts = [node.label, STATE_LABELS[node.visibility] ?? node.visibility];
  if (node.action) parts.push(`→ ${node.action.destination}`);
  // Current-node coordinate readout (slim-minimap-island D2): on the
  // closed coordinate-bearing set the payload x/y are validated world
  // coordinates, and the island's position statement is the header's axis
  // orientation marks plus exactly this one figure — the current node's
  // two payload integers, no unit, delta, or derived quantity. Any other
  // active node, any other layer, and the overlay never gain a coordinate
  // figure (the ban stays verbatim outside this single part).
  if (node.current && (layer.value === "grid" || layer.value === "wilderness")) {
    parts.push(`座標 ${node.x},${node.y}`);
  }
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
  // 4 island sections (meta, canvas, remembered list when non-empty,
  // detail) separated by 8px (--sp-2) gaps. Fixed chrome (25px): 18px
  // island padding (9px top + 9px bottom), the canvas element's 2px
  // border, the meta row's 4px margin-bottom outside its own bounding
  // box, and 1px of rounding slack so the island never needs to scroll
  // a required surface. The island's own 1px border-box border is
  // deliberately not reserved: reserving it (rubber-duck run 2) cost
  // the canvas 2px and regressed the dense-lattice >=2px separation
  // contract, while the resulting <=1px scroll range stays inside the
  // +1px sub-pixel tolerance the browser budget tests enforce.
  const gapCount = 2 + (remembered.value.length > 0 ? 1 : 0);
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
// in an interactive descendant — the expand button, a lattice node group
// (carrying `data-node`), its actionable halo, or a remembered-list item
// (`[tabindex]`) — runs only that control's own behavior. The root
// deliberately gains no role or tabindex: the labelled expand sibling stays
// the only keyboard path, so the focus-restore contract is untouched.
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
      <!-- The island's top-meta line (design D9): the payload's title plus,
           on the coordinate-bearing layers only, the renderer's axis
           orientation marks in the draft's header treatment (`北↑ 東→`,
           webclient-map-01-draft-chrome). No bearing or distance is
           rendered.

           Header budget (the redesign review's first finding): three text
           items sharing one `space-between` row could not fit the island's
           210px content box — a real title is authored server-side as
           `f"{room.key}街道圖"`, so 冒險者公會外街道圖 alone is ~101px next to
           the ~46px axis marks and the ~71px labelled button, and all three
           wrapped onto second lines. The row is re-budgeted instead of
           re-sized: the title is the one elastic item (single line, ellipsis,
           `min-width: 0`) so ANY authored length is safe, the axis marks and
           the trigger are fixed-size, and the trigger drops to its glyph. -->
      <div class="local-map__meta" data-testid="local-map__title" ref="metaEl">
        <span class="local-map__meta-title" :title="title">{{ title }}</span>
        <span v-if="showsOrientation" class="local-map__orientation" data-testid="local-map__orientation">
          北↑ 東→
        </span>
        <!-- H5 (task 6.2): the island's full-map trigger, a sibling of the
             lattice on the island's header row (H2's deferred affordance now
             that the full-map surface is reachable). Opening the map overlay
             routes through the parent's overlay slice.

             The draft shows NO button at all — its whole `.mini` is clickable
             with `title="展開全地圖"` — which is a pointer-only affordance. The
             island keeps the real <button> (it is the only keyboard path to
             the overlay, and the focus-restore contract restores focus onto
             it), and reconciles with the draft by spending header width like
             the draft does: the visible text becomes the expand glyph while
             `aria-label` keeps the full name for assistive tech and `title`
             keeps it for pointer users. -->
        <button
          type="button"
          class="local-map__expand"
          data-testid="local-map__expand"
          aria-label="展開全地圖"
          title="展開全地圖"
          @click="emit('open-map')"
        >
          <svg
            class="local-map__expand-icon"
            viewBox="0 0 24 24"
            width="12"
            height="12"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
          >
            <path d="M9 3H3v6M15 3h6v6M9 21H3v-6M15 21h6v-6" />
          </svg>
        </button>
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
           label and gutter geometry stays proportional; `max-upscale` bounds
           it so a one-room payload cannot blow that ramp up ~3.5x. -->
      <MapLattice
        :local-map="localMap"
        :variant="localMap.layoutVariant || 'lattice'"
        :max-height="canvasMaxHeight || 296"
        :fill-width="true"
        :max-upscale="2"
        :show-legend="false"
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

      <!-- The island's closing readout line, in the draft `.mini .compass`
           treatment (small centred mono under the canvas) rather than the
           bordered box the review flagged: a box drawn around a line that can
           legitimately be empty reads as a broken widget, while an unboxed
           line just is not there. The element itself stays unconditionally
           mounted — `local-map-detail` is a committed testid and the island's
           plain-text body click target. -->
      <p
        class="local-map__detail"
        :class="{ 'local-map__detail--empty': detailParts.length === 0 }"
        data-testid="local-map-detail"
        ref="detailEl"
      >
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

/* The full-map trigger (H5, task 6.2): a compact square control at the end of
   the island's meta row, sibling of the lattice — never a wrapper around the
   actionable move nodes. Sized to a 24px target (WCAG 2.2 target-size floor)
   so dropping the visible label costs nothing in pointer accuracy, and fixed
   (`flex: none`) so it is never the thing that shrinks.

   Deliberately NOT the shared `.ui-icon-btn` primitive: that control is the
   draft's 34px `.closebtn` at chrome weight (filled ink chip, seal hover),
   and 34px is both taller than this 10px header row and 24px wider than the
   row has to spend — the very budget this change went to recover. Routing it
   through the control layer wants a small variant of that primitive, which is
   a tokens.css decision, not an island one. */
.local-map__expand {
  flex: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  min-width: 24px;
  min-height: 24px;
  padding: 0;
  color: var(--gold-400);
  background: transparent;
  border: var(--line);
  border-radius: var(--radius-sm);
  cursor: pointer;
}

/* The glyph never becomes the click target: `onIslandClick` skips clicks that
   originate inside a button, and keeping the SVG out of hit-testing means the
   button element is always `event.target` — the same reason the lattice's own
   decorative layers disable pointer events. */
.local-map__expand-icon {
  display: block;
  pointer-events: none;
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

/* The draft `.mini .compass` readout treatment: a small centred mono line
   closing the island, no box. Sitting at the canvas's own 11px label size
   keeps the island on one type ramp (10px meta / 11px canvas + list / 11px
   readout) and buys back the two lines the 13px boxed version cost at 230px.
   It is plain text, so it stays part of the island's click-to-open body.
   The draft's own `.compass` is `--paper-500` (4.98:1 on the panel) because it
   states a constant drawing name; this line states the live node, its state
   and, on a coordinate layer, its coordinates, so it keeps the shipped
   `--paper-300` (9.58:1) — only the box goes away, not the legibility. */
.local-map__detail {
  margin: 0;
  color: var(--paper-300);
  font-family: var(--f-mono);
  font-size: 11px;
  line-height: 1.45;
  text-align: center;
  overflow-wrap: anywhere;
}

/* An island with no resolvable active node states nothing rather than
   reserving a blank line (and, with it, a blank slot in the height budget —
   `sectionHeight` reads 0 for a display:none section). Every available
   payload carries a current node, so this is the degenerate branch, not the
   normal one. */
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
