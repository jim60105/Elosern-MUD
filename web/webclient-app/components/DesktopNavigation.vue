<script setup>
import { glyphPath } from "./dock-icons.js";

defineProps({
  mode: { type: String, default: "exploration" },
  items: { type: Array, default: () => [] },
  drawer: { type: String, default: null },
});
defineEmits(["navigate", "overlay", "home"]);
const drawerKeys = { character: "status", inventory: "inventory", bag: "inventory", quests: "quest" };
</script>

<template>
  <nav v-if="mode !== 'creation'" class="desktop-navigation" aria-label="主要導覽" @keydown.enter.stop @keydown.space.stop>
    <button type="button" :aria-current="!drawer ? 'page' : undefined" @click="$emit('home')">
      <svg viewBox="0 0 24 24" aria-hidden="true"><path :d="glyphPath(mode === 'combat' ? 'attack' : 'look')" /></svg>
      <span>{{ mode === "combat" ? "戰鬥" : "探索" }}</span>
    </button>
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
    <button type="button" @click="$emit('overlay', 'settings')">
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m9 3-1 3-3 1 1 3-2 2 2 2-1 3 3 1 1 3h6l1-3 3-1-1-3 2-2-2-2 1-3-3-1-1-3ZM12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8" /></svg>
      <span>設定</span>
    </button>
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
  width: clamp(58px, 5.3vw, 86px);
  white-space: nowrap;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 7px;
  border: 0;
  border-inline: 1px solid transparent;
  border-bottom: 2px solid transparent;
  border-radius: 0 0 6px 6px;
  background: transparent;
  color: var(--paper-500);
  font: 14px var(--f-serif);
  cursor: pointer;
}
.desktop-navigation svg {
  width: 23px;
  height: 23px;
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
</style>
