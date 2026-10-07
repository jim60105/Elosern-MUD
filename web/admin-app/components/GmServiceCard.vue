<script setup>
// One external-service status card (gm-portal-s2b-dashboard). The status is
// stated three ways — the badge text, its glyph, and the left rule style
// (warn dashed, crit double) — never by colour alone. A slot `error` renders
// as a critical card carrying the server's message and stable code.
import { computed } from "vue";
import GmStatusBadge from "./GmStatusBadge.vue";

const props = defineProps({
  name: { type: String, required: true },
  status: {
    type: String,
    default: "neutral",
    validator: (value) => ["ok", "warn", "crit", "neutral"].includes(value),
  },
  statusLabel: { type: String, default: "" },
  detail: { type: String, default: "" },
  meta: { type: Array, default: () => [] },
  error: { type: Object, default: null },
});

const tone = computed(() => (props.error ? "crit" : props.status));
const label = computed(() => (props.error ? "無法取得狀態" : props.statusLabel));
const line = computed(() => (props.error ? props.error.message : props.detail));
</script>

<template>
  <article class="gm-service-card" :class="`gm-service-card--${tone}`" :data-status="tone">
    <header class="gm-service-card__head">
      <h3 class="gm-service-card__name">{{ name }}</h3>
      <GmStatusBadge :status="tone" :label="label" />
    </header>
    <p v-if="line" class="gm-service-card__detail">{{ line }}</p>
    <dl v-if="error || meta.length" class="gm-service-card__meta">
      <div v-if="error" class="gm-service-card__row">
        <dt>錯誤代碼</dt>
        <dd><code>{{ error.code }}</code></dd>
      </div>
      <template v-else>
        <div v-for="item in meta" :key="item.label" class="gm-service-card__row">
          <dt>{{ item.label }}</dt>
          <dd :class="{ 'gm-mono': item.mono }" :title="item.title || null">{{ item.value }}</dd>
        </div>
      </template>
    </dl>
  </article>
</template>

<style scoped>
.gm-service-card {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
  min-width: 0;
  min-height: 132px;
  padding: var(--sp-4) var(--sp-4) var(--sp-4) calc(var(--sp-4) + 3px);
  background: var(--ink-860);
  border: var(--line);
  border-left: 3px solid transparent;
  border-radius: var(--radius);
  box-shadow: inset 0 1px 0 color-mix(in srgb, var(--gold-500) 22%, transparent);
}

.gm-service-card--ok {
  border-left: 3px solid color-mix(in srgb, var(--ok) 70%, transparent);
}

.gm-service-card--warn {
  border-left: 3px dashed var(--warn);
}

.gm-service-card--crit {
  background: color-mix(in srgb, var(--crit) 6%, var(--ink-860));
  border-left: 3px double var(--crit);
}

.gm-service-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-3);
}

.gm-service-card__name {
  font-family: var(--f-serif);
  font-size: var(--text-md);
  font-weight: 600;
  color: var(--paper-100);
}

.gm-service-card__detail {
  font-size: var(--text-sm);
  color: var(--paper-300);
}

.gm-service-card__meta {
  display: grid;
  gap: var(--sp-1);
  margin-top: auto;
  padding-top: var(--sp-3);
  border-top: 1px dashed var(--ink-700);
}

.gm-service-card__row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--sp-3);
  min-width: 0;
}

.gm-service-card__row dt {
  flex: none;
  font-size: var(--text-xs);
  color: var(--paper-500);
}

.gm-service-card__row dd {
  min-width: 0;
  overflow: hidden;
  font-size: var(--text-sm);
  color: var(--paper-200);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.gm-service-card__row code {
  font-size: var(--text-sm);
  color: var(--paper-100);
  user-select: all;
}
</style>
