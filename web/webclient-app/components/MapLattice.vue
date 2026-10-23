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
//
// Scale-aware island motion (animate-minimap-scale-transitions; approved
// minimap auto-scale design §6.5): the island pans only while its projection
// keeps one mode and level, and then the world-anchored dot field rides the
// pan with the routes and nodes. A changed mode or level never pans: at the
// effective `full` level the previous drawing dissolves into the new one
// (composables/use-island-dissolve.js), at `reduced` and `off` the new
// projection shows at once with no previous frame left behind.
import { computed, onBeforeUnmount, ref, useId, watch } from "vue";
import { islandMotion, panOffset, scaleKey } from "../lib/map_pan.js";
import { useIslandDissolve } from "../composables/use-island-dissolve.js";
import {
  useMapLatticeGeometry,
  MARKER_CURRENT_R,
  MARKER_DOT_R,
  MARKER_LANDMARK_R,
  MARKER_DIAMOND_HALF,
  MARKER_CURRENT_RING_R,
  HALO_R,
  GATE_ARCH_R,
  STUB_FOOTPRINT,
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
  // Both are declared minimums and the drawn lattice cell is square: the
  // larger of the two binds both axes, because a coordinate-bearing map is
  // projected at one uniform physical scale (project-metric-local-maps).
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
  // Type size for node labels (SVG user units). Defaults to 16 for bare
  // mounts; the island and the overlay both pass 16 — the shared legibility
  // floor (retarget-desktop-viewport-contract D7), so a drawn node label never
  // renders below 16 CSS px at the reference scale. A user-unit size IS the
  // drawn CSS px size at scale 1, because the island's pitch fit resolves the
  // uniform scale to 1 on ordinary neighbourhoods.
  labelFont: { type: Number, default: 16 },
  // Type size for the island's edge-marker names (SVG user units). Declared
  // by the surface for the same reason `labelFont` is: the island's coordinate
  // margin resolves the uniform scale to ~1, so a user-unit size IS the
  // drawn CSS px size. The island no longer keeps marker names below its
  // chrome step — the 16px floor forbids it — so the name's step matches the
  // node label's at 16 units. The number also drives
  // the along-edge fit budget and the stacked-column line step below: a
  // horizontal name is budgeted in monospace cells of CELL_EM × this size
  // (lib/mono_cells.js: one cell for a glyph the monospace face draws narrow,
  // two for any other), and a stacked column advances one type step per
  // glyph, so a divisor that disagreed with the drawn size would either
  // overflow the marker's slot or truncate names that had room to spare.
  markerNameFont: { type: Number, default: 16 },
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
  // the model's metric grid placement, "graph" draws the model's
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
  // The node the exit compass aims (exploration-exit-compass design D6): it
  // gains a highlight class and a decorative ring; null draws nothing.
  aimedNode: { type: String, default: null },
  // The island's automatic projection (render-auto-scaled-minimap-island):
  // LocalMap passes the projection it holds with its hysteresis level. Only
  // the fixed-canvas lattice island reads it; null makes a bare island mount
  // project statelessly, and the overlay and graph variants ignore it.
  islandProjection: { type: Object, default: null },
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
  isIsland,
  nodeTier,
  islandDots,
  islandRings,
  islandRingLabels,
  islandStubs,
  islandLabels,
  isGateway,
  projection,
} = geometry;

// The island's context tier (two-hop places) draws as a small background dot
// with no visible label and no activation.
function isContext(node) {
  return nodeTier(node) === "context";
}

// The island's placed label block for a node (lib/island_labels.js), in the
// node group's own coordinates; null when the block was omitted (a context
// label with no free position) or the node draws no visible label.
function placedLabel(node) {
  const placed = islandLabels.value.get(String(node.id));
  const pos = nodePos(node);
  if (!placed || !pos) return null;
  return relativeTo(placed, pos);
}

function relativeTo(placed, origin) {
  return {
    ...placed,
    lines: placed.lines.map((line) => ({ ...line, x: line.x - origin.x, y: line.y - origin.y })),
    leader: placed.leader
      ? {
          x1: placed.leader.x1 - origin.x,
          y1: placed.leader.y1 - origin.y,
          x2: placed.leader.x2 - origin.x,
          y2: placed.leader.y2 - origin.y,
        }
      : null,
  };
}

function stubLabel(stub) {
  return islandLabels.value.get(`stub:${stub.index}`) ?? null;
}

