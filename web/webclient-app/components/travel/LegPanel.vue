<script setup>
// LegPanel (OpenSpec change wilderness-travel-leg-ui; interface design §7,
// after the approved prototype docs/design/wilderness-travel/LegPanel.vue):
// the travel band's command region. Top to bottom — the intent line (the
// screen-reader channel for aim and plan), today's leg gauge (one tick per
// step of a supplied plan, or the server's foot capacity by stage with the
// pace's stop marked), its legend, the pace radio group with the 入夜停步
// switch, and the actions 出發/停步, 紮營 and 環顧.
//
// It renders the pure `legView` projection (leg-model.js) and emits intents;
// it keeps no state and sends nothing. Ticks differ by height and outline as
// well as colour (normal full, light shorter, moderate shorter still, severe
// shortest with a rust ring; the terminal sleep step adds a crescent).
// Disabled controls stay focusable with `aria-disabled` and their reason.
import { computed, ref } from "vue";
import { PACE_OPTIONS } from "./leg-model.js";
import { glyphPath } from "../dock-icons.js";
import { SLEEP_CRESCENT_PATH } from "../../lib/map_glyphs.js";

const CAMP_GLYPH = glyphPath("camp");
const LOOK_GLYPH = glyphPath("look");

const props = defineProps({
  // The `legView` result.
  view: { type: Object, required: true },
  motionLevel: { type: String, default: "full" },
});
const emit = defineEmits(["pace", "night", "depart", "stop", "camp", "look"]);

const uid = `leg-${Math.random().toString(36).slice(2, 8)}`;
const intent = computed(() => props.view.intent);
const gauge = computed(() => props.view.gauge);
const legend = computed(() => props.view.legend);
const controls = computed(() => props.view.controls);
const actions = computed(() => props.view.actions);
const primary = computed(() => actions.value.primary);

const radios = ref([]);

function onPace(key) {
  if (!controls.value.enabled || key === controls.value.pace) return;
  emit("pace", key);
}

// The radio pattern: arrows move the selection (and focus) within the group.
function onPaceKey(event, index) {
  const delta = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[event.key];
  if (!delta) return;
  event.preventDefault();
  event.stopPropagation();
  // A frozen group keeps focus (and its ring) on the checked radio.
  if (!controls.value.enabled) return;
  const next = (index + delta + PACE_OPTIONS.length) % PACE_OPTIONS.length;
  radios.value[next]?.focus();
  onPace(PACE_OPTIONS[next].key);
}

function onNight() {
  if (controls.value.enabled) emit("night", !controls.value.stopAtNight);
}

function onPrimary() {
  const action = primary.value;
  if (!action.enabled) return;
  emit(action.kind === "stop" ? "stop" : "depart");
}

function onCamp() {
  if (actions.value.camp.enabled) emit("camp");
}

function onLook() {
  if (actions.value.look.enabled) emit("look");
}

function tickStyle(index) {
  return { "--i": index };
}
</script>

