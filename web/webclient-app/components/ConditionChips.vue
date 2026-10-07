<script setup>
// ConditionChips (H2, webclient-hud-02-status-islands, design D6/D7/D8;
// vitals-bar-redesign design D3): the vitals dock's condition icon row. No
// window, no header, no labels: one small icon button per committed
// condition, carrying only its per-severity shape glyph in that severity's
// hue, directly above the bars. The readable name, the remaining duration
// (only when the payload supplies `remaining_seconds`, shown verbatim —
// never decremented between revisions) and every derived modifier live in a
// tooltip opened by hover or keyboard focus and closed by pointer leave,
// blur, or Escape; the icon's accessible name carries the same prose.
// Visible icons are capped at 6; the remainder stays reachable in one action
// through the `+N` icon's bounded disclosure, which lists the same tooltip
// content for every hidden condition.
//
// The tooltip is teleported to `body` and placed from the icon's box: the
// `vitals` anchor is a scroll container, so an absolutely positioned tip
// hung above the dock would be clipped. A scroll or resize while it is open
// closes it rather than leaving it adrift.
import { computed, onBeforeUnmount, ref, useId, watch } from "vue";
import { conditionLabel, conditionModifiers, conditionSource } from "../lib/condition_label.js";

const props = defineProps({
  // The committed `status.conditions[]` array.
  conditions: { type: Array, default: () => [] },
  // Whether the dock showing the row is revealed: a hiding dock fires no
  // mouseleave, so the open tooltip is dropped here.
  revealed: { type: Boolean, default: true },
});

// Five distinct glyph shapes: the `warning` glyph changed from the old
// panel's `▲` (shared with `beneficial`) to `▽`, so no two severities are
// separated by colour alone.
const SEVERITY_GLYPHS = {
  beneficial: "▲",
  informational: "◆",
  warning: "▽",
  harmful: "▼",
  critical: "✕",
};
function glyph(condition) {
  return SEVERITY_GLYPHS[condition.severity] ?? "◆";
}

const VISIBLE_CAP = 6;

const visible = computed(() => props.conditions.slice(0, VISIBLE_CAP));
const overflowCount = computed(() => Math.max(0, props.conditions.length - VISIBLE_CAP));
const overflowItems = computed(() => props.conditions.slice(VISIBLE_CAP));

// The `+N` disclosure (design D7): bounded + scrollable, collapses on
// re-activation or Escape.
const overflowOpen = ref(false);
function toggleOverflow() {
  overflowOpen.value = !overflowOpen.value;
}

// The accessible icon name is the shared condition label rule (the same
// label, duration, and modifier prose the character-status drawer roster
// renders) — one copy in lib/condition_label.js.
const chipName = conditionLabel;
function hasTimer(condition) {
  return typeof condition.remaining_seconds === "number";
}

// The one tooltip of the row. Pointer and keyboard are two sources: the
// icon the pointer rests on wins, else the focused icon.
const tipId = `condition-tip-${useId()}`;
const hoverCode = ref(null);
const focusCode = ref(null);
const tipCode = computed(() => hoverCode.value ?? focusCode.value);
const tipCondition = computed(() =>
  tipCode.value === null ? null : props.conditions[tipCode.value] ?? null,
);
const tipPlace = ref({ left: 0, bottom: 0, tick: 0 });

function place(event) {
  const rect = event.currentTarget.getBoundingClientRect();
  const inset = rect.width / 2;
  tipPlace.value = {
    left: Math.max(4, rect.left + inset - 14),
    bottom: window.innerHeight - rect.top + 6,
    tick: rect.left + inset - Math.max(4, rect.left + inset - 14),
  };
}
function onEnter(event, code) {
  place(event);
  hoverCode.value = code;
}
function onLeave() {
  hoverCode.value = null;
}
function onFocus(event, code) {
  place(event);
  focusCode.value = code;
}
function onBlur() {
  focusCode.value = null;
}
function closeTip() {
  hoverCode.value = null;
  focusCode.value = null;
}

// A condition that stops being committed, or a dock that hides, takes its
// tooltip with it.
watch(tipCondition, (condition) => {
  if (tipCode.value !== null && condition === null) closeTip();
});
// Local indices distinguish duplicate definition codes. A replaced roster
// closes the tooltip so reordering cannot silently retarget its detail.
watch(() => props.conditions, closeTip);
watch(
  () => props.revealed,
  (revealed) => {
    if (!revealed) closeTip();
  },
);
const tipOpen = computed(() => tipCondition.value !== null);
watch(tipOpen, (open) => {
  if (open) {
    window.addEventListener("scroll", closeTip, true);
    window.addEventListener("resize", closeTip);
  } else {
    window.removeEventListener("scroll", closeTip, true);
    window.removeEventListener("resize", closeTip);
  }
});
onBeforeUnmount(() => {
  window.removeEventListener("scroll", closeTip, true);
  window.removeEventListener("resize", closeTip);
});

