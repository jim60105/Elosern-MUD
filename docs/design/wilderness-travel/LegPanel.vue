<script setup>
// The leg panel (prototype): the band's command region in travel mode.
// It states the current movement intent, today's leg as one tick per step
// coloured and shaped by predicted fatigue stage (with the nightfall moon
// and the stop's camp mark), the pace and the nightfall toggle, and the
// actions: 出發 / 停步, 紮營, 環顧. With no route it shows how far the party
// can still walk, split by stage, with the pace's stop notched in.
import { computed } from "vue";
import { PACES, STAGE_INDEX, formatClock } from "./travel-model.js";

const props = defineProps({
  intent: { type: Object, required: true },
  plan: { type: Object, default: null },
  // Steps of the plan already walked (they render as spent).
  progress: { type: Number, default: 0 },
  capacity: { type: Object, required: true },
  pace: { type: String, default: "standard" },
  stopAtNight: { type: Boolean, default: true },
  walking: { type: Boolean, default: false },
  locked: { type: Boolean, default: false },
});
const emit = defineEmits(["pace", "night", "depart", "stop", "camp", "look"]);

const STAGE_SHORT = { normal: "充沛", light: "輕度", moderate: "中度", severe: "重度" };

const ticks = computed(() => {
  if (props.plan) {
    return props.plan.steps.map((s, i) => ({
      stage: s.stage,
      done: i < props.progress,
      beyond: i > props.plan.stopIndex,
      night: props.plan.nightfallIndex !== null && i >= props.plan.nightfallIndex,
      moon: i === props.plan.nightfallIndex,
      camp: i === props.plan.stopIndex && props.plan.stopReason !== "arrival",
    }));
  }
  const out = [];
  const stopStage = PACES.find((p) => p.key === props.pace)?.stopStage;
  for (const key of ["normal", "light", "moderate", "severe"]) {
    for (let i = 0; i < props.capacity[key]; i += 1) out.push({ stage: key, beyond: false });
  }
  if (stopStage) {
    const stopAt = out.findIndex((t) => STAGE_INDEX[t.stage] >= STAGE_INDEX[stopStage]);
    if (stopAt >= 0) {
      out[stopAt].camp = true;
      for (let i = stopAt + 1; i < out.length; i += 1) out[i].beyond = true;
    }
  }
  return out;
});

const legend = computed(() => {
  const counts = { normal: 0, light: 0, moderate: 0, severe: 0 };
  if (props.plan) {
    props.plan.steps.forEach((s, i) => {
      if (i <= props.plan.stopIndex && counts[s.stage] !== undefined) counts[s.stage] += 1;
    });
  } else {
    Object.assign(counts, props.capacity);
  }
  return Object.entries(counts).filter(([, n]) => n > 0);
});

const summary = computed(() => {
  if (!props.plan) {
    const total = Object.values(props.capacity).reduce((a, b) => a + b, 0);
    return `精力還夠走約 ${total} 格`;
  }
  const stop = props.plan.steps[props.plan.stopIndex];
  if (!stop) return "";
  const minutes = props.plan.steps.slice(0, props.plan.stopIndex + 1).reduce((a, s) => a + s.sec, 0) / 60;
  const h = Math.floor(minutes / 60);
  const m = Math.round(minutes % 60);
  return `${props.plan.stopIndex + 1} 步・${h ? `${h} 小時 ` : ""}${m} 分・${formatClock(stop.minutes).text} 停`;
});

const STOP_TEXT = {
  pace: "依節制在此紮營",
  nightfall: "入夜即停",
  depletion: "精力不足以再走",
  arrival: "抵達目的地",
};
</script>

