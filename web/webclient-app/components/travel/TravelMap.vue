<script setup>
// TravelMap (OpenSpec changes wilderness-travel-interface and
// wilderness-travel-map-ui; interface design §4): the travel stage's
// full-bleed ink map in the HudFrame `backdrop` slot.
//
// Layers, bottom to top:
//   - the hatched fog: one surface for unknown ground inside and outside
//     the window (the painted canvas is transparent where nothing is known);
//   - the world: the painted canvas (lib/travel-paint.js, exactly
//     width x 12 by height x 12 pixels, scaled by a CSS transform), the SVG
//     overlay (live-sight ring, bearing rays, hover/aim cells, landmarks,
//     hostiles, the eight neighbour targets, the party seal) and the HTML
//     chips (names, hostile count/threat, ford, aim and hover readouts), all
//     moved together by one camera translation;
//   - screen chrome: the north mark and 5 km scale at the open stage's top
//     left, and the distant-sighting cards on the safe rectangle's edge.
//
// Repaint keys: the canvas repaints only when the grid's content signature
// (`paintSignature`) changes, once per animation frame however many
// publications arrive in it. Camera, zoom, UI scale, aim, hover, walking,
// the plan and the refresh status move or redraw overlays only.
//
// The camera follows the party (centred between the header and the band)
// or, for a locked plan while not walking, fits the party, route and
// destination between the side columns (lib/travel-camera.js). Bounds are
// measured from the real HudFrame through a ResizeObserver. It glides over
// 380 ms x --motion-travel; a zoom or a new map snaps.
//
// Status (from the base change): `ready` shows the adopted map at full
// strength; `refreshing` the last map dimmed (or the fog on a first load);
// `retired` the neutral fog; `unavailable` / `invalid` the last map dimmed
// with one status line and a 重新整理 control (the player's own input).
// Focus that was inside never falls to the document when an element goes
// away: it moves to the stage section itself. One mounted live region
// speaks the state.
//
// Intents (wilderness-travel-walking-ui, design §5): the map is one
// `role="application"` focus stop. It emits pointer `hover`/`pick` and
// `zoom`, and on its own focused root: `aim(direction)` and `hold(direction)`
// for each newly pressed arrow (two arrows combine into a diagonal through
// the compass key model), `release` when a held arrow is released or the map
// blurs, `step` for Enter and `cancel` for Escape while an aim or a walk
// stands (a bare Escape bubbles). Each keyboard intent carries its event, so
// the walking owner can tell an event that already stopped a walk. Native
// key repeat emits nothing; modified and composing keys are ignored. The
// store (stores/elosern/travel.js) owns the aim, the hold and the queue.
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import WorldHatchPattern from "../WorldHatchPattern.vue";
import MapNodeGlyph from "../MapNodeGlyph.vue";
import TravelGlyph from "./TravelGlyph.vue";
import { SAMPLES_PER_CELL, paintSignature, paintTravelMap } from "../../lib/travel-paint.js";
import {
  GLIDE_MS,
  ZOOM,
  bearingAngle,
  cellSize,
  fitRouteCamera,
  followCamera,
  openStage,
  projectSightings,
  safeScale,
  stepZoom,
} from "../../lib/travel-camera.js";
import { travelCellAt } from "../../lib/travel-grid.js";
import { TERRAIN_NAMES } from "../../lib/area_map_view.js";
import { TRAVEL_GLYPH_CELL } from "../../lib/map_glyphs.js";
import { ARROW_KEYS, directionForKeys } from "./travel-walk-model.js";

const props = defineProps({
  // The decoded travel grid (lib/travel-grid.js), or null before adoption.
  grid: { type: Object, default: null },
  // ready | refreshing | unavailable | invalid | retired
  status: { type: String, default: "refreshing" },
  // The aimed neighbour as a canonical direction word ("north", ...), or null.
  aim: { type: String, default: null },
  // The committed exit row for the aim refuses it (disabled, or no exit):
  // the aimed node is drawn blocked whatever the window's node says.
  aimBlocked: { type: Boolean, default: false },
  // The committed reason a blocked aim shows in its chip (`方位・阻擋原因`).
  aimReason: { type: String, default: null },
  // The walking state, or null while standing.
  walking: { type: Object, default: null },
  // The current travel.plan result ({ steps: [{x, y}], destination }), or null.
  plan: { type: Object, default: null },
  locked: { type: Boolean, default: false },
  motionLevel: { type: String, default: "full" },
  // The UI scale; null reads the stage's own `--ui-scale`.
  uiScale: { type: Number, default: null },
});
const emit = defineEmits(["aim", "hover", "pick", "step", "confirm", "cancel", "hold", "release", "zoom", "retry"]);

// The accessible name states the controls (design §5).
const CONTROLS_LABEL = "旅行地圖：方向鍵瞄準相鄰的格子，同時按兩個方向鍵為斜向；Enter 前進一步；按住方向鍵連續前進，放開或按任意鍵停步；Esc 取消瞄準；＋／－ 縮放。";

