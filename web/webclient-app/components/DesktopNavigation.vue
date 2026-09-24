<script setup>
// DesktopNavigation: the top bar's navigation row (webclient-desktop-shell;
// webclient-avg-place-card-top-bar design D1/D2). One labelled control per
// navigation-presented entry plus the map and settings controls, followed by
// the icon-only tool group (`工具`: 技能系譜, 圖鑑, 稱號冊, 角色肖像圖庫 when
// available, and 說明; webclient-collapsible-command-line design D6), inside
// the 48px band. There is no home entry:
// the stage itself is the screen the player is on, and Escape and the
// dock's back controls return the dock to its root.
import { glyphPath } from "./dock-icons.js";

defineProps({
  mode: { type: String, default: "exploration" },
  items: { type: Array, default: () => [] },
  drawer: { type: String, default: null },
  galleryAvailable: { type: Boolean, default: false },
});
defineEmits(["navigate", "overlay", "drawer"]);
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
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m3 5 6-2 6 2 6-2v16l-6 2-6-2-6 2ZM9 3v16M15 5v16" /></svg>
      <span>地圖</span>
    </button>
    <button type="button" data-testid="nav-settings" @click="$emit('overlay', 'settings')">
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m9 3-1 3-3 1 1 3-2 2 2 2-1 3 3 1 1 3h6l1-3 3-1-1-3 2-2-2-2 1-3-3-1-1-3ZM12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8" /></svg>
      <span>設定</span>
    </button>
    <div class="desktop-navigation__tools" role="group" aria-label="工具" data-testid="nav-tools">
      <button
        type="button"
        aria-label="技能系譜"
        title="技能系譜"
        data-testid="nav-tool-lineage"
        @click="$emit('overlay', 'lineage')"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="12" cy="5" r="2.2" />
          <circle cx="5.5" cy="18.5" r="2.2" />
          <circle cx="18.5" cy="18.5" r="2.2" />
          <path d="M12 7.2v4.3M12 11.5 6.6 16.6M12 11.5l5.4 5.1" stroke-linecap="round" />
        </svg>
      </button>
      <button
        type="button"
        aria-label="圖鑑"
        title="圖鑑"
        data-testid="nav-tool-lore"
        @click="$emit('drawer', 'lore')"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="12" cy="12" r="8.5" />
          <ellipse cx="12" cy="12" rx="3.8" ry="8.5" />
          <path d="M3.5 12h17" stroke-linecap="round" />
        </svg>
      </button>
      <button
        type="button"
        aria-label="稱號冊"
        title="稱號冊"
        data-testid="nav-tool-codex"
        @click="$emit('overlay', 'codex')"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M5 4h11a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3z" stroke-linecap="round" stroke-linejoin="round" />
          <path d="M5 17h14" stroke-linecap="round" />
          <path d="m12 7 .9 1.9 2.1.3-1.5 1.5.4 2-1.9-1-1.9 1 .4-2L9 9.2l2.1-.3z" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
      </button>
      <button
        v-if="galleryAvailable"
        type="button"
        aria-label="角色肖像圖庫"
        title="角色肖像圖庫"
        data-testid="gallery-opener"
        @click="$emit('overlay', 'gallery')"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
          <circle cx="8.5" cy="8.5" r="1.5" />
          <polyline points="21 15 16 10 5 21" />
        </svg>
      </button>
      <button
        type="button"
        aria-label="說明"
        title="說明"
        data-testid="nav-tool-help"
        @click="$emit('overlay', 'help')"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="12" cy="12" r="10" />
          <path d="M9.5 9a2.5 2.5 0 1 1 3.7 2.2c-.7.4-.7 1.3-.7 2.3M12 16h.01" stroke-linecap="round" />
        </svg>
      </button>
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
  font: 14px var(--f-serif);
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
