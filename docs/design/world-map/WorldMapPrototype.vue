<script setup>
// Visual prototype of the redesigned big-map drawer
// (docs/superpowers/specs/2026-10-22-world-map-drawer-design.md).
// Reference only: self-contained mock data, not wired to any payload.
//
// `layout="floating"` is option A (full-bleed map, floating control pill,
// quest dropdown, drawer only on selection). `layout="columns"` is option B
// (persistent left rail and right detail panel).
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import {
  COAST_KM,
  WATERWAYS,
  NATIONS,
  PLAYER_WORLD,
  TRAIL_CELLS,
  PLACES_WORLD,
  QUESTS,
  ALTORIA_NODES,
  ALTORIA_ROADS,
  ALTORIA_VISITED,
  ALTORIA_CURRENT,
  AREA_QUESTS,
  WILD_LOCAL_SPAN,
} from "./prototype-data.js";
import {
  LANDMARKS,
  LIT,
  LIT_PATHS,
  UNLIT_PATHS,
  NATION_BORDER_PATH,
  TERRAIN_SHAPES,
  RIDGE_SEGMENTS,
  districtAt,
  districtName,
  landmarkName,
} from "./world-geometry.js";

const props = defineProps({
  layout: { type: String, default: "floating" },
  initialTab: { type: String, default: "area" },
  // "city": standing in Altoria; "wild": standing in the wilderness outside it.
  location: { type: String, default: "city" },
  initialSelection: { type: String, default: null },
  initialSpan: { type: Number, default: null },
});

const tab = ref(props.initialTab);
const selection = ref(props.initialSelection);
const legendOpen = ref(false);
const questsOpen = ref(false);

// ── viewport measurement ────────────────────────────────────────────
const mapEl = ref(null);
const size = reactive({ w: 1000, h: 600 });
let ro = null;
onMounted(() => {
  ro = new ResizeObserver(([entry]) => {
    size.w = Math.max(200, entry.contentRect.width);
    size.h = Math.max(200, entry.contentRect.height);
  });
  ro.observe(mapEl.value);
  window.addEventListener("keydown", onKey);
});
onBeforeUnmount(() => {
  ro?.disconnect();
  window.removeEventListener("keydown", onKey);
});

// ── views (span = world units across the map width) ─────────────────
const continentSpan = computed(() => 2750 * Math.max(1, size.w / size.h));
const WORLD_STOPS_REST = [
  { name: "國", span: 800 },
  { name: "地區", span: 200 },
  { name: "近郊", span: 40 },
];
const WORLD_STOPS = computed(() => [{ name: "大陸", span: continentSpan.value }, ...WORLD_STOPS_REST]);
const CITY_STOPS = [
  { name: "全城", span: 8200 },
  { name: "街區", span: 3600 },
  { name: "近處", span: 1500 },
];
const WILD_STOPS = [
  { name: "周邊", span: 17 },
  { name: "近處", span: 9 },
];

const isWild = computed(() => props.location === "wild");
const playerWild = computed(() => (isWild.value ? PLAYER_WORLD : { x: 862, y: 1078 }));

const views = reactive({
  world:
    props.initialSpan >= 2700
      ? { cx: 1350, cy: 1350, span: props.initialSpan }
      : { cx: PLAYER_WORLD.x + 60, cy: PLAYER_WORLD.y + 40, span: props.initialSpan ?? 800 },
  area: isWild.value
    ? { cx: PLAYER_WORLD.x + 0.5, cy: PLAYER_WORLD.y + 0.5, span: 17 }
    : { cx: ALTORIA_NODES[ALTORIA_CURRENT].x, cy: ALTORIA_NODES[ALTORIA_CURRENT].y + 300, span: 5200 },
});
const view = computed(() => views[tab.value]);
const stops = computed(() => (tab.value === "world" ? WORLD_STOPS.value : isWild.value ? WILD_STOPS : CITY_STOPS));
const spanLimits = computed(() => {
  const s = stops.value;
  return [s[s.length - 1].span * 0.75, s[0].span * 1.1];
});
const stopName = computed(() => {
  let best = stops.value[0];
  for (const s of stops.value) {
    if (Math.abs(Math.log(s.span / view.value.span)) < Math.abs(Math.log(best.span / view.value.span))) best = s;
  }
  return best.name;
});

const k = computed(() => size.w / view.value.span);
const T = computed(
  () => `translate(${size.w / 2 - view.value.cx * k.value} ${size.h / 2 + view.value.cy * k.value}) scale(${k.value} ${-k.value})`,
);
function toPx(x, y) {
  return { x: (x - view.value.cx) * k.value + size.w / 2, y: size.h / 2 - (y - view.value.cy) * k.value };
}
function fromPx(px, py) {
  return { x: (px - size.w / 2) / k.value + view.value.cx, y: (size.h / 2 - py) / k.value + view.value.cy };
}

function setSpan(span, anchor) {
  const [lo, hi] = spanLimits.value;
  const next = Math.min(hi, Math.max(lo, span));
  const a = anchor ?? { x: size.w / 2, y: size.h / 2 };
  const before = fromPx(a.x, a.y);
  view.value.span = next;
  const after = fromPx(a.x, a.y);
  view.value.cx += before.x - after.x;
  view.value.cy += before.y - after.y;
}
function zoomIn() {
  const next = stops.value.find((s) => s.span < view.value.span * 0.95);
  if (next) setSpan(next.span);
}
function zoomOut() {
  const next = [...stops.value].reverse().find((s) => s.span > view.value.span * 1.05);
  if (next) setSpan(next.span);
}
function fitAll() {
  if (tab.value === "world") Object.assign(views.world, { cx: 1350, cy: 1350, span: continentSpan.value });
  else if (!isWild.value) Object.assign(views.area, { cx: 3800, cy: 3200, span: 8200 });
  else Object.assign(views.area, { cx: PLAYER_WORLD.x + 0.5, cy: PLAYER_WORLD.y + 0.5, span: 17 });
}
function recentre() {
  if (tab.value === "world") Object.assign(views.world, { cx: PLAYER_WORLD.x, cy: PLAYER_WORLD.y });
  else if (isWild.value) Object.assign(views.area, { cx: PLAYER_WORLD.x + 0.5, cy: PLAYER_WORLD.y + 0.5 });
  else Object.assign(views.area, { cx: ALTORIA_NODES[ALTORIA_CURRENT].x, cy: ALTORIA_NODES[ALTORIA_CURRENT].y });
}
function centreOn(x, y) {
  view.value.cx = x;
  view.value.cy = y;
}