const DIRECTIONS = Object.freeze([
  { key: "north", dx: 0, dy: 1, word: "北" },
  { key: "northeast", dx: 1, dy: 1, word: "東北" },
  { key: "east", dx: 1, dy: 0, word: "東" },
  { key: "southeast", dx: 1, dy: -1, word: "東南" },
  { key: "south", dx: 0, dy: -1, word: "南" },
  { key: "southwest", dx: -1, dy: -1, word: "西南" },
  { key: "west", dx: -1, dy: 0, word: "西" },
  { key: "northwest", dx: -1, dy: 1, word: "西北" },
]);

// ── status ───────────────────────────────────────────────────────────────

const failed = computed(() => props.status === "unavailable" || props.status === "invalid");
const showMap = computed(() => !!props.grid && props.status !== "retired");
const stateText = computed(() =>
  props.status === "invalid" ? "無法讀取這一帶的地圖。" : "這一帶的地圖暫時無法更新。",
);
// A step's ready -> refreshing -> ready cycle keeps the same line, so a
// screen reader hears "updated" when the map first arrives, recovers or
// changes title, not on every step.
let readyLine = "";
const announcement = computed(() => {
  if (failed.value) return stateText.value;
  if (!showMap.value) return "正在展開這一帶的地圖。";
  if (props.status === "ready") readyLine = `${props.grid.title ?? ""}的地圖已更新。`;
  return readyLine;
});

const root = ref(null);
const canvas = ref(null);

function focusInside() {
  const active = typeof document === "undefined" ? null : document.activeElement;
  return !!(root.value && active && active !== root.value && root.value.contains(active));
}
function keepFocus() {
  nextTick(() => {
    const active = document.activeElement;
    if (!active || active === document.body || !root.value?.contains(active)) root.value?.focus({ preventScroll: true });
  });
}
// The retry control's removal or the map's disappearance: rescue focus that
// was inside before the patch.
watch(
  () => [failed.value, showMap.value],
  () => {
    if (focusInside()) keepFocus();
  },
  { flush: "pre" },
);
function onRetry() {
  emit("retry");
  keepFocus();
}

// ── measurement ──────────────────────────────────────────────────────────

const measured = ref({ stage: { left: 0, top: 0, right: 1200, bottom: 700 }, safe: { left: 0, top: 0, right: 1200, bottom: 700 }, scale: 1 });
let observer = null;
let observed = [];

function frameParts() {
  const stage = root.value?.closest?.(".elosern-stage") ?? null;
  return {
    stage,
    header: stage?.querySelector?.('[data-testid="stage-metrics"] [data-metric="--header-h"]') ?? null,
    band: stage?.querySelector?.('[data-testid="stage-band"]') ?? null,
    left: stage?.querySelector?.('[data-testid="anchor-vitals"]') ?? null,
    right: stage?.querySelector?.('[data-testid="anchor-map"]') ?? null,
  };
}

function rectOf(el) {
  if (!el?.getBoundingClientRect) return null;
  const r = el.getBoundingClientRect();
  return r.width > 0 && r.height > 0 ? r : null;
}

function measure() {
  const el = root.value;
  if (!el) return;
  const rootRect = el.getBoundingClientRect();
  if (!(rootRect.width > 0 && rootRect.height > 0)) return;
  const parts = frameParts();
  const styleScale =
    typeof getComputedStyle === "function" ? Number.parseFloat(getComputedStyle(el).getPropertyValue("--ui-scale")) : NaN;
  const scale = safeScale(props.uiScale ?? styleScale);
  const stageRect = rectOf(parts.stage) ?? rootRect;
  const headerH = parts.header?.getBoundingClientRect?.().height;
  const band = rectOf(parts.band);
  const { stage, safe } = openStage({
    root: rootRect,
    headerBottom: Number.isFinite(headerH) && headerH > 0 ? stageRect.top + headerH : null,
    bandTop: band ? band.top : null,
    left: rectOf(parts.left),
    right: rectOf(parts.right),
    gap: 16 * scale,
  });
  measured.value = { stage, safe, scale };
}

function observe() {
  observer?.disconnect();
  observed = [];
  if (typeof ResizeObserver !== "function") return;
  observer = new ResizeObserver(() => measure());
  const parts = frameParts();
  for (const el of [root.value, parts.band, parts.left, parts.right, parts.header]) {
    if (el) {
      observer.observe(el);
      observed.push(el);
    }
  }
}

// ── camera ───────────────────────────────────────────────────────────────

const zoom = ref(ZOOM.initial);
const uiScaleNow = computed(() => safeScale(props.uiScale ?? measured.value.scale));
const baseCell = computed(() => cellSize(zoom.value, uiScaleNow.value));

const camera = computed(() => {
  const grid = props.grid;
  if (!grid) return { tx: 0, ty: 0, cellPx: baseCell.value };
  const plan = props.plan;
  if (plan && props.locked && !props.walking) {
    const points = [grid.party, ...(Array.isArray(plan.steps) ? plan.steps : []), plan.destination].filter(Boolean);
    return fitRouteCamera({ points, cellPx: baseCell.value, minCellPx: 14 * uiScaleNow.value, safe: measured.value.safe });
  }
  return followCamera({ party: grid.party, cellPx: baseCell.value, stage: measured.value.stage });
});
const c = computed(() => camera.value.cellPx);

