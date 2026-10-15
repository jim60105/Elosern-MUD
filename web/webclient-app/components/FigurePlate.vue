<script setup>
// FigurePlate (OpenSpec change webclient-combat-formation, design D4): the
// glance plate a combat figure other than the controlled one carries in the
// stage's `plates` layer, standing in the plate slot the combat formation
// engine (combat-formation.js) returns: above its figure's head, or, in the
// front rank of a two-rank side, on the floor line over its figure's lower
// body. No plate ever covers a head, and nothing covers a plate.
//
// - `full` (112×52px·S): the serif name (with the session token only while
//   two drawn participants share the name), then a 4px tapered hit-point
//   stroke beside the tabular readout (the current value bright, `/ max`
//   receding), then the condition glyph line.
// - `compact` (72×36px·S): the stroke and the current value, then the glyph
//   line; the name leaves the layout (the accessible name keeps it).
//
// Conditions, alarm and keyboard (webclient-combat-figure-plates, design
// D2/D4/D5): the glyph line shows the participant's committed conditions as
// the vitals dock's severity glyphs (ConditionChips' plate variant) — three
// and `+N` on a full plate, the most severe and `+N` on a compact one, most
// severe first — each in a 24px·S hit box bottom-aligned on the slot's
// edge, with the detail only in an on-demand tooltip. At or below
// LOW_HP_THRESHOLD the current value turns the critical hue and a 危險 tag
// opens the glyph line, which then keeps one box fewer on a full plate
// (two) and folds the `+N` into the glyph on a compact one. The plate is a
// `tabindex="-1"` stop of the plates group (plate-group.js); `data-stage-x`
// gives the group its left-to-right order.
//
// The stroke fills to the displayed value while a round plays (the caller
// passes `displayHp`'s value as `hpCurrent`), and a pale trailing segment
// follows a drop after the vitals' trail delay, so the damage reads as a gap.
// Chrome follows the HUD panel notes: no box, border, radius or shadow — a
// feathered ground, densest at the foot, kept inside the slot's height, and
// one brass hairline crown along the bottom edge. `role="group"` with the whole
// reading (and its conditions) as its accessible name; only the glyphs take
// pointer events.
import { computed, inject } from "vue";
import ConditionChips from "./ConditionChips.vue";
import { bySeverity, isLowPlateHp, plateHpPercent, plateLabel } from "./figure-plate.js";

const props = defineProps({
  name: { type: String, default: "" },
  // The session token (`e1`, `a2`, …): always in the accessible name, shown
  // only when `showToken` says the name repeats among the drawn figures.
  token: { type: String, default: "" },
  showToken: { type: Boolean, default: false },
  side: { type: String, default: "foes", validator: (value) => value === "party" || value === "foes" },
  hpCurrent: { type: Number, default: null },
  hpMaximum: { type: Number, default: null },
  form: { type: String, default: "full", validator: (value) => value === "full" || value === "compact" },
  // The engine's plate slot (`box`) in stage pixels: { left, top, width, height }.
  // Without one (a standalone story) the plate lays out in flow.
  box: { type: Object, default: null },
  identity: { type: [Number, String], default: null },
  // Non-colour cues: the focused target and the acting foe.
  target: { type: Boolean, default: false },
  acting: { type: Boolean, default: false },
  // The participant's committed conditions (code, label, severity).
  conditions: { type: Array, default: () => [] },
  // Every change closes an open condition tooltip (AppClient's counter).
  closeSignal: { type: Number, default: 0 },
  // The slot's centre x in stage pixels: the plates group's stage order.
  stageX: { type: Number, default: null },
});

