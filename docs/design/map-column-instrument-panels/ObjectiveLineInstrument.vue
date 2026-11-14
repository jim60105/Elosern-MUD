<script setup>
// ObjectiveLineInstrument (design prototype, reference only): the objective
// line as its own instrument panel (instrument-panel.css): no box, a
// feathered ink ground and one brass fitting at its top-right corner. The
// 目標 word moves into the region's accessible name: the visible width goes
// to the objective itself, which otherwise truncates in a 250px column. A
// lozenge states the completion state by shape and hue (open while
// in progress, filled with a check once reached); a counted objective
// restates its quantity as one tick per unit under the line, beside the
// tabular `n / m` readout. Same `rows` prop as the live ObjectiveTracker.
import { computed } from "vue";
import "./instrument-panel.css";

const props = defineProps({
  rows: { type: Array, default: () => [] },
});

// One tick per unit reads up to this many; above it the quantity is one
// continuous stroke so the ticks never shrink below a readable width.
const TICK_LIMIT = 12;

const safeRows = computed(() => (Array.isArray(props.rows) ? props.rows : []));
const first = computed(() => safeRows.value[0] || null);
const rest = computed(() => Math.max(0, safeRows.value.length - 1));

const counted = computed(() => Number(first.value?.objective_quantity) > 1);
const quantity = computed(() => Number(first.value?.objective_quantity) || 0);
const progress = computed(() => {
  const value = Number(first.value?.stage_progress) || 0;
  return Math.max(0, Math.min(quantity.value, value));
});
const done = computed(() => {
  const row = first.value;
  return (
    typeof row?.stage_progress === "number" &&
    typeof row?.objective_quantity === "number" &&
    row.stage_progress >= row.objective_quantity
  );
});
const ticked = computed(() => counted.value && quantity.value <= TICK_LIMIT);
const ratio = computed(() => (quantity.value > 0 ? progress.value / quantity.value : 0));
</script>

<template>
  <div
    v-if="first"
    class="icp-panel icp-obj"
    :class="{ 'icp-obj--done': done }"
    data-testid="objective-tracker"
    role="region"
    aria-label="目標"
  >
    <div class="icp-obj__line">
      <span class="icp-obj__state" role="img" :aria-label="done ? '已達成' : '進行中'">
        <svg viewBox="0 0 12 12" aria-hidden="true">
          <path class="icp-obj__lozenge" d="M6 .9 11.1 6 6 11.1 .9 6Z" />
          <path v-if="done" class="icp-obj__check" d="M3.6 6.2 5.4 7.9 8.5 4.4" />
        </svg>
      </span>
      <span class="icp-obj__text" :title="first.objective_line">{{ first.objective_line }}</span>
      <span v-if="counted" class="icp-obj__count">
        <b>{{ first.stage_progress }}</b><i>/ {{ first.objective_quantity }}</i>
      </span>
      <span v-else-if="first.reward_copper != null" class="icp-obj__reward">+{{ first.reward_copper }}</span>
      <span
        v-if="rest > 0"
        class="icp-obj__more"
        role="img"
        :aria-label="`另有 ${rest} 項追蹤目標`"
        :title="`另有 ${rest} 項追蹤目標`"
      >
        <svg viewBox="0 0 12 12" aria-hidden="true"><path d="M1.5 3h9M1.5 6h9M1.5 9h9" /></svg>{{ rest }}
      </span>
    </div>
    <div v-if="ticked" class="icp-obj__ticks" aria-hidden="true">
      <span
        v-for="n in quantity"
        :key="n"
        class="icp-obj__tick"
        :class="{ 'icp-obj__tick--on': n <= progress }"
      ></span>
    </div>
    <div v-else-if="counted" class="icp-obj__stroke" aria-hidden="true">
      <span class="icp-obj__fill" :style="{ width: `${ratio * 100}%` }"></span>
    </div>
  </div>
</template>

<style scoped>
.icp-obj {
  box-sizing: border-box;
  flex: none;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: calc(5px * var(--ui-scale));
  font-family: var(--f-serif);
  color: var(--paper-100);
}
/* One phrase set from the spine: it ends at the right edge and grows to the
   left, never stretched across the column. */
