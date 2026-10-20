<script setup>
// DesktopNavigation: the top bar's navigation row (webclient-desktop-shell;
// webclient-main-navigation-hotkeys, design §8 of the party member
// management design). The labelled primary entries 隊伍, 任務 and 地圖 (each
// with its window hotkey drawn as a key chip), then the icon-only tool group
// (`工具`: 信件, 圖鑑, 稱號冊, 角色肖像圖庫 when available, and 說明), then 設定
// at the very end, inside the 48px band. There is no home entry: the stage
// itself is the screen the player is on, and Escape and the dock's back
// controls return the dock to its root.
//
// Stable placement (webclient-chrome-navigation-polish): the labelled
// entries live in a fixed-width primary region sized for all three and
// packed against its trailing edge, so the tool group and 設定 never move
// when a mode or an unavailable panel drops an entry; the space a missing
// entry leaves collects on the brand side. A missing entry is simply not
// rendered — never a disabled or hidden stand-in. The bar takes no
// possession input: it renders identically while possessing.
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { glyphAttrs, glyphPath } from "./dock-icons.js";
import { NAV_SETTINGS, NAV_TOOLS } from "./nav-tools.js";
import { primaryEntries } from "./nav-primary.js";

const props = defineProps({
  mode: { type: String, default: "exploration" },
  // The server's navigation rows; the bar reads the `quests` row from them.
  items: { type: Array, default: () => [] },
  // The open drawer name: 隊伍 is current while the party window is open,
  // 任務 while the quest board is.
  drawer: { type: String, default: null },
  // The committed `party` panel's availability: 隊伍 renders only with it.
  partyAvailable: { type: Boolean, default: false },
  galleryAvailable: { type: Boolean, default: false },
});
const emit = defineEmits(["navigate", "overlay", "drawer"]);
const CURRENT_DRAWER = { party: "party", quests: "quest" };
const entries = computed(() => primaryEntries({ mode: props.mode, partyAvailable: props.partyAvailable, items: props.items }));