// Escape closes an open tooltip (then the disclosure) and is consumed only
// while one of them is open, mirroring DesktopNavigation.onToolKeydown: with
// nothing of the row's own open it falls through to the shell's ladder.
function onRowKeydown(event) {
  if (event.key !== "Escape") return;
  if (tipOpen.value) {
    event.stopPropagation();
    event.preventDefault();
    closeTip();
  } else if (overflowOpen.value) {
    event.stopPropagation();
    event.preventDefault();
    overflowOpen.value = false;
  }
}
</script>

<template>
  <div
    v-if="conditions.length > 0"
    class="conditions"
    data-testid="status-panel__conditions"
    @keydown="onRowKeydown"
  >
    <div class="icons">
      <button
        v-for="(condition, index) in visible"
        :key="index"
        type="button"
        class="chip"
        :class="[`chip--${condition.severity}`, { active: tipCode === index }]"
        :data-testid="`status-panel__condition--${condition.code}`"
        :data-severity="condition.severity"
        :data-code="condition.code"
        :aria-label="chipName(condition)"
        :aria-describedby="tipCode === index && tipOpen ? tipId : null"
        @focus="onFocus($event, index)"
        @blur="onBlur"
        @mouseenter="onEnter($event, index)"
        @mouseleave="onLeave"
      >
        <span class="glyph" aria-hidden="true">{{ glyph(condition) }}</span>
      </button>
      <button
        v-if="overflowCount > 0"
        type="button"
        class="chip more"
        :class="{ open: overflowOpen }"
        data-testid="status-panel__condition-overflow"
        :aria-expanded="String(overflowOpen)"
        :aria-label="`剩餘 ${overflowCount} 個狀態`"
        @click="toggleOverflow"
      >
        +{{ overflowCount }}
      </button>
    </div>
    <!-- The disclosure: the hidden conditions' tooltip content as one
         bounded column, in flow, so the bottom-anchored dock grows upward. -->
    <div
      v-if="overflowOpen && overflowCount > 0"
      class="disclosure"
      data-testid="status-panel__condition-disclosure"
    >
      <div
        v-for="(condition, index) in overflowItems"
        :key="index + VISIBLE_CAP"
        class="detail-row"
        :class="`detail--${condition.severity}`"
        :data-testid="`status-panel__condition--${condition.code}`"
        :data-severity="condition.severity"
        :aria-label="chipName(condition)"
      >
        <span class="detail-glyph" aria-hidden="true">{{ glyph(condition) }}</span>
        <span class="detail-label">{{ condition.label ?? condition.code }}</span>
        <span v-if="hasTimer(condition)" class="detail-timer">剩 {{ condition.remaining_seconds }} 秒</span>
        <span
          v-for="modifier in conditionModifiers(condition)"
          :key="modifier.key"
          class="detail-mod"
          :data-testid="`status-panel__condition-mod--${modifier.key}`"
        >{{ modifier.text }}</span>
        <span v-if="conditionSource(condition)" class="detail-source">{{ conditionSource(condition) }}</span>
      </div>
    </div>
    <Teleport to="body">
      <div
        v-if="tipCondition"
        :id="tipId"
        role="tooltip"
        class="condition-tip"
        :class="`detail--${tipCondition.severity}`"
        data-testid="status-panel__condition-tooltip"
        :data-code="tipCondition.code"
        :style="{
          left: `${tipPlace.left}px`,
          bottom: `${tipPlace.bottom}px`,
          '--tip-tick': `${tipPlace.tick}px`,
        }"
      >
        <p class="tip-title">
          <span class="detail-glyph" aria-hidden="true">{{ glyph(tipCondition) }}</span>
          <span class="detail-label">{{ tipCondition.label ?? tipCondition.code }}</span>
        </p>
        <p
          v-if="hasTimer(tipCondition)"
          class="detail-timer"
          data-testid="status-panel__condition-timer"
        >剩 {{ tipCondition.remaining_seconds }} 秒</p>
        <p
          v-for="modifier in conditionModifiers(tipCondition)"
          :key="modifier.key"
          class="detail-mod"
          :data-testid="`status-panel__condition-mod--${modifier.key}`"
        >{{ modifier.text }}</p>
        <p v-if="conditionSource(tipCondition)" class="detail-source">{{ conditionSource(tipCondition) }}</p>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
/* The icon row (vitals-bar-redesign design D3): no fill, no blur, no
   border, no label. It pulls left by the icon's own inset, so each glyph's
   centre stands on the bars' icon column below it, and up and down by the
   air the 22px buttons carry around their glyphs, so the glyphs sit as far
   from the dock's rim and from the bars as the bars sit from the side rims. */
.conditions {
  margin: calc(-3px * var(--ui-scale)) 0 calc(-2px * var(--ui-scale));
  font-family: var(--f-sans);
}

.icons {
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  gap: calc(2px * var(--ui-scale));
  margin-left: calc(-5px * var(--ui-scale));
}

