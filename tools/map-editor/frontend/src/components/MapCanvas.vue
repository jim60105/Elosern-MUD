<script setup>
// The map surface. Projection, fit, pan and zoom come from the shared
// @elosern/map-view primitives; selection and theme are this host's. With
// `movable`, an interior room card can be dragged: the drag is a draft drawn
// at the pointer, Escape cancels it, and only the release emits one `move`
// (scene point) -- the host turns that into one saved command. The card stays
// at its draft place until the host settles that command; no new drag
// starts while `busy`.
// Keyboard: Tab walks the marks in object-list order, an arrow key moves
// focus to the nearest mark in that direction, Enter selects and asks the
// host to focus the inspector. Ctrl/⌘-click toggles, Shift-click extends.
// Floating chrome: tool pill (top left), zoom pill (top right), north arrow,
// scale bar and coordinate frame (bottom left).
// Continent: the core's terrain preview raster sits under the authored
// shapes; a selectable shape (a feature) is chosen by click; derived shapes
// (national borders) have no handler and no handle. Any mark flagged
// `draggable` (control-point diamonds, locations, sites, fords, rooms) uses
// the same one-release-one-move drag. With a placing tool, a click on the map
// emits `place` (scene point) instead of selecting.
// Authored labels render through text interpolation only.
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import {
  dotField,
  fitBounds,
  gatePath,
  NODE_DOT_R,
  panByPixels,
  project,
  resolveTheme,
  unproject,
  themeVars,
  wheelFactor,
  zoomBy,
  scaleBar,
  scaleOf,
  DRAG_THRESHOLD_PX,
} from "@elosern/map-view";
import { nearestInDirection } from "../lib/keyboard.js";
import { previewPixels } from "../lib/continent.js";

const props = defineProps({
  scene: { type: Object, default: null },
  selected: { type: Array, default: () => [] },
  tools: { type: Array, default: () => [] },
  tool: { type: String, default: "select" },
  frameLabel: { type: String, default: "" },
  stale: { type: Boolean, default: false },
  label: { type: String, default: "" },
  movable: { type: Boolean, default: false },
  busy: { type: Boolean, default: false },
  // Tools whose canvas click places something (emits `place` with the point).
  placing: { type: Boolean, default: false },
  // Pending tool points (scene metres), drawn as dashed diamonds.
  pending: { type: Array, default: () => [] },
});
const emit = defineEmits(["select", "enter", "move", "tool", "place"]);
const chosen = computed(() => new Set(props.selected));
// { id, point } while a mark is dragged or its move awaits the service.
const draft = ref(null);

const host = ref(null);
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

const at = (point) => (view.value && frame.value ? project(view.value, frame.value, point) : { x: 0, y: 0 });
const path = (points, closed = false) =>
  points.map((p, i) => `${i ? "L" : "M"}${at(p).x.toFixed(1)} ${at(p).y.toFixed(1)}`).join(" ") + (closed ? " Z" : "");

const shapes = computed(() =>
  view.value && props.scene ? props.scene.shapes.map((shape) => ({ ...shape, d: path(shape.points, shape.type === "polygon") })) : [],
);
const pendingMarks = computed(() => (view.value ? props.pending.map((point) => at(point)) : []));

