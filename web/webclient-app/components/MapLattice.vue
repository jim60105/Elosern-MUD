<script setup>
// MapLattice (webclient-full-map-fit-view design D1): the shared `local_map`
// lattice renderer. Extracted from `LocalMap.vue` so the minimap island
// (`LocalMap.vue`) and the full-map overlay (`MapOverlay.vue`) share one
// node/marker/edge/label rendering logic, parameterized by scale
// props rather than the island's fixed constants. The full-map overlay
// declares a fitted view (`fitView: true`); the island keeps its
// selection state and detail line; this component owns only the stateless
// lattice rendering and emits `select`/`hover`/`leave`/`move` so each
// caller drives its own chrome.
//
// The geometry and presentation math lives in the sibling composables
// (use-map-lattice-geometry.js / use-map-lattice-render.js); every binding
// below is a group's verbatim state/helper, destructured so the template is
// unchanged. The scoped stylesheet lives in ./map-lattice.css (included via
// the style src, same mechanism as CreationOverlay.vue).
//
// The minimap pan (webclient-scene-transitions, design D3): with `panOnMove`
// a move of the current node starts the drawing translated so the node the
// player left sits where it stood on screen, then eases it to the committed
// placement (a FLIP offset; `lib/map_pan.js`). Only the drawing's two pan
// groups move — edges and axis; the node groups — as one rigid shape,
// and they carry the `.map-lattice__pan` transform only with `panOnMove`, so
// the full map's drawing has no CSS transform at all. Nodes, names, and click
// targets carry the new placement from the commit on. The dot field, the fog, and the gutter's
// edge-direction markers stay put. Travel is multiplied by `--motion-travel`,
// so the reduced and off levels show the new placement at once.
import { computed, onBeforeUnmount, ref, useId, watch } from "vue";
import { panOffset } from "../lib/map_pan.js";
import {
  useMapLatticeGeometry,
  MARKER_CURRENT_R,
  MARKER_DOT_R,
  MARKER_LANDMARK_R,
  MARKER_DIAMOND_HALF,
  MARKER_CURRENT_RING_R,
  HALO_R,
} from "../composables/use-map-lattice-geometry.js";
import { useMapLatticeRender } from "../composables/use-map-lattice-render.js";
import { useMapView } from "../composables/use-map-view.js";

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
  // Fitted view (webclient-full-map-fit-view design D1): when set, the SVG fills
  // a clipped viewport box and its viewBox becomes a window over the unchanged drawing.
  fitView: { type: Boolean, default: false },
  // Type size for node labels (SVG user units). Defaults to 11 for bare
  // mounts; the overlay passes 14 and the island 12 — its own 12px chrome
  // step (webclient-map-legibility), so a label never out-weighs the island's
  // title yet reads at 11 CSS px or more on ordinary neighbourhoods.
  labelFont: { type: Number, default: 11 },
  // Type size for the island's edge-marker names (SVG user units). Declared
  // by the surface for the same reason `labelFont` is: the island's coordinate
  // margin now resolves the uniform scale to ~1, so a user-unit size IS the
  // drawn CSS px size. A marker name annotates the drawing's rim rather than
  // naming a drawn place, so the island keeps it at 10 units, below its 12px
  // chrome step and its 12-unit node labels. The number also drives
  // the along-edge fit budget and the stacked-column line step below: a
  // horizontal name is budgeted in monospace cells of CELL_EM × this size
  // (lib/mono_cells.js: one cell for a glyph the monospace face draws narrow,
  // two for any other), and a stacked column advances one type step per
  // glyph, so a divisor that disagreed with the drawn size would either
  // overflow the marker's slot or truncate names that had room to spare.
  markerNameFont: { type: Number, default: 10 },
  // Fixed square canvas size (CSS px, design D1): when set, the canvas
  // renders as a fixed square of exactly this size and its viewBox side is at
  // least this size so scale never exceeds 1.
  canvasSize: { type: Number, default: null },
  // Knowledge-edge vignette (island-only opt-in): radial gradient wash.
  fogVignette: { type: Boolean, default: false },
  // Axis cross (island-only opt-in): drawn through current node.
  showAxis: { type: Boolean, default: false },
  // Draft overlay chrome (webclient-map-01-draft-chrome design D4): the
  // full-map surface paints its canvas in the `mapcanvas` treatment and
  // rings the current marker (webclient-map-legibility). Off on the minimap
  // island; only the overlay passes it.
  overlayChrome: { type: Boolean, default: false },
  markerNames: { type: Boolean, default: false },
  edgeMarkers: { type: Object, default: null },
  // Layout variant (webclient-map-02-layout-variants D2/D3): "lattice" draws
  // the model's rank-compressed grid placement, "graph" draws the model's
  // radial (D1) placement. Both surfaces pass `model.layoutVariant` — the
  // variant is a renderer parameter sourced from the committed payload, and
  // it changes coordinate sourcing ONLY: markers, edges, labels, legend,
  // activation, focus, and accessible names stay the shared wave-1 renderer.
  variant: { type: String, default: "lattice" },
  // Pan the drawing from the previous current node on a move (the minimap
  // island only; the full-map overlay owns its own view and never pans).
  panOnMove: { type: Boolean, default: false },
  // The EFFECTIVE motion level (`store.view.motionLevel`,
  // webclient-scene-transitions D1): at `off` the transition has no CSS
  // phase, so the final state is on screen in the commit's frame (a CSS
  // phase would outlive the commit by a double frame even at 0s).
  motionLevel: { type: String, default: "full" },
});

