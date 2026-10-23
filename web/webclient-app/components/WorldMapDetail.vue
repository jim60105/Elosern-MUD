<script setup>
// The world map's selection reading (OpenSpec change render-world-map-view):
// the selected district, place or commission as text — its kind, full name
// (wrapped, never truncated), every nation a lit district belongs to, its
// landmark, places and commissions, and its bearing from the player. An
// unlit district reads only 未探明. WorldMapView mounts it by default; the
// final map drawer may render its own card from the same `detail` object
// through WorldMapView's `detail` slot. It is not a drawer shell: no focus
// trap, no map close, no data request.
defineProps({
  // featureDetail() from lib/world_map_view.js.
  detail: { type: Object, required: true },
});
const emit = defineEmits(["centre", "close"]);
</script>

<template>
  <section class="world-map-detail" data-testid="world-map-detail" :aria-label="`地圖詳情：${detail.title}`">
    <button
      type="button"
      class="world-map-detail__close"
      data-testid="world-map-detail__close"
      aria-label="關閉詳情"
      @click="emit('close')"
    >✕</button>
    <p class="world-map-detail__kind" :class="`is-${detail.kind}`">{{ detail.label }}</p>
    <h3
      class="world-map-detail__title"
      :class="{ 'is-unlit': detail.kind === 'district' && !detail.lit }"
      data-testid="world-map-detail__title"
    >{{ detail.title }}</h3>
    <ul v-if="detail.nations.length" class="world-map-detail__nations" aria-label="所屬國家">
      <li
        v-for="nation in detail.nations"
        :key="nation"
        class="world-map-detail__nation"
        data-testid="world-map-detail__nation"
      >{{ nation }}</li>
    </ul>
    <ul class="world-map-detail__lines">
      <li v-for="line in detail.lines" :key="line" class="world-map-detail__line">{{ line }}</li>
    </ul>
    <template v-if="detail.places.length">
      <h4 class="world-map-detail__subhead">區內地點</h4>
      <ul class="world-map-detail__list">
        <li v-for="name in detail.places" :key="name" class="world-map-detail__item">
          <span class="world-map-detail__glyph is-place" aria-hidden="true">◇</span>{{ name }}
        </li>
      </ul>
    </template>
    <template v-if="detail.quests.length">
      <h4 class="world-map-detail__subhead">相關委託</h4>
      <ul class="world-map-detail__list">
        <li v-for="quest in detail.quests" :key="quest.id" class="world-map-detail__item">
          <span class="world-map-detail__glyph is-quest" aria-hidden="true">◆</span>{{ quest.title }}
        </li>
      </ul>
    </template>
    <div class="world-map-detail__actions">
      <button
        type="button"
        class="world-map-detail__centre"
        data-testid="world-map-detail__centre"
        @click="emit('centre', detail.key)"
      >置中顯示</button>
    </div>
  </section>
</template>

<style scoped>
.world-map-detail {
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
.world-map-detail__close {
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
.world-map-detail__close:hover { color: var(--paper-50); border-color: var(--gold-600); }
.world-map-detail__kind {
  margin: 0 0 calc(6px * var(--ui-scale));
  color: var(--gold-500);
  font-size: var(--text-xs);
  letter-spacing: 0.2em;
}
.world-map-detail__kind.is-quest { color: var(--seal-400); }
.world-map-detail__title {
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
.world-map-detail__title.is-unlit { color: var(--paper-400); font-style: italic; letter-spacing: 0.2em; }
.world-map-detail__nations {
  display: flex;
  flex-wrap: wrap;
  gap: calc(6px * var(--ui-scale));
  margin: 0 0 calc(12px * var(--ui-scale));
  padding: 0;
  list-style: none;
}
.world-map-detail__nation {
  padding: calc(2px * var(--ui-scale)) calc(10px * var(--ui-scale));
  color: var(--paper-100);
  font-size: var(--text-xs);
  letter-spacing: 0.08em;
  background: rgba(176, 87, 79, 0.14);
  border: 1px solid rgba(176, 87, 79, 0.55);
  border-radius: 999px;
}
.world-map-detail__lines,
.world-map-detail__list { margin: 0; padding: 0; list-style: none; }
.world-map-detail__line {
  margin: 0 0 calc(6px * var(--ui-scale));
  color: var(--paper-300);
  font-size: var(--text-xs);
  line-height: 1.6;
}
.world-map-detail__subhead {
  margin: calc(18px * var(--ui-scale)) 0 calc(6px * var(--ui-scale));
  color: var(--paper-500);
  font-size: var(--text-xs);
  font-weight: 400;
  letter-spacing: 0.18em;
}
.world-map-detail__item {
  display: flex;
  gap: calc(8px * var(--ui-scale));
  color: var(--paper-100);
  font-size: var(--text-xs);
  line-height: 1.6;
}
.world-map-detail__glyph.is-place { color: var(--gold-400); }
.world-map-detail__glyph.is-quest { color: var(--seal-400); }
.world-map-detail__actions { margin-top: calc(20px * var(--ui-scale)); }
.world-map-detail__centre {
  min-width: calc(120px * var(--ui-scale));
  padding: calc(8px * var(--ui-scale)) calc(26px * var(--ui-scale));
  color: var(--gold-400);
  font-family: var(--f-display);
  font-size: var(--text-xs);
  letter-spacing: 0.2em;
  background: none;
  border: 1px solid var(--gold-600);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: color var(--motion-fast), border-color var(--motion-fast);
}
.world-map-detail__centre:hover { color: var(--gold-300); border-color: var(--gold-500); }
.world-map-detail :focus-visible { outline: 2px solid var(--gold-400); outline-offset: 2px; }
</style>