// A zoom, a new map or the first frame snaps instead of gliding.
const snapping = ref(true);
let snapFrame = 0;
function snap() {
  snapping.value = true;
  if (typeof requestAnimationFrame !== "function") return;
  cancelAnimationFrame(snapFrame);
  snapFrame = requestAnimationFrame(() => {
    snapFrame = requestAnimationFrame(() => {
      snapping.value = false;
    });
  });
}
watch(c, snap);
watch(() => props.grid?.mapId ?? null, snap);

const worldStyle = computed(() => ({
  transform: `translate(${camera.value.tx}px, ${camera.value.ty}px)`,
  "--travel-glide": `${GLIDE_MS}ms`,
}));

// ── painting ─────────────────────────────────────────────────────────────

const painted = ref(null); // { origin, width, height } of the canvas's grid
const paintCache = {};
let paintFrame = 0;
let lastSignature = null;

function paintNow() {
  paintFrame = 0;
  const grid = props.grid;
  const el = canvas.value;
  if (!grid || !el || !showMap.value) return;
  const signature = paintSignature(grid);
  if (signature === lastSignature) return;
  const w = grid.width * SAMPLES_PER_CELL;
  const h = grid.height * SAMPLES_PER_CELL;
  if (el.width !== w) el.width = w;
  if (el.height !== h) el.height = h;
  const ctx = el.getContext?.("2d") ?? null;
  if (!ctx) return;
  paintTravelMap(ctx, grid, { cache: paintCache });
  lastSignature = signature;
  painted.value = { origin: { ...grid.origin }, width: grid.width, height: grid.height };
}

function schedulePaint() {
  if (paintFrame) return;
  if (typeof requestAnimationFrame !== "function") {
    paintNow();
    return;
  }
  paintFrame = requestAnimationFrame(paintNow);
}
watch(() => [props.grid, showMap.value], schedulePaint);

const canvasStyle = computed(() => {
  const p = painted.value;
  if (!p) return { visibility: "hidden" };
  return {
    left: `${p.origin.x * c.value}px`,
    top: `${-(p.origin.y + p.height) * c.value}px`,
    transform: `scale(${c.value / SAMPLES_PER_CELL})`,
  };
});

// ── overlay model ────────────────────────────────────────────────────────

// The overlay and chip layers sit on the current grid's window, so cell
// coordinates inside them are local to its north-west corner.
const layerStyle = computed(() => {
  const grid = props.grid;
  if (!grid) return {};
  return {
    left: `${grid.origin.x * c.value}px`,
    top: `${-(grid.origin.y + grid.height) * c.value}px`,
    width: `${grid.width * c.value}px`,
    height: `${grid.height * c.value}px`,
  };
});
function lx(x) {
  return (x - props.grid.origin.x + 0.5) * c.value;
}
function ly(y) {
  return (props.grid.origin.y + props.grid.height - 1 - y + 0.5) * c.value;
}
function cellBox(x, y, inset = 1) {
  return { x: lx(x) - c.value / 2 + inset, y: ly(y) - c.value / 2 + inset, width: c.value - inset * 2, height: c.value - inset * 2 };
}
// Never below 0.75, so the smallest target stays perceivable at minimum zoom.
const glyphScale = computed(() => Math.max(0.75, c.value / TRAVEL_GLYPH_CELL));
const party = computed(() => props.grid?.party ?? null);
const partyInWindow = computed(() => !!party.value && !!travelCellAt(props.grid, party.value.x, party.value.y));
const radius = computed(() => (typeof props.grid?.groundRadius === "number" ? props.grid.groundRadius : null));

function terrainLabel(cell) {
  return cell.display?.terrain_label ?? TERRAIN_NAMES[cell.terrain] ?? cell.terrain;
}

const neighbours = computed(() => {
  const grid = props.grid;
  if (!grid || !partyInWindow.value || props.walking) return [];
  const out = [];
  for (const d of DIRECTIONS) {
    const cell = travelCellAt(grid, grid.party.x + d.dx, grid.party.y + d.dy);
    if (!cell) continue;
    const state = !cell.known ? "unknown" : cell.node?.action ? "open" : "blocked";
    const aimedHere = props.aim === d.key && state === "open";
    out.push({ ...d, cell, state: aimedHere ? (props.aimBlocked ? "blocked" : "aimed") : state });
  }
  return out;
});
const aimed = computed(() => neighbours.value.find((n) => n.key === props.aim) ?? null);
const aimText = computed(() => {
  const n = aimed.value;
  if (!n) return "";
  if (n.state === "blocked" && props.aimReason) return `${n.word}・${props.aimReason}`;
  return `${n.word}・${n.cell.known ? terrainLabel(n.cell) : "未探明"}`;
});