const compact = computed(() => props.form === "compact");
// The client's close counter (AppClient provides it): read reactively here,
// so a plate fading out after leaving combat — whose props are no longer
// patched — still closes its tooltip.
const providedClose = inject("plateTooltipClose", null);
const closeAll = computed(() => props.closeSignal + (providedClose?.value ?? 0));
const percent = computed(() => plateHpPercent(props.hpCurrent, props.hpMaximum));
const strokeWidth = computed(() => `${percent.value ?? 0}%`);
const low = computed(() => isLowPlateHp(props.hpCurrent, props.hpMaximum));
// The glyph line's boxes (design D2): four on a full plate, two on a compact
// one, one fewer when the 危險 tag takes the line's start (two and one). The
// conditions show most severe first; when more than the boxes, the last box
// is the `+N` — or, with a single box, the `+N` folds into the glyph.
const shownConditions = computed(() => bySeverity(props.conditions));
const glyphBoxes = computed(() => (compact.value ? 2 : 4) - (low.value ? (compact.value ? 1 : 2) : 0));
const glyphFold = computed(() => glyphBoxes.value === 1 && shownConditions.value.length > 1);
const glyphCap = computed(() =>
  shownConditions.value.length <= glyphBoxes.value || glyphFold.value ? glyphBoxes.value : glyphBoxes.value - 1,
);
const label = computed(() =>
  plateLabel({
    name: props.name,
    token: props.token,
    side: props.side,
    current: props.hpCurrent,
    maximum: props.hpMaximum,
    conditions: props.conditions,
  }),
);
const style = computed(() =>
  props.box
    ? {
        left: `${props.box.left}px`,
        top: `${props.box.top}px`,
        width: `${props.box.width}px`,
        height: `${props.box.height}px`,
      }
    : null,
);
const current = computed(() => (typeof props.hpCurrent === "number" ? String(props.hpCurrent) : "--"));
const maximum = computed(() => (typeof props.hpMaximum === "number" ? String(props.hpMaximum) : "--"));
</script>

<template>
  <div
    class="figure-plate"
    data-testid="figure-plate"
    role="group"
    tabindex="-1"
    :aria-label="label"
    :data-identity="identity"
    :data-side="side"
    :data-form="form"
    :data-target="target ? 'true' : null"
    :data-acting="acting ? 'true' : null"
    :data-low-hp="low ? 'true' : null"
    :data-stage-x="stageX"
    :style="style"
  >
    <div class="figure-plate__name" :aria-hidden="compact ? 'true' : null" :title="name">
      <span class="figure-plate__name-text">{{ name }}</span>
      <span v-if="showToken && token" class="figure-plate__token" data-testid="figure-plate-token">{{ token }}</span>
    </div>
    <div class="figure-plate__line">
      <span
        class="figure-plate__stroke"
        data-testid="figure-plate-stroke"
        :data-percent="percent ?? ''"
        aria-hidden="true"
      >
        <span class="figure-plate__trail" :style="{ width: strokeWidth }"></span>
        <span class="figure-plate__fill" :style="{ width: strokeWidth }"></span>
      </span>
      <span class="figure-plate__readout" data-testid="figure-plate-readout" aria-hidden="true"
        ><span class="figure-plate__current" :class="{ 'figure-plate__current--low': low }">{{ current }}</span
        ><span v-if="!compact" class="figure-plate__maximum">/{{ maximum }}</span></span
      >
    </div>
    <div class="figure-plate__glyphs" data-testid="figure-plate-glyphs">
      <span v-if="low" class="figure-plate__danger" data-testid="figure-plate-danger" aria-hidden="true">危險</span>
      <ConditionChips
        :conditions="shownConditions"
        variant="plate"
        :cap="glyphCap"
        :tabbable="false"
        :fold="glyphFold"
        :close-signal="closeAll"
      />
    </div>
  </div>
</template>

<style>
/* The plate box is the engine's slot (inline left/top/width/height); the
   lines stack from its top and the glyph line takes what remains above the
   figure's head. Every length is a reference px multiplied once by the
   chrome factor. */
