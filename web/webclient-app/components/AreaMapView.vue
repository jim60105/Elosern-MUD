<script setup>
// The area tab's map (OpenSpec change render-area-map-view; approved design
// docs/superpowers/specs/2026-10-22-world-map-drawer-design.md §6.2-§6.5).
// It draws one validated `area_map` v1 body and nothing else:
//   - grid: the settlement's metre coordinates at one uniform scale under
//     pan and zoom (map_viewport.js), with no compressed mode;
//   - instance / interior: coordinate-free rooms on the minimap's radial
//     placement (no metric position is ever fabricated);
//   - wilderness: the provider's 15 x 15 cell window and current district.
// Metric views carry a scale-true dot field (dots on round world multiples)
// and a scale caption that share one formatter, so both always state the
// same real distance. Fog is the server's: only payload nodes and roads are
// drawn, and a commission that points into fog adds nothing.
//
// Selection: a node selects on click or Enter/Space; its reading (kind, full
// name, state, gate far side, bearing/distance, commissions) renders in the
// `detail` slot, by default AreaMapDetail. 前往 exists only for the
// server's move descriptor on a node one road from the current node, and
// emits `move` once with `{ exit_ref, destination, current_node }` — the
// opaque descriptor plus this payload's canonical current node, the exact
// `explore.move` source; no route is ever derived from geometry.
//
// Host contract (MapDrawer, redesign-map-drawer): `v-model:view`
// (`{ signature, cx, cy, span }`, scoped by `${layer}|${frame.key}|${unit}`)
// and `v-model:selected` keep per-tab session memory; a supplied view whose
// signature differs from the payload's is ignored and the opening fit
// replaces it, and a new map clears the selection. The exposed `zoomIn`,
// `zoomOut`, `recentre`, `showWhole`, `panBy`, `stops` and `stopLabel` drive
// the host's floating pill and keyboard (arrows, ＋/－, C, 0). Arrow keys
// on a focused node move focus spatially to the nearest node that way (the
// map follows it); Shift+arrows are left to the host's pan. This component
// requests no data and owns no drawer chrome.
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import AreaMapDetail from "./AreaMapDetail.vue";
import MapNodeGlyph from "./MapNodeGlyph.vue";
import {
  DETAIL_DRAWER_WIDTH,
  DRAG_THRESHOLD_PX,
  cellRect,
  centreOn,
  nextStop,
  panByPixels,
  previousStop,
  project,
  usableRect,
  wheelFactor,
  zoomAt,
  zoomBy,
} from "../lib/map_viewport.js";
import {
  DOT_MIN_GAP_PX,
  LABEL_FONT_PX,
  adjacentIds,
  areaStops,
  areaUnit,
  cellOf,
  dotField,
  estimateTextWidth,
  isRadialLayer,
  labelCandidates,
  leadsToOf,
  nearestStop,
  nodeAccessibleName,
  nodeDetail,
  openingView,
  placeLabels,
  placeNodes,
  scaleBar,
  spanLimits,
  travelAction,
  viewSignature,
  wholeView,
} from "../lib/area_map_view.js";

const props = defineProps({
  // A validated area_map v1 body in its available form.
  area: { type: Object, required: true },
  // Controlled view `{ signature, cx, cy, span }`; undefined = uncontrolled.
  view: { type: Object, default: undefined },
  // Controlled selected node id; undefined = uncontrolled.
  selected: { type: String, default: undefined },
  // Render the selection reading inside the map (the host may supply its own).
  showDetail: { type: Boolean, default: true },
  // The host cannot send a move yet (a request in flight, or this body is
  // older than the committed position): 前往 waits, visibly, and sends nothing.
  moveBusy: { type: Boolean, default: false },
});
const emit = defineEmits(["update:view", "update:selected", "select", "move"]);

// A 0x0 first paint (jsdom, a hidden host) keeps a sane provisional frame;
// the opening fit is recomputed once the real frame is measured.
const FALLBACK_FRAME = Object.freeze({ width: 960, height: 600 });
// The smallest measured box the opening fit (96 px margins) can use.
const MIN_FRAME_PX = 240;

let instanceCounter = 0;
const uid = `area-map-${(instanceCounter += 1)}-${Math.random().toString(36).slice(2, 8)}`;

const surface = ref(null);
const svgEl = ref(null);
const frame = ref(FALLBACK_FRAME);
const measured = ref(false);
const uiScale = ref(1);

function readUiScale() {
  if (typeof window === "undefined" || typeof document === "undefined") return 1;
  const raw = Number.parseFloat(window.getComputedStyle(document.documentElement).getPropertyValue("--ui-scale"));
  return Number.isFinite(raw) && raw > 0 ? raw : 1;
}

// ── geometry ────────────────────────────────────────────────────────────

