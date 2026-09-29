<script setup>
// DesktopNavigation: the top bar's navigation row (webclient-desktop-shell;
// webclient-avg-place-card-top-bar design D1/D2). One labelled control per
// navigation-presented entry plus the map and settings controls, followed by
// the icon-only tool group (`工具`: 技能系譜, 圖鑑, 稱號冊, 角色肖像圖庫 when
// available, and 說明; webclient-collapsible-command-line design D6), inside
// the 48px band. There is no home entry:
// the stage itself is the screen the player is on, and Escape and the
// dock's back controls return the dock to its root.
import { glyphAttrs, glyphPath } from "./dock-icons.js";

defineProps({
  mode: { type: String, default: "exploration" },
  items: { type: Array, default: () => [] },
  drawer: { type: String, default: null },
  galleryAvailable: { type: Boolean, default: false },
});
defineEmits(["navigate", "overlay", "drawer"]);
// The 工具 group in order. Each tool's glyph key is also the key of the
// surface it opens, so the opened surface's DrawerHeader draws the same
// registry glyph (webclient-drawer-frame-unification). 圖鑑 opens the lore
// drawer; the rest open overlays.
const TOOLS = [
  { key: "lineage", label: "技能系譜", testid: "nav-tool-lineage" },
  { key: "lore", label: "圖鑑", testid: "nav-tool-lore", drawer: "lore" },
  { key: "codex", label: "稱號冊", testid: "nav-tool-codex" },
  { key: "gallery", label: "角色肖像圖庫", testid: "gallery-opener" },
  { key: "help", label: "說明", testid: "nav-tool-help" },
];
const drawerKeys = { character: "status", inventory: "inventory", bag: "inventory", quests: "quest" };
</script>

<template>
  <nav v-if="mode !== 'creation'" class="desktop-navigation" aria-label="主要導覽" @keydown.enter.stop @keydown.space.stop>
    <button
      v-for="item in items"
      :key="item.key"
      type="button"
      :disabled="!item.enabled"
      :title="item.disabled_reason?.message"
      :aria-current="drawer === drawerKeys[item.key] ? 'page' : undefined"
      @click="$emit('navigate', item.key)"
    >
      <svg viewBox="0 0 24 24" aria-hidden="true"><path :d="glyphPath(item.key === 'bag' ? 'inventory' : item.key)" /></svg>
      <span>{{ item.label }}</span>
    </button>
    <button v-if="mode !== 'combat'" type="button" @click="$emit('overlay', 'map')">
      <svg viewBox="0 0 24 24" aria-hidden="true"><path :d="glyphPath('map')" /></svg>
      <span>地圖</span>
    </button>
    <button type="button" data-testid="nav-settings" @click="$emit('overlay', 'settings')">
      <svg viewBox="0 0 24 24" aria-hidden="true"><path :d="glyphPath('settings')" /></svg>
      <span>設定</span>
    </button>
    <div class="desktop-navigation__tools" role="group" aria-label="工具" data-testid="nav-tools">
      <template v-for="tool in TOOLS" :key="tool.key">
        <button
          v-if="tool.key !== 'gallery' || galleryAvailable"
          type="button"
          :aria-label="tool.label"
          :title="tool.label"
          :data-testid="tool.testid"
          @click="$emit(tool.drawer ? 'drawer' : 'overlay', tool.drawer || tool.key)"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true"><path :d="glyphPath(tool.key)" v-bind="glyphAttrs(tool.key)" /></svg>
        </button>
      </template>
    </div>
  </nav>
</template>

<style>
.desktop-navigation {
  position: absolute;
  left: var(--left-column);
  top: 0;
  height: var(--header-h);
  display: flex;
  align-items: stretch;
  z-index: 8;
}
.desktop-navigation button {
  white-space: nowrap;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  gap: 7px;
  padding: 0 14px;
  border: 0;
  border-inline: 1px solid transparent;
  border-bottom: 2px solid transparent;
  border-radius: 0 0 6px 6px;
  background: transparent;
  color: var(--paper-500);
  font: var(--text-md) var(--f-serif);
  letter-spacing: .08em;
  cursor: pointer;
}
.desktop-navigation svg {
  width: 18px;
  height: 18px;
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
  box-shadow: 0 9px 18px -15px var(--gold-400);
}
.desktop-navigation button:focus-visible { outline: 2px solid var(--gold-400); outline-offset: -4px; }
.desktop-navigation button:disabled { opacity: .45; cursor: not-allowed; }
.desktop-navigation__tools {
  display: flex;
  align-items: stretch;
  margin-left: 4px;
  padding-left: 4px;
  border-left: var(--line);
}
.desktop-navigation__tools button {
  width: 38px;
  padding: 0;
}
</style>
