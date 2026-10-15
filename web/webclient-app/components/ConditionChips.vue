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
// hung above the dock would be clipped. Once rendered it measures itself:
// it shifts left to stay 4px inside the viewport (its tick still points at
// the icon) and opens below the icon when it would cross the viewport's top.
// A scroll or resize while it is open closes it rather than leaving it adrift.
//
// The `plate` variant (webclient-combat-figure-plates, design D2/D3) is the
// row a combat figure plate carries: `cap` icons, the `+N` icon opening a
// tooltip of the hidden conditions instead of the dock's in-flow disclosure
// (which would grow the plate out of its slot), `fold` carrying the hidden
// conditions in the last icon instead of a `+N`, its own test hooks
// (`figure-plate__condition…`), and icons out of the tab order when the
// plate group manages focus (`tabbable=false`).
import { computed, nextTick, onBeforeUnmount, ref, useId, watch } from "vue";
import { conditionLabel, conditionModifiers, conditionSource } from "../lib/condition_label.js";

const props = defineProps({
  // The committed `status.conditions[]` array (or a combat participant's
  // `conditions`: code, label and severity only).
  conditions: { type: Array, default: () => [] },
  // Whether the dock showing the row is revealed: a hiding dock fires no
  // mouseleave, so the open tooltip is dropped here.
  revealed: { type: Boolean, default: true },
  // How many icons show before the `+N` icon.
  cap: { type: Number, default: 6 },
  // false: no icon is in the tab order (a roving group focuses them).
  tabbable: { type: Boolean, default: true },
  variant: { type: String, default: "dock", validator: (value) => value === "dock" || value === "plate" },
  // Plate only: no `+N` icon; the last visible icon carries the hidden ones.
  fold: { type: Boolean, default: false },
  // Every change closes the open tooltip (a round starts, the mode changes).
  closeSignal: { type: Number, default: 0 },
});

const plate = computed(() => props.variant === "plate");
const hook = computed(() => (plate.value ? "figure-plate__condition" : "status-panel__condition"));
const tabindex = computed(() => (props.tabbable ? null : "-1"));

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

const visibleCap = computed(() => Math.max(1, Math.floor(props.cap)));
const visible = computed(() => props.conditions.slice(0, visibleCap.value));
const hiddenCount = computed(() => Math.max(0, props.conditions.length - visibleCap.value));
const overflowItems = computed(() => props.conditions.slice(visibleCap.value));
// Folded, the hidden conditions ride the last visible icon: no `+N` icon.
const folded = computed(() => plate.value && props.fold && hiddenCount.value > 0);
const overflowCount = computed(() => (folded.value ? 0 : hiddenCount.value));
function carriesHidden(index) {
  return folded.value && index === visible.value.length - 1;
}

// The `+N` disclosure (design D7): bounded + scrollable, collapses on
// re-activation or Escape.
const overflowOpen = ref(false);
function toggleOverflow() {
  overflowOpen.value = !overflowOpen.value;
}

// The accessible icon name is the shared condition label rule (the same
// label, duration, and modifier prose the character-status drawer roster
// renders) — one copy in lib/condition_label.js.
function chipName(condition, index) {
  if (index !== undefined && carriesHidden(index)) {
    return [condition, ...overflowItems.value].map(conditionLabel).join("；");
  }
  return conditionLabel(condition);
}
const overflowName = computed(() =>
  plate.value
    ? `另有 ${overflowCount.value} 個狀態：${overflowItems.value.map(conditionLabel).join("；")}`
    : `剩餘 ${overflowCount.value} 個狀態`,
);
function hasTimer(condition) {
  return typeof condition.remaining_seconds === "number";
}

// The one tooltip of the row. Pointer and keyboard are two sources: the
// icon the pointer rests on wins, else the focused icon. A code is an icon
// index, or OVERFLOW for the plate's `+N` icon.
const OVERFLOW = "overflow";
const tipId = `condition-tip-${useId()}`;
const hoverCode = ref(null);
const focusCode = ref(null);
const tipCode = computed(() => hoverCode.value ?? focusCode.value);
// The conditions the open tooltip describes: one for an icon, the hidden
// ones for the `+N` icon, an icon's own plus the hidden ones when folded.
const tipItems = computed(() => {
  const code = tipCode.value;
  if (code === null) return [];
  if (code === OVERFLOW) return overflowCount.value > 0 ? overflowItems.value : [];
  const condition = props.conditions[code];
  if (!condition || code >= visible.value.length) return [];
  return carriesHidden(code) ? [condition, ...overflowItems.value] : [condition];
});
const tipCondition = computed(() => tipItems.value[0] ?? null);
const tipRef = ref(null);
const tipPlace = ref({ left: 0, bottom: 0, top: null, tick: 0 });
let anchorRect = null;

