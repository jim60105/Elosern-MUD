<script setup>
// MapDrawer (OpenSpec change redesign-map-drawer; approved design
// docs/superpowers/specs/2026-10-22-world-map-drawer-design.md §6, layout
// option A). The map surface inside the shared OverlayHost (which keeps the
// modal dialog, focus trap, opener restoration and final Escape): one header
// with the 區域 / 世界 tabs (keys 1 / 2), the place caption and the close
// control, then the active tab's real view filling the body with floating
// chrome over it —
//   - top left: the commission list (a disclosure listing every accepted
//     commission of the tab as text, the keyboard path to each one);
//   - top right: the control pill  － <stop> ＋ │ ⌖ 全圖 │ ?  with the
//     legend popover under `?`;
//   - bottom left: the view's own scale bar and north mark;
//   - right: the view's ~360 px detail card, only while something is
//     selected; the pill and the edge pointers move left of it.
// Off-screen commissions get edge pointers (MapEdgePointers).
//
// Keyboard (focus anywhere in the drawer): ←↑→↓ pan, ＋／－ jump zoom stops,
// C recentres, 0 shows the whole map, 1 / 2 switch tabs. Escape closes the
// open popover, then the selection, then (in OverlayHost) the map. Keys a
// view consumes for its own focus (node arrows, the world feature list)
// never reach these handlers, and modified or composing keys pass through.
//
// Data: this component requests nothing. The host (use-map-drawer.js) sends
// `map.view` and owns the per-tab session memory passed in as `memory`; this
// component writes only that memory's view/selection fields and emits the
// adjacent 前往 descriptor with the drawn body's canonical current node.
import { computed, nextTick, ref, useId, watch } from "vue";
import AreaMapView from "./AreaMapView.vue";
import WorldMapView from "./WorldMapView.vue";
import DrawerHeader from "./DrawerHeader.vue";
import MapEdgePointers from "./MapEdgePointers.vue";
import { DETAIL_DRAWER_WIDTH, centreOn, usableRect } from "../lib/map_viewport.js";
import { placeNodes, viewSignature } from "../lib/area_map_view.js";
import { WORLD_SIGNATURE } from "../lib/world_map_view.js";
import { layoutEdgePointers } from "../lib/map_edge_pointers.js";
import {
  areaPointerTargets,
  areaQuestRows,
  worldPointerTargets,
  worldQuestRows,
} from "../lib/map_drawer_model.js";

const props = defineProps({
  // The committed `area_map` / `world_map` bodies (available or the
  // registry-owned unavailable form), or null before the first response.
  area: { type: Object, default: null },
  world: { type: Object, default: null },
  // The active scope: "area" | "world" (v-model:tab).
  tab: { type: String, default: "area" },
  // Per-tab session memory `{ area: { view, selected }, world: { view,
  // selected } }`, owned by the host and scoped to its epoch.
  memory: { type: Object, required: true },
  // The transport/puppet scope the world view's discovery re-baselines on.
  epoch: { type: [String, Number], default: null },
  // The committed location label (header caption fallback).
  locationLabel: { type: String, default: "" },
  // The host is settling a request or a move: 前往 waits.
  busy: { type: Boolean, default: false },
});
const emit = defineEmits(["update:tab", "move", "close"]);

const uid = useId();
const TABS = Object.freeze([
  Object.freeze({ key: "area", label: "區域", shortcut: "1" }),
  Object.freeze({ key: "world", label: "世界", shortcut: "2" }),
]);
const tabId = (key) => `${uid}-tab-${key}`;
const panelId = `${uid}-panel`;
const questListId = `${uid}-quests`;
const legendId = `${uid}-legend`;

const rootEl = ref(null);
const viewRef = ref(null);
const tabButtons = {};
function setTabButton(key, el) {
  if (el) tabButtons[key] = el;
  else delete tabButtons[key];
}
const questToggle = ref(null);
const questListEl = ref(null);
const legendToggle = ref(null);

// ── bodies and readings ─────────────────────────────────────────────────

const areaReady = computed(() => props.area?.available === true);
const worldReady = computed(() => props.world?.available === true);
const activeBody = computed(() => (props.tab === "world" ? props.world : props.area));
const activeReady = computed(() => (props.tab === "world" ? worldReady.value : areaReady.value));
const unavailableText = computed(() => {
  const body = activeBody.value;
  if (!body || body.available !== false) return "";
  return body.reason?.message || "地圖目前無法顯示";
});

const caption = computed(() => {
  if (props.tab === "area" && areaReady.value) {
    const district = props.area.layer === "wilderness" && props.area.district_name ? ` · ${props.area.district_name}` : "";
    return `${props.area.title}${district}`;
  }
  if (props.tab === "world" && worldReady.value) {
    const lit = props.world.districts.filter((district) => district.lit).length;
    const place = props.locationLabel ? `${props.locationLabel} · ` : "";
    return `${place}已探明 ${lit}／${props.world.districts.length} 分區`;
  }
  return props.locationLabel;
});

