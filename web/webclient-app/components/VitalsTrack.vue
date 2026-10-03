<script setup>
// VitalsTrack (H2, webclient-hud-02-status-islands, design D4/D5;
// vitals-bar-redesign design D2): the vitals dock's gauges as one instrument.
// A single numeral readout row — each gauge's icon (its shape tells the three
// apart without colour) and its `current / maximum` value, in the lines'
// order — stands over three thin trailing-bar lines laid almost edge to edge.
// The readout carries the preserved `status-panel__gauge-value--<key>` hooks
// the combat and transport-mount browser journeys depend on; each gauge's
// Traditional Chinese label is its readout's accessible name, not visible
// text. Each line holds a trailing
// "ghost" bar behind the fill so damage taken is visible as the gap; the
// ghost is decorative (aria-hidden, no accessible name) and holds only a
// previously committed ratio of its own gauge, resetting to the current
// ratio on an epoch change so a reconnect never draws a trail across
// sessions. The combat session line (the old panel's last row) renders
// above the readout, so no pre-change row loses its only home. The component
// is transparent: the dock chrome belongs to StatusPanel's root.
import { computed, ref, watch } from "vue";
import { gaugeRatio } from "./vitals.js";

const props = defineProps({
  // The committed `status` v1 panel payload; the track reads `resources`.
  status: { type: Object, required: true },
  // The derived low-HP state from the store's `view.vitals` slice.
  lowHp: { type: Boolean, default: false },
  // The committed transport revision: within one epoch, a revision change
  // moves the fill immediately while the ghost chases it with a CSS
  // delay (the gap is the damage taken); on an epoch change the ghost
  // resets to the current ratio (no trail across a reconnect).
  revision: { type: [Number, String], default: null },
  epoch: { type: [Number, String], default: null },
  // The hit points a playing combat round displays instead of the committed
  // `status.resources.hp.current` (webclient-combat-beat-queue D7): a Number
  // while the round plays, null otherwise. The numerals, the fill, and the
  // trailing bar's ratio all follow it, so the bar lags every displayed drop
  // and every snap. Only hp reads it: a beat carries no other resource.
  displayHp: { type: Number, default: null },
});

const GAUGES = [
  { key: "hp", label: "生命" },
  { key: "mp", label: "魔力" },
  { key: "sp", label: "耐力" },
];

const resources = computed(() => props.status?.resources ?? {});
function gauge(key) {
  const r = resources.value[key];
  if (!r) {
    return null;
  }
  // A displayed value replaces the committed current for hp only, and the
  // ratio is computed from it, so the fill and the trailing bar follow the
  // same number the numerals show.
  const current = key === "hp" && props.displayHp != null ? props.displayHp : r.current;
  return { current, maximum: r.maximum, ratio: gaugeRatio({ current, maximum: r.maximum }) };
}

// The combat session line (the pre-change `StatusPanel`'s last row) now
// renders above the bars, inside the dock.
const COMBAT_MODES = {
  hostile: "敵對",
  guild_exam: "公會考核",
};
const combat = computed(
  () =>
    props.status?.combat && typeof props.status.combat.round === "number"
      ? props.status.combat
      : null,
);
function combatLabel(mode) {
  return COMBAT_MODES[mode] ?? mode;
}

// The ghost (trailing bar) rule: on a new revision within the same epoch
// the ghost keeps its previously committed ratio and chases the new ratio
// with the draft's delayed transition; on an epoch change it resets to the
// current ratio so no trail is drawn across sessions. The reset is
// instantaneous (transition suppressed for one frame).
const lastSeen = ref({ revision: null, epoch: null });
const ghostInstant = ref(false);
watch(
  [() => props.revision, () => props.epoch],
  ([revision, epoch]) => {
    if (revision === null) {
      return;
    }
    if (
      lastSeen.value.epoch !== null &&
      lastSeen.value.epoch !== epoch
    ) {
      ghostInstant.value = true;
      // Re-arm only after the transition:none state has actually painted:
      // a single nextTick can flip the flag back in the same rendering
      // cycle, before the browser paints. Two nested frames guarantee the
      // snap is visible (design D4: no trail is drawn across a reconnect).
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          ghostInstant.value = false;
        });
      });
    }
    lastSeen.value = { revision, epoch };
  },
);
</script>

