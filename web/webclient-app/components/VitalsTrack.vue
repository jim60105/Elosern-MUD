<script setup>
// VitalsTrack (H2, webclient-hud-02-status-islands, design D4/D5): the
// left stack's vitals island. One row per gauge (hp/mp/sp) carrying an
// icon, a Traditional Chinese label, and the `current / maximum` numerals
// (the preserved `status-panel__gauge-value--<key>` hooks the combat and
// transport-mount browser journeys depend on). Each track holds a trailing
// "ghost" bar behind the fill so damage taken is visible as the gap; the
// ghost is decorative (aria-hidden, no accessible name) and holds only a
// previously committed ratio of its own gauge, resetting to the current
// ratio on an epoch change so a reconnect never draws a trail across
// sessions. The combat session line (the old panel's last row) renders as
// this island's header row, so no pre-change row loses its only home.
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
});

const GAUGES = [
  { key: "hp", label: "生命" },
  { key: "mp", label: "魔力" },
  { key: "sp", label: "耐力" },
];

const resources = computed(() => props.status?.resources ?? {});
function gauge(key) {
  const r = resources.value[key];
  return r ? { current: r.current, maximum: r.maximum, ratio: gaugeRatio(r) } : null;
}

// The combat session line (the pre-change `StatusPanel`'s last row) now
// renders as the vitals island's header row.
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
  <div class="hud vitals" data-testid="vitals-track">
    <p
      v-if="combat"
      class="combat"
      data-testid="status-panel__combat"
      :data-mode="combat.mode"
    >
      戰鬥中（{{ combatLabel(combat.mode) }}）· 第 {{ combat.round }} 回合
    </p>
    <div
      v-for="g in GAUGES"
      :key="g.key"
      class="vital"
      :class="[g.key, { low: g.key === 'hp' && lowHp }]"
      :data-testid="`status-panel__gauge--${g.key}`"
      :data-low="g.key === 'hp' && lowHp ? 'true' : 'false'"
    >
      <div class="vh">
        <span class="lbl">
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
          {{ g.label }}
        </span>
        <span
          class="num"
          :data-testid="`status-panel__gauge-value--${g.key}`"
        >{{ gauge(g.key)?.current ?? 0 }} / {{ gauge(g.key)?.maximum ?? 0 }}</span>
        <span v-if="g.key === 'hp' && lowHp" class="low-mark" data-testid="vitals-low-marker">
          危險
        </span>
      </div>
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
</template>

<style scoped>
/* The shared island chrome (design D1/D2.1), expressed through the shared
   design tokens only. */
.hud {
  background: var(--panel);
  backdrop-filter: blur(9px);
  -webkit-backdrop-filter: blur(9px);
  border: var(--line);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
}

.vitals {
  display: flex;
  flex-direction: column;
  gap: 9px;
  padding: 10px 12px 12px;
  font-family: var(--f-sans);
}

.combat {
  margin: 0;
  padding: var(--sp-1) var(--sp-2);
  color: var(--seal-400);
  border: 1px dashed var(--seal-600);
  border-radius: var(--radius-sm);
  font-size: 0.85em;
}

.vital .vh {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
  margin-bottom: 4px;
}

.vital .vh .lbl {
  display: flex;
  align-items: center;
  gap: 5px;
  color: var(--paper-100);
  font-weight: 500;
}

.vital .vh .lbl .ic {
  color: currentColor;
  flex: none;
}

.vital .vh .num {
  margin-left: auto;
  font-family: var(--f-mono);
  font-size: 11px;
  color: var(--paper-300);
}

.low-mark {
  font-size: 10.5px;
  color: var(--crit);
  font-weight: 700;
}

/* The track holds the trailing ghost bar (the delayed transition makes
   damage visible as the gap) behind the fill; the ghost is decorative. */
.track {
  position: relative;
  height: 10px;
  border-radius: 99px;
  background: var(--ink-780);
  overflow: hidden;
  border: 1px solid rgba(0, 0, 0, 0.45);
}

.track .ghost {
  position: absolute;
  inset: 0;
  width: 0;
  background: rgba(255, 255, 255, 0.28);
  transition: width 0.6s ease 0.25s;
}

.track .ghost[data-instant="true"] {
  transition: none;
}

.track .fill {
  position: absolute;
  inset: 0 auto 0 0;
  border-radius: 99px;
  transition: width 0.4s var(--ease-standard);
}

.track .fill::after {
  content: "";
  position: absolute;
  inset: 0 0 50% 0;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.18), transparent);
  border-radius: 99px 99px 0 0;
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
  background: repeating-linear-gradient(45deg, rgba(255, 255, 255, 0.22) 0 4px, transparent 4px 9px),
    linear-gradient(90deg, #9a7516, var(--vit-sp));
}

.vital.sp .fill::after {
  display: none;
}

/* The low state: a recolour of the numerals plus the explicit 危險 marker,
   never colour alone. The hp fill renders the elosern-hp-pulse keyframe
   the migration extracted but never consumed (design D5). */
.vital.low .vh .num {
  color: var(--crit);
}

.vital.low .fill {
  animation: elosern-hp-pulse var(--motion-hp-pulse) ease-in-out infinite;
}
</style>