// ── pointer: drag to pan, wheel to zoom, click to select ────────────
let drag = null;
function onPointerDown(e) {
  if (e.button !== 0) return;
  drag = { x: e.clientX, y: e.clientY, cx: view.value.cx, cy: view.value.cy, moved: false };
  e.currentTarget.setPointerCapture(e.pointerId);
}
function onPointerMove(e) {
  if (!drag) return;
  const dx = e.clientX - drag.x;
  const dy = e.clientY - drag.y;
  if (Math.hypot(dx, dy) > 4) drag.moved = true;
  if (!drag.moved) return;
  view.value.cx = drag.cx - dx / k.value;
  view.value.cy = drag.cy + dy / k.value;
}
function onPointerUp(e) {
  const d = drag;
  drag = null;
  if (!d || d.moved) return;
  const target = e.target.closest?.("[data-pick]");
  if (target) {
    selection.value = target.dataset.pick;
    return;
  }
  if (tab.value === "world") {
    const rect = mapEl.value.getBoundingClientRect();
    const w = fromPx(e.clientX - rect.left, e.clientY - rect.top);
    const id = districtAt(w.x, w.y);
    selection.value = id >= 0 ? `district:${id}` : null;
  } else {
    selection.value = null;
  }
}
function onWheel(e) {
  e.preventDefault();
  const rect = mapEl.value.getBoundingClientRect();
  setSpan(view.value.span * Math.pow(1.0018, e.deltaY), { x: e.clientX - rect.left, y: e.clientY - rect.top });
}

function onKey(e) {
  if (e.target?.closest?.("input, textarea")) return;
  const step = view.value.span * 0.12;
  const map = {
    "+": zoomIn, "=": zoomIn, "-": zoomOut, "0": fitAll, c: recentre, C: recentre,
    "1": () => (tab.value = "area"), "2": () => (tab.value = "world"),
    ArrowLeft: () => (view.value.cx -= step), ArrowRight: () => (view.value.cx += step),
    ArrowUp: () => (view.value.cy += step), ArrowDown: () => (view.value.cy -= step),
    Escape: () => {
      if (legendOpen.value) legendOpen.value = false;
      else if (questsOpen.value) questsOpen.value = false;
      else selection.value = null;
    },
  };
  if (map[e.key] && !e.ctrlKey && !e.metaKey) {
    e.preventDefault();
    map[e.key]();
  }
}
watch(tab, () => {
  selection.value = null;
  legendOpen.value = false;
});

// ── world layers ────────────────────────────────────────────────────
const coastPoints = COAST_KM.map((p) => p.join(",")).join(" ");
const riverPoints = WATERWAYS.map((r) => r.map((p) => p.join(",")).join(" "));
const trailPoints = TRAIL_CELLS.map(([x, y]) => `${x + 0.5},${y + 0.5}`).join(" ");
const trailCellSet = new Set(TRAIL_CELLS.map(([x, y]) => `${x}:${y}`));
const trailUnique = [...trailCellSet].map((s) => s.split(":").map(Number));

const showCells = computed(() => tab.value === "world" && view.value.span <= 90);

function inView(p, pad = 40) {
  return p.x > -pad && p.y > -pad && p.x < size.w + pad && p.y < size.h + pad;
}

const nationLabels = computed(() =>
  view.value.span >= 600
    ? Object.entries(NATIONS).map(([key, n]) => ({ key, name: n.name, ...toPx(n.at[0], n.at[1]) }))
    : [],
);
const districtLabels = computed(() => {
  if (view.value.span > 1000 || view.value.span < 60) return [];
  return LANDMARKS.map(([x, y], i) => ({ i, lit: LIT.has(i), ...toPx(x, y) }))
    .filter((d) => inView(d, 0) && (d.lit || view.value.span <= 450))
    .map((d) => ({ ...d, name: districtName(d.i) }));
});
const landmarkGlyphs = computed(() =>
  view.value.span <= 1000
    ? LANDMARKS.map(([x, y], i) => ({ i, ...toPx(x, y) })).filter((d) => LIT.has(d.i) && inView(d))
    : [],
);
const placeMarkers = computed(() =>
  PLACES_WORLD.filter((p) => LIT.has(districtAt(p.x, p.y)) || p.visited)
    .map((p) => ({ ...p, ...toPx(p.x, p.y), label: view.value.span <= 1000 }))
    .filter((p) => inView(p)),
);

// Quest markers, with edge pointers when off-screen.
const drawerOpen = computed(() => props.layout === "floating" && !!selection.value);
const DRAWER_W = 360;
const usable = computed(() => ({
  left: 24,
  top: 24,
  right: size.w - 24 - (drawerOpen.value ? DRAWER_W : 0),
  bottom: size.h - 24,
}));
function edgeClamp(p) {
  const u = usable.value;
  const c = { x: (u.left + u.right) / 2, y: (u.top + u.bottom) / 2 };
  const dx = p.x - c.x;
  const dy = p.y - c.y;
  const tx = dx > 0 ? (u.right - c.x) / dx : dx < 0 ? (u.left - c.x) / dx : Infinity;
  const ty = dy > 0 ? (u.bottom - c.y) / dy : dy < 0 ? (u.top - c.y) / dy : Infinity;
  const t = Math.min(tx, ty);
  const side = tx <= ty ? (dx > 0 ? "right" : "left") : dy > 0 ? "bottom" : "top";
  return { x: c.x + dx * t, y: c.y + dy * t, angle: (Math.atan2(dy, dx) * 180) / Math.PI, side };
}
function inside(p) {
  const u = usable.value;
  return p.x >= u.left && p.x <= u.right && p.y >= u.top && p.y <= u.bottom;
}
function kmFrom(x, y) {
  return Math.round(Math.hypot(x - PLAYER_WORLD.x, y - PLAYER_WORLD.y) / 10) * 10;
}
const worldQuests = computed(() =>
  QUESTS.map((q) => {
    const p = toPx(q.x, q.y);
    const lit = LIT.has(districtAt(q.x, q.y));
    const precise = q.precise && lit;
    return { ...q, px: p.x, py: p.y, precise, onScreen: inside(p), edge: edgeClamp(p), km: kmFrom(q.x, q.y) };
  }),
);

const player = computed(() => toPx(playerWild.value.x, playerWild.value.y));

