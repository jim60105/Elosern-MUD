<script setup>
// The interactive map canvas: the workbench host of the shared map surface
// (MapSurface.vue). Projection, fit, pan and zoom come from the shared
// @elosern/map-view primitives; selection, the camera and theme are this
// host's. With `movable`, an interior room card can be dragged: the drag is a
// draft drawn at the pointer, Escape cancels it, and only the release emits
// one `move` (scene point) -- the host turns that into one saved command. The
// card stays at its draft place until the host settles that command; no new
// drag starts while `busy`.
// Keyboard: Tab walks the marks in object-list order, an arrow key moves
// focus to the nearest mark in that direction, Enter selects and asks the
// host to focus the inspector. Ctrl/⌘-click toggles, Shift-click extends.
// Floating chrome: tool pill (top left), zoom pill (top right), north arrow,
// scale bar and coordinate frame (bottom left). Every painted element comes
// from MapSurface; this file only adds the camera, the chrome and the
// interaction.
// Continent: the core's terrain preview raster sits under the authored
// shapes; a selectable shape (a feature) is chosen by click; derived shapes
// (national borders) have no handler and no handle. Any mark flagged
// `draggable` (control-point diamonds, locations, sites, fords, rooms) uses
// the same one-release-one-move drag. With a placing tool, a click on the map
// emits `place` (scene point) instead of selecting.
// Settlement: node marks and bend diamonds drag the same way; a directed
// road is chosen by clicking its line, and the selected road shows its
// direction chevrons at the start of each segment (pointing downstream).
// Interior: the exterior entrance is a dashed, non-draggable card naming
// the other map and node, joined to its room by a dashed link.
// Authored labels render through text interpolation only.
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import {
  fitBounds,
  panByPixels,
  resolveTheme,
  themeVars,
  unproject,
  wheelFactor,
  zoomBy,
  scaleBar,
  scaleOf,
  DRAG_THRESHOLD_PX,
} from "@elosern/map-view";
import { nearestInDirection } from "../lib/keyboard.js";
import MapSurface from "./MapSurface.vue";

const props = defineProps({
  scene: { type: Object, default: null },
  selected: { type: Array, default: () => [] },
  tools: { type: Array, default: () => [] },
  tool: { type: String, default: "select" },
  frameLabel: { type: String, default: "" },
  stale: { type: Boolean, default: false },
  // The drawn partition outlines belong to older inputs (persistent label).
  olderPartition: { type: Boolean, default: false },
  label: { type: String, default: "" },
  movable: { type: Boolean, default: false },
  busy: { type: Boolean, default: false },
  // Tools whose canvas click places something (emits `place` with the point).
  placing: { type: Boolean, default: false },
  // Pending tool points (scene metres), drawn as dashed diamonds.
  pending: { type: Array, default: () => [] },
});
const emit = defineEmits(["select", "enter", "move", "tool", "place"]);
// { id, point } while a mark is dragged or its move awaits the service.
const draft = ref(null);

const host = ref(null);
const surface = ref(null);
const frame = ref(null);
const view = ref(null);
const fitted = ref(null);
let observer = null;

const theme = themeVars(
  resolveTheme({
    node: "var(--paper-100)",
    paper: "var(--paper-50)",
    current: "var(--seal-deep)",
    accent: "var(--gold-500)",
    accentMuted: "var(--gold-600)",
    selection: "var(--gold-300)",
    halo: "var(--gold-600)",
  }),
);

function measure() {
  const element = host.value;
  if (!element) return;
  const { width, height } = element.getBoundingClientRect();
  if (width > 0 && height > 0) frame.value = { width, height };
}

function fit() {
  if (!props.scene || !frame.value) return;
  const minSpan = props.scene.kind === "interior" ? 4 : 200;
  try {
    view.value = fitBounds(props.scene.bounds, frame.value, { minSpan, marginPx: 72 });
    fitted.value = view.value;
  } catch {
    view.value = null;
    fitted.value = null;
  }
}

onMounted(() => {
  measure();
  observer = new ResizeObserver(() => {
    measure();
    fit();
  });
  observer.observe(host.value);
  fit();
});
onBeforeUnmount(() => observer?.disconnect());
watch(
  () => props.scene,
  (next, previous) => {
    if (!previous || !next || next.kind !== previous.kind || !view.value) fit();
  },
);