const signature = computed(() => viewSignature(props.area));
const unit = computed(() => areaUnit(props.area));
const radial = computed(() => isRadialLayer(props.area));
const isWild = computed(() => props.area.layer === "wilderness");
const placed = computed(() => placeNodes(props.area));
const placedById = computed(() => new Map(placed.value.map((entry) => [entry.node.id, entry])));
const adjacent = computed(() => adjacentIds(props.area));
const stops = computed(() => areaStops(props.area, placed.value, frame.value));
const limits = computed(() => spanLimits(stops.value));

const localView = ref(null);
// True while the shown view is the automatic opening fit (no user input yet).
let viewIsOpening = false;

function sameSignature(view) {
  return !!view && view.signature === signature.value && [view.cx, view.cy, view.span].every(Number.isFinite) && view.span > 0;
}

function commitView(next, { opening = false } = {}) {
  const view = Object.freeze({ signature: signature.value, cx: next.cx, cy: next.cy, span: next.span });
  viewIsOpening = opening;
  localView.value = view;
  emit("update:view", view);
}

function openView() {
  commitView(openingView(props.area, placed.value, frame.value, stops.value), { opening: true });
}

function adoptOrOpen() {
  if (sameSignature(props.view)) {
    localView.value = props.view;
    viewIsOpening = false;
    return;
  }
  if (sameSignature(localView.value)) return;
  openView();
}
adoptOrOpen();

watch(
  () => props.view,
  (next) => {
    if (sameSignature(next) && next !== localView.value) {
      localView.value = next;
      viewIsOpening = false;
    }
  },
);

const view = computed(() => (sameSignature(localView.value) ? localView.value : openingView(props.area, placed.value, frame.value, stops.value)));

// ── selection ───────────────────────────────────────────────────────────

const localSelected = ref(props.selected ?? null);
const focusedId = ref(null);

watch(
  () => props.selected,
  (next) => {
    if (next !== undefined) localSelected.value = next ?? null;
  },
);

const selectedId = computed(() =>
  localSelected.value && placedById.value.has(localSelected.value) ? localSelected.value : null,
);

const detail = computed(() => (selectedId.value ? nodeDetail(props.area, placed.value, selectedId.value) : null));
const detailShown = computed(() => props.showDetail && !!detail.value);

function setSelected(id) {
  const next = id && placedById.value.has(id) ? id : null;
  if (localSelected.value === next) return;
  localSelected.value = next;
  emit("update:selected", next);
  emit("select", next ? nodeDetail(props.area, placed.value, next) : null);
}

// A new map (layer, key or unit) never inherits the old view or selection.
watch(signature, () => {
  localView.value = null;
  focusedId.value = null;
  adoptOrOpen();
  // A host restoring this tab's own selection keeps it; anything else clears.
  const kept = props.selected && placedById.value.has(props.selected) ? props.selected : null;
  if (kept) localSelected.value = kept;
  else setSelected(null);
  moveSent = false;
});

// A republished body that no longer holds the selection drops it.
watch(placedById, (byId) => {
  if (localSelected.value && !byId.has(localSelected.value)) setSelected(null);
  if (focusedId.value && !byId.has(focusedId.value)) focusedId.value = null;
});

// ── projection for drawing ──────────────────────────────────────────────

const usable = computed(() => usableRect(frame.value, { drawerOpen: detailShown.value, drawerWidth: DETAIL_DRAWER_WIDTH }));

const projected = computed(() =>
  placed.value.map((entry) => ({ ...entry, p: project(view.value, frame.value, entry) })),
);

// Paint order depends on the payload only: re-sorting on selection would move
// the focused node's element and drop keyboard focus.
const paintRank = (node) => {
  if (node.visibility === "current") return 8;
  if (travelAction(props.area, node, adjacent.value)) return 6;
  if (leadsToOf(node)) return 5;
  return node.visibility === "visited" ? 3 : 1;
};

const questNodeIds = computed(
  () =>
    new Set(
      props.area.quest_markers
        .filter((marker) => marker.destination.kind === "node")
        .map((marker) => marker.destination.node_id)
        .filter((id) => placedById.value.has(id)),
    ),
);

// Screen directions (radians) of the roads leaving each drawn node, so the
// commission pin can sit in the clearest diagonal instead of on a road.
const roadAngles = computed(() => {
  const out = new Map();
  if (isWild.value) return out;
  const byId = new Map(projected.value.map((entry) => [entry.node.id, entry.p]));
  const add = (from, to) => {
    const a = byId.get(from);
    const b = byId.get(to);
    if (!a || !b || (a.x === b.x && a.y === b.y)) return;
    if (!out.has(from)) out.set(from, []);
    out.get(from).push(Math.atan2(b.y - a.y, b.x - a.x));
  };
  for (const edge of props.area.edges) {
    add(edge.source, edge.destination);
    add(edge.destination, edge.source);
  }
  return out;
});

