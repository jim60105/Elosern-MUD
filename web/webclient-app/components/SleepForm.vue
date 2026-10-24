<script setup>
// The rest entry's sleep form (align-sleep-handoff-and-owner-dream;
// redesign-rest-entry): recovery/default or one bounded duration, using the
// existing rest-form input conventions. The second-layer shell's caption
// (睡眠) names the form, so the form carries no caption of its own. Hours are
// presentation-only; the action contract remains bounded seconds. Emits
// exactly one intent: `recover` or `submit(seconds)`.
import { computed, onMounted, ref, watch } from "vue";

const props = defineProps({
  max: { type: Number, default: 43200 },
  autofocus: { type: Boolean, default: true },
  disabled: { type: Boolean, default: false },
});
const emit = defineEmits(["recover", "submit", "close", "error"]);
const raw = ref("1");
const input = ref(null);
const error = ref("");
const maxHours = computed(() => props.max / 3600);

function focusForm() {
  input.value?.focus();
}
onMounted(() => {
  if (props.autofocus) focusForm();
});
watch(
  () => props.autofocus,
  (value) => {
    if (value) focusForm();
  },
);

function submit() {
  if (props.disabled) return;
  const hours = Number(raw.value);
  const seconds = Math.round(hours * 3600);
  if (
    !String(raw.value).trim() ||
    !Number.isFinite(hours) ||
    hours < 1 / 3600 ||
    hours > maxHours.value ||
    seconds < 1 ||
    seconds > props.max
  ) {
    error.value = `請輸入有效時長，最短 1 秒、最長 ${maxHours.value} 小時。`;
    emit("error", error.value);
    return;
  }
  error.value = "";
  emit("submit", seconds);
}

function recover() {
  if (props.disabled) return;
  emit("recover");
}

function onKeyDown(event) {
  event.stopPropagation();
  if (event.key === "Escape") {
    event.preventDefault();
    emit("close");
  }
}
</script>

<template>
  <form
    class="exploration-sleep-form"
    data-testid="sleep-form"
    novalidate
    @submit.prevent="submit"
    @keydown="onKeyDown"
  >
    <button
      type="button"
      class="exploration-sleep-recover"
      data-testid="sleep-form-recovery"
      :disabled="disabled"
      @click="recover"
    >
      睡眠至完全恢復
    </button>
    <label class="exploration-sleep-label">
      或指定時長（小時）
      <input
        ref="input"
        v-model="raw"
        type="number"
        inputmode="decimal"
        :min="1 / 3600"
        :max="maxHours"
        step="any"
        :disabled="disabled"
        aria-label="睡眠時長（小時）"
      />
    </label>
    <small>最長 {{ maxHours }} 小時，可輸入小數。</small>
    <p v-if="error" role="alert">{{ error }}</p>
    <button type="submit" :disabled="disabled">以此時長入睡</button>
  </form>
</template>

<style scoped>
.exploration-sleep-form {
  display: flex;
  flex-direction: column;
  gap: calc(10px * var(--ui-scale));
  padding: calc(14px * var(--ui-scale));
  background: var(--panel-hi);
  border: var(--line);
  border-radius: var(--radius-sm);
  color: var(--paper-100);
}
.exploration-sleep-label {
  display: grid;
  gap: calc(8px * var(--ui-scale));
  color: var(--paper-300);
}
input {
  width: 100%;
  box-sizing: border-box;
  min-width: 0;
  padding: calc(8px * var(--ui-scale));
  color: var(--gold-400);
  background: #101214;
  border: 1px solid var(--gold-600);
  font-size: var(--text-xl);
  text-align: center;
}
button {
  padding: calc(10px * var(--ui-scale));
  color: var(--gold-400);
  background: var(--gold-glow);
  border: 1px solid var(--gold-500);
  border-radius: var(--radius-sm);
  cursor: pointer;
}
input:focus-visible,
button:focus-visible {
  outline: 2px solid var(--gold-400);
  outline-offset: 2px;
}
button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
small {
  color: var(--paper-400);
}
p {
  margin: 0;
  color: var(--warn);
}
</style>