<template>
  <section class="leg-panel" aria-label="行程">
    <header class="leg-panel__head">
      <h2 class="leg-panel__intent" :class="{ 'is-quiet': intent.kind === 'none' }">{{ intent.title }}</h2>
      <p class="leg-panel__summary">{{ intent.detail ?? summary }}</p>
    </header>

    <div class="leg-panel__gauge" :aria-label="`今日行程：${summary}`">
      <span
        v-for="(t, i) in ticks"
        :key="i"
        class="leg-tick"
        :class="[`is-${t.stage}`, { 'is-beyond': t.beyond, 'is-night': t.night, 'is-done': t.done }]"
      >
        <span v-if="t.moon" class="leg-tick__moon" aria-hidden="true">☾</span>
        <span v-if="t.camp" class="leg-tick__camp" aria-hidden="true"></span>
      </span>
    </div>
    <p class="leg-panel__legend">
      <span v-for="[key, n] in legend" :key="key" :class="`is-${key}`"><i></i>{{ STAGE_SHORT[key] }} {{ n }}</span>
      <span v-if="plan" class="leg-panel__stop">{{ STOP_TEXT[plan.stopReason] }}</span>
    </p>

    <div class="leg-panel__controls">
      <div class="leg-seg" role="radiogroup" aria-label="行程節制">
        <button
          v-for="p in PACES"
          :key="p.key"
          type="button"
          role="radio"
          class="leg-seg__opt"
          :aria-checked="pace === p.key ? 'true' : 'false'"
          :title="p.hint"
          :disabled="walking"
          @click="emit('pace', p.key)"
        >{{ p.label }}</button>
      </div>
      <button
        type="button"
        class="leg-toggle"
        role="switch"
        :aria-checked="stopAtNight ? 'true' : 'false'"
        :disabled="walking"
        @click="emit('night', !stopAtNight)"
      >
        <span class="leg-toggle__track"><span class="leg-toggle__knob"></span></span>入夜停步
      </button>
    </div>

    <div class="leg-panel__actions">
      <button
        v-if="walking"
        type="button"
        class="leg-btn leg-btn--primary leg-btn--stop"
        @click="emit('stop')"
      >停步 <kbd>任意鍵</kbd></button>
      <button
        v-else
        type="button"
        class="leg-btn leg-btn--primary"
        :disabled="!plan || locked"
        @click="emit('depart')"
      >出發 <kbd>Enter</kbd></button>
      <button type="button" class="leg-btn" :disabled="walking || locked" @click="emit('camp')">紮營</button>
      <button type="button" class="leg-btn" :disabled="walking || locked" @click="emit('look')">環顧</button>
    </div>
  </section>
</template>