const QUEST_PIN_OFFSET = 12;
const QUEST_DIAGONALS = [
  [1, -1],
  [-1, -1],
  [1, 1],
  [-1, 1],
];

function questOffset(id, distance) {
  const angles = roadAngles.value.get(id) ?? [];
  let best = QUEST_DIAGONALS[0];
  let bestClearance = -1;
  for (const [sx, sy] of QUEST_DIAGONALS) {
    const theta = Math.atan2(sy, sx);
    let clearance = Math.PI;
    for (const angle of angles) {
      const diff = Math.abs(((theta - angle + 3 * Math.PI) % (2 * Math.PI)) - Math.PI);
      clearance = Math.min(clearance, diff);
    }
    if (clearance > bestClearance + 1e-6) {
      bestClearance = clearance;
      best = [sx, sy];
    }
  }
  return { dx: best[0] * distance, dy: best[1] * distance };
}

const nodeDraws = computed(() =>
  projected.value
    .map((entry) => {
      const { node } = entry;
      const draw = {
        id: node.id,
        x: entry.p.x,
        y: entry.p.y,
        visibility: node.visibility,
        gate: leadsToOf(node) !== "",
        travel: !!travelAction(props.area, node, adjacent.value),
        quest: questNodeIds.value.has(node.id),
        selected: node.id === selectedId.value,
        name: nodeAccessibleName(props.area, node),
        rank: paintRank(node),
        questAt: !isWild.value && questNodeIds.value.has(node.id) ? questOffset(node.id, QUEST_PIN_OFFSET) : null,
        cell: null,
      };
      if (isWild.value) {
        const { col, row } = cellOf(entry);
        const r = cellRect(view.value, frame.value, col, row);
        const inset = Math.min(3, (r.right - r.left) * 0.06);
        draw.cell = {
          x: r.left + inset,
          y: r.top + inset,
          width: Math.max(1, r.right - r.left - 2 * inset),
          height: Math.max(1, r.bottom - r.top - 2 * inset),
        };
      }
      return draw;
    })
    .sort((a, b) => a.rank - b.rank),
);

const edgeDraws = computed(() => {
  if (isWild.value) return [];
  const byId = new Map(projected.value.map((entry) => [entry.node.id, entry]));
  const walked = (node) => node.visibility === "visited" || node.visibility === "current";
  return props.area.edges
    .map((edge, i) => {
      const a = byId.get(edge.source);
      const b = byId.get(edge.destination);
      if (!a || !b) return null;
      return {
        key: `${edge.source}>${edge.destination}#${i}`,
        x1: a.p.x,
        y1: a.p.y,
        x2: b.p.x,
        y2: b.p.y,
        walked: walked(a.node) && walked(b.node),
        travel:
          (edge.source === props.area.current_node && !!travelAction(props.area, b.node, adjacent.value)) ||
          (edge.destination === props.area.current_node && !!travelAction(props.area, a.node, adjacent.value)),
      };
    })
    .filter(Boolean);
});

const dots = computed(() =>
  dotField(view.value, frame.value, unit.value, DOT_MIN_GAP_PX * uiScale.value, isWild.value ? unit.value.metres : 0),
);
const scale = computed(() => (unit.value ? scaleBar(view.value, frame.value, unit.value, 120 * uiScale.value) : null));

// ── labels ──────────────────────────────────────────────────────────────

const fontPx = computed(() => LABEL_FONT_PX * uiScale.value);
const measureCache = new Map();
let measureContext;
function measureText(text, px) {
  const key = `${px}|${text}`;
  if (measureCache.has(key)) return measureCache.get(key);
  if (measureContext === undefined) {
    measureContext = null;
    const jsdom = typeof navigator !== "undefined" && /jsdom/i.test(navigator.userAgent || "");
    if (!jsdom && typeof document !== "undefined") {
      try {
        measureContext = document.createElement("canvas").getContext("2d");
      } catch {
        // observability: ignore R2: a canvas-less host falls back to the glyph-class estimate
        measureContext = null;
      }
    }
  }
  let width = estimateTextWidth(text, px);
  if (measureContext) {
    measureContext.font = `700 ${px}px "Noto Sans TC", "Noto Serif TC", sans-serif`;
    width = measureContext.measureText(text).width;
  }
  // The labels' 0.04em letter spacing, plus a small safety margin.
  width = width * 1.04 + [...text].length * 0.04 * px;
  measureCache.set(key, width);
  return width;
}

// Web fonts land after the first paint: re-measure once they are ready.
const fontsVersion = ref(0);