const TIP_GAP = 6;
const VIEWPORT_INSET = 4;
function place(event) {
  anchorEl = event.currentTarget;
  const rect = event.currentTarget.getBoundingClientRect();
  anchorRect = { left: rect.left, top: rect.top, bottom: rect.bottom, width: rect.width };
  const centre = rect.left + rect.width / 2;
  const left = Math.max(VIEWPORT_INSET, centre - 14);
  tipPlace.value = { left, bottom: window.innerHeight - rect.top + TIP_GAP, top: null, tick: centre - left };
}
// Measured once rendered: shift left inside the viewport, flip below the
// icon when the tip would cross the viewport's top.
async function keepInView() {
  await nextTick();
  const tip = tipRef.value;
  if (!tip || !anchorRect) return;
  const box = tip.getBoundingClientRect();
  const centre = anchorRect.left + anchorRect.width / 2;
  let left = tipPlace.value.left;
  const overflowRight = left + box.width - (window.innerWidth - VIEWPORT_INSET);
  if (overflowRight > 0) left = Math.max(VIEWPORT_INSET, left - overflowRight);
  const flip = anchorRect.top - TIP_GAP - box.height < VIEWPORT_INSET;
  tipPlace.value = {
    left,
    bottom: flip ? null : tipPlace.value.bottom,
    top: flip ? anchorRect.bottom + TIP_GAP : null,
    tick: centre - left,
  };
}
function onEnter(event, code) {
  place(event);
  hoverCode.value = code;
  keepInView();
}
function onLeave() {
  hoverCode.value = null;
}
function onFocus(event, code) {
  place(event);
  focusCode.value = code;
  keepInView();
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
watch(() => props.closeSignal, closeTip);
// Local indices distinguish duplicate definition codes. A roster whose
// content under the open tooltip changes closes it, so reordering cannot
// silently retarget its detail; a commit that only replaces the array with
// the same content (every combat revision does) keeps it open.
function signature(items) {
  return JSON.stringify(
    items.map((c) => [c.code, c.label ?? null, c.severity, c.remaining_seconds ?? null, c.modifiers ?? null, c.provenance ?? null]),
  );
}
watch(
  () => [tipCode.value, signature(tipItems.value)],
  ([code, next], [previousCode, previous]) => {
    if (code !== null && code === previousCode && next !== previous) closeTip();
  },
);
watch(
  () => props.revealed,
  (revealed) => {
    if (!revealed) closeTip();
  },
);
const tipOpen = computed(() => tipCondition.value !== null);
// A scroll moves the icon only when it scrolls the document or a container
// of the icon; any other scroll (the message log following a new line)
// leaves the tooltip open.
let anchorEl = null;
function onScroll(event) {
  const target = event.target;
  if (!anchorEl || target === document || target === document.documentElement || target === window || (target?.contains && target.contains(anchorEl))) {
    closeTip();
  }
}
// Plate variant: an open tooltip claims the next Escape wherever focus is
// (a focused plate, or the dock while the pointer rests on a glyph), so the
// plates group never moves focus away from a tooltip left open.
function onWindowEscape(event) {
  if (event.key !== "Escape" || !tipOpen.value) return;
  event.stopPropagation();
  event.preventDefault();
  closeTip();
}
function unlisten() {
  window.removeEventListener("scroll", onScroll, true);
  window.removeEventListener("resize", closeTip);
  window.removeEventListener("keydown", onWindowEscape, true);
}
watch(tipOpen, (open) => {
  if (open) {
    window.addEventListener("scroll", onScroll, true);
    window.addEventListener("resize", closeTip);
    if (plate.value) window.addEventListener("keydown", onWindowEscape, true);
  } else {
    unlisten();
  }
});
onBeforeUnmount(unlisten);

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
    :class="{ 'conditions--plate': plate }"
    :data-testid="`${hook}s`"
    @keydown="onRowKeydown"
  >
    <div class="icons">
      <button
        v-for="(condition, index) in visible"
        :key="`${index}:${condition.code}`"
        type="button"
        class="chip"
        :class="[`chip--${condition.severity}`, { active: tipCode === index, carries: carriesHidden(index) }]"
        :tabindex="tabindex"
        :data-testid="`${hook}--${condition.code}`"
        :data-severity="condition.severity"
        :data-code="condition.code"
        :data-carries="carriesHidden(index) ? String(hiddenCount) : null"
        :aria-label="chipName(condition, index)"
        :aria-describedby="tipCode === index && tipOpen ? tipId : null"
        @focus="onFocus($event, index)"
        @blur="onBlur"
        @mouseenter="onEnter($event, index)"
        @mouseleave="onLeave"
      >
        <span class="glyph" aria-hidden="true">{{ glyph(condition) }}</span>
      </button>
      <!-- The plate's `+N`: a tooltip of the hidden conditions. -->
      <button
        v-if="overflowCount > 0 && plate"
        type="button"
        class="chip more"
        :class="{ active: tipCode === OVERFLOW }"
        :tabindex="tabindex"
        :data-testid="`${hook}-overflow`"
        :aria-label="overflowName"
        :aria-describedby="tipCode === OVERFLOW && tipOpen ? tipId : null"
        @focus="onFocus($event, OVERFLOW)"
        @blur="onBlur"
        @mouseenter="onEnter($event, OVERFLOW)"
        @mouseleave="onLeave"
      >
        +{{ overflowCount }}
      </button>
      <button
        v-else-if="overflowCount > 0"
        type="button"
        class="chip more"
        :class="{ open: overflowOpen }"
        :tabindex="tabindex"
        :data-testid="`${hook}-overflow`"
        :aria-expanded="String(overflowOpen)"
        :aria-label="overflowName"
        @click="toggleOverflow"
      >
        +{{ overflowCount }}
      </button>
    </div>
    <!-- The disclosure: the hidden conditions' tooltip content as one
         bounded column, in flow, so the bottom-anchored dock grows upward. -->
    <div
      v-if="!plate && overflowOpen && overflowCount > 0"
      class="disclosure"
      :data-testid="`${hook}-disclosure`"
    >
      <div
        v-for="(condition, index) in overflowItems"
        :key="index + visibleCap"
        class="detail-row"
        :class="`detail--${condition.severity}`"
        :data-testid="`${hook}--${condition.code}`"
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
          :data-testid="`${hook}-mod--${modifier.key}`"
        >{{ modifier.text }}</span>
        <span v-if="conditionSource(condition)" class="detail-source">{{ conditionSource(condition) }}</span>
      </div>
    </div>
    <Teleport to="body">
      <div
        v-if="tipCondition"
        :id="tipId"
        ref="tipRef"
        role="tooltip"
        class="condition-tip"
        :class="[`detail--${tipCondition.severity}`, { 'condition-tip--below': tipPlace.top !== null, 'condition-tip--list': tipItems.length > 1 }]"
        :data-testid="`${hook}-tooltip`"
        :data-code="tipCondition.code"
        :data-placement="tipPlace.top !== null ? 'below' : 'above'"
        :style="{
          left: `${tipPlace.left}px`,
          bottom: tipPlace.top === null ? `${tipPlace.bottom}px` : null,
          top: tipPlace.top === null ? null : `${tipPlace.top}px`,
          '--tip-tick': `${tipPlace.tick}px`,
        }"
      >
        <div
          v-for="(item, index) in tipItems"
          :key="index"
          class="tip-item"
          :class="`detail--${item.severity}`"
        >
          <p class="tip-title">
            <span class="detail-glyph" aria-hidden="true">{{ glyph(item) }}</span>
            <span class="detail-label">{{ item.label ?? item.code }}</span>
          </p>
          <p
            v-if="hasTimer(item)"
            class="detail-timer"
            :data-testid="`${hook}-timer`"
          >剩 {{ item.remaining_seconds }} 秒</p>
          <p
            v-for="modifier in conditionModifiers(item)"
            :key="modifier.key"
            class="detail-mod"
            :data-testid="`${hook}-mod--${modifier.key}`"
          >{{ modifier.text }}</p>
          <p v-if="conditionSource(item)" class="detail-source">{{ conditionSource(item) }}</p>
        </div>
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