.icp-obj__line {
  max-width: 100%;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: calc(8px * var(--ui-scale));
  white-space: nowrap;
  text-shadow: 0 1px 1px rgba(0, 0, 0, 0.8), 0 0 calc(8px * var(--ui-scale)) rgba(11, 13, 16, 0.7);
}
.icp-obj__state {
  flex: none;
  display: grid;
  place-items: center;
  width: calc(12px * var(--ui-scale));
  height: calc(12px * var(--ui-scale));
}
.icp-obj__state svg {
  width: 100%;
  height: 100%;
  overflow: visible;
  filter: drop-shadow(0 1px 1px rgba(0, 0, 0, 0.8));
}
.icp-obj__lozenge {
  fill: none;
  stroke: var(--gold-400);
  stroke-width: 1.2;
}
.icp-obj__check {
  fill: none;
  stroke: var(--ink-950);
  stroke-width: 1.6;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.icp-obj--done .icp-obj__lozenge {
  fill: var(--buff);
  stroke: var(--buff);
}
.icp-obj__text {
  flex: 0 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: var(--text-sm);
  line-height: 1.3;
  letter-spacing: 0.04em;
}
.icp-obj__count,
.icp-obj__reward,
.icp-obj__more {
  flex: none;
  font-family: var(--f-mono);
  font-variant-numeric: tabular-nums lining-nums;
  line-height: 1.2;
}
.icp-obj__count b {
  font-weight: 600;
  font-size: var(--text-sm);
  color: var(--paper-50);
}
.icp-obj__count i {
  margin-left: calc(4px * var(--ui-scale));
  font-style: normal;
  font-size: var(--text-xs);
  color: var(--paper-500);
}
.icp-obj__reward {
  font-size: var(--text-xs);
  color: var(--gold-400);
}
/* The further-rows count: a stacked-lines glyph, so it never reads as a
   second `+N` beside a reward. */
.icp-obj__more {
  display: inline-flex;
  align-items: center;
  gap: calc(3px * var(--ui-scale));
  font-size: var(--text-xs);
  color: var(--paper-300);
}
.icp-obj__more svg {
  width: calc(11px * var(--ui-scale));
  height: calc(11px * var(--ui-scale));
  fill: none;
  stroke: currentColor;
  stroke-width: 1.2;
  stroke-linecap: round;
}

/* Quantity as strokes: one 3px tick per unit, a 2px seam, slanted ends. The
   empty tick is a faint paper wash, the reached one the gauge gold. */
.icp-obj__ticks {
  display: flex;
  gap: calc(2px * var(--ui-scale));
  filter: drop-shadow(0 1px 1px rgba(0, 0, 0, 0.7));
}
.icp-obj__tick {
  width: calc(13px * var(--ui-scale));
  height: calc(3px * var(--ui-scale));
  background: rgba(231, 224, 209, 0.18);
  clip-path: polygon(calc(2px * var(--ui-scale)) 0, 100% 0, calc(100% - 2px * var(--ui-scale)) 100%, 0 100%);
}
.icp-obj__tick--on {
  background: var(--gold-400);
}
.icp-obj--done .icp-obj__tick--on {
  background: var(--buff);
}
/* Above the tick limit: one continuous stroke, its far (left) end tapering
   to a point. */
.icp-obj__stroke {
  width: calc(180px * var(--ui-scale));
  max-width: 100%;
  height: calc(3px * var(--ui-scale));
  background: linear-gradient(270deg, rgba(231, 224, 209, 0.16), rgba(231, 224, 209, 0.07));
  clip-path: polygon(calc(10px * var(--ui-scale)) 0, 100% 0, 100% 100%, calc(10px * var(--ui-scale)) 100%, 0 50%);
  filter: drop-shadow(0 1px 1px rgba(0, 0, 0, 0.7));
}
.icp-obj__fill {
  display: block;
  height: 100%;
  background: var(--gold-400);
}
.icp-obj--done .icp-obj__fill {
  background: var(--buff);
}
</style>
