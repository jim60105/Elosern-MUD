<script setup>
// Design/MapEditor: the approved standalone map-editor frontend as an
// interactive reference prototype
// (docs/superpowers/specs/2026-10-26-map-editor-frontend-design.md).
// Mock data only: nothing is saved, no service is called, and the save
// chip's ⟳ → ✓ transition is simulated. It consumes the game's tokens.css
// (loaded by the Storybook preview) and none of the game shell CSS.
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import {
  CONTINENT,
  DIAGNOSTICS,
  DOMAINS,
  ENTRANCE,
  INTERIOR,
  SETTLEMENT,
  TOOLS,
  WORLD_TREE,
} from "./prototype-data.js";

const props = defineProps({
  initialDomain: { type: String, default: "settlement" },
  initialSelection: { type: String, default: null },
  // null | disconnected | saveFailed | externalDraft | stale
  banner: { type: String, default: null },
  noPreview: { type: Boolean, default: false },
  // current | stale | generating | failed
  partition: { type: String, default: "stale" },
  // current | unavailable
  index: { type: String, default: "current" },
  draftDemo: { type: Boolean, default: false },
  deleteDemo: { type: Boolean, default: false },
  followedFrom: { type: String, default: null },
  roadTool: { type: Boolean, default: false },
  drawers: { type: Boolean, default: false },
  diagnosticsOpen: { type: Boolean, default: false },
});

const domain = ref(props.initialDomain);
const selection = ref(props.initialSelection);
const tool = ref(props.roadTool ? "road" : "select");
const returnTo = ref(props.followedFrom);
const diagOpen = ref(props.diagnosticsOpen);
const navOpen = ref(false);
const inspOpen = ref(Boolean(props.drawers && props.initialSelection));
const saveState = ref(props.banner === "saveFailed" ? "failed" : props.banner === "externalDraft" ? "draft" : "saved");
const savedAt = ref("14:02");
const partitionState = ref(props.partition);
const deleteShown = ref(props.deleteDemo);
const copied = ref(false);
const bidirectional = ref(true);
const root = ref(null);

// ------------------------------------------------------------------ fields
const drafts = ref({});
const errors = ref({});
if (props.draftDemo) {
  drafts.value = { name: "北門大道（舊城段）", n: "12o" };
  errors.value = { n: "需要整數公尺（目前輸入含字母 o）。未存檔，焦點保留在此欄位。" };
}
if (props.banner === "externalDraft") drafts.value = { name: "北門大道（舊城段）" };

const nodeById = Object.fromEntries(SETTLEMENT.nodes.map((n) => [n.id, n]));
const roomById = Object.fromEntries(INTERIOR.rooms.map((r) => [r.id, r]));

// ---------------------------------------------------------------- geometry
const px = (node) => ({ x: 400 + node.e * 2, y: 300 - node.n * 2 });
const settlementRoads = computed(() => {
  const seen = new Set();
  const out = [];
  for (const [a, b, dir] of SETTLEMENT.roads) {
    const key = [a, b].sort().join("|");
    const twoWay = SETTLEMENT.roads.some(([c, d]) => c === b && d === a);
    if (seen.has(key)) continue;
    seen.add(key);
    out.push({ a, b, dir, twoWay, ...segment(nodeById[a], nodeById[b]) });
  }
  return out;
});
function segment(a, b) {
  const p = px(a);
  const q = px(b);
  return { x1: p.x, y1: p.y, x2: q.x, y2: q.y };
}
function roadLength(a, b) {
  const p = nodeById[a];
  const q = nodeById[b];
  return Math.round(Math.hypot(p.e - q.e, p.n - q.n));
}

function brackets({ x, y }) {
  const r = 18;
  const l = 6;
  return [
    `M${x - r} ${y - r + l} v${-l} h${l}`,
    `M${x + r} ${y - r + l} v${-l} h${-l}`,
    `M${x - r} ${y + r - l} v${l} h${l}`,
    `M${x + r} ${y + r - l} v${l} h${-l}`,
  ].join(" ");
}
// A chevron on the outgoing side of a directed road from the selected node.
function chevron(a, b) {
  const p = px(a);
  const q = px(b);
  const len = Math.hypot(q.x - p.x, q.y - p.y) || 1;
  const ux = (q.x - p.x) / len;
  const uy = (q.y - p.y) / len;
  const cx = p.x + ux * Math.min(46, len / 2);
  const cy = p.y + uy * Math.min(46, len / 2);
  const s = 6;
  return `M${cx - ux * s - uy * s} ${cy - uy * s + ux * s} L${cx} ${cy} L${cx - ux * s + uy * s} ${cy - uy * s - ux * s}`;
}

// Interior connection curves, clipped to the 140x56 room cards; a two-way
// pair draws two offset arrows and one ⇄ label.
const interiorConnections = computed(() => {
  const at = Object.fromEntries([...INTERIOR.rooms, INTERIOR.exterior].map((r) => [r.id, r]));
  const out = [];
  for (const c of INTERIOR.connections) {
    const a = at[c.from];
    const b = at[c.to];
    const pairs = c.back ? [[a, b, 7], [b, a, 7]] : [[a, b, 0]];
    for (const [p, q, off] of pairs) out.push({ key: `${p.id}>${q.id}`, d: arc(p, q, off) });
    const mx = (a.x + b.x) / 2;
    const my = (a.y + b.y) / 2;
    out[out.length - 1].label = c.back ? `${c.dir} ⇄ ${c.back}` : `${c.dir}（單向）`;
    out[out.length - 1].lx = mx + 20;
    out[out.length - 1].ly = my + 26;
  }
  return out;
});
function clip(p, q) {
  const dx = q.x - p.x;
  const dy = q.y - p.y;
  const t = Math.min(76 / Math.abs(dx || 1e-6), 34 / Math.abs(dy || 1e-6));
  return { x: p.x + dx * t, y: p.y + dy * t };
}
function arc(p, q, off) {
  const s = clip(p, q);
  const e = clip(q, p);
  const len = Math.hypot(e.x - s.x, e.y - s.y) || 1;
  const nx = -(e.y - s.y) / len;
  const ny = (e.x - s.x) / len;
  const ox = nx * off;
  const oy = ny * off;
  return `M${s.x + ox} ${s.y + oy} L${e.x + ox} ${e.y + oy}`;
}

// --------------------------------------------------------------- selection
const selectedNode = computed(() => (domain.value === "settlement" ? nodeById[selection.value] : null));
const selectedRoom = computed(() => (domain.value === "interior" ? roomById[selection.value] : null));
const selectedPoint = computed(() => {
  if (domain.value !== "continent" || !selection.value?.startsWith("cp:")) return null;
  const index = Number(selection.value.slice(3));
  return { index, ...CONTINENT.waterways[0].points[index] };
});
const selectedEntrance = computed(() => selection.value === "entrance");

const objectList = computed(() => {
  if (domain.value === "settlement") return SETTLEMENT.nodes.map((n) => ({ id: n.id, label: n.name }));
  if (domain.value === "interior") return INTERIOR.rooms.map((r) => ({ id: r.id, label: r.name }));
  return CONTINENT.waterways[0].points.map((_, i) => ({ id: `cp:${i}`, label: `霜溪 · 控制點 ${i + 1}` }));
});
const objectHeading = computed(() => {
  if (domain.value === "settlement") return `物件 · ${SETTLEMENT.nodes.length}`;
  if (domain.value === "interior") return `房間 · ${INTERIOR.rooms.length}`;
  return "水系 · 霜溪 · 9 個控制點";
});
const crumb = computed(() => {
  if (domain.value === "continent") return ["艾洛森大陸", "水系"];
  if (domain.value === "interior") return ["灰岩鎮", INTERIOR.name];
  return ["灰岩鎮", SETTLEMENT.map];
});