/* Below the icon (too close to the viewport's top): the tick moves to the
   upper edge and points up at the glyph. */
.condition-tip--below::after {
  bottom: auto;
  top: -1px;
}

/* Several conditions (a plate's `+N`, or a folded icon): one block each,
   divided by a hairline. */
.condition-tip--list .tip-item + .tip-item {
  margin-top: calc(5px * var(--ui-scale));
  padding-top: calc(5px * var(--ui-scale));
  border-top: 1px solid rgba(54, 54, 56, 0.9);
}

/* The plate variant (webclient-combat-figure-plates, design D2): 24px·S
   hit boxes, the glyph at the smallest text step, the row flush with the
   plate's own edge so no box leaves the slot. */
.conditions--plate {
  margin: 0;
}
.conditions--plate .icons {
  gap: calc(2px * var(--ui-scale));
  margin-left: 0;
}
.conditions--plate .chip {
  width: calc(24px * var(--ui-scale));
  height: calc(24px * var(--ui-scale));
  align-items: flex-end;
  padding-bottom: calc(2px * var(--ui-scale));
  box-sizing: border-box;
  pointer-events: auto;
  opacity: 0.92;
}
.conditions--plate .chip .glyph {
  font-size: var(--text-xs);
}
.conditions--plate .chip::after {
  bottom: 0;
}
.conditions--plate .chip.more {
  min-width: calc(24px * var(--ui-scale));
  padding: 0 calc(2px * var(--ui-scale)) calc(2px * var(--ui-scale));
  line-height: 1;
}
/* A folded icon carries hidden conditions: a small drawn plus at its
   upper right (an icon mark, not text). */
.conditions--plate .chip.carries::before {
  content: "";
  position: absolute;
  top: calc(6px * var(--ui-scale));
  right: calc(2px * var(--ui-scale));
  width: calc(6px * var(--ui-scale));
  height: calc(6px * var(--ui-scale));
  background:
    linear-gradient(currentColor, currentColor) center / 100% 1.5px no-repeat,
    linear-gradient(currentColor, currentColor) center / 1.5px 100% no-repeat;
  filter: drop-shadow(0 1px 0 rgba(0, 0, 0, 0.85));
}

@keyframes condition-tip-in {
  from { opacity: 0; }
}
</style>