const labelDraws = computed(() => {
  void fontsVersion.value;
  const candidates = labelCandidates(props.area, placed.value, selectedId.value);
  const labelFrame = {
    width: Math.max(1, frame.value.width - (detailShown.value ? DETAIL_DRAWER_WIDTH : 0)),
    height: frame.value.height,
  };
  const obstacles = projected.value
    .filter((entry) => !isWild.value || entry.node.id === props.area.current_node || leadsToOf(entry.node))
    .map((entry) => ({ id: entry.node.id, x: entry.p.x, y: entry.p.y }));
  // Commission pins are obstacles too, so no name is drawn over its pin.
  for (const draw of nodeDraws.value) {
    if (!draw.questAt) continue;
    obstacles.push({ id: `quest:${draw.id}`, x: draw.x + draw.questAt.dx, y: draw.y + draw.questAt.dy });
  }
  const placedLabels = placeLabels(candidates, (entry) => project(view.value, frame.value, entry), labelFrame, {
    fontPx: fontPx.value,
    measure: measureText,
    markerRadius: (isWild.value ? 10 : 12) * uiScale.value,
    obstacles,
    segments: edgeDraws.value,
  });
  const byId = placedById.value;
  return placedLabels.map((label) => {
    const node = byId.get(label.id).node;
    return {
      ...label,
      visibility: node.visibility,
      gateLine: label.lines.length > 1 || (label.lines[0] ?? "").startsWith("通往 "),
    };
  });
});

// ── pointer: drag pans, wheel zooms, click selects ──────────────────────

let drag = null;

function surfacePoint(event) {
  const rect = surface.value?.getBoundingClientRect?.();
  return { x: (event.clientX ?? 0) - (rect?.left ?? 0), y: (event.clientY ?? 0) - (rect?.top ?? 0) };
}

function onPointerDown(event) {
  if (event.button !== undefined && event.button !== 0) return;
  const target = event.target?.closest?.("[data-node-id]");
  drag = {
    pointerId: event.pointerId,
    x: event.clientX ?? 0,
    y: event.clientY ?? 0,
    view: view.value,
    moved: false,
    nodeId: target ? target.getAttribute("data-node-id") : null,
  };
  try {
    if (event.pointerId !== undefined) surface.value?.setPointerCapture?.(event.pointerId);
  } catch {
    // observability: ignore R2: a synthetic pointer without an active pointer id cannot be captured
  }
}

function onPointerMove(event) {
  if (!drag) return;
  const dx = (event.clientX ?? 0) - drag.x;
  const dy = (event.clientY ?? 0) - drag.y;
  if (!drag.moved && Math.hypot(dx, dy) < DRAG_THRESHOLD_PX) return;
  drag.moved = true;
  commitView(panByPixels(drag.view, frame.value, dx, dy));
}

function onPointerUp() {
  if (!drag) return;
  const { moved, nodeId } = drag;
  drag = null;
  if (moved) return;
  if (nodeId) {
    focusedId.value = nodeId;
    setSelected(nodeId);
  } else {
    setSelected(null);
  }
}

function onPointerCancel() {
  drag = null;
}

function onWheel(event) {
  commitView(zoomBy(view.value, frame.value, wheelFactor(event.deltaY ?? 0), surfacePoint(event), limits.value));
}

// ── keyboard on nodes ───────────────────────────────────────────────────

const tabStopId = computed(() => {
  const candidates = [focusedId.value, selectedId.value, props.area.current_node];
  return candidates.find((id) => id && placedById.value.has(id));
});

function nodeElement(id) {
  for (const el of svgEl.value?.querySelectorAll?.("[data-node-id]") ?? []) {
    if (el.getAttribute("data-node-id") === id) return el;
  }
  return null;
}

function ensureVisible(id) {
  const entry = placedById.value.get(id);
  if (!entry) return;
  const p = project(view.value, frame.value, entry);
  const r = usable.value;
  if (p.x < r.left || p.x > r.right || p.y < r.top || p.y > r.bottom) {
    commitView(centreOn(view.value, frame.value, entry, r));
  }
}

function focusNode(id) {
  focusedId.value = id;
  ensureVisible(id);
  nodeElement(id)?.focus?.();
}

const ARROWS = { ArrowRight: [1, 0], ArrowLeft: [-1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] };

// The nearest node within 60 degrees of the arrow's screen direction.
function spatialNeighbour(fromId, [ux, uy]) {
  const from = projected.value.find((entry) => entry.node.id === fromId);
  if (!from) return null;
  let best = null;
  let bestScore = Infinity;
  for (const entry of projected.value) {
    if (entry.node.id === fromId) continue;
    const dx = entry.p.x - from.p.x;
    const dy = entry.p.y - from.p.y;
    const along = dx * ux + dy * uy;
    if (along <= 0) continue;
    const across = Math.abs(dx * uy - dy * ux);
    if (across > along * Math.tan(Math.PI / 3)) continue;
    const score = along + 2 * across;
    if (score < bestScore) {
      bestScore = score;
      best = entry.node.id;
    }
  }
  return best;
}

