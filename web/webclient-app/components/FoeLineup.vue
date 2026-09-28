<script setup>
// FoeLineup (OpenSpec change webclient-combat-foes-on-stage, design D1-D5;
// the AVG stage design §4 and §10.2): the combat foes standing opposite the
// player in the `actor-right` anchor.
// - At most three foes, in presenter order, as one `StageActor` each
//   (`side="right"`, never dimmed); further foes stand only in the
//   participant frame, which stays the complete numbers panel.
// - A depth-staged row (foe-lineup.js): the first foe stands in front at the
//   anchor's right edge, and each later foe stands behind the one before it,
//   further toward the stage centre and smaller. The whole row steps in from
//   the anchor until the front foe's face clears the participant frame
//   (`--foe-face-clear`).
// - Each foe carries a decorative hit-point gauge on the stage floor (the
//   same baseline as the scene caption) with a trailing bar that makes damage
//   visible; no numerals, tokens, names, or states — those are the frame's.
// - Each slot exposes `data-portrait-ref`, the art-catalog key the combat
//   beats name, so the beat presentation can address a foe.
// - A foe joining or leaving the active set inside combat enters or fades
//   (`TransitionGroup name="foe"`); the others glide to their new places.
//   The leaving slot is inert from the commit on.
// - While a combat round plays (webclient-combat-beat-choreography D5), the
//   row stands the round's pre-round foes (`stage.foes`), so a foe the round
//   defeats stays until its own defeat beat; each foe plays its beat gesture
//   (`stage.gestures`), and each gauge follows the displayed hit points.
// Decorative art: no focusable element, no pointer events, hidden from
// assistive technology (the frame is the accessible list of participants).
import { computed } from "vue";
import StageActor from "./StageActor.vue";
import { FOE_LINEUP_MAX, foeHpPercent, foeSlots } from "./foe-lineup.js";
import { inertWhileLeaving } from "../lib/transition_hooks.js";

const props = defineProps({
  // The committed combat participants to stand on the stage: the active
  // foes, in presenter order (AppClient filters them).
  foes: { type: Array, default: () => [] },
  // The committed `art` panel; its `portrait_catalog` resolves each foe.
  artPanel: { type: Object, default: null },
  // The EFFECTIVE motion level: at `off` the transitions have no CSS phase.
  motionLevel: { type: String, default: "full" },
  // The cap (three); stories and tests pass it only to show the cap.
  max: { type: Number, default: FOE_LINEUP_MAX },
  // The playing round's stage (`view.beatStage`), or null: its `foes` stand
  // instead of `foes`, and its `gestures` animate them.
  stage: { type: Object, default: null },
  // The hit points the playing round displays (`view.displayHp`), keyed by
  // portrait reference, or null.
  displayHp: { type: Object, default: null },
});

// `settled` fires when a foe that left the row has finished fading (at `off`,
// in the commit's frame), so the client can release the room it held.
const emit = defineEmits(["settled"]);

const shown = computed(() =>
  (props.stage ? props.stage.foes : props.foes).slice(0, Math.min(props.max, FOE_LINEUP_MAX)),
);
const slots = computed(() => foeSlots(shown.value.length));

// The raw catalog entry the participant's `portrait_ref` names: a pending
// entry keeps its own placeholder card, and a null or unknown reference
// falls to the StageActor's name placeholder. The client builds no key.
function entryFor(participant) {
  const ref = participant.portrait_ref;
  if (ref === null || ref === undefined) {
    return null;
  }
  return props.artPanel?.portrait_catalog?.[ref] ?? null;
}

function slotStyle(index) {
  const slot = slots.value[index];
  return {
    "--foe-index": index,
    "--foe-scale": slot.scale,
    "--foe-lift": slot.lift,
    bottom: `${slot.lift * 100}%`,
    height: `${slot.scale * 100}%`,
    right: `${slot.right * 100}%`,
    zIndex: slot.z,
  };
}

