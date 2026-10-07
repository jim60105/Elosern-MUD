<script setup>
// The runtime list filter bar (gm-portal-s3-runtime-state §6).
//
// One declarative renderer for the per-kind filter vocabulary: a select for
// the enumerated filters, a monospace text input for identifier filters and a
// checkbox for flags. Any committed change restarts pagination — the parent
// owns that, this component only reports the new filter set it should use.
import { computed } from "vue";

const props = defineProps({
  fields: { type: Array, required: true },
  modelValue: { type: Object, default: () => ({}) },
  busy: { type: Boolean, default: false },
  caption: { type: String, default: "查詢條件" },
});

const emit = defineEmits(["update:modelValue", "change"]);

const valueOf = (field) => {
  const current = props.modelValue[field.key];
  if (current !== undefined) return current;
  return field.type === "checkbox" ? false : (field.default ?? "");
};

const activeCount = computed(
  () => props.fields.filter((field) => {
    const value = valueOf(field);
    return value !== "" && value !== false && value !== null;
  }).length,
);

function commit(key, value) {
  const next = { ...props.modelValue };
  if (value === "" || value === false || value === null) delete next[key];
  else next[key] = value;
  emit("update:modelValue", next);
  emit("change", next);
}

function reset() {
  emit("update:modelValue", {});
  emit("change", {});
}

function inputValue(event) {
  return event.target.value;
}

function checkboxValue(event) {
  return event.target.checked;
}

defineExpose({ reset });
</script>

<template>
  <form class="gm-filter-bar" :aria-busy="busy ? 'true' : null" @submit.prevent>
    <p class="gm-filter-bar__caption">
      <span class="gm-filter-bar__title">{{ caption }}</span>
      <span v-if="activeCount" class="gm-filter-bar__count">已套用 {{ activeCount }} 項</span>
      <span v-else class="gm-filter-bar__count">未套用條件</span>
    </p>
    <div class="gm-filter-bar__fields">
      <label v-for="field in fields" :key="field.key" class="gm-filter-bar__field">
        <span class="gm-filter-bar__label">
          {{ field.label }}
          <span v-if="field.required" class="gm-filter-bar__required" title="必填">＊</span>
        </span>
        <select
          v-if="field.type === 'select'"
          class="gm-filter-bar__control"
          :name="field.key"
          :value="valueOf(field)"
          @change="commit(field.key, inputValue($event))"
        >
          <option v-for="option in field.options" :key="option.value" :value="option.value">
            {{ option.label }}
          </option>
        </select>
        <input
          v-else-if="field.type === 'checkbox'"
          class="gm-filter-bar__checkbox"
          type="checkbox"
          :name="field.key"
          :checked="valueOf(field)"
          @change="commit(field.key, checkboxValue($event))"
        >
        <input
          v-else
          class="gm-filter-bar__control"
          :class="{ 'gm-mono': field.mono }"
          type="text"
          :name="field.key"
          :placeholder="field.placeholder ?? ''"
          :value="valueOf(field)"
          @change="commit(field.key, inputValue($event))"
        >
      </label>
    </div>
    <button
      type="button"
      class="ui-btn ui-btn--ghost ui-btn--sm gm-filter-bar__reset"
      :aria-disabled="activeCount ? null : 'true'"
      @click="activeCount && reset()"
    >
      重設條件
    </button>
  </form>
</template>

<style scoped>
.gm-filter-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: var(--sp-3) var(--sp-5);
  padding: var(--sp-3) var(--sp-4);
  background: var(--ink-860);
  border: var(--line);
  border-radius: var(--radius);
}

.gm-filter-bar__caption {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 7em;
}

.gm-filter-bar__title {
  font-family: var(--f-serif);
  font-size: var(--text-md);
  color: var(--paper-100);
}

.gm-filter-bar__count {
  font-size: var(--text-xs);
  letter-spacing: 0.08em;
  color: var(--paper-500);
}

.gm-filter-bar__fields {
  display: flex;
  flex: 1 1 24em;
  flex-wrap: wrap;
  gap: var(--sp-3) var(--sp-4);
}

.gm-filter-bar__field {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 8em;
}

.gm-filter-bar__label {
  font-size: var(--text-xs);
  letter-spacing: 0.08em;
  color: var(--paper-400);
}

.gm-filter-bar__required {
  color: var(--warn);
}

.gm-filter-bar__control {
  min-height: 32px;
  padding: 0 var(--sp-2);
  font-size: var(--text-sm);
  color: var(--paper-100);
  background: var(--ink-950);
  border: var(--line);
  border-radius: var(--radius-sm);
}

.gm-filter-bar__control:focus-visible {
  box-shadow: var(--focus);
  outline: none;
}

.gm-filter-bar__control::placeholder {
  color: var(--paper-600, var(--paper-500));
}

.gm-filter-bar__checkbox {
  width: 18px;
  height: 18px;
  margin-top: var(--sp-2);
  accent-color: var(--gold-500);
}

.gm-filter-bar__reset {
  margin-left: auto;
}
</style>