const landmarks = computed(() =>
  (props.grid?.cells ?? [])
    .filter((cell) => cell.known && typeof cell.node?.landmark?.name === "string" && cell.node.landmark.name)
    .map((cell) => ({ key: `${cell.x}:${cell.y}`, x: cell.x, y: cell.y, name: cell.node.landmark.name })),
);
// One label per crossing: a ford cell within three cells of an already-labelled one of
// the same name (a crossing several cells long) adds no second chip.
const fords = computed(() => {
  const out = [];
  for (const cell of props.grid?.cells ?? []) {
    const label = cell.known && cell.ford ? cell.display?.ford_label : null;
    if (typeof label !== "string" || !label) continue;
    if (out.some((f) => f.label === label && Math.abs(f.x - cell.x) <= 3 && Math.abs(f.y - cell.y) <= 3)) continue;
    out.push({ key: `${cell.x}:${cell.y}`, x: cell.x, y: cell.y, label });
  }
  return out;
});
const hostiles = computed(() =>
  (props.grid?.entities ?? [])
    .filter((e) => e?.hostile === true && e.cell && travelCellAt(props.grid, e.cell.x, e.cell.y))
    .map((e) => ({
      id: e.id,
      x: e.cell.x,
      y: e.cell.y,
      label: e.label,
      count: Number.isSafeInteger(e.count) && e.count > 1 ? e.count : null,
      threat: typeof e.threat === "string" && e.threat ? e.threat : null,
    })),
);

const hoverCell = ref(null);
const hoverInfo = computed(() => {
  const h = hoverCell.value;
  const grid = props.grid;
  if (!h || !grid || props.walking) return null;
  const cell = travelCellAt(grid, h.x, h.y);
  if (!cell) return null;
  if (!cell.known) return { ...h, text: "未探明", known: false };
  const name = cell.node?.landmark?.name;
  return { ...h, text: name || terrainLabel(cell), known: true };
});

// Bearing rays leave the party past its live sight.
const rays = computed(() => {
  const grid = props.grid;
  if (!grid || !partyInWindow.value) return [];
  const r = radius.value ?? 2;
  return (grid.sightings ?? [])
    .map((s, index) => ({ s, index, angle: bearingAngle(s?.bearing) }))
    .filter((item) => item.angle !== null)
    .map(({ index, angle }) => {
      const ux = Math.sin(angle);
      const uy = -Math.cos(angle);
      const ox = lx(grid.party.x);
      const oy = ly(grid.party.y);
      return {
        key: `ray-${index}`,
        x1: ox + ux * (r + 1) * c.value,
        y1: oy + uy * (r + 1) * c.value,
        x2: ox + ux * (r + 4.5) * c.value,
        y2: oy + uy * (r + 4.5) * c.value,
      };
    });
});

const sightingCards = computed(() => {
  const grid = props.grid;
  if (!grid) return [];
  const s = uiScaleNow.value;
  return projectSightings(grid.sightings ?? [], { safe: measured.value.safe, inset: { x: 120 * s, y: 38 * s } }).map(
    (item, index) => ({
      key: `${index}:${item.sighting.bearing}`,
      left: `${item.x}px`,
      top: `${item.y}px`,
      head: `${item.sighting.bearing}・約 ${item.sighting.distance_km} 公里`,
      body: item.sighting.silhouette_zh,
      name: item.sighting.name ?? null,
    }),
  );
});

const legendStyle = computed(() => {
  const s = uiScaleNow.value;
  return { left: `${measured.value.stage.left + 22 * s}px`, top: `${measured.value.stage.top + 18 * s}px` };
});
const scaleBar = computed(() => {
  const km = props.grid?.cellKm;
  return Number.isFinite(km) && km > 0 ? (5 / km) * c.value : null;
});

// ── pointer and zoom ─────────────────────────────────────────────────────