<template>
  <section
    class="leg-panel"
    :class="[`leg-panel--${intent.kind}`, `leg-panel--gauge-${gauge.source}`]"
    data-testid="leg-panel"
    :data-intent="intent.kind"
    :data-gauge="gauge.source"
    :data-motion-level="motionLevel"
    aria-label="行程"
  >
    <header class="leg-panel__head">
      <div
        class="leg-panel__intent"
        role="status"
        aria-live="polite"
        aria-atomic="true"
        data-testid="leg-intent"
        :data-quote="intent.quote?.kind ?? null"
        :data-minutes="intent.quote?.minutes ?? null"
      >
        <p class="leg-panel__title" data-testid="leg-intent-title">{{ intent.title }}</p>
        <p class="leg-panel__detail" data-testid="leg-intent-detail">{{ intent.detail }}</p>
      </div>
      <div v-if="$slots.aside" class="leg-panel__aside"><slot name="aside" /></div>
    </header>

    <div class="leg-panel__gauge-wrap">
      <div
        class="leg-gauge"
        role="img"
        :aria-label="gauge.summary"
        data-testid="leg-gauge"
        :data-ticks="gauge.ticks.length"
      >
        <span
          v-for="(t, i) in gauge.ticks"
          :key="i"
          class="leg-tick"
          :class="[`is-${t.bucket}`, { 'is-sleep': t.sleep, 'is-done': t.done, 'is-beyond': t.beyond, 'is-night': t.night, 'is-camp': t.camp }]"
          :style="tickStyle(i)"
          data-testid="leg-tick"
          :data-stage="t.stage"
          :data-bucket="t.bucket"
          aria-hidden="true"
        >
          <span class="leg-tick__bar" />
          <svg v-if="t.moon || t.sleep" class="leg-tick__moon" viewBox="0 0 10 10" focusable="false"><path :d="SLEEP_CRESCENT_PATH" /></svg>
          <span v-if="t.camp" class="leg-tick__camp" data-testid="leg-camp-mark" />
        </span>
        <span v-if="!gauge.ticks.length" class="leg-gauge__empty" aria-hidden="true">
          {{ gauge.source === "pending" ? "估算中…" : gauge.source === "unavailable" ? "無法估算腳程" : "精力已不足以再走" }}
        </span>
      </div>
      <p class="leg-panel__legend" data-testid="leg-legend" aria-hidden="true">
        <span
          v-for="e in legend.entries"
          :key="e.bucket"
          class="leg-legend__entry"
          :class="`is-${e.bucket}`"
          :data-bucket="e.bucket"
        ><i class="leg-legend__swatch" />{{ e.label }} <b>{{ e.count }}</b></span>
        <span v-if="legend.stop" class="leg-legend__stop"><i class="leg-legend__camp" />{{ legend.stop }}</span>
      </p>
    </div>

    <div class="leg-panel__controls">
      <div
        class="leg-seg"
        role="radiogroup"
        aria-label="行程節制"
        :aria-disabled="controls.enabled ? null : 'true'"
        :aria-describedby="controls.enabled ? null : `${uid}-controls`"
        data-testid="leg-pace"
      >
        <button
          v-for="(p, i) in PACE_OPTIONS"
          :key="p.key"
          :ref="(el) => (radios[i] = el)"
          type="button"
          role="radio"
          class="leg-seg__opt"
          :aria-checked="controls.pace === p.key ? 'true' : 'false'"
          :aria-disabled="controls.enabled ? null : 'true'"
          :aria-describedby="controls.enabled ? `${uid}-pace-${p.key}` : `${uid}-pace-${p.key} ${uid}-controls`"
          :tabindex="controls.pace === p.key ? 0 : -1"
          :title="controls.enabled ? p.hint : controls.reason"
          :data-testid="`leg-pace-${p.key}`"
          @click="onPace(p.key)"
          @keydown="onPaceKey($event, i)"
          @keydown.enter.stop
          @keydown.space.stop
        >{{ p.label }}</button>
      </div>
      <span v-for="p in PACE_OPTIONS" :id="`${uid}-pace-${p.key}`" :key="`hint-${p.key}`" class="leg-sr">{{ p.hint }}</span>
      <button
        type="button"
        class="leg-switch"
        role="switch"
        :aria-checked="controls.stopAtNight ? 'true' : 'false'"
        :aria-disabled="controls.enabled ? null : 'true'"
        :aria-describedby="controls.enabled ? null : `${uid}-controls`"
        :title="controls.enabled ? '入夜後自動停下' : controls.reason"
        data-testid="leg-night"
        @click="onNight"
        @keydown.enter.stop
        @keydown.space.stop
      >
        <span class="leg-switch__track" aria-hidden="true"><span class="leg-switch__knob" /></span>
        <span class="leg-switch__label">入夜停步</span>
      </button>
      <span :id="`${uid}-controls`" class="leg-sr">{{ controls.reason }}</span>
    </div>

    <div class="leg-panel__actions">
      <button
        type="button"
        class="leg-btn leg-btn--primary"
        :class="{ 'leg-btn--stop': primary.kind === 'stop' }"
        :aria-disabled="primary.enabled ? null : 'true'"
        :aria-describedby="primary.enabled ? null : `${uid}-primary`"
        :title="primary.reason ?? null"
        :data-testid="primary.kind === 'stop' ? 'leg-stop' : 'leg-depart'"
        @click="onPrimary"
        @keydown.enter.stop
        @keydown.space.stop
      >
        <span class="leg-btn__label">{{ primary.label }}</span>
        <kbd class="leg-btn__key" aria-hidden="true">{{ primary.hint }}</kbd>
      </button>
      <span :id="`${uid}-primary`" class="leg-sr">{{ primary.reason }}</span>
      <button
        type="button"
        class="leg-btn"
        :aria-disabled="actions.camp.enabled ? null : 'true'"
        :aria-describedby="actions.camp.enabled ? null : `${uid}-camp`"
        :title="actions.camp.reason ?? null"
        data-testid="leg-camp"
        @click="onCamp"
        @keydown.enter.stop
        @keydown.space.stop
      ><svg class="leg-btn__glyph" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path :d="CAMP_GLYPH" /></svg>紮營</button>
      <span :id="`${uid}-camp`" class="leg-sr">{{ actions.camp.reason }}</span>
      <button
        type="button"
        class="leg-btn"
        :aria-disabled="actions.look.enabled ? null : 'true'"
        :aria-describedby="actions.look.enabled ? null : `${uid}-look`"
        :title="actions.look.reason ?? null"
        data-testid="leg-look"
        @click="onLook"
        @keydown.enter.stop
        @keydown.space.stop
      ><svg class="leg-btn__glyph" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path :d="LOOK_GLYPH" /></svg>環顧</button>
      <span :id="`${uid}-look`" class="leg-sr">{{ actions.look.reason }}</span>
    </div>
  </section>
