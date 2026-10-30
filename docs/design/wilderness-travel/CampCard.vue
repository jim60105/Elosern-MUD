<script setup>
// The camp card (prototype, sub-project 3): one decision. Two choices —
// 睡到天亮 and 睡到精力全滿 — each stating when the party wakes and with how
// much 精力, the remembered 夢境協作 checkbox, and one confirmation. Keys:
// 1 / 2 pick, D toggles the dream checkbox, Enter confirms, Esc cancels.
import { computed, onMounted, ref } from "vue";
import { RESERVE_FULL, formatClock } from "./travel-model.js";

const props = defineProps({
  place: { type: String, required: true },
  minutes: { type: Number, required: true },
  phase: { type: String, required: true },
  options: { type: Array, required: true },
  initialChoice: { type: String, default: null },
  dream: { type: Boolean, default: false },
});
const emit = defineEmits(["confirm", "cancel"]);

const choice = ref(props.initialChoice ?? props.options[0].key);
const dreamOn = ref(props.dream);
const card = ref(null);

const picked = computed(() => props.options.find((o) => o.key === choice.value));

function pct(r) {
  return Math.round((r / RESERVE_FULL) * 100);
}

function onKey(event) {
  if (event.key === "1" || event.key === "2") {
    const o = props.options[Number(event.key) - 1];
    if (o) choice.value = o.key;
  } else if (event.key === "d" || event.key === "D") {
    dreamOn.value = !dreamOn.value;
  } else if (event.key === "Enter") {
    event.preventDefault();
    emit("confirm", { choice: choice.value, dream: dreamOn.value });
  } else if (event.key === "Escape") {
    event.preventDefault();
    emit("cancel");
  }
}

onMounted(() => card.value?.focus({ preventScroll: true }));
</script>

<template>
  <section
    ref="card"
    class="choice-card camp-card"
    tabindex="-1"
    role="dialog"
    aria-label="紮營"
    @keydown="onKey"
  >
    <p class="choice-card__caption">紮營</p>
    <header class="camp-card__head">
      <h2 class="camp-card__title">在{{ place }}過夜</h2>
      <p class="camp-card__now">{{ formatClock(minutes).label }}</p>
    </header>

    <div class="camp-card__options" role="radiogroup" aria-label="睡到何時">
      <button
        v-for="(o, i) in options"
        :key="o.key"
        type="button"
        role="radio"
        class="camp-opt"
        :aria-checked="choice === o.key ? 'true' : 'false'"
        @click="choice = o.key"
      >
        <span class="camp-opt__digit">{{ i + 1 }}</span>
        <span class="camp-opt__label">{{ o.label }}</span>
        <span class="camp-opt__when">{{ formatClock(o.wake).text }} 醒來</span>
        <span class="camp-opt__note">{{ o.note }}</span>
      </button>
    </div>

    <ul class="camp-card__members" aria-label="醒來時的精力">
      <li v-for="m in picked.members" :key="m.id">
        <span class="camp-card__name">{{ m.name }}</span>
        <span class="camp-card__bar">
          <span class="camp-card__from" :style="{ width: `${pct(m.from)}%` }"></span>
          <span class="camp-card__to" :style="{ width: `${pct(m.to)}%` }"></span>
        </span>
        <span class="camp-card__pct">{{ pct(m.from) }}% → <b>{{ pct(m.to) }}%</b></span>
      </li>
    </ul>

    <label class="camp-card__dream">
      <input v-model="dreamOn" type="checkbox" />
      <span class="camp-card__check" aria-hidden="true"></span>
      進入夢境協作<small>（記住這個選擇）</small>
    </label>

    <footer class="camp-card__foot">
      <button type="button" class="leg-btn" @click="emit('cancel')">取消 <kbd>Esc</kbd></button>
      <button type="button" class="leg-btn leg-btn--primary" @click="emit('confirm', { choice, dream: dreamOn })">
        全隊紮營 <kbd>Enter</kbd>
      </button>
    </footer>
  </section>
</template>