// The gauge reads the displayed value while a round plays, else the
// committed one.
function gaugeWidth(participant) {
  const ref = participant.portrait_ref;
  const displayed = ref == null ? undefined : props.displayHp?.[ref];
  const row = typeof displayed === "number" ? { ...participant, hp_current: displayed } : participant;
  return `${foeHpPercent(row) ?? 0}%`;
}

// The foe's beat gesture for the current step, or null.
function gestureFor(participant) {
  const ref = participant.portrait_ref;
  return (ref != null && props.stage?.gestures?.[ref]) || null;
}
</script>

<template>
  <div
    class="foe-lineup"
    data-testid="foe-lineup"
    :data-count="shown.length"
    :style="{ '--foe-front-scale': slots[0]?.scale ?? 1 }"
    aria-hidden="true"
  >
    <TransitionGroup
      name="foe"
      :css="motionLevel !== 'off'"
      v-bind="inertWhileLeaving"
      @after-leave="emit('settled')"
    >
      <div
        v-for="(p, i) in shown"
        :key="p.identity"
        class="foe-lineup__slot"
        :class="{ 'foe-lineup__slot--before': i < shown.length - 1 }"
        data-testid="foe-slot"
        :data-portrait-ref="p.portrait_ref ?? ''"
        :data-beat="gestureFor(p)?.gesture ?? null"
        :style="slotStyle(i)"
      >
        <StageActor
          :portrait="entryFor(p)"
          :name="p.display_name"
          side="right"
          :dimmed="false"
          :motion-level="motionLevel"
          :gesture="gestureFor(p)?.gesture ?? null"
          :gesture-key="stage?.key ?? null"
          :float-amount="gestureFor(p)?.amount ?? null"
        />
        <div class="foe-lineup__gauge" data-testid="foe-gauge">
          <span class="foe-lineup__ghost" :style="{ width: gaugeWidth(p) }"></span>
          <span class="foe-lineup__fill" :style="{ width: gaugeWidth(p) }"></span>
        </div>
      </div>
    </TransitionGroup>
  </div>
</template>

<style>
/* The row (design D2): the anchor's box, stepped in from the anchor's right
   edge until the front foe's face clears the participant frame
   (`--foe-face-clear`, tokens.css). Slots are absolutely placed inside it; their
   percentages are of the anchor (height for heights, width for offsets). */
.foe-lineup {
  position: absolute;
  bottom: 0;
  right: calc(
    max(var(--actor-right-inset), var(--foe-face-clear) - var(--actor-h) * var(--foe-front-scale, 1) / 3) -
      var(--actor-right-inset)
  );
  width: 100%;
  height: 100%;
  pointer-events: none;
  /* The front foe's scale sets the inset, so a new front foe (the old one
     fell) glides the row in step with its slots. */
  transition: right calc(var(--motion-actor) * var(--motion-travel)) var(--ease-standard);
}

/* One foe. Re-slotting (a foe joining or leaving) glides the others to their
   new place and size through `right` and `height`; the base transition never
   names `transform`, so TransitionGroup's FLIP move stays off (a FLIP would
   move the box but jump its size). Below `full` the glide is instant. */
.foe-lineup__slot {
  position: absolute;
  bottom: 0;
  aspect-ratio: 2 / 3;
  transition:
    right calc(var(--motion-actor) * var(--motion-travel)) var(--ease-standard),
    bottom calc(var(--motion-actor) * var(--motion-travel)) var(--ease-standard),
    height calc(var(--motion-actor) * var(--motion-travel)) var(--ease-standard);
}
.foe-lineup__slot > .stage-actor {
  height: 100%;
}
/* Depth: a foe that stands in front of another casts a soft shadow onto it,
   so overlapping figures separate even when their art shares a backdrop. */
.foe-lineup__slot--before .reference-artwork {
  filter: drop-shadow(-14px 0 18px rgba(4, 3, 6, 0.55));
}