// ── area layers (city) ──────────────────────────────────────────────
const visitedSet = new Set(ALTORIA_VISITED);
const seenSet = new Set();
for (const [a, b] of ALTORIA_ROADS) {
  if (visitedSet.has(a) && !visitedSet.has(b)) seenSet.add(b);
  if (visitedSet.has(b) && !visitedSet.has(a)) seenSet.add(a);
}
const adjacentToCurrent = new Set(
  ALTORIA_ROADS.flatMap(([a, b]) => (a === ALTORIA_CURRENT ? [b] : b === ALTORIA_CURRENT ? [a] : [])),
);
const cityRoads = computed(() =>
  ALTORIA_ROADS.filter(([a, b]) => visitedSet.has(a) || visitedSet.has(b)).map(([a, b]) => ({
    key: `${a}-${b}`,
    a: ALTORIA_NODES[a],
    b: ALTORIA_NODES[b],
    seen: !(visitedSet.has(a) && visitedSet.has(b)),
  })),
);
const cityNodes = computed(() =>
  Object.entries(ALTORIA_NODES)
    .filter(([id]) => visitedSet.has(id) || seenSet.has(id))
    .map(([id, n]) => ({
      id,
      ...n,
      ...toPx(n.x, n.y),
      state: id === ALTORIA_CURRENT ? "current" : visitedSet.has(id) ? "visited" : "seen",
      adjacent: adjacentToCurrent.has(id),
      quest: AREA_QUESTS.find((q) => q.node === id),
    })),
);
const cityOutsideQuests = computed(() =>
  AREA_QUESTS.filter((q) => q.outside).map((q) => {
    const rad = (q.outside.bearingDeg * Math.PI) / 180;
    const far = toPx(view.value.cx + Math.sin(rad) * 1e6, view.value.cy + Math.cos(rad) * 1e6);
    return { ...q, edge: edgeClamp(far) };
  }),
);

// Scale-true dot field for the area map: spacing is a round metric step.
const NICE = [1, 2, 5];
function niceStep(target) {
  const p = Math.pow(10, Math.floor(Math.log10(target)));
  for (const n of NICE) if (n * p >= target) return n * p;
  return 10 * p;
}
const dotStep = computed(() => niceStep(28 / k.value));
const dotPattern = computed(() => {
  const s = dotStep.value * k.value;
  const o = toPx(0, 0);
  return { s, ox: ((o.x % s) + s) % s, oy: ((o.y % s) + s) % s };
});
const scaleBar = computed(() => {
  const len = niceStep(110 / k.value);
  const unit = tab.value === "world" || isWild.value ? "km" : "m";
  const text = unit === "m" && len >= 1000 ? `${len / 1000} km` : `${len} ${unit}`;
  return { px: len * k.value, text };
});

// ── area layers (wilderness neighbourhood) ──────────────────────────
const wildCells = computed(() => {
  const half = Math.floor(WILD_LOCAL_SPAN / 2);
  const out = [];
  for (let dx = -half; dx <= half; dx++) {
    for (let dy = -half; dy <= half; dy++) {
      const x = PLAYER_WORLD.x + dx;
      const y = PLAYER_WORLD.y + dy;
      const visited = trailCellSet.has(`${x}:${y}`);
      const current = dx === 0 && dy === 0;
      const adjacent = !current && Math.abs(dx) <= 1 && Math.abs(dy) <= 1;
      if (!visited && !adjacent && !current) continue;
      out.push({ x, y, visited, current, adjacent });
    }
  }
  return out;
});

// ── header and selection details ────────────────────────────────────
const currentDistrict = districtAt(PLAYER_WORLD.x, PLAYER_WORLD.y);
const headerPlace = computed(() =>
  tab.value === "world"
    ? `${districtName(currentDistrict)} · ${NATIONS.altoria.name}`
    : isWild.value
      ? `荒野 · ${districtName(currentDistrict)}`
      : `聖潔王都 · ${ALTORIA_NODES[ALTORIA_CURRENT].name}`,
);

const detail = computed(() => {
  const s = selection.value;
  if (!s) return null;
  if (s.startsWith("district:")) {
    const i = Number(s.slice(9));
    const lit = LIT.has(i);
    const [x, y] = LANDMARKS[i];
    return {
      kind: lit ? "已探明分區" : "未探明分區",
      title: districtName(i),
      lines: lit
        ? [`地標：${landmarkName(i)}（已抵達）`, `距你約 ${kmFrom(x, y)} km`]
        : ["抵達此分區的地標即可點亮詳細地形。", "地標位置未知；常見於高處、哨站或古道路標。"],
      quests: QUESTS.filter((q) => districtAt(q.x, q.y) === i),
      at: [x, y],
    };
  }
  if (s.startsWith("quest:")) {
    const q = QUESTS.find((item) => `quest:${item.id}` === s) ?? AREA_QUESTS.find((item) => `quest:${item.id}` === s);
    return {
      kind: `委託 · ${q.rank ?? "E"} 級`,
      title: q.title,
      lines: [q.target ? `目的地：${q.target}` : "目的地：大神殿前", q.note ?? "", q.x ? `距你約 ${kmFrom(q.x, q.y)} km` : ""].filter(Boolean),
      quests: [],
      at: q.x ? [q.x, q.y] : null,
    };
  }
  if (s.startsWith("place:")) {
    const p = PLACES_WORLD.find((item) => `place:${item.id}` === s);
    return { kind: "聚落", title: p.name, lines: [`距你約 ${kmFrom(p.x, p.y)} km`], quests: [], at: [p.x, p.y] };
  }
  if (s.startsWith("node:")) {
    const id = s.slice(5);
    const n = ALTORIA_NODES[id];
    const state = id === ALTORIA_CURRENT ? "你在這裡" : visitedSet.has(id) ? "到過" : "看過，尚未到訪";
    const dist = Math.round(Math.hypot(n.x - ALTORIA_NODES[ALTORIA_CURRENT].x, n.y - ALTORIA_NODES[ALTORIA_CURRENT].y) / 10) * 10;
    return {
      kind: n.gateway ? "城門" : "街區",
      title: n.name,
      lines: [state, n.gateway ? `通往 ${n.gateway}` : "", id === ALTORIA_CURRENT ? "" : `直線約 ${dist} m`].filter(Boolean),
      quests: AREA_QUESTS.filter((q) => q.node === id),
      move: adjacentToCurrent.has(id),
      at: [n.x, n.y],
    };
  }
  return null;
});

const trackedQuests = computed(() =>
  tab.value === "world"
    ? worldQuests.value.map((q) => ({ id: q.id, title: q.title, sub: q.precise ? `${q.km} km` : `大致方位 · ${q.km} km`, at: [q.x, q.y] }))
    : AREA_QUESTS.map((q) => ({
        id: q.id,
        title: q.title,
        sub: q.outside ? q.outside.label : "大神殿前",
        at: q.node ? [ALTORIA_NODES[q.node].x, ALTORIA_NODES[q.node].y] : null,
      })),
);
function focusQuest(q) {
  questsOpen.value = false;
  selection.value = `quest:${q.id}`;
  if (q.at) centreOn(q.at[0], q.at[1]);
}