<style>
.camp-card {
  gap: calc(12px * var(--ui-scale));
  padding: 0 calc(24px * var(--ui-scale)) calc(18px * var(--ui-scale));
  overflow-y: auto;
}
.camp-card__head {
  text-align: center;
}
.camp-card__title {
  margin: calc(4px * var(--ui-scale)) 0 0;
  font: var(--text-2xl)/1.3 var(--f-display);
  color: var(--paper-50);
}
.camp-card__now {
  margin: calc(2px * var(--ui-scale)) 0 0;
  font: var(--text-xs)/1.3 var(--f-sans);
  color: var(--paper-400);
}
.camp-card__options {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: calc(10px * var(--ui-scale));
}
.camp-opt {
  position: relative;
  display: grid;
  gap: calc(4px * var(--ui-scale));
  justify-items: start;
  text-align: left;
  padding: calc(12px * var(--ui-scale)) calc(14px * var(--ui-scale));
  border-radius: calc(6px * var(--ui-scale));
  border: 1px solid rgba(143, 113, 60, 0.45);
  background: rgba(11, 13, 16, 0.55);
  color: var(--paper-300);
  cursor: pointer;
  transition: border-color var(--motion-fast), background var(--motion-fast);
}
.camp-opt[aria-checked="true"] {
  border-color: var(--gold-400);
  background: linear-gradient(180deg, rgba(185, 154, 96, 0.22), rgba(143, 113, 60, 0.1));
  box-shadow: inset 0 0 0 1px rgba(228, 200, 142, 0.25);
}
.camp-opt:focus-visible {
  outline: 2px solid var(--gold-400);
  outline-offset: 2px;
}
.camp-opt__digit {
  position: absolute;
  right: calc(10px * var(--ui-scale));
  top: calc(8px * var(--ui-scale));
  font: var(--text-xs)/1 var(--f-sans);
  color: var(--paper-700);
}
.camp-opt__label {
  font: var(--text-lg)/1.2 var(--f-serif);
  color: var(--paper-50);
}
.camp-opt__when {
  font: var(--text-sm)/1.2 var(--f-sans);
  color: var(--gold-300);
  font-variant-numeric: tabular-nums;
}
.camp-opt__note {
  font: var(--text-xs)/1.35 var(--f-sans);
  color: var(--paper-400);
}
.camp-card__members {
  display: grid;
  gap: calc(6px * var(--ui-scale));
  margin: 0;
  padding: 0;
  list-style: none;
}
.camp-card__members li {
  display: grid;
  grid-template-columns: calc(56px * var(--ui-scale)) 1fr auto;
  align-items: center;
  gap: calc(10px * var(--ui-scale));
  font: var(--text-xs)/1.2 var(--f-sans);
  color: var(--paper-400);
}
.camp-card__name {
  font-family: var(--f-serif);
  color: var(--paper-100);
}
.camp-card__bar {
  position: relative;
  height: calc(6px * var(--ui-scale));
  border-radius: 3px;
  background: rgba(36, 38, 42, 0.95);
  overflow: hidden;
}
.camp-card__to,
.camp-card__from {
  position: absolute;
  inset: 0 auto 0 0;
}
.camp-card__to {
  background: repeating-linear-gradient(90deg, rgba(216, 168, 62, 0.45) 0 4px, rgba(216, 168, 62, 0.25) 4px 6px);
}
.camp-card__from {
  z-index: 1;
  background: var(--vit-sp);
}
.camp-card__pct {
  font-variant-numeric: tabular-nums;
}
.camp-card__pct b {
  color: var(--gold-300);
  font-weight: 500;
}
.camp-card__dream {
  display: flex;
  align-items: center;
  gap: calc(10px * var(--ui-scale));
  font: var(--text-sm)/1.2 var(--f-serif);
  color: var(--paper-200);
  cursor: pointer;
}
.camp-card__dream input {
  position: absolute;
  opacity: 0;
}
.camp-card__dream small {
  font: var(--text-xs)/1 var(--f-sans);
  color: var(--paper-500);
}
.camp-card__check {
  width: calc(18px * var(--ui-scale));
  height: calc(18px * var(--ui-scale));
  border-radius: 4px;
  border: 1px solid var(--gold-600);
  background: rgba(11, 13, 16, 0.7);
  display: grid;
  place-items: center;
}
.camp-card__dream input:checked + .camp-card__check::after {
  content: "";
  width: 55%;
  height: 30%;
  border-left: 2px solid var(--gold-300);
  border-bottom: 2px solid var(--gold-300);
  transform: rotate(-45deg) translate(1px, -1px);
}
.camp-card__dream input:focus-visible + .camp-card__check {
  outline: 2px solid var(--gold-400);
  outline-offset: 2px;
}
.camp-card__foot {
  display: grid;
  grid-template-columns: 1fr 1.6fr;
  gap: calc(10px * var(--ui-scale));
}
</style>
