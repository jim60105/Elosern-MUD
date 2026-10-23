<script setup>
// The area map's selection reading (OpenSpec change render-area-map-view):
// the selected node's kind, full name (wrapped, never truncated), state,
// gate far side, bearing/distance and related commissions, then 前往 only
// for the server's adjacent move descriptor. AreaMapView mounts it by
// default; the final map drawer may render its own card from the same
// `detail` object through AreaMapView's `detail` slot. It is not a drawer
// shell: no focus trap, no map close, no data request.
defineProps({
  // nodeDetail() from lib/area_map_view.js.
  detail: { type: Object, required: true },
});
const emit = defineEmits(["move", "centre", "close"]);
</script>

<template>
  <section class="area-map-detail" data-testid="area-map-detail" :aria-label="`地點詳情：${detail.title}`">
    <button
      type="button"
      class="area-map-detail__close"
      data-testid="area-map-detail__close"
      aria-label="關閉詳情"
      @click="emit('close')"
    >✕</button>
    <p class="area-map-detail__kind">{{ detail.kind }}</p>
    <h3 class="area-map-detail__title" data-testid="area-map-detail__title">{{ detail.title }}</h3>
    <ul class="area-map-detail__lines">
      <li
        v-for="line in detail.lines"
        :key="line"
        class="area-map-detail__line"
        :class="{ 'is-gate': line.startsWith('通往 ') }"
      >{{ line }}</li>
    </ul>
    <template v-if="detail.quests.length">
      <h4 class="area-map-detail__subhead">相關委託</h4>
      <ul class="area-map-detail__quests">
        <li v-for="quest in detail.quests" :key="quest.id" class="area-map-detail__quest">
          <span class="area-map-detail__quest-glyph" aria-hidden="true">◆</span>{{ quest.title }}
        </li>
      </ul>
    </template>
    <div class="area-map-detail__actions">
      <button
        v-if="detail.move"
        type="button"
        class="area-map-detail__go"
        data-testid="area-map-detail__go"
        @click="emit('move', detail.move)"
      >前往</button>
      <button
        v-else
        type="button"
        class="area-map-detail__centre"
        data-testid="area-map-detail__centre"
        @click="emit('centre', detail.id)"
      >置中顯示</button>
    </div>
  </section>
</template>

<style scoped>
.area-map-detail {
  position: relative;
  box-sizing: border-box;
  height: 100%;
  overflow-y: auto;
  padding: calc(24px * var(--ui-scale)) calc(22px * var(--ui-scale)) calc(20px * var(--ui-scale));
  color: var(--paper-200);
  font-family: var(--f-sans);
  background:
    linear-gradient(180deg, rgba(238, 221, 180, 0.05), transparent 38%),
    linear-gradient(180deg, #17181cf5, #0f1013f8);
  border-left: 1px solid rgba(185, 154, 96, 0.32);
  box-shadow: -18px 0 36px rgba(0, 0, 0, 0.42);
}
.area-map-detail__close {
  position: absolute;
  top: calc(14px * var(--ui-scale));
  right: calc(14px * var(--ui-scale));
  width: calc(32px * var(--ui-scale));
  height: calc(32px * var(--ui-scale));
  color: var(--paper-400);
  font-size: var(--text-xs);
  background: none;
  border: 1px solid var(--ink-600);
  border-radius: 50%;
  cursor: pointer;
  transition: color var(--motion-fast), border-color var(--motion-fast);
}
.area-map-detail__close:hover { color: var(--paper-50); border-color: var(--gold-600); }
.area-map-detail__kind {
  margin: 0 0 calc(6px * var(--ui-scale));
  color: var(--gold-500);
  font-size: var(--text-xs);
  letter-spacing: 0.2em;
}
.area-map-detail__title {
  margin: 0 calc(40px * var(--ui-scale)) calc(14px * var(--ui-scale)) 0;
  padding-bottom: calc(12px * var(--ui-scale));
  color: var(--paper-50);
  font-family: var(--f-display);
  font-size: var(--text-xl);
  font-weight: 400;
  line-height: 1.35;
  letter-spacing: 0.06em;
  overflow-wrap: anywhere;
  border-bottom: 1px solid rgba(185, 154, 96, 0.22);
}
.area-map-detail__lines,
.area-map-detail__quests { margin: 0; padding: 0; list-style: none; }
.area-map-detail__line {
  margin: 0 0 calc(6px * var(--ui-scale));
  color: var(--paper-300);
  font-size: var(--text-xs);
  line-height: 1.6;
}
.area-map-detail__line.is-gate { color: var(--gold-400); }
.area-map-detail__subhead {
  margin: calc(18px * var(--ui-scale)) 0 calc(6px * var(--ui-scale));
  color: var(--paper-500);
  font-size: var(--text-xs);
  font-weight: 400;
  letter-spacing: 0.18em;
}
.area-map-detail__quest {
  display: flex;
  gap: calc(8px * var(--ui-scale));
  color: var(--paper-100);
  font-size: var(--text-xs);
  line-height: 1.6;
}
.area-map-detail__quest-glyph { color: var(--seal-400); }
.area-map-detail__actions { margin-top: calc(20px * var(--ui-scale)); }
.area-map-detail__go,
.area-map-detail__centre {
  min-width: calc(120px * var(--ui-scale));
  padding: calc(8px * var(--ui-scale)) calc(26px * var(--ui-scale));
  font-family: var(--f-display);
  font-size: var(--text-xs);
  letter-spacing: 0.2em;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background var(--motion-fast), border-color var(--motion-fast), color var(--motion-fast);
}
.area-map-detail__go {
  color: var(--paper-50);
  background: linear-gradient(180deg, var(--seal-600), var(--seal-700));
  border: 1px solid var(--seal-500);
  box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.4), 0 6px 16px rgba(124, 32, 38, 0.35);
}
.area-map-detail__go:hover { background: linear-gradient(180deg, var(--seal-500), var(--seal-600)); }
.area-map-detail__centre {
  color: var(--gold-400);
  background: none;
  border: 1px solid var(--gold-600);
}
.area-map-detail__centre:hover { color: var(--gold-300); border-color: var(--gold-500); }
.area-map-detail :focus-visible { outline: 2px solid var(--gold-400); outline-offset: 2px; }
</style>