function activatePrimary(entry) {
  if (entry.key === "map") emit("overlay", "map");
  else emit("navigate", entry.key);
}

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
const visibleTools = computed(() => NAV_TOOLS.filter((tool) => tool.key !== "gallery" || props.galleryAvailable));
const renderedTools = computed(() =>
  props.mode === "creation" ? [] : [...visibleTools.value.map((tool) => tool.key), NAV_SETTINGS.key],
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
function activateSettings() {
  hoverKey.value = null;
  focusKey.value = null;
  emit("overlay", NAV_SETTINGS.key);
}
</script>

<template>
  <nav v-if="props.mode !== 'creation'" class="desktop-navigation" aria-label="主要導覽" @keydown.enter.stop @keydown.space.stop>
    <div class="desktop-navigation__primary" data-testid="nav-primary">
      <button
        v-for="entry in entries"
        :key="entry.key"
        type="button"
        :style="{ '--nav-glyphs': entry.glyphs }"
        :data-nav-slot="entry.key"
        :disabled="!entry.enabled"
        :title="entry.reason ?? undefined"
        :aria-current="CURRENT_DRAWER[entry.key] && props.drawer === CURRENT_DRAWER[entry.key] ? 'page' : undefined"
        :aria-keyshortcuts="entry.hotkey"
        @click="activatePrimary(entry)"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true"><path :d="glyphPath(entry.glyph)" v-bind="glyphAttrs(entry.glyph)" /></svg>
        <span class="desktop-navigation__label">{{ entry.label }}</span>
        <kbd class="desktop-navigation__key" aria-hidden="true">{{ entry.hotkey }}</kbd>
      </button>
    </div>
    <span class="desktop-navigation__sep" aria-hidden="true"></span>
    <div class="desktop-navigation__tools" role="group" aria-label="工具" data-testid="nav-tools">
      <span
        v-for="tool in visibleTools"
        :key="tool.key"
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
    </div>
    <span class="desktop-navigation__sep" aria-hidden="true"></span>
    <span
      class="desktop-navigation__tool desktop-navigation__settings"
      @mouseenter="onToolEnter(NAV_SETTINGS.key)"
      @mouseleave="onToolLeave(NAV_SETTINGS.key)"
    >
      <button
        type="button"
        :aria-label="NAV_SETTINGS.label"
        :data-testid="NAV_SETTINGS.testid"
        data-nav-slot="settings"
        @focus="onToolFocus($event, NAV_SETTINGS.key)"
        @blur="onToolBlur(NAV_SETTINGS.key)"
        @keydown="onToolKeydown($event, NAV_SETTINGS.key)"
        @click="activateSettings"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true"><path :d="glyphPath('settings')" v-bind="glyphAttrs('settings')" /></svg>
      </button>
      <span
        v-if="tipKey === NAV_SETTINGS.key"
        class="desktop-navigation__tooltip"
        data-testid="nav-tooltip"
        aria-hidden="true"
      >{{ NAV_SETTINGS.label }}</span>
    </span>
  </nav>
</template>

<style>
.desktop-navigation {
  --nav-pad: calc(14px * var(--ui-scale));
  /* The key chip's fixed box, so every control's width stays a function of
     its label's glyph count alone. */
  --nav-key: calc(18px * var(--ui-scale));
  --nav-chrome: calc(2 * var(--nav-pad) + 34px * var(--ui-scale) + var(--nav-key));
  position: absolute;
  left: var(--left-column);
  top: 0;
  height: var(--header-h);
  display: flex;
  align-items: stretch;
  z-index: 8;
  font: var(--text-md) var(--f-serif);
}
/* The primary region is as wide as the three labelled entries together
   (three two-glyph labels): six glyphs of 1em plus their .08em tracking,
   and three times the fixed chrome of a control (padding, the 1px side
   borders, the 18px glyph, the key chip and their two 7px gaps). Controls
   pack against the trailing edge, so a missing entry frees space on the
   brand side and never moves the tool group or 設定. */
.desktop-navigation__primary {
  flex: none;
  display: flex;
  justify-content: flex-end;
  align-items: stretch;
  width: calc(6 * 1.08em + 3 * var(--nav-chrome));
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
  transition: color var(--motion-fast) var(--ease-standard), background-color var(--motion-fast) var(--ease-standard);
}
.desktop-navigation__primary button {
  /* Each entry binds its own glyph count; two is every shipped label's. */
  --nav-glyphs: 2;
  flex: none;
  box-sizing: border-box;
  width: calc(var(--nav-glyphs) * 1.08em + var(--nav-chrome));
  overflow: hidden;
  color: var(--paper-300);
}
.desktop-navigation__label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}
/* The window hotkey, drawn as a small engraved key cap after the label
   (the approved prototype's chip). Decorative: the control carries it as
   `aria-keyshortcuts`. */
.desktop-navigation__key {
  flex: none;
  box-sizing: border-box;
  width: var(--nav-key);
  height: var(--nav-key);
  display: grid;
  place-items: center;
  border: 1px solid var(--ink-600);
  border-bottom-width: 2px;
  border-radius: calc(3px * var(--ui-scale));
  background: #0a0b0d8c;
  color: var(--paper-500);
  font: var(--text-xs)/1 var(--f-mono);
  letter-spacing: 0;
  transition: inherit;
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
.desktop-navigation button:hover .desktop-navigation__key,
.desktop-navigation button[aria-current="page"] .desktop-navigation__key {
  border-color: var(--gold-600);
  color: var(--gold-300);
}
.desktop-navigation button:focus-visible { outline: 2px solid var(--gold-400); outline-offset: calc(-4px * var(--ui-scale)); }
.desktop-navigation button:disabled { opacity: .45; cursor: not-allowed; }
/* A thin gold hairline between the entries, the tools and 設定, the
   prototype's separators: they divide without boxing the bar in. */
.desktop-navigation__sep {
  flex: none;
  align-self: center;
  width: 1px;
  height: calc(22px * var(--ui-scale));
  margin: 0 calc(6px * var(--ui-scale));
  background: linear-gradient(180deg, transparent, #b99a6080 25%, #b99a6080 75%, transparent);
}
.desktop-navigation__tools {
  display: flex;
  align-items: stretch;
}
.desktop-navigation__tool {
  position: relative;
  display: flex;
}
.desktop-navigation__tool button {
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
