<script setup>
// The world tab's map (OpenSpec change render-world-map-view; approved
// design docs/superpowers/specs/2026-10-22-world-map-drawer-design.md §4.4,
// §6.2-§6.5). It draws one validated `world_map` v1 body and nothing else.
//
// Layers, bottom to top, each a `<g data-layer>` in exactly this order: sea,
// land, lit terrain (wash, terrain tints, rivers, ridge, roads of lit
// districts), unlit hatching, district borders, national borders,
// coastline, trail, approximate-commission circles, places and landmarks,
// commission markers, current position, labels, chrome. Lit and unlit
// districts differ by fill (terrain ink versus hatching), border style
// (solid versus dotted) and label (name versus 未探明), not by colour alone.
// An unlit district is only its supplied outline and opaque id: nothing in
// this file reads, draws or hit-tests a landmark, name, nation or place for
// it. An approximate commission is a dashed circle labelled 大致方位 with
// no centre point.
//
// Level of detail (lib/world_map_view.js lodFor, inclusive): nation names at
// the 大陸 and 國 views, lit district and place names up to 1000 km, 未探明
// up to 450 km, and the trail as cells (at the payload's own 1 or 5 km
// resolution) only at the 近郊 view. Labels are screen-space SVG text, at
// least 16 CSS px times the UI scale; a lower-priority label that collides
// is hidden, never shrunk.
//
// Discovery: the component remembers the last payload it presented. A
// district that was unlit in it and is lit in the next one, observed while
// mounted, spreads its ink from its landmark for the `--motion-district-
// reveal` token (600 ms at `full`, 0 at `reduced`/`off`, which places it
// instantly) and announces `已探明：<district>` once in a live region. The
// first payload, a repeated payload, a remount, a new `epoch` and a payload
// in which a lit district went dark (someone else's knowledge) re-baseline
// silently. Nothing here writes knowledge.
//
// Host contract (MapDrawer, redesign-map-drawer): `v-model:view`
// (`{ signature, cx, cy, span }`, signature `world|elosern|km`) and
// `v-model:selected` (`district:<id>`, `place:<id>` or `quest:<id>`) keep the
// tab's session memory, and `epoch` is the transport/puppet epoch. `select`
// carries the semantic reading (featureDetail). The exposed `zoomIn`,
// `zoomOut`, `recentre`, `showWhole`, `panBy`, `stops` and `stopLabel` drive
// the host's pill and keyboard. Keyboard focus stays in real HTML: a list of
// buttons, one per selectable feature (roving tabindex, ↑/↓/Home/End),
// whose focus draws a ring on the map and pans it into view. This component
// requests no data and owns no drawer chrome.
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import WorldMapDetail from "./WorldMapDetail.vue";
import {
  DETAIL_DRAWER_WIDTH,
  DRAG_THRESHOLD_PX,
  centreOn,
  nearestStop,
  nextStop,
  panByPixels,
  previousStop,
  project,
  scaleBar,
  spanLimits,
  usableRect,
  wheelFactor,
  zoomAt,
  zoomBy,
  UNITS,
} from "../lib/map_viewport.js";
import { readMotionMs } from "../lib/motion_tokens.js";
import {
  APPROXIMATE_MIN_RADIUS_PX,
  APPROXIMATE_RADIUS_KM,
  LABEL_FONT_PX,
  NATION_FONT_PX,
  REVEAL_TOKEN,
  WORLD_SIGNATURE,
  estimateTextWidth,
  featureDetail,
  featureKeys,
  featureName,
  featurePoint,
  labelCandidates,
  linesPath,
  lodFor,
  openingView,
  placeWorldLabels,
  placesOf,
  revealRadiusKm,
  revealTransitions,
  ringsPath,
  trailCellCount,
  trailCellsPath,
  trailGridKm,
  trailLinePath,
  wholeView,
  worldStopsFor,
} from "../lib/world_map_view.js";

const props = defineProps({
  // A validated world_map v1 body in its available form. Replace it with a
  // new object for every publication, never mutate it in place: per-payload
  // derivations are memoised on its identity.
  world: { type: Object, required: true },
  // Controlled view `{ signature, cx, cy, span }`; undefined = uncontrolled.
  view: { type: Object, default: undefined },
  // Controlled selection key; undefined = uncontrolled.
  selected: { type: String, default: undefined },
  // Render the selection reading inside the map (the host may supply its own).
  showDetail: { type: Boolean, default: true },
  // The host's transport/puppet epoch: a change re-baselines discovery.
  epoch: { type: [String, Number], default: null },
});
const emit = defineEmits(["update:view", "update:selected", "select"]);

const FALLBACK_FRAME = Object.freeze({ width: 960, height: 600 });
// The smallest measured box the opening fit (96 px margins) can use.
const MIN_FRAME_PX = 240;

let instanceCounter = 0;
const uid = `world-map-${(instanceCounter += 1)}-${Math.random().toString(36).slice(2, 8)}`;

const surface = ref(null);
const frame = ref(FALLBACK_FRAME);
const measured = ref(false);
const uiScale = ref(1);

function readUiScale() {
  if (typeof window === "undefined" || typeof document === "undefined") return 1;
  const raw = Number.parseFloat(window.getComputedStyle(document.documentElement).getPropertyValue("--ui-scale"));
  return Number.isFinite(raw) && raw > 0 ? raw : 1;
}

// ── view ────────────────────────────────────────────────────────────────

const stops = computed(() => worldStopsFor(props.world, frame.value));
const limits = computed(() => spanLimits(stops.value));
const localView = ref(null);
let viewIsOpening = false;

function validView(view) {
  return !!view && view.signature === WORLD_SIGNATURE && [view.cx, view.cy, view.span].every(Number.isFinite) && view.span > 0;
}

function commitView(next, { opening = false } = {}) {
  const view = Object.freeze({ signature: WORLD_SIGNATURE, cx: next.cx, cy: next.cy, span: next.span });
  viewIsOpening = opening;
  localView.value = view;
  emit("update:view", view);
}

function openView() {
  commitView(openingView(props.world, frame.value, stops.value), { opening: true });
}

if (validView(props.view)) localView.value = props.view;
else openView();

watch(
  () => props.view,
  (next) => {
    // Compare by value: a host that clones or serialises its echo of our own
    // emit must not cancel the post-measure opening re-fit.
    const current = localView.value;
    const same = !!current && next && next.cx === current.cx && next.cy === current.cy && next.span === current.span;
    if (validView(next) && !same) {
      localView.value = next;
      viewIsOpening = false;
    }
  },
);

