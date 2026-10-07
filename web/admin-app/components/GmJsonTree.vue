<script setup>
// The sole JSON-tree renderer (gm-portal-s3-runtime-state §3/§6).
//
// Used for raw tabs, curated ``tree`` sections and the structured S2 payload
// drawer. Object references arrive as ``{"$ref": "#12", …}`` and become links
// to the object's raw inspection; values JSON cannot carry arrive as
// ``{"$unserializable": "<type>", "repr": "…"}`` and are shown as a distinct,
// bounded marker so one bad leaf never hides the rest of the inventory.
// Collapsing uses native <details>, so it is keyboard-operable and stays
// motion-neutral.
import { computed } from "vue";
import GmEntityLink from "./GmEntityLink.vue";

const props = defineProps({
  value: { type: null, default: null },
  // The key this node hangs under (rendered as the row label).
  name: { type: [String, Number], default: "" },
  depth: { type: Number, default: 0 },
  // Levels rendered expanded; deeper levels start collapsed.
  openDepth: { type: Number, default: 2 },
});

const emit = defineEmits(["open-call"]);

const isRef = computed(
  () => props.value !== null && typeof props.value === "object" &&
    !Array.isArray(props.value) && typeof props.value.$ref === "string",
);
const isMarker = computed(
  () => props.value !== null && typeof props.value === "object" &&
    !Array.isArray(props.value) && typeof props.value.$unserializable === "string",
);
const container = computed(() => {
  if (props.value === null || typeof props.value !== "object") return null;
  return Array.isArray(props.value) ? "array" : "object";
});
const entries = computed(() => {
  if (container.value === "array") return props.value.map((item, index) => [index, item]);
  if (container.value === "object") return Object.entries(props.value);
  return [];
});
const open = computed(() => props.depth < props.openDepth);
const summary = computed(() => {
  const count = entries.value.length;
  return container.value === "array" ? `陣列 · ${count} 項` : `物件 · ${count} 鍵`;
});
const refLink = computed(() => ({
  kind: "object",
  id: props.value.$ref,
  label: props.value.key || props.value.$ref,
}));
const scalar = computed(() => {
  if (typeof props.value === "string") return JSON.stringify(props.value);
  if (props.value === undefined) return "undefined";
  return String(props.value);
});
</script>

<template>
  <div class="gm-json-tree" :data-depth="depth">
    <p v-if="isRef" class="gm-json-tree__row">
      <span v-if="name !== ''" class="gm-json-tree__key">{{ name }}</span>
      <GmEntityLink :link="refLink" glyph="▸" @open-call="emit('open-call', $event)" />
      <span v-if="value.typeclass" class="gm-json-tree__type">{{ value.typeclass }}</span>
    </p>

    <p v-else-if="isMarker" class="gm-json-tree__row gm-json-tree__row--marker">
      <span v-if="name !== ''" class="gm-json-tree__key">{{ name }}</span>
      <span class="gm-json-tree__marker" :title="`無法轉換為 JSON 的 ${value.$unserializable}`">
        ⟨{{ value.$unserializable }}⟩
      </span>
      <code class="gm-json-tree__repr">{{ value.repr }}</code>
    </p>

    <p v-else-if="container === null" class="gm-json-tree__row">
      <span v-if="name !== ''" class="gm-json-tree__key">{{ name }}</span>
      <code class="gm-json-tree__scalar" :data-type="typeof value">{{ scalar }}</code>
    </p>

    <details v-else class="gm-json-tree__branch" :open="open">
      <summary class="gm-json-tree__summary">
        <span v-if="name !== ''" class="gm-json-tree__key">{{ name }}</span>
        <span class="gm-json-tree__summary-meta">{{ summary }}</span>
      </summary>
      <ul v-if="entries.length" class="gm-json-tree__list">
        <li v-for="[key, item] in entries" :key="key">
          <GmJsonTree
            :value="item"
            :name="key"
            :depth="depth + 1"
            :open-depth="openDepth"
            @open-call="emit('open-call', $event)"
          />
        </li>
      </ul>
      <p v-else class="gm-json-tree__empty">（空）</p>
    </details>
  </div>
</template>

<style scoped>
.gm-json-tree {
  min-width: 0;
}

.gm-json-tree__row {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: var(--sp-2);
  min-width: 0;
  padding: 1px 0;
}

.gm-json-tree__key {
  flex: none;
  font-family: var(--f-mono);
  font-size: var(--text-sm);
  color: var(--paper-500);
}

.gm-json-tree__key::after {
  content: ":";
}

.gm-json-tree__scalar {
  font-family: var(--f-mono);
  font-size: var(--text-sm);
  color: var(--paper-100);
  overflow-wrap: anywhere;
}

.gm-json-tree__scalar[data-type="number"],
.gm-json-tree__scalar[data-type="boolean"] {
  color: var(--gold-300);
}

.gm-json-tree__type {
  font-family: var(--f-mono);
  font-size: var(--text-xs);
  color: var(--paper-600, var(--paper-500));
  overflow-wrap: anywhere;
}

/* A value that cannot be carried as JSON stays visible and unmistakable. */
.gm-json-tree__row--marker {
  padding: 2px var(--sp-2);
  background: color-mix(in srgb, var(--warn) 7%, var(--ink-860));
  border-left: 3px dashed var(--warn);
  border-radius: var(--radius-sm);
}

.gm-json-tree__marker {
  font-family: var(--f-mono);
  font-size: var(--text-xs);
  color: var(--warn);
  white-space: nowrap;
}

.gm-json-tree__repr {
  min-width: 0;
  font-family: var(--f-mono);
  font-size: var(--text-xs);
  color: var(--paper-300);
  overflow-wrap: anywhere;
}

.gm-json-tree__branch {
  min-width: 0;
}

.gm-json-tree__summary {
  display: flex;
  align-items: baseline;
  gap: var(--sp-2);
  cursor: pointer;
  border-radius: var(--radius-sm);
}

.gm-json-tree__summary:focus-visible {
  box-shadow: var(--focus);
  outline: none;
}

.gm-json-tree__summary-meta {
  font-size: var(--text-xs);
  color: var(--paper-500);
}

.gm-json-tree__list {
  margin: var(--sp-1) 0 0;
  padding: 0 0 0 var(--sp-4);
  list-style: none;
  border-left: 1px dashed var(--ink-700);
}

.gm-json-tree__empty {
  padding-left: var(--sp-4);
  font-size: var(--text-xs);
  color: var(--paper-500);
}
</style>
