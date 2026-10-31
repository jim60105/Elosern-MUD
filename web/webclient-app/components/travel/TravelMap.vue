<script setup>
// TravelMap (OpenSpec change wilderness-travel-interface): the travel stage's
// full-bleed map in the HudFrame `backdrop` slot. Until wilderness-travel-
// map-ui replaces its drawing surface it wraps the real `AreaMapView` over the
// area body the refresh owner (composables/use-travel-map.js) last adopted:
// pan and zoom work, and it sends nothing itself.
//
// It shows the owner's status truthfully and derives none of it:
//   - `ready`: the adopted current map at full strength;
//   - `refreshing`: the last adopted map dimmed while the next one settles, or
//     the hatched fog on a first load with no map yet;
//   - `retired`: the neutral first-load fog (the new session's own snapshot
//     re-arms the owner);
//   - `unavailable` / `invalid`: the last map (or the fog) dimmed, with one
//     status line and a 重新整理 control that asks the owner for one more
//     read. That control is the player's own input, never a timer.
// Each adopted body remounts the view keyed by its current node, so the
// opening fit always frames the party's own cell.
import { computed } from "vue";
import AreaMapView from "../AreaMapView.vue";
import WorldHatchPattern from "../WorldHatchPattern.vue";

const props = defineProps({
  // The adopted area_map body, or null before the first adoption.
  area: { type: Object, default: null },
  // ready | refreshing | unavailable | invalid | retired
  status: { type: String, default: "refreshing" },
});
const emit = defineEmits(["retry"]);

const failed = computed(() => props.status === "unavailable" || props.status === "invalid");
const showMap = computed(() => !!props.area && props.status !== "retired");
const stateText = computed(() =>
  props.status === "invalid" ? "無法讀取這一帶的地圖。" : "這一帶的地圖暫時無法更新。",
);
const label = computed(() => {
  if (!showMap.value) return "旅行地圖：正在展開這一帶的地圖";
  if (props.status === "ready") return `旅行地圖：${props.area.title}`;
  return `旅行地圖：${props.area.title}（尚未更新）`;
});
const viewKey = computed(() => (props.area ? `${props.area.map_id}|${props.area.current_node}` : "none"));
</script>

<template>
  <section
    class="travel-map"
    data-testid="travel-map"
    :data-map-status="status"
    :data-map-shown="showMap ? 'true' : 'false'"
    :aria-label="label"
  >
    <svg class="travel-map__fog" aria-hidden="true" focusable="false">
      <defs><WorldHatchPattern id="travel-map-fog" /></defs>
      <rect width="100%" height="100%" fill="url(#travel-map-fog)" />
    </svg>
    <div v-if="showMap" class="travel-map__view" data-testid="travel-map__view">
      <AreaMapView :key="viewKey" :area="area" :show-detail="false" />
    </div>
    <div v-if="failed" class="travel-map__state" role="status" data-testid="travel-map__state">
      <span class="travel-map__state-text">{{ stateText }}</span>
      <button
        type="button"
        class="travel-map__retry"
        data-testid="travel-map__retry"
        @click="emit('retry')"
        @keydown.enter.stop
        @keydown.space.stop
      >重新整理</button>
    </div>
  </section>
</template>

<style>
/* The full-bleed ink ground: the one hatched fog surface under the map, so
   unknown land inside and outside the window reads as one cloth. */
.travel-map {
  position: absolute;
  inset: 0;
  z-index: 0;
  overflow: hidden;
  background:
    radial-gradient(90% 80% at 42% 38%, #221f1a 0%, #161411 52%, var(--ink-950) 100%);
}
.travel-map__fog {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}
.travel-map__view {
  position: absolute;
  inset: 0;
  transition:
    opacity var(--motion-base) var(--ease-standard),
    filter var(--motion-base) var(--ease-standard);
}
/* A map that is not the current one yet is drawn as memory: dimmed and
   drained, so the stale image never reads as the present. */
.travel-map:not([data-map-status="ready"]) .travel-map__view {
  opacity: 0.55;
  filter: saturate(0.45) brightness(0.8);
}
/* The failure line: a quiet ink plate centred in the open stage, between the
   header and the band, with the gold hairline of the shared islands. */
.travel-map__state {
  position: absolute;
  left: 50%;
  top: calc(var(--header-h) + (100% - var(--header-h) - var(--band-h)) / 2);
  transform: translate(-50%, -50%);
  z-index: 2;
  display: flex;
  align-items: center;
  gap: calc(14px * var(--ui-scale));
  padding: calc(10px * var(--ui-scale)) calc(12px * var(--ui-scale)) calc(10px * var(--ui-scale)) calc(18px * var(--ui-scale));
  border: 1px solid rgba(185, 154, 96, 0.38);
  border-radius: var(--radius);
  background: var(--panel);
  box-shadow: var(--shadow);
  backdrop-filter: blur(6px);
  font: var(--text-sm)/1.4 var(--f-serif);
  color: var(--paper-200);
  white-space: nowrap;
}
.travel-map__retry {
  flex: none;
  min-height: calc(36px * var(--ui-scale));
  padding: 0 calc(14px * var(--ui-scale));
  border: 1px solid var(--gold-600);
  border-radius: var(--radius-sm);
  background: rgba(185, 154, 96, 0.1);
  color: var(--gold-300);
  font: var(--text-sm)/1 var(--f-sans);
  cursor: pointer;
  transition: background var(--motion-fast) var(--ease-standard), border-color var(--motion-fast) var(--ease-standard);
}
.travel-map__retry:hover {
  background: rgba(185, 154, 96, 0.2);
  border-color: var(--gold-400);
}
.travel-map__retry:focus-visible {
  outline: none;
  box-shadow: var(--focus);
}
</style>