function onNodeKeydown(event, id) {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    event.stopPropagation();
    focusedId.value = id;
    setSelected(id);
    return;
  }
  if (event.key === "Home") {
    event.preventDefault();
    event.stopPropagation();
    focusNode(props.area.current_node);
    return;
  }
  const direction = ARROWS[event.key];
  if (!direction || event.shiftKey || event.altKey || event.ctrlKey || event.metaKey) return;
  event.preventDefault();
  event.stopPropagation();
  const next = spatialNeighbour(id, direction);
  if (next) focusNode(next);
}

function onNodeFocus(id) {
  focusedId.value = id;
}

function onRootKeydown(event) {
  if (event.key === "Escape" && selectedId.value) {
    event.stopPropagation();
    const id = selectedId.value;
    setSelected(null);
    focusNode(id);
  }
}

// ── travel and detail actions ───────────────────────────────────────────

// One 前往 per published body: a double click or key repeat sends nothing
// more until the server republishes the area.
let moveSent = false;
watch(
  () => props.area,
  () => {
    moveSent = false;
  },
);
// A host that held the move until its refresh landed releases the guard too.
watch(
  () => props.moveBusy,
  (busy) => {
    if (!busy) moveSent = false;
  },
);

function onDetailMove(action) {
  if (moveSent || props.moveBusy) return;
  const node = placedById.value.get(selectedId.value)?.node;
  const current = travelAction(props.area, node, adjacent.value);
  // Only the selected node's live descriptor travels; a stale card sends nothing.
  if (!current || current !== action) return;
  moveSent = true;
  emit("move", {
    exit_ref: current.exit_ref,
    destination: current.destination,
    current_node: props.area.current_node,
  });
}

function centreNode(id) {
  const entry = placedById.value.get(id);
  if (entry) commitView(centreOn(view.value, frame.value, entry, usable.value));
}

function closeDetail() {
  const id = selectedId.value;
  setSelected(null);
  if (id) focusNode(id);
}

const announcement = computed(() => (detail.value ? `已選取：${detail.value.title}` : ""));

// ── host controls ───────────────────────────────────────────────────────

function rectCentre() {
  const r = usable.value;
  return { x: (r.left + r.right) / 2, y: (r.top + r.bottom) / 2 };
}

function zoomIn() {
  const stop = nextStop(stops.value, view.value.span);
  if (stop) commitView(zoomAt(view.value, frame.value, stop.span, rectCentre(), limits.value));
}

function zoomOut() {
  const stop = previousStop(stops.value, view.value.span);
  if (stop) commitView(zoomAt(view.value, frame.value, stop.span, rectCentre(), limits.value));
}

function recentre() {
  centreNode(props.area.current_node);
}

function showWhole() {
  commitView(wholeView(props.area, placed.value, frame.value, usable.value));
}

function panBy(dxPx, dyPx) {
  commitView(panByPixels(view.value, frame.value, dxPx, dyPx));
}

const stopLabel = computed(() => nearestStop(stops.value, view.value.span).label);

defineExpose({ zoomIn, zoomOut, recentre, showWhole, panBy, stops, stopLabel, detail, view, frame, detailShown });

// ── frame measurement ───────────────────────────────────────────────────

let observer = null;
function applyFrame(width, height) {
  uiScale.value = readUiScale();
  // A host still laying out (a 0x0 or sliver box while the drawer mounts)
  // is not a frame to fit in: keep the provisional one until it is real.
  if (!(width >= MIN_FRAME_PX) || !(height >= MIN_FRAME_PX)) return;
  const changed = width !== frame.value.width || height !== frame.value.height;
  frame.value = Object.freeze({ width, height });
  const first = !measured.value;
  measured.value = true;
  // The provisional fit is replaced by the real one until the player acts.
  if ((first || changed) && viewIsOpening) openView();
}

onMounted(() => {
  document.fonts?.ready?.then(() => {
    measureCache.clear();
    fontsVersion.value += 1;
  });
  const el = surface.value;
  applyFrame(el?.clientWidth ?? 0, el?.clientHeight ?? 0);
  if (typeof ResizeObserver !== "undefined" && el) {
    observer = new ResizeObserver((entries) => {
      const box = entries[0]?.contentRect;
      if (box) applyFrame(Math.round(box.width), Math.round(box.height));
    });
    observer.observe(el);
  }
});

onBeforeUnmount(() => {
  observer?.disconnect();
  observer = null;
});
</script>

