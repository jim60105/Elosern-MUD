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
import { computed, ref, useId } from "vue";
import {
  useMapLatticeGeometry,
  MARKER_CURRENT_R,
  MARKER_DOT_R,
  MARKER_LANDMARK_R,
  MARKER_DIAMOND_HALF,
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
  // Type size for node labels (SVG user units). Defaults to 11 for the overlay
  // and bare mounts; the island passes 9 to respect the type proportion and
  // stay below the island's own 10px chrome step.
  labelFont: { type: Number, default: 11 },
  // Type size for the island's edge-marker names (SVG user units). Declared
  // by the surface for the same reason `labelFont` is: the island's coordinate
  // margin now resolves the uniform scale to ~1, so a user-unit size IS the
  // drawn CSS px size. The island's smallest chrome type step is 10px (its
  // header row), and a marker name annotates the drawing rather than titling
  // it, so it renders AT that step and never above it. The number also drives
  // the along-edge fit budget and the stacked-column line step below: the
  // labels are full-width CJK in the shared monospace token, so one glyph
  // advances exactly one type step on either axis, and a divisor that
  // disagreed with the drawn size would either overflow the marker's slot or
  // truncate names that had room to spare.
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
  // draws the teardrop location pin above the current marker. Off on the
  // minimap island; only the overlay passes it.
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
      d="M0 -18 C-2 -21 -7 -26 -7 -30 a7 7 0 0 1 14 0 C7 -26 2 -21 0 -18 Z"
      aria-hidden="true"
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
  </svg>
  </div>
</template>

<style scoped src="./map-lattice.css"></style>