const LEGEND = computed(() =>
  tab.value === "world"
    ? [
        { g: "here", t: "目前位置" },
        { g: "trail", t: "走過的路徑" },
        { g: "lit", t: "已探明分區" },
        { g: "unlit", t: "未探明分區（斜線）" },
        { g: "nation", t: "國境" },
        { g: "tower", t: "分區地標" },
        { g: "quest", t: "委託目的地" },
        { g: "questVague", t: "委託大致方位（虛線圈）" },
      ]
    : [
        { g: "here", t: "目前位置" },
        { g: "visited", t: "到過的地點" },
        { g: "seen", t: "看過、未到訪（淡化）" },
        { g: "gate", t: "城門：通往城外" },
        { g: "quest", t: "委託目的地" },
      ],
);
</script>

<template>
  <section class="wm" :class="`wm--${layout}`" role="dialog" aria-label="地圖">
    <header class="wm-head">
      <span class="wm-head__seal" aria-hidden="true">◈</span>
      <div class="wm-tabs" role="tablist" aria-label="地圖範圍">
        <button type="button" role="tab" class="wm-tab" :class="{ 'is-active': tab === 'area' }" :aria-selected="tab === 'area'" @click="tab = 'area'">
          區域<kbd>1</kbd>
        </button>
        <button type="button" role="tab" class="wm-tab" :class="{ 'is-active': tab === 'world' }" :aria-selected="tab === 'world'" @click="tab = 'world'">
          世界<kbd>2</kbd>
        </button>
      </div>
      <p class="wm-head__place">{{ headerPlace }}</p>
      <button type="button" class="wm-head__close" aria-label="關閉地圖">✕</button>
    </header>

    <div class="wm-body">
      <!-- Option B: persistent left rail -->
      <aside v-if="layout === 'columns'" class="wm-rail">
        <h3>追蹤中的委託</h3>
        <ul class="wm-qlist">
          <li v-for="q in trackedQuests" :key="q.id">
            <button type="button" @click="focusQuest(q)"><span class="wm-qglyph">◆</span>{{ q.title }}<small>{{ q.sub }}</small></button>
          </li>
        </ul>
        <h3>圖例</h3>
        <ul class="wm-legend">
          <li v-for="item in LEGEND" :key="item.g"><i :class="`lg lg--${item.g}`" />{{ item.t }}</li>
        </ul>
      </aside>

      <div
        ref="mapEl"
        class="wm-map"
        :class="{ 'is-world': tab === 'world' }"
        tabindex="0"
        aria-label="地圖畫布：方向鍵平移，＋／－縮放，C 回到目前位置，0 顯示全圖"
        @pointerdown="onPointerDown"
        @pointermove="onPointerMove"
        @pointerup="onPointerUp"
        @wheel="onWheel"
      >
        <svg class="wm-svg" :width="size.w" :height="size.h">
          <defs>
            <pattern id="wm-hatch" width="9" height="9" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
              <line x1="0" y1="0" x2="0" y2="9" stroke="#8a7f68" stroke-width="1.1" stroke-opacity=".38" />
            </pattern>
            <pattern id="wm-dots" :width="dotPattern.s" :height="dotPattern.s" patternUnits="userSpaceOnUse" :x="dotPattern.ox" :y="dotPattern.oy">
              <circle :cx="0" :cy="0" r="1.2" fill="#e4c88e" fill-opacity=".16" />
            </pattern>
            <mask id="wm-unlit" maskUnits="userSpaceOnUse" x="0" y="0" :width="size.w" :height="size.h">
              <g :transform="T">
                <path v-for="p in UNLIT_PATHS" :key="p.id" :d="p.d" fill="#fff" stroke="#fff" stroke-width="8" stroke-linejoin="round" />
              </g>
            </mask>
            <clipPath id="wm-coastpx" clipPathUnits="userSpaceOnUse">
              <polygon :points="coastPoints" :transform="T" />
            </clipPath>
            <clipPath id="wm-coastclip" clipPathUnits="userSpaceOnUse">
              <polygon :points="coastPoints" />
            </clipPath>
            <mask id="wm-litmask" maskUnits="userSpaceOnUse" x="0" y="0" :width="size.w" :height="size.h">
              <g :transform="T">
                <path v-for="p in LIT_PATHS" :key="p.id" :d="p.d" fill="#fff" stroke="#fff" stroke-width="8" stroke-linejoin="round" />
              </g>
            </mask>
            <filter id="wm-paper" x="0" y="0" width="100%" height="100%">
              <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="4" result="n" />
              <feColorMatrix in="n" type="matrix" values="0 0 0 0 0.55  0 0 0 0 0.5  0 0 0 0 0.4  0 0 0 0.09 0" />
            </filter>
          </defs>

          <!-- ═══ WORLD ═══ -->
          <template v-if="tab === 'world'">
            <rect class="wm-sea" :width="size.w" :height="size.h" />
            <g :transform="T">
              <polygon class="wm-land" :points="coastPoints" />
            </g>
            <g mask="url(#wm-litmask)">
              <g :transform="T" clip-path="url(#wm-coastclip)">
                <polygon class="wm-wash" :points="coastPoints" />
                <polygon v-for="s in TERRAIN_SHAPES" :key="s.key" :points="s.points" :fill="s.fill" fill-opacity=".85" />
                <polyline v-for="(p, i) in riverPoints" :key="`r${i}`" class="wm-river" :points="p" />
                <polyline v-for="(p, i) in RIDGE_SEGMENTS" :key="`m${i}`" class="wm-ridge" :points="p" />
                <polyline class="wm-road" points="310,360 600,800 860,1080 1150,1100 1340,1200" />
              </g>
            </g>
            <g clip-path="url(#wm-coastpx)">
              <rect :width="size.w" :height="size.h" fill="url(#wm-hatch)" mask="url(#wm-unlit)" />
            </g>
            <rect :width="size.w" :height="size.h" filter="url(#wm-paper)" style="pointer-events: none" />
            <g :transform="T">
              <path v-for="p in UNLIT_PATHS" :key="`u${p.id}`" class="wm-dborder wm-dborder--dark" :class="{ 'is-selected': selection === `district:${p.id}` }" :d="p.d" />
              <path v-for="p in LIT_PATHS" :key="`l${p.id}`" class="wm-dborder wm-dborder--lit" :class="{ 'is-selected': selection === `district:${p.id}` }" :d="p.d" />
              <path class="wm-nborder" :d="NATION_BORDER_PATH" />
              <polygon class="wm-coast" :points="coastPoints" />
              <polyline class="wm-trail" :points="trailPoints" />
              <template v-if="showCells">
                <rect v-for="([x, y], i) in trailUnique" :key="`c${i}`" class="wm-trailcell" :x="x" :y="y" width="1" height="1" />
              </template>
              <circle
                v-for="q in worldQuests.filter((item) => !item.precise)"
                :key="`v${q.id}`"
                class="wm-vague"
                :cx="q.x"
                :cy="q.y"
                r="55"
              />
            </g>

            <!-- pixel-space labels and markers -->
            <text v-for="n in nationLabels" :key="n.key" class="wm-nation" :x="n.x" :y="n.y">{{ n.name }}</text>
            <g v-for="d in landmarkGlyphs" :key="`t${d.i}`" class="wm-tower" :transform="`translate(${d.x} ${d.y})`" :data-pick="`district:${d.i}`">
              <path d="M-5 7 L-3 -6 L0 -9 L3 -6 L5 7 Z" />
            </g>
            <text
              v-for="d in districtLabels"
              :key="`d${d.i}`"
              class="wm-district"
              :class="{ 'is-unlit': !d.lit }"
              :x="d.x"
              :y="d.y + (d.lit ? 26 : 6)"
            >{{ d.name }}</text>
            <g v-for="p in placeMarkers" :key="p.id" class="wm-place" :class="`wm-place--${p.kind}`" :transform="`translate(${p.x} ${p.y})`" :data-pick="`place:${p.id}`">
              <rect x="-7" y="-7" width="14" height="14" transform="rotate(45)" />
              <text v-if="p.label" x="12" y="5">{{ p.name }}</text>
            </g>
            <template v-for="q in worldQuests" :key="`q${q.id}`">
              <g v-if="q.onScreen" class="wm-quest" :class="{ 'is-vague': !q.precise, 'is-selected': selection === `quest:${q.id}` }" :transform="`translate(${q.px} ${q.py})`" :data-pick="`quest:${q.id}`">
                <path d="M0 -16 L9 -4 L0 6 L-9 -4 Z" />
                <circle cy="-5" r="2.5" class="wm-quest__eye" />
                <text x="0" y="24">{{ q.precise ? q.target : `${q.target}（大致方位）` }}</text>
              </g>
            </template>
            <g class="wm-here" :transform="`translate(${player.x} ${player.y})`">
              <circle r="11" class="wm-here__ring" />
              <circle r="6" class="wm-here__dot" />
            </g>
          </template>

          <!-- ═══ AREA: CITY ═══ -->
          <template v-else-if="!isWild">
            <rect class="wm-citybg" :width="size.w" :height="size.h" />
            <rect :width="size.w" :height="size.h" fill="url(#wm-dots)" />
            <line
              v-for="r in cityRoads"
              :key="r.key"
              class="wm-street"
              :class="{ 'is-seen': r.seen }"
              :x1="toPx(r.a.x, r.a.y).x"
              :y1="toPx(r.a.x, r.a.y).y"
              :x2="toPx(r.b.x, r.b.y).x"
              :y2="toPx(r.b.x, r.b.y).y"
            />
            <g
              v-for="n in cityNodes"
              :key="n.id"
              class="wm-node"
              :class="[`is-${n.state}`, { 'is-adjacent': n.adjacent, 'is-gate': n.gateway, 'is-selected': selection === `node:${n.id}` }]"
              :transform="`translate(${n.x} ${n.y})`"
              :data-pick="`node:${n.id}`"
            >
              <circle v-if="n.adjacent" r="15" class="wm-node__halo" />
              <path v-if="n.gateway" d="M-8 8 V-3 A8 8 0 0 1 8 -3 V8 Z" class="wm-node__gate" />
              <circle v-else :r="n.state === 'current' ? 8 : 5.5" class="wm-node__dot" />
              <text class="wm-node__label" x="0" :y="-16">{{ n.name }}</text>
              <text v-if="n.gateway" class="wm-node__sub" x="0" y="26">通往 {{ n.gateway }}</text>
              <g v-if="n.quest" class="wm-quest wm-quest--pin" transform="translate(14 -14)">
                <path d="M0 -12 L7 -3 L0 4 L-7 -3 Z" />
              </g>
            </g>
          </template>

          <!-- ═══ AREA: WILDERNESS NEIGHBOURHOOD ═══ -->
          <template v-else>
            <rect class="wm-citybg" :width="size.w" :height="size.h" />
            <g :transform="T">
              <rect
                v-for="c in wildCells"
                :key="`${c.x}:${c.y}`"
                class="wm-wcell"
                :class="{ 'is-visited': c.visited, 'is-current': c.current, 'is-adjacent': c.adjacent }"
                :x="c.x + 0.06"
                :y="c.y + 0.06"
                width="0.88"
                height="0.88"
              />
            </g>
            <text
              v-for="c in wildCells.filter((cell) => cell.adjacent)"
              :key="`l${c.x}:${c.y}`"
              class="wm-wlabel"
              :x="toPx(c.x + 0.5, c.y + 0.5).x"
              :y="toPx(c.x + 0.5, c.y + 0.5).y + 5"
            >{{ ['西南','南','東南','西','','東','西北','北','東北'][(c.y - PLAYER_WORLD.y + 1) * 3 + (c.x - PLAYER_WORLD.x + 1)] }}</text>
            <g class="wm-here" :transform="`translate(${toPx(PLAYER_WORLD.x + 0.5, PLAYER_WORLD.y + 0.5).x} ${toPx(PLAYER_WORLD.x + 0.5, PLAYER_WORLD.y + 0.5).y})`">
              <circle r="11" class="wm-here__ring" />
              <circle r="6" class="wm-here__dot" />
            </g>
          </template>
        </svg>

        <!-- edge pointers for off-screen quest destinations (HTML layer) -->
        <div class="wm-edges">
          <template v-if="tab === 'world'">
            <button
              v-for="q in worldQuests.filter((item) => !item.onScreen)"
              :key="q.id"
              type="button"
              class="wm-edge"
              :class="`wm-edge--${q.edge.side}`"
              :style="{ left: `${q.edge.x}px`, top: `${q.edge.y}px` }"
              :aria-label="`委託 ${q.title}，約 ${q.km} km，移到地圖上`"
              @pointerdown.stop
              @click="selection = `quest:${q.id}`; centreOn(q.x, q.y)"
            >
              <span class="wm-edge__arrow" :style="{ transform: `rotate(${q.edge.angle}deg)` }">➤</span>
              <span class="wm-edge__text">{{ q.title }}<small>{{ q.km }} km</small></span>
            </button>
          </template>
          <template v-else-if="!isWild">
            <button
              v-for="q in cityOutsideQuests"
              :key="q.id"
              type="button"
              class="wm-edge"
              :class="`wm-edge--${q.edge.side}`"
              :style="{ left: `${q.edge.x}px`, top: `${q.edge.y}px` }"
              @pointerdown.stop
              @click="tab = 'world'"
            >
              <span class="wm-edge__arrow" :style="{ transform: `rotate(${q.edge.angle}deg)` }">➤</span>
              <span class="wm-edge__text">{{ q.title }}<small>{{ q.outside.label }} · 開世界地圖</small></span>
            </button>
          </template>
        </div>

        <!-- Option A: floating chrome -->
        <div v-if="layout === 'floating'" class="wm-qdrop">
          <button type="button" class="wm-chip" :aria-expanded="questsOpen" @pointerdown.stop @click="questsOpen = !questsOpen">
            ◆ 委託 {{ trackedQuests.length }} <span aria-hidden="true">▾</span>
          </button>
          <ul v-if="questsOpen" class="wm-qlist wm-pop" @pointerdown.stop>
            <li v-for="q in trackedQuests" :key="q.id">
              <button type="button" @click="focusQuest(q)"><span class="wm-qglyph">◆</span>{{ q.title }}<small>{{ q.sub }}</small></button>
            </li>
          </ul>
        </div>

        <div class="wm-pill" :style="drawerOpen ? { right: `${DRAWER_W + 16}px` } : null" @pointerdown.stop>
          <button type="button" aria-label="縮小" @click="zoomOut">－</button>
          <span class="wm-pill__stop">{{ stopName }}</span>
          <button type="button" aria-label="放大" @click="zoomIn">＋</button>
          <span class="wm-pill__sep" />
          <button type="button" aria-label="回到目前位置" title="回到目前位置 (C)" @click="recentre">⌖</button>
          <button type="button" title="全圖 (0)" @click="fitAll">全圖</button>
          <template v-if="layout === 'floating'">
            <span class="wm-pill__sep" />
            <button type="button" aria-label="圖例" :aria-expanded="legendOpen" @click="legendOpen = !legendOpen">?</button>
          </template>
          <ul v-if="legendOpen" class="wm-legend wm-pop wm-pop--right">
            <li v-for="item in LEGEND" :key="item.g"><i :class="`lg lg--${item.g}`" />{{ item.t }}</li>
          </ul>
        </div>

        <div class="wm-scale" aria-hidden="true">
          <span class="wm-scale__bar" :style="{ width: `${scaleBar.px}px` }" />
          <span>{{ scaleBar.text }}</span>
          <span v-if="tab === 'area' && !isWild" class="wm-scale__dots">· 格距 {{ dotStep >= 1000 ? `${dotStep / 1000} km` : `${dotStep} m` }}</span>
        </div>

        <!-- Option A: drawer only on selection -->
        <aside v-if="layout === 'floating'" class="wm-drawer" :class="{ 'is-open': !!detail }" @pointerdown.stop>
          <template v-if="detail">
            <button type="button" class="wm-drawer__close" aria-label="關閉詳情" @click="selection = null">✕</button>
            <p class="wm-drawer__kind">{{ detail.kind }}</p>
            <h3 class="wm-drawer__title">{{ detail.title }}</h3>
            <p v-for="line in detail.lines" :key="line" class="wm-drawer__line">{{ line }}</p>
            <template v-if="detail.quests.length">
              <h4>相關委託</h4>
              <ul class="wm-qlist">
                <li v-for="q in detail.quests" :key="q.id"><button type="button" @click="selection = `quest:${q.id}`"><span class="wm-qglyph">◆</span>{{ q.title }}</button></li>
              </ul>
            </template>
            <button v-if="detail.move" type="button" class="wm-cta">前往</button>
            <button v-else-if="detail.at" type="button" class="wm-ghost" @click="centreOn(detail.at[0], detail.at[1])">置中顯示</button>
          </template>
        </aside>
      </div>

      <!-- Option B: persistent detail panel -->
      <aside v-if="layout === 'columns'" class="wm-panel">
        <template v-if="detail">
          <p class="wm-drawer__kind">{{ detail.kind }}</p>
          <h3 class="wm-drawer__title">{{ detail.title }}</h3>
          <p v-for="line in detail.lines" :key="line" class="wm-drawer__line">{{ line }}</p>
          <button v-if="detail.move" type="button" class="wm-cta">前往</button>
        </template>
        <p v-else class="wm-panel__empty">點選地圖上的地點、分區或委託，這裡會顯示詳情。</p>
      </aside>
    </div>
  </section>
