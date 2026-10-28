<script setup>
// Exact layout-grid values for one interior room (the non-drag path).
// Typing makes a draft that is never written: Enter or blur confirms a
// complete integer as one operation, Escape restores the saved value, and an
// incomplete value keeps the draft with an inline error and writes nothing.
import { computed, onBeforeUnmount, reactive, watch } from "vue";
import { parseIntegerDraft } from "../lib/persistence.js";

const props = defineProps({
  position: { type: Array, required: true },
  roomRef: { type: String, required: true },
});
const emit = defineEmits(["confirm", "drafts"]);

const AXES = [
  { key: "x", index: 0, label: "版面 X" },
  { key: "y", index: 1, label: "版面 Y" },
];
const drafts = reactive({});
const errors = reactive({});

const count = computed(() => Object.keys(drafts).length);
watch(count, (value) => emit("drafts", value), { immediate: true });
// An unmounted form (deselection, or drafts discarded by 載入新版) holds none.
onBeforeUnmount(() => {
  for (const key of Object.keys(drafts)) delete drafts[key];
  emit("drafts", 0);
});
// Another room is a new form; its drafts were resolved or cancelled by now.
watch(
  () => props.roomRef,
  () => {
    for (const key of Object.keys(drafts)) delete drafts[key];
    for (const key of Object.keys(errors)) delete errors[key];
  },
);

function shown(axis) {
  return axis.key in drafts ? drafts[axis.key] : String(props.position[axis.index]);
}

function onInput(axis, event) {
  drafts[axis.key] = event.target.value;
  delete errors[axis.key];
}

function cancel(axis, event) {
  if (!(axis.key in drafts)) return;
  // Escape belongs to this draft, not to the selection.
  event.stopPropagation();
  event.preventDefault();
  delete drafts[axis.key];
  delete errors[axis.key];
  event.target.value = String(props.position[axis.index]);
}

function confirm(axis) {
  if (!(axis.key in drafts)) return;
  const parsed = parseIntegerDraft(drafts[axis.key]);
  if (!parsed.ok) {
    errors[axis.key] = "需要整數。未存檔，草稿保留在此欄位。";
    return;
  }
  delete drafts[axis.key];
  delete errors[axis.key];
  if (parsed.value === props.position[axis.index]) return;
  const next = [...props.position];
  next[axis.index] = parsed.value;
  emit("confirm", next);
}
</script>

<template>
  <div class="layout-fields" data-layout-fields>
    <label v-for="axis in AXES" :key="axis.key" class="layout-field">
      <span class="layout-field__label">{{ axis.label }}</span>
      <input
        class="layout-field__input mono"
        :class="{ 'layout-field__input--draft': axis.key in drafts, 'layout-field__input--error': errors[axis.key] }"
        type="text"
        inputmode="numeric"
        :value="shown(axis)"
        :data-layout-field="axis.key"
        :data-draft="axis.key in drafts ? 'true' : null"
        :aria-invalid="errors[axis.key] ? 'true' : 'false'"
        :aria-describedby="`layout-field-${axis.key}-hint`"
        @input="onInput(axis, $event)"
        @keydown.enter.prevent="confirm(axis)"
        @keydown.esc="cancel(axis, $event)"
        @blur="confirm(axis)"
      />
      <span :id="`layout-field-${axis.key}-hint`" class="layout-field__hint" :data-field-error="errors[axis.key] ? axis.key : null">
        <template v-if="errors[axis.key]">{{ errors[axis.key] }}</template>
        <template v-else-if="axis.key in drafts">草稿 · Enter 確認並存檔 · Esc 取消</template>
      </span>
    </label>
  </div>
</template>