<style>
.leg-panel {
  height: 100%;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: calc(8px * var(--ui-scale));
  padding: calc(14px * var(--ui-scale)) calc(22px * var(--ui-scale)) calc(14px * var(--ui-scale));
  min-height: 0;
}
.leg-panel__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: calc(12px * var(--ui-scale));
  min-width: 0;
}
.leg-panel__intent {
  margin: 0;
  font: var(--text-lg)/1.25 var(--f-display);
  color: var(--paper-50);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.leg-panel__intent.is-quiet {
  color: var(--paper-400);
}
.leg-panel__summary {
  margin: 0;
  flex: none;
  font: var(--text-xs)/1.2 var(--f-sans);
  color: var(--paper-400);
  font-variant-numeric: tabular-nums;
}

.leg-panel__gauge {
  display: flex;
  gap: calc(2px * var(--ui-scale));
  height: calc(14px * var(--ui-scale));
  margin-top: calc(6px * var(--ui-scale));
}
.leg-tick {
  position: relative;
  flex: 1;
  min-width: calc(3px * var(--ui-scale));
  border-radius: 2px;
  background: var(--gold-400);
}
.leg-tick.is-light {
  background: var(--warn);
  clip-path: polygon(0 18%, 100% 18%, 100% 82%, 0 82%);
}
.leg-tick.is-moderate {
  background: #c46a4f;
  clip-path: polygon(0 30%, 100% 30%, 100% 70%, 0 70%);
}
.leg-tick.is-severe {
  background: #7a3a32;
  clip-path: polygon(0 38%, 100% 38%, 100% 62%, 0 62%);
}
.leg-tick.is-night {
  filter: brightness(0.7) saturate(0.6) hue-rotate(-20deg);
}
.leg-tick.is-done {
  opacity: 0.28;
}
.leg-tick.is-beyond {
  background: rgba(186, 181, 174, 0.18);
  clip-path: polygon(0 38%, 100% 38%, 100% 62%, 0 62%);
  filter: none;
}
.leg-tick__moon {
  position: absolute;
  left: 50%;
  top: calc(-20px * var(--ui-scale));
  transform: translateX(-50%);
  font-size: var(--text-xs);
  color: #c8d4ee;
}
.leg-tick__camp {
  position: absolute;
  right: calc(-6px * var(--ui-scale));
  top: calc(-5px * var(--ui-scale));
  bottom: calc(-5px * var(--ui-scale));
  width: 2px;
  background: var(--gold-300);
  box-shadow: 0 0 6px rgba(238, 221, 180, 0.6);
}
.leg-panel__legend {
  margin: 0;
  display: flex;
  flex-wrap: wrap;
  gap: calc(4px * var(--ui-scale)) calc(14px * var(--ui-scale));
  font: var(--text-xs)/1.2 var(--f-sans);
  color: var(--paper-400);
}
.leg-panel__legend i {
  display: inline-block;
  width: calc(10px * var(--ui-scale));
  height: calc(6px * var(--ui-scale));
  margin-right: calc(5px * var(--ui-scale));
  vertical-align: middle;
  border-radius: 1px;
  background: var(--gold-400);
}
.leg-panel__legend .is-light i { background: var(--warn); }
.leg-panel__legend .is-moderate i { background: #c46a4f; }
.leg-panel__legend .is-severe i { background: #7a3a32; }
.leg-panel__stop {
  margin-left: auto;
  color: var(--gold-300);
}

.leg-panel__controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: calc(10px * var(--ui-scale));
  margin-top: auto;
}
.leg-seg {
  display: inline-flex;
  padding: 2px;
  border-radius: calc(6px * var(--ui-scale));
  background: rgba(11, 13, 16, 0.7);
  border: 1px solid rgba(143, 113, 60, 0.5);
}
.leg-seg__opt {
  border: 0;
  background: transparent;
  color: var(--paper-400);
  font: var(--text-xs)/1 var(--f-serif);
  padding: calc(6px * var(--ui-scale)) calc(13px * var(--ui-scale));
  border-radius: calc(4px * var(--ui-scale));
  cursor: pointer;
}
.leg-seg__opt[aria-checked="true"] {
  background: linear-gradient(180deg, rgba(185, 154, 96, 0.45), rgba(143, 113, 60, 0.35));
  color: var(--gold-300);
  box-shadow: inset 0 0 0 1px rgba(228, 200, 142, 0.45);
}
.leg-seg__opt:focus-visible,
.leg-toggle:focus-visible,
.leg-btn:focus-visible {
  outline: 2px solid var(--gold-400);
  outline-offset: 2px;
}
.leg-toggle {
  display: inline-flex;
  align-items: center;
  gap: calc(8px * var(--ui-scale));
  border: 0;
  background: none;
  color: var(--paper-300);
  font: var(--text-xs)/1 var(--f-serif);
  cursor: pointer;
  padding: 0;
}
.leg-toggle__track {
  position: relative;
  width: calc(34px * var(--ui-scale));
  height: calc(18px * var(--ui-scale));
  border-radius: 999px;
  background: rgba(54, 54, 56, 0.9);
  border: 1px solid rgba(143, 113, 60, 0.6);
  transition: background var(--motion-fast);
}
.leg-toggle__knob {
  position: absolute;
  top: 1px;
  left: 1px;
  width: calc(14px * var(--ui-scale));
  height: calc(14px * var(--ui-scale));
  border-radius: 50%;
  background: var(--paper-400);
  transition: transform var(--motion-fast) var(--ease-standard);
}
.leg-toggle[aria-checked="true"] .leg-toggle__track {
  background: rgba(70, 82, 120, 0.9);
  border-color: rgba(170, 190, 230, 0.6);
}
.leg-toggle[aria-checked="true"] .leg-toggle__knob {
  transform: translateX(calc(16px * var(--ui-scale)));
  background: #c8d4ee;
}

.leg-panel__actions {
  display: grid;
  grid-template-columns: 1.6fr 1fr 1fr;
  gap: calc(8px * var(--ui-scale));
}
.leg-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: calc(8px * var(--ui-scale));
  height: calc(38px * var(--ui-scale));
  border-radius: calc(5px * var(--ui-scale));
  border: 1px solid var(--gold-600);
  background: rgba(43, 42, 39, 0.55);
  color: var(--gold-300);
  font: var(--text-sm)/1 var(--f-serif);
  cursor: pointer;
  transition: background var(--motion-fast), border-color var(--motion-fast);
}
.leg-btn:hover:not(:disabled) {
  background: rgba(143, 113, 60, 0.3);
  border-color: var(--gold-400);
}
.leg-btn:disabled {
  opacity: 0.4;
  cursor: default;
}
.leg-btn--primary {
  background: linear-gradient(180deg, rgba(185, 154, 96, 0.42), rgba(143, 113, 60, 0.28));
  border-color: var(--gold-500);
  color: var(--paper-50);
}
.leg-btn--stop {
  background: linear-gradient(180deg, rgba(169, 50, 42, 0.6), rgba(124, 32, 38, 0.5));
  border-color: var(--seal-500);
}
.leg-btn kbd {
  font: var(--text-xs)/1 var(--f-sans);
  color: var(--paper-400);
  padding: calc(2px * var(--ui-scale)) calc(5px * var(--ui-scale));
  border-radius: 3px;
  border: 1px solid rgba(186, 181, 174, 0.3);
}
</style>
