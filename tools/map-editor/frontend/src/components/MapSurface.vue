<script setup>
// The shared map drawing: one SVG for every consumer of the editor's map
// projection (the interactive canvas today, the offline capture host next).
//
// This component owns painting only: the dot-field background, the terrain
// preview raster, authored and derived shapes, links (bent roads, curved
// interior connections, the dashed exterior link) and marks (nodes, gate
// glyphs, locations, sites, fords, passes, control-point handles and the
// room/exterior cards), with each label drawn through text interpolation.
//
// It owns no interaction, no selection policy, no camera and no chrome. The
// host passes a scene, a view and a frame; `interactive` turns the marks into
// focusable, clickable targets and forwards `mark-select` / `mark-key` to the
// host so a host keeps its own selection and keyboard behaviour.
//
// `showLabel: false` on a scene drawable suppresses that drawable's text
// only: geometry, cards and direction indicators stay painted. Layer
// filtering happens before the scene arrives (see lib/layers.js and
// lib/capture.js); the background rectangle is excluded from painted content
// measurement via `data-background`.
import { computed, nextTick, ref } from "vue";
import {
  dotField,
  gatePath,
  NODE_DOT_R,
  project,
} from "@elosern/map-view";
import { previewPixels } from "../lib/continent.js";

const props = defineProps({
  scene: { type: Object, default: null },
  view: { type: Object, default: null },
  frame: { type: Object, default: null },
  selected: { type: Array, default: () => [] },
  // { id, point } while a mark is dragged or its move awaits the service.
  draft: { type: Object, default: null },
  // Pending tool points (scene metres), drawn as dashed diamonds.
  pending: { type: Array, default: () => [] },
  label: { type: String, default: "" },
  // Attach mark roles, tabindex and pointer/keyboard forwarding.
  interactive: { type: Boolean, default: false },
});
const emit = defineEmits(["mark-select", "mark-key"]);

const element = ref(null);
const chosen = computed(() => new Set(props.selected));

const at = (point) => (props.view && props.frame ? project(props.view, props.frame, point) : { x: 0, y: 0 });
const path = (points, closed = false) =>
  points.map((p, i) => `${i ? "L" : "M"}${at(p).x.toFixed(1)} ${at(p).y.toFixed(1)}`).join(" ") + (closed ? " Z" : "");

const shapes = computed(() =>
  props.view && props.scene ? props.scene.shapes.map((shape) => ({ ...shape, d: path(shape.points, shape.type === "polygon") })) : [],
);
const pendingMarks = computed(() => (props.view ? props.pending.map((point) => at(point)) : []));

// The terrain preview as one image (painted once per snapshot), placed by
// projecting its south-west and north-east corners.
// Keyed on the preview object itself (stable within one snapshot), so a
// selection change that rebuilds the scene does not re-encode the image.
const rasterPreview = computed(() => props.scene?.raster?.preview ?? null);
const rasterHref = computed(() => {
  const preview = rasterPreview.value;
  if (!preview || typeof document === "undefined") return null;
  const { columns, rows } = preview;
  const canvas = document.createElement("canvas");
  canvas.width = columns;
  canvas.height = rows;
  const context = canvas.getContext("2d");
  if (!context) return null;
  context.putImageData(new ImageData(previewPixels(preview), columns, rows), 0, 0);
  return canvas.toDataURL("image/png");
});
const rasterBox = computed(() => {
  const raster = props.scene?.raster;
  if (!raster || !props.view) return null;
  const sw = at({ x: raster.west, y: raster.south });
  const ne = at({ x: raster.east, y: raster.north });
  return { x: Math.min(sw.x, ne.x), y: Math.min(sw.y, ne.y), width: Math.abs(ne.x - sw.x), height: Math.abs(sw.y - ne.y) };
});