// The terrain preview as one image (painted once per snapshot), placed by
// projecting its south-west and north-east corners.
const rasterHref = computed(() => {
  const raster = props.scene?.raster;
  if (!raster || typeof document === "undefined") return null;
  const { columns, rows } = raster.preview;
  const canvas = document.createElement("canvas");
  canvas.width = columns;
  canvas.height = rows;
  const context = canvas.getContext("2d");
  if (!context) return null;
  context.putImageData(new ImageData(previewPixels(raster.preview), columns, rows), 0, 0);
  return canvas.toDataURL("image/png");
});
const rasterBox = computed(() => {
  const raster = props.scene?.raster;
  if (!raster || !view.value) return null;
  const sw = at({ x: raster.west, y: raster.south });
  const ne = at({ x: raster.east, y: raster.north });
  return { x: Math.min(sw.x, ne.x), y: Math.min(sw.y, ne.y), width: Math.abs(ne.x - sw.x), height: Math.abs(sw.y - ne.y) };
});
const links = computed(() =>
  view.value && props.scene
    ? props.scene.links.map((link) => {
        const mid = at(link.points[Math.floor(link.points.length / 2)]);
        const start = at(link.points[0]);
        return { ...link, d: path(link.points), labelAt: link.points.length > 2 ? mid : { x: (start.x + at(link.points.at(-1)).x) / 2, y: (start.y + at(link.points.at(-1)).y) / 2 } };
      })
    : [],
);
const marks = computed(() =>
  view.value && props.scene
    ? props.scene.marks.map((mark) => ({
        ...mark,
        at: at(draft.value?.id === mark.id ? draft.value.point : mark),
        draft: draft.value?.id === mark.id,
      }))
    : [],
);
const lattice = computed(() =>
  view.value && frame.value && props.scene?.unit ? dotField(view.value, frame.value, props.scene.unit, 36) : null,
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
    draft.value = { id: markDrag.id, point: unproject(view.value, frame.value, pixelOf(event)) };
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
  if (props.placing) {
    emit("place", { point: unproject(view.value, frame.value, pixelOf(event)) });
    return;
  }
  const shape = event.target.closest("[data-shape-ref]");
  if (shape) emit("select", { ref: shape.dataset.shapeRef, toggle: Boolean(event.ctrlKey || event.metaKey), range: false });
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

function brackets(at) {
  const r = 18;
  const l = 6;
  const { x, y } = at;
  return [
    `M${x - r} ${y - r + l} v${-l} h${l}`,
    `M${x + r} ${y - r + l} v${-l} h${-l}`,
    `M${x - r} ${y + r - l} v${l} h${l}`,
    `M${x + r} ${y + r - l} v${l} h${-l}`,
  ].join(" ");
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
    <svg v-if="scene && view" class="map-canvas__svg" :viewBox="`0 0 ${frame.width} ${frame.height}`" role="img" :aria-label="label">
      <defs v-if="lattice">
        <pattern
          id="map-editor-dots"
          :width="lattice.spacingPx"
          :height="lattice.spacingPx"
          patternUnits="userSpaceOnUse"
          :x="lattice.offsetX"
          :y="lattice.offsetY"
        >
          <circle cx="0" cy="0" r="1.2" class="map-canvas__dot" />
        </pattern>
      </defs>
      <rect v-if="lattice" width="100%" height="100%" fill="url(#map-editor-dots)" />
      <image
        v-if="rasterHref && rasterBox"
        :href="rasterHref"
        :x="rasterBox.x"
        :y="rasterBox.y"
        :width="rasterBox.width"
        :height="rasterBox.height"
        preserveAspectRatio="none"
        class="map-canvas__raster"
        data-terrain-preview
      />
      <path
        v-for="shape in shapes"
        :key="shape.id"
        :d="shape.d"
        :class="[
          'map-shape',
          ...shape.role.split(' ').map((role) => `map-shape--${role}`),
          { 'map-shape--selected': shape.selected, 'map-shape--selectable': shape.selectable },
        ]"
        :data-shape="shape.id"
        :data-shape-ref="shape.selectable ? shape.ref : null"
        :data-derived="shape.derived ? 'true' : null"
      />
      <g v-for="link in links" :key="link.id" class="map-link" :class="`map-link--${link.kind}`" :data-link="link.id">
        <path :d="link.d" class="map-link__casing" />
        <path :d="link.d" class="map-link__core" :class="{ 'map-link__core--oneway': !link.twoWay }" />
        <text v-if="link.label" :x="link.labelAt.x" :y="link.labelAt.y - 6" class="map-link__label">{{ link.label }}</text>
      </g>
      <g
        v-for="mark in marks"
        :key="mark.id"
        class="map-mark"
        :class="[`map-mark--${mark.role}`, { 'map-mark--selected': chosen.has(mark.id), 'map-mark--draft': mark.draft }]"
        :data-draft="mark.draft ? 'true' : null"
        :transform="`translate(${mark.at.x.toFixed(1)} ${mark.at.y.toFixed(1)})`"
        :data-kind="mark.kind"
        :data-draggable="mark.draggable ? 'true' : null"
        :data-qualified-ref="mark.id"
        role="button"
        tabindex="0"
        :aria-label="mark.label"
        :aria-pressed="chosen.has(mark.id)"
        @click="select(mark, $event)"
        @keydown="onMarkKey(mark, $event)"
      >
        <template v-if="mark.kind === 'room'">
          <rect x="-100" y="-26" width="200" height="52" rx="6" class="map-mark__card" />
          <text y="-3" class="map-mark__card-name">{{ mark.label }}</text>
          <text y="17" class="map-mark__card-id">{{ mark.detail }}</text>
        </template>
        <template v-else-if="mark.kind === 'handle'">
          <circle v-if="chosen.has(mark.id)" r="14" class="map-mark__ring" />
          <rect x="-6" y="-6" width="12" height="12" transform="rotate(45)" class="map-mark__handle" />
        </template>
        <template v-else-if="mark.kind === 'ford' || mark.kind === 'pass' || mark.kind === 'site'">
          <circle v-if="chosen.has(mark.id)" r="14" class="map-mark__ring" />
          <path v-if="mark.kind === 'ford'" d="M-8 -4 h16 M-8 4 h16" class="map-mark__ford" />
          <path v-else-if="mark.kind === 'pass'" d="M-9 0 h18 M-5 -6 v12 M5 -6 v12" class="map-mark__pass" />
          <rect v-else x="-5" y="-5" width="10" height="10" class="map-mark__site" />
          <text y="-14" class="map-mark__label">{{ mark.label }}</text>
        </template>
        <template v-else>
          <template v-if="chosen.has(mark.id)">
            <circle r="14" class="map-mark__ring" />
            <path :d="brackets({ x: 0, y: 0 })" class="map-mark__brackets" />
          </template>
          <path v-if="mark.gateway" :d="gatePath()" class="map-mark__gate" />
          <circle v-else :r="NODE_DOT_R" class="map-mark__dot" />
          <text y="-14" class="map-mark__label">{{ mark.label }}</text>
        </template>
      </g>
      <g v-for="(point, index) in pendingMarks" :key="`pending-${index}`" :transform="`translate(${point.x.toFixed(1)} ${point.y.toFixed(1)})`" data-pending-point>
        <rect x="-6" y="-6" width="12" height="12" transform="rotate(45)" class="map-mark__handle map-mark__handle--pending" />
      </g>
    </svg>
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
  </div>
</template>
