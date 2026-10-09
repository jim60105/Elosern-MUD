<script setup>
// Prototype of ChoiceCard (spec §4.2): the presentational card extracted
// from DialogueChoices — crest, corner brackets, digit-badged rows, and one
// keyboard composite — shared by the verb card, the wait menu, the
// suggestions list, and the presence overflow list. Reference only.
//
// Keys: ArrowUp / ArrowDown wrap, digits 1–N pick, Enter / Space activate,
// Escape backs out. The last row is always ✕ 返回.
import { computed, nextTick, onMounted, ref } from "vue";

const props = defineProps({
  caption: { type: String, default: null },
  rows: { type: Array, required: true }, // [{key, label}]
  backLabel: { type: String, default: "返回" },
});
const emit = defineEmits(["pick", "back"]);

const listEl = ref(null);
const allRows = computed(() => [...props.rows, { key: "__back", label: props.backLabel, back: true }]);
const active = ref(0);

function activate(index) {
  const row = allRows.value[index];
  if (!row) {
    return;
  }
  if (row.back) {
    emit("back");
  } else {
    emit("pick", row.key);
  }
}

function onKeyDown(event) {
  const n = allRows.value.length;
  if (event.key === "ArrowDown") {
    active.value = (active.value + 1) % n;
  } else if (event.key === "ArrowUp") {
    active.value = (active.value - 1 + n) % n;
  } else if (event.key === "Enter" || event.key === " ") {
    activate(active.value);
  } else if (event.key === "Escape") {
    emit("back");
  } else if (/^[1-9]$/.test(event.key) && Number(event.key) <= props.rows.length) {
    activate(Number(event.key) - 1);
  } else {
    return;
  }
  event.preventDefault();
  event.stopPropagation();
}

onMounted(async () => {
  await nextTick();
  listEl.value?.focus({ preventScroll: true });
});
</script>

<template>
  <div
    ref="listEl"
    class="card"
    tabindex="0"
    role="listbox"
    :aria-activedescendant="`card-row-${active}`"
    @keydown="onKeyDown"
  >
    <span class="card__corners" aria-hidden="true"><i /><i /><i /><i /></span>
    <div v-if="caption" class="card__caption">{{ caption }}</div>
    <div class="card__rows">
      <template v-for="(row, i) in allRows" :key="row.key">
        <div v-if="row.back" class="card__rule" />
        <div
          :id="`card-row-${i}`"
          class="card__row"
          :class="{ 'card__row--active': active === i, 'card__row--back': row.back }"
          :style="{ '--row-index': i }"
          role="option"
          :aria-selected="active === i"
          @pointerenter="active = i"
          @click="activate(i)"
        >
          <span class="card__caret">{{ active === i ? "▸" : "" }}</span>
          <span class="card__badge">{{ row.back ? "✕" : i + 1 }}</span>
          <span class="card__label">{{ row.label }}</span>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.card {
  position: relative;
  width: min(calc(680px * var(--ui-scale)), 46vw);
  display: flex;
  flex-direction: column;
  background:
    radial-gradient(120% 60% at 50% 0%, rgba(185, 154, 96, 0.1), transparent 70%),
    linear-gradient(180deg, rgba(27, 25, 29, 0.95), rgba(12, 13, 17, 0.95));
  border: 1px solid rgba(185, 154, 96, 0.45);
  border-radius: var(--radius);
  box-shadow: var(--shadow-lg), inset 0 0 0 1px rgba(0, 0, 0, 0.55);
  backdrop-filter: blur(calc(6px * var(--ui-scale)));
  outline: none;
  animation: card-in var(--motion-reveal) var(--ease-standard) backwards;
}
.card:focus-visible {
  border-color: rgba(228, 200, 142, 0.72);
}
.card::before {
  content: "";
  position: absolute;
  left: 18%;
  right: 18%;
  top: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--gold-400), transparent);
}
.card::after {
  content: "";
  position: absolute;
  left: 50%;
  top: calc(-3px * var(--ui-scale));
  width: calc(6px * var(--ui-scale));
  height: calc(6px * var(--ui-scale));
  margin-left: calc(-3px * var(--ui-scale));
  transform: rotate(45deg);
  background: var(--gold-400);
}
.card__corners i {
  position: absolute;
  width: calc(10px * var(--ui-scale));
  height: calc(10px * var(--ui-scale));
  border-color: var(--gold-500);
  border-style: solid;
  opacity: 0.55;
}
.card__corners i:nth-child(1) { left: 3px; top: 3px; border-width: 1px 0 0 1px; }
.card__corners i:nth-child(2) { right: 3px; top: 3px; border-width: 1px 1px 0 0; }
.card__corners i:nth-child(3) { left: 3px; bottom: 3px; border-width: 0 0 1px 1px; }
.card__corners i:nth-child(4) { right: 3px; bottom: 3px; border-width: 0 1px 1px 0; }
.card__caption {
  padding: calc(12px * var(--ui-scale)) calc(20px * var(--ui-scale)) 0;
  font: var(--text-xs) / 1.4 var(--f-sans);
  letter-spacing: 0.3em;
  color: var(--gold-500);
  text-align: center;
}
.card__rows {
  display: flex;
  flex-direction: column;
  gap: calc(4px * var(--ui-scale));
  padding: calc(12px * var(--ui-scale)) calc(10px * var(--ui-scale));
}
.card__rule {
  height: 1px;
  margin: calc(4px * var(--ui-scale)) calc(30px * var(--ui-scale));
  background: rgba(85, 82, 75, 0.6);
}
.card__row {
  display: grid;
  grid-template-columns: calc(16px * var(--ui-scale)) calc(30px * var(--ui-scale)) 1fr;
  align-items: center;
  gap: calc(10px * var(--ui-scale));
  min-height: calc(44px * var(--ui-scale));
  padding: 0 calc(12px * var(--ui-scale));
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  color: var(--paper-100);
  font: var(--text-base) / 1.3 var(--f-serif);
  cursor: pointer;
  animation: row-in var(--motion-reveal) var(--ease-enter) calc(var(--motion-stagger, 40ms) * var(--row-index, 0)) backwards;
}
.card__row--active {
  background: linear-gradient(90deg, rgba(185, 154, 96, 0.32), rgba(185, 154, 96, 0.12));
  border-color: rgba(228, 200, 142, 0.6);
  color: var(--paper-50);
}
.card__caret {
  color: var(--gold-400);
  font-size: var(--text-xs);
}
.card__badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: calc(28px * var(--ui-scale));
  height: calc(28px * var(--ui-scale));
  border-radius: 50%;
  border: 1px solid var(--gold-500);
  color: var(--gold-300);
  font: var(--text-xs) / 1 var(--f-sans);
}
.card__row--active .card__badge {
  background: var(--gold-400);
  color: var(--ink-950);
}
.card__row--back .card__badge {
  border-color: var(--seal-600);
  color: var(--seal-400);
}
@keyframes card-in {
  from { opacity: 0; }
}
@keyframes row-in {
  from { opacity: 0; transform: translateY(6px); }
}
</style>