const emit = defineEmits(["select", "hover", "leave", "move"]);

const uid = useId();
const patternId = computed(() => `map-lattice-grid-${uid}`);
const fogId = computed(() => `map-lattice-fog-${uid}`);

const geometry = useMapLatticeGeometry(props);
const {
  edges,
  drawnNodes,
  edgeGeoms,
  canvasWidth,
  canvasHeight,
  viewBox,
  effectiveColPitch,
  effectiveRowPitch,
  dotCx,
  dotCy,
  latticeStyle,
  currentPos,
  isGraph,
  visibleNodeLabel,
  nodePos,
} = geometry;

const {
  fittedEdgeMarkers,
  labelY,
  labelTier,
  edgeClass,
  activateNode,
  markerNameX,
  markerNameY,
  markerNameAnchor,
} = useMapLatticeRender(props, emit, geometry);

const viewportEl = ref(null);
const currentNodeId = computed(
  () => props.localMap.nodes?.find((n) => n.visibility === "current")?.id,
);

const mapView = useMapView({
  enabled: computed(() => props.fitView),
  canvasWidth,
  canvasHeight,
  currentPos,
  nodePos,
  currentNodeId,
  viewportEl,
  markerScale: computed(() => props.markerScale),
  labelFont: computed(() => props.labelFont),
});

const {
  viewBox: mapViewBox,
  canZoomIn,
  canZoomOut,
  canRecentre,
  isDragging,
  zoomIn,
  zoomOut,
  recentre,
  onWheel,
  onPointerDown,
  onPointerMove,
  onPointerUp,
  onPointerCancel,
  onClickCapture,
  onFocusIn,
} = mapView;

// ---- the minimap pan (design D3) ----

const svgEl = ref(null);
let panFrame = null;

function parseViewBox(svg) {
  const parts = (svg.getAttribute("viewBox") || "").trim().split(/[\s,]+/).map(Number);
  if (parts.length !== 4 || parts.some((n) => !Number.isFinite(n))) return null;
  return { x: parts[0], y: parts[1], width: parts[2], height: parts[3] };
}

function nodeTranslate(svg, id) {
  if (id == null) return null;
  const el = [...svg.querySelectorAll("[data-node]")].find((node) => node.getAttribute("data-node") === id);
  const match = el?.getAttribute("transform")?.match(/translate\(\s*([-\d.e]+)[\s,]+([-\d.e]+)\s*\)/);
  return match ? { x: Number(match[1]), y: Number(match[2]) } : null;
}