/* A foe is a figure among figures: its portrait's flat backdrop gives way
   sooner than the player's, so neighbours overlap as bodies rather than as
   pale cards. */
.foe-lineup .stage-actor .reference-artwork img {
  --actor-mask-shape: radial-gradient(ellipse 48% 58% at 49% 45%, #000 46%, transparent 100%);
}

/* The placeholder at the slot's scale: the ring and the initial shrink with
   the figure, so a back foe's placeholder never looks larger than its body. */
.foe-lineup .stage-actor .reference-artwork__placeholder-glyph {
  width: calc(clamp(88px, 11vh, 132px) * var(--foe-scale, 1));
  font-size: calc(clamp(44px, 5.6vh, 66px) * var(--foe-scale, 1));
}
.foe-lineup .stage-actor .reference-artwork__placeholder-label {
  font-size: calc(var(--text-md) * max(0.86, var(--foe-scale, 1)));
}

/* The decorative hit-point gauge (design D5; AVG stage design §10.2): a slim
   track on the stage floor, on the scene caption's baseline above the
   expanded command-line row, centred under the figure. A dark trough with the
   caption plate's gold hairline keeps it legible over light and dark art; the
   fill is the vitals' hit-point red, and the pale trailing bar lags behind a
   drop so the damage shows as a gap (the vitals' own trail tokens). */
.foe-lineup__gauge {
  position: absolute;
  left: 50%;
  bottom: calc(var(--command-line-h, 44px) + 12px + (var(--scene-caption-h, 34px) - 8px) / 2 - var(--actor-h) * var(--foe-lift, 0));
  width: clamp(72px, 44%, 168px);
  height: 8px;
  box-sizing: border-box;
  transform: translateX(-50%);
  padding: 1px;
  border: 1px solid rgba(202, 183, 138, 0.42);
  border-radius: 99px;
  background: rgba(8, 7, 10, 0.82);
  box-shadow:
    0 0 0 1px rgba(0, 0, 0, 0.55),
    0 3px 10px rgba(0, 0, 0, 0.65);
  overflow: hidden;
}
.foe-lineup__ghost,
.foe-lineup__fill {
  position: absolute;
  top: 1px;
  bottom: 1px;
  left: 1px;
  max-width: calc(100% - 2px);
  border-radius: 99px;
}
.foe-lineup__ghost {
  background: rgba(244, 226, 200, 0.55);
  transition: width var(--motion-trail) ease var(--motion-trail-delay);
}
.foe-lineup__fill {
  background: linear-gradient(90deg, #7c2026, #b8342e 45%, var(--vit-hp));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.22);
  transition: width var(--motion-slow) var(--ease-standard);
}

/* A defeated foe's gauge thins away with its figure
   (webclient-combat-beat-choreography D5), so the slot that leaves after
   the defeat beat is already empty. */
.foe-lineup__slot[data-beat="defeat"] > .foe-lineup__gauge {
  opacity: 0;
  transition: opacity var(--motion-beat-defeat) var(--ease-exit);
}

/* Membership inside combat (design D3): a joining foe slides in from the
   right as it fades in; a leaving foe (defeated, fled) fades where it stands
   while the others glide into its place. */
.foe-lineup > .foe-enter-active {
  transition:
    opacity var(--motion-actor) var(--ease-standard),
    transform var(--motion-actor) var(--ease-enter),
    right calc(var(--motion-actor) * var(--motion-travel)) var(--ease-standard),
    height calc(var(--motion-actor) * var(--motion-travel)) var(--ease-standard);
}
.foe-lineup > .foe-leave-active {
  transition: opacity var(--motion-actor) var(--ease-exit);
}
.foe-lineup > .foe-enter-from {
  opacity: 0;
  transform: translateX(calc(var(--motion-shift-lg) * 1.5 * var(--motion-travel)));
}
.foe-lineup > .foe-leave-to {
  opacity: 0;
}
</style>