// A curved link (interior connections): a quadratic arc bowed to the right of
// travel, so a two-way pair separates into two arrows; it always carries one
// direction chevron. Pixel space only: nothing here is a distance.
const CURVE_PX = 26;
function curved(link) {
  const a = at(link.points[0]);
  const b = at(link.points.at(-1));
  const length = Math.hypot(b.x - a.x, b.y - a.y) || 1;
  const normal = { x: -(b.y - a.y) / length, y: (b.x - a.x) / length };
  const control = { x: (a.x + b.x) / 2 + normal.x * CURVE_PX, y: (a.y + b.y) / 2 + normal.y * CURVE_PX };
  const pointAt = (t) => ({
    x: (1 - t) * (1 - t) * a.x + 2 * (1 - t) * t * control.x + t * t * b.x,
    y: (1 - t) * (1 - t) * a.y + 2 * (1 - t) * t * control.y + t * t * b.y,
  });
  const middle = pointAt(0.5);
  return {
    ...link,
    d: `M${a.x.toFixed(1)} ${a.y.toFixed(1)} Q${control.x.toFixed(1)} ${control.y.toFixed(1)} ${b.x.toFixed(1)} ${b.y.toFixed(1)}`,
    labelAt: { x: middle.x + normal.x * 12, y: middle.y + normal.y * 12 + 6 },
    chevrons: [chevronAt(pointAt(0.55), pointAt(0.6), pointAt(0.5))],
  };
}

const links = computed(() =>
  props.view && props.scene
    ? props.scene.links.map((link) => {
        if (link.curve) return curved(link);
        const mid = at(link.points[Math.floor(link.points.length / 2)]);
        const start = at(link.points[0]);
        return {
          ...link,
          d: path(link.points),
          labelAt: link.points.length > 2 ? mid : { x: (start.x + at(link.points.at(-1)).x) / 2, y: (start.y + at(link.points.at(-1)).y) / 2 },
          chevrons: link.selected ? chevrons(link.points.map(at)) : [],
        };
      })
    : [],
);
const marks = computed(() =>
  props.view && props.scene
    ? props.scene.marks.map((mark) => ({
        ...mark,
        at: at(props.draft?.id === mark.id ? props.draft.point : mark),
        draft: props.draft?.id === mark.id,
      }))
    : [],
);
const lattice = computed(() =>
  props.view && props.frame && props.scene?.unit ? dotField(props.view, props.frame, props.scene.unit, 36) : null,
);

// One chevron per segment, 60 % along it, pointing from start to end.
function chevrons(points) {
  const marks = [];
  for (let i = 0; i + 1 < points.length; i += 1) {
    const a = points[i];
    const b = points[i + 1];
    const length = Math.hypot(b.x - a.x, b.y - a.y);
    if (length < 16) continue;
    const ux = (b.x - a.x) / length;
    const uy = (b.y - a.y) / length;
    const x = a.x + (b.x - a.x) * 0.6;
    const y = a.y + (b.y - a.y) * 0.6;
    marks.push(
      `M${(x - 7 * ux - 5 * uy).toFixed(1)} ${(y - 7 * uy + 5 * ux).toFixed(1)} L${x.toFixed(1)} ${y.toFixed(1)} L${(x - 7 * ux + 5 * uy).toFixed(1)} ${(y - 7 * uy - 5 * ux).toFixed(1)}`,
    );
  }
  return marks;
}

// One chevron at `tip`, pointing along `from` -> `to`.
function chevronAt(tip, to, from) {
  const length = Math.hypot(to.x - from.x, to.y - from.y) || 1;
  const ux = (to.x - from.x) / length;
  const uy = (to.y - from.y) / length;
  const { x, y } = tip;
  return `M${(x - 7 * ux - 5 * uy).toFixed(1)} ${(y - 7 * uy + 5 * ux).toFixed(1)} L${x.toFixed(1)} ${y.toFixed(1)} L${(x - 7 * ux + 5 * uy).toFixed(1)} ${(y - 7 * uy - 5 * ux).toFixed(1)}`;
}

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

function onMarkClick(mark, event) {
  if (!props.interactive) return;
  // One selection path: the host's surface click handler ignores marks, and
  // stopping the bubble keeps that true if its handler is ever reordered.
  event.stopPropagation();
  emit("mark-select", mark, event);
}
function onMarkKey(mark, event) {
  if (!props.interactive) return;
  emit("mark-key", mark, event);
}

// The faces settle only after the newly inserted text has been laid out:
// `document.fonts.ready` is already resolved until a layout starts the face
// loads, so force style/layout and re-read it (bounded) before judging errors.
async function settleFonts() {
  if (!document.fonts) return;
  for (let attempt = 0; attempt < 4; attempt += 1) {
    element.value?.getBoundingClientRect?.();
    await new Promise((resolve) => requestAnimationFrame(resolve));
    await document.fonts.ready;
    if (document.fonts.status !== "loading") break;
  }
  const failed = [...document.fonts].filter((face) => face.status === "error");
  if (failed.length) throw new Error(`map surface: ${failed.length} local font face(s) failed to load`);
}