const view = computed(() => (validView(localView.value) ? localView.value : openingView(props.world, frame.value, stops.value)));
const k = computed(() => frame.value.width / view.value.span);
// World km -> frame px, north up: one matrix for every world-unit layer.
const matrix = computed(() => {
  const s = k.value;
  const e = frame.value.width / 2 - view.value.cx * s;
  const f = frame.value.height / 2 + view.value.cy * s;
  return `matrix(${s} 0 0 ${-s} ${e} ${f})`;
});
const px = (point) => project(view.value, frame.value, point);
const lod = computed(() => lodFor(view.value.span));

// ── static paths (rebuilt only for a new payload) ───────────────────────

const coastD = computed(() => ringsPath([props.world.common.coastline]));
const bordersD = computed(() => linesPath(props.world.common.borders));
const litDistricts = computed(() => props.world.districts.filter((district) => district.lit));
const unlitDistricts = computed(() => props.world.districts.filter((district) => !district.lit));

const litDraws = computed(() =>
  litDistricts.value.map((district) => ({
    id: district.id,
    // A quiet per-district tone so neighbouring lit districts read apart.
    tone: [...district.id].reduce((sum, ch) => sum + ch.codePointAt(0), 0) % 3,
    outline: ringsPath(district.outline),
    terrain: district.terrain.map((row, i) => ({ key: `${row.region}#${i}`, region: row.region, d: ringsPath(row.polygons) })),
    rivers: linesPath(district.rivers),
    ridge: linesPath(district.ridge),
    roads: linesPath(district.roads),
  })),
);
const borderDraws = computed(() =>
  props.world.districts.map((district) => ({ id: district.id, lit: district.lit, d: ringsPath(district.outline) })),
);
const unlitD = computed(() => unlitDistricts.value.map((district) => ringsPath(district.outline)).join(""));

const trailCells = computed(() => trailCellsPath(props.world.trail));
const trailCount = computed(() => trailCellCount(props.world.trail));
const trailGrid = computed(() => trailGridKm(props.world.trail, 1 / k.value));
// Memoised per payload and join grid: zoom steps reuse one path.
const trailLineCache = new Map();
watch(
  () => props.world.trail,
  () => trailLineCache.clear(),
);
const trailLine = computed(() => {
  const grid = trailGrid.value;
  if (!trailLineCache.has(grid)) trailLineCache.set(grid, trailLinePath(props.world.trail, grid).d);
  return trailLineCache.get(grid);
});

// ── discovery (ink reveal and announcement) ─────────────────────────────

const revealing = ref([]); // [{ id, start, ms, radiusKm, landmark }]
const revealNow = ref(0);
const discoveryText = ref("");
let presented = null;
let presentedEpoch = props.epoch;
let frameHandle = null;

const now = () => (typeof performance !== "undefined" ? performance.now() : Date.now());
const requestFrame = (cb) =>
  typeof requestAnimationFrame === "function" ? requestAnimationFrame(cb) : setTimeout(() => cb(now()), 16);
const cancelFrame = (handle) =>
  typeof cancelAnimationFrame === "function" ? cancelAnimationFrame(handle) : clearTimeout(handle);

function tickReveal() {
  frameHandle = null;
  const t = now();
  revealNow.value = t;
  revealing.value = revealing.value.filter((entry) => t - entry.start < entry.ms);
  if (revealing.value.length) frameHandle = requestFrame(tickReveal);
}

function stopReveal() {
  announceToken += 1;
  if (frameHandle !== null) cancelFrame(frameHandle);
  frameHandle = null;
  revealing.value = [];
}

// Bumped by every re-baseline, so a queued announcement from before it
// never lands afterwards. Defensive: Vue's flush order already runs each
// payload's announcement before the next re-baseline can be observed.
let announceToken = 0;
function announce(text) {
  // Re-set so an identical announcement is still read.
  discoveryText.value = "";
  const token = announceToken;
  queueMicrotask(() => {
    if (token === announceToken) discoveryText.value = text;
  });
}

function present(world) {
  const epochChanged = props.epoch !== presentedEpoch;
  const { lit, regressed } = revealTransitions(epochChanged ? null : presented, world);
  presented = world;
  presentedEpoch = props.epoch;
  if (epochChanged || regressed) {
    stopReveal();
    discoveryText.value = "";
    return;
  }
  if (!lit.length) return;
  const districts = lit.map((id) => world.districts.find((district) => district.id === id));
  announce(`已探明：${districts.map((district) => district.name).join("、")}`);
  const ms = readMotionMs(REVEAL_TOKEN);
  if (!(ms > 0)) return;
  const start = now();
  revealNow.value = start;
  revealing.value = [
    ...revealing.value.filter((entry) => !lit.includes(entry.id)),
    ...districts.map((district) => ({
      id: district.id,
      start,
      ms,
      radiusKm: revealRadiusKm(district),
      landmark: { x: district.landmark.x, y: district.landmark.y },
    })),
  ];
  if (frameHandle === null) frameHandle = requestFrame(tickReveal);
}

presented = props.world;
watch(
  () => props.world,
  (world) => present(world),
);
watch(
  () => props.epoch,
  () => {
    presented = props.world;
    presentedEpoch = props.epoch;
    stopReveal();
    discoveryText.value = "";
  },
);

const easeOut = (t) => 1 - (1 - t) ** 3;
const revealDraws = computed(() => {
  const t = revealNow.value;
  return revealing.value.map((entry) => {
    const progress = Math.min(1, Math.max(0, (t - entry.start) / entry.ms));
    const p = px(entry.landmark);
    return {
      id: entry.id,
      ms: entry.ms,
      outline: borderDraws.value.find((draw) => draw.id === entry.id)?.d ?? "",
      r: entry.radiusKm * easeOut(progress),
      landmark: entry.landmark,
      // A gilt rim rides the ink front and fades as it settles.
      ripple: { x: p.x, y: p.y, r: Math.max(1, entry.radiusKm * easeOut(progress) * k.value * 0.91), opacity: 0.85 * (1 - progress) },
    };
  });
});
const revealById = computed(() => new Map(revealDraws.value.map((entry) => [entry.id, entry])));
const revealMaskId = (id) => `${uid}-reveal-${id}`;

// ── selection ───────────────────────────────────────────────────────────

