<script setup>
// DesktopNavigation: the top bar's navigation row (webclient-desktop-shell;
// webclient-avg-place-card-top-bar design D1/D2). One labelled control per
// navigation-presented entry plus the map and settings controls, followed by
// the icon-only tool group (`工具`: 技能系譜, 圖鑑, 稱號冊, 角色肖像圖庫 when
// available, and 說明; webclient-collapsible-command-line design D6), inside
// the 48px band. There is no home entry:
// the stage itself is the screen the player is on, and Escape and the
// dock's back controls return the dock to its root.
//
// Stable placement (webclient-chrome-navigation-polish): the labelled
// controls live in a fixed-width primary region sized for the full set of
// five primary concepts and packed against its trailing edge, so 設定 and the
// tool group never move when a mode or an unavailable panel drops an entry;
// the space a missing entry leaves collects on the brand side. A missing
// entry is simply not rendered — never a disabled or hidden stand-in.
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { glyphAttrs, glyphPath } from "./dock-icons.js";
import { NAV_TOOLS } from "./nav-tools.js";

const props = defineProps({
  mode: { type: String, default: "exploration" },
  items: { type: Array, default: () => [] },
  drawer: { type: String, default: null },
  galleryAvailable: { type: Boolean, default: false },
});
const emit = defineEmits(["navigate", "overlay", "drawer"]);
const drawerKeys = { character: "status", inventory: "inventory", bag: "inventory", quests: "quest" };
// The glyph count of each primary concept's label sizes its control, so the
// region's width is the same whichever entries the mode supplies.
const GLYPHS = { character: 4, quests: 2, inventory: 2, bag: 2, map: 2, settings: 2 };

// The one visible tooltip of the tool group. Pointer and keyboard are two
// independent sources: `hoverKey` is the tool the pointer rests on (the
// control or its tooltip), `focusKey` the tool keyboard focus reached by Tab.
// Each is cleared by its own end (mouseleave, blur), by Escape, or by
// activation. The tooltip only duplicates the control's accessible name, so
// it is hidden from assistive technology.
const hoverKey = ref(null);
const focusKey = ref(null);
const tipKey = computed(() => hoverKey.value ?? focusKey.value);
// Focus shows the tooltip only when Tab moved it there: focus restored to
// the opener by a closing overlay (after Escape or a click), or regained
// with the window, stays quiet, so the player never needs a second Escape
// that would reach the dock.
let tabbed = false;

function onDocumentKeydown(event) {
  tabbed = event.key === "Tab";
  // A pointer-shown tooltip yields to any Escape without claiming it: the
  // key still closes an open overlay or pops the dock.
  if (event.key === "Escape") hoverKey.value = null;
}
function resetTabbed() {
  tabbed = false;
}
onMounted(() => {
  document.addEventListener("keydown", onDocumentKeydown, true);
  document.addEventListener("pointerdown", resetTabbed, true);
  window.addEventListener("blur", resetTabbed);
});
onBeforeUnmount(() => {
  document.removeEventListener("keydown", onDocumentKeydown, true);
  document.removeEventListener("pointerdown", resetTabbed, true);
  window.removeEventListener("blur", resetTabbed);
});

// A tool that stops rendering (the gallery going unavailable, the whole bar
// leaving in creation) fires no mouseleave or blur, so its tooltip state is
// dropped here; it never reappears without a new hover or Tab.
const renderedTools = computed(() =>
  props.mode === "creation" ? [] : NAV_TOOLS.filter((tool) => tool.key !== "gallery" || props.galleryAvailable).map((tool) => tool.key),
);
watch(renderedTools, (keys) => {
  if (!keys.includes(hoverKey.value)) hoverKey.value = null;
  if (!keys.includes(focusKey.value)) focusKey.value = null;
});

function onToolEnter(key) {
  hoverKey.value = key;
}
function onToolLeave(key) {
  if (hoverKey.value === key) hoverKey.value = null;
}
function onToolFocus(event, key) {
  if (tabbed && focusVisible(event.target)) focusKey.value = key;
}
function focusVisible(el) {
  try {
    return el.matches(":focus-visible");
  } catch {
    return true;
  }
}
function onToolBlur(key) {
  if (focusKey.value === key) focusKey.value = null;
}
// Escape on the focused control dismisses its own tooltip and is consumed
// there; with no tooltip of its own showing it falls through to the dock.
function onToolKeydown(event, key) {
  if (event.key === "Escape" && focusKey.value === key) {
    event.preventDefault();
    event.stopPropagation();
    focusKey.value = null;
  }
}
function activateTool(tool) {
  hoverKey.value = null;
  focusKey.value = null;
  if (tool.drawer) emit("drawer", tool.drawer);
  else emit("overlay", tool.key);
}
</script>

