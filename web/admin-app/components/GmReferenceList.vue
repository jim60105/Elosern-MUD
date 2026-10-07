<script setup>
// One list of authored references (gm-portal-s4-world-data §4.1).
//
// ``outgoing`` rows are the entries this entry references, by field path;
// ``incoming`` rows are the referrers of one inverse group, with the field of
// theirs that points here. Every target renders through GmEntityLink (◇); a
// declared reference whose target key is absent is shown broken — glyph,
// strike-through and a text badge, never by colour alone — and is not a link.
// Long lists show ``previewCount`` rows behind a disclosure.
import { computed, nextTick, ref } from "vue";
import GmEntityLink from "./GmEntityLink.vue";
import GmStatusBadge from "./GmStatusBadge.vue";

const props = defineProps({
  items: { type: Array, required: true },
  mode: {
    type: String,
    default: "outgoing",
    validator: (value) => ["outgoing", "incoming"].includes(value),
  },
  previewCount: { type: Number, default: 8 },
});

const expanded = ref(false);
const list = ref(null);
const hidden = computed(() => Math.max(props.items.length - props.previewCount, 0));
const shown = computed(() => (expanded.value || hidden.value === 0 ? props.items : props.items.slice(0, props.previewCount)));

function linkOf(item) {
  return { kind: "registry", registry: item.registry, id: item.key, missing: Boolean(item.missing) };
}

async function expand() {
  expanded.value = true;
  await nextTick();
  list.value?.querySelectorAll?.("li")?.[props.previewCount]?.querySelector?.("a, span")?.focus?.();
}
</script>

<template>
  <div class="gm-refs" :data-mode="mode">
    <ol ref="list" class="gm-refs__list">
      <li
        v-for="(item, index) in shown"
        :key="`${item.registry}/${item.key}/${item.fieldPath}/${index}`"
        class="gm-refs__row"
        :class="{ 'is-missing': item.missing }"
      >
        <p class="gm-refs__target">
          <span class="gm-refs__registry">{{ item.registryLabel || item.registry }}</span>
          <GmEntityLink :link="linkOf(item)" :label="String(item.key ?? '—')" />
          <span v-if="item.label" class="gm-refs__label">{{ item.label }}</span>
          <GmStatusBadge v-if="item.missing" status="crit" label="目標不存在" />
        </p>
        <p class="gm-refs__field">
          <span class="gm-refs__field-label">{{ mode === "outgoing" ? "此條目欄位" : "對方欄位" }}</span>
          <code class="gm-refs__path">{{ item.fieldPath }}</code>
        </p>
      </li>
    </ol>
    <button
      v-if="hidden > 0"
      type="button"
      class="ui-btn ui-btn--ghost ui-btn--sm gm-refs__more"
      :aria-expanded="expanded ? 'true' : 'false'"
      @click="expanded ? (expanded = false) : expand()"
    >
      {{ expanded ? "收合" : `顯示其餘 ${hidden} 筆` }}
    </button>
  </div>
</template>

<style scoped>
.gm-refs {
  display: grid;
  gap: var(--sp-2);
  min-width: 0;
}

.gm-refs__list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.gm-refs__row {
  display: grid;
  gap: 2px;
  padding: var(--sp-2) var(--sp-1);
  border-bottom: 1px dashed var(--ink-700);
}

.gm-refs__row:last-child {
  border-bottom: 0;
}

.gm-refs__row.is-missing {
  padding-inline: var(--sp-2);
  background: color-mix(in srgb, var(--crit) 8%, transparent);
  border-radius: var(--radius-sm);
}

.gm-refs__target {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: var(--sp-1) var(--sp-2);
  min-width: 0;
}

.gm-refs__registry {
  font-size: var(--text-xs);
  color: var(--paper-500);
}

.gm-refs__label {
  font-family: var(--f-serif);
  font-size: var(--text-sm);
  color: var(--paper-300);
}

.gm-refs__field {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: var(--sp-2);
  min-width: 0;
}

.gm-refs__field-label {
  font-size: var(--text-xs);
  color: var(--paper-500);
}

.gm-refs__path {
  min-width: 0;
  font-family: var(--f-mono);
  font-size: var(--text-xs);
  color: var(--paper-400);
  overflow-wrap: anywhere;
}

.gm-refs__more {
  justify-self: start;
}
</style>