const localSelected = ref(props.selected ?? null);
watch(
  () => props.selected,
  (next) => {
    if (next !== undefined) localSelected.value = next ?? null;
  },
);
const selectedKey = computed(() => (localSelected.value && featureDetail(props.world, localSelected.value) ? localSelected.value : null));
const detail = computed(() => (selectedKey.value ? featureDetail(props.world, selectedKey.value) : null));
const detailShown = computed(() => props.showDetail && !!detail.value);

function setSelected(key) {
  const next = key && featureDetail(props.world, key) ? key : null;
  if (localSelected.value === next) return;
  localSelected.value = next;
  emit("update:selected", next);
  emit("select", next ? featureDetail(props.world, next) : null);
}

// A republished body that no longer holds the selection drops it; a district
// that lit while selected keeps its key and now reads its supplied name.
watch(
  () => props.world,
  () => {
    if (localSelected.value && !featureDetail(props.world, localSelected.value)) setSelected(null);
  },
);

const selectedDistrictId = computed(() => (selectedKey.value?.startsWith("district:") ? selectedKey.value.slice(9) : null));
const selectedBorder = computed(() => borderDraws.value.find((draw) => draw.id === selectedDistrictId.value) ?? null);

const usable = computed(() => usableRect(frame.value, { drawerOpen: detailShown.value, drawerWidth: DETAIL_DRAWER_WIDTH }));

// ── screen-space markers ────────────────────────────────────────────────

function onScreen(p, pad = 40) {
  return p.x > -pad && p.y > -pad && p.x < frame.value.width + pad && p.y < frame.value.height + pad;
}

const places = computed(() => placesOf(props.world));

const placeDraws = computed(() =>
  places.value
    .map((place) => ({ ...place, key: `place:${place.id}`, p: px(place) }))
    .filter((place) => onScreen(place.p)),
);

const landmarkDraws = computed(() => {
  const placeAt = places.value.map((place) => px(place));
  return litDistricts.value
    .map((district) => ({ id: district.id, key: `district:${district.id}`, name: district.name, p: px(district.landmark) }))
    .filter((draw) => onScreen(draw.p))
    .map((draw) => ({
      ...draw,
      // A place drawn on the landmark's own spot stands for it; no spire.
      shared: placeAt.some((p) => Math.hypot(p.x - draw.p.x, p.y - draw.p.y) < 9 * uiScale.value),
    }));
});

const approxDraws = computed(() =>
  props.world.quest_markers
    .filter((marker) => marker.approximate)
    .map((marker) => ({
      id: marker.id,
      key: `quest:${marker.id}`,
      tracked: marker.tracked,
      p: px(marker),
      r: Math.max(APPROXIMATE_RADIUS_KM * k.value, APPROXIMATE_MIN_RADIUS_PX * uiScale.value),
    }))
    .filter((draw) => onScreen(draw.p, draw.r + 40)),
);

const questDraws = computed(() =>
  props.world.quest_markers
    .filter((marker) => !marker.approximate)
    .map((marker) => ({ id: marker.id, key: `quest:${marker.id}`, tracked: marker.tracked, p: px(marker) }))
    .filter((draw) => onScreen(draw.p)),
);

const here = computed(() => px(props.world.current));

const districtCount = computed(() => props.world.districts.length);

// ── labels ──────────────────────────────────────────────────────────────

const fontPx = computed(() => LABEL_FONT_PX * uiScale.value);
const nationFontPx = computed(() => NATION_FONT_PX * uiScale.value);
const measureCache = new Map();
let measureContext;
function measureText(text, size, spacingEm = 0) {
  const key = `${size}|${spacingEm}|${text}`;
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
  let width = estimateTextWidth(text, size, spacingEm);
  if (measureContext) {
    measureContext.font = `700 ${size}px "Noto Sans TC", "Noto Serif TC", sans-serif`;
    width = measureContext.measureText(text).width + [...text].length * spacingEm * size;
  }
  width = width * 1.04;
  measureCache.set(key, width);
  return width;
}
const fontsVersion = ref(0);
const legendEl = ref(null);
const legendBox = ref(null);
function measureLegend() {
  const el = legendEl.value;
  const host = surface.value;
  if (!el?.getBoundingClientRect || !host?.getBoundingClientRect) return;
  const a = el.getBoundingClientRect();
  const b = host.getBoundingClientRect();
  if (!(a.width > 0)) return;
  const pad = 6;
  legendBox.value = { left: a.left - b.left - pad, top: a.top - b.top - pad, right: a.right - b.left + pad, bottom: a.bottom - b.top + pad };
}

const labelDraws = computed(() => {
  void fontsVersion.value;
  const s = uiScale.value;
  const labelFrame = {
    width: Math.max(1, frame.value.width - (detailShown.value ? DETAIL_DRAWER_WIDTH : 0)),
    height: frame.value.height,
  };
  const box = (key, p, r) => ({ key, left: p.x - r, right: p.x + r, top: p.y - r, bottom: p.y + r });
  const obstacles = [
    box("current", here.value, 12 * s),
    // The legend card sits over the bottom-left corner.
    ...(legendBox.value ? [{ key: "legend", ...legendBox.value }] : []),
    ...placeDraws.value.map((draw) => box(draw.key, draw.p, 8 * s)),
    ...landmarkDraws.value.map((draw) => box(draw.key, draw.p, 9 * s)),
    ...questDraws.value.map((draw) => box(draw.key, draw.p, 11 * s)),
    // An approximate circle is kept clear of every other name.
    ...approxDraws.value.map((draw) => box(draw.key, draw.p, draw.r * 0.8)),
  ];
  const approxRadius = new Map(approxDraws.value.map((draw) => [draw.key, draw.r]));
  const radius = (candidate) => {
    if (candidate.kind === "quest-approx") return approxRadius.get(candidate.key) ?? APPROXIMATE_MIN_RADIUS_PX * s;
    if (candidate.kind === "quest") return 13 * s;
    if (candidate.kind === "district") return 11 * s;
    if (candidate.kind === "nation") return 4 * s;
    if (candidate.kind === "unlit") return 0;
    return 8 * s;
  };
  return placeWorldLabels(labelCandidates(props.world, lod.value, selectedKey.value), px, labelFrame, {
    fontPx: fontPx.value,
    nationFontPx: nationFontPx.value,
    measure: measureText,
    radius,
    obstacles,
  });
});

