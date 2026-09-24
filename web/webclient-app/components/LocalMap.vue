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
//   DOM child so keyboard Tab reaches the primary action.
// - No hover or selection state is tracked; the readout is a pure function
//   of the committed payload's current node (design D3/D6).
// - The readout states only `座標 x,y` on coordinate-bearing layers
//   (grid/wilderness); nothing on coordinate-free layers.
import { computed } from "vue";
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

// Pointer-click convenience (webclient-map-01-draft-chrome D5): clicking the
// island's non-interactive body opens the full map. A click that originated
// in an interactive descendant — the full-bleed affordance button (a <button>)
// or a lattice node group (carrying `data-node`) — runs only that control's own
// behavior.
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
  <aside class="local-map" data-testid="local-map" @click="onIslandClick">
    <p v-if="!available" class="local-map__unavailable" data-testid="local-map__unavailable">
      {{ reason }}
    </p>
    <template v-else>
      <!-- Single full-map affordance (webclient-minimap-04-island-single-affordance
           D1): a content-free <button> spanning the island's whole box,
           transparent and layered beneath the island's visual content so the
           button element itself contains no focusable descendant. It is a real
           <button> (Enter/Space via the platform, never a key handler on a
           div), carries 展開全地圖 as its accessible name.

           Pointer behaviour is unchanged and stays single-emit: content sits
           above this button, so a click on visible content targets that
           content and reaches onIslandClick, which emits open-map. A click on
           genuinely empty island area lands on this button, which emits
           open-map itself — and onIslandClick, which also sees that bubbling
           click, skips it because event.target.closest("button, …") matches
           this button. Keyboard activation produces the same bubbling click
           and is skipped by the same guard. So every path emits exactly one
           open-map, and a click originating in a lattice node group still emits none. -->
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
      <div class="local-map__meta" data-testid="local-map__title">
        <span class="local-map__meta-title" :title="title">{{ title }}</span>
        <span v-if="showsOrientation" class="local-map__orientation" data-testid="local-map__orientation">
          北↑ 東→
        </span>
        <svg class="local-map__expand-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
          <path d="M14 3h7v7M21 3l-7 7M10 21H3v-7M3 21l7-7" />
        </svg>
      </div>

      <!-- Shared lattice renderer (improve-webclient-map-overlay-scale): the
           minimap composes MapLattice with a fixed square 208px canvasSize
           (design D1), pitch-fit (D3), and footprint crop (D4).
           Scale never exceeds 1.

           The island no longer listens to select/hover/leave (D3): the shared
           renderer keeps its event surface for the overlay and future changes
           to consume. -->
      <MapLattice
        :local-map="localMap"
        :variant="localMap.layoutVariant || 'lattice'"
        :canvas-size="208"
        :col-pitch="40"
        :row-pitch="40"
        :label-font="9"
        :marker-name-font="10"
        :show-axis="true"
        :fog-vignette="true"
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

      <!-- Assistive technology mirror for graph variant remembered nodes (design D5):
           visually-hidden, non-focusable list in payload order. -->
      <ul
        v-if="isGraph && remembered.length"
        class="visually-hidden"
        aria-label="記得的地點"
        data-testid="local-map-remembered-mirror"
      >
        <li v-for="node in remembered" :key="node.id">
          {{ node.label }}
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
  /* The island renders at a constant size (design D1/D2): a fixed 208px square
     canvas, 1px hairline border, and --sp-1 padding. It is right-aligned in
     the anchor and does not stretch to the column width. */
  min-height: auto;
  width: auto;
  align-self: flex-end;
  padding: var(--sp-1);
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

/* Every direct child that paints is raised above the affordance, so its
   clicks target the visible content and reach onIslandClick, and the
   affordance only receives clicks on genuinely empty island area (padding,
   the flex gaps between sections). Written as a `:not()` rule rather than a
   per-child opt-in so a future island child is raised by construction.

   `.visually-hidden` is excluded deliberately, and the exclusion is
   load-bearing twice over. This rule's specificity (0,2,0) outranks
   `.visually-hidden`'s (0,1,0), so without the exclusion it re-positions the
   assistive-technology mirror to `relative` — and (a) `clip` only applies to
   absolutely positioned boxes, so the clip-rect hiding pattern silently stops
   working, and (b) the mirror becomes an in-flow flex item, adding its 1px box
   plus a full `--sp-2` gap to the island. The mirror has nothing to
   raise: it is clipped to nothing and never paints. */
.local-map > *:not(.local-map__affordance):not(.visually-hidden) {
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
  font-family: var(--f-serif);
  font-size: 12px;
  letter-spacing: 0.04em;
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
  color: var(--gold-400);
}

.local-map__expand-icon {
  flex: none;
  width: 14px;
  height: 14px;
  color: var(--gold-400);
}

/* The renderer-axis orientation legend (北↑): a statement about the
   drawing's axis convention, not about the world (design D9). Fixed-size:
   the marks are a two-token convention, never a wrapping phrase. */
.local-map__orientation {
  flex: none;
  white-space: nowrap;
  font-family: var(--f-mono);
  font-size: 10px;
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
  /* Coordinates remain secondary to the map and its larger title. */
  font-size: 10px;
  line-height: 1.45;
  min-height: 1.45em;
  text-align: center;
  overflow-wrap: anywhere;
}

/* An island with no coordinate figure on the current layer states nothing
   and paints no box, while reserving its single line height so the card height
   does not change with the layer (design D2). */
.local-map__detail--empty {
  visibility: hidden;
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
  /* The display:contents viewport adds no stacking box of its own. Keep
     node hit targets above the island's full-bleed expansion button. */
  position: relative;
  z-index: 1;
  pointer-events: none;
  border: 0;
  /* A drawing larger than the legibility floor is windowed around the
     current node (ISLAND_MIN_SCALE); clip it to the fixed square so the
     rest of the street never paints over the stage. */
  overflow: hidden;
}

.local-map :deep(.local-map__node) {
  pointer-events: auto;
}

</style>
