<script setup>
// A ledger table (gm-portal-s1-foundation). Columns flagged `mono` render
// their values verbatim in the monospace face (registry keys, ids, codes);
// a cell slot `#cell-<key>` can supply richer content such as a status
// badge. With no rows the table yields to GmEmpty.
import GmEmpty from "./GmEmpty.vue";

defineProps({
  columns: { type: Array, required: true },
  rows: { type: Array, required: true },
  rowKey: { type: String, default: "id" },
  caption: { type: String, required: true },
  captionHidden: { type: Boolean, default: false },
  flush: { type: Boolean, default: false },
  emptyTitle: { type: String, default: "目前沒有資料" },
  emptyMessage: { type: String, default: "" },
});
</script>

<template>
  <GmEmpty v-if="rows.length === 0" :title="emptyTitle" :message="emptyMessage" />
  <div v-else class="gm-table" :class="{ 'gm-table--flush': flush }" role="region" :aria-label="caption" tabindex="0">
    <table>
      <caption :class="{ 'gm-visually-hidden': captionHidden }">{{ caption }}</caption>
      <thead>
        <tr>
          <th
            v-for="column in columns"
            :key="column.key"
            scope="col"
            :style="column.align ? { textAlign: column.align } : null"
          >
            {{ column.label }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, index) in rows" :key="row[rowKey] ?? index">
          <td
            v-for="column in columns"
            :key="column.key"
            :class="{ 'gm-table__mono': column.mono }"
            :style="column.align ? { textAlign: column.align } : null"
          >
            <slot :name="`cell-${column.key}`" :row="row" :value="row[column.key]">{{ row[column.key] }}</slot>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.gm-table {
  overflow-x: auto;
  border-radius: inherit;
}

.gm-table:focus-visible {
  box-shadow: var(--focus);
}

table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
}

caption {
  caption-side: top;
  padding: var(--sp-3) var(--sp-4) var(--sp-2);
  text-align: start;
  font-size: var(--text-sm);
  color: var(--paper-500);
}

th {
  padding: var(--sp-3) var(--sp-4);
  text-align: start;
  font-size: var(--text-xs);
  font-weight: 600;
  letter-spacing: 0.08em;
  color: var(--paper-400);
  background: var(--ink-820);
  border-bottom: 1px solid var(--band-edge-dim);
  white-space: nowrap;
}

td {
  height: 48px;
  padding: var(--sp-3) var(--sp-4);
  font-size: var(--text-md);
  color: var(--paper-200);
  border-bottom: 1px solid var(--ink-700);
  transition:
    background-color var(--motion-fast) var(--ease-standard),
    color var(--motion-fast) var(--ease-standard);
}

tbody tr:last-child td {
  border-bottom: 0;
}

tbody tr:nth-child(even) td {
  background: color-mix(in srgb, var(--ink-820) 55%, transparent);
}

tbody tr:hover td {
  background: var(--ink-820);
}

.gm-table__mono {
  font-family: var(--f-mono);
  font-size: var(--text-sm);
  font-variant-numeric: tabular-nums;
  color: var(--paper-300);
  white-space: nowrap;
}

.gm-table--flush th:first-child,
.gm-table--flush td:first-child {
  padding-inline-start: var(--sp-5);
}

.gm-table--flush th:last-child,
.gm-table--flush td:last-child {
  padding-inline-end: var(--sp-5);
}
</style>
