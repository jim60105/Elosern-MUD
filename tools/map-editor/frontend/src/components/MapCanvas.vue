<script setup>
// The read-only map surface. Projection, fit, pan and zoom come from the
// shared @elosern/map-view primitives; selection and theme are this host's.
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
  themeVars,
  wheelFactor,
  zoomBy,
  DRAG_THRESHOLD_PX,
} from "@elosern/map-view";

const props = defineProps({
  scene: { type: Object, default: null },
  selected: { type: String, default: null },
  stale: { type: Boolean, default: false },
  label: { type: String, default: "" },
});
const emit = defineEmits(["select"]);

const host = ref(null);
const frame = ref(null);
const view = ref(null);
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
  } catch {
    view.value = null;
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
  view.value && props.scene ? props.scene.marks.map((mark) => ({ ...mark, at: at(mark) })) : [],
);
const lattice = computed(() =>
  view.value && frame.value && props.scene?.unit ? dotField(view.value, frame.value, props.scene.unit, 36) : null,
);

// Pointer pan and wheel zoom (view only; no world change).
let drag = null;
function onPointerDown(event) {
  if (event.button !== 0 || event.target.closest(".map-mark")) return;
  drag = { x: event.clientX, y: event.clientY, moved: false };
  host.value.setPointerCapture?.(event.pointerId);
}
function onPointerMove(event) {
  if (!drag || !view.value) return;
  const dx = event.clientX - drag.x;
  const dy = event.clientY - drag.y;
  if (!drag.moved && Math.hypot(dx, dy) < DRAG_THRESHOLD_PX) return;
  drag.moved = true;
  view.value = panByPixels(view.value, frame.value, dx, dy);
  drag.x = event.clientX;
  drag.y = event.clientY;
}
function onPointerUp() {
  drag = null;
}
function onWheel(event) {
  if (!view.value) return;
  const rect = host.value.getBoundingClientRect();
  view.value = zoomBy(view.value, frame.value, wheelFactor(event.deltaY), {
    x: event.clientX - rect.left,
    y: event.clientY - rect.top,
  });
}

function select(mark) {
  emit("select", mark.id);
}

defineExpose({ fit });
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
    @pointercancel="onPointerUp"
    @wheel.prevent="onWheel"
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
      <path v-for="shape in shapes" :key="shape.id" :d="shape.d" :class="`map-shape map-shape--${shape.role}`" :data-shape="shape.id" />
      <g v-for="link in links" :key="link.id" class="map-link" :class="`map-link--${link.kind}`" :data-link="link.id">
        <path :d="link.d" class="map-link__casing" />
        <path :d="link.d" class="map-link__core" :class="{ 'map-link__core--oneway': !link.twoWay }" />
        <text v-if="link.label" :x="link.labelAt.x" :y="link.labelAt.y - 6" class="map-link__label">{{ link.label }}</text>
      </g>
      <g
        v-for="mark in marks"
        :key="mark.id"
        class="map-mark"
        :class="[`map-mark--${mark.role}`, { 'map-mark--selected': mark.id === selected }]"
        :transform="`translate(${mark.at.x.toFixed(1)} ${mark.at.y.toFixed(1)})`"
        :data-kind="mark.kind"
        :data-qualified-ref="mark.id"
        role="button"
        tabindex="0"
        :aria-label="mark.label"
        :aria-pressed="mark.id === selected"
        @click="select(mark)"
        @keydown.enter.prevent="select(mark)"
        @keydown.space.prevent="select(mark)"
      >
        <template v-if="mark.kind === 'room'">
          <rect x="-100" y="-26" width="200" height="52" rx="6" class="map-mark__card" />
          <text y="-3" class="map-mark__card-name">{{ mark.label }}</text>
          <text y="17" class="map-mark__card-id">{{ mark.detail }}</text>
        </template>
        <template v-else>
          <circle v-if="mark.id === selected" r="14" class="map-mark__ring" />
          <path v-if="mark.gateway" :d="gatePath()" class="map-mark__gate" />
          <circle v-else :r="NODE_DOT_R" class="map-mark__dot" />
          <text y="-14" class="map-mark__label">{{ mark.label }}</text>
        </template>
      </g>
    </svg>
    <p v-if="scene?.kind === 'interior'" class="map-canvas__note">版面僅供編輯器使用 · 不代表距離或座標</p>
    <span v-if="stale" class="map-canvas__badge">過期預覽</span>
  </div>
</template>
