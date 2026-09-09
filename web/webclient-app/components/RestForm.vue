<script setup>
// Hours are presentation-only; the action contract remains bounded seconds.
import { computed, onMounted, ref, watch } from "vue";

const props = defineProps({
  max: { type: Number, default: 43200 },
  autofocus: { type: Boolean, default: true },
  disabled: { type: Boolean, default: false },
  label: { type: String, default: "開始休息" },
});
const emit = defineEmits(["submit", "close", "error"]);
const raw = ref("1");
const input = ref(null);
const error = ref("");
const maxHours = computed(() => props.max / 3600);
function focusForm() { input.value?.focus(); }
onMounted(() => { if (props.autofocus) focusForm(); });
watch(() => props.autofocus, (value) => { if (value) focusForm(); });
function submit() {
  if (props.disabled) return;
  const hours = Number(raw.value);
  const seconds = Math.round(hours * 3600);
  if (!String(raw.value).trim() || !Number.isFinite(hours) || hours < 1 / 3600 || hours > maxHours.value || seconds < 1 || seconds > props.max) {
    error.value = `請輸入有效時長，最短 1 秒、最長 ${maxHours.value} 小時。`;
    emit("error", error.value);
    return;
  }
  error.value = "";
  emit("submit", seconds);
}
function onKeyDown(event) {
  // Keep native editing and Tab behavior; claim keys before the dock router.
  event.stopPropagation();
  if (event.key === "Escape") {
    event.preventDefault();
    emit("close");
  }
}
</script>

<template>
  <form class="exploration-rest-form" data-testid="exploration-rest-form" novalidate @submit.prevent="submit" @keydown="onKeyDown">
    <label class="exploration-rest-label">
      時長（小時）
      <input ref="input" v-model="raw" type="number" inputmode="decimal" :min="1 / 3600" :max="maxHours" step="any" :disabled="disabled" aria-label="時長（小時）" />
    </label>
    <small>最長 {{ maxHours }} 小時，可輸入小數。</small>
    <p v-if="error" role="alert">{{ error }}</p>
    <button type="submit" :disabled="disabled">{{ label }}</button>
  </form>
</template>

<style scoped>
.exploration-rest-form { display: flex; flex-direction: column; gap: 10px; padding: 14px; background: var(--panel-hi); border: var(--line); border-radius: var(--radius-sm); color: var(--paper-100); }
.exploration-rest-label { display: grid; gap: 8px; color: var(--paper-300); }
input { width: 100%; box-sizing: border-box; min-width: 0; padding: 8px; color: var(--gold-400); background: #101214; border: 1px solid var(--gold-600); font-size: 20px; }
button { padding: 10px; color: var(--gold-400); background: var(--gold-glow); border: 1px solid var(--gold-500); border-radius: 4px; cursor: pointer; }
input:focus-visible, button:focus-visible { outline: 2px solid var(--gold-400); outline-offset: 2px; }
button:disabled { opacity: .5; cursor: not-allowed; }
small { color: var(--paper-400); }
p { margin: 0; color: var(--warn); }
</style>