<template>
  <div
    class="area-map"
    :class="[`area-map--${area.layer}`, { 'has-detail': detailShown }]"
    data-testid="area-map"
    :data-layer="area.layer"
    @keydown="onRootKeydown"
  >
    <div
      ref="surface"
      class="area-map__surface"
      data-testid="area-map__surface"
      @pointerdown="onPointerDown"
      @pointermove="onPointerMove"
      @pointerup="onPointerUp"
      @pointercancel="onPointerCancel"
      @wheel.prevent="onWheel"
    >
      <svg
        ref="svgEl"
        class="area-map__svg"
        data-testid="area-map__svg"
        :width="frame.width"
        :height="frame.height"
        :viewBox="`0 0 ${frame.width} ${frame.height}`"
        role="group"
        :aria-label="`${area.title}：${radial ? '房間關係示意' : '依實際距離繪製'}`"
      >
        <defs>
          <pattern
            v-if="dots"
            :id="`${uid}-dots`"
            patternUnits="userSpaceOnUse"
            :x="dots.offsetX - dots.spacingPx / 2"
            :y="dots.offsetY - dots.spacingPx / 2"
            :width="dots.spacingPx"
            :height="dots.spacingPx"
          >
            <circle class="area-map__dot" :cx="dots.spacingPx / 2" :cy="dots.spacingPx / 2" r="1.35" />
          </pattern>
          <radialGradient :id="`${uid}-vignette`" cx="50%" cy="48%" r="75%">
            <stop offset="0.55" stop-color="#0a0908" stop-opacity="0" />
            <stop offset="1" stop-color="#0a0908" stop-opacity="0.62" />
          </radialGradient>
        </defs>

        <rect
          v-if="dots"
          class="area-map__dot-field"
          data-testid="area-map__dot-field"
          :data-step-metres="dots.stepMetres"
          :data-spacing-px="dots.spacingPx"
          x="0"
          y="0"
          :width="frame.width"
          :height="frame.height"
          :fill="`url(#${uid}-dots)`"
          aria-hidden="true"
        />

        <g class="area-map__roads" aria-hidden="true">
          <g v-for="edge in edgeDraws" :key="edge.key" class="area-map__road" :class="{ 'is-walked': edge.walked, 'is-frontier': !edge.walked, 'is-travel': edge.travel }">
            <line class="area-map__road-casing" :x1="edge.x1" :y1="edge.y1" :x2="edge.x2" :y2="edge.y2" />
            <line class="area-map__road-core" :x1="edge.x1" :y1="edge.y1" :x2="edge.x2" :y2="edge.y2" />
          </g>
        </g>

        <g class="area-map__nodes">
          <g
            v-for="node in nodeDraws"
            :key="node.id"
            class="area-map__node"
            :class="[
              `is-${node.visibility}`,
              { 'is-gate': node.gate, 'is-travel': node.travel, 'is-selected': node.selected, 'has-quest': node.quest },
            ]"
            :data-node-id="node.id"
            data-testid="area-map__node"
            role="button"
            :tabindex="node.id === tabStopId ? 0 : -1"
            :aria-label="node.name"
            :aria-pressed="node.selected ? 'true' : 'false'"
            :aria-current="node.visibility === 'current' ? 'location' : null"
            @keydown="onNodeKeydown($event, node.id)"
            @focus="onNodeFocus(node.id)"
          >
            <template v-if="node.cell">
              <rect
                class="area-map__cell"
                :x="node.cell.x"
                :y="node.cell.y"
                :width="node.cell.width"
                :height="node.cell.height"
                rx="2"
              />
              <g v-if="node.visibility === 'current' || node.gate || node.quest" :transform="`translate(${node.x} ${node.y})`">
                <template v-if="node.visibility === 'current'">
                  <circle class="area-map__here-glow" r="13" />
                  <circle class="area-map__here-ring" r="9" />
                  <circle class="area-map__here-dot" r="5" />
                </template>
                <path v-else-if="node.gate" class="area-map__gate" d="M-7 7 V-2 A7 7 0 0 1 7 -2 V7 Z" />
                <path v-if="node.quest" class="area-map__quest" d="M0 -9 L5.5 -2 L0 4 L-5.5 -2 Z" :transform="node.visibility === 'current' || node.gate ? 'translate(11 -11)' : ''" />
              </g>
            </template>
            <g v-else :transform="`translate(${node.x} ${node.y})`">
              <circle class="area-map__hit" r="20" />
              <circle v-if="node.selected" class="area-map__selected-ring" r="13" />
              <MapNodeGlyph :state="node.visibility" :gate="node.gate" :travel="node.travel" :selected="node.selected" />
              <g v-if="node.questAt" :transform="`translate(${node.questAt.dx} ${node.questAt.dy})`">
                <path class="area-map__quest" d="M0 -7.5 L5.5 0 L0 7.5 L-5.5 0 Z" />
              </g>
            </g>
          </g>
        </g>

        <g class="area-map__labels" aria-hidden="true">
          <text
            v-for="label in labelDraws"
            :key="`label-${label.id}`"
            class="area-map__label"
            :class="[`is-${label.visibility}`, { 'is-gate-label': label.gateLine }]"
            data-testid="area-map__label"
            :data-label-for="label.id"
            :x="label.x"
            :y="label.y"
            :text-anchor="label.anchor"
          >
            <tspan
              v-for="(line, i) in label.lines"
              :key="i"
              :x="label.x"
              :dy="i === 0 ? 0 : label.lineHeight"
              :class="{ 'area-map__label-gate': line.startsWith('通往 ') }"
            >{{ line }}</tspan>
          </text>
        </g>

        <rect class="area-map__vignette" x="0" y="0" :width="frame.width" :height="frame.height" :fill="`url(#${uid}-vignette)`" aria-hidden="true" />
      </svg>

      <div class="area-map__legend" data-testid="area-map__legend">
        <p v-if="isWild" class="area-map__district" data-testid="area-map__district">{{ area.district_name }}</p>
        <div class="area-map__scale-row">
          <span class="area-map__north" aria-label="上方為北">
            <svg viewBox="0 0 14 18" width="14" height="18" aria-hidden="true"><path d="M7 0 L13 16 L7 12 L1 16 Z" /></svg>
            <span aria-hidden="true">北</span>
          </span>
          <template v-if="scale">
            <span class="area-map__scale-bar" data-testid="area-map__scale-bar" :style="{ width: `${scale.px}px` }" aria-hidden="true" />
            <span class="area-map__scale-text" data-testid="area-map__scale-text">{{ scale.text }}</span>
            <span v-if="dots" class="area-map__dot-caption" data-testid="area-map__dot-caption">{{ dots.caption }}</span>
          </template>
          <span v-else class="area-map__dot-caption" data-testid="area-map__schematic">示意圖 · 不依實際距離</span>
        </div>
      </div>
    </div>

    <div v-if="detailShown" class="area-map__detail" :style="{ width: `${DETAIL_DRAWER_WIDTH}px` }">
      <slot name="detail" :detail="detail" :move="onDetailMove" :centre="centreNode" :close="closeDetail" :busy="moveBusy">
        <AreaMapDetail :detail="detail" :busy="moveBusy" @move="onDetailMove" @centre="centreNode" @close="closeDetail" />
      </slot>
    </div>
    <p class="area-map__live" aria-live="polite" data-testid="area-map__live">{{ announcement }}</p>
  </div>