// Pointer pan and wheel zoom (view only; no world change), and room drags.
let drag = null;
let panned = false;
let markDrag = null;
let suppressClick = false;
function pixelOf(event) {
  const rect = host.value.getBoundingClientRect();
  return { x: event.clientX - rect.left, y: event.clientY - rect.top };
}
function cancelMarkDrag() {
  if (!markDrag) return;
  markDrag = null;
  draft.value = null;
  window.removeEventListener("keydown", onDragKey, true);
}
function onDragKey(event) {
  if (event.key === "Escape") {
    event.preventDefault();
    event.stopPropagation();
    suppressClick = true;
    cancelMarkDrag();
  }
}
function onPointerDown(event) {
  if (event.button !== 0) return;
  panned = false;
  // Floating chrome keeps its own clicks; only the map surface pans.
  if (event.target.closest(".map-pill")) return;
  const markElement = event.target.closest(".map-mark");
  if (markElement) {
    if (!props.movable || markElement.dataset.draggable !== "true" || props.busy || !view.value) return;
    markDrag = { id: markElement.dataset.qualifiedRef, x: event.clientX, y: event.clientY, moved: false };
    window.addEventListener("keydown", onDragKey, true);
    host.value.setPointerCapture?.(event.pointerId);
    return;
  }
  drag = { x: event.clientX, y: event.clientY, moved: false };
  host.value.setPointerCapture?.(event.pointerId);
}
function onPointerMove(event) {
  if (markDrag) {
    if (!markDrag.moved && Math.hypot(event.clientX - markDrag.x, event.clientY - markDrag.y) < DRAG_THRESHOLD_PX) return;
    markDrag.moved = true;
    draft.value = { id: markDrag.id, point: unprojectPixel(pixelOf(event)) };
    return;
  }
  if (!drag || !view.value) return;
  const dx = event.clientX - drag.x;
  const dy = event.clientY - drag.y;
  if (!drag.moved && Math.hypot(dx, dy) < DRAG_THRESHOLD_PX) return;
  drag.moved = true;
  panned = true;
  view.value = panByPixels(view.value, frame.value, dx, dy);
  drag.x = event.clientX;
  drag.y = event.clientY;
}
function onPointerUp() {
  drag = null;
  if (!markDrag) return;
  const { id, moved } = markDrag;
  markDrag = null;
  window.removeEventListener("keydown", onDragKey, true);
  if (!moved || !draft.value) {
    draft.value = null;
    return;
  }
  suppressClick = true;
  // The draft stays drawn until the host settles the command it started.
  const pending = draft.value;
  emit("move", {
    id,
    point: pending.point,
    settle: () => {
      if (draft.value === pending) draft.value = null;
    },
  });
}
function onPointerCancel() {
  drag = null;
  cancelMarkDrag();
}
onBeforeUnmount(() => window.removeEventListener("keydown", onDragKey, true));
function onWheel(event) {
  if (!view.value) return;
  const rect = host.value.getBoundingClientRect();
  view.value = zoomBy(view.value, frame.value, wheelFactor(event.deltaY), {
    x: event.clientX - rect.left,
    y: event.clientY - rect.top,
  });
}

// A click on the map surface (not a mark, not chrome): place with a placing
// tool, else choose the clicked feature. A pan never counts as a click.
function onSurfaceClick(event) {
  if (panned) {
    panned = false;
    return;
  }
  if (!view.value || event.target.closest(".map-mark, .map-pill")) return;
  // A finished or cancelled mark drag ends with this click wherever it was
  // released: it is consumed here, never turned into a placement.
  if (suppressClick) {
    suppressClick = false;
    return;
  }
  // Pointer capture (taken for a possible drag) may retarget the click to
  // the host: read the element under the pointer instead of the event target.
  const under = document.elementFromPoint?.(event.clientX, event.clientY) ?? event.target;
  const markElement = under?.closest?.(".map-mark");
  if (markElement) {
    const mark = props.scene?.marks.find((item) => item.id === markElement.dataset.qualifiedRef);
    if (mark) select(mark, event);
    return;
  }
  if (props.placing) {
    emit("place", { point: unprojectPixel(pixelOf(event)) });
    return;
  }
  const shape = under?.closest?.("[data-shape-ref], [data-link-ref]");
  const ref = shape?.dataset.shapeRef ?? shape?.dataset.linkRef;
  if (ref) emit("select", { ref, toggle: Boolean(event.ctrlKey || event.metaKey), range: false });
}

