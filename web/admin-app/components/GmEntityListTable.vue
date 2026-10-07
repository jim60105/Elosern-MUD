<script setup>
// The one list table of the runtime pages (gm-portal-s3-runtime-state §4/§6).
//
// Every list route and every narrative-tab collection answers with the same
// row shape — ``{id, kind, label, fields:[{label, value, mono?, link?}]}`` —
// so this renders the entity name as a link, one column per distinct field
// label (first-seen order, stable across pages), and an optional trailing
// column for a row expander. Lists never carry raw inventories or section
// payloads; nothing here invents a field a row does not have.
import { computed } from "vue";
import GmEmpty from "./GmEmpty.vue";
import GmEntityLink from "./GmEntityLink.vue";
import { entityTarget, kindLabel, linkTarget, targetHref } from "../lib/runtime.js";

const props = defineProps({
  rows: { type: Array, required: true },
  // The kind these rows are, for the label column's own link target.
  kind: { type: String, default: "" },
  caption: { type: String, required: true },
  emptyTitle: { type: String, default: "目前沒有資料" },
  emptyMessage: { type: String, default: "" },
  // A trailing column (e.g. 展開) backed by the `extra` slot.
  extraColumn: { type: String, default: "" },
});

const emit = defineEmits(["open-call"]);

const labels = computed(() => {
  const seen = [];
  for (const row of props.rows) {
    for (const field of row.fields ?? []) {
      if (!seen.includes(field.label)) seen.push(field.label);
    }
  }
  return seen;
});

function fieldOf(row, label) {
  return (row.fields ?? []).find((field) => field.label === label) ?? null;
}

function rowTarget(row) {
  // Records whose identity is owner-scoped carry their owner on the row.
  const target = linkTarget({
    kind: row.kind || props.kind,
    id: row.id,
    label: row.label,
    owner: row.owner ?? null,
  });
  return target ?? entityTarget(row.kind || props.kind, row.id, { owner: row.owner ?? null });
}

function rowHref(row) {
  return targetHref(rowTarget(row));
}

function cellText(field) {
  if (!field) return "—";
  const value = field.value;
  if (value === null || value === undefined) return "—";
  if (typeof value === "object") {
    try {
      return JSON.stringify(value);
    } catch {
      return String(value);
    }
  }
  return String(value);
}
</script>

<template>
  <GmEmpty v-if="rows.length === 0" :title="emptyTitle" :message="emptyMessage" />
  <div v-else class="gm-list" role="region" :aria-label="caption" tabindex="0">
    <table>
      <caption class="gm-visually-hidden">{{ caption }}</caption>
      <thead>
        <tr>
          <th scope="col">名稱</th>
          <th v-for="label in labels" :key="label" scope="col">{{ label }}</th>
          <th v-if="extraColumn" scope="col">{{ extraColumn }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, index) in rows" :key="row.id ?? index">
          <td class="gm-list__name">
            <a class="gm-entity-link" :href="rowHref(row)" :data-kind="row.kind || kind">{{ row.label }}</a>
          </td>
          <td
            v-for="label in labels"
            :key="label"
            :class="{ 'gm-list__mono': fieldOf(row, label)?.mono }"
          >
            <GmEntityLink
              v-if="fieldOf(row, label)?.link"
              :link="fieldOf(row, label).link"
              :label="cellText(fieldOf(row, label))"
              mono
              @open-call="emit('open-call', $event)"
            />
            <template v-else>{{ cellText(fieldOf(row, label)) }}</template>
          </td>
          <td v-if="extraColumn" class="gm-list__extra">
            <slot name="extra" :row="row" :index="index" />
          </td>
        </tr>
      </tbody>
    </table>
    <p class="gm-list__kind gm-visually-hidden">{{ kindLabel(kind) }}</p>
  </div>
</template>

<style scoped>
.gm-list {
  overflow-x: auto;
  background: var(--ink-860);
  border: var(--line);
  border-radius: var(--radius);
}

.gm-list:focus-visible {
  box-shadow: var(--focus);
  outline: none;
}

table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
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
  padding: var(--sp-2) var(--sp-4);
  font-size: var(--text-sm);
  color: var(--paper-200);
  border-bottom: 1px solid var(--ink-700);
  vertical-align: top;
  overflow-wrap: anywhere;
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

.gm-list__name {
  white-space: nowrap;
  font-weight: 600;
}

.gm-list__mono {
  font-family: var(--f-mono);
  font-size: var(--text-xs);
  font-variant-numeric: tabular-nums;
  color: var(--paper-300);
  /* Identifiers and codes stay on one line; the region scrolls instead of
     breaking a key mid-word. */
  white-space: nowrap;
}

.gm-list__name .gm-entity-link {
  text-decoration: none;
}

.gm-list__extra {
  white-space: nowrap;
}
</style>