</template>

<style scoped>
.area-map {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  color: var(--paper-200);
  font-family: var(--f-sans);
  /* Ink on aged vellum, in the obsidian palette: a warm umber wash lit from
     the upper left, settling into soot at the rim. */
  background:
    radial-gradient(85% 75% at 38% 32%, #2a2620 0%, #1c1a16 46%, #121110 100%);
  isolation: isolate;
}
/* Paper grain: a static tile, so panning never repaints a filter. */
.area-map::before {
  content: "";
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  opacity: 0.5;
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='180' height='180'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' seed='7'/><feColorMatrix values='0 0 0 0 0.62 0 0 0 0 0.55 0 0 0 0 0.42 0 0 0 0.11 0'/></filter><rect width='180' height='180' filter='url(%23n)'/></svg>");
}
.area-map__surface {
  position: absolute;
  inset: 0;
  z-index: 1;
  touch-action: none;
  cursor: grab;
  user-select: none;
}
.area-map__surface:active { cursor: grabbing; }
.area-map__svg { position: absolute; inset: 0; display: block; overflow: hidden; }

/* scale-true dot field */
.area-map__dot { fill: var(--gold-400); fill-opacity: 0.26; }

/* roads: a soot casing under a paper-ink core */
.area-map__road line { fill: none; stroke-linecap: round; }
.area-map__road-casing { stroke: #0c0b09; stroke-opacity: 0.85; stroke-width: 7; }
.area-map__road-core { stroke: #b9aa86; stroke-width: 2.6; }
.area-map__road.is-frontier .area-map__road-casing { stroke-width: 5; stroke-opacity: 0.6; }
.area-map__road.is-frontier .area-map__road-core { stroke: #7a7162; stroke-width: 1.8; stroke-dasharray: 5 6; }
.area-map__road.is-travel .area-map__road-core { stroke: var(--gold-400); }
.area-map__road.is-travel.is-frontier .area-map__road-core { stroke: var(--gold-500); }

/* nodes */
.area-map__node { cursor: pointer; outline: none; }
.area-map__hit { fill: transparent; }
.area-map__selected-ring { fill: none; stroke: var(--gold-300); stroke-width: 2.6; }
.area-map__here-glow {
  fill: rgba(165, 44, 49, 0.22);
  stroke: none;
  transform-box: fill-box;
  transform-origin: center;
  animation: area-map-here-breathe var(--motion-pulse) ease-in-out infinite;
}
@keyframes area-map-here-breathe {
  0%, 100% { opacity: 0.55; transform: scale(0.86); }
  50% { opacity: 1; transform: scale(1.18); }
}
@media (prefers-reduced-motion: reduce) {
  .area-map__here-glow { animation: none; }
}
.area-map__here-ring { fill: none; stroke: var(--paper-50); stroke-width: 2; }
.area-map__here-dot { fill: var(--seal-deep); stroke: #fff2e6; stroke-width: 1.5; }
.area-map__gate { fill: #3a342a; stroke: var(--gold-400); stroke-width: 2; stroke-linejoin: round; }
.area-map__node.is-seen .area-map__gate { fill: #26231d; stroke: var(--gold-500); }
.area-map__node.is-selected .area-map__gate { stroke: var(--gold-300); stroke-width: 2.6; }
.area-map__quest { fill: var(--seal-500); stroke: #fff2e6; stroke-width: 1.3; stroke-linejoin: round; }
.area-map__node:focus-visible .area-map__hit,
.area-map__node:focus-visible .area-map__cell {
  stroke: var(--gold-300);
  stroke-width: 2;
  stroke-dasharray: none;
}

/* wilderness cells */
.area-map__cell { fill: rgba(42, 40, 35, 0.5); stroke: rgba(148, 139, 123, 0.28); stroke-width: 1; }
.area-map__node.is-visited .area-map__cell { fill: rgba(185, 154, 96, 0.3); stroke: rgba(185, 154, 96, 0.55); }
.area-map__node.is-current .area-map__cell { fill: rgba(165, 44, 49, 0.2); stroke: var(--seal-400); stroke-width: 1.5; }
.area-map__node.is-travel .area-map__cell { stroke: var(--gold-500); stroke-width: 1.4; stroke-dasharray: 4 3; }
.area-map__node.is-gate .area-map__cell { fill: rgba(58, 52, 42, 0.8); }
.area-map__node.is-selected .area-map__cell { stroke: var(--gold-300); stroke-width: 2.4; stroke-dasharray: none; }

/* labels: 16 CSS px at ui-scale 1, never smaller; a soot halo keeps them
   legible over roads and dots */
.area-map__label {
  fill: var(--paper-100);
  font-family: var(--f-sans);
  font-size: var(--text-xs);
  letter-spacing: 0.04em;
  paint-order: stroke;
  stroke: #14120e;
  stroke-width: 4.5px;
  stroke-linejoin: round;
  pointer-events: none;
}
.area-map__label.is-current { fill: var(--paper-50); font-weight: 700; }
.area-map__label.is-seen { fill: var(--map-label-seen); }
.area-map__label-gate { fill: var(--gold-400); }

.area-map__vignette { pointer-events: none; }

/* legend: district, north mark, scale bar and the dot step */
.area-map__legend {
  position: absolute;
  left: calc(18px * var(--ui-scale));
  bottom: calc(16px * var(--ui-scale));
  display: grid;
  gap: calc(6px * var(--ui-scale));
  padding: calc(8px * var(--ui-scale)) calc(14px * var(--ui-scale));
  background: rgba(14, 13, 11, 0.62);
  border: 1px solid rgba(185, 154, 96, 0.22);
  border-radius: var(--radius-sm);
  pointer-events: none;
}
.area-map__district {
  margin: 0;
  color: var(--paper-100);
  font-family: var(--f-display);
  font-size: var(--text-md);
  letter-spacing: 0.16em;
}
.area-map__scale-row {
  display: flex;
  align-items: center;
  gap: calc(10px * var(--ui-scale));
  color: var(--paper-300);
  font-size: var(--text-xs);
  white-space: nowrap;
}
.area-map__north {
  display: inline-flex;
  align-items: center;
  gap: calc(3px * var(--ui-scale));
  color: var(--gold-400);
  font-family: var(--f-display);
}
.area-map__north path { fill: var(--gold-400); }
.area-map__scale-bar {
  display: inline-block;
  box-sizing: border-box;
  height: calc(7px * var(--ui-scale));
  border: 2px solid var(--paper-300);
  border-top: 0;
}
.area-map__dot-caption { color: var(--paper-500); }

/* selection reading (default card) */
.area-map__detail {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  z-index: 2;
}

.area-map__live {
  position: absolute;
  width: 1px;
  height: 1px;
  margin: -1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}
</style>
