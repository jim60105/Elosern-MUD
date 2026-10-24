<script setup>
// Prototype of the new wait form: the wait-side mirror of SleepForm (one
// until-state button, then one bounded duration). Reference only; it emits
// the payloads the real form would dispatch through `explore.wait`.
import { computed, onMounted, ref } from "vue";

const props = defineProps({
  max: { type: Number, default: 43200 },
  disabled: { type: Boolean, default: false },
});
const emit = defineEmits(["dawn", "submit", "close"]);
const raw = ref("1");
const input = ref(null);
const error = ref("");
const maxHours = computed(() => props.max / 3600);

onMounted(() => input.value?.focus());

function submit() {
  if (props.disabled) return;
  const hours = Number(raw.value);
  const seconds = Math.round(hours * 3600);
  if (!String(raw.value).trim() || !Number.isFinite(hours) || seconds < 1 || seconds > props.max) {
    error.value = `請輸入有效時長，最短 1 秒、最長 ${maxHours.value} 小時。`;
    return;
  }
  error.value = "";
  emit("submit", seconds);
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
  <form class="proto-wait-form" novalidate @submit.prevent="submit" @keydown="onKeyDown">
    <button type="button" class="proto-wait-form__dawn" :disabled="disabled" @click="emit('dawn')">
      等待直到黎明
    </button>
    <label class="proto-wait-form__label">
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
/* The same rules as SleepForm, so the two second-layer forms read as one
   pair. */
.proto-wait-form {
  display: flex;
  flex-direction: column;
  gap: calc(10px * var(--ui-scale));
  padding: calc(4px * var(--ui-scale)) calc(6px * var(--ui-scale)) 0;
  color: var(--paper-100);
}
.proto-wait-form__label {
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
