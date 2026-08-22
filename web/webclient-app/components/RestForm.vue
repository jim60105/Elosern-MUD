<script setup>
// RestForm (C4, webclient-vue-10-wire-views-browser): the keyboard-operable
// bounded rest-duration form. It mirrors the legacy `exploration-rest-form`
// surface: a div-based keyboard input (not a real <input>) collecting a
// 1..max seconds value. The browser collects the value; the server parses
// and validates it — the browser never advances its own clock.
//
// Keyboard isolation (Phase-0 audit §2.3): the form binds a capture-phase
// keydown listener so the global KeyboardRouter (the C2 bridge's document
// listener) does not claim the form's digits / Backspace / Escape / Enter /
// slash keys; a slash while the form is open must never toggle the command
// drawer (the legacy isEditingRestForm gate).
import { onBeforeUnmount, onMounted, ref } from "vue";

const props = defineProps({
  // The bounded maximum rest seconds (the legacy 43200s = 12h cap).
  max: { type: Number, default: 43200 },
});

const emit = defineEmits(["submit", "close", "error"]);

const MAX_DIGITS = 8;
const raw = ref("");

function onKeyDown(event) {
  const key = event.key;
  if (key.length === 1 && key >= "0" && key <= "9") {
    event.preventDefault();
    event.stopPropagation();
    if (raw.value.length < MAX_DIGITS) {
      raw.value += key;
    }
    return;
  }
  if (key === "Backspace") {
    event.preventDefault();
    event.stopPropagation();
    raw.value = raw.value.slice(0, -1);
    return;
  }
  if (key === "Escape") {
    event.preventDefault();
    event.stopPropagation();
    emit("close");
    return;
  }
  if (key === "Enter") {
    event.preventDefault();
    event.stopPropagation();
    const seconds = parseInt(raw.value, 10);
    if (!raw.value || !Number.isInteger(seconds) || seconds < 1 || seconds > props.max) {
      emit("error", `請輸入 1～${props.max} 的有效秒數。`);
      return;
    }
    emit("submit", seconds);
    raw.value = "";
    return;
  }
  if (key === "/") {
    // The slash gate: while the rest form is open, a slash is ordinary text
    // input in an editable control and must never toggle the command drawer.
    event.preventDefault();
    event.stopPropagation();
    return;
  }
}

function focusForm() {
  const el = document.querySelector('[data-testid="exploration-rest-form"]');
  if (el) el.focus();
}

onMounted(focusForm);
</script>

<template>
  <div
    class="exploration-rest-form"
    data-testid="exploration-rest-form"
    tabindex="0"
    @keydown="onKeyDown"
  >
    <div class="exploration-rest-label">
      休息秒數（1～{{ max }}）：
    </div>
    <div class="exploration-rest-value">{{ raw === "" ? "＿" : raw }}</div>
  </div>
</template>

<style scoped>
.exploration-rest-form {
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
  padding: var(--sp-2) var(--sp-3);
  background: var(--panel-hi);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  font-family: var(--f-sans);
  font-size: var(--text-sm);
  color: var(--paper-100);
}

.exploration-rest-form:focus {
  outline: 2px solid var(--seal-500);
  outline-offset: 1px;
}

.exploration-rest-label {
  color: var(--paper-500);
}

.exploration-rest-value {
  font-family: var(--f-mono, var(--f-sans));
  color: var(--paper-100);
}
</style>