const scale = computed(() => scaleBar(view.value, frame.value, UNITS.km, 120 * uiScale.value));
const stopLabel = computed(() => nearestStop(stops.value, view.value.span).label);

// ── pointer: drag pans, wheel zooms, click selects ──────────────────────

let drag = null;

function surfacePoint(event) {
  const rect = surface.value?.getBoundingClientRect?.();
  return { x: (event.clientX ?? 0) - (rect?.left ?? 0), y: (event.clientY ?? 0) - (rect?.top ?? 0) };
}

function onPointerDown(event) {
  if (event.button !== undefined && event.button !== 0) return;
  const target = event.target?.closest?.("[data-pick]");
  drag = {
    x: event.clientX ?? 0,
    y: event.clientY ?? 0,
    view: view.value,
    moved: false,
    pick: target ? target.getAttribute("data-pick") : null,
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
  const { moved, pick } = drag;
  drag = null;
  if (moved) return;
  setSelected(pick);
}

function onPointerCancel() {
  drag = null;
}

function onWheel(event) {
  commitView(zoomBy(view.value, frame.value, wheelFactor(event.deltaY ?? 0), surfacePoint(event), limits.value));
}

// ── keyboard: the feature list ──────────────────────────────────────────

const keys = computed(() => featureKeys(props.world));
const focusedKey = ref(null);
const listEl = ref(null);
const tabStopKey = computed(() => {
  for (const key of [focusedKey.value, selectedKey.value, keys.value[0]]) {
    if (key && keys.value.includes(key)) return key;
  }
  return null;
});
const features = computed(() => keys.value.map((key) => ({ key, name: featureName(props.world, key) })));

function ensureVisible(key) {
  const point = featurePoint(props.world, key);
  if (!point) return;
  const p = px(point);
  const r = usable.value;
  if (p.x < r.left || p.x > r.right || p.y < r.top || p.y > r.bottom) {
    commitView(centreOn(view.value, frame.value, point, r));
  }
}

// A selection opens the detail card over the right edge: keep the selected
// feature inside what remains visible.
watch(
  selectedKey,
  (key) => {
    if (key) ensureVisible(key);
  },
  { flush: "post" },
);

function onFeatureFocus(key) {
  focusedKey.value = key;
  ensureVisible(key);
}

function onFeatureBlur(key) {
  if (focusedKey.value === key) focusedKey.value = null;
}

function focusFeature(key) {
  focusedKey.value = key;
  for (const el of listEl.value?.querySelectorAll?.("[data-feature]") ?? []) {
    if (el.getAttribute("data-feature") === key) {
      el.focus();
      return;
    }
  }
}

function onFeatureKeydown(event, key) {
  const list = keys.value;
  const index = list.indexOf(key);
  const moves = { ArrowDown: index + 1, ArrowUp: index - 1, Home: 0, End: list.length - 1 };
  if (!(event.key in moves)) return;
  event.preventDefault();
  event.stopPropagation();
  const next = list[Math.min(list.length - 1, Math.max(0, moves[event.key]))];
  if (next) focusFeature(next);
}

const focusRing = computed(() => {
  if (!focusedKey.value) return null;
  const point = featurePoint(props.world, focusedKey.value);
  if (!point) return null;
  // An approximate commission is ringed around its whole circle, never at a
  // centre point it does not claim.
  const approx = approxDraws.value.find((draw) => draw.key === focusedKey.value);
  return { ...px(point), r: approx ? approx.r + 5 * uiScale.value : 18 * uiScale.value };
});

function onRootKeydown(event) {
  if (event.key === "Escape" && selectedKey.value) {
    event.stopPropagation();
    const key = selectedKey.value;
    setSelected(null);
    focusFeature(key);
  }
}

// ── detail actions and host controls ────────────────────────────────────

function centreFeature(key) {
  const point = featurePoint(props.world, key);
  if (point) commitView(centreOn(view.value, frame.value, point, usable.value));
}

function closeDetail() {
  const key = selectedKey.value;
  setSelected(null);
  if (key) focusFeature(key);
}

const selectionText = computed(() => (detail.value ? `已選取：${detail.value.title}` : ""));

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
  commitView(centreOn(view.value, frame.value, props.world.current, usable.value));
}

function showWhole() {
  commitView(wholeView(props.world, frame.value, usable.value));
}

function panBy(dxPx, dyPx) {
  commitView(panByPixels(view.value, frame.value, dxPx, dyPx));
}

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
  if ((first || changed) && viewIsOpening) openView();
  measureLegend();
}