/* An icon: the glyph alone, in its severity's hue, with a dark halo so it
   reads on any art behind the translucent dock. Hover, focus, or an open
   tooltip lifts it to full strength and draws a short brass tick under it. */
.chip {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: none;
  width: calc(22px * var(--ui-scale));
  height: calc(22px * var(--ui-scale));
  padding: 0;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  cursor: default;
  font-family: var(--f-sans);
  opacity: 0.86;
  transition: opacity var(--motion-fast) var(--ease-standard);
}

.chip::after {
  content: "";
  position: absolute;
  left: 50%;
  bottom: calc(1px * var(--ui-scale));
  width: calc(10px * var(--ui-scale));
  height: 1px;
  transform: translateX(-50%);
  background: var(--gold-500);
  opacity: 0;
  transition: opacity var(--motion-fast) var(--ease-standard);
}

.chip:hover,
.chip:focus-visible,
.chip.active {
  opacity: 1;
}

.chip:hover::after,
.chip:focus-visible::after,
.chip.active::after,
.chip.more.open::after {
  opacity: 1;
}

.chip .glyph {
  font-size: var(--text-md);
  line-height: 1;
  text-shadow: 0 1px 1px rgba(0, 0, 0, 0.85);
}

/* `✕` draws thinner than the solid triangles in the text faces; a heavier
   weight gives the critical icon the same visual mass as its neighbours. */
.chip--critical .glyph {
  font-weight: 700;
}

.chip--beneficial,
.detail--beneficial .detail-glyph { color: var(--buff); }
.chip--informational,
.detail--informational .detail-glyph { color: var(--paper-300); }
.chip--warning,
.detail--warning .detail-glyph { color: var(--warn); }
.chip--harmful,
.detail--harmful .detail-glyph { color: var(--debuff); }
.chip--critical,
.detail--critical .detail-glyph { color: var(--crit); }

/* The `+N` icon: the hidden count in the numeral face, same footprint. */
.chip.more {
  width: auto;
  min-width: calc(22px * var(--ui-scale));
  padding: 0 calc(4px * var(--ui-scale));
  color: var(--paper-300);
  font: 600 var(--text-xs)/1 var(--f-num);
  font-variant-numeric: tabular-nums lining-nums;
  cursor: pointer;
}

.chip.more.open,
.chip.more:hover {
  color: var(--paper-50);
}

/* The disclosure: the hidden conditions' detail, one row each, divided by
   hairlines — no box of its own inside the dock. */
.disclosure {
  margin-top: calc(5px * var(--ui-scale));
  max-height: calc(96px * var(--ui-scale));
  overflow-y: auto;
  border-top: var(--line);
  scrollbar-width: thin;
  scrollbar-color: var(--ink-600) transparent;
}

.detail-row {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  column-gap: calc(6px * var(--ui-scale));
  padding: calc(4px * var(--ui-scale)) 0;
  border-bottom: 1px solid rgba(54, 54, 56, 0.6);
  font-size: var(--text-xs);
  line-height: 1.4;
}

.detail-glyph {
  font-size: var(--text-xs);
}

.detail-label {
  color: var(--paper-50);
  font-family: var(--f-serif);
  font-weight: 600;
  letter-spacing: 0.04em;
}

.detail-timer,
.detail-mod {
  margin: 0;
  color: var(--paper-300);
  font-family: var(--f-num);
  font-variant-numeric: tabular-nums lining-nums;
}

/* The tooltip: the navigation's ink plate with its gold tick, hung above
   the icon (the tick on its lower edge points down at the glyph). It is
   fixed to the viewport from the icon's box and never sized by the row. */
.condition-tip {
  position: fixed;
  z-index: var(--z-surface-modal);
  box-sizing: border-box;
  max-width: calc(240px * var(--ui-scale));
  padding: calc(7px * var(--ui-scale)) calc(11px * var(--ui-scale)) calc(7px * var(--ui-scale));
  border: 1px solid var(--band-edge-dim);
  border-radius: var(--radius-sm);
  background: var(--surface-panel);
  box-shadow: 0 calc(8px * var(--ui-scale)) calc(22px * var(--ui-scale)) rgba(0, 0, 0, 0.73);
  color: var(--paper-100);
  font-size: var(--text-xs);
  line-height: 1.45;
  pointer-events: none;
  animation: condition-tip-in var(--motion-fast) var(--ease-standard);
}

.condition-tip::after {
  content: "";
  position: absolute;
  bottom: -1px;
  left: calc(var(--tip-tick, 50%) - 7px * var(--ui-scale));
  width: calc(14px * var(--ui-scale));
  height: 1px;
  background: var(--gold-400);
}

.tip-title {
  display: flex;
  align-items: baseline;
  gap: calc(6px * var(--ui-scale));
  margin: 0 0 calc(2px * var(--ui-scale));
  font-size: var(--text-sm);
}

@keyframes condition-tip-in {
  from { opacity: 0; }
}
</style>