.figure-plate {
  position: absolute;
  box-sizing: border-box;
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr);
  align-content: start;
  padding: calc(2px * var(--ui-scale)) calc(3px * var(--ui-scale)) 0;
  pointer-events: none;
  isolation: isolate;
  color: var(--paper-50);
}
.figure-plate:not([style]) {
  position: relative;
  width: calc(112px * var(--ui-scale));
  height: calc(52px * var(--ui-scale));
}
.figure-plate:not([style])[data-form="compact"] {
  width: calc(72px * var(--ui-scale));
  height: calc(36px * var(--ui-scale));
}

/* The ground: the panel ink under a light backdrop blur, densest at the
   plate's foot and lighter toward its top, feathered out to both sides. It
   never reaches above the plate's own slot, so it can cover nothing the
   formation keeps clear (a head is never under a plate). */
.figure-plate::before {
  content: "";
  position: absolute;
  inset: 0 calc(-12px * var(--ui-scale)) 0;
  z-index: -1;
  background: var(--panel);
  opacity: 0.8;
  backdrop-filter: blur(calc(3px * var(--ui-scale)));
  -webkit-mask-image:
    linear-gradient(0deg, #000 0%, #000 60%, rgba(0, 0, 0, 0.72) 100%),
    linear-gradient(90deg, transparent 0%, #000 14%, #000 86%, transparent 100%);
  -webkit-mask-composite: source-in;
  mask-image:
    linear-gradient(0deg, #000 0%, #000 60%, rgba(0, 0, 0, 0.72) 100%),
    linear-gradient(90deg, transparent 0%, #000 14%, #000 86%, transparent 100%);
  mask-composite: intersect;
}
/* The crown: one brass hairline along the foot, brightest at its centre. */
.figure-plate::after {
  content: "";
  position: absolute;
  left: 6%;
  right: 6%;
  bottom: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--band-edge-dim) 22%, var(--band-edge) 50%, var(--band-edge-dim) 78%, transparent);
}

.figure-plate__name {
  display: flex;
  align-items: baseline;
  gap: calc(4px * var(--ui-scale));
  min-width: 0;
  font: var(--text-sm)/1 var(--f-serif);
  white-space: nowrap;
  text-shadow: 0 1px 1px rgba(0, 0, 0, 0.85);
}
.figure-plate__name-text {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}
.figure-plate__token {
  flex: none;
  font: var(--text-xs)/1 var(--f-num);
  color: var(--paper-300);
  font-variant-numeric: tabular-nums lining-nums;
}
/* Compact: the name leaves the layout; the accessible name keeps it. */
.figure-plate[data-form="compact"] .figure-plate__name {
  display: none;
}

.figure-plate__line {
  display: flex;
  align-items: center;
  gap: calc(4px * var(--ui-scale));
  min-width: 0;
}
/* The stroke: a blunt butt at the spine, a long point at the far end, over
   a faint paper wash (the vitals' own stroke). */
.figure-plate__stroke {
  position: relative;
  flex: 1 1 auto;
  min-width: calc(40px * var(--ui-scale));
  height: calc(4px * var(--ui-scale));
  overflow: hidden;
  background: linear-gradient(90deg, rgba(231, 224, 209, 0.16), rgba(231, 224, 209, 0.07));
  clip-path: polygon(0 0, calc(100% - 10px * var(--ui-scale)) 0, 100% 50%, calc(100% - 10px * var(--ui-scale)) 100%, 0 100%);
  filter: drop-shadow(0 1px 0 rgba(0, 0, 0, 0.75));
}
.figure-plate[data-form="compact"] .figure-plate__stroke {
  min-width: calc(30px * var(--ui-scale));
}
.figure-plate__trail,
.figure-plate__fill {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
}
.figure-plate__trail {
  background: rgba(255, 255, 255, 0.28);
  transition: width var(--motion-trail) ease var(--motion-trail-delay);
}
.figure-plate__fill {
  transition: width var(--motion-slow) var(--ease-standard);
}
.figure-plate__fill::after {
  content: "";
  position: absolute;
  inset: 0 0 50% 0;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.22), transparent);
}
/* Allies read in the vitals' hit-point hue, foes in the foe gauge's red. */
.figure-plate[data-side="party"] .figure-plate__fill {
  background: linear-gradient(90deg, #8c2f2a, var(--vit-hp));
}
.figure-plate[data-side="foes"] .figure-plate__fill {
  background: linear-gradient(90deg, #7c2026, #b8342e 45%, var(--vit-hp));
}

/* The readout: the numeral role (proportional sans, tabular lining
   figures); the current value bright, the maximum a size smaller and two
   steps of ink down. */
.figure-plate__readout {
  flex: none;
  display: inline-flex;
  align-items: baseline;
  font-family: var(--f-num);
  font-variant-numeric: tabular-nums lining-nums;
  line-height: 1;
  letter-spacing: 0;
  text-shadow: 0 1px 1px rgba(0, 0, 0, 0.85);
}
.figure-plate__current {
  color: var(--paper-50);
  font-size: var(--text-sm);
  font-weight: 600;
}
.figure-plate__maximum {
  color: var(--paper-500);
  font-size: var(--text-xs);
}

/* The low-HP alarm (design D5): the current value in the critical hue and
   the 危險 tag in the vitals marker's style — text and colour together,
   no pulse (many plates pulsing would compete). */
.figure-plate__current--low {
  color: var(--crit);
}
.figure-plate__danger {
  flex: none;
  align-self: center;
  box-sizing: border-box;
  padding: 0 calc(3px * var(--ui-scale));
  border: 1px solid var(--seal-600);
  border-radius: 2px;
  background: rgba(20, 8, 8, 0.55);
  color: var(--crit);
  font: 700 var(--text-xs)/1 var(--f-sans);
  letter-spacing: 0.02em;
  text-shadow: none;
}

/* The glyph line (design D2): the last grid row (16px·S on a full plate,
   17px·S on a compact one). Its 24px·S hit boxes stand on the slot's lower
   edge and rise over the lower part of the readout line, which takes no
   pointer events, so no box ever leaves the slot. Empty rows render
   nothing. */
.figure-plate__glyphs {
  grid-row: 3;
  align-self: end;
  display: flex;
  align-items: flex-end;
  gap: calc(2px * var(--ui-scale));
  min-width: 0;
  height: calc(24px * var(--ui-scale));
  margin: 0 calc(-3px * var(--ui-scale));
}
.figure-plate[data-form="compact"] {
  grid-template-rows: auto minmax(0, 1fr);
}
.figure-plate[data-form="compact"] .figure-plate__glyphs {
  grid-row: 2;
}
.figure-plate__glyphs > .figure-plate__danger {
  align-self: flex-end;
  margin: 0 0 calc(1px * var(--ui-scale)) calc(3px * var(--ui-scale));
}
.figure-plate[data-form="compact"] .figure-plate__glyphs > .figure-plate__danger {
  margin-bottom: 0;
}

/* Keyboard focus (the plates group): the global gold double ring; a
   focused target keeps its paper brackets inside it. */
.figure-plate:focus-visible[data-target="true"] {
  box-shadow:
    var(--focus),
    inset calc(2px * var(--ui-scale)) 0 0 var(--paper-50),
    inset calc(-2px * var(--ui-scale)) 0 0 var(--paper-50);
}

/* Non-colour cues (webclient-contextual-hud "Combat identity and status
   remain legible"): the focused target is bracketed by two paper rules at
   the plate's sides; the acting foe's crown doubles. */
.figure-plate[data-target="true"] {
  box-shadow:
    inset calc(2px * var(--ui-scale)) 0 0 var(--paper-50),
    inset calc(-2px * var(--ui-scale)) 0 0 var(--paper-50);
}
.figure-plate[data-acting="true"]::after {
  height: calc(3px * var(--ui-scale));
  background: none;
  border-top: 1px solid var(--band-edge);
  border-bottom: 1px solid var(--band-edge);
  box-sizing: border-box;
}
</style>