// A gateway exit stub's hit boxes in user units: the native button covers
// its arrow and, while the label sits beside it, the label too. A label set
// far out on a leader line keeps its own hit box (a child of the button), so
// the button never spans the unrelated markers between them.
function stubHitBoxes(stub) {
  const label = stubLabel(stub);
  const arrow = {
    x0: stub.x - STUB_FOOTPRINT,
    y0: stub.y - STUB_FOOTPRINT,
    x1: stub.x + STUB_FOOTPRINT,
    y1: stub.y + STUB_FOOTPRINT,
  };
  if (!label) return { button: arrow, label: null };
  if (label.leader) return { button: arrow, label: label.box };
  return {
    button: {
      x0: Math.min(arrow.x0, label.box.x0),
      y0: Math.min(arrow.y0, label.box.y0),
      x1: Math.max(arrow.x1, label.box.x1),
      y1: Math.max(arrow.y1, label.box.y1),
    },
    label: null,
  };
}

// The button's box in percent of the square, padded and clamped inside it.
function stubButtonStyle(stub) {
  const { button } = stubHitBoxes(stub);
  const pad = 2;
  const size = canvasWidth.value || 240;
  const pct = (v) => `${(v / size) * 100}%`;
  const x0 = Math.max(0, button.x0 - pad);
  const y0 = Math.max(0, button.y0 - pad);
  return {
    left: pct(x0),
    top: pct(y0),
    width: pct(Math.min(size, button.x1 + pad) - x0),
    height: pct(Math.min(size, button.y1 + pad) - y0),
  };
}

// A leadered label's own hit box, relative to (and in units of) the button.
function stubLabelHitStyle(stub) {
  const { button, label } = stubHitBoxes(stub);
  if (!label) return null;
  const pad = 2;
  const bx0 = Math.max(0, button.x0 - pad);
  const by0 = Math.max(0, button.y0 - pad);
  const bw = Math.min(canvasWidth.value || 240, button.x1 + pad) - bx0;
  const bh = Math.min(canvasWidth.value || 240, button.y1 + pad) - by0;
  const pctX = (v) => `${(v / bw) * 100}%`;
  const pctY = (v) => `${(v / bh) * 100}%`;
  return {
    left: pctX(label.x0 - pad - bx0),
    top: pctY(label.y0 - pad - by0),
    width: pctX(label.x1 - label.x0 + 2 * pad),
    height: pctY(label.y1 - label.y0 + 2 * pad),
  };
}

// A held Enter repeats the platform's click; only the first press moves.
function onStubKeydown(event) {
  if (event.key === "Enter" && event.repeat) event.preventDefault();
}

// A stub activates its own target's move action, exactly once, and never
// the island's full-map affordance (the click stops here).
function onStubActivate(stub) {
  if (!stub.actionable) return;
  emit("move", {
    exit_ref: stub.action.exit_ref,
    destination: stub.action.destination,
  });
}

const STUB_ARROW = "0,-8 6.5,5 0,2 -6.5,5";

// The island paints its quiet context first and the current node last, so
// the player's own name is never covered by a neighbour's marker or label.
const paintedNodes = computed(() => {
  if (!isIsland.value) return drawnNodes.value;
  const rank = (node) => (isContext(node) ? 0 : node.visibility === "current" ? 2 : 1);
  return [...drawnNodes.value].sort((a, b) => rank(a) - rank(b));
});

function onNodeActivate(node) {
  if (isContext(node)) return;
  activateNode(node);
}

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
// A scale change settles any pan still in flight from the previous step: its
// residual offset is in the old scale's units (the copy keeps it frozen).
let settlePan = false;

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

// The island projection's scale (mode and level), only on a coordinate-
// bearing island: the overlay, the radial graph and a coordinate-free layer
// have none, so they never crossfade.
const islandScale = computed(() =>
  isIsland.value && (props.localMap.layer === "grid" || props.localMap.layer === "wilderness")
    ? scaleKey(projection.value)
    : null,
);

const leavingHost = ref(null);
const dissolve = useIslandDissolve(leavingHost);

// Before the patch: decide what the commit plays (lib/map_pan.js
// `islandMotion`). A pan records the previous current node where it stands
// now; a full-motion scale change copies the drawing as it stands; a reduced
// or off scale change drops every previous frame in this very frame.
watch(
  [currentNodeId, islandScale],
  ([nextId, nextScale], [prevId, prevScale] = []) => {
    panFrame = null;
    settlePan = false;
    const svg = svgEl.value;
    if (!props.panOnMove || !svg) return;
    const motion = islandMotion({
      previousId: prevId,
      nextId,
      previousScale: prevScale,
      nextScale,
      motionLevel: props.motionLevel,
    });
    if (motion === "crossfade") {
      if (!dissolve.snapshot(svg)) dissolve.clear();
      settlePan = true;
      return;
    }
    if (motion === "switch") {
      dissolve.clear();
      settlePan = true;
      return;
    }
    // A same-scale step during a dissolve lets the copy finish fading above
    // the panning drawing: cutting it would be a harder jump than the fade.
    if (motion === "pan") panFrame = { id: prevId, frame: readFrame(svg, prevId, true) };
  },
  { flush: "pre" },
);

