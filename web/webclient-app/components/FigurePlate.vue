<script setup>
// FigurePlate (OpenSpec change webclient-combat-formation, design D4): the
// glance plate a combat figure other than the controlled one carries in the
// stage's `plates` layer, standing in the plate slot the combat formation
// engine (combat-formation.js) returns, its bottom edge on the figure's head.
//
// - `full` (112×52px·S): the serif name (with the session token only while
//   two drawn participants share the name), then a 4px tapered hit-point
//   stroke beside the tabular readout (the current value bright, `/ max`
//   receding), then a line kept empty for condition glyphs.
// - `compact` (72×36px·S): the stroke and the current value, then the glyph
//   line; the name leaves the layout (the accessible name keeps it).
//
// The stroke fills to the displayed value while a round plays (the caller
// passes `displayHp`'s value as `hpCurrent`), and a pale trailing segment
// follows a drop after the vitals' trail delay, so the damage reads as a gap.
// Chrome follows the HUD panel notes: no box, border, radius or shadow — a
// feathered ground that fades upward and to the sides (so a back-rank face
// behind a front-rank plate still reads through it), and one brass hairline
// crown along the bottom edge. Display-only: `role="group"` with the whole
// reading as its accessible name, no focusable element, no pointer events.
import { computed } from "vue";
import { plateHpPercent, plateLabel } from "./figure-plate.js";

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
});

const compact = computed(() => props.form === "compact");
const percent = computed(() => plateHpPercent(props.hpCurrent, props.hpMaximum));
const strokeWidth = computed(() => `${percent.value ?? 0}%`);
const label = computed(() =>
  plateLabel({ name: props.name, token: props.token, side: props.side, current: props.hpCurrent, maximum: props.hpMaximum }),
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
    :aria-label="label"
    :data-identity="identity"
    :data-side="side"
    :data-form="form"
    :data-target="target ? 'true' : null"
    :data-acting="acting ? 'true' : null"
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
        ><span class="figure-plate__current">{{ current }}</span
        ><span v-if="!compact" class="figure-plate__maximum">/{{ maximum }}</span></span
      >
    </div>
    <div class="figure-plate__glyphs" data-testid="figure-plate-glyphs" aria-hidden="true"></div>
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

/* The ground: the panel ink under a light backdrop blur, feathered so it
   is densest at the plate's foot (over the figure's head) and fades out
   upward and toward both sides. It overhangs the slot above and to the
   sides, so the fade happens outside the type, never across it: the name
   and the readout always sit on the dense part, and a face behind the
   plate's thin edges still reads through. */
.figure-plate::before {
  content: "";
  position: absolute;
  inset: calc(-12px * var(--ui-scale)) calc(-12px * var(--ui-scale)) 0;
  z-index: -1;
  background: var(--panel);
  opacity: 0.78;
  backdrop-filter: blur(calc(3px * var(--ui-scale)));
  -webkit-mask-image:
    linear-gradient(0deg, #000 0%, #000 55%, rgba(0, 0, 0, 0.7) 78%, transparent 100%),
    linear-gradient(90deg, transparent 0%, #000 14%, #000 86%, transparent 100%);
  -webkit-mask-composite: source-in;
  mask-image:
    linear-gradient(0deg, #000 0%, #000 55%, rgba(0, 0, 0, 0.7) 78%, transparent 100%),
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
  font: var(--text-sm)/1.15 var(--f-serif);
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
  font: var(--text-xs)/1.15 var(--f-num);
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
  line-height: 1.15;
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