function panGroups(svg) {
  return [...svg.querySelectorAll(".map-lattice__pan")];
}

// The on-screen drawing as the DOM holds it: the node's user-unit position
// plus any pan still in flight, the viewBox, and the canvas's CSS size.
function readFrame(svg, id, withInFlight) {
  const pos = nodeTranslate(svg, id);
  const viewBox = parseViewBox(svg);
  const rect = svg.getBoundingClientRect();
  if (!pos || !viewBox) return null;
  if (withInFlight) {
    const group = panGroups(svg)[0];
    const matrix = group ? getComputedStyle(group).transform : "none";
    const m = matrix && matrix !== "none" ? matrix.match(/matrix\(([^)]+)\)/) : null;
    if (m) {
      const v = m[1].split(",").map(Number);
      pos.x += v[4] || 0;
      pos.y += v[5] || 0;
    }
  }
  return { pos, viewBox, size: { width: rect.width, height: rect.height } };
}

function setPan(el, dx, dy) {
  const axis = el.classList.contains("map-lattice__pan") ? "pan" : "glide";
  el.style.setProperty(`--${axis}-x`, `${dx}px`);
  el.style.setProperty(`--${axis}-y`, `${dy}px`);
}

// Before the patch: the previous current node where it stands now.
watch(
  currentNodeId,
  (_next, prev) => {
    panFrame = null;
    const svg = svgEl.value;
    if (!props.panOnMove || !svg || props.motionLevel === "off" || prev == null) return;
    panFrame = { id: prev, frame: readFrame(svg, prev, true) };
  },
  { flush: "pre" },
);

// After the patch: start the drawing where the previous node stood on
// screen, then release it to the committed placement on the base duration.
watch(
  currentNodeId,
  (nextId) => {
    const recorded = panFrame;
    panFrame = null;
    const svg = svgEl.value;
    if (!recorded || !svg) return;
    const offset = panOffset(recorded.frame, readFrame(svg, recorded.id, false));
    if (!offset) return;
    const groups = panGroups(svg);
    // The current-node marker travels the step it stands for: it starts on
    // the node the player left (in the new placement) and glides to the new
    // node, while the drawing pans under it. Both share one duration and
    // curve, so on screen the marker moves in a straight line from where it
    // was to where it is now.
    const from = nodeTranslate(svg, recorded.id);
    const to = nodeTranslate(svg, nextId);
    const marker = svg.querySelector(".local-map__marker--current");
    const glides = [];
    if (marker && from && to) {
      glides.push([marker, from.x - to.x, from.y - to.y]);
    }
    if (Math.abs(offset.dx) >= 0.5 || Math.abs(offset.dy) >= 0.5) {
      for (const el of groups) glides.push([el, offset.dx, offset.dy]);
    }
    for (const [el, dx, dy] of glides) {
      el.style.transition = "none";
      setPan(el, dx, dy);
    }
    // Commit the start state before the release (FLIP's "invert" step).
    for (const [el] of glides) void getComputedStyle(el).transform;
    for (const [el] of glides) {
      el.style.transition = "";
      setPan(el, 0, 0);
    }
  },
  { flush: "post" },
);

onBeforeUnmount(() => {
  panFrame = null;
});

defineExpose({
  zoomIn,
  zoomOut,
  recentre,
  canZoomIn,
  canZoomOut,
  canRecentre,
});
</script>