// The world layer's live on-screen origin, so a pointer mid-glide resolves
// against what is drawn, not where the camera is heading.
const world = ref(null);
function cellFromEvent(event) {
  const grid = props.grid;
  if (!grid || !world.value) return null;
  const origin = world.value.getBoundingClientRect();
  const wx = event.clientX - origin.left;
  const wy = event.clientY - origin.top;
  const x = Math.floor(wx / c.value);
  const y = Math.ceil(-wy / c.value) - 1;
  return travelCellAt(grid, x, y) ? { x, y } : null;
}
function sameCell(a, b) {
  return a === b || (!!a && !!b && a.x === b.x && a.y === b.y);
}
const interactive = computed(() => showMap.value && props.status === "ready");
function clearHover() {
  if (hoverCell.value === null) return;
  hoverCell.value = null;
  emit("hover", null);
}
// A map that stops being the current one drops its hover.
watch(interactive, (now) => {
  if (!now) clearHover();
});
function onPointerMove(event) {
  if (props.walking || !interactive.value) return;
  const cell = cellFromEvent(event);
  if (sameCell(cell, hoverCell.value)) return;
  hoverCell.value = cell;
  emit("hover", cell);
}
function onPointerLeave() {
  clearHover();
}
function onClick(event) {
  if (event.target?.closest?.(".travel-map__state")) return;
  root.value?.focus({ preventScroll: true });
  if (!interactive.value) return;
  const cell = cellFromEvent(event);
  if (cell) emit("pick", cell);
}
function zoomBy(direction) {
  const next = stepZoom(zoom.value, direction);
  if (next === zoom.value) return;
  zoom.value = next;
  emit("zoom", next);
}
// Wheel travel accumulates to one zoom step per notch (100 px of delta), so
// a trackpad's stream of small deltas does not slam the zoom to a clamp.
const WHEEL_STEP = 100;
let wheelTravel = 0;
function onWheel(event) {
  if (!showMap.value || event.deltaY === 0) return;
  event.preventDefault();
  const unit = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? 800 : 1;
  if (Math.sign(event.deltaY) !== Math.sign(wheelTravel)) wheelTravel = 0;
  wheelTravel += event.deltaY * unit;
  while (Math.abs(wheelTravel) >= WHEEL_STEP) {
    zoomBy(wheelTravel < 0 ? 1 : -1);
    wheelTravel -= Math.sign(wheelTravel) * WHEEL_STEP;
  }
}
// The arrows held on the focused map, in press order.
const pressed = new Set();
function modified(event) {
  return event.ctrlKey || event.altKey || event.metaKey || event.isComposing || event.keyCode === 229;
}
function consume(event) {
  event.preventDefault();
  event.stopPropagation();
}
function onKeyDown(event) {
  if (event.target !== root.value || modified(event)) return;
  if (ARROW_KEYS.includes(event.key)) {
    if (event.shiftKey) return;
    consume(event);
    // Native repeat of a held arrow is no new input: the walk owner reads
    // it as the hold's continuation.
    if (event.repeat || pressed.has(event.key)) return;
    pressed.add(event.key);
    const direction = directionForKeys(pressed);
    if (direction) {
      emit("aim", direction, event);
      emit("hold", direction, event);
    }
    return;
  }
  if (event.key === "Enter") {
    consume(event);
    if (!event.repeat) emit("step", event);
    return;
  }
  if (event.key === "Escape") {
    if (!props.aim && !props.walking) return;
    consume(event);
    emit("cancel", event);
    return;
  }
  if (event.key === "+" || event.key === "=") {
    event.preventDefault();
    event.stopPropagation();
    zoomBy(1);
  } else if (event.key === "-" || event.key === "_") {
    event.preventDefault();
    event.stopPropagation();
    zoomBy(-1);
  }
}

function onKeyUp(event) {
  if (pressed.delete(event.key)) {
    event.stopPropagation();
    emit("release", event);
  }
}
function onBlur() {
  const held = pressed.size > 0;
  pressed.clear();
  if (held || props.walking) emit("release", null);
}

// ── lifecycle ────────────────────────────────────────────────────────────

function onWindowResize() {
  measure();
}
onMounted(() => {
  measure();
  observe();
  if (typeof window !== "undefined") window.addEventListener("resize", onWindowResize);
  snap();
  schedulePaint();
});
watch(() => props.uiScale, measure);
onBeforeUnmount(() => {
  observer?.disconnect();
  observer = null;
  observed = [];
  if (typeof window !== "undefined") window.removeEventListener("resize", onWindowResize);
  if (typeof cancelAnimationFrame === "function") {
    cancelAnimationFrame(paintFrame);
    cancelAnimationFrame(snapFrame);
  }
  paintFrame = 0;
});

defineExpose({ focusInside, focus: () => root.value?.focus({ preventScroll: true }), el: () => root.value });
</script>

