<script setup>
// ListDetail (webclient-window-primitives, design §6/§9): the window body
// grid — an optional rail (MemberRail), a list column and a detail column.
// The list column and the detail's scroll region overflow independently,
// and the action bar slot is pinned to the bottom of the detail column,
// outside its scroll region, so scrolling either column never moves it.
// `variant="portrait"` narrows the list column for the 成員 tab's nameplate.
defineProps({
  variant: {
    type: String,
    default: "default",
    validator: (value) => ["default", "portrait"].includes(value),
  },
  listLabel: { type: String, default: null },
  detailLabel: { type: String, default: null },
});
</script>

<template>
  <div
    class="list-detail"
    :class="{ 'list-detail--rail': $slots.rail, 'list-detail--portrait': variant === 'portrait' }"
    data-testid="list-detail"
  >
    <div v-if="$slots.rail" class="list-detail__rail" data-testid="list-detail__rail">
      <slot name="rail" />
    </div>
    <section class="list-detail__list" :aria-label="listLabel || undefined" data-testid="list-detail__list">
      <slot name="list" />
    </section>
    <section class="list-detail__detail" :aria-label="detailLabel || undefined" data-testid="list-detail__detail">
      <div class="list-detail__scroll" data-testid="list-detail__scroll">
        <slot name="detail" />
      </div>
      <div v-if="$slots.actions" class="list-detail__actions" data-testid="list-detail__actions">
        <slot name="actions" />
      </div>
    </section>
  </div>
</template>

<style scoped>
/* The approved prototype's `.pm-body`, `.pm-col`, `.pm-list` and
   `.pm-detail` (docs/design/party-member-management/prototype.css). */
.list-detail {
  --list-detail-rail-w: calc(68px * var(--ui-scale));
  display: grid;
  grid-template-columns: minmax(calc(340px * var(--ui-scale)), 0.85fr) minmax(0, 1.15fr);
  flex: 1;
  min-width: 0;
  min-height: 0;
  height: 100%;
}

.list-detail--rail {
  grid-template-columns: var(--list-detail-rail-w) minmax(calc(340px * var(--ui-scale)), 0.85fr) minmax(0, 1.15fr);
}

.list-detail--portrait {
  grid-template-columns: calc(280px * var(--ui-scale)) minmax(0, 1fr);
}

.list-detail--rail.list-detail--portrait {
  grid-template-columns: var(--list-detail-rail-w) calc(280px * var(--ui-scale)) minmax(0, 1fr);
}

.list-detail__rail {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.list-detail__rail > * {
  flex: 1;
}

.list-detail__list {
  min-width: 0;
  min-height: 0;
  overflow: auto;
  box-sizing: border-box;
  padding: var(--sp-4) var(--sp-5);
  background: var(--list-detail-list-bg, #15171c);
  scrollbar-color: var(--ink-600) transparent;
  scrollbar-width: thin;
}

.list-detail__detail {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  box-sizing: border-box;
  padding: var(--sp-4) var(--sp-5);
}

.list-detail__scroll {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding-right: var(--sp-1);
  scrollbar-color: var(--ink-600) transparent;
  scrollbar-width: thin;
}

.list-detail__actions {
  flex: none;
}
</style>