onMounted(() => {
  document.fonts?.ready?.then(() => {
    measureCache.clear();
    fontsVersion.value += 1;
    measureLegend();
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
  stopReveal();
});

const litCount = computed(() => litDistricts.value.length);
</script>

<template>
  <div class="world-map" :class="{ 'has-detail': detailShown }" data-testid="world-map" @keydown="onRootKeydown">
    <div
      ref="surface"
      class="world-map__surface"
      data-testid="world-map__surface"
      @pointerdown="onPointerDown"
      @pointermove="onPointerMove"
      @pointerup="onPointerUp"
      @pointercancel="onPointerCancel"
      @wheel.prevent="onWheel"
    >
      <svg
        class="world-map__svg"
        data-testid="world-map__svg"
        :width="frame.width"
        :height="frame.height"
        :viewBox="`0 0 ${frame.width} ${frame.height}`"
        role="img"
        :aria-label="`世界地圖：已探明 ${litCount} 個分區，共 ${districtCount} 個分區`"
        :data-span="view.span"
      >
        <defs>
          <radialGradient :id="`${uid}-sea`" cx="46%" cy="44%" r="80%">
            <stop offset="0" stop-color="#14202a" />
            <stop offset="0.6" stop-color="#0d151c" />
            <stop offset="1" stop-color="#080c10" />
          </radialGradient>
          <pattern :id="`${uid}-swell`" patternUnits="userSpaceOnUse" width="28" height="14">
            <path class="world-map__swell" d="M0 10 Q7 6 14 10 T28 10" />
          </pattern>
          <pattern :id="`${uid}-hatch`" patternUnits="userSpaceOnUse" width="8" height="8" patternTransform="rotate(45)">
            <line class="world-map__hatch-line" x1="0" y1="0" x2="0" y2="8" />
          </pattern>
          <clipPath :id="`${uid}-coast`" clipPathUnits="userSpaceOnUse">
            <path :d="coastD" :transform="matrix" />
          </clipPath>
          <!-- Feathered ink: solid to 82% of the radius, then soft. -->
          <radialGradient :id="`${uid}-ink`">
            <stop offset="0.82" stop-color="#fff" stop-opacity="1" />
            <stop offset="1" stop-color="#fff" stop-opacity="0" />
          </radialGradient>
          <radialGradient :id="`${uid}-ink-cut`">
            <stop offset="0.82" stop-color="#000" stop-opacity="1" />
            <stop offset="1" stop-color="#000" stop-opacity="0" />
          </radialGradient>
          <mask :id="`${uid}-unlit`" maskUnits="userSpaceOnUse" x="0" y="0" :width="frame.width" :height="frame.height">
            <g :transform="matrix">
              <path :d="unlitD" fill="#fff" fill-rule="evenodd" />
            </g>
          </mask>
          <!-- A district still inking keeps its hatching outside the
               spreading ink: its own outline, minus the ink circle. -->
          <mask
            v-for="entry in revealDraws"
            :id="`${uid}-recede-${entry.id}`"
            :key="`recede-${entry.id}`"
            maskUnits="userSpaceOnUse"
            x="0"
            y="0"
            :width="frame.width"
            :height="frame.height"
          >
            <g :transform="matrix">
              <path :d="entry.outline" fill="#fff" fill-rule="evenodd" />
              <circle :cx="entry.landmark.x" :cy="entry.landmark.y" :r="entry.r" :fill="`url(#${uid}-ink-cut)`" />
            </g>
          </mask>
          <clipPath v-for="entry in revealDraws" :id="`${uid}-inking-${entry.id}`" :key="`inking-${entry.id}`" clipPathUnits="userSpaceOnUse">
            <path :d="entry.outline" :transform="matrix" clip-rule="evenodd" />
          </clipPath>
          <!-- The ink masks the district's lit group, which already sits in
               world units, so its content and region are world units too. -->
          <mask
            v-for="entry in revealDraws"
            :id="revealMaskId(entry.id)"
            :key="`mask-${entry.id}`"
            maskUnits="userSpaceOnUse"
            maskContentUnits="userSpaceOnUse"
            x="-100000"
            y="-100000"
            width="200000"
            height="200000"
          >
            <circle
              class="world-map__ink"
              data-testid="world-map__ink"
              :data-district="entry.id"
              :data-reveal-ms="entry.ms"
              :cx="entry.landmark.x"
              :cy="entry.landmark.y"
              :r="entry.r"
              :fill="`url(#${uid}-ink)`"
            />
          </mask>
          <radialGradient :id="`${uid}-vignette`" cx="50%" cy="48%" r="75%">
            <stop offset="0.6" stop-color="#05070a" stop-opacity="0" />
            <stop offset="1" stop-color="#05070a" stop-opacity="0.66" />
          </radialGradient>
        </defs>

        <g data-layer="sea" class="world-map__layer">
          <rect :width="frame.width" :height="frame.height" :fill="`url(#${uid}-sea)`" />
          <rect :width="frame.width" :height="frame.height" :fill="`url(#${uid}-swell)`" />
        </g>

        <g data-layer="land" class="world-map__layer" :transform="matrix">
          <path class="world-map__shelf" :d="coastD" />
          <path class="world-map__land" :d="coastD" />
        </g>

        <g data-layer="lit-terrain" class="world-map__layer" :clip-path="`url(#${uid}-coast)`">
          <g :transform="matrix">
            <g
              v-for="draw in litDraws"
              :key="draw.id"
              class="world-map__lit"
              :data-district="draw.id"
              :mask="revealById.has(draw.id) ? `url(#${revealMaskId(draw.id)})` : null"
            >
              <path class="world-map__wash" :class="`tone-${draw.tone}`" :d="draw.outline" fill-rule="evenodd" />
              <path
                v-for="terrain in draw.terrain"
                :key="terrain.key"
                class="world-map__terrain"
                :class="`is-${terrain.region}`"
                :data-region="terrain.region"
                :d="terrain.d"
                fill-rule="evenodd"
              />
              <path v-if="draw.rivers" class="world-map__river" :d="draw.rivers" />
              <path v-if="draw.ridge" class="world-map__ridge" :d="draw.ridge" />
              <path v-if="draw.roads" class="world-map__road" :d="draw.roads" />
            </g>
          </g>
        </g>

        <g data-layer="unlit-hatching" class="world-map__layer" :clip-path="`url(#${uid}-coast)`">
          <rect
            class="world-map__hatch"
            data-testid="world-map__hatch"
            :width="frame.width"
            :height="frame.height"
            :fill="`url(#${uid}-hatch)`"
            :mask="`url(#${uid}-unlit)`"
          />
          <rect
            v-for="entry in revealDraws"
            :key="`receding-${entry.id}`"
            class="world-map__hatch"
            :width="frame.width"
            :height="frame.height"
            :fill="`url(#${uid}-hatch)`"
            :mask="`url(#${uid}-recede-${entry.id})`"
          />
        </g>

        <g data-layer="district-borders" class="world-map__layer" :clip-path="`url(#${uid}-coast)`">
          <g :transform="matrix">
            <path
              v-for="draw in borderDraws.filter((item) => item.lit)"
              :key="`edge-${draw.id}`"
              class="world-map__district-edge"
              :d="draw.d"
            />
            <path
              v-for="draw in borderDraws"
              :key="draw.id"
              class="world-map__district"
              :class="draw.lit ? 'is-lit' : 'is-unlit'"
              data-testid="world-map__district"
              :data-district="draw.id"
              :data-lit="draw.lit ? 'true' : 'false'"
              :data-pick="`district:${draw.id}`"
              :d="draw.d"
              fill-rule="evenodd"
            />
            <path v-if="selectedBorder" class="world-map__district-selected" :d="selectedBorder.d" fill-rule="evenodd" />
          </g>
        </g>

        <g data-layer="national-borders" class="world-map__layer" :transform="matrix">
          <path class="world-map__nation-casing" :d="bordersD" />
          <path class="world-map__nation-border" data-testid="world-map__nation-border" :d="bordersD" />
        </g>

        <g data-layer="coastline" class="world-map__layer" :transform="matrix">
          <path class="world-map__coast-glow" :d="coastD" />
          <path class="world-map__coast" :d="coastD" />
        </g>

        <g
          data-layer="trail"
          class="world-map__layer"
          :transform="matrix"
          data-testid="world-map__trail"
          :data-mode="lod.trailCells ? 'cells' : 'line'"
          :data-resolution-km="world.trail.resolution_km"
          :data-cells="trailCount"
        >
          <path v-if="lod.trailCells" class="world-map__trail-cells" :d="trailCells" />
          <template v-else>
            <path class="world-map__trail-casing" :d="trailLine" />
            <path class="world-map__trail-line" :d="trailLine" />
          </template>
        </g>

        <g data-layer="approximate-quests" class="world-map__layer">
          <g
            v-for="draw in approxDraws"
            :key="draw.key"
            class="world-map__approx"
            :class="{ 'is-selected': draw.key === selectedKey, 'is-tracked': draw.tracked }"
            data-testid="world-map__approx"
            :data-quest="draw.id"
            :data-pick="draw.key"
          >
            <circle class="world-map__approx-fill" :cx="draw.p.x" :cy="draw.p.y" :r="draw.r" />
            <circle class="world-map__approx-ring" :cx="draw.p.x" :cy="draw.p.y" :r="draw.r" />
          </g>
        </g>

        <g data-layer="places-landmarks" class="world-map__layer">
          <g
            v-for="draw in landmarkDraws.filter((item) => !item.shared)"
            :key="draw.key"
            class="world-map__landmark"
            :class="{ 'is-selected': draw.key === selectedKey }"
            data-testid="world-map__landmark"
            :data-pick="draw.key"
            :transform="`translate(${draw.p.x} ${draw.p.y}) scale(${uiScale})`"
          >
            <circle class="world-map__hit" r="12" />
            <path class="world-map__spire" d="M-5 7 L-3.2 -5 L0 -10 L3.2 -5 L5 7 Z" />
            <path class="world-map__spire-light" d="M0 -10 L1.4 -5.6 L0 -2 L-1.4 -5.6 Z" />
          </g>
          <g
            v-for="draw in placeDraws"
            :key="draw.key"
            class="world-map__place"
            :class="[`is-${draw.kind}`, { 'is-selected': draw.key === selectedKey }]"
            data-testid="world-map__place"
            :data-place="draw.id"
            :data-pick="draw.key"
            :transform="`translate(${draw.p.x} ${draw.p.y}) scale(${uiScale})`"
          >
            <circle class="world-map__hit" r="12" />
            <template v-if="draw.kind === 'capital'">
              <rect class="world-map__place-glyph" x="-7" y="-7" width="14" height="14" transform="rotate(45)" />
              <rect class="world-map__place-core" x="-2.6" y="-2.6" width="5.2" height="5.2" transform="rotate(45)" />
            </template>
            <circle v-else-if="draw.kind === 'harbour'" class="world-map__place-glyph" r="5.5" />
            <rect v-else class="world-map__place-glyph" x="-5" y="-5" width="10" height="10" transform="rotate(45)" />
          </g>
        </g>

        <g data-layer="quest-markers" class="world-map__layer">
          <g
            v-for="draw in questDraws"
            :key="draw.key"
            class="world-map__quest"
            :class="{ 'is-selected': draw.key === selectedKey, 'is-tracked': draw.tracked }"
            data-testid="world-map__quest"
            :data-quest="draw.id"
            :data-pick="draw.key"
            :transform="`translate(${draw.p.x} ${draw.p.y}) scale(${uiScale})`"
          >
            <circle class="world-map__hit" r="14" />
            <circle v-if="draw.tracked" class="world-map__quest-halo" cy="-5" r="12" />
            <path class="world-map__quest-pin" d="M0 -16 L8.5 -5 L0 6 L-8.5 -5 Z" />
            <circle class="world-map__quest-eye" cy="-5" r="2.4" />
          </g>
        </g>

        <g data-layer="current" class="world-map__layer" :transform="`translate(${here.x} ${here.y}) scale(${uiScale})`">
          <circle class="world-map__here-glow" r="14" />
          <circle class="world-map__here-ring" r="10" />
          <circle class="world-map__here-dot" r="5.5" />
        </g>

        <g data-layer="labels" class="world-map__layer" aria-hidden="true">
          <text
            v-for="label in labelDraws"
            :key="`label-${label.key}`"
            class="world-map__label"
            :class="`is-${label.kind}`"
            data-testid="world-map__label"
            :data-label-for="label.key"
            :data-kind="label.kind"
            :x="label.x"
            :y="label.y"
            :text-anchor="label.anchor"
            :style="{ fontSize: `${label.fontPx}px`, strokeWidth: `${label.fontPx * 0.28}px` }"
          >
            <tspan
              v-for="(line, i) in label.lines"
              :key="i"
              :x="label.x"
              :dy="i === 0 ? 0 : label.lineHeight"
              :class="{ 'world-map__label-precision': line === '大致方位' }"
            >{{ line }}</tspan>
          </text>
        </g>

        <g data-layer="chrome" class="world-map__layer" aria-hidden="true">
          <circle
            v-for="entry in revealDraws"
            :key="`ripple-${entry.id}`"
            class="world-map__ripple"
            :clip-path="`url(#${uid}-inking-${entry.id})`"
            :cx="entry.ripple.x"
            :cy="entry.ripple.y"
            :r="entry.ripple.r"
            :opacity="entry.ripple.opacity"
          />
          <circle
            v-if="focusRing"
            class="world-map__focus-ring"
            data-testid="world-map__focus-ring"
            :cx="focusRing.x"
            :cy="focusRing.y"
            :r="focusRing.r"
          />
          <rect class="world-map__vignette" :width="frame.width" :height="frame.height" :fill="`url(#${uid}-vignette)`" />
        </g>
      </svg>

      <div ref="legendEl" class="world-map__legend" data-testid="world-map__legend">
        <p class="world-map__explored" data-testid="world-map__explored">已探明 {{ litCount }}／{{ districtCount }} 分區</p>
        <div class="world-map__scale-row">
          <span class="world-map__north" aria-label="上方為北">
            <svg viewBox="0 0 14 18" width="14" height="18" aria-hidden="true"><path d="M7 0 L13 16 L7 12 L1 16 Z" /></svg>
            <span aria-hidden="true">北</span>
          </span>
          <span class="world-map__scale-bar" data-testid="world-map__scale-bar" :style="{ width: `${scale.px}px` }" aria-hidden="true" />
          <span class="world-map__scale-text" data-testid="world-map__scale-text">{{ scale.text }}</span>
          <span class="world-map__stop" data-testid="world-map__stop">{{ stopLabel }}</span>
        </div>
      </div>
    </div>

    <ul ref="listEl" class="world-map__features" aria-label="地圖要素：上下鍵切換，Enter 查看詳情" data-testid="world-map__features">
      <li v-for="feature in features" :key="feature.key">
        <button
          type="button"
          class="world-map__feature"
          :data-feature="feature.key"
          :tabindex="feature.key === tabStopKey ? 0 : -1"
          :aria-pressed="feature.key === selectedKey ? 'true' : 'false'"
          @click="setSelected(feature.key)"
          @focus="onFeatureFocus(feature.key)"
          @blur="onFeatureBlur(feature.key)"
          @keydown="onFeatureKeydown($event, feature.key)"
        >{{ feature.name }}</button>
      </li>
    </ul>

    <div v-if="detailShown" class="world-map__detail" :style="{ width: `${DETAIL_DRAWER_WIDTH}px` }">
      <slot name="detail" :detail="detail" :centre="centreFeature" :close="closeDetail">
        <WorldMapDetail :detail="detail" @centre="centreFeature" @close="closeDetail" />
      </slot>
    </div>
    <p class="world-map__live" aria-live="polite" data-testid="world-map__discovery">{{ discoveryText }}</p>
    <p class="world-map__live" aria-live="polite" data-testid="world-map__live">{{ selectionText }}</p>
  </div>
</template>

<style scoped>
.world-map {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  color: var(--paper-200);
  font-family: var(--f-sans);
  background: #080c10;
  isolation: isolate;
}
.world-map__surface {
  position: absolute;
  inset: 0;
  z-index: 1;
  touch-action: none;
  cursor: grab;
  user-select: none;
}
.world-map__surface:active { cursor: grabbing; }
.world-map__svg { position: absolute; inset: 0; display: block; overflow: hidden; }
/* Paper grain over the whole chart: a static tile, so panning never
   repaints a filter. */
.world-map__surface::after {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0.55;
  mix-blend-mode: soft-light;
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='200' height='200'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' seed='11'/><feColorMatrix values='0 0 0 0 0.72 0 0 0 0 0.64 0 0 0 0 0.48 0 0 0 0.16 0'/></filter><rect width='200' height='200' filter='url(%23n)'/></svg>");
}

/* every world-unit stroke keeps its screen width under zoom */
.world-map__layer path,
.world-map__layer circle { vector-effect: non-scaling-stroke; }

/* sea and land */
.world-map__swell { fill: none; stroke: #5b7a8c; stroke-opacity: 0.07; stroke-width: 1; }
.world-map__shelf { fill: none; stroke: #2a3b47; stroke-opacity: 0.55; stroke-width: 14; stroke-linejoin: round; }
.world-map__land { fill: #1d1b17; }

/* lit ink: a warm vellum wash under terrain tints */
.world-map__wash { fill: #4a4535; }
.world-map__wash.tone-1 { fill: #5a5240; }
.world-map__wash.tone-2 { fill: #3f3b2e; }
.world-map__terrain { fill: #575238; fill-opacity: 0.8; }
.world-map__terrain.is-north_deep_forest { fill: #2f4232; }
.world-map__terrain.is-northwest_highland_forest { fill: #3c4c36; }
.world-map__terrain.is-western_hills_valleys { fill: #5a5a3b; }
.world-map__terrain.is-eastern_plains { fill: #66603a; }
.world-map__terrain.is-southwest_coast,
.world-map__terrain.is-southeast_coast { fill: #6a6046; }
.world-map__terrain.is-central_mountains { fill: #5c544b; }
.world-map__river { fill: none; stroke: #6f9db3; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; stroke-opacity: 0.9; }
.world-map__ridge { fill: none; stroke: #d6c7a2; stroke-width: 2.4; stroke-dasharray: 1 4; stroke-linecap: round; stroke-opacity: 0.8; }
.world-map__road { fill: none; stroke: #ead8aa; stroke-width: 1.5; stroke-dasharray: 7 4; stroke-opacity: 0.82; }

/* unlit: diagonal hatching over the bare land */
.world-map__hatch-line { stroke: #8a7f68; stroke-width: 1.1; stroke-opacity: 0.34; }
.world-map__hatch { pointer-events: none; }

/* district borders: solid gilt for lit, dotted ash for unlit; the fill is a
   transparent hit area for selection */
.world-map__district { fill: transparent; cursor: pointer; stroke-linejoin: round; }
/* a soft umber rim inside each lit district, like a hand-tinted plate */
.world-map__district-edge { fill: none; stroke: #1a150d; stroke-opacity: 0.16; stroke-width: 7; stroke-linejoin: round; pointer-events: none; }
.world-map__district.is-lit { stroke: #d9c493; stroke-width: 1.1; stroke-opacity: 0.6; }
.world-map__district.is-unlit { stroke: #7d7462; stroke-width: 1.1; stroke-dasharray: 1 4; stroke-linecap: round; stroke-opacity: 0.6; }
.world-map__district:hover { fill: rgba(238, 221, 180, 0.04); }
.world-map__district-selected {
  fill: rgba(228, 200, 142, 0.1);
  stroke: var(--gold-300);
  stroke-width: 2.6;
  stroke-linejoin: round;
  pointer-events: none;
}

/* national borders: a dark casing under a dash-dot seal line */
.world-map__nation-casing { fill: none; stroke: #0b0a08; stroke-opacity: 0.5; stroke-width: 4.5; stroke-linejoin: round; }
.world-map__nation-border {
  fill: none;
  stroke: #c0645a;
  stroke-width: 2;
  stroke-dasharray: 10 4 2 4;
  stroke-linejoin: round;
  stroke-opacity: 0.9;
}

/* coastline: an inked line with a faint surf glow */
.world-map__coast-glow { fill: none; stroke: #b9a77c; stroke-opacity: 0.16; stroke-width: 6; stroke-linejoin: round; }
.world-map__coast { fill: none; stroke: #b9a77c; stroke-width: 1.5; stroke-linejoin: round; }

/* trail: a gold line with a soot casing, or real cells at 近郊 */
.world-map__trail-casing { fill: none; stroke: #120f0a; stroke-opacity: 0.7; stroke-width: 6; stroke-linecap: round; stroke-linejoin: round; }
.world-map__trail-line { fill: none; stroke: var(--gold-300); stroke-width: 3; stroke-linecap: round; stroke-linejoin: round; }
.world-map__trail-cells { fill: rgba(238, 221, 180, 0.32); stroke: var(--gold-300); stroke-width: 1; stroke-opacity: 0.85; }

/* approximate commissions: a dashed seal ring, never a point */
.world-map__approx { cursor: pointer; }
.world-map__approx-fill { fill: rgba(207, 68, 68, 0.09); }
.world-map__approx-ring { fill: none; stroke: var(--seal-400); stroke-width: 1.8; stroke-dasharray: 6 5; }
.world-map__approx.is-tracked .world-map__approx-ring { stroke-width: 2.4; }
.world-map__approx.is-selected .world-map__approx-ring { stroke: var(--gold-300); stroke-width: 2.6; }

/* places and landmarks */
.world-map__hit { fill: transparent; }
.world-map__landmark,
.world-map__place,
.world-map__quest { cursor: pointer; }
.world-map__spire { fill: var(--gold-400); stroke: #15140f; stroke-width: 1.5; stroke-linejoin: round; }
.world-map__spire-light { fill: #fff3d2; fill-opacity: 0.75; }
.world-map__landmark.is-selected .world-map__spire { stroke: var(--gold-300); stroke-width: 2.4; }
.world-map__place-glyph { fill: #e7e0d1; stroke: #15140f; stroke-width: 2; }
.world-map__place.is-capital .world-map__place-glyph { fill: var(--gold-400); }
.world-map__place-core { fill: #15140f; }
.world-map__place.is-harbour .world-map__place-glyph { fill: #9cc1d2; }
.world-map__place.is-hidden .world-map__place-glyph { fill: #2a2722; stroke: #cfc4ad; stroke-width: 1.4; stroke-dasharray: 2 2; }
.world-map__place.is-selected .world-map__place-glyph { stroke: var(--gold-300); stroke-width: 2.6; stroke-dasharray: none; }

/* exact commissions */
.world-map__quest-halo { fill: rgba(207, 68, 68, 0.18); stroke: rgba(224, 107, 107, 0.6); stroke-width: 1; }
.world-map__quest-pin { fill: var(--seal-500); stroke: #fff2e6; stroke-width: 1.6; stroke-linejoin: round; }
.world-map__quest-eye { fill: #fff2e6; }
.world-map__quest.is-selected .world-map__quest-pin { stroke: var(--gold-300); stroke-width: 2.6; }

/* the player */
.world-map__here-glow {
  fill: rgba(165, 44, 49, 0.24);
  transform-box: fill-box;
  transform-origin: center;
  animation: world-map-here-breathe var(--motion-pulse) ease-in-out infinite;
}
@keyframes world-map-here-breathe {
  0%, 100% { opacity: 0.55; transform: scale(0.86); }
  50% { opacity: 1; transform: scale(1.2); }
}
.world-map__here-ring { fill: none; stroke: #fff2e6; stroke-width: 2; }
.world-map__here-dot { fill: var(--seal-deep); stroke: #fff2e6; stroke-width: 1.5; }

/* labels: screen-space, 16 CSS px times the UI scale or larger, with a soot
   halo; nation names are spaced display type */
.world-map__label {
  fill: var(--paper-100);
  font-family: var(--f-sans);
  letter-spacing: 0.04em;
  paint-order: stroke;
  stroke: #12100c;
  /* the halo width is set beside the font size, so it scales with the UI */
  stroke-linejoin: round;
  pointer-events: none;
}
.world-map__label.is-nation {
  fill: rgba(242, 232, 210, 0.62);
  font-family: var(--f-display);
  letter-spacing: 0.32em;
  stroke: #0b0d10;
  stroke-opacity: 0.85;
}
.world-map__label.is-district { fill: #f4ead2; font-family: var(--f-display); letter-spacing: 0.1em; }
.world-map__label.is-unlit { fill: #9a917f; font-style: italic; letter-spacing: 0.2em; }
.world-map__label.is-place { fill: var(--paper-50); }
.world-map__label.is-quest,
.world-map__label.is-quest-approx { fill: #ffd9d4; }
.world-map__label-precision { fill: #f0a29a; font-style: italic; letter-spacing: 0.12em; }

/* chrome */
.world-map__ripple { fill: none; stroke: var(--gold-300); stroke-width: 1.6; stroke-opacity: 0.75; pointer-events: none; }
.world-map__focus-ring { fill: none; stroke: var(--gold-300); stroke-width: 2.4; stroke-dasharray: 4 3; pointer-events: none; }
.world-map__vignette { pointer-events: none; }

.world-map__legend {
  position: absolute;
  left: calc(18px * var(--ui-scale));
  bottom: calc(16px * var(--ui-scale));
  z-index: 2;
  display: grid;
  gap: calc(6px * var(--ui-scale));
  padding: calc(8px * var(--ui-scale)) calc(14px * var(--ui-scale));
  background: rgba(10, 12, 14, 0.66);
  border: 1px solid rgba(185, 154, 96, 0.22);
  border-radius: var(--radius-sm);
  pointer-events: none;
}
.world-map__explored {
  margin: 0;
  color: var(--paper-200);
  font-family: var(--f-display);
  font-size: var(--text-xs);
  letter-spacing: 0.14em;
}
.world-map__scale-row {
  display: flex;
  align-items: center;
  gap: calc(10px * var(--ui-scale));
  color: var(--paper-300);
  font-size: var(--text-xs);
  white-space: nowrap;
}
.world-map__north {
  display: inline-flex;
  align-items: center;
  gap: calc(3px * var(--ui-scale));
  color: var(--gold-400);
  font-family: var(--f-display);
}
.world-map__north path { fill: var(--gold-400); }
.world-map__scale-bar {
  display: inline-block;
  box-sizing: border-box;
  height: calc(7px * var(--ui-scale));
  border: 2px solid var(--paper-300);
  border-top: 0;
}
.world-map__stop { color: var(--gold-400); font-family: var(--f-display); letter-spacing: 0.2em; }

/* The keyboard path: real buttons, visually hidden; the focused feature
   is ringed on the map itself. */
.world-map__features {
  position: absolute;
  width: 1px;
  height: 1px;
  margin: -1px;
  padding: 0;
  overflow: hidden;
  clip: rect(0 0 0 0);
  list-style: none;
  white-space: nowrap;
}

.world-map__detail {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  z-index: 3;
}

.world-map__live {
  position: absolute;
  width: 1px;
  height: 1px;
  margin: -1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}
</style>
