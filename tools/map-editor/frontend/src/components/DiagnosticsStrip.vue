<script setup>
// Diagnostics strip (frontend design §2): a one-line summary that expands
// into rows grouped by class. Each row names its object, file, field and
// line and offers 前往, or 顯示圖層並前往 for a target on a hidden layer.
// Message text renders through text interpolation only.
import { REVEAL_GO } from "../lib/diagnostics.js";

defineProps({
  groups: { type: Array, default: () => [] },
  counts: { type: Object, required: true },
  open: { type: Boolean, default: false },
  summary: { type: Array, default: () => [] },
  lastDocument: { type: String, default: null },
  notice: { type: Object, default: null },
  hints: { type: String, default: "" },
});
const emit = defineEmits(["toggle", "go"]);
</script>

<template>
  <div class="diagnostics">
    <div class="diagnostics__summary">
      <button type="button" class="diagnostics__toggle" :aria-expanded="open" data-diagnostics-toggle @click="emit('toggle')">
        診斷 · {{ counts.total }} {{ open ? "▾" : "▸" }}
      </button>
      <span class="diagnostics__count diagnostics__count--seal" data-count="errors">✕ {{ counts.errors }}</span>
      <span class="diagnostics__count diagnostics__count--warn" data-count="warnings">▲ {{ counts.warnings }}</span>
      <span v-for="item in summary" :key="item" class="diagnostics__muted">· {{ item }}</span>
      <span v-if="lastDocument" class="diagnostics__muted mono" data-last-saved>版面檔：{{ lastDocument }}</span>
      <span class="diagnostics__notice" role="status" :data-copy-notice="notice?.state ?? null">{{ notice?.text ?? "" }}</span>
      <span class="diagnostics__hint">{{ hints }}</span>
    </div>
    <div v-if="open" class="diagnostics__list" tabindex="-1" data-diagnostics-list>
      <section v-for="group in groups" :key="group.key" class="diagnostics__group" :data-diagnostic-group="group.key">
        <h3 class="diagnostics__group-label" :class="`diagnostics__group-label--${group.tone}`">
          {{ group.glyph }} {{ group.label }} · {{ group.rows.length }}
        </h3>
        <ol class="plain">
          <li v-for="row in group.rows" :key="row.id" class="diagnostic" :data-diagnostic="row.code" :data-diagnostic-class="group.key">
            <span class="diagnostic__glyph" :class="`diagnostic__glyph--${group.tone}`" aria-hidden="true">{{ group.glyph }}</span>
            <span class="diagnostic__message">{{ row.message }}</span>
            <span v-if="row.object" class="diagnostic__object">{{ row.object }}</span>
            <span class="mono diagnostic__where">{{ row.where }}<template v-if="row.field"> · {{ row.field }}</template></span>
            <button
              v-if="row.action"
              type="button"
              class="button diagnostic__go"
              :data-diagnostic-action="row.action"
              @click="emit('go', row)"
            >
              {{ row.action === REVEAL_GO ? "顯示圖層並前往" : "前往" }}
            </button>
          </li>
        </ol>
      </section>
      <p v-if="!groups.length" class="diagnostics__muted">沒有診斷。</p>
    </div>
  </div>
</template>