<template>
  <div class="vitals" data-testid="vitals-track">
    <p
      v-if="combat"
      class="combat"
      data-testid="status-panel__combat"
      :data-mode="combat.mode"
    >
      <span>戰鬥中（{{ combatLabel(combat.mode) }}）</span>‧ <span>{{ combat.round === 0 ? "準備中" : `第 ${combat.round} 回合` }}</span>
    </p>
    <!-- The readout (design D2): one value per gauge, in the lines' order.
         Each reading is named by its gauge's label for assistive technology;
         the 危險 marker joins the hp reading. -->
    <div class="readout">
      <span
        v-for="g in GAUGES"
        :key="g.key"
        class="reading"
        :class="[g.key, { low: g.key === 'hp' && lowHp }]"
        role="group"
        :aria-label="g.label"
        :data-testid="`status-panel__reading--${g.key}`"
      >
        <svg
          v-if="g.key === 'hp'"
          class="ic"
          width="12"
          height="12"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            d="M12 21s-8-5.5-8-11a4.5 4.5 0 0 1 8-2 4.5 4.5 0 0 1 8 2c0 5.5-8 11-8 11z"
            fill="currentColor"
          />
        </svg>
        <svg
          v-else-if="g.key === 'mp'"
          class="ic"
          width="12"
          height="12"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            d="M12 2l2.7 6.3 6.3 2.7-6.3 2.7L12 20l-2.7-6.3L3 11l6.3-2.7L12 2z"
            fill="currentColor"
          />
        </svg>
        <svg v-else class="ic" width="12" height="12" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M13 2L4.5 13H11l-1 9L19 10h-6.5L13 2z" fill="currentColor" />
        </svg>
        <span
          class="num"
          :data-testid="`status-panel__gauge-value--${g.key}`"
        ><span class="cur">{{ gauge(g.key)?.current ?? 0 }}</span><span class="max"> / {{ gauge(g.key)?.maximum ?? 0 }}</span></span>
        <span v-if="g.key === 'hp' && lowHp" class="low-mark" data-testid="vitals-low-marker">危險</span>
      </span>
    </div>
    <!-- The three thin lines, almost edge to edge: decorative restatements of
         the readout's ratios, so they carry no text of their own. -->
    <div class="lines">
      <div
        v-for="g in GAUGES"
        :key="g.key"
        class="vital"
        :class="[g.key, { low: g.key === 'hp' && lowHp }]"
        :data-testid="`status-panel__gauge--${g.key}`"
        :data-low="g.key === 'hp' && lowHp ? 'true' : 'false'"
      >
        <div class="track">
          <span
            class="ghost"
            :data-instant="ghostInstant ? 'true' : 'false'"
            aria-hidden="true"
            :style="{ width: `${gauge(g.key)?.ratio ?? 0}%` }"
          ></span>
          <span class="fill" :style="{ width: `${gauge(g.key)?.ratio ?? 0}%` }"></span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Transparent (vitals-bar-redesign design D4): the dock chrome is on
   StatusPanel's root. The readout row stands over the three lines. */
.vitals {
  display: flex;
  flex-direction: column;
  gap: calc(6px * var(--ui-scale));
  font-family: var(--f-sans);
}

/* The combat session line: a quiet seal-ruled caption above the readout. */
.combat {
  margin: 0;
  padding: 0 0 0 calc(7px * var(--ui-scale));
  color: var(--paper-300);
  border-left: calc(2px * var(--ui-scale)) solid var(--seal-600);
  font: var(--text-xs)/1.4 var(--f-serif);
  letter-spacing: 0.06em;
}
.combat > span { white-space: nowrap; }

/* The readout: three readings set as one phrase from the spine, in the
   lines' order, on one baseline. The current value
   leads in the brightest paper at the mono face's tabular figures; the
   maximum recedes a size and two steps of ink, joined by a hairline slash.
   It wraps rather than overflow should a value grow unusually long. */
.readout {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-start;
  align-items: baseline;
  column-gap: calc(18px * var(--ui-scale));
  row-gap: calc(2px * var(--ui-scale));
  padding: 0 1px;
}