function select(mark, event = {}) {
  if (suppressClick) {
    suppressClick = false;
    return;
  }
  emit("select", { ref: mark.id, toggle: Boolean(event.ctrlKey || event.metaKey), range: Boolean(event.shiftKey) });
}

function focusMark(id) {
  const element = [...(host.value?.querySelectorAll(".map-mark") ?? [])].find((el) => el.dataset.qualifiedRef === id);
  element?.focus();
}

function onMarkKey(mark, event) {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    select(mark, event);
    if (event.key === "Enter") emit("enter", mark.id);
    return;
  }
  if (event.shiftKey || event.ctrlKey || event.metaKey || event.altKey) return;
  const next = nearestInDirection(props.scene?.marks ?? [], mark.id, event.key);
  if (event.key.startsWith("Arrow")) event.preventDefault();
  if (next) focusMark(next);
}

function zoom(factor) {
  if (!view.value || !frame.value) return;
  view.value = zoomBy(view.value, frame.value, factor, { x: frame.value.width / 2, y: frame.value.height / 2 });
}

const zoomLevel = computed(() => {
  if (!view.value || !fitted.value || !frame.value) return "—";
  return `${Math.round((scaleOf(view.value, frame.value) / scaleOf(fitted.value, frame.value)) * 100)}%`;
});

const bar = computed(() => {
  if (!view.value || !frame.value || !props.scene?.unit) return null;
  try {
    return scaleBar(view.value, frame.value, props.scene.unit, 96);
  } catch {
    return null;
  }
});

// Frame pixel -> scene point (the shared inverse projection).
function unprojectPixel(pixel) {
  return unproject(view.value, frame.value, pixel);
}

defineExpose({ fit, focusMark });
</script>

<template>
  <div
    ref="host"
    class="map-canvas"
    :class="[`map-canvas--${scene?.kind ?? 'empty'}`, { 'map-canvas--stale': stale }]"
    :style="theme"
    :data-domain="scene?.kind ?? ''"
    @pointerdown="onPointerDown"
    @pointermove="onPointerMove"
    @pointerup="onPointerUp"
    @pointercancel="onPointerCancel"
    @wheel.prevent="onWheel"
    @click="onSurfaceClick"
  >
    <MapSurface
      ref="surface"
      :scene="scene"
      :view="view"
      :frame="frame"
      :selected="selected"
      :draft="draft"
      :pending="pending"
      :label="label"
      interactive
      @mark-select="select"
      @mark-key="onMarkKey"
    />
    <div class="map-pill map-pill--tools" role="toolbar" aria-label="工具">
      <button
        v-for="item in tools"
        :key="item.key"
        type="button"
        class="map-pill__button"
        :class="{ 'map-pill__button--on': tool === item.key }"
        :aria-pressed="tool === item.key"
        :aria-keyshortcuts="item.hotkey ? item.hotkey.toUpperCase() : null"
        :data-tool="item.key"
        @click="emit('tool', item.key)"
      >
        <span aria-hidden="true">{{ item.glyph }}</span> {{ item.label }}
        <kbd v-if="item.hotkey" class="editor__key">{{ item.hotkey.toUpperCase() }}</kbd>
      </button>
    </div>
    <div class="map-pill map-pill--zoom" role="group" aria-label="視圖">
      <button type="button" class="map-pill__button" aria-label="縮小" data-zoom="out" @click="zoom(1.25)">−</button>
      <span class="map-pill__level mono">{{ zoomLevel }}</span>
      <button type="button" class="map-pill__button" aria-label="放大" data-zoom="in" @click="zoom(0.8)">+</button>
      <button type="button" class="map-pill__button" data-zoom="fit" @click="fit">⌖ 適配</button>
    </div>
    <p class="map-canvas__frame">
      <span v-if="scene?.unit" class="map-canvas__north" aria-hidden="true">▲北</span>
      <template v-if="bar">
        <i class="map-canvas__bar" :style="{ width: `${bar.px.toFixed(0)}px` }" aria-hidden="true" />
        <span>{{ bar.text }}</span>
      </template>
      <span class="mono">{{ frameLabel }}</span>
    </p>
    <p v-if="scene?.kind === 'interior'" class="map-canvas__note">版面僅供編輯器使用 · 不代表距離或座標</p>
    <span v-if="stale" class="map-canvas__badge">▲ 過期預覽</span>
    <span v-if="olderPartition" class="map-canvas__badge map-canvas__badge--partition" data-older-partition>
      ▲ 分區輸出屬於舊輸入 · 不可作為遊戲就緒
    </span>
  </div>
</template>