const questRows = computed(() => (props.tab === "world" ? worldQuestRows(props.world) : areaQuestRows(props.area)));
const trackedCount = computed(() => questRows.value.filter((row) => row.tracked).length);

// The exposed view state (refs unwrap on the component's public instance).
const viewState = computed(() => {
  const map = viewRef.value;
  if (!map || !activeReady.value) return null;
  return { view: map.view, frame: map.frame, detailShown: !!map.detailShown, stopLabel: map.stopLabel };
});
const detailOpen = computed(() => viewState.value?.detailShown === true);
const stopLabel = computed(() => viewState.value?.stopLabel ?? "");

// ── edge pointers ───────────────────────────────────────────────────────

const pointerLayout = computed(() => {
  const state = viewState.value;
  if (!state?.view || !state.frame) return { pointers: [], more: null };
  const s = readUiScale();
  const rect = usableRect(state.frame, {
    drawerOpen: state.detailShown,
    drawerWidth: DETAIL_DRAWER_WIDTH,
    marginPx: 18 * s,
    // The commission chip and the pill float over the top band, the view's
    // scale card over the bottom one.
    insets: { top: 54 * s, right: 0, bottom: 60 * s, left: 0 },
  });
  const targets =
    props.tab === "world"
      ? worldPointerTargets(props.world, state.view, state.frame)
      : areaPointerTargets(props.area, state.view, state.frame);
  return layoutEdgePointers(targets, rect, { pitch: 44 * s, halfWidth: 130 * s, halfHeight: 20 * s });
});

function readUiScale() {
  if (typeof window === "undefined" || typeof document === "undefined") return 1;
  const raw = Number.parseFloat(window.getComputedStyle(document.documentElement).getPropertyValue("--ui-scale"));
  return Number.isFinite(raw) && raw > 0 ? raw : 1;
}

// ── tabs ────────────────────────────────────────────────────────────────

function selectTab(key, { focus = false } = {}) {
  if (!TABS.some((tab) => tab.key === key)) return;
  closePopovers();
  if (key !== props.tab) emit("update:tab", key);
  // A tab switch unmounts the old panel; keep focus inside the dialog.
  if (focus) nextTick(() => tabButtons[key]?.focus());
}

function onTabKeydown(event, key) {
  if (event.altKey || event.ctrlKey || event.metaKey) return;
  const index = TABS.findIndex((tab) => tab.key === key);
  let next = null;
  if (event.key === "ArrowRight") next = TABS[(index + 1) % TABS.length].key;
  else if (event.key === "ArrowLeft") next = TABS[(index - 1 + TABS.length) % TABS.length].key;
  else if (event.key === "Home") next = TABS[0].key;
  else if (event.key === "End") next = TABS[TABS.length - 1].key;
  if (next === null) return;
  event.preventDefault();
  event.stopPropagation();
  selectTab(next, { focus: true });
}

// ── popovers ────────────────────────────────────────────────────────────

const questsOpen = ref(false);
const legendOpen = ref(false);

function closePopovers() {
  questsOpen.value = false;
  legendOpen.value = false;
}

function toggleQuests() {
  const next = !questsOpen.value;
  closePopovers();
  questsOpen.value = next;
  if (next) nextTick(() => questListEl.value?.querySelector("button")?.focus());
}

function toggleLegend() {
  const next = !legendOpen.value;
  closePopovers();
  legendOpen.value = next;
}

function onQuestListKeydown(event) {
  const buttons = [...(questListEl.value?.querySelectorAll("button") ?? [])];
  const index = buttons.indexOf(document.activeElement);
  const moves = { ArrowDown: index + 1, ArrowUp: index - 1, Home: 0, End: buttons.length - 1 };
  if (!(event.key in moves) || !buttons.length) return;
  event.preventDefault();
  event.stopPropagation();
  buttons[Math.min(buttons.length - 1, Math.max(0, moves[event.key]))].focus();
}

// A press elsewhere in the drawer closes an open popover without consuming
// the press, so a drag or a click on the map still works.
function onPointerDownCapture(event) {
  if (!questsOpen.value && !legendOpen.value) return;
  const target = event.target;
  const inside = (el) => el && el.contains(target);
  if (questsOpen.value && !inside(questListEl.value) && !inside(questToggle.value)) questsOpen.value = false;
  if (legendOpen.value && !inside(rootEl.value?.querySelector(`#${CSS.escape(legendId)}`)) && !inside(legendToggle.value)) {
    legendOpen.value = false;
  }
}

// ── commissions: select and show ────────────────────────────────────────

