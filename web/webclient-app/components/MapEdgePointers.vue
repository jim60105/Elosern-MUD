<script setup>
// MapEdgePointers (OpenSpec change redesign-map-drawer; design §6.2/§6.5):
// the map drawer's HTML layer of off-screen commission pointers. It draws
// what lib/map_edge_pointers.js laid out — at most three pointers on the
// drawer-aware rectangle's edge, nearest first, and one `＋n` chip for the
// rest — as real buttons: each names its commission, direction and distance,
// and activating it asks the host to select and centre that commission. The
// chip opens the host's commission list, which always holds every accepted
// commission as text, so nothing here is the only way to reach one.
import { computed } from "vue";

const props = defineProps({
  // layoutEdgePointers(...).pointers
  pointers: { type: Array, default: () => [] },
  // layoutEdgePointers(...).more
  more: { type: Object, default: null },
});
const emit = defineEmits(["activate", "more"]);

const items = computed(() => props.pointers);

function place(entry) {
  return { left: `${entry.x}px`, top: `${entry.y}px` };
}
</script>

<template>
  <div class="map-edge-pointers" data-testid="map-edge-pointers">
    <button
      v-for="pointer in items"
      :key="pointer.id"
      type="button"
      class="map-edge-pointer"
      :class="`is-${pointer.side}`"
      data-testid="map-edge-pointer"
      :data-quest="pointer.id"
      :data-side="pointer.side"
      :style="place(pointer)"
      :aria-label="`委託 ${pointer.title}，${pointer.sub}，在地圖上顯示`"
      @pointerdown.stop
      @click="emit('activate', pointer.id)"
    >
      <span class="map-edge-pointer__arrow" :style="{ transform: `rotate(${pointer.angle}deg)` }" aria-hidden="true">
        <svg viewBox="0 0 16 16" width="16" height="16"><path d="M3 3.2 14 8 3 12.8 5.6 8Z" /></svg>
      </span>
      <span class="map-edge-pointer__text" aria-hidden="true">
        <span class="map-edge-pointer__title">{{ pointer.title }}</span>
        <span class="map-edge-pointer__sub">{{ pointer.sub }}</span>
      </span>
    </button>
    <button
      v-if="more"
      type="button"
      class="map-edge-pointer map-edge-pointer--more"
      :class="`is-${more.side}`"
      data-testid="map-edge-pointer-more"
      :data-side="more.side"
      :style="place(more)"
      :aria-label="`另有 ${more.count} 項委託在畫面外，開啟委託清單`"
      @pointerdown.stop
      @click="emit('more')"
    >＋{{ more.count }}</button>
  </div>
</template>

<style scoped>
.map-edge-pointers {
  position: absolute;
  inset: 0;
  z-index: 3;
  pointer-events: none;
}

.map-edge-pointer {
  position: absolute;
  display: flex;
  align-items: center;
  gap: calc(8px * var(--ui-scale));
  box-sizing: border-box;
  /* Its own width, not the room left of its anchor point near an edge. */
  width: max-content;
  max-width: calc(280px * var(--ui-scale));
  min-height: calc(36px * var(--ui-scale));
  padding: calc(4px * var(--ui-scale)) calc(14px * var(--ui-scale)) calc(4px * var(--ui-scale)) calc(6px * var(--ui-scale));
  color: #ffe2dc;
  font-family: var(--f-sans);
  font-size: var(--text-xs);
  line-height: 1.15;
  text-align: left;
  white-space: nowrap;
  background: linear-gradient(180deg, rgba(42, 18, 18, 0.94), rgba(22, 11, 11, 0.94));
  border: 1px solid rgba(207, 68, 68, 0.62);
  border-radius: var(--radius-pill);
  box-shadow: 0 calc(6px * var(--ui-scale)) calc(18px * var(--ui-scale)) rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 220, 210, 0.08);
  pointer-events: auto;
  cursor: pointer;
  animation: map-edge-pointer-in var(--motion-base) var(--ease-standard) both;
  transition: border-color var(--motion-fast) ease, box-shadow var(--motion-fast) ease, left var(--motion-base) var(--ease-standard), top var(--motion-base) var(--ease-standard);
}
.map-edge-pointer.is-left { transform: translate(0, -50%); }
.map-edge-pointer.is-right { transform: translate(-100%, -50%); flex-direction: row-reverse; padding: calc(4px * var(--ui-scale)) calc(6px * var(--ui-scale)) calc(4px * var(--ui-scale)) calc(14px * var(--ui-scale)); text-align: right; }
.map-edge-pointer.is-top { transform: translate(-50%, 0); }
.map-edge-pointer.is-bottom { transform: translate(-50%, -100%); }

.map-edge-pointer:hover {
  border-color: var(--seal-400);
  box-shadow: 0 calc(6px * var(--ui-scale)) calc(20px * var(--ui-scale)) rgba(0, 0, 0, 0.55), 0 0 calc(14px * var(--ui-scale)) rgba(207, 68, 68, 0.28);
}
.map-edge-pointer:focus-visible {
  outline: none;
  border-color: var(--gold-400);
  box-shadow: var(--focus);
}

.map-edge-pointer__arrow {
  flex: none;
  display: grid;
  place-items: center;
  width: calc(26px * var(--ui-scale));
  height: calc(26px * var(--ui-scale));
  border-radius: 50%;
  background: radial-gradient(circle at 50% 40%, rgba(207, 68, 68, 0.32), rgba(207, 68, 68, 0.08));
}
.map-edge-pointer__arrow svg {
  width: calc(14px * var(--ui-scale));
  height: calc(14px * var(--ui-scale));
}
.map-edge-pointer__arrow path { fill: var(--seal-400); }

.map-edge-pointer__text {
  display: grid;
  min-width: 0;
}
.map-edge-pointer__title {
  overflow: hidden;
  text-overflow: ellipsis;
  letter-spacing: 0.04em;
}
.map-edge-pointer__sub {
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--paper-400);
  font-size: var(--text-xs);
  letter-spacing: 0.02em;
}

.map-edge-pointer--more {
  justify-content: center;
  min-width: calc(48px * var(--ui-scale));
  padding: calc(4px * var(--ui-scale)) calc(12px * var(--ui-scale));
  color: var(--gold-300);
  font-family: var(--f-display);
  letter-spacing: 0.08em;
  background: rgba(14, 16, 20, 0.92);
  border-color: var(--gold-600);
}
.map-edge-pointer--more.is-right { padding: calc(4px * var(--ui-scale)) calc(12px * var(--ui-scale)); }

@keyframes map-edge-pointer-in {
  from { opacity: 0; }
  to { opacity: 1; }
}
@media (prefers-reduced-motion: reduce) {
  .map-edge-pointer { animation: none; transition: none; }
}
</style>
