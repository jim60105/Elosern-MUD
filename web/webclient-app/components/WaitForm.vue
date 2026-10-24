<script setup>
// The rest entry's wait form (redesign-rest-entry design D8): the wait-side
// mirror of SleepForm — one until-state (等待直到黎明) or one bounded
// duration, with SleepForm's validation and keys. The second-layer shell's
// caption (等待) names the form. Hours are presentation-only; the action
// contract remains bounded seconds. Emits exactly one intent: `dawn` or
// `submit(seconds)`.
import { computed, onMounted, ref, watch } from "vue";

const props = defineProps({
  max: { type: Number, default: 43200 },
  autofocus: { type: Boolean, default: true },
  disabled: { type: Boolean, default: false },
});
const emit = defineEmits(["dawn", "submit", "close", "error"]);
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

function dawn() {
  if (props.disabled) return;
  emit("dawn");
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
    class="exploration-wait-form"
    data-testid="wait-form"
    novalidate
    @submit.prevent="submit"
    @keydown="onKeyDown"
  >
    <button
      type="button"
      class="exploration-wait-dawn"
      data-testid="wait-form-dawn"
      :disabled="disabled"
      @click="dawn"
    >
      等待直到黎明
    </button>
    <label class="exploration-wait-label">
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
        aria-label="等待時長（小時）"
      />
    </label>
    <small>最長 {{ maxHours }} 小時，可輸入小數。</small>
    <p v-if="error" role="alert">{{ error }}</p>
    <button type="submit" :disabled="disabled">等待此時長</button>
  </form>
</template>

<style scoped>
.exploration-wait-form {
  display: flex;
  flex-direction: column;
  gap: calc(10px * var(--ui-scale));
  padding: calc(14px * var(--ui-scale));
  background: var(--panel-hi);
  border: var(--line);
  border-radius: var(--radius-sm);
  color: var(--paper-100);
}
.exploration-wait-label {
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