</template>

<style scoped>
.wm {
  --wm-line: rgba(185, 154, 96, 0.3);
  --wm-gold: var(--gold-400);
  position: relative;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  height: 100%;
  color: var(--paper-200);
  font-family: var(--f-sans);
  background: linear-gradient(180deg, #16181dfa, #0e1014fa);
  border: 1px solid rgba(185, 154, 96, 0.45);
  border-radius: var(--radius, 6px);
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.55);
  overflow: hidden;
  box-sizing: border-box;
}
.wm *, .wm *::before, .wm *::after { box-sizing: border-box; }
.wm button { font: inherit; color: inherit; cursor: pointer; }
.wm :focus-visible { outline: 2px solid var(--gold-400); outline-offset: 2px; }

.wm-head {
  display: grid;
  grid-template-columns: auto auto 1fr auto;
  align-items: center;
  gap: 16px;
  padding: 10px 18px;
  border-bottom: 1px solid var(--wm-line);
  background: linear-gradient(180deg, rgba(0, 0, 0, 0.25), transparent);
}
.wm-head__seal {
  display: grid; place-items: center;
  width: 36px; height: 36px;
  color: var(--gold-400);
  font-size: 18px;
  border: 1px solid var(--gold-600);
  border-radius: 50%;
}
.wm-tabs { display: flex; gap: 4px; }
.wm-tab {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 18px;
  font-family: var(--f-display) !important;
  font-size: 20px !important;
  letter-spacing: 0.12em;
  background: none;
  border: 1px solid transparent;
  border-radius: 4px;
  color: var(--paper-400) !important;
}
.wm-tab kbd {
  font: 12px var(--f-mono, monospace);
  padding: 0 5px;
  border: 1px solid var(--ink-600);
  border-radius: 3px;
  color: var(--paper-500);
}
.wm-tab.is-active {
  color: var(--paper-50) !important;
  border-color: var(--gold-600);
  background: radial-gradient(circle at 50% 0%, rgba(185, 154, 96, 0.2), transparent 70%);
}
.wm-head__place { margin: 0; color: var(--paper-400); font-size: 16px; letter-spacing: 0.05em; }
.wm-head__close {
  width: 34px; height: 34px;
  background: none;
  border: 1px solid var(--ink-600);
  border-radius: 50%;
}

