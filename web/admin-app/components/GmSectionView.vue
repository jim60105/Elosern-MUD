<script setup>
// The one curated-section renderer (gm-portal-s3-runtime-state §6).
//
// Every reader section shares one wire vocabulary — ledger, table, groups,
// tiles, chips, tree, text, empty, bullets — so the SPA renders all curated
// panels (accounts through art, and the narrative tabs) with a single
// component instead of one bespoke panel per entity kind. A section that
// failed carries its own error slot, which is rendered in place: the other
// panels of the page stay readable.
import { computed, defineComponent, h } from "vue";
import GmCodeBlock from "./GmCodeBlock.vue";
import GmEntityLink from "./GmEntityLink.vue";
import GmError from "./GmError.vue";
import GmJsonTree from "./GmJsonTree.vue";
import GmTable from "./GmTable.vue";

const props = defineProps({
  section: { type: Object, required: true },
});

const emit = defineEmits(["open-call"]);

function display(value) {
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

// One value renderer for ledger rows and table cells (mono/tone/link).
const GmValue = defineComponent({
  name: "GmValue",
  props: { entry: { type: Object, required: true } },
  emits: ["open-call"],
  setup(inner, { emit: emitValue }) {
    return () => {
      const entry = inner.entry ?? {};
      const text = display(entry.value);
      const classes = {
        "gm-value": true,
        "gm-mono": Boolean(entry.mono),
        [`is-${entry.tone}`]: Boolean(entry.tone),
      };
      return h(
        "span",
        { class: classes },
        entry.link
          ? [
              h(GmEntityLink, {
                link: entry.link,
                label: text,
                mono: false,
                onOpenCall: (id) => emitValue("open-call", id),
              }),
            ]
          : [text],
      );
    };
  },
});

const error = computed(() => props.section.error ?? null);
const payload = computed(() => props.section.type ?? null);
const note = computed(() => props.section.note ?? "");
const rows = computed(() => props.section.rows ?? []);
const tableRows = computed(() =>
  (rows.value ?? []).map((row, index) => ({ ...(row.cells ?? {}), key: row.key ?? String(index) })),
);
const columns = computed(() => props.section.columns ?? []);
</script>

<template>
  <section class="gm-section" :data-section="section.key" :data-type="error ? 'error' : payload">
    <header class="gm-section__header">
      <h3 class="gm-section__title">{{ section.title }}</h3>
      <span class="gm-section__key gm-mono">{{ section.key }}</span>
    </header>

    <GmError
      v-if="error"
      compact
      live="off"
      :title="`「${section.title}」無法讀取`"
      :message="error.message"
      :code="error.code"
    />

    <template v-else>
      <dl v-if="payload === 'ledger'" class="gm-ledger gm-section__ledger">
        <div v-for="(row, index) in rows" :key="row.key ?? index" class="gm-ledger__row">
          <dt>{{ row.label }}</dt>
          <dd><GmValue :entry="row" @open-call="emit('open-call', $event)" /></dd>
        </div>
      </dl>

      <GmTable
        v-else-if="payload === 'table'"
        :columns="columns"
        :rows="tableRows"
        :caption="section.title"
        caption-hidden
        empty-title="目前沒有資料"
        :empty-message="section.empty_note ?? ''"
      >
        <template v-for="column in columns" #[`cell-${column.key}`]="{ value }">
          <GmValue :entry="value ?? { value: null }" @open-call="emit('open-call', $event)" />
        </template>
      </GmTable>

      <div v-else-if="payload === 'groups'" class="gm-section__groups">
        <div v-for="(item, index) in section.groups ?? []" :key="item.key ?? index" class="gm-section__group">
          <h4 class="gm-section__group-title">
            {{ item.title }}
            <span v-if="item.note" class="gm-section__group-note">{{ item.note }}</span>
          </h4>
          <dl class="gm-ledger">
            <div v-for="(row, rowIndex) in item.rows ?? []" :key="row.key ?? rowIndex" class="gm-ledger__row">
              <dt>{{ row.label }}</dt>
              <dd><GmValue :entry="row" @open-call="emit('open-call', $event)" /></dd>
            </div>
          </dl>
        </div>
      </div>

      <ul v-else-if="payload === 'tiles'" class="gm-stats">
        <li v-for="(tile, index) in section.tiles ?? []" :key="tile.key ?? index" class="gm-stat">
          <span class="gm-stat__value" :class="{ [`is-${tile.tone}`]: tile.tone }">{{ tile.value }}</span>
          <span class="gm-stat__label">{{ tile.label }}<template v-if="tile.unit"> {{ tile.unit }}</template></span>
        </li>
      </ul>

      <ul v-else-if="payload === 'chips'" class="gm-section__chips">
        <li v-for="(chip, index) in section.chips ?? []" :key="chip.key ?? index">
          <GmEntityLink
            v-if="chip.link"
            class="gm-chip gm-section__chip"
            :link="chip.link"
            :label="chip.label"
            @open-call="emit('open-call', $event)"
          />
          <span v-else class="gm-chip gm-section__chip">{{ chip.label }}</span>
        </li>
      </ul>

      <GmJsonTree
        v-else-if="payload === 'tree'"
        :value="section.value"
        @open-call="emit('open-call', $event)"
      />

      <GmCodeBlock
        v-else-if="payload === 'text'"
        :text="section.text"
        :max-lines="20"
        label="原文"
      />

      <ul v-else-if="payload === 'bullets'" class="gm-section__bullets">
        <li v-for="(item, index) in section.items ?? []" :key="index">{{ item }}</li>
      </ul>

      <p v-else-if="payload === 'empty'" class="gm-section__empty">{{ section.note }}</p>

      <GmJsonTree v-else :value="section" :open-depth="1" @open-call="emit('open-call', $event)" />
    </template>

    <p v-if="note && payload !== 'empty'" class="gm-section__note">{{ note }}</p>
  </section>
</template>

<style scoped>
.gm-section {
  display: grid;
  gap: var(--sp-3);
  min-width: 0;
}

.gm-section__header {
  display: flex;
  align-items: baseline;
  gap: var(--sp-3);
}

.gm-section__title {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  font-family: var(--f-serif);
  font-size: var(--text-md);
  font-weight: 600;
  color: var(--paper-100);
}

/* The same seal-like gold diamond the panel header uses. */
.gm-section__title::before {
  content: "";
  flex: none;
  width: 5px;
  height: 5px;
  background: var(--gold-500);
  transform: rotate(45deg);
}

.gm-section__key {
  font-size: var(--text-xs);
  color: var(--paper-500);
}

.gm-section__ledger {
  padding: var(--sp-3) var(--sp-4);
  background: var(--ink-860);
  border: var(--line);
  border-radius: var(--radius-sm);
}

.gm-section__groups {
  display: grid;
  gap: var(--sp-4);
}

.gm-section__group {
  display: grid;
  gap: var(--sp-2);
}

.gm-section__group-title {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: var(--sp-3);
  font-size: var(--text-sm);
  font-weight: 600;
  letter-spacing: 0.08em;
  color: var(--paper-300);
}

.gm-section__group-note {
  font-weight: 400;
  letter-spacing: 0;
  color: var(--paper-500);
}

.gm-section__chips,
.gm-section__bullets {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-2);
  padding: 0;
  list-style: none;
}

.gm-section__bullets {
  flex-direction: column;
  font-size: var(--text-sm);
  color: var(--paper-200);
}

.gm-section__chip {
  text-decoration: none;
}

.gm-section__empty,
.gm-section__note {
  font-size: var(--text-sm);
  color: var(--paper-500);
}

.gm-section__note {
  padding-left: var(--sp-3);
  border-left: 2px solid var(--ink-700);
}
</style>

<!-- Shared with the GmValue render function this file defines, so it cannot
     carry the SFC's scope id. -->
<style>
.gm-value {
  min-width: 0;
  overflow-wrap: anywhere;
  color: var(--paper-100);
}

.gm-value.gm-mono {
  font-family: var(--f-mono);
  font-size: var(--text-sm);
  font-variant-numeric: tabular-nums;
}

.gm-value.is-gold {
  color: var(--gold-300);
}

.gm-value.is-ok {
  color: var(--ok, var(--paper-100));
}

.gm-value.is-warn {
  color: var(--warn);
}

.gm-value.is-crit {
  color: var(--crit);
}
</style>
