<script setup>
// Approved visual prototype of the main navigation
// (docs/superpowers/specs/2026-10-18-party-member-management-ui-design.md §8).
// Reference only. Three labelled entries (隊伍, 任務, 地圖) with their
// hotkeys, the icon tool group, and 設定 fixed at the end.
import { ref } from "vue";
import "./prototype.css";
import PmGlyph from "./PmGlyph.vue";

defineProps({ possessing: { type: Boolean, default: false } });

const PRIMARY = [
  { key: "party", label: "隊伍", glyph: "party", hotkey: "P" },
  { key: "quests", label: "任務", glyph: "quests", hotkey: "J" },
  { key: "map", label: "地圖", glyph: "map", hotkey: "M" },
];
// Bound, so Vite serves it from staticDirs instead of resolving an import.
const FIGURE = "/art/defaults/woman.webp";
const TOOLS = [
  { key: "letters", label: "信件", glyph: "letters" },
  { key: "lore", label: "圖鑑", glyph: "lore" },
  { key: "codex", label: "稱號冊", glyph: "codex" },
  { key: "gallery", label: "角色肖像圖庫", glyph: "gallery" },
  { key: "help", label: "說明", glyph: "help" },
];
const tip = ref(null);
</script>

<template>
  <div class="nv">
    <nav class="nv-bar" aria-label="主導覽">
      <span class="nv-brand">ELOSERN</span>
      <button v-for="p in PRIMARY" :key="p.key" type="button" class="nv-primary" :class="{ 'is-open': p.key === 'party' }">
        <PmGlyph :name="p.glyph" />{{ p.label }}<kbd>{{ p.hotkey }}</kbd>
      </button>
      <span class="nv-sep" />
      <span class="nv-tools" role="group" aria-label="工具">
        <button v-for="t in TOOLS" :key="t.key" type="button" class="nv-tool" :aria-label="t.label" @mouseenter="tip = t.key" @mouseleave="tip = null" @focus="tip = t.key" @blur="tip = null">
          <PmGlyph :name="t.glyph" />
          <span v-if="tip === t.key" class="nv-tip" aria-hidden="true">{{ t.label }}</span>
        </button>
      </span>
      <span class="nv-sep" />
      <button type="button" class="nv-tool" aria-label="設定"><PmGlyph name="settings" /></button>
    </nav>
    <div v-if="possessing" class="nv-banner">附身中 ‧ 艾拉</div>
    <div class="nv-stage">
      <img class="nv-figure" :src="FIGURE" alt="" />
      <div class="nv-lineup">
        <button type="button" class="nv-mate"><span class="pm-avatar">艾</span>艾拉</button>
        <button type="button" class="nv-mate"><span class="pm-avatar" style="filter: grayscale(0.8) brightness(0.7)">卡</span>卡恩</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.nv { position: relative; height: 100%; display: grid; grid-template-rows: auto 1fr; color: var(--paper-200); font-family: var(--f-sans); }
.nv-bar {
  grid-row: 1;
  display: flex; align-items: center; gap: var(--sp-2);
  height: calc(48px * var(--ui-scale));
  padding: 0 var(--sp-5);
  background: linear-gradient(180deg, rgba(10, 11, 13, 0.95), rgba(10, 11, 13, 0.75));
  border-bottom: 1px solid rgba(185, 154, 96, 0.28);
}
.nv-brand { margin-right: auto; color: var(--gold-400); font: var(--text-lg) var(--f-display); letter-spacing: 0.3em; }
.nv-primary {
  display: inline-flex; align-items: center; gap: var(--sp-2);
  padding: var(--sp-1) var(--sp-3);
  color: var(--paper-200);
  font: var(--text-sm) var(--f-sans);
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  cursor: pointer;
}
.nv-primary .pm-glyph { font-size: calc(18px * var(--ui-scale)); }
.nv-primary:hover { color: var(--paper-50); border-color: var(--ink-600); }
.nv-primary.is-open { color: var(--gold-300); border-color: var(--gold-600); }
.nv-primary kbd {
  padding: 0 var(--sp-1);
  color: var(--paper-500);
  font: var(--text-xs) var(--f-mono);
  border: 1px solid var(--ink-600);
  border-radius: 3px;
}
.nv-sep { width: 1px; height: calc(22px * var(--ui-scale)); margin: 0 var(--sp-1); background: rgba(185, 154, 96, 0.28); }
.nv-tools { display: inline-flex; gap: var(--sp-1); }
.nv-tool {
  position: relative;
  display: grid; place-items: center;
  width: calc(34px * var(--ui-scale)); height: calc(34px * var(--ui-scale));
  color: var(--paper-500);
  font-size: calc(18px * var(--ui-scale));
  background: transparent; border: 0; border-radius: var(--radius-sm);
  cursor: pointer;
}
.nv-tool:hover { color: var(--paper-50); }
.nv-tool:focus-visible, .nv-primary:focus-visible { outline: none; box-shadow: var(--focus); }
.nv-tip {
  position: absolute; top: calc(100% + 6px); left: 50%; transform: translateX(-50%);
  padding: 2px var(--sp-2);
  color: var(--paper-100); font-size: var(--text-xs); white-space: nowrap;
  background: var(--panel-solid); border: 1px solid rgba(185, 154, 96, 0.45); border-radius: var(--radius-sm);
  z-index: 2;
}
/* The banner overlays the stage so toggling possession never moves the scene. */
.nv-banner { position: absolute; top: calc(48px * var(--ui-scale)); left: 0; right: 0; z-index: 1; padding: var(--sp-1) var(--sp-5); color: var(--paper-50); font-size: var(--text-xs); letter-spacing: 0.1em; background: rgba(124, 32, 38, 0.85); }
.nv-stage { grid-row: 2; position: relative; background: linear-gradient(rgba(5, 6, 8, 0.55), rgba(5, 6, 8, 0.8)), url(/art/showcase/sample-guild.webp) center / cover; overflow: hidden; }
.nv-figure { position: absolute; left: 8%; bottom: 0; height: 88%; opacity: 0.85; }
.nv-lineup { position: absolute; right: var(--sp-8); bottom: var(--sp-8); display: flex; gap: var(--sp-3); }
.nv-mate { display: grid; justify-items: center; gap: 2px; color: var(--paper-300); font-size: var(--text-xs); background: transparent; border: 0; cursor: pointer; }
</style>
