<script setup>
// The runtime list pager (gm-portal-s3-runtime-state §4/§6).
//
// Forward-only cursor paging: the server returns an opaque ``next_cursor``
// that already carries the filter fingerprint, so this control can only ask
// for the next page or restart from the first — it never invents an offset.
import { computed } from "vue";
import { LIST_LIMIT_CHOICES } from "../lib/runtime.js";

const props = defineProps({
  nextCursor: { type: String, default: null },
  limit: { type: Number, required: true },
  shown: { type: Number, default: 0 },
  // How many pages have been walked in this session (1 = first page).
  page: { type: Number, default: 1 },
  busy: { type: Boolean, default: false },
});

const emit = defineEmits(["more", "limit", "first"]);

const hasMore = computed(() => Boolean(props.nextCursor));
const choices = computed(() =>
  LIST_LIMIT_CHOICES.includes(props.limit)
    ? LIST_LIMIT_CHOICES
    : [...LIST_LIMIT_CHOICES, props.limit].sort((a, b) => a - b),
);

function onLimit(event) {
  const value = Number(event.target.value);
  if (Number.isFinite(value) && value !== props.limit) emit("limit", value);
}
</script>

<template>
  <div class="gm-pager" :aria-busy="busy ? 'true' : null">
    <p class="gm-pager__status" role="status">
      <span class="gm-pager__page">第 {{ page }} 頁</span>
      <span class="gm-pager__shown">本頁 {{ shown }} 筆</span>
    </p>

    <label class="gm-pager__limit">
      <span>每頁</span>
      <select class="gm-pager__select" :value="limit" @change="onLimit">
        <option v-for="option in choices" :key="option" :value="option">{{ option }}</option>
      </select>
      <span>筆</span>
    </label>

    <button
      type="button"
      class="ui-btn ui-btn--ghost ui-btn--sm"
      :aria-disabled="page > 1 && !busy ? null : 'true'"
      @click="page > 1 && !busy && emit('first')"
    >
      回到最前
    </button>
    <button
      type="button"
      class="ui-btn ui-btn--sm gm-pager__more"
      :aria-disabled="hasMore && !busy ? null : 'true'"
      @click="hasMore && !busy && emit('more')"
    >
      {{ busy ? "載入中…" : hasMore ? "載入下一頁" : "已到最後一頁" }}
    </button>
  </div>
</template>

<style scoped>
.gm-pager {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--sp-2) var(--sp-4);
  padding: var(--sp-2) var(--sp-3) var(--sp-2) var(--sp-4);
  background: var(--ink-860);
  border: var(--line);
  border-radius: var(--radius);
}

.gm-pager__status {
  display: flex;
  gap: var(--sp-3);
  font-size: var(--text-sm);
  color: var(--paper-200);
}

.gm-pager__page {
  font-family: var(--f-serif);
}

.gm-pager__shown {
  color: var(--paper-500);
}

.gm-pager__limit {
  display: flex;
  align-items: center;
  gap: var(--sp-1);
  margin-left: auto;
  font-size: var(--text-xs);
  color: var(--paper-500);
}

.gm-pager__select {
  min-height: 28px;
  padding: 0 var(--sp-1);
  font-family: var(--f-mono);
  font-size: var(--text-sm);
  color: var(--paper-100);
  background: var(--ink-950);
  border: var(--line);
  border-radius: var(--radius-sm);
}

.gm-pager__select:focus-visible {
  box-shadow: var(--focus);
  outline: none;
}

.gm-pager__more {
  min-width: 9em;
}
</style>