function centreAreaNode(nodeId) {
  const state = viewState.value;
  const entry = placeNodes(props.area).find((item) => item.node.id === nodeId);
  if (!state || !entry) return;
  const rect = usableRect(state.frame, { drawerOpen: true, drawerWidth: DETAIL_DRAWER_WIDTH });
  props.memory.area.view = Object.freeze({ signature: viewSignature(props.area), ...centreOn(state.view, state.frame, entry, rect) });
}

function showQuest(questId) {
  closePopovers();
  if (props.tab === "world") {
    // The world view pans a newly selected feature into view itself.
    props.memory.world.selected = `quest:${questId}`;
    return;
  }
  const row = areaQuestRows(props.area).find((item) => item.id === questId);
  if (!row) return;
  if (row.kind === "node" && row.nodeId) {
    props.memory.area.selected = row.nodeId;
    centreAreaNode(row.nodeId);
    return;
  }
  // A destination the area tab cannot place (elsewhere or in fog) opens on
  // the world tab, where the server states its permitted precision.
  if (worldReady.value && props.world.quest_markers.some((marker) => marker.id === questId)) {
    props.memory.world.selected = `quest:${questId}`;
  }
  selectTab("world", { focus: true });
}

function onMore() {
  closePopovers();
  questsOpen.value = true;
  nextTick(() => questListEl.value?.querySelector("button")?.focus());
}

// ── view controls ───────────────────────────────────────────────────────

function control(name, ...args) {
  const map = viewRef.value;
  if (map && activeReady.value && typeof map[name] === "function") map[name](...args);
}

const PAN_STEP_PX = 96;

function clearSelection() {
  const slot = props.tab === "world" ? props.memory.world : props.memory.area;
  if (!slot.selected) return false;
  slot.selected = null;
  return true;
}

function selectionShown() {
  return detailOpen.value;
}

// ── keyboard ────────────────────────────────────────────────────────────

function editable(target) {
  if (!target || typeof target.closest !== "function") return false;
  return !!target.closest("input, textarea, select, [contenteditable=''], [contenteditable='true']");
}

// Capture: an open popover is the topmost Escape layer.
function onKeydownCapture(event) {
  if (event.key !== "Escape" || event.isComposing || event.defaultPrevented) return;
  if (questsOpen.value) {
    questsOpen.value = false;
    event.stopPropagation();
    event.preventDefault();
    questToggle.value?.focus();
  } else if (legendOpen.value) {
    legendOpen.value = false;
    event.stopPropagation();
    event.preventDefault();
    legendToggle.value?.focus();
  }
}

// Bubble: whatever the views and controls left. Escape with a selection
// clears it here (a view clears its own when focus is inside it); every
// other Escape reaches OverlayHost, which closes the map.
function onKeydown(event) {
  if (event.isComposing || event.defaultPrevented || editable(event.target)) return;
  if (event.key === "Escape") {
    if (selectionShown() && clearSelection()) event.stopPropagation();
    return;
  }
  if (event.ctrlKey || event.metaKey || event.altKey) return;
  const pan = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }[event.key];
  let handled = true;
  if (pan) control("panBy", pan[0] * PAN_STEP_PX, pan[1] * PAN_STEP_PX);
  else if (event.key === "+" || event.key === "=" || event.key === "Add") control("zoomIn");
  else if (event.key === "-" || event.key === "_" || event.key === "Subtract") control("zoomOut");
  else if (event.key === "c" || event.key === "C") control("recentre");
  else if (event.key === "0") control("showWhole");
  else if (event.key === "1") selectTab("area", { focus: true });
  else if (event.key === "2") selectTab("world", { focus: true });
  else handled = false;
  if (handled) event.preventDefault();
}

// ── movement ────────────────────────────────────────────────────────────

function onAreaMove(payload) {
  if (props.busy) return;
  const destination = props.area?.nodes?.find((node) => node.id === payload.destination);
  emit("move", { ...payload, label: destination?.label ?? null });
}

// A new body or tab closes the popovers so they never describe another map.
watch(
  () => [props.tab, activeBody.value],
  () => closePopovers(),
);

defineExpose({ viewRef });
</script>