<template>
  <section
    class="travel-map"
    :class="{ 'is-night': grid?.lightPhase === 'night', 'is-walking': !!walking }"
    data-testid="travel-map"
    :data-map-status="status"
    :data-map-shown="showMap ? 'true' : 'false'"
    :data-motion="motionLevel"
    :data-zoom="zoom"
    :data-cell-px="c"
    role="application"
    :aria-label="CONTROLS_LABEL"
    tabindex="0"
    ref="root"
    @pointermove="onPointerMove"
    @pointerleave="onPointerLeave"
    @click="onClick"
    @wheel="onWheel"
    @keydown="onKeyDown"
    @keyup="onKeyUp"
    @blur="onBlur"
  >
    <svg class="travel-map__fog" aria-hidden="true" focusable="false">
      <defs><WorldHatchPattern id="travel-map-fog" /></defs>
      <rect width="100%" height="100%" fill="url(#travel-map-fog)" />
    </svg>
    <div
      v-show="showMap"
      ref="world"
      class="travel-map__world"
      :class="{ 'is-snap': snapping }"
      :style="worldStyle"
      data-testid="travel-map__world"
    >
      <canvas ref="canvas" class="travel-map__canvas" :style="canvasStyle" data-testid="travel-map__canvas" aria-hidden="true"></canvas>
      <template v-if="grid">
        <svg
          class="travel-map__overlay"
          :style="layerStyle"
          :width="grid.width * c"
          :height="grid.height * c"
          aria-hidden="true"
          focusable="false"
          data-testid="travel-map__overlay"
        >
          <circle
            v-if="radius !== null && partyInWindow"
            class="travel-map__sight"
            data-testid="travel-map__sight"
            :cx="lx(party.x)"
            :cy="ly(party.y)"
            :r="(radius + 0.5) * c"
          />
          <line v-for="ray in rays" :key="ray.key" class="travel-map__ray" :x1="ray.x1" :y1="ray.y1" :x2="ray.x2" :y2="ray.y2" />
          <rect
            v-if="hoverInfo"
            class="travel-map__hover"
            :class="{ 'is-fog': !hoverInfo.known }"
            data-testid="travel-map__hover"
            v-bind="cellBox(hoverInfo.x, hoverInfo.y, 1)"
            rx="2"
          />
          <rect
            v-if="aimed && aimed.state === 'aimed'"
            class="travel-map__aim-cell"
            v-bind="cellBox(aimed.cell.x, aimed.cell.y, 1)"
            rx="3"
          />
          <g v-for="l in landmarks" :key="l.key" :transform="`translate(${lx(l.x)} ${ly(l.y)})`">
            <TravelGlyph kind="landmark" :size="glyphScale * 2.2" test-id="travel-map__landmark" />
          </g>
          <g v-for="h in hostiles" :key="h.id" :transform="`translate(${lx(h.x)} ${ly(h.y)})`">
            <TravelGlyph kind="hostile" :size="glyphScale" test-id="travel-map__hostile" />
          </g>
          <g v-for="n in neighbours" :key="n.key" :transform="`translate(${lx(n.cell.x)} ${ly(n.cell.y)})`">
            <TravelGlyph kind="neighbour" :state="n.state" :size="glyphScale" test-id="travel-map__neighbour" />
          </g>
          <g v-if="partyInWindow" class="travel-map__party" :transform="`translate(${lx(party.x)} ${ly(party.y)})`">
            <MapNodeGlyph state="party" :size="glyphScale" :test-ids="{ marker: 'travel-map__party' }" />
          </g>
        </svg>
        <div class="travel-map__chips" :style="layerStyle" aria-hidden="true">
          <div
            v-for="l in landmarks"
            :key="`chip-${l.key}`"
            class="tm-chip tm-chip--gold"
            data-side="above"
            :style="{ left: `${lx(l.x)}px`, top: `${ly(l.y) - c * 0.55}px` }"
          >{{ l.name }}</div>
          <div
            v-for="h in hostiles"
            :key="`chip-${h.id}`"
            class="tm-chip tm-chip--seal"
            :style="{ left: `${lx(h.x)}px`, top: `${ly(h.y) + c * 0.48}px` }"
          >{{ h.label }}<template v-if="h.count"> ×{{ h.count }}</template><template v-if="h.threat">・<b>{{ h.threat }}</b></template></div>
          <div
            v-for="f in fords"
            :key="`ford-${f.key}`"
            class="tm-chip tm-chip--quiet"
            :style="{ left: `${lx(f.x)}px`, top: `${ly(f.y) + c * 0.5}px` }"
          >{{ f.label }}</div>
          <div
            v-if="aimed"
            class="tm-chip tm-chip--aim"
            :class="{ 'is-blocked': aimed.state !== 'aimed' }"
            data-testid="travel-map__aim-chip"
            :data-side="aimed.dx >= 0 ? 'right' : 'left'"
            :style="{ left: `${lx(aimed.cell.x) + (aimed.dx >= 0 ? c * 0.7 : -c * 0.7)}px`, top: `${ly(aimed.cell.y)}px` }"
          >{{ aimText }}</div>
          <div
            v-else-if="hoverInfo"
            class="tm-chip"
            :class="hoverInfo.known ? 'tm-chip--paper' : 'tm-chip--quiet'"
            data-side="above"
            data-testid="travel-map__hover-chip"
            :style="{ left: `${lx(hoverInfo.x)}px`, top: `${ly(hoverInfo.y) - c * 0.6}px` }"
          >{{ hoverInfo.text }}</div>
        </div>
      </template>
    </div>
    <div v-if="showMap" class="tm-legend" :style="legendStyle" aria-hidden="true" data-testid="travel-map__legend">
      <svg class="tm-legend__rose" viewBox="-20 -20 40 40">
        <circle r="15" class="tm-legend__ring" />
        <path d="M0 -17 L4 0 L0 4 L-4 0 Z" class="tm-legend__north" />
        <path d="M0 17 L4 0 L0 -4 L-4 0 Z" class="tm-legend__south" />
        <path d="M-17 0 L0 -2.5 L17 0 L0 2.5 Z" class="tm-legend__south" />
      </svg>
      <span class="tm-legend__n">北</span>
      <span v-if="scaleBar !== null" class="tm-legend__scale">
        <span class="tm-legend__bar" data-testid="travel-map__scale-bar" :style="{ width: `${scaleBar}px` }"></span>
        5 公里
      </span>
    </div>
    <template v-if="showMap">
      <div
        v-for="card in sightingCards"
        :key="card.key"
        class="tm-sighting"
        data-testid="travel-map__sighting"
        :style="{ left: card.left, top: card.top }"
      >
        <span class="tm-sighting__bearing">{{ card.head }}</span>
        <span class="tm-sighting__what">{{ card.body }}<template v-if="card.name">（{{ card.name }}）</template></span>
      </div>
    </template>
    <p class="travel-map__live" role="status" data-testid="travel-map__live">{{ announcement }}</p>
    <div v-if="failed" class="travel-map__state" data-testid="travel-map__state">
      <span class="travel-map__state-text">{{ stateText }}</span>
      <button
        type="button"
        class="travel-map__retry"
        data-testid="travel-map__retry"
        @click="onRetry"
        @keydown.enter.stop
        @keydown.space.stop
      >重新整理</button>
    </div>
  </section>