.reading {
  display: inline-flex;
  align-items: baseline;
  gap: calc(5px * var(--ui-scale));
  white-space: nowrap;
}

/* The icon is the reading's only chromatic accent: its gauge's own hue,
   the same hue as its line below. The width/height attributes are its
   reference size; the chrome factor scales the drawn box. */
.reading .ic {
  flex: none;
  align-self: center;
  width: calc(11px * var(--ui-scale));
  height: calc(11px * var(--ui-scale));
  filter: drop-shadow(0 1px 0 rgba(0, 0, 0, 0.7));
}
.reading.hp .ic { color: var(--vit-hp); }
.reading.mp .ic { color: var(--vit-mp); }
.reading.sp .ic { color: var(--vit-sp); }

.num {
  font-family: var(--f-mono);
  font-variant-numeric: tabular-nums lining-nums;
  line-height: 1;
  letter-spacing: 0;
  text-shadow: 0 1px 1px rgba(0, 0, 0, 0.8);
}
.num .cur {
  color: var(--paper-50);
  font-size: var(--text-sm);
  font-weight: 600;
}
.num .max {
  color: var(--paper-500);
  font-size: calc(10px * var(--ui-scale));
}

.low-mark {
  align-self: center;
  padding: 1px calc(4px * var(--ui-scale)) 0;
  border: 1px solid var(--seal-600);
  border-radius: 2px;
  color: var(--crit);
  font: 700 calc(10px * var(--ui-scale))/1.2 var(--f-sans);
  letter-spacing: 0.1em;
}

/* The low state: the hp reading's icon and current value recolour, the
   explicit 危險 marker joins them, and the hp line pulses — never colour
   alone (design D5). */
.reading.low .num .cur {
  color: var(--crit);
}

/* The three lines, laid almost edge to edge like three brush strokes from
   one hand: each tapers to a point at its right end, and each runs a little
   shorter than the one above, so the set fans off to the right instead of
   ending on a hard square edge. A 1px seam of shadow parts them. */
.lines {
  display: flex;
  flex-direction: column;
  gap: 1px;
  filter: drop-shadow(0 1px 0 rgba(0, 0, 0, 0.75));
}
.lines .vital.mp { margin-right: 5%; }
.lines .vital.sp { margin-right: 10%; }

.track {
  position: relative;
  height: calc(4px * var(--ui-scale));
  background: linear-gradient(90deg, rgba(231, 224, 209, 0.16), rgba(231, 224, 209, 0.07));
  overflow: hidden;
  /* The stroke: a blunt butt at the spine, a long point at the far end. */
  clip-path: polygon(0 0, calc(100% - 10px * var(--ui-scale)) 0, 100% 50%, calc(100% - 10px * var(--ui-scale)) 100%, 0 100%);
}

.track .ghost {
  position: absolute;
  inset: 0;
  width: 0;
  background: rgba(255, 255, 255, 0.28);
  transition: width var(--motion-trail) ease var(--motion-trail-delay);
}

.track .ghost[data-instant="true"] {
  transition: none;
}

.track .fill {
  position: absolute;
  inset: 0 auto 0 0;
  transition: width var(--motion-slow) var(--ease-standard);
}

.track .fill::after {
  content: "";
  position: absolute;
  inset: 0 0 50% 0;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.22), transparent);
}

.vital.hp .fill {
  background: linear-gradient(90deg, #8c2f2a, var(--vit-hp));
}

.vital.mp .fill {
  background: linear-gradient(90deg, #33507f, var(--vit-mp));
}

/* The sp fill carries a diagonal stripe texture, so it is distinguishable
   from the hp and mp fills without colour (design D1). */
.vital.sp .fill {
  background: repeating-linear-gradient(45deg, rgba(255, 255, 255, 0.3) 0 calc(2px * var(--ui-scale)), transparent calc(2px * var(--ui-scale)) calc(5px * var(--ui-scale))),
    linear-gradient(90deg, #9a7516, var(--vit-sp));
}

.vital.sp .fill::after {
  display: none;
}

.vital.low .fill {
  animation: elosern-hp-pulse var(--motion-hp-pulse) ease-in-out infinite;
}
</style>