function select(id) {
  selection.value = id;
  deleteShown.value = false;
  if (props.drawers) inspOpen.value = true;
}
function setDomain(key) {
  if (domain.value === key) return;
  domain.value = key;
  selection.value = null;
  deleteShown.value = false;
  tool.value = "select";
}

// --------------------------------------------------------- inspector edits
function fieldValue(key, saved) {
  return key in drafts.value ? drafts.value[key] : saved;
}
function onInput(key, event) {
  drafts.value = { ...drafts.value, [key]: event.target.value };
  const { [key]: _drop, ...rest } = errors.value;
  errors.value = rest;
}
function commit(key, kind, event) {
  if (!(key in drafts.value)) return;
  const value = drafts.value[key];
  if (kind === "int" && !/^-?\d+$/.test(String(value).trim())) {
    errors.value = { ...errors.value, [key]: "需要整數公尺。未存檔，焦點保留在此欄位。" };
    event?.target?.focus();
    return;
  }
  if (kind === "id" && SETTLEMENT.nodes.some((n) => n.id === value)) {
    errors.value = { ...errors.value, [key]: `這份文件中已有 ${value}。` };
    event?.target?.focus();
    return;
  }
  const { [key]: _drop, ...rest } = drafts.value;
  drafts.value = rest;
  saveState.value = "saving";
  setTimeout(() => {
    saveState.value = "saved";
    savedAt.value = "14:12";
  }, 700);
}
function cancel(key, event) {
  const { [key]: _d, ...rest } = drafts.value;
  drafts.value = rest;
  const { [key]: _e, ...restErrors } = errors.value;
  errors.value = restErrors;
  event?.target?.blur();
}
const hasDraft = computed(() => Object.keys(drafts.value).length > 0);
const anyError = computed(() => Object.keys(errors.value).length > 0);

// --------------------------------------------------------------- deletion
const deleteRefs = computed(() => {
  if (props.index === "unavailable") return null;
  if (selectedNode.value) {
    const refs = [...(SETTLEMENT.references[selectedNode.value.id] || [])];
    const roads = SETTLEMENT.roads.filter(([, b]) => b === selectedNode.value.id);
    for (const [a, , dir] of roads) refs.unshift({ kind: "道路", label: `${nodeById[a].name} → ${selectedNode.value.name}（${dir}）`, source: "同一份文件", target: a });
    return refs;
  }
  return [];
});

// ------------------------------------------------------------ navigation
function followEntrance() {
  if (domain.value === "settlement") {
    returnTo.value = `${SETTLEMENT.map} · 北門大道`;
    domain.value = "interior";
    selection.value = "shopfront";
  } else {
    returnTo.value = `${INTERIOR.name} · 前店`;
    domain.value = "settlement";
    selection.value = "entrance";
  }
}
function goBack() {
  if (!returnTo.value) return;
  if (domain.value === "settlement") {
    domain.value = "interior";
    selection.value = "shopfront";
  } else {
    domain.value = "settlement";
    selection.value = "north_gate_ave";
  }
  returnTo.value = null;
}

// ------------------------------------------------------------ copy context
const contextText = computed(() => {
  const current = props.banner === "stale" || props.banner === "disconnected" ? "過期預覽（最後可用版本 14:07）" : "現行檔案";
  if (selectedNode.value) {
    const n = selectedNode.value;
    return [
      `[地圖編纂脈絡] 來源：${current}`,
      `文件：${SETTLEMENT.path}`,
      `物件：settlement:${SETTLEMENT.id}/${n.id}（${n.name}）`,
      `座標：東 ${n.e} m、北 ${n.n} m（據點地方座標，公尺）`,
    ].join("\n");
  }
  return `[地圖編纂脈絡] 來源：${current}\n選取：${selection.value ?? "（無）"}`;
});
async function copyContext() {
  try {
    await navigator.clipboard?.writeText(contextText.value);
  } catch {
    // Storybook frames may refuse clipboard access; the prototype still
    // shows the confirmation.
  }
  copied.value = true;
  setTimeout(() => (copied.value = false), 1800);
}

// ------------------------------------------------------------ chips/banner
const chips = computed(() => {
  const save = {
    saved: { tone: "ok", text: `✓ 已存檔 ${savedAt.value}` },
    saving: { tone: "busy", text: "⟳ 存檔中" },
    draft: { tone: "warn", text: "✎ 有未確認草稿" },
    failed: { tone: "bad", text: "✕ 存檔失敗" },
  }[hasDraft.value && saveState.value === "saved" ? "draft" : saveState.value];
  let sync = { tone: "ok", text: "◉ 已同步 14:07" };
  if (props.banner === "disconnected") sync = { tone: "bad", text: "⦸ 服務未連線" };
  else if (props.noPreview) sync = { tone: "off", text: "⦸ 無可用預覽" };
  else if (props.banner === "stale") sync = { tone: "warn", text: "▲ 預覽過期 · YAML 錯誤" };
  else if (props.banner === "externalDraft") sync = { tone: "warn", text: "▲ 外部變更待載入" };
  const index = props.index === "current" ? { tone: "ok", text: "索引 現行" } : { tone: "warn", text: "▲ 索引不可用 · 無法刪除" };
  const partition = {
    current: { tone: "ok", text: "分區 現行" },
    stale: { tone: "warn", text: "▲ 分區過期 · 重新產生" },
    generating: { tone: "busy", text: "⟳ 分區產生中 · 取消" },
    cancelled: { tone: "off", text: "分區已取消 · 保留舊版" },
    failed: { tone: "bad", text: "✕ 分區產生失敗 · 保留舊版" },
  }[partitionState.value];
  return [
    { key: "save", label: "存檔狀態", ...save },
    { key: "sync", label: "檔案同步狀態", ...sync },
    { key: "index", label: "外部索引狀態", ...index },
    { key: "partition", label: "分區狀態", ...partition },
  ];
});
function onChip(key) {
  if (key === "partition") {
    if (partitionState.value === "stale" || partitionState.value === "cancelled" || partitionState.value === "failed") partitionState.value = "generating";
    else if (partitionState.value === "generating") partitionState.value = "cancelled";
    return;
  }
  diagOpen.value = true;
}

const banner = computed(() => {
  if (props.banner === "disconnected") return { tone: "bad", title: "✕ 與編纂服務的連線中斷", body: "畫面停留在 14:07 的快照，現在無法寫入。", action: "重新連線並讀取" };
  if (props.banner === "saveFailed") return { tone: "bad", title: "✕「移動北門大道」未存檔", body: "磁碟已滿（ENOSPC）。檔案仍是 14:02 的版本。", action: "重新讀取" };
  if (props.banner === "externalDraft") return { tone: "warn", title: "▲ greyrock_town.yaml 已被外部修改", body: "載入新版會捨棄「名稱」欄位的草稿與目前的復原歷史。", action: "載入新版" };
  if (props.banner === "stale" || props.noPreview) return { tone: "warn", title: props.noPreview ? "▲ 沒有可用的預覽" : "▲ 顯示的是 14:07 的最後可用版本", body: "content/maps/settlements/greyrock_town.yaml:118 — 重複的鍵「north_gate_ave」", mono: true, action: null };
  return null;
});
const stale = computed(() => props.banner === "stale" || props.banner === "disconnected");