// Readiness for a host that must not report a partial paint: the local font
// faces settle, the terrain raster decodes, and the update has been applied.
// A failed local font face is an error, never a silently unreadable image.
const decodedRaster = new Set();
async function ready() {
  if (typeof document === "undefined") return;
  await settleFonts();
  await nextTick();
  const href = element.value?.querySelector?.("image[data-terrain-preview]")?.getAttribute("href");
  if (href && !decodedRaster.has(href)) {
    const probe = new Image();
    probe.src = href;
    await probe.decode();
    decodedRaster.add(href);
  }
  await nextTick();
}

defineExpose({ element, ready });
</script>

<template>
  <svg
    v-if="scene && view && frame"
    ref="element"
    class="map-canvas__svg"
    :viewBox="`0 0 ${frame.width} ${frame.height}`"
    role="img"
    :aria-label="label"
  >
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
    <rect v-if="lattice" width="100%" height="100%" fill="url(#map-editor-dots)" data-background />
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
      :data-district="shape.district ?? null"
      :data-older-input="shape.older ? 'true' : null"
    >
      <title v-if="shape.derived && shape.label && shape.showLabel !== false">{{ shape.label }}</title>
    </path>
    <g
      v-for="link in links"
      :key="link.id"
      class="map-link"
      :class="[`map-link--${link.kind}`, { 'map-link--selected': link.selected, 'map-link--selectable': link.ref }]"
      :data-link="link.id"
      :data-link-ref="link.ref ?? null"
    >
      <path v-if="link.ref" :d="link.d" class="map-link__hit" />
      <path :d="link.d" class="map-link__casing" />
      <path :d="link.d" class="map-link__core" :class="{ 'map-link__core--oneway': !link.twoWay }" />
      <path v-for="(chevron, index) in link.chevrons" :key="index" :d="chevron" class="map-link__chevron" data-direction-chevron />
      <text v-if="link.label && link.showLabel !== false" :x="link.labelAt.x" :y="link.labelAt.y - 6" class="map-link__label">{{ link.label }}</text>
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
      :role="interactive ? 'button' : null"
      :tabindex="interactive ? 0 : null"
      :aria-label="interactive ? mark.label : null"
      :aria-pressed="interactive ? chosen.has(mark.id) : null"
      @click="onMarkClick(mark, $event)"
      @keydown="onMarkKey(mark, $event)"
    >
      <template v-if="mark.kind === 'room'">
        <rect x="-100" y="-26" width="200" height="52" rx="6" class="map-mark__card" />
        <template v-if="mark.showLabel !== false">
          <text y="-3" class="map-mark__card-name">{{ mark.label }}</text>
          <text y="17" class="map-mark__card-id">{{ mark.detail }}</text>
        </template>
      </template>
      <template v-else-if="mark.kind === 'exterior'">
        <rect x="-100" y="-26" width="200" height="52" rx="6" class="map-mark__card map-mark__card--exterior" />
        <template v-if="mark.showLabel !== false">
          <text y="-3" class="map-mark__card-name">{{ mark.label }}</text>
          <text y="17" class="map-mark__card-id">{{ mark.detail }}</text>
        </template>
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
        <text v-if="mark.showLabel !== false" y="-14" class="map-mark__label">{{ mark.label }}</text>
      </template>
      <template v-else>
        <circle r="16" class="map-mark__hit" />
        <template v-if="chosen.has(mark.id)">
          <circle r="14" class="map-mark__ring" />
          <path :d="brackets({ x: 0, y: 0 })" class="map-mark__brackets" />
        </template>
        <path v-if="mark.gateway" :d="gatePath()" class="map-mark__gate" />
        <circle v-else :r="NODE_DOT_R" class="map-mark__dot" />
        <text v-if="mark.showLabel !== false" y="-14" class="map-mark__label">{{ mark.label }}</text>
      </template>
    </g>
    <g v-for="(point, index) in pendingMarks" :key="`pending-${index}`" :transform="`translate(${point.x.toFixed(1)} ${point.y.toFixed(1)})`" data-pending-point>
      <rect x="-6" y="-6" width="12" height="12" transform="rotate(45)" class="map-mark__handle map-mark__handle--pending" />
    </g>
  </svg>
</template>