// After the patch: a scale change lays the copied drawing over the committed
// one and dissolves it; a pan starts the drawing where the previous node stood
// on screen, then releases it to the committed placement on the base duration.
watch(
  [currentNodeId, islandScale],
  ([nextId]) => {
    dissolve.play();
    const recorded = panFrame;
    panFrame = null;
    const svg = svgEl.value;
    if (settlePan && svg) {
      settlePan = false;
      const offset = (el) =>
        ["--pan-x", "--pan-y", "--glide-x", "--glide-y"].some((name) => {
          const value = el.style.getPropertyValue(name);
          return value !== "" && Number.parseFloat(value) !== 0;
        });
      const moving = [
        ...panGroups(svg),
        ...svg.querySelectorAll(".map-lattice__pan .local-map__marker--current"),
      ].filter(offset);
      for (const el of moving) {
        el.style.transition = "none";
        setPan(el, 0, 0);
      }
      for (const el of moving) void getComputedStyle(el).transform;
      for (const el of moving) el.style.transition = "";
    }
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

// Leaving `full` (or the island) mid-dissolve shows the committed drawing at
// once: no previous frame outlives the level that allowed it.
watch(
  () => props.motionLevel !== "full" || !isIsland.value || !props.panOnMove,
  (stop) => {
    if (stop) dissolve.clear();
  },
);

onBeforeUnmount(() => {
  panFrame = null;
  dissolve.clear();
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
      'local-map__viewport--island': isIsland,
    }"
    :style="isIsland ? latticeStyle : null"
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
    :class="{ 'local-map__lattice--canvas': overlayChrome, 'local-map__lattice--island': isIsland }"
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
        v-if="!isIsland"
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
    <!-- The island's scale-true background (design §5): in uniform mode a
         bounded list of world-anchored dots inside a pan group, so the ground
         slides with the drawing; in compressed mode labelled distance rings
         centred on the player, outside the pan (shape and text, not colour,
         state the compression). Pure decoration: pointer-inert, aria-hidden,
         no marker/label classes, token colours. -->
    <g
      v-if="isIsland && islandDots.length"
      :class="{ 'map-lattice__pan': panOnMove }"
      data-testid="map-lattice__pan--field"
    >
      <g class="local-map__dot-field" data-testid="local-map__dot-field" aria-hidden="true">
        <circle
          v-for="(dot, i) in islandDots"
          :key="i"
          class="local-map__dot"
          :cx="dot.x"
          :cy="dot.y"
          :r="1.15 * markerScale"
          fill="var(--ink-edge)"
          fill-opacity="0.85"
        />
      </g>
    </g>
    <g
      v-if="isIsland && islandRings.length"
      class="local-map__rings"
      data-testid="local-map__rings"
      aria-hidden="true"
    >
      <circle
        v-for="ring in islandRings"
        :key="`ring-${ring.distance}`"
        class="local-map__ring"
        :data-distance="ring.distance"
        :cx="120"
        :cy="120"
        :r="ring.radius"
      />
      <text
        v-for="ring in islandRingLabels"
        :key="`ring-label-${ring.distance}`"
        class="local-map__ring-label"
        :style="{ fontSize: `${labelFont}px` }"
        :x="ring.labelX"
        :y="ring.labelY"
        dy="0.35em"
        text-anchor="middle"
      >{{ ring.label }}</text>
    </g>
    <rect
      v-if="!isGraph && !isIsland"
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
        :x="-(marker.half ?? MARKER_DIAMOND_HALF * markerScale)"
        :y="-(marker.half ?? MARKER_DIAMOND_HALF * markerScale)"
        :width="(marker.half ?? MARKER_DIAMOND_HALF * markerScale) * 2"
        :height="(marker.half ?? MARKER_DIAMOND_HALF * markerScale) * 2"
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
        <!-- The island's rim markers (render-auto-scaled-minimap-island):
             the whole name, never shortened, laid out inside the square by
             the geometry's rim layout — beside the diamond in the band, or
             wrapped onto inward rows (columns on the left/right sides). -->
        <text
          v-else-if="marker.rim && marker.visibleName"
          class="local-map__edge-marker-name--island"
          :style="{ fontSize: `${markerNameFont}px` }"
          :text-anchor="marker.rimName?.horizontal ? 'start' : 'middle'"
        >
          <tspan
            v-for="(line, i) in marker.rimName?.lines ?? []"
            :key="i"
            :x="line.x"
            :y="line.y"
          >{{ line.text }}</tspan>
        </text>
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
      v-for="node in paintedNodes"
      :key="node.id"
      class="local-map__node"
      :class="[`local-map__node--${node.visibility}`, { 'local-map__node--context': isContext(node) }, { 'local-map__node--aimed': aimedNode !== null && String(node.id) === String(aimedNode) }]"
      :data-testid="`local-map__node--${node.id}`"
      :data-node="node.id"
      :data-node-id="node.id"
      :data-visibility="node.visibility"
      :role="overlayChrome && node.action?.kind === 'move' ? 'button' : null"
      :tabindex="overlayChrome && node.action?.kind === 'move' ? 0 : null"
      :aria-label="overlayChrome ? node.label : null"
      :transform="`translate(${nodePos(node).x}, ${nodePos(node).y})`"
      @click="onNodeActivate(node)"
      @keydown.enter.prevent="onNodeActivate(node)"
      @keydown.space.prevent="onNodeActivate(node)"
      @mouseenter="emit('hover', node)"
    >
      <!-- An island context node (two-hop place): one small background dot,
           its full name only as the group's title; no marker class, label,
           halo or activation. -->
      <template v-if="isContext(node)">
        <title>{{ node.label }}</title>
        <circle
          class="local-map__context-dot"
          data-testid="local-map__context-dot"
          :r="2.4 * markerScale"
          aria-hidden="true"
        />
        <!-- Its name only where a free position remains after every exit
             and the current node (fits-or-omitted, design §6.4). -->
        <text
          v-if="placedLabel(node)"
          class="local-map__node-label local-map__node-label--context"
          :style="{ fontSize: `${labelFont}px` }"
          text-anchor="middle"
        >
          <tspan
            v-for="(line, i) in placedLabel(node).lines"
            :key="i"
            :x="line.x"
            :y="line.y"
          >{{ line.text }}</tspan>
        </text>
      </template>
      <template v-else>
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
      <!-- The compass aim ring (exploration-exit-compass D6): decoration
           only, outside the `local-map__marker` class the geometry audit
           pairs, so it never reads as a second location. -->
      <circle
        v-if="aimedNode !== null && String(node.id) === String(aimedNode)"
        class="local-map__aim-ring"
        data-testid="local-map__aim-ring"
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
      <!-- The island's gate glyph (label-minimap-exits-and-gateways): an
           arch framing the node's own visibility marker, so a gateway reads
           by shape whatever its state. Decoration: not a marker class. -->
      <path
        v-if="isGateway(node)"
        class="local-map__gate-glyph"
        data-testid="local-map__gate-glyph"
        :d="`M ${-GATE_ARCH_R} ${GATE_ARCH_R - 2} V -1 A ${GATE_ARCH_R} ${GATE_ARCH_R} 0 0 1 ${GATE_ARCH_R} -1 V ${GATE_ARCH_R - 2} M ${-GATE_ARCH_R - 3} ${GATE_ARCH_R - 2} H ${-GATE_ARCH_R + 3} M ${GATE_ARCH_R - 3} ${GATE_ARCH_R - 2} H ${GATE_ARCH_R + 3}`"
        aria-hidden="true"
      />
      <template v-if="isIsland">
        <!-- A suppressed duplicate region name keeps the full name. -->
        <title v-if="!placedLabel(node)">{{ node.label }}</title>
        <!-- A label that found no free position sits farther out, joined to
             its marker by a hairline leader. -->
        <line
          v-if="placedLabel(node)?.leader"
          class="local-map__leader"
          data-testid="local-map__leader"
          :x1="placedLabel(node).leader.x1"
          :y1="placedLabel(node).leader.y1"
          :x2="placedLabel(node).leader.x2"
          :y2="placedLabel(node).leader.y2"
          aria-hidden="true"
        />
        <text
          v-if="placedLabel(node)"
          class="local-map__node-label"
          :class="`local-map__node-label--${labelTier(node)}`"
          :style="{ fontSize: `${labelFont}px` }"
          text-anchor="middle"
        >
          <title>{{ node.label }}</title>
          <tspan
            v-for="(line, i) in placedLabel(node).lines"
            :key="i"
            :class="{ 'local-map__via': line.kind === 'via' }"
            :x="line.x"
            :y="line.y"
          >{{ line.text }}</tspan>
        </text>
      </template>
      <text
        v-else
        class="local-map__node-label"
        :class="`local-map__node-label--${labelTier(node)}`"
        :style="{ fontSize: `${labelFont}px` }"
        :y="labelY()"
        text-anchor="middle"
      >
        <title>{{ node.label }}</title>{{ visibleNodeLabel(node) }}
      </text>
      </template>
    </g>
    </g>
    <!-- Gateway exit stubs (label-minimap-exits-and-gateways; design §4.2):
         a cross-layer target is never a node. Its exit is an arrowhead on the
         exit ring at the target's bearing, a route from the player to it, and
         a `通往 <leads_to>` label. Fixed to the current node's ring, so it
         stays outside the pan groups. A locked stub (no action) keeps its
         hollow arrow and label: information, never a way through. -->
    <g
      v-for="stub in islandStubs"
      :key="`stub-${stub.key}`"
      class="local-map__stub"
      :class="{ 'local-map__stub--locked': !stub.actionable }"
      :data-testid="`local-map__stub--${stub.index}`"
      aria-hidden="true"
    >
      <title>{{ stub.label }}</title>
      <line
        class="local-map__edge"
        :class="stub.actionable ? 'local-map__edge--traversable' : 'local-map__edge--blocked'"
        :x1="120 + (HALO_R + 1) * Math.sin((stub.bearing * Math.PI) / 180)"
        :y1="120 - (HALO_R + 1) * Math.cos((stub.bearing * Math.PI) / 180)"
        :x2="120 + (88 - 6) * Math.sin((stub.bearing * Math.PI) / 180)"
        :y2="120 - (88 - 6) * Math.cos((stub.bearing * Math.PI) / 180)"
      />
      <polygon
        class="local-map__stub-arrow"
        data-testid="local-map__stub-arrow"
        :points="STUB_ARROW"
        :transform="`translate(${stub.x}, ${stub.y}) rotate(${stub.bearing})`"
      />
      <line
        v-if="stubLabel(stub)?.leader"
        class="local-map__leader"
        :x1="stubLabel(stub).leader.x1"
        :y1="stubLabel(stub).leader.y1"
        :x2="stubLabel(stub).leader.x2"
        :y2="stubLabel(stub).leader.y2"
      />
      <text
        v-if="stubLabel(stub)"
        class="local-map__node-label local-map__stub-label"
        :style="{ fontSize: `${labelFont}px` }"
        text-anchor="middle"
      >
        <tspan
          v-for="(line, i) in stubLabel(stub).lines"
          :key="i"
          :x="line.x"
          :y="line.y"
        >{{ line.text }}</tspan>
      </text>
    </g>
  </svg>
  <!-- The island's scale-change dissolve (animate-minimap-scale-transitions):
       a childless host over the drawing and under the stub buttons, into
       which the script lays inert, aria-hidden copies of the previous
       drawing while they fade out. Vue renders no children here, so it never
       patches the copies; each one removes itself when its fade ends. -->
  <div
    v-if="isIsland && panOnMove"
    ref="leavingHost"
    class="local-map__leaving-host"
    data-testid="local-map__leaving-host"
    aria-hidden="true"
    inert
  ></div>
  <!-- An actionable stub's control: a native button over its arrow and
       label (the island svg is role="img", whose children are presentational,
       so the control is the svg's sibling). Enter, Space and pointer all
       reach the one click handler; the click never also opens the map.
       Space stops at the button so the shell's document key routing (which
       claims Space for paging and multi-select and prevents its default)
       never sees it, leaving the platform's own Space activation intact. -->
  <template v-if="isIsland">
    <button
      v-for="stub in islandStubs.filter((s) => s.actionable)"
      :key="`stub-button-${stub.key}`"
      type="button"
      class="local-map__stub-button"
      :data-testid="`local-map__stub-button--${stub.index}`"
      :aria-label="`往 ${stub.leadsTo} 移動`"
      :title="`往 ${stub.leadsTo} 移動`"
      :style="stubButtonStyle(stub)"
      @click.stop="onStubActivate(stub)"
      @keydown.space.stop
      @keydown="onStubKeydown"
    >
      <span
        v-if="stubLabelHitStyle(stub)"
        class="local-map__stub-hit"
        :style="stubLabelHitStyle(stub)"
        aria-hidden="true"
      ></span>
    </button>
  </template>
  </div>
</template>

<style scoped src="./map-lattice.css"></style>