</template>

<style scoped>
/* A quiet ink plate framed by the shared gold hairline, after the
   prototype: every row keeps the 16px × scale text floor. */
.leg-panel {
  --leg-normal: var(--gold-400);
  --leg-light: var(--warn);
  --leg-moderate: #d0705a;
  --leg-severe: #8e3b30;
  --leg-night: #c8d4ee;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: calc(4px * var(--ui-scale));
  width: 100%;
  height: 100%;
  min-height: 0;
  min-width: 0;
  padding: calc(7px * var(--ui-scale)) calc(12px * var(--ui-scale)) calc(8px * var(--ui-scale));
  border: 1px solid rgba(185, 154, 96, 0.28);
  border-radius: var(--radius);
  background:
    radial-gradient(120% 90% at 0% 0%, rgba(185, 154, 96, 0.09), transparent 60%),
    linear-gradient(180deg, rgba(11, 13, 16, 0.38), rgba(11, 13, 16, 0.56));
  font-family: var(--f-sans);
  font-size: var(--text-xs);
  overflow: hidden;
}


/* ── intent ── */
.leg-panel__head {
  display: flex;
  align-items: flex-start;
  gap: calc(10px * var(--ui-scale));
  min-width: 0;
}
.leg-panel__intent {
  flex: 1 1 auto;
  min-width: 0;
  padding-left: calc(10px * var(--ui-scale));
  border-left: 2px solid var(--gold-500);
  transition: border-color var(--motion-fast) var(--ease-standard);
}
.leg-panel__title {
  margin: 0;
  font: var(--text-md) / 1.22 var(--f-display);
  letter-spacing: 0.04em;
  color: var(--paper-50);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.leg-panel__detail {
  margin: 0;
  font-size: var(--text-xs);
  line-height: 1.25;
  color: var(--paper-400);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.leg-panel__aside {
  flex: none;
  display: flex;
}
.leg-panel--idle .leg-panel__intent { border-left-color: var(--ink-600); }
.leg-panel--idle .leg-panel__title { color: var(--paper-300); }
.leg-panel--walking .leg-panel__detail,
.leg-panel--aim .leg-panel__detail,
.leg-panel--plan .leg-panel__detail { color: var(--gold-300); }
.leg-panel--blocked .leg-panel__intent,
.leg-panel--refused .leg-panel__intent,
.leg-panel--stale .leg-panel__intent { border-left-color: var(--seal-500); }
.leg-panel--blocked .leg-panel__detail,
.leg-panel--refused .leg-panel__detail,
.leg-panel--stale .leg-panel__detail { color: var(--paper-200); }
.leg-panel--advice .leg-panel__intent { border-left-color: var(--warn); }
.leg-panel--night .leg-panel__intent { border-left-color: var(--leg-night); }
.leg-panel--advice .leg-panel__detail { color: var(--warn); }
.leg-panel--night .leg-panel__detail { color: var(--leg-night); }

/* ── gauge ── */
.leg-panel__gauge-wrap {
  display: flex;
  flex-direction: column;
  gap: calc(3px * var(--ui-scale));
  min-width: 0;
  /* Spare height (tall viewports) is shared above and below the gauge. */
  margin-top: auto;
  padding-top: calc(2px * var(--ui-scale));
}
.leg-gauge {
  position: relative;
  display: flex;
  align-items: flex-end;
  gap: calc(2px * var(--ui-scale));
  height: calc(14px * var(--ui-scale));
  padding-bottom: calc(2px * var(--ui-scale));
  border-bottom: 1px solid rgba(185, 154, 96, 0.32);
}
.leg-gauge__empty {
  align-self: center;
  font-size: var(--text-xs);
  line-height: 1;
  color: var(--paper-500);
}
.leg-tick {
  position: relative;
  flex: 1 1 0;
  min-width: calc(2px * var(--ui-scale));
  max-width: calc(14px * var(--ui-scale));
  height: 100%;
  display: flex;
  align-items: flex-end;
}
.leg-tick__bar {
  display: block;
  width: 100%;
  height: 100%;
  border-radius: 1.5px;
  background: var(--leg-normal);
  box-shadow: 0 0 6px rgba(228, 200, 142, 0.18);
}
.leg-tick.is-light .leg-tick__bar { height: 74%; background: var(--leg-light); box-shadow: none; }
.leg-tick.is-moderate .leg-tick__bar { height: 52%; background: var(--leg-moderate); box-shadow: none; }
/* Severe: the shortest tick, a dark core inside a rust ring. */
.leg-tick.is-severe .leg-tick__bar {
  height: 34%;
  box-sizing: border-box;
  background: #2a1416;
  border: 1.5px solid var(--leg-moderate);
  box-shadow: none;
}
.leg-tick.is-night .leg-tick__bar { filter: brightness(0.72) saturate(0.6); }
.leg-tick.is-done .leg-tick__bar { opacity: 0.28; }
/* Past the stop: a faint stub on the baseline. */
.leg-tick.is-beyond .leg-tick__bar {
  height: 18%;
  background: rgba(186, 181, 174, 0.22);
  border: 0;
  filter: none;
}
.leg-tick__moon {
  position: absolute;
  left: 50%;
  bottom: calc(100% - 3px * var(--ui-scale));
  width: calc(9px * var(--ui-scale));
  height: calc(9px * var(--ui-scale));
  transform: translateX(-50%);
  fill: var(--leg-night);
  pointer-events: none;
}
.leg-tick.is-sleep .leg-tick__moon { fill: var(--leg-moderate); }
/* The stop: a gold camp line standing proud of the gauge. */
.leg-tick__camp {
  position: absolute;
  right: calc(-2px * var(--ui-scale));
  top: calc(-5px * var(--ui-scale));
  bottom: calc(-4px * var(--ui-scale));
  width: 2px;
  background: var(--gold-300);
  box-shadow: 0 0 6px rgba(238, 221, 180, 0.65);
}
.leg-tick__camp::before {
  content: "";
  position: absolute;
  top: 0;
  left: 2px;
  border-top: calc(4px * var(--ui-scale)) solid transparent;
  border-bottom: calc(4px * var(--ui-scale)) solid transparent;
  border-left: calc(7px * var(--ui-scale)) solid var(--gold-300);
}
/* A soft left-to-right reveal at full motion only. */
.leg-panel[data-motion-level="full"] .leg-tick__bar {
  animation: leg-tick-in var(--motion-panel) var(--ease-enter) both;
  animation-delay: calc(var(--i) * var(--motion-fast) / 15);
}
@keyframes leg-tick-in {
  from { transform: scaleY(0.2); opacity: 0; }
  to { transform: none; }
}
.leg-tick__bar { transform-origin: bottom; }

.leg-panel__legend {
  margin: 0;
  display: flex;
  align-items: baseline;
  flex-wrap: nowrap;
  gap: calc(12px * var(--ui-scale));
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
  font-size: var(--text-xs);
  line-height: 1.25;
  color: var(--paper-400);
  font-variant-numeric: tabular-nums;
}
.leg-legend__entry b {
  font-weight: 600;
  color: var(--paper-200);
}
.leg-legend__swatch {
  display: inline-block;
  width: calc(5px * var(--ui-scale));
  height: calc(12px * var(--ui-scale));
  margin-right: calc(5px * var(--ui-scale));
  vertical-align: -1px;
  border-radius: 1px;
  background: var(--leg-normal);
}
.leg-legend__entry.is-light .leg-legend__swatch { height: calc(9px * var(--ui-scale)); background: var(--leg-light); }
.leg-legend__entry.is-moderate .leg-legend__swatch { height: calc(7px * var(--ui-scale)); background: var(--leg-moderate); }
.leg-legend__entry.is-severe .leg-legend__swatch {
  box-sizing: border-box;
  height: calc(5px * var(--ui-scale));
  background: #2a1416;
  border: 1px solid var(--leg-moderate);
}
.leg-legend__stop {
  margin-left: auto;
  color: var(--gold-300);
  overflow: hidden;
  text-overflow: ellipsis;
}
.leg-legend__camp {
  display: inline-block;
  width: 2px;
  height: calc(12px * var(--ui-scale));
  margin-right: calc(6px * var(--ui-scale));
  vertical-align: -1px;
  background: var(--gold-300);
}

/* ── controls ── */
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
  border-radius: var(--radius-sm);
  background: rgba(11, 13, 16, 0.7);
  border: 1px solid rgba(143, 113, 60, 0.55);
}
.leg-seg__opt {
  border: 0;
  background: transparent;
  color: var(--paper-400);
  font: var(--text-xs) / 1 var(--f-serif);
  letter-spacing: 0.08em;
  padding: calc(5px * var(--ui-scale)) calc(12px * var(--ui-scale));
  border-radius: calc(3px * var(--ui-scale));
  cursor: pointer;
  line-height: 1;
  transition: background var(--motion-fast) var(--ease-standard), color var(--motion-fast) var(--ease-standard);
}
.leg-seg__opt:hover:not([aria-disabled="true"]):not([aria-checked="true"]) { color: var(--paper-100); }
.leg-seg__opt[aria-checked="true"] {
  background: linear-gradient(180deg, rgba(185, 154, 96, 0.45), rgba(143, 113, 60, 0.32));
  color: var(--gold-300);
  box-shadow: inset 0 0 0 1px rgba(228, 200, 142, 0.45);
}
.leg-switch {
  display: inline-flex;
  align-items: center;
  gap: calc(8px * var(--ui-scale));
  border: 0;
  background: none;
  padding: calc(3px * var(--ui-scale)) calc(4px * var(--ui-scale));
  border-radius: var(--radius-sm);
  color: var(--paper-300);
  font: var(--text-xs) / 1 var(--f-serif);
  letter-spacing: 0.06em;
  cursor: pointer;
}
.leg-switch__track {
  position: relative;
  width: calc(36px * var(--ui-scale));
  height: calc(20px * var(--ui-scale));
  box-sizing: border-box;
  border-radius: var(--radius-pill);
  background: rgba(54, 54, 56, 0.9);
  border: 1px solid rgba(143, 113, 60, 0.6);
  transition: background var(--motion-fast) var(--ease-standard), border-color var(--motion-fast) var(--ease-standard);
}
.leg-switch__knob {
  position: absolute;
  top: 1px;
  left: 1px;
  width: calc(16px * var(--ui-scale));
  height: calc(16px * var(--ui-scale));
  border-radius: 50%;
  background: var(--paper-500);
  transition: transform var(--motion-fast) var(--ease-standard), background var(--motion-fast) var(--ease-standard);
}
.leg-switch[aria-checked="true"] .leg-switch__track {
  background: rgba(54, 66, 104, 0.92);
  border-color: rgba(170, 190, 230, 0.6);
}
.leg-switch[aria-checked="true"] .leg-switch__knob {
  transform: translateX(calc(16px * var(--ui-scale)));
  background: var(--leg-night);
  box-shadow: 0 0 6px rgba(200, 212, 238, 0.5);
}
.leg-switch[aria-checked="true"] .leg-switch__label { color: var(--leg-night); }

/* ── actions ── */
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
  min-width: 0;
  height: calc(32px * var(--ui-scale));
  padding: 0 calc(10px * var(--ui-scale));
  border-radius: var(--radius-sm);
  border: 1px solid var(--gold-600);
  background: rgba(43, 42, 39, 0.55);
  color: var(--gold-300);
  font: var(--text-sm) / 1 var(--f-serif);
  letter-spacing: 0.12em;
  white-space: nowrap;
  cursor: pointer;
  transition:
    background var(--motion-fast) var(--ease-standard),
    border-color var(--motion-fast) var(--ease-standard),
    color var(--motion-fast) var(--ease-standard);
}
.leg-btn:hover:not([aria-disabled="true"]) {
  background: rgba(143, 113, 60, 0.3);
  border-color: var(--gold-400);
}
.leg-btn__glyph {
  flex: none;
  width: calc(17px * var(--ui-scale));
  height: calc(17px * var(--ui-scale));
  fill: none;
  stroke: var(--gold-500);
  stroke-width: 1.6;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.leg-btn--primary {
  background: linear-gradient(180deg, rgba(185, 154, 96, 0.42), rgba(143, 113, 60, 0.26));
  border-color: var(--gold-500);
  color: var(--paper-50);
}
.leg-btn--stop {
  background: linear-gradient(180deg, rgba(169, 50, 42, 0.62), rgba(124, 32, 38, 0.5));
  border-color: var(--seal-500);
}
.leg-btn--stop:hover:not([aria-disabled="true"]) {
  background: linear-gradient(180deg, rgba(190, 60, 50, 0.7), rgba(140, 36, 42, 0.58));
  border-color: var(--seal-400);
}
.leg-btn__key {
  font: var(--text-xs) / 1 var(--f-sans);
  letter-spacing: 0;
  color: var(--paper-400);
  padding: calc(2px * var(--ui-scale)) calc(5px * var(--ui-scale));
  border-radius: 3px;
  border: 1px solid rgba(186, 181, 174, 0.3);
}
.leg-btn[aria-disabled="true"],
.leg-seg__opt[aria-disabled="true"],
.leg-switch[aria-disabled="true"] {
  cursor: default;
}
.leg-btn[aria-disabled="true"] {
  border-color: var(--ink-600);
  background: rgba(27, 29, 33, 0.5);
  color: var(--paper-500);
}
.leg-btn[aria-disabled="true"] .leg-btn__glyph { stroke: var(--paper-700); }
.leg-btn[aria-disabled="true"] .leg-btn__key { color: var(--paper-700); border-color: var(--ink-700); }
.leg-seg[aria-disabled="true"],
.leg-switch[aria-disabled="true"] { opacity: 0.55; }

.leg-seg__opt:focus-visible,
.leg-switch:focus-visible,
.leg-btn:focus-visible {
  outline: none;
  box-shadow: var(--focus);
}

.leg-sr {
  position: absolute;
  width: 1px;
  height: 1px;
  margin: -1px;
  padding: 0;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
  border: 0;
}
</style>
