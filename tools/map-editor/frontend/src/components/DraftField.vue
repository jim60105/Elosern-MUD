<script setup>
// One inspector field with the draft contract of frontend design §5.3.
// Typing makes a draft that is never written: Enter (Ctrl/⌘+Enter in a
// multiline field) or blur confirms a complete value as one operation, Esc
// restores the saved value, and an incomplete value keeps the draft with an
// inline error (aria-describedby) and writes nothing. A select confirms on
// change. The parent receives the parsed value; the service and the core
// schema decide whether it is valid. Every label carries its frame and unit.
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { parseIntegerDraft } from "../lib/persistence.js";

const props = defineProps({
  label: { type: String, required: true },
  fieldKey: { type: String, required: true },
  value: { type: [String, Number, Array, Boolean, null], default: null },
  // int | text | textarea | nullable | list | lines | select
  type: { type: String, default: "text" },
  unit: { type: String, default: null },
  options: { type: Array, default: () => [] },
  note: { type: String, default: null },
});
const emit = defineEmits(["confirm", "drafts"]);

const draft = ref(null);
const error = ref(null);
const id = computed(() => `field-${props.fieldKey.replace(/[^a-z0-9_-]/gi, "-")}`);

watch(
  () => draft.value !== null,
  (open) => emit("drafts", open ? 1 : 0),
  { immediate: true },
);
// An unmounted field (another selection, or drafts discarded by 載入新版)
// holds no draft.
onBeforeUnmount(() => emit("drafts", 0));
// A new saved value for the same field (own save or adopted change) keeps an
// open draft; a closed field shows the new value.

function format(value) {
  if (value === null || value === undefined) return "";
  if (props.type === "list") return value.join(", ");
  if (props.type === "lines") return value.join("\n");
  return String(value);
}

const shown = computed(() => (draft.value !== null ? draft.value : format(props.value)));

function parse(text) {
  switch (props.type) {
    case "int": {
      const parsed = parseIntegerDraft(text);
      return parsed.ok ? parsed : { ok: false, message: "需要整數。未存檔，草稿保留在此欄位。" };
    }
    case "nullable": {
      const trimmed = text.trim();
      return { ok: true, value: trimmed ? trimmed : null };
    }
    case "list":
      return { ok: true, value: text.split(/[,，\s]+/).map((item) => item.trim()).filter(Boolean) };
    case "lines":
      return { ok: true, value: text.split("\n").map((item) => item.trim()).filter(Boolean) };
    default:
      return { ok: true, value: text };
  }
}

function same(a, b) {
  return JSON.stringify(a ?? null) === JSON.stringify(b ?? null);
}

function onInput(event) {
  draft.value = event.target.value;
  error.value = null;
}

function cancel(event) {
  if (draft.value === null) return;
  // Escape belongs to this draft, not to the selection.
  event.stopPropagation();
  event.preventDefault();
  draft.value = null;
  error.value = null;
  event.target.value = format(props.value);
}

function confirm() {
  if (draft.value === null) return;
  const parsed = parse(draft.value);
  if (!parsed.ok) {
    error.value = parsed.message;
    return;
  }
  draft.value = null;
  error.value = null;
  if (!same(parsed.value, props.value)) emit("confirm", parsed.value);
}

function onKeydown(event) {
  if (event.key === "Escape") {
    cancel(event);
    return;
  }
  if (event.key !== "Enter" || event.isComposing) return;
  if (props.type === "textarea" || props.type === "lines") {
    if (!(event.ctrlKey || event.metaKey)) return;
  }
  event.preventDefault();
  confirm();
}

function onSelect(event) {
  const raw = event.target.value;
  const value = raw === "" ? null : raw;
  if (!same(value, props.value)) emit("confirm", value);
}
</script>

<template>
  <label class="draft-field" :data-field-key="fieldKey">
    <span class="draft-field__label">{{ label }}<span v-if="unit" class="draft-field__unit">{{ unit }}</span></span>
    <select
      v-if="type === 'select'"
      class="draft-field__input"
      :value="value ?? ''"
      :data-field-input="fieldKey"
      :aria-describedby="`${id}-hint`"
      @change="onSelect"
    >
      <option v-for="option in options" :key="option.value ?? ''" :value="option.value ?? ''">{{ option.label }}</option>
    </select>
    <textarea
      v-else-if="type === 'textarea' || type === 'lines'"
      class="draft-field__input"
      :class="{ 'draft-field__input--draft': draft !== null, 'draft-field__input--error': error }"
      rows="3"
      :value="shown"
      :data-field-input="fieldKey"
      :data-draft="draft !== null ? 'true' : null"
      :aria-invalid="error ? 'true' : 'false'"
      :aria-describedby="`${id}-hint`"
      @input="onInput"
      @keydown="onKeydown"
      @blur="confirm"
    />
    <input
      v-else
      class="draft-field__input"
      :class="{ 'draft-field__input--draft': draft !== null, 'draft-field__input--error': error, mono: type === 'int' }"
      type="text"
      :inputmode="type === 'int' ? 'numeric' : null"
      :value="shown"
      :data-field-input="fieldKey"
      :data-draft="draft !== null ? 'true' : null"
      :aria-invalid="error ? 'true' : 'false'"
      :aria-describedby="`${id}-hint`"
      @input="onInput"
      @keydown="onKeydown"
      @blur="confirm"
    />
    <span :id="`${id}-hint`" class="draft-field__hint" :data-field-error="error ? fieldKey : null">
      <template v-if="error">{{ error }}</template>
      <template v-else-if="draft !== null">草稿 · {{ type === 'textarea' || type === 'lines' ? 'Ctrl+Enter' : 'Enter' }} 確認並存檔 · Esc 取消</template>
      <template v-else-if="note">{{ note }}</template>
    </span>
  </label>
</template>