<template>
  <nav v-if="props.mode !== 'creation'" class="desktop-navigation" aria-label="主要導覽" @keydown.enter.stop @keydown.space.stop>
    <div class="desktop-navigation__primary" data-testid="nav-primary">
      <button
        v-for="item in props.items"
        :key="item.key"
        type="button"
        :style="{ '--nav-glyphs': GLYPHS[item.key] ?? 2 }"
        :data-nav-slot="item.key === 'bag' ? 'inventory' : item.key"
        :disabled="!item.enabled"
        :title="item.disabled_reason?.message"
        :aria-current="props.drawer === drawerKeys[item.key] ? 'page' : undefined"
        @click="emit('navigate', item.key)"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true"><path :d="glyphPath(item.key === 'bag' ? 'inventory' : item.key)" /></svg>
        <span>{{ item.label }}</span>
      </button>
      <button v-if="props.mode !== 'combat'" type="button" data-nav-slot="map" style="--nav-glyphs: 2" @click="emit('overlay', 'map')">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path :d="glyphPath('map')" /></svg>
        <span>地圖</span>
      </button>
      <button type="button" data-testid="nav-settings" data-nav-slot="settings" style="--nav-glyphs: 2" @click="emit('overlay', 'settings')">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path :d="glyphPath('settings')" /></svg>
        <span>設定</span>
      </button>
    </div>
    <div class="desktop-navigation__tools" role="group" aria-label="工具" data-testid="nav-tools">
      <template v-for="tool in NAV_TOOLS" :key="tool.key">
        <span
          v-if="tool.key !== 'gallery' || props.galleryAvailable"
          class="desktop-navigation__tool"
          @mouseenter="onToolEnter(tool.key)"
          @mouseleave="onToolLeave(tool.key)"
        >
          <button
            type="button"
            :aria-label="tool.label"
            :data-testid="tool.testid"
            @focus="onToolFocus($event, tool.key)"
            @blur="onToolBlur(tool.key)"
            @keydown="onToolKeydown($event, tool.key)"
            @click="activateTool(tool)"
          >
            <svg viewBox="0 0 24 24" aria-hidden="true"><path :d="glyphPath(tool.key)" v-bind="glyphAttrs(tool.key)" /></svg>
          </button>
          <span
            v-if="tipKey === tool.key"
            class="desktop-navigation__tooltip"
            data-testid="nav-tooltip"
            aria-hidden="true"
          >{{ tool.label }}</span>
        </span>
      </template>
    </div>
  </nav>
</template>

<style>
.desktop-navigation {
  --nav-pad: calc(14px * var(--ui-scale));
  position: absolute;
  left: var(--left-column);
  top: 0;
  height: var(--header-h);
  display: flex;
  align-items: stretch;
  z-index: 8;
  font: var(--text-md) var(--f-serif);
}
/* The primary region is as wide as the five primary controls together (one
   four-glyph label, four two-glyph labels): twelve glyphs of 1em plus their
   .08em tracking, and five times the fixed chrome of a control (padding,
   the 1px side borders, the 18px glyph and its 7px gap). Controls pack
   against the trailing edge, so a missing entry frees space on the brand
   side and never moves 設定 or the tool group. */
.desktop-navigation__primary {
  flex: none;
  display: flex;
  justify-content: flex-end;
  align-items: stretch;
  width: calc(12 * 1.08em + 5 * (2 * var(--nav-pad) + calc(27px * var(--ui-scale))));
}
.desktop-navigation button {
  white-space: nowrap;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  gap: calc(7px * var(--ui-scale));
  padding: 0 var(--nav-pad);
  border: 0;
  border-inline: 1px solid transparent;
  border-bottom: 2px solid transparent;
  border-radius: 0 0 var(--radius) var(--radius);
  background: transparent;
  color: var(--paper-500);
  font: inherit;
  letter-spacing: .08em;
  cursor: pointer;
}
.desktop-navigation__primary button {
  flex: none;
  box-sizing: border-box;
  width: calc(var(--nav-glyphs) * 1.08em + 2 * var(--nav-pad) + 27px * var(--ui-scale));
  overflow: hidden;
}
.desktop-navigation__primary button span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}
.desktop-navigation svg {
  width: calc(18px * var(--ui-scale));
  height: calc(18px * var(--ui-scale));
  flex: none;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.6;
}
.desktop-navigation button:hover,
.desktop-navigation button[aria-current="page"] {
  color: var(--gold-400);
  border-inline-color: #cbb78524;
  border-bottom-color: var(--gold-400);
  background: linear-gradient(0deg, #d8bb7833, transparent 75%);
  box-shadow: 0 calc(9px * var(--ui-scale)) calc(18px * var(--ui-scale)) calc(-15px * var(--ui-scale)) var(--gold-400);
}
.desktop-navigation button:focus-visible { outline: 2px solid var(--gold-400); outline-offset: calc(-4px * var(--ui-scale)); }
.desktop-navigation button:disabled { opacity: .45; cursor: not-allowed; }
.desktop-navigation__tools {
  display: flex;
  align-items: stretch;
  margin-left: calc(4px * var(--ui-scale));
  padding-left: calc(4px * var(--ui-scale));
  border-left: var(--line);
}
.desktop-navigation__tool {
  position: relative;
  display: flex;
}
.desktop-navigation__tools button {
  width: calc(38px * var(--ui-scale));
  padding: 0;
}
/* The shared tool tooltip: a small ink plate hung under the control from a
   gold tick, the label in the chrome serif. It sits flush against the
   control (no gap), so the pointer can travel onto it without it closing. */
.desktop-navigation__tooltip {
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  padding: calc(7px * var(--ui-scale)) calc(11px * var(--ui-scale)) calc(6px * var(--ui-scale));
  border: 1px solid #bda47759;
  border-radius: var(--radius-sm);
  background: var(--surface-panel, #121418);
  box-shadow: 0 calc(8px * var(--ui-scale)) calc(22px * var(--ui-scale)) #000b;
  color: var(--paper-100);
  font: var(--text-sm)/1.2 var(--f-serif);
  letter-spacing: .08em;
  white-space: nowrap;
  animation: desktop-navigation-tip var(--motion-fast) var(--ease-standard);
}
.desktop-navigation__tooltip::before {
  content: "";
  position: absolute;
  top: -1px;
  left: 50%;
  width: calc(14px * var(--ui-scale));
  height: 1px;
  transform: translateX(-50%);
  background: var(--gold-400);
}
@keyframes desktop-navigation-tip {
  from { opacity: 0; }
}
@media (max-width: 1350px) {
  /* Compact padding keeps the region clear of the character switcher. */
  .desktop-navigation { --nav-pad: calc(10px * var(--ui-scale)); }
}
</style>