</template>

<style>
/* The full-bleed ink ground: the one hatched fog surface under the map, so
   unknown land inside and outside the window reads as one cloth. */
.travel-map {
  position: absolute;
  inset: 0;
  z-index: 0;
  overflow: hidden;
  outline: none;
  cursor: crosshair;
  background:
    radial-gradient(90% 80% at 50% 42%, #221f1a 0%, #161411 52%, var(--ink-950) 100%);
}
/* The focus ring is an inset frame around the open stage, clear of the
   header and the band. */
.travel-map:focus-visible::after {
  content: "";
  position: absolute;
  inset: calc(var(--header-h) + 6px * var(--ui-scale)) calc(6px * var(--ui-scale)) calc(var(--band-h) + 6px * var(--ui-scale));
  border: 1px solid rgba(228, 200, 142, 0.42);
  border-radius: var(--radius);
  box-shadow: inset 0 0 0 1px rgba(228, 200, 142, 0.12);
  pointer-events: none;
}
.travel-map__live {
  position: absolute;
  width: 1px;
  height: 1px;
  margin: -1px;
  padding: 0;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}
.travel-map__fog {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}
/* The world layer: one translation moves the canvas, the overlay and the
   chips together. It glides at full motion and lands at once otherwise. */
.travel-map__world {
  position: absolute;
  left: 0;
  top: 0;
  width: 0;
  height: 0;
  transition:
    transform calc(var(--travel-glide) * var(--motion-travel)) var(--ease-standard),
    opacity var(--motion-base) var(--ease-standard),
    filter var(--motion-base) var(--ease-standard);
  will-change: transform;
}
.travel-map__world.is-snap,
.travel-map[data-motion="off"] .travel-map__world {
  transition: opacity var(--motion-base) var(--ease-standard), filter var(--motion-base) var(--ease-standard);
}
.travel-map[data-motion="off"] .travel-map__world {
  transition: none;
}
/* A map that is not the current one yet is drawn as memory: dimmed and
   drained, so the stale image never reads as the present. */
.travel-map:not([data-map-status="ready"]) .travel-map__world {
  opacity: 0.55;
  filter: saturate(0.45) brightness(0.8);
}
.travel-map__canvas {
  position: absolute;
  transform-origin: 0 0;
  image-rendering: auto;
}
.travel-map__overlay,
.travel-map__chips {
  position: absolute;
  overflow: visible;
  pointer-events: none;
}

.travel-map__sight {
  fill: none;
  stroke: rgba(242, 236, 223, 0.26);
  stroke-width: 1;
  stroke-dasharray: 2 6;
}
.travel-map.is-night .travel-map__sight {
  stroke: rgba(170, 190, 230, 0.36);
}
.travel-map__ray {
  stroke: rgba(228, 200, 142, 0.5);
  stroke-width: 1.2;
  stroke-dasharray: 1 6;
  stroke-linecap: round;
}
.travel-map__hover {
  fill: rgba(242, 236, 223, 0.06);
  stroke: rgba(242, 236, 223, 0.5);
  stroke-width: 1;
}
.travel-map__hover.is-fog {
  fill: none;
  stroke: rgba(242, 236, 223, 0.24);
  stroke-dasharray: 3 3;
}
.travel-map__aim-cell {
  fill: rgba(228, 200, 142, 0.14);
  stroke: var(--gold-400);
  stroke-width: 1.2;
}

.tm-chip {
  position: absolute;
  transform: translate(-50%, 0);
  white-space: nowrap;
  padding: calc(2px * var(--ui-scale)) calc(9px * var(--ui-scale));
  border-radius: calc(4px * var(--ui-scale));
  font: var(--text-xs)/1.35 var(--f-sans);
  letter-spacing: 0.04em;
  pointer-events: none;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.45);
}
.tm-chip[data-side="right"] {
  transform: translate(0, -50%);
}
.tm-chip[data-side="left"] {
  transform: translate(-100%, -50%);
}
.tm-chip[data-side="above"] {
  transform: translate(-50%, -100%);
}
.tm-chip--gold {
  color: var(--gold-300);
  background: rgba(15, 17, 21, 0.88);
  border: 1px solid rgba(143, 113, 60, 0.9);
  font-family: var(--f-serif);
}
.tm-chip--seal {
  color: #f2d6d0;
  background: rgba(52, 16, 18, 0.9);
  border: 1px solid var(--seal-600);
}
.tm-chip--seal b {
  font-weight: 600;
  color: #ffb4a6;
}
.tm-chip--quiet {
  color: var(--paper-400);
  background: rgba(15, 17, 21, 0.72);
  border: 1px dashed rgba(186, 181, 174, 0.3);
}
.tm-chip--paper {
  color: var(--paper-50);
  background: rgba(15, 17, 21, 0.86);
  border: 1px solid rgba(242, 236, 223, 0.25);
}
.tm-chip--aim {
  color: var(--gold-300);
  background: rgba(15, 17, 21, 0.9);
  border: 1px solid var(--gold-600);
}
.tm-chip--aim.is-blocked {
  color: var(--paper-400);
  border-style: dashed;
  border-color: var(--paper-700);
}