<template>
  <div
    ref="rootEl"
    class="map-drawer"
    :class="[`map-drawer--${tab}`, { 'map-drawer--detail': detailOpen }]"
    data-testid="map-drawer"
    :data-tab="tab"
    @keydown.capture="onKeydownCapture"
    @keydown="onKeydown"
    @pointerdown.capture="onPointerDownCapture"
  >
    <DrawerHeader
      class="map-drawer__header"
      surface="overlay-host"
      icon="map"
      title="地圖"
      :subtitle="caption"
      @close="emit('close')"
    >
      <div class="map-drawer__tabs" role="tablist" aria-label="地圖範圍" data-testid="map-drawer-tabs">
        <button
          v-for="entry in TABS"
          :id="tabId(entry.key)"
          :key="entry.key"
          :ref="(el) => setTabButton(entry.key, el)"
          type="button"
          role="tab"
          class="map-drawer__tab"
          :class="{ 'is-active': entry.key === tab }"
          :data-testid="`map-drawer-tab--${entry.key}`"
          :aria-selected="entry.key === tab ? 'true' : 'false'"
          :aria-controls="panelId"
          :aria-keyshortcuts="entry.shortcut"
          :tabindex="entry.key === tab ? 0 : -1"
          @click="selectTab(entry.key)"
          @keydown="onTabKeydown($event, entry.key)"
        >
          <span class="map-drawer__tab-label">{{ entry.label }}</span>
          <kbd class="map-drawer__kbd" aria-hidden="true">{{ entry.shortcut }}</kbd>
        </button>
      </div>
    </DrawerHeader>

    <div
      :id="panelId"
      class="map-drawer__stage"
      role="tabpanel"
      :aria-labelledby="tabId(tab)"
      data-testid="map-drawer-stage"
    >
      <AreaMapView
        v-if="tab === 'area' && areaReady"
        ref="viewRef"
        :area="area"
        :view="memory.area.view"
        :selected="memory.area.selected"
        :move-busy="busy"
        @update:view="(view) => (memory.area.view = view)"
        @update:selected="(id) => (memory.area.selected = id)"
        @move="onAreaMove"
      />
      <WorldMapView
        v-else-if="tab === 'world' && worldReady"
        ref="viewRef"
        :world="world"
        :view="memory.world.view"
        :selected="memory.world.selected"
        :epoch="epoch"
        @update:view="(view) => (memory.world.view = view)"
        @update:selected="(key) => (memory.world.selected = key)"
      />
      <div v-else class="map-drawer__state" data-testid="map-drawer-state">
        <span class="map-drawer__state-seal" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="28" height="28" fill="none">
            <path d="m3 5 6-2 6 2 6-2v16l-6 2-6-2-6 2ZM9 3v16M15 5v16" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round" />
          </svg>
        </span>
        <p v-if="unavailableText" class="map-drawer__state-text" data-testid="map-drawer-unavailable">{{ unavailableText }}</p>
        <p v-else class="map-drawer__state-text" data-testid="map-drawer-loading" aria-live="polite">正在展開地圖…</p>
      </div>

      <MapEdgePointers
        v-if="activeReady"
        :pointers="pointerLayout.pointers"
        :more="pointerLayout.more"
        @activate="showQuest"
        @more="onMore"
      />

      <!-- Top left: every accepted commission of this tab, as text. -->
      <div v-if="activeReady" class="map-drawer__quests" @pointerdown.stop>
        <button
          ref="questToggle"
          type="button"
          class="map-drawer__chip"
          data-testid="map-drawer-quests-toggle"
          :aria-expanded="questsOpen ? 'true' : 'false'"
          :aria-controls="questListId"
          :aria-label="`委託清單，共 ${questRows.length} 項`"
          @click="toggleQuests"
        >
          <span class="map-drawer__chip-glyph" aria-hidden="true">◆</span>
          <span aria-hidden="true">委託</span>
          <span class="map-drawer__chip-count" aria-hidden="true">{{ questRows.length }}</span>
          <span v-if="trackedCount" class="map-drawer__chip-tracked" aria-hidden="true">追蹤 {{ trackedCount }}</span>
          <svg class="map-drawer__chip-caret" viewBox="0 0 12 12" width="12" height="12" aria-hidden="true"><path d="M2.5 4.5 6 8l3.5-3.5" /></svg>
        </button>
        <div
          v-show="questsOpen"
          :id="questListId"
          class="map-drawer__popover map-drawer__quest-popover"
          data-testid="map-drawer-quests"
          role="group"
          aria-label="委託清單"
        >
          <p v-if="!questRows.length" class="map-drawer__empty">目前沒有已接下的委託。</p>
          <ul v-else ref="questListEl" class="map-drawer__quest-list" @keydown="onQuestListKeydown">
            <li v-for="row in questRows" :key="row.id">
              <button
                type="button"
                class="map-drawer__quest"
                :class="{ 'is-tracked': row.tracked, 'is-approx': row.approximate, 'is-fog': row.kind === 'fog' }"
                data-testid="map-drawer-quest"
                :data-quest="row.id"
                @click="showQuest(row.id)"
              >
                <span class="map-drawer__quest-glyph" aria-hidden="true">{{ row.approximate ? "◇" : "◆" }}</span>
                <span class="map-drawer__quest-title">{{ row.title }}</span>
                <span class="map-drawer__quest-sub">{{ row.tracked ? "追蹤中 · " : "" }}{{ row.sub }}</span>
              </button>
            </li>
          </ul>
        </div>
      </div>

      <!-- Top right: the control pill; it steps left of the detail card. -->
      <div
        v-if="activeReady"
        class="map-drawer__pill"
        role="group"
        aria-label="地圖檢視"
        data-testid="map-drawer-pill"
        :style="detailOpen ? { right: `calc(${DETAIL_DRAWER_WIDTH}px + 16px * var(--ui-scale))` } : null"
        @pointerdown.stop
      >
        <button type="button" class="map-drawer__pill-button map-drawer__pill-glyph" data-testid="map-drawer-zoom-out" aria-label="縮小" aria-keyshortcuts="-" title="縮小（－）" @click="control('zoomOut')">－</button>
        <span class="map-drawer__stop" data-testid="map-drawer-stop" aria-live="polite">{{ stopLabel }}</span>
        <button type="button" class="map-drawer__pill-button map-drawer__pill-glyph" data-testid="map-drawer-zoom-in" aria-label="放大" aria-keyshortcuts="+" title="放大（＋）" @click="control('zoomIn')">＋</button>
        <span class="map-drawer__pill-sep" aria-hidden="true"></span>
        <button type="button" class="map-drawer__pill-button map-drawer__pill-glyph" data-testid="map-drawer-recentre" aria-label="回到目前位置" aria-keyshortcuts="C" title="回到目前位置（C）" @click="control('recentre')">
          <svg viewBox="0 0 20 20" width="18" height="18" aria-hidden="true">
            <circle cx="10" cy="10" r="5.2" />
            <circle class="is-dot" cx="10" cy="10" r="1.6" />
            <path d="M10 1.5v3.2M10 15.3v3.2M1.5 10h3.2M15.3 10h3.2" />
          </svg>
        </button>
        <button type="button" class="map-drawer__pill-button" data-testid="map-drawer-whole" aria-keyshortcuts="0" title="顯示全圖（0）" @click="control('showWhole')">全圖</button>
        <span class="map-drawer__pill-sep" aria-hidden="true"></span>
        <button
          ref="legendToggle"
          type="button"
          class="map-drawer__pill-button map-drawer__pill-glyph"
          data-testid="map-drawer-legend-toggle"
          aria-label="圖例"
          :aria-expanded="legendOpen ? 'true' : 'false'"
          :aria-controls="legendId"
          @click="toggleLegend"
        >?</button>
        <div
          v-show="legendOpen"
          :id="legendId"
          class="map-drawer__popover map-drawer__legend"
          data-testid="map-drawer-legend"
          role="group"
          aria-label="圖例"
        >
          <ul v-if="tab === 'area'" class="map-drawer__legend-list">
            <li><i class="lg lg--here" aria-hidden="true"></i>目前位置</li>
            <li><i class="lg lg--visited" aria-hidden="true"></i>到過的地點</li>
            <li><i class="lg lg--seen" aria-hidden="true"></i>看過，尚未到訪</li>
            <li><i class="lg lg--travel" aria-hidden="true"></i>相鄰，可前往</li>
            <li><i class="lg lg--gate" aria-hidden="true"></i>城門與出入口</li>
            <li><i class="lg lg--road" aria-hidden="true"></i>走過的路</li>
            <li><i class="lg lg--frontier" aria-hidden="true"></i>看見但未走過的路</li>
            <li><i class="lg lg--quest" aria-hidden="true"></i>委託目的地</li>
          </ul>
          <ul v-else class="map-drawer__legend-list">
            <li><i class="lg lg--here" aria-hidden="true"></i>目前位置</li>
            <li><i class="lg lg--lit" aria-hidden="true"></i>已探明的分區</li>
            <li><i class="lg lg--unlit" aria-hidden="true"></i>未探明的分區</li>
            <li><i class="lg lg--nation" aria-hidden="true"></i>國界</li>
            <li><i class="lg lg--trail" aria-hidden="true"></i>走過的足跡</li>
            <li><i class="lg lg--tower" aria-hidden="true"></i>分區地標</li>
            <li><i class="lg lg--place" aria-hidden="true"></i>城鎮與地點</li>
            <li><i class="lg lg--quest" aria-hidden="true"></i>委託目的地</li>
            <li><i class="lg lg--approx" aria-hidden="true"></i>委託大致方位</li>
          </ul>
          <p class="map-drawer__legend-keys">
            <kbd>←↑→↓</kbd> 平移 <kbd>＋</kbd><kbd>－</kbd> 縮放 <kbd>C</kbd> 回到目前位置 <kbd>0</kbd> 全圖 <kbd>Esc</kbd> 返回
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.map-drawer {
  position: relative;
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  color: var(--paper-200);
  font-family: var(--f-sans);
}