<template>
  <div
    ref="viewportEl"
    class="local-map__viewport"
    :class="{
      'local-map__viewport--fit': fitView,
      'local-map__viewport--fit--dragging': fitView && isDragging,
    }"
    @wheel="onWheel"
    @pointerdown="onPointerDown"
    @pointermove="onPointerMove"
    @pointerup="onPointerUp"
    @pointercancel="onPointerCancel"
    @click.capture="onClickCapture"
    @focusin="onFocusIn"
  >
  <svg
    ref="svgEl"
    class="local-map__lattice"
    :class="{ 'local-map__lattice--canvas': overlayChrome }"
    :width="canvasSize ?? canvasWidth"
    :height="canvasSize ?? canvasHeight"
    :viewBox="fitView ? mapViewBox : viewBox"
    :style="latticeStyle"
    :role="overlayChrome ? 'group' : 'img'"
    :aria-label="overlayChrome ? '區域地圖' : '區域地圖縮圖'"
    data-testid="local-map__lattice"
    @mouseleave="emit('leave')"
  >
    <defs>
      <pattern
        :id="patternId"
        :width="effectiveColPitch"
        :height="effectiveRowPitch"
        patternUnits="userSpaceOnUse"
      >
        <circle
          :cx="dotCx"
          :cy="dotCy"
          :r="1.15 * markerScale"
          class="local-map__dot"
          fill="var(--ink-edge)"
          fill-opacity="0.85"
        />
      </pattern>
      <radialGradient
        :id="fogId"
        gradientUnits="userSpaceOnUse"
        :cx="canvasWidth / 2"
        :cy="canvasHeight / 2"
        :r="Math.hypot(canvasWidth / 2, canvasHeight / 2)"
      >
        <stop offset="0.5" stop-color="var(--map-canvas-lo)" stop-opacity="0" />
        <stop offset="0.78" stop-color="var(--map-canvas-lo)" stop-opacity="0.26" />
        <stop offset="1" stop-color="var(--map-canvas-lo)" stop-opacity="0.50" />
      </radialGradient>
    </defs>
    <rect
      v-if="!isGraph"
      class="local-map__dot-field"
      data-testid="local-map__dot-field"
      x="0"
      y="0"
      :width="canvasWidth"
      :height="canvasHeight"
      :fill="`url(#${patternId})`"
      aria-hidden="true"
    />
    <rect
      v-if="fogVignette && !isGraph"
      class="local-map__vignette"
      data-testid="local-map__vignette"
      x="0"
      y="0"
      :width="canvasWidth"
      :height="canvasHeight"
      :fill="`url(#${fogId})`"
      aria-hidden="true"
    />
    <g :class="{ 'map-lattice__pan': panOnMove }" data-testid="map-lattice__pan--lines">
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
      v-if="showAxis && !isGraph && currentPos"
      class="local-map__axis"
      data-testid="local-map__axis"
      stroke="var(--ink-edge)"
      stroke-width="1.5"
      opacity="0.8"
      aria-hidden="true"
    >
      <line :x1="0" :y1="currentPos.y" :x2="canvasWidth" :y2="currentPos.y" />
      <line :x1="currentPos.x" :y1="0" :x2="currentPos.x" :y2="canvasHeight" />
    </g>
    </g>
    <!-- Edge direction markers (map-02 D3b): remembered places outside the
         in-view extent, claimed by the true current→remote bearing, drawn in
         the gutter OUTSIDE the node canvas. A pure decoration layer:
         deliberately NOT the `local-map__marker` class (the browser geometry
         audit pairs every `.local-map__marker` box; these are not node
         placements), no activation, pointer-events none. The island keeps
         its assistive-technology mirror as the canonical reading path and
         renders the layer with names in its gutter; at the overlay scale
         each marker shows its (truncated) place name and carries it as the
         accessible name. -->
    <g
      v-for="marker in fittedEdgeMarkers"
      :key="`edge-marker-${marker.id}`"
      class="local-map__edge-marker"
      :data-testid="`local-map__edge-marker--${marker.id}`"
      :transform="`translate(${marker.x}, ${marker.y})`"
      :role="overlayChrome ? 'img' : null"
      :aria-label="overlayChrome ? marker.name : null"
      :aria-hidden="overlayChrome ? null : 'true'"
    >
      <title>{{ marker.name }}</title>
      <rect
        class="local-map__edge-marker-diamond"
        :x="-MARKER_DIAMOND_HALF * markerScale"
        :y="-MARKER_DIAMOND_HALF * markerScale"
        :width="MARKER_DIAMOND_HALF * 2 * markerScale"
        :height="MARKER_DIAMOND_HALF * 2 * markerScale"
        transform="rotate(45)"
      />
      <circle
        v-if="marker.landmark"
        class="local-map__edge-marker-landmark"
        :r="MARKER_LANDMARK_R * markerScale"
      />
      <template v-if="markerNames">
        <text
          v-if="overlayChrome && marker.visibleName"
          class="local-map__edge-marker-name"
          :style="{ fontSize: `${markerNameFont}px` }"
          :x="markerNameX(marker)"
          :y="markerNameY(marker)"
          :text-anchor="markerNameAnchor(marker)"
        >{{ marker.visibleName }}</text>
        <text
          v-else-if="marker.visibleName && (marker.side === 'top' || marker.side === 'bottom')"
          class="local-map__edge-marker-name--island"
          :style="{ fontSize: `${markerNameFont}px` }"
          :x="markerNameX(marker)"
          :y="markerNameY(marker)"
          :text-anchor="markerNameAnchor(marker)"
        >{{ marker.visibleName }}</text>
        <text
          v-else-if="marker.visibleName && (marker.side === 'left' || marker.side === 'right')"
          class="local-map__edge-marker-name--island"
          :style="{ fontSize: `${markerNameFont}px` }"
          :x="markerNameX(marker)"
          :y="markerNameY(marker)"
          :text-anchor="markerNameAnchor(marker)"
        >
          <tspan
            v-for="(glyph, i) in marker.glyphs"
            :key="i"
            :x="markerNameX(marker)"
            :dy="i === 0 ? 0 : markerNameFont"
          >{{ glyph }}</tspan>
        </text>
      </template>
    </g>
    <g :class="{ 'map-lattice__pan': panOnMove }" data-testid="map-lattice__pan--nodes">
    <g
      v-for="node in drawnNodes"
      :key="node.id"
      class="local-map__node"
      :class="`local-map__node--${node.visibility}`"
      :data-testid="`local-map__node--${node.id}`"
      :data-node="node.id"
      :data-node-id="node.id"
      :data-visibility="node.visibility"
      :role="overlayChrome && node.action?.kind === 'move' ? 'button' : null"
      :tabindex="overlayChrome && node.action?.kind === 'move' ? 0 : null"
      :aria-label="overlayChrome ? node.label : null"
      :transform="`translate(${nodePos(node).x}, ${nodePos(node).y})`"
      @click="activateNode(node)"
      @keydown.enter.prevent="activateNode(node)"
      @keydown.space.prevent="activateNode(node)"
      @mouseenter="emit('hover', node)"
    >
      <!-- The draft marker ladder (webclient-map-01-draft-chrome D2): the
           current node is the large seal-stroked circle; visited is a small
           ink-filled circle; unvisited is a small hollow circle (keeps the
           未探索 rule); remembered keeps the rotated diamond. Shape/size
           distinguish the states without colour. -->
      <!-- The current-location ring (webclient-map-legibility): the full
           map's one ornament of the player's place, concentric with the real
           marker inside the node's own group, so it can never read as a second
           location or float over a connector. Decoration only: not a
           `local-map__marker` (the geometry audit pairs marker boxes), no
           label, no activation. -->
      <circle
        v-if="overlayChrome && node.visibility === 'current'"
        class="local-map__current-ring"
        data-testid="local-map__current-ring"
        :r="MARKER_CURRENT_RING_R * markerScale"
        aria-hidden="true"
      />
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
        :style="{ fontSize: `${labelFont}px` }"
        :y="labelY()"
        text-anchor="middle"
      >
        <title>{{ node.label }}</title>{{ visibleNodeLabel(node) }}
      </text>
    </g>
    </g>
  </svg>
  </div>
</template>

<style scoped src="./map-lattice.css"></style>