.wm-body { position: relative; display: grid; grid-template-columns: minmax(0, 1fr); min-height: 0; }
.wm--columns .wm-body { grid-template-columns: 260px minmax(0, 1fr) 320px; }

.wm-map {
  position: relative;
  min-height: 0;
  overflow: hidden;
  touch-action: none;
  cursor: grab;
  background: radial-gradient(70% 60% at 40% 30%, var(--map-canvas-hi), var(--map-canvas-lo));
}
.wm-map:active { cursor: grabbing; }
.wm-svg { position: absolute; inset: 0; display: block; }

/* world layers */
.wm-sea { fill: #0b1117; }
.wm-land { fill: #23211c; }
.wm-coast { fill: none; stroke: #9c8d6c; stroke-width: 1.6; vector-effect: non-scaling-stroke; }
.wm-river { fill: none; stroke: #4f7487; stroke-width: 2.4; vector-effect: non-scaling-stroke; }
.wm-ridge { fill: none; stroke: #b9ab8c; stroke-width: 2.2; stroke-dasharray: 2 3; vector-effect: non-scaling-stroke; }
.wm-road { fill: none; stroke: #d9c79c; stroke-width: 1.4; stroke-dasharray: 7 4; vector-effect: non-scaling-stroke; opacity: 0.8; }
.wm-dborder { fill: none; vector-effect: non-scaling-stroke; }
.wm-wash { fill: #5f5b40; }
.wm-dborder--lit { stroke: #c9b78e; stroke-width: 1.1; stroke-opacity: 0.6; }
.wm-dborder--dark { stroke: #6f6655; stroke-width: 1; stroke-dasharray: 1 4; stroke-opacity: 0.55; }
.wm-dborder.is-selected { stroke: var(--gold-300); stroke-width: 2.6; stroke-opacity: 1; stroke-dasharray: none; }
.wm-nborder { fill: none; stroke: #b0574f; stroke-width: 2.2; stroke-dasharray: 9 4 2 4; vector-effect: non-scaling-stroke; stroke-opacity: 0.85; }
.wm-trail { fill: none; stroke: var(--gold-300); stroke-width: 3; stroke-linejoin: round; vector-effect: non-scaling-stroke; }
.wm-trailcell { fill: rgba(238, 221, 180, 0.35); stroke: var(--gold-300); stroke-width: 1; vector-effect: non-scaling-stroke; }
.wm-vague { fill: rgba(224, 107, 107, 0.06); stroke: var(--seal-400); stroke-width: 1.6; stroke-dasharray: 6 5; vector-effect: non-scaling-stroke; }

.wm-nation {
  fill: rgba(242, 236, 223, 0.55);
  font: 20px var(--f-display);
  letter-spacing: 0.4em;
  text-anchor: middle;
  paint-order: stroke;
  stroke: #0b1117; stroke-width: 4;
  pointer-events: none;
}
.wm-district {
  fill: var(--paper-100);
  font: 16px var(--f-display);
  letter-spacing: 0.12em;
  text-anchor: middle;
  paint-order: stroke;
  stroke: #15140f; stroke-width: 4;
  pointer-events: none;
}
.wm-district.is-unlit { fill: #8f877a; font-style: italic; font-size: 16px; letter-spacing: 0.2em; }
.wm-tower path { fill: var(--gold-400); stroke: #15140f; stroke-width: 1.5; cursor: pointer; }
.wm-place rect { fill: #e7e0d1; stroke: #15140f; stroke-width: 2; cursor: pointer; }
.wm-place--capital rect { fill: var(--gold-400); }
.wm-place text {
  fill: var(--paper-50); font: 16px var(--f-sans);
  paint-order: stroke; stroke: #15140f; stroke-width: 4; pointer-events: none;
}

.wm-quest path { fill: var(--seal-500); stroke: #fff2e6; stroke-width: 1.6; cursor: pointer; }
.wm-quest__eye { fill: #fff2e6; }
.wm-quest.is-vague path { fill: rgba(207, 68, 68, 0.15); stroke: var(--seal-400); stroke-dasharray: 3 2; }
.wm-quest.is-vague .wm-quest__eye { fill: var(--seal-400); }
.wm-quest.is-selected path { stroke: var(--gold-300); stroke-width: 3; }
.wm-quest text {
  fill: #ffd9d4; font: 16px var(--f-sans); text-anchor: middle;
  paint-order: stroke; stroke: #15140f; stroke-width: 4; pointer-events: none;
}

.wm-here__ring { fill: none; stroke: #fff2e6; stroke-width: 2; }
.wm-here__dot { fill: var(--seal-deep); stroke: #fff2e6; stroke-width: 2; }

/* edge pointers */
.wm-edge {
  position: absolute;
  transform: translate(-50%, -50%);
  display: flex; align-items: center; gap: 6px;
  padding: 4px 10px 4px 6px;
  font-size: 16px !important;
  color: #ffd9d4 !important;
  background: rgba(20, 12, 12, 0.88);
  border: 1px solid var(--seal-600);
  border-radius: 999px;
  white-space: nowrap;
  max-width: 260px;
}
.wm-edges { position: absolute; inset: 0; pointer-events: none; }
.wm-edges .wm-edge { pointer-events: auto; }
.wm-edge--right { transform: translate(-100%, -50%); flex-direction: row-reverse; padding: 4px 6px 4px 10px; }
.wm-edge--left { transform: translate(0, -50%); }
.wm-edge--top { transform: translate(-50%, 0); }
.wm-edge--bottom { transform: translate(-50%, -100%); }
.wm-edge__arrow { display: inline-block; color: var(--seal-400); font-size: 16px; }
.wm-edge__text small { margin-left: 6px; color: var(--paper-400); font-size: 14px; }

/* area: city */
.wm-citybg { fill: transparent; }
.wm-street { stroke: #b6a888; stroke-width: 3; stroke-linecap: round; }
.wm-street.is-seen { stroke: #6d6656; stroke-dasharray: 5 6; stroke-width: 2; }
.wm-node { cursor: pointer; }
.wm-node__dot { fill: #d8d2c5; stroke: #15140f; stroke-width: 2; }
.wm-node.is-seen .wm-node__dot { fill: #2a2925; stroke: #8f877a; stroke-dasharray: 2 2; }
.wm-node.is-current .wm-node__dot { fill: var(--seal-deep); stroke: #fff2e6; }
.wm-node__gate { fill: #3a342a; stroke: var(--gold-400); stroke-width: 2; }
.wm-node__halo { fill: rgba(228, 200, 142, 0.1); stroke: var(--gold-500); stroke-width: 1; stroke-dasharray: 3 3; }
.wm-node.is-selected .wm-node__halo, .wm-node.is-selected .wm-node__dot { stroke: var(--gold-300); stroke-width: 3; }
.wm-node__label {
  fill: var(--paper-100); font: 16px var(--f-sans); text-anchor: middle;
  paint-order: stroke; stroke: #101216; stroke-width: 4; pointer-events: none;
}
.wm-node.is-current .wm-node__label { fill: var(--paper-50); font-weight: 700; }
.wm-node.is-seen .wm-node__label { fill: #9a9385; }
.wm-node__sub {
  fill: var(--gold-400); font: 16px var(--f-sans); text-anchor: middle;
  paint-order: stroke; stroke: #101216; stroke-width: 4; pointer-events: none;
}
.wm-quest--pin path { fill: var(--seal-500); stroke: #fff2e6; stroke-width: 1.4; }

/* area: wilderness */
.wm-wcell { fill: rgba(42, 41, 37, 0.6); stroke: #4e483d; stroke-width: 1; vector-effect: non-scaling-stroke; }
.wm-wcell.is-visited { fill: rgba(185, 154, 96, 0.28); stroke: #8f713c; }
.wm-wcell.is-adjacent { stroke: var(--gold-500); stroke-dasharray: 4 3; cursor: pointer; }
.wm-wcell.is-current { fill: rgba(165, 44, 49, 0.25); stroke: var(--seal-400); }
.wm-wlabel { fill: var(--paper-200); font: 16px var(--f-sans); text-anchor: middle; pointer-events: none; }

/* floating chrome */
.wm-chip, .wm-pill {
  background: rgba(14, 16, 20, 0.9);
  border: 1px solid var(--wm-line);
  border-radius: 999px;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.45);
}
.wm-qdrop { position: absolute; top: 14px; left: 14px; }
.wm-chip { padding: 6px 14px; font-size: 16px !important; color: #ffd9d4 !important; }
.wm-pill {
  position: absolute; top: 14px; right: 14px;
  display: flex; align-items: center; gap: 2px;
  padding: 4px 6px;
  transition: right 0.2s ease;
}
.wm-pill button { min-width: 34px; height: 32px; padding: 0 8px; background: none; border: 0; border-radius: 999px; font-size: 16px !important; }
.wm-pill button:hover { background: rgba(185, 154, 96, 0.14); }
.wm-pill__stop { min-width: 44px; text-align: center; color: var(--gold-400); font: 16px var(--f-display); letter-spacing: 0.1em; }
.wm-pill__sep { width: 1px; height: 20px; background: var(--wm-line); margin: 0 4px; }
.wm-pop {
  position: absolute; top: calc(100% + 8px); left: 0;
  min-width: 280px; margin: 0; padding: 10px 12px;
  list-style: none;
  background: rgba(14, 16, 20, 0.96);
  border: 1px solid var(--wm-line);
  border-radius: 8px;
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.5);
}
.wm-pop--right { left: auto; right: 0; }

.wm-qlist { margin: 0; padding: 0; list-style: none; }
.wm-qlist button {
  display: grid; grid-template-columns: auto 1fr; column-gap: 8px;
  width: 100%; padding: 6px 4px; text-align: left;
  font-size: 16px !important;
  background: none; border: 0; border-radius: 4px;
}
.wm-qlist button:hover { background: rgba(185, 154, 96, 0.12); }
.wm-qlist small { grid-column: 2; color: var(--paper-500); font-size: 14px; }
.wm-qglyph { color: var(--seal-400); }

.wm-legend { margin: 0; padding: 0; list-style: none; font-size: 16px; }
.wm-legend li { display: flex; align-items: center; gap: 10px; padding: 3px 0; }
.lg { display: inline-block; width: 22px; height: 14px; flex: none; }
.lg--here { width: 14px; border-radius: 50%; background: var(--seal-deep); box-shadow: 0 0 0 2px #fff2e6; }
.lg--trail { height: 3px; background: var(--gold-300); }
.lg--lit { background: #5b5a3e; border: 1px solid #c9b78e; }
.lg--unlit { background: repeating-linear-gradient(45deg, rgba(138, 127, 104, 0.45) 0 1px, transparent 1px 6px), #23211c; border: 1px dotted #6f6655; }
.lg--nation { height: 0; border-top: 2px dashed #b0574f; }
.lg--tower { width: 10px; background: var(--gold-400); clip-path: polygon(20% 100%, 30% 15%, 50% 0, 70% 15%, 80% 100%); }
.lg--quest { width: 14px; background: var(--seal-500); clip-path: polygon(50% 0, 100% 55%, 50% 100%, 0 55%); }
.lg--questVague { width: 18px; height: 18px; border-radius: 50%; border: 1.5px dashed var(--seal-400); }
.lg--visited { width: 12px; height: 12px; border-radius: 50%; background: #d8d2c5; }
.lg--seen { width: 12px; height: 12px; border-radius: 50%; border: 1.5px dashed #8f877a; }
.lg--gate { width: 14px; background: #3a342a; border: 2px solid var(--gold-400); border-radius: 7px 7px 0 0; }

.wm-scale {
  position: absolute; left: 16px; bottom: 14px;
  display: flex; align-items: center; gap: 8px;
  font-size: 16px; color: var(--paper-300);
  pointer-events: none;
}
.wm-scale__bar { height: 8px; border: 2px solid var(--paper-300); border-top: 0; }
.wm-scale__dots { color: var(--paper-500); }

/* option A drawer */
.wm-drawer {
  position: absolute; top: 0; right: 0; bottom: 0;
  width: 360px;
  padding: 22px 22px 18px;
  background: linear-gradient(180deg, #17191ef5, #101216f8);
  border-left: 1px solid var(--wm-line);
  box-shadow: -14px 0 30px rgba(0, 0, 0, 0.4);
  transform: translateX(100%);
  transition: transform 0.22s ease;
}
.wm-drawer.is-open { transform: none; }
@media (prefers-reduced-motion: reduce) { .wm-drawer, .wm-pill { transition: none; } }
.wm-drawer__close { position: absolute; top: 14px; right: 14px; width: 30px; height: 30px; background: none; border: 1px solid var(--ink-600); border-radius: 50%; }
.wm-drawer__kind { margin: 0 0 4px; color: var(--gold-500); font-size: 14px; letter-spacing: 0.15em; }
.wm-drawer__title { margin: 0 0 14px; color: var(--paper-50); font: 24px var(--f-display); letter-spacing: 0.08em; }
.wm-drawer__line { margin: 0 0 8px; font-size: 16px; line-height: 1.6; color: var(--paper-300); }
.wm-drawer h4, .wm-rail h3 { margin: 18px 0 6px; color: var(--paper-500); font-size: 14px; font-weight: 400; letter-spacing: 0.15em; }
.wm-cta, .wm-ghost {
  margin-top: 18px; padding: 8px 26px;
  font-size: 16px !important;
  border-radius: 4px;
}
.wm-cta { color: #fff !important; background: var(--seal-600); border: 1px solid var(--seal-500); }
.wm-ghost { background: none; border: 1px solid var(--gold-600); color: var(--gold-400) !important; }

/* option B columns */
.wm-rail, .wm-panel { padding: 14px 16px; overflow: auto; background: #121418; }
.wm-rail { border-right: 1px solid var(--wm-line); }
.wm-rail h3:first-child { margin-top: 0; }
.wm-panel { border-left: 1px solid var(--wm-line); }
.wm-panel__empty { color: var(--paper-500); font-size: 16px; line-height: 1.6; }
</style>