/* ── header tabs ─────────────────────────────────────────────────────── */
.map-drawer__tabs {
  display: flex;
  align-items: stretch;
  gap: calc(4px * var(--ui-scale));
  margin-left: calc(6px * var(--ui-scale));
  padding: calc(3px * var(--ui-scale));
  background: rgba(0, 0, 0, 0.28);
  border: 1px solid var(--ink-700);
  border-radius: var(--radius-pill);
}
.map-drawer__tab {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: calc(8px * var(--ui-scale));
  padding: calc(4px * var(--ui-scale)) calc(16px * var(--ui-scale)) calc(4px * var(--ui-scale)) calc(18px * var(--ui-scale));
  color: var(--paper-400);
  font-family: var(--f-display);
  font-size: var(--text-md);
  letter-spacing: 0.18em;
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--radius-pill);
  cursor: pointer;
  transition: color var(--motion-fast) ease, background-color var(--motion-fast) ease, border-color var(--motion-fast) ease;
}
.map-drawer__tab:hover:not(.is-active) { color: var(--paper-100); background: rgba(255, 255, 255, 0.03); }
.map-drawer__tab.is-active {
  color: var(--gold-300);
  background: radial-gradient(120% 140% at 50% 0%, rgba(207, 179, 120, 0.22), rgba(207, 179, 120, 0.04) 70%);
  border-color: rgba(207, 179, 120, 0.5);
  box-shadow: inset 0 1px 0 rgba(255, 240, 210, 0.08), 0 0 calc(14px * var(--ui-scale)) rgba(207, 179, 120, 0.12);
}
.map-drawer__tab:focus-visible { outline: none; box-shadow: var(--focus); }
.map-drawer__kbd {
  display: inline-grid;
  place-items: center;
  min-width: calc(22px * var(--ui-scale));
  height: calc(22px * var(--ui-scale));
  padding: 0 calc(4px * var(--ui-scale));
  box-sizing: border-box;
  color: var(--paper-500);
  font-family: var(--f-mono);
  font-size: var(--text-xs);
  line-height: 1;
  letter-spacing: 0;
  border: 1px solid var(--ink-600);
  border-bottom-width: 2px;
  border-radius: calc(4px * var(--ui-scale));
}
.map-drawer__tab.is-active .map-drawer__kbd { color: var(--gold-400); border-color: var(--gold-600); }