// -------------------------------------------------------------- keyboard
const REGIONS = ["header", "nav", "canvas", "insp", "diag"];
function focusRegion(step) {
  const els = REGIONS.map((r) => root.value?.querySelector(`[data-region="${r}"]`)).filter(Boolean);
  const current = els.findIndex((el) => el.contains(document.activeElement));
  const next = els[(current + step + els.length) % els.length];
  next?.focus();
}
function isTextTarget(target) {
  return target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.tagName === "SELECT" || target.isContentEditable);
}
function onKeydown(event) {
  if (event.key === "F6") {
    event.preventDefault();
    focusRegion(event.shiftKey ? -1 : 1);
    return;
  }
  if (event.altKey && event.key === "ArrowLeft") {
    event.preventDefault();
    goBack();
    return;
  }
  if (isTextTarget(event.target) || event.isComposing || event.ctrlKey || event.metaKey || event.altKey) return;
  const domainKey = DOMAINS.find((d) => d.hotkey === event.key);
  if (domainKey) {
    setDomain(domainKey.key);
    return;
  }
  const t = TOOLS[domain.value].find((x) => x.hotkey && x.hotkey.toLowerCase() === event.key.toLowerCase());
  if (t) {
    tool.value = t.key;
    return;
  }
  if (event.key === "Escape") {
    if (tool.value !== "select") tool.value = "select";
    else if (deleteShown.value) deleteShown.value = false;
    else selection.value = null;
  }
  if (event.key === "Delete" && selection.value) deleteShown.value = true;
  if (event.key === "/") {
    event.preventDefault();
    root.value?.querySelector(".me-search")?.focus();
  }
}
function onCanvasKey(event) {
  if (event.key !== "ArrowRight" && event.key !== "ArrowLeft" && event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
  if (event.shiftKey) return;
  event.preventDefault();
  const list = objectList.value;
  const at = list.findIndex((o) => o.id === selection.value);
  const step = event.key === "ArrowRight" || event.key === "ArrowDown" ? 1 : -1;
  select(list[(at + step + list.length) % list.length].id);
}
function onCanvasEnter() {
  nextTick(() => root.value?.querySelector('[data-region="insp"] input, [data-region="insp"] textarea')?.focus());
}

onMounted(() => window.addEventListener("keydown", onKeydown));
onBeforeUnmount(() => window.removeEventListener("keydown", onKeydown));
watch(domain, () => (deleteShown.value = false));
// Bring the inline refusal into view; it sits below the inspector's fields.
watch(deleteShown, (shown) => {
  if (shown) nextTick(() => root.value?.querySelector(".me-refuse")?.scrollIntoView({ block: "nearest" }));
});
onMounted(() => {
  if (deleteShown.value) nextTick(() => root.value?.querySelector(".me-refuse")?.scrollIntoView({ block: "nearest" }));
});
</script>

<template>
  <div
    ref="root"
    class="me"
    :class="{ 'me--drawers': drawers }"
    lang="zh-Hant-TW"
  >
    <!-- ============================== header ============================== -->
    <header class="me-head" data-region="header" tabindex="-1" aria-label="工作區">
      <span class="me-seal" aria-hidden="true">✎</span>
      <h1 class="me-title">地圖編纂</h1>
      <div class="me-tabs" role="tablist" aria-label="領域">
        <button
          v-for="d in DOMAINS"
          :key="d.key"
          role="tab"
          class="me-tab"
          :class="{ 'is-on': domain === d.key }"
          :aria-selected="domain === d.key"
          :aria-keyshortcuts="d.hotkey"
          @click="setDomain(d.key)"
        >
          {{ d.label }} <span class="me-key" aria-hidden="true">{{ d.hotkey }}</span>
        </button>
      </div>
      <span class="me-vr" aria-hidden="true" />
      <nav class="me-crumb" aria-label="目前位置">
        <button v-if="returnTo" class="me-btn me-back" aria-keyshortcuts="Alt+ArrowLeft" @click="goBack">← 返回 {{ returnTo }}</button>
        <span>{{ crumb[0] }}</span><span class="me-crumb-sep" aria-hidden="true">›</span><span>{{ crumb[1] }}</span>
      </nav>
      <div v-if="drawers" class="me-drawer-toggles">
        <button class="me-btn" :aria-expanded="navOpen" @click="navOpen = !navOpen">導覽</button>
        <button class="me-btn" :aria-expanded="inspOpen" @click="inspOpen = !inspOpen">檢查器</button>
      </div>
      <ul class="me-chips" aria-label="工作區狀態">
        <li v-for="c in chips" :key="c.key">
          <button class="me-chip" :class="`is-${c.tone}`" :aria-label="`${c.label}：${c.text}`" @click="onChip(c.key)">{{ c.text }}</button>
        </li>
      </ul>
    </header>

    <!-- ============================== banner ============================== -->
    <div v-if="banner" class="me-banner" :class="`is-${banner.tone}`" role="status" aria-live="polite">
      <b>{{ banner.title }}</b>
      <span :class="{ 'me-mono': banner.mono }">{{ banner.body }}</span>
      <button v-if="banner.action" class="me-btn me-btn--primary me-push">{{ banner.action }}</button>
    </div>

    <div class="me-body">
      <!-- ============================ navigation ============================ -->
      <nav
        class="me-side"
        :class="{ 'is-open': navOpen }"
        data-region="nav"
        tabindex="-1"
        aria-label="世界導覽"
      >
        <template v-if="domain === 'continent'">
          <h2 class="me-sec">圖層</h2>
          <ul class="me-plain">
            <li v-for="l in CONTINENT.layers" :key="l.key"><label class="me-check"><input type="checkbox" :checked="l.on"> {{ l.label }}</label></li>
          </ul>
        </template>
        <h2 class="me-sec">世界</h2>
        <ul class="me-tree" role="tree" aria-label="世界樹">
          <li
            v-for="t in WORLD_TREE"
            :key="t.id"
            role="treeitem"
            :aria-current="t.domain === domain ? 'page' : undefined"
            :class="[`d${t.depth}`, { 'is-cur': t.domain === domain }]"
            @click="t.domain && setDomain(t.domain)"
          >
            <span class="me-tree-label">{{ t.label }}</span><span v-if="t.tag" class="me-tag">{{ t.tag }}</span>
          </li>
        </ul>
        <h2 class="me-sec">{{ objectHeading }}</h2>
        <input class="me-search" type="search" placeholder="搜尋名稱或 ID…" aria-label="搜尋名稱或 ID" aria-keyshortcuts="/">
        <ul class="me-list" role="listbox" aria-label="物件清單">
          <li
            v-for="o in objectList"
            :key="o.id"
            role="option"
            tabindex="-1"
            :aria-selected="selection === o.id"
            :class="{ 'is-cur': selection === o.id }"
            @click="select(o.id)"
          >
            {{ o.label }}
          </li>
        </ul>
      </nav>

      <!-- ============================== canvas ============================== -->
      <main
        class="me-canvas"
        :class="[`me-canvas--${domain}`, { 'is-stale': stale }]"
        data-region="canvas"
        tabindex="0"
        :aria-label="`地圖畫布：${crumb.join(' › ')}。方向鍵巡覽物件，Enter 編輯。`"
        @keydown="onCanvasKey"
        @keydown.enter="onCanvasEnter"
      >
        <div v-if="noPreview" class="me-nopreview">
          <p class="me-nopreview-title">⦸ 無可用預覽</p>
          <p>尚未成功載入任何版本。請依診斷修正檔案；修正後會自動載入。</p>
        </div>

        <!-- settlement -->
        <svg v-else-if="domain === 'settlement'" viewBox="0 0 800 560" class="me-svg" aria-hidden="true">
          <g class="me-road" v-for="r in settlementRoads" :key="r.a + r.b">
            <line class="me-road-casing" v-bind="{ x1: r.x1, y1: r.y1, x2: r.x2, y2: r.y2 }" />
            <line class="me-road-core" :class="{ 'is-oneway': !r.twoWay }" v-bind="{ x1: r.x1, y1: r.y1, x2: r.x2, y2: r.y2 }" />
          </g>
          <g v-for="n in SETTLEMENT.nodes" :key="n.id" class="me-node" @click="select(n.id)">
            <template v-if="n.prototype === 'gate'">
              <path :d="`M${px(n).x - 9} ${px(n).y + 6} v-8 a9 9 0 0 1 18 0 v8`" class="me-gate" />
            </template>
            <circle v-else :cx="px(n).x" :cy="px(n).y" :r="n.unfinished ? 4 : 6" :class="n.unfinished ? 'me-node-dot is-unfinished' : 'me-node-dot'" />
            <text :x="px(n).x" :y="px(n).y + (n.prototype === 'gate' ? -18 : selection === n.id ? 36 : 24)" class="me-label" :class="{ 'is-sel': selection === n.id }">{{ n.name }}{{ n.gate ? ` · ${n.gate}` : '' }}</text>
          </g>
          <g v-if="selectedNode" class="me-sel">
            <circle :cx="px(selectedNode).x" :cy="px(selectedNode).y" r="14" />
            <path :d="brackets(px(selectedNode))" />
          </g>
          <g v-if="selectedNode" class="me-chevrons">
            <template v-for="[a, b] in SETTLEMENT.roads.filter(([a]) => a === selectedNode.id)" :key="a + b">
              <path :d="chevron(nodeById[a], nodeById[b])" />
            </template>
          </g>
          <g v-if="selectedEntrance" class="me-entrance">
            <path d="M424 162 v-8 a8 8 0 0 1 16 0 v8" class="me-gate" />
            <line x1="410" y1="170" x2="424" y2="162" class="me-dash" />
            <text x="432" y="140" class="me-label is-gold">⌂ 鍛冶工坊</text>
          </g>
        </svg>

        <!-- continent -->
        <svg v-else-if="domain === 'continent'" viewBox="0 0 800 560" class="me-svg" aria-hidden="true">
          <path :d="CONTINENT.coast" class="me-land" />
          <path :d="CONTINENT.coast" class="me-wash" />
          <path v-for="(d, i) in CONTINENT.partition" :key="i" :d="d" class="me-district" />
          <path :d="CONTINENT.ridge" class="me-ridge" />
          <path :d="CONTINENT.ridge" class="me-ridge-dash" />
          <path :d="CONTINENT.waterways[0].path" class="me-river-casing" />
          <path :d="CONTINENT.waterways[0].path" class="me-river" />
          <g v-for="(p, i) in CONTINENT.waterways[0].points" :key="i" @click="select(`cp:${i}`)">
            <rect
              :x="p.x - 6"
              :y="p.y - 6"
              width="12"
              height="12"
              :transform="`rotate(45 ${p.x} ${p.y})`"
              class="me-handle"
              :class="{ 'is-sel': selection === `cp:${i}` }"
            />
          </g>
          <circle v-if="selectedPoint" :cx="selectedPoint.x" :cy="selectedPoint.y" r="16" class="me-handle-ring" />
          <text v-if="selectedPoint" :x="selectedPoint.x + 22" :y="selectedPoint.y - 12" class="me-label is-sel" text-anchor="start">霜溪 · 控制點 {{ selectedPoint.index + 1 }}</text>
          <g v-for="l in CONTINENT.locations" :key="l.id">
            <path v-if="l.local" :d="`M${l.x - 8} ${l.y + 7} l8 -14 l8 14z`" class="me-loc" />
            <circle v-else :cx="l.x" :cy="l.y" r="5" class="me-loc-far" />
            <text :x="l.x" :y="l.y + 26" class="me-label" :class="{ 'is-far': !l.local }">{{ l.name }}</text>
          </g>
          <g transform="translate(340 330)" class="me-ford"><path d="M-8 -4 h16 M-8 4 h16" /></g>
        </svg>

        <!-- interior -->
        <template v-else>
          <svg viewBox="0 0 800 560" class="me-svg" aria-hidden="true">
            <defs>
              <marker id="me-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
                <path d="M0 0 L10 5 L0 10z" class="me-arrowhead" />
              </marker>
            </defs>
            <g class="me-conn">
              <template v-for="c in interiorConnections" :key="c.key">
                <path :d="c.d" marker-end="url(#me-arrow)" />
              </template>
            </g>
            <text v-for="c in interiorConnections.filter((c) => c.label)" :key="'l' + c.key" :x="c.lx" :y="c.ly" class="me-label is-gold">{{ c.label }}</text>
            <g
              v-for="r in [...INTERIOR.rooms, { ...INTERIOR.exterior, ext: true }]"
              :key="r.id"
              class="me-room"
              :class="{ 'is-sel': selection === r.id, 'is-ext': r.ext }"
              @click="r.ext ? followEntrance() : select(r.id)"
            >
              <rect :x="r.x - 70" :y="r.y - 28" width="140" height="56" rx="6" />
              <text :x="r.x" :y="r.y - 4" class="me-room-name">{{ r.ext ? `⌂ ${r.name}` : r.name }}</text>
              <text :x="r.x" :y="r.y + 18" class="me-room-id">{{ r.ext ? r.sub : r.id }}</text>
            </g>
          </svg>
          <p class="me-note">版面僅供編輯器使用 · 不代表距離或座標</p>
        </template>

        <!-- floating chrome -->
        <div class="me-pill me-tools" role="toolbar" aria-label="工具">
          <button
            v-for="t in TOOLS[domain]"
            :key="t.key"
            class="me-tool"
            :class="{ 'is-on': tool === t.key }"
            :aria-pressed="tool === t.key"
            :aria-keyshortcuts="t.hotkey"
            @click="tool = t.key"
          >
            <span aria-hidden="true">{{ t.glyph }}</span> {{ t.label }} <span v-if="t.hotkey" class="me-key" aria-hidden="true">{{ t.hotkey }}</span>
          </button>
        </div>
        <div class="me-pill me-zoom" role="group" aria-label="視圖">
          <button class="me-tool" aria-label="縮小">−</button>
          <span class="me-zoom-level">{{ domain === 'continent' ? '大陸' : domain === 'settlement' ? '全鎮' : '全部' }}</span>
          <button class="me-tool" aria-label="放大">+</button>
          <span class="me-vr" aria-hidden="true" />
          <button class="me-tool">⌖ 適配</button>
        </div>
        <div v-if="domain !== 'interior'" class="me-scale">
          <span class="me-north">▲北</span><i aria-hidden="true" />
          {{ domain === 'continent' ? '100 km · 地理座標（公里）' : '50 m · 地方座標（公尺）' }}
        </div>
        <span v-if="stale" class="me-stale-badge">▲ 過期預覽</span>

        <div v-if="tool === 'road'" class="me-tool-panel" role="group" aria-label="建立道路">
          <h3>建立道路</h3>
          <p>起點 <span class="me-mono">bell_square</span>（鐘樓廣場）→ 終點 <span class="me-mono">copper_street</span>（銅匠街）</p>
          <p>方向 <select class="me-select" aria-label="去程方向"><option>東</option><option>北</option></select>
            <label class="me-check"><input v-model="bidirectional" type="checkbox"> 建立雙向</label>
            <select v-if="bidirectional" class="me-select" aria-label="回程方向"><option>西</option></select></p>
          <p class="me-muted">{{ bidirectional ? '一次操作建立兩筆有向道路：東 → 銅匠街、西 → 鐘樓廣場。' : '只建立一筆有向道路。' }}</p>
          <div><button class="me-btn me-btn--primary">建立</button> <button class="me-btn" @click="tool = 'select'">取消（Esc）</button></div>
        </div>
      </main>

      <!-- ============================= inspector ============================ -->
      <aside
        class="me-side me-insp"
        :class="{ 'is-open': inspOpen }"
        data-region="insp"
        tabindex="-1"
        aria-label="檢查器"
      >
        <!-- settlement node -->
        <template v-if="selectedNode">
          <h2 class="me-sec">檢查器 · 節點</h2>
          <h3 class="me-h">{{ fieldValue('name', selectedNode.name) }}</h3>
          <p class="me-mono me-id">settlement:{{ SETTLEMENT.id }} / {{ selectedNode.id }}</p>
          <p class="me-mono me-id">{{ SETTLEMENT.path }}</p>
          <div class="me-field">
            <label for="me-f-name">名稱</label>
            <input
              id="me-f-name"
              class="me-inp me-inp--text"
              :class="{ 'is-draft': 'name' in drafts }"
              :value="fieldValue('name', selectedNode.name)"
              aria-describedby="me-f-name-hint"
              @input="onInput('name', $event)"
              @keydown.enter="commit('name', 'text', $event)"
              @keydown.esc.stop="cancel('name', $event)"
              @blur="commit('name', 'text', $event)"
            >
            <p v-if="'name' in drafts" id="me-f-name-hint" class="me-hint">草稿 · <kbd>Enter</kbd> 確認並存檔 · <kbd>Esc</kbd> 取消</p>
          </div>
          <div class="me-field">
            <label for="me-f-e">東向</label>
            <span><input id="me-f-e" class="me-inp" :value="selectedNode.e" inputmode="numeric"> <span class="me-unit">m 地方</span></span>
          </div>
          <div class="me-field">
            <label for="me-f-n">北向</label>
            <span>
              <input
                id="me-f-n"
                class="me-inp"
                :class="{ 'is-draft': 'n' in drafts && !errors.n, 'is-err': errors.n }"
                :value="fieldValue('n', selectedNode.n)"
                inputmode="numeric"
                :aria-invalid="Boolean(errors.n)"
                aria-describedby="me-f-n-err"
                @input="onInput('n', $event)"
                @keydown.enter="commit('n', 'int', $event)"
                @keydown.esc.stop="cancel('n', $event)"
              > <span class="me-unit">m 地方</span>
            </span>
            <p v-if="errors.n" id="me-f-n-err" class="me-err">✕ {{ errors.n }}</p>
          </div>
          <div class="me-field"><label>原型</label><span class="me-mono">{{ selectedNode.prototype }}</span></div>
          <div v-if="selectedNode.scene" class="me-field"><label>場景</label><span class="me-mono">{{ selectedNode.scene }}</span></div>
          <div v-if="selectedNode.desc" class="me-field"><label for="me-f-desc">描述</label><textarea id="me-f-desc" class="me-inp me-inp--text" rows="3">{{ selectedNode.desc }}</textarea></div>
          <h2 class="me-sec">道路 · 有向</h2>
          <ul class="me-plain">
            <li v-for="[a, b, dir] in SETTLEMENT.roads.filter(([a]) => a === selectedNode.id)" :key="'o' + b">
              <span class="me-arrow">{{ dir }} →</span> <a href="#" @click.prevent="select(b)">{{ nodeById[b].name }}</a> <span class="me-muted">· {{ roadLength(a, b) }} m</span>
            </li>
            <li v-for="[a, , dir] in SETTLEMENT.roads.filter(([, b]) => b === selectedNode.id)" :key="'i' + a" class="me-muted">
              <span class="me-arrow">← {{ dir }}</span> 來自 {{ nodeById[a].name }}
            </li>
          </ul>
          <h2 v-if="SETTLEMENT.references[selectedNode.id]" class="me-sec">引用</h2>
          <ul class="me-plain">
            <li v-for="r in SETTLEMENT.references[selectedNode.id] || []" :key="r.label">
              {{ r.kind }} · <a v-if="r.target" href="#" @click.prevent="r.target === 'entrance' ? select('entrance') : null">{{ r.label }}</a><span v-else>{{ r.label }}</span>
            </li>
          </ul>
          <div class="me-actions">
            <button class="me-btn" aria-keyshortcuts="Control+C" @click="copyContext">⧉ 複製 OMP 脈絡</button>
            <button class="me-btn" aria-keyshortcuts="Delete" @click="deleteShown = true">✕ 刪除 {{ selectedNode.name }}</button>
          </div>
          <div v-if="deleteShown" class="me-refuse" role="alert">
            <template v-if="deleteRefs === null">
              <b>▲ 外部索引不可用，無法確認外部引用，因此不能刪除。</b>
              <p class="me-muted">檢視、移動與編輯欄位不受影響。重新產生索引後再試。</p>
            </template>
            <template v-else-if="deleteRefs.length">
              <b>✕ 無法刪除：仍有 {{ deleteRefs.length }} 個引用</b>
              <ul>
                <li v-for="r in deleteRefs" :key="r.label">{{ r.kind }} · <a href="#" @click.prevent="r.target && r.target !== 'entrance' ? select(r.target) : select('entrance')">{{ r.label }}</a> <span class="me-mono">{{ r.source }}</span></li>
              </ul>
              <p class="me-muted">不會連帶刪除。請先移除這些引用。</p>
            </template>
            <template v-else><b>已刪除（可用 ⌘Z 復原）</b></template>
          </div>
        </template>

        <!-- entrance -->
        <template v-else-if="selectedEntrance">
          <h2 class="me-sec">檢查器 · 入口關係</h2>
          <h3 class="me-h">北門大道 ⇄ 鍛冶工坊</h3>
          <p class="me-mono me-id">擁有者：{{ ENTRANCE.owner }}（單一紀錄）</p>
          <dl class="me-dl">
            <dt>外側端點</dt><dd>{{ ENTRANCE.outer.domain }} · <a href="#" class="me-mono" @click.prevent="select('north_gate_ave')">{{ ENTRANCE.outer.ref }}</a><br><span class="me-arrow">進入 →</span> 標籤「{{ ENTRANCE.outer.label }}」</dd>
            <dt>內側端點</dt><dd>{{ ENTRANCE.inner.domain }} · <a href="#" class="me-mono" @click.prevent="followEntrance">{{ ENTRANCE.inner.ref }}</a><br><span class="me-arrow">離開 →</span> 標籤「{{ ENTRANCE.inner.label }}」</dd>
            <dt>方向</dt><dd><b>雙向</b>（兩個方向都可通行）</dd>
          </dl>
          <div class="me-actions">
            <button class="me-btn" @click="followEntrance">⇄ 前往另一端</button>
            <button class="me-btn">✎ 更換端點…</button>
          </div>
        </template>

        <!-- continent control point -->
        <template v-else-if="selectedPoint">
          <h2 class="me-sec">檢查器 · 控制點</h2>
          <h3 class="me-h">霜溪 · 控制點 {{ selectedPoint.index + 1 }}</h3>
          <p class="me-mono me-id">continent:waterway/frost_creek#{{ selectedPoint.index + 1 }}</p>
          <p class="me-mono me-id">{{ CONTINENT.path }}</p>
          <p class="me-muted">隸屬：<a href="#" @click.prevent>霜溪</a>（水系 · 9 個控制點）</p>
          <div class="me-field"><label for="me-f-ke">東向</label><span><input id="me-f-ke" class="me-inp" :value="selectedPoint.e.toFixed(1)"> <span class="me-unit">km 地理</span></span></div>
          <div class="me-field"><label for="me-f-kn">北向</label><span><input id="me-f-kn" class="me-inp" :value="selectedPoint.n.toFixed(1)"> <span class="me-unit">km 地理</span></span></div>
          <p class="me-muted">對應野外格 ({{ Math.floor(selectedPoint.e) }}, {{ Math.floor(selectedPoint.n) }}) · 1 km 格</p>
          <div class="me-actions"><button class="me-btn">◇ 前方插入</button><button class="me-btn">◇ 後方插入</button><button class="me-btn">✕ 移除控制點</button></div>
          <h2 class="me-sec">衍生結果</h2>
          <p>地形預覽：<span class="me-ok">✓ 已更新</span></p>
          <p>分區：<span class="me-warn">▲ 過期</span>（輸入 r41 · 現行 r43）</p>
          <button class="me-btn" @click="onChip('partition')">⟳ 重新產生分區</button>
        </template>

        <!-- interior room -->
        <template v-else-if="selectedRoom">
          <h2 class="me-sec">檢查器 · 房間</h2>
          <h3 class="me-h">{{ selectedRoom.name }}</h3>
          <p class="me-mono me-id">interior:{{ INTERIOR.id }} / {{ selectedRoom.id }}</p>
          <p class="me-mono me-id">{{ INTERIOR.path }}</p>
          <div class="me-field"><label for="me-f-rn">名稱</label><input id="me-f-rn" class="me-inp me-inp--text" :value="selectedRoom.name"></div>
          <div v-if="selectedRoom.scene" class="me-field"><label>場景</label><span class="me-mono">{{ selectedRoom.scene }}</span></div>
          <div v-if="selectedRoom.desc" class="me-field"><label for="me-f-rd">描述</label><textarea id="me-f-rd" class="me-inp me-inp--text" rows="4">{{ selectedRoom.desc }}</textarea></div>
          <h2 class="me-sec">連接 · 有向</h2>
          <ul class="me-plain">
            <li v-for="c in INTERIOR.connections.filter((c) => c.from === selectedRoom.id || (c.back && c.to === selectedRoom.id))" :key="c.from + c.to">
              <template v-if="c.from === selectedRoom.id"><span class="me-arrow">{{ c.dir }} →</span> {{ roomById[c.to]?.name ?? '街道圖 · 北門大道' }} <span v-if="!c.back" class="me-muted">（單向）</span></template>
              <template v-else><span class="me-arrow">{{ c.back }} →</span> {{ roomById[c.from].name }}</template>
            </li>
          </ul>
          <template v-if="selectedRoom.id === 'shopfront'">
            <h2 class="me-sec">外部入口</h2>
            <p><a href="#" @click.prevent="followEntrance">⌂ 北門大道 ⇄ 前店</a></p>
          </template>
          <h2 class="me-sec">服務</h2>
          <p class="me-muted">service_place: {{ INTERIOR.service }}（檢視用）</p>
        </template>

        <template v-else>
          <h2 class="me-sec">檢查器</h2>
          <p class="me-muted">尚未選取。在畫布或物件清單中選取物件，或在畫布上用方向鍵巡覽。</p>
        </template>
      </aside>
    </div>

    <!-- ============================ diagnostics =========================== -->
    <section class="me-foot" data-region="diag" tabindex="-1" aria-label="診斷">
      <div class="me-foot-row">
        <button class="me-diag-toggle" :aria-expanded="diagOpen" @click="diagOpen = !diagOpen">
          <span class="me-orn" aria-hidden="true" />診斷 · {{ DIAGNOSTICS.length }} {{ diagOpen ? '▾' : '▸' }}
        </button>
        <span class="me-bad">✕ 1 結構錯誤</span>
        <span class="me-warn">▲ 2 未完成</span>
        <span v-if="domain === 'interior'" class="me-muted">版面檔：{{ INTERIOR.layoutPath }}</span>
        <span v-if="copied" class="me-ok" role="status">✓ 已複製 OMP 脈絡</span>
        <span class="me-muted me-push">⌘Z 復原 · ⇧⌘Z 重做 · ⌘C 複製脈絡 · F6 切換區域</span>
      </div>
      <ul v-if="diagOpen" class="me-diag-list">
        <li v-for="d in DIAGNOSTICS" :key="d.text">
          <span :class="d.cls === 'error' ? 'me-bad' : 'me-warn'">{{ d.glyph }}</span>
          <span>{{ d.text }}</span>
          <span class="me-mono">{{ d.where }}</span>
          <button v-if="d.target" class="me-btn me-push" @click="domain = 'settlement'; select(d.target)">前往</button>
        </li>
      </ul>
    </section>
  </div>
</template>


<style scoped>
.me,
.me * { box-sizing: border-box; }
.me {
  --me-hair: rgba(185, 154, 96, 0.38);
  --me-hair-dim: rgba(143, 113, 60, 0.28);
  --me-side-w: calc(250px * var(--ui-scale));
  --me-insp-w: calc(340px * var(--ui-scale));
  position: relative;
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background: var(--panel-solid);
  color: var(--paper-100);
  font: var(--text-xs) / 1.5 var(--f-sans);
  overflow: hidden;
}
.me button { font: inherit; color: inherit; background: none; border: 0; cursor: pointer; padding: 0; }
.me :focus-visible { outline: 2px solid var(--gold-400); outline-offset: 2px; }
.me-mono { font-family: var(--f-mono); color: var(--paper-500); }
.me-muted { color: var(--paper-500); }
.me-ok { color: #a9cdb2; }
.me-warn { color: #e3c27f; }
.me-bad { color: var(--seal-400); }
.me-push { margin-left: auto; }
.me-vr { width: 1px; align-self: stretch; background: var(--me-hair-dim); }
.me-key { font: calc(13px * var(--ui-scale)) / 1.2 var(--f-mono); border: 1px solid currentColor; border-radius: 3px; padding: 0 4px; opacity: 0.8; }

/* header */
.me-head { display: flex; align-items: center; gap: var(--sp-3); padding: var(--sp-2) var(--sp-4); border-bottom: 1px solid var(--me-hair); background: linear-gradient(#1a1c20, #14161a); white-space: nowrap; flex-wrap: wrap; }
.me-seal { width: calc(32px * var(--ui-scale)); height: calc(32px * var(--ui-scale)); border-radius: 50%; border: 1px solid var(--gold-500); display: grid; place-items: center; color: var(--gold-400); }
.me-title { font: 600 var(--text-xl) var(--f-serif); color: var(--gold-300); margin: 0; letter-spacing: 0.04em; }
.me-tabs { display: flex; gap: 2px; border: 1px solid var(--me-hair-dim); border-radius: 999px; padding: 2px; }
.me-tab { padding: 1px var(--sp-4) !important; border-radius: 999px; color: var(--paper-300) !important; display: flex; gap: 6px; align-items: center; border: 1px solid transparent !important; }
.me-tab.is-on { border-color: var(--gold-400) !important; color: var(--gold-300) !important; box-shadow: inset 0 0 0 1px rgba(228, 200, 142, 0.3); }
.me-crumb { display: flex; gap: var(--sp-2); align-items: center; color: var(--paper-300); }
.me-crumb-sep { color: var(--gold-500); }
.me-chips { display: flex; gap: 6px; list-style: none; margin: 0 0 0 auto; padding: 0; }
.me-chip { padding: 0 var(--sp-3) !important; border: 1px solid var(--me-hair-dim) !important; border-radius: 999px; color: var(--paper-300) !important; white-space: nowrap; }
.me-chip.is-ok { border-color: rgba(112, 150, 122, 0.7) !important; color: #a9cdb2 !important; }
.me-chip.is-warn { border-color: var(--warn) !important; color: #e3c27f !important; }
.me-chip.is-bad { border-color: var(--seal-400) !important; color: #f1b3b3 !important; }
.me-chip.is-busy { border-color: var(--gold-400) !important; color: var(--gold-300) !important; }
.me-chip.is-off { border-style: dashed !important; color: var(--paper-500) !important; }

/* banner */
.me-banner { display: flex; gap: var(--sp-3); align-items: center; padding: 6px var(--sp-4); border-bottom: 1px solid; }
.me-banner b { font-family: var(--f-serif); }
.me-banner.is-bad { background: linear-gradient(90deg, rgba(124, 32, 38, 0.5), rgba(124, 32, 38, 0.15)); border-color: var(--seal-500); color: #f6d9d9; }
.me-banner.is-warn { background: linear-gradient(90deg, rgba(199, 154, 74, 0.22), rgba(199, 154, 74, 0.06)); border-color: var(--warn); color: #f1e1bd; }
.me-banner .me-mono { color: inherit; }

/* buttons */
.me-btn { border: 1px solid var(--me-hair) !important; border-radius: 4px; padding: 0 var(--sp-3) !important; color: var(--paper-100); white-space: nowrap; }
.me-btn:hover { border-color: var(--gold-400) !important; }
.me-btn--primary { background: var(--gold-400) !important; color: var(--ink-950) !important; border-color: var(--gold-400) !important; font-weight: 700 !important; }

/* body columns */
.me-body { flex: 1; display: flex; min-height: 0; position: relative; }
.me-side { width: var(--me-side-w); flex: none; padding: var(--sp-3) var(--sp-3); border-right: 1px solid var(--me-hair-dim); background: rgba(11, 13, 16, 0.45); overflow: auto; }
.me-insp { width: var(--me-insp-w); border-right: 0; border-left: 1px solid var(--me-hair-dim); }
.me-sec { font: 600 var(--text-xs) var(--f-serif); color: var(--gold-400); letter-spacing: 0.06em; margin: var(--sp-3) 0 6px; display: flex; gap: 6px; align-items: center; }
.me-sec:first-child { margin-top: 0; }
.me-sec::after { content: ""; flex: 1; height: 1px; background: linear-gradient(90deg, var(--me-hair), transparent); }
.me-plain { list-style: none; margin: 0; padding: 0; }
.me-plain li { margin: 2px 0; }
.me-check { display: inline-flex; gap: 6px; align-items: center; }
.me-check input { accent-color: var(--gold-400); }
.me-tree, .me-list { list-style: none; margin: 0; padding: 0; }
.me-tree li, .me-list li { padding: 1px 6px; border-radius: 3px; cursor: pointer; display: flex; gap: 4px; align-items: baseline; }
.me-tree .d1 { padding-left: calc(20px * var(--ui-scale)); }
.me-tree .d2 { padding-left: calc(36px * var(--ui-scale)); }
.me-tree-label { overflow-wrap: anywhere; }
.me-tree .is-cur, .me-list .is-cur { background: rgba(185, 154, 96, 0.16); color: var(--gold-300); box-shadow: inset 2px 0 0 var(--gold-400); }
.me-tag { font-size: var(--text-xs); color: var(--paper-500); border: 1px solid var(--me-hair-dim); border-radius: 3px; padding: 0 4px; white-space: nowrap; flex: none; }
.me-search { width: 100%; margin-bottom: 6px; background: rgba(11, 13, 16, 0.6); border: 1px solid var(--me-hair-dim); border-radius: 4px; color: var(--paper-100); font: inherit; padding: 0 var(--sp-2); }

/* canvas */
.me-canvas { flex: 1; position: relative; overflow: hidden; min-width: 0; outline: none;
  background: radial-gradient(circle, rgba(185, 154, 96, 0.2) 1px, transparent 1.4px) 0 0 / calc(24px * var(--ui-scale)) calc(24px * var(--ui-scale)), radial-gradient(ellipse at 50% 45%, var(--map-canvas-hi), var(--map-canvas-lo) 75%); }
.me-canvas:focus-visible { box-shadow: inset 0 0 0 2px var(--gold-400); }
.me-canvas--continent { background: radial-gradient(ellipse at 50% 50%, #13202b, #0a1016 80%); }
.me-canvas--interior { background: radial-gradient(ellipse at 50% 45%, #1b1d21, #0f1114 80%); }
.me-canvas.is-stale .me-svg { filter: grayscale(0.75) brightness(0.75); }
.me-svg { position: absolute; inset: 0; width: 100%; height: 100%; }
.me-road line { stroke-linecap: round; fill: none; }
.me-road-casing { stroke: #0c0b09; stroke-opacity: 0.85; stroke-width: 7; }
.me-road-core { stroke: #b9aa86; stroke-width: 2.6; }
.me-road-core.is-oneway { stroke: #7a7162; stroke-width: 1.8; stroke-dasharray: 5 6; }
.me-node { cursor: pointer; }
.me-node-dot { fill: var(--paper-100); stroke: #0c0b09; stroke-width: 1.5; }
.me-node-dot.is-unfinished { fill: none; stroke: #a6a095; stroke-dasharray: 2 2; }
.me-gate { fill: none; stroke: var(--gold-400); stroke-width: 2.4; }
.me-dash { stroke: var(--gold-400); stroke-dasharray: 3 3; }
.me-label { fill: var(--paper-100); font: 15px var(--f-sans); text-anchor: middle; paint-order: stroke; stroke: #0b0d10; stroke-width: 3px; }
.me-label.is-sel { fill: var(--paper-50); font-weight: 700; }
.me-label.is-far { fill: #a6a095; }
.me-label.is-gold { fill: var(--gold-300); text-anchor: start; }
.me-sel circle { fill: none; stroke: var(--gold-400); stroke-width: 1.6; }
.me-sel path, .me-chevrons path { fill: none; stroke: var(--gold-400); stroke-width: 1.8; }
.me-land { fill: #1d1b17; stroke: #d9c493; stroke-width: 2; }
.me-wash { fill: #4a4535; opacity: 0.55; }
.me-district { fill: none; stroke: #7d7462; stroke-width: 1.2; stroke-dasharray: 1 4; stroke-linecap: round; }
.me-ridge { fill: none; stroke: #a6a095; stroke-width: 3; }
.me-ridge-dash { fill: none; stroke: #1d1b17; stroke-dasharray: 3 5; }
.me-river-casing { fill: none; stroke: #0b0a08; stroke-width: 7; }
.me-river { fill: none; stroke: #6f9fd6; stroke-width: 3; }
.me-handle { fill: var(--panel-solid); stroke: var(--gold-400); stroke-width: 2; cursor: pointer; }
.me-handle.is-sel { fill: var(--gold-400); stroke: #0b0a08; }
.me-handle-ring { fill: none; stroke: var(--gold-400); stroke-width: 1.4; stroke-dasharray: 3 3; }
.me-loc { fill: var(--gold-300); stroke: #0b0a08; }
.me-loc-far { fill: none; stroke: #a6a095; stroke-dasharray: 2 2; }
.me-ford path { stroke: var(--gold-300); stroke-width: 2; }
.me-conn path { fill: none; stroke: #b9aa86; stroke-width: 2; }
.me-room { cursor: pointer; }
.me-room rect { fill: #191b1f; stroke: var(--me-hair); stroke-width: 1; }
.me-room.is-sel rect { stroke: var(--gold-400); stroke-width: 2; filter: drop-shadow(0 0 4px rgba(228, 200, 142, 0.35)); }
.me-room.is-ext rect { fill: #15171b; stroke-dasharray: 4 3; }
.me-room-name { fill: var(--paper-50); font: 16px var(--f-sans); text-anchor: middle; }
.me-room-id { fill: var(--paper-500); font: 14px var(--f-mono); text-anchor: middle; }
.me-arrowhead { fill: var(--gold-400); }
.me-note { position: absolute; left: var(--sp-3); bottom: var(--sp-3); margin: 0; border: 1px dashed var(--me-hair); border-radius: 6px; padding: 2px var(--sp-3); background: rgba(18, 21, 25, 0.92); color: var(--paper-300); }
.me-pill { position: absolute; display: flex; gap: 2px; align-items: center; border: 1px solid var(--me-hair); border-radius: 999px; background: rgba(18, 21, 25, 0.92); padding: 3px 4px; }
.me-tools { left: var(--sp-3); top: var(--sp-3); flex-wrap: wrap; max-width: calc(100% - 2 * var(--sp-3)); }
.me-zoom { right: var(--sp-3); bottom: var(--sp-3); }
.me-zoom-level { color: var(--gold-300); padding: 0 6px; }
.me-tool { padding: 0 var(--sp-3) !important; border-radius: 999px; color: var(--paper-300) !important; display: flex; gap: 6px; align-items: center; border: 1px solid transparent !important; }
.me-tool.is-on { color: var(--gold-300) !important; border-color: var(--gold-400) !important; }
.me-scale { position: absolute; left: var(--sp-3); bottom: var(--sp-3); border: 1px solid var(--me-hair); border-radius: 6px; background: rgba(18, 21, 25, 0.92); padding: 2px var(--sp-3); color: var(--paper-300); display: flex; gap: var(--sp-2); align-items: center; }
.me-scale i { display: inline-block; width: calc(56px * var(--ui-scale)); height: 6px; border: 1px solid var(--paper-300); border-top: 0; }
.me-north { color: var(--gold-400); }
.me-stale-badge { position: absolute; right: var(--sp-3); top: calc(56px * var(--ui-scale)); border: 1px dashed var(--warn); color: #e3c27f; padding: 0 var(--sp-3); border-radius: 4px; background: var(--panel-solid); }
.me-nopreview { position: absolute; inset: 0; display: grid; place-content: center; text-align: center; color: var(--paper-300); }
.me-nopreview-title { font: 600 var(--text-lg) var(--f-serif); color: #e3c27f; margin: 0 0 6px; }
.me-tool-panel { position: absolute; left: var(--sp-3); top: calc(64px * var(--ui-scale)); width: calc(420px * var(--ui-scale)); border: 1px solid var(--me-hair); border-radius: 8px; background: rgba(18, 21, 25, 0.96); padding: var(--sp-3) var(--sp-4); box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5); }
.me-tool-panel h3 { font: 600 var(--text-sm) var(--f-serif); color: var(--gold-300); margin: 0 0 6px; }
.me-tool-panel p { margin: 4px 0; display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.me-select { background: rgba(11, 13, 16, 0.8); color: var(--paper-50); border: 1px solid var(--me-hair); border-radius: 4px; font: inherit; }

/* inspector */
.me-h { font: 600 var(--text-lg) var(--f-serif); color: var(--gold-300); margin: 0; overflow-wrap: anywhere; }
.me-id { margin: 0; font-size: var(--text-xs); line-height: 1.35; overflow-wrap: anywhere; }
.me-field { display: grid; grid-template-columns: calc(64px * var(--ui-scale)) 1fr; gap: 4px var(--sp-2); align-items: center; margin: 6px 0; }
.me-field label { color: var(--paper-500); }
.me-inp { width: calc(110px * var(--ui-scale)); border: 0; border-bottom: 1px solid var(--me-hair); background: rgba(11, 13, 16, 0.6); color: var(--paper-50); font: var(--text-xs) var(--f-mono); padding: 0 6px; }
.me-inp--text { width: 100%; font-family: var(--f-sans); resize: vertical; }
.me-inp.is-draft { border-bottom: 2px dashed var(--gold-400); background: rgba(228, 200, 142, 0.08); }
.me-inp.is-err { border-bottom: 2px solid var(--seal-400); }
.me-unit { color: var(--gold-500); font-size: var(--text-xs); }
.me-hint { grid-column: 2; margin: 0; color: var(--gold-300); }
.me-err { grid-column: 2; margin: 0; color: #f1b3b3; }
.me kbd { font: var(--text-xs) var(--f-mono); border: 1px solid var(--me-hair); border-bottom-width: 2px; border-radius: 3px; padding: 0 4px; }
.me-arrow { color: var(--gold-400); font-family: var(--f-mono); }
.me a { color: var(--gold-400); }
.me-actions { display: flex; flex-wrap: wrap; gap: 6px; margin-top: var(--sp-3); }
.me-refuse { margin-top: var(--sp-2); border: 1px solid var(--seal-500); border-radius: 6px; padding: var(--sp-2) var(--sp-3); background: rgba(124, 32, 38, 0.15); }
.me-refuse b { color: #f6d9d9; }
.me-refuse ul { margin: 4px 0; padding-left: 18px; }
.me-refuse .me-mono { display: block; overflow-wrap: anywhere; }
.me-refuse p { margin: 4px 0 0; }
.me-dl { margin: var(--sp-2) 0; }
.me-dl dt { color: var(--paper-50); font-weight: 700; margin-top: 6px; }
.me-dl dd { margin: 0; overflow-wrap: anywhere; }
.me-insp p { margin: 4px 0; }

/* diagnostics */
.me-foot { border-top: 1px solid var(--me-hair); background: #111317; outline: none; }
.me-foot-row { display: flex; gap: var(--sp-4); align-items: center; padding: 3px var(--sp-4); white-space: nowrap; }
.me-diag-toggle { font-family: var(--f-serif) !important; color: var(--gold-400) !important; display: flex; gap: 6px; align-items: center; }
.me-orn { width: 30px; height: 11px; background: var(--band-ornament) no-repeat; }
.me-diag-list { list-style: none; margin: 0; padding: 0 var(--sp-4) var(--sp-2); max-height: calc(160px * var(--ui-scale)); overflow: auto; }
.me-diag-list li { display: flex; gap: var(--sp-3); align-items: center; padding: 2px 0; border-top: 1px solid var(--me-hair-dim); }

/* 200 % zoom / narrow: side columns become drawers */
.me--drawers .me-side { position: absolute; top: 0; bottom: 0; z-index: 3; display: none; box-shadow: 0 0 24px rgba(0, 0, 0, 0.6); background: var(--panel-solid); }
.me--drawers .me-side:not(.me-insp) { left: 0; }
.me--drawers .me-insp { right: 0; }
.me--drawers .me-side.is-open { display: block; }
.me--drawers .me-chips { margin-left: 0; flex-wrap: wrap; }
.me--drawers .me-head { white-space: normal; }
.me-drawer-toggles { display: flex; gap: 6px; }

@media (prefers-reduced-motion: reduce) {
  .me * { transition: none !important; animation: none !important; }
}
</style>