/* Orientation: a north mark and a five-kilometre bar at the open stage's
   top left, in the band ornament's gold. */
.tm-legend {
  position: absolute;
  z-index: 1;
  display: grid;
  grid-template-columns: auto auto;
  align-items: center;
  column-gap: calc(10px * var(--ui-scale));
  row-gap: calc(4px * var(--ui-scale));
  pointer-events: none;
}
.tm-legend__rose {
  width: calc(44px * var(--ui-scale));
  height: calc(44px * var(--ui-scale));
  grid-row: span 2;
  filter: drop-shadow(0 2px 6px rgba(0, 0, 0, 0.5));
}
.tm-legend__ring {
  fill: rgba(11, 13, 16, 0.72);
  stroke: rgba(185, 154, 96, 0.6);
  stroke-width: 0.8;
}
.tm-legend__north {
  fill: var(--gold-400);
}
.tm-legend__south {
  fill: rgba(186, 181, 174, 0.45);
}
.tm-legend__n {
  font: var(--text-xs)/1 var(--f-display);
  color: var(--gold-400);
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.8);
}
.tm-legend__scale {
  display: grid;
  gap: calc(3px * var(--ui-scale));
  font: var(--text-xs)/1 var(--f-sans);
  color: var(--paper-300);
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.8);
}
.tm-legend__bar {
  display: block;
  height: calc(5px * var(--ui-scale));
  border: 1px solid rgba(201, 196, 185, 0.7);
  border-top: 0;
  transition: width var(--motion-base) var(--ease-standard);
}
/* Distant sightings: cards on the safe rectangle's edge along their bearing. */
.tm-sighting {
  position: absolute;
  z-index: 1;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: calc(1px * var(--ui-scale));
  padding: calc(5px * var(--ui-scale)) calc(12px * var(--ui-scale));
  border-radius: calc(6px * var(--ui-scale));
  background: linear-gradient(180deg, rgba(20, 19, 22, 0.92), rgba(12, 13, 16, 0.92));
  border: 1px solid rgba(185, 154, 96, 0.55);
  box-shadow: 0 4px 18px rgba(0, 0, 0, 0.5);
  pointer-events: none;
  white-space: nowrap;
}
.tm-sighting__bearing {
  font: var(--text-xs)/1.3 var(--f-sans);
  color: var(--gold-400);
  letter-spacing: 0.06em;
}
.tm-sighting__what {
  font: var(--text-sm)/1.3 var(--f-serif);
  color: var(--paper-50);
}
.travel-map.is-night .tm-sighting {
  border-color: rgba(170, 190, 230, 0.5);
}
.travel-map.is-night .tm-sighting__bearing {
  color: #c8d4ee;
}

/* The failure line: a quiet ink plate centred in the open stage, between the
   header and the band, with the gold hairline of the shared islands. */
.travel-map__state {
  position: absolute;
  left: 50%;
  top: calc(var(--header-h) + (100% - var(--header-h) - var(--band-h)) / 2);
  transform: translate(-50%, -50%);
  z-index: 2;
  display: flex;
  align-items: center;
  gap: calc(14px * var(--ui-scale));
  padding: calc(10px * var(--ui-scale)) calc(12px * var(--ui-scale)) calc(10px * var(--ui-scale)) calc(18px * var(--ui-scale));
  border: 1px solid rgba(185, 154, 96, 0.38);
  border-radius: var(--radius);
  background: var(--panel);
  box-shadow: var(--shadow);
  backdrop-filter: blur(6px);
  font: var(--text-sm)/1.4 var(--f-serif);
  color: var(--paper-200);
  white-space: nowrap;
  cursor: default;
}
.travel-map__retry {
  flex: none;
  min-height: calc(36px * var(--ui-scale));
  padding: 0 calc(14px * var(--ui-scale));
  border: 1px solid var(--gold-600);
  border-radius: var(--radius-sm);
  background: rgba(185, 154, 96, 0.1);
  color: var(--gold-300);
  font: var(--text-sm)/1 var(--f-sans);
  cursor: pointer;
  transition: background var(--motion-fast) var(--ease-standard), border-color var(--motion-fast) var(--ease-standard);
}
.travel-map__retry:hover {
  background: rgba(185, 154, 96, 0.2);
  border-color: var(--gold-400);
}
.travel-map__retry:focus-visible {
  outline: none;
  box-shadow: var(--focus);
}
</style>