/* ── stage ───────────────────────────────────────────────────────────── */
.map-drawer__stage {
  position: relative;
  flex: 1;
  min-height: 0;
  overflow: hidden;
  background: radial-gradient(90% 80% at 40% 30%, #1d1b17, #0e0d0b);
}

.map-drawer__state {
  position: absolute;
  inset: 0;
  display: grid;
  place-content: center;
  justify-items: center;
  gap: calc(12px * var(--ui-scale));
  color: var(--paper-400);
}
.map-drawer__state-seal {
  display: grid;
  place-items: center;
  width: calc(56px * var(--ui-scale));
  height: calc(56px * var(--ui-scale));
  color: var(--gold-500);
  border: 1px solid rgba(207, 179, 120, 0.35);
  border-radius: 50%;
  background: radial-gradient(circle at 50% 35%, #2a261e, #15161a 70%);
}
.map-drawer__state-seal svg { width: calc(28px * var(--ui-scale)); height: calc(28px * var(--ui-scale)); }
.map-drawer__state-text {
  margin: 0;
  font-family: var(--f-serif);
  font-size: var(--text-base);
  letter-spacing: 0.12em;
}

/* ── floating glass (chip, pill, popovers) ───────────────────────────── */
.map-drawer__chip,
.map-drawer__pill,
.map-drawer__popover {
  background: linear-gradient(180deg, rgba(24, 26, 31, 0.93), rgba(14, 15, 19, 0.93));
  border: 1px solid rgba(185, 154, 96, 0.38);
  box-shadow: 0 calc(8px * var(--ui-scale)) calc(24px * var(--ui-scale)) rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 240, 210, 0.06);
  backdrop-filter: blur(calc(8px * var(--ui-scale)));
  -webkit-backdrop-filter: blur(calc(8px * var(--ui-scale)));
}

.map-drawer__quests {
  position: absolute;
  top: calc(16px * var(--ui-scale));
  left: calc(16px * var(--ui-scale));
  z-index: 4;
}
.map-drawer__chip {
  display: inline-flex;
  align-items: center;
  gap: calc(8px * var(--ui-scale));
  height: calc(38px * var(--ui-scale));
  padding: 0 calc(14px * var(--ui-scale)) 0 calc(14px * var(--ui-scale));
  color: var(--paper-100);
  font-family: var(--f-display);
  font-size: var(--text-xs);
  letter-spacing: 0.14em;
  border-radius: var(--radius-pill);
  cursor: pointer;
  transition: border-color var(--motion-fast) ease;
}
.map-drawer__chip:hover,
.map-drawer__chip[aria-expanded="true"] { border-color: var(--gold-500); }
.map-drawer__chip:focus-visible { outline: none; box-shadow: var(--focus); }
.map-drawer__chip-glyph { color: var(--seal-400); }
.map-drawer__chip-count {
  min-width: calc(22px * var(--ui-scale));
  padding: 0 calc(6px * var(--ui-scale));
  color: var(--gold-300);
  font-family: var(--f-num, var(--f-sans));
  letter-spacing: 0;
  text-align: center;
  border-left: 1px solid var(--ink-700);
}
.map-drawer__chip-tracked { color: #ffd9d4; letter-spacing: 0.06em; }
.map-drawer__chip-caret { width: calc(12px * var(--ui-scale)); height: calc(12px * var(--ui-scale)); transition: transform var(--motion-fast) ease; }
.map-drawer__chip-caret path { fill: none; stroke: var(--paper-400); stroke-width: 1.6; stroke-linecap: round; stroke-linejoin: round; }
.map-drawer__chip[aria-expanded="true"] .map-drawer__chip-caret { transform: rotate(180deg); }

.map-drawer__popover {
  position: absolute;
  top: calc(100% + 8px * var(--ui-scale));
  box-sizing: border-box;
  padding: calc(10px * var(--ui-scale)) calc(10px * var(--ui-scale));
  border-radius: var(--radius);
}
.map-drawer__quest-popover {
  left: 0;
  width: calc(360px * var(--ui-scale));
  max-height: calc(60vh);
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--gold-600) transparent;
}
.map-drawer__quest-list { margin: 0; padding: 0; list-style: none; display: grid; gap: 2px; }
.map-drawer__quest {
  display: grid;
  grid-template-columns: auto 1fr;
  column-gap: calc(10px * var(--ui-scale));
  row-gap: 2px;
  width: 100%;
  padding: calc(8px * var(--ui-scale)) calc(10px * var(--ui-scale));
  color: var(--paper-100);
  font: inherit;
  font-size: var(--text-xs);
  text-align: left;
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  cursor: pointer;
}
.map-drawer__quest:hover { background: rgba(185, 154, 96, 0.1); }
.map-drawer__quest:focus-visible { outline: none; border-color: var(--gold-500); background: rgba(185, 154, 96, 0.12); }
.map-drawer__quest-glyph { grid-row: span 2; align-self: start; color: var(--seal-400); line-height: 1.35; }
.map-drawer__quest.is-tracked .map-drawer__quest-title { color: var(--paper-50); font-weight: 600; }
.map-drawer__quest-title { letter-spacing: 0.04em; overflow-wrap: anywhere; }
.map-drawer__quest-sub { grid-column: 2; color: var(--paper-500); letter-spacing: 0.02em; }
.map-drawer__quest.is-fog .map-drawer__quest-sub,
.map-drawer__quest.is-approx .map-drawer__quest-sub { font-style: italic; }
.map-drawer__empty { margin: 0; padding: calc(6px * var(--ui-scale)); color: var(--paper-500); font-size: var(--text-xs); }

.map-drawer__pill {
  position: absolute;
  top: calc(16px * var(--ui-scale));
  right: calc(16px * var(--ui-scale));
  z-index: 4;
  display: flex;
  align-items: center;
  gap: 2px;
  padding: calc(3px * var(--ui-scale)) calc(5px * var(--ui-scale));
  border-radius: var(--radius-pill);
  transition: right var(--motion-base) var(--ease-standard);
}
.map-drawer__pill-button {
  display: inline-grid;
  place-items: center;
  min-width: calc(34px * var(--ui-scale));
  height: calc(32px * var(--ui-scale));
  padding: 0 calc(10px * var(--ui-scale));
  color: var(--paper-200);
  font-family: var(--f-sans);
  font-size: var(--text-xs);
  letter-spacing: 0.1em;
  background: none;
  border: 0;
  border-radius: var(--radius-pill);
  cursor: pointer;
  transition: background-color var(--motion-fast) ease, color var(--motion-fast) ease;
}
.map-drawer__pill-glyph { padding: 0 calc(6px * var(--ui-scale)); font-size: var(--text-md); letter-spacing: 0; }
.map-drawer__pill-button:hover { color: var(--gold-300); background: rgba(185, 154, 96, 0.14); }
.map-drawer__pill-button[aria-expanded="true"] { color: var(--gold-300); background: rgba(207, 179, 120, 0.18); }
.map-drawer__pill-button:focus-visible { outline: none; box-shadow: var(--focus); }
.map-drawer__pill-button svg { width: calc(18px * var(--ui-scale)); height: calc(18px * var(--ui-scale)); }
.map-drawer__pill-button svg circle,
.map-drawer__pill-button svg path { fill: none; stroke: currentColor; stroke-width: 1.5; stroke-linecap: round; }
.map-drawer__pill-button svg .is-dot { fill: currentColor; stroke: none; }
.map-drawer__stop {
  min-width: calc(52px * var(--ui-scale));
  color: var(--gold-400);
  font-family: var(--f-display);
  font-size: var(--text-xs);
  letter-spacing: 0.16em;
  text-align: center;
  white-space: nowrap;
}
.map-drawer__pill-sep {
  width: 1px;
  height: calc(20px * var(--ui-scale));
  margin: 0 calc(4px * var(--ui-scale));
  background: linear-gradient(180deg, transparent, rgba(185, 154, 96, 0.45), transparent);
}

/* ── legend ──────────────────────────────────────────────────────────── */
.map-drawer__legend {
  right: 0;
  width: calc(300px * var(--ui-scale));
  padding: calc(14px * var(--ui-scale)) calc(16px * var(--ui-scale));
}
.map-drawer__legend-list {
  display: grid;
  gap: calc(6px * var(--ui-scale));
  margin: 0;
  padding: 0;
  list-style: none;
  color: var(--paper-200);
  font-size: var(--text-xs);
}
.map-drawer__legend-list li { display: flex; align-items: center; gap: calc(12px * var(--ui-scale)); }
.map-drawer__legend-keys {
  margin: calc(12px * var(--ui-scale)) 0 0;
  padding-top: calc(10px * var(--ui-scale));
  color: var(--paper-500);
  font-size: var(--text-xs);
  line-height: 1.9;
  border-top: 1px solid var(--ink-700);
}
.map-drawer__legend-keys kbd {
  padding: 0 calc(4px * var(--ui-scale));
  color: var(--paper-300);
  font-family: var(--f-mono);
  font-size: var(--text-xs);
  border: 1px solid var(--ink-600);
  border-radius: calc(3px * var(--ui-scale));
}
.lg {
  flex: none;
  display: inline-block;
  box-sizing: border-box;
  width: calc(22px * var(--ui-scale));
  height: calc(14px * var(--ui-scale));
}
.lg--here { width: calc(14px * var(--ui-scale)); border-radius: 50%; background: var(--seal-deep); box-shadow: 0 0 0 2px #fff2e6, 0 0 0 5px rgba(165, 44, 49, 0.3); }
.lg--visited { width: calc(12px * var(--ui-scale)); height: calc(12px * var(--ui-scale)); border-radius: 50%; background: var(--paper-200); border: 2px solid #15130f; }
.lg--seen { width: calc(12px * var(--ui-scale)); height: calc(12px * var(--ui-scale)); border-radius: 50%; background: #2b2924; border: 1.5px dashed #948b7b; }
.lg--travel { width: calc(16px * var(--ui-scale)); height: calc(16px * var(--ui-scale)); border-radius: 50%; background: rgba(228, 200, 142, 0.08); border: 1.2px dashed var(--gold-500); }
.lg--gate { width: calc(14px * var(--ui-scale)); background: #3a342a; border: 2px solid var(--gold-400); border-bottom: 0; border-radius: calc(7px * var(--ui-scale)) calc(7px * var(--ui-scale)) 0 0; }
.lg--road { height: 3px; background: #b9aa86; box-shadow: 0 0 0 2px rgba(12, 11, 9, 0.8); }
.lg--frontier { height: 0; border-top: 2px dashed #7a7162; }
.lg--quest { width: calc(12px * var(--ui-scale)); height: calc(16px * var(--ui-scale)); background: var(--seal-500); clip-path: polygon(50% 0, 100% 50%, 50% 100%, 0 50%); }
.lg--lit { background: #4a4535; border: 1px solid #d9c493; }
.lg--unlit { background: repeating-linear-gradient(45deg, rgba(138, 127, 104, 0.5) 0 1px, transparent 1px 6px), #1d1b17; border: 1px dotted #7d7462; }
.lg--nation { height: 0; border-top: 2px dashed #c0645a; }
.lg--trail { height: 3px; background: var(--gold-300); border-radius: 2px; }
.lg--tower { width: calc(10px * var(--ui-scale)); background: var(--gold-400); clip-path: polygon(20% 100%, 30% 15%, 50% 0, 70% 15%, 80% 100%); }
.lg--place { width: calc(12px * var(--ui-scale)); height: calc(12px * var(--ui-scale)); background: #e7e0d1; transform: rotate(45deg) scale(0.82); }
.lg--approx { width: calc(18px * var(--ui-scale)); height: calc(18px * var(--ui-scale)); border-radius: 50%; border: 1.5px dashed var(--seal-400); background: rgba(207, 68, 68, 0.09); }

@media (prefers-reduced-motion: reduce) {
  .map-drawer__pill { transition: none; }
}
</style>
