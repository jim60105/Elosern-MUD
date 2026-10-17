<script setup>
// FoeLineup (OpenSpec changes webclient-combat-foes-on-stage and
// webclient-combat-formation, design D1/D3/D4): the combat foes standing
// opposite the party.
// - Every foe that has not fled up to the line-up's maximum (`max`, 16 minus the drawn
//   party, never above FOE_STAGE_MAX), in presenter order, as one
//   `StageActor` each (`side="right"`, never dimmed).
// - In combat the `actor-right` anchor spans the stage, so each slot stands
//   at the box the combat formation engine gives it (`formation.figures`,
//   stage pixels) at the scale the party shares; a re-formed line glides
//   every slot's box together (`glide`), and the shell's formation glide
//   (composables/use-formation-glide.js) drives the inner `.formation-figure`
//   wrapper when a foe appears, so its height matches every other figure's
//   in every frame.
// - Names, hit points and cues live on the figure plates (FigurePlate.vue in
//   the stage's `plates` layer), not on the stage floor.
// - Each foe's figure is the canonical artwork descriptor its combat
//   participant row's catalog reference names, resolved against the committed
//   `art` panel — or, while a held round stands the pre-round roster after
//   combat ended, against the retained catalog that round captured. The row
//   reference itself is the admission fact, so a participant the catalog does
//   not carry is a local failure while an unadmitted one is expected absence.
// - Each slot exposes `data-portrait-ref`, the art-catalog key the combat
//   beats name, so the beat presentation can address a foe.
// - A knocked-out or defeated foe keeps its slot in its defeated look
//   (webclient-combat-defeated-foes D1/D5; StageActor's `fallen`), so a
//   defeat never re-forms the line. A foe joining or fleeing inside combat
//   enters or fades (`TransitionGroup name="foe"`); the leaving slot is inert
//   from the commit on and fades where it stands.
// - While a combat round plays (webclient-combat-beat-choreography D5), the
//   row stands the round's pre-round foes (`stage.foes`); a foe the round
//   defeats stands in its pre-round look until its own defeat beat collapses
//   it (`fallen`, from the stage); each foe plays its beat gesture
//   (`stage.gestures`).
// - During the stage target step (webclient-combat-stage-target-picking D4,
//   `targeting`): every foe outside the focused position's lit set takes the
//   dialogue listener dim through StageActor's `dimmed` (a fallen foe keeps
//   its fallen look instead, lit or not); a lit foe carries
//   `data-target-focus` (a pulsing ring at `full`, a static one below); each
//   selectable foe carries one hit area over its box, the only element of the
//   line-up that takes a pointer. No box, z or position changes.
// Decorative art: no focusable element, no pointer events outside the step's
// hit areas, hidden from assistive technology (the plates carry each foe's
// accessible reading; the card's live region the step's).
import { computed } from "vue";
import StageActor from "./StageActor.vue";
import { FOE_STAGE_MAX, fallenLook } from "./foe-lineup.js";
import { inertWhileLeaving } from "../lib/transition_hooks.js";

const props = defineProps({
  // The committed combat participants to stand on the stage: the foes that
  // have not fled, in presenter order (AppClient filters them).
  foes: { type: Array, default: () => [] },
  // The committed `art` panel; its `portrait_catalog` resolves each foe.
  artPanel: { type: Object, default: null },
  // The EFFECTIVE motion level: at `off` the transitions have no CSS phase.
  motionLevel: { type: String, default: "full" },
  // The line-up's maximum: 16 minus the drawn party (AppClient), never above
  // FOE_STAGE_MAX.
  max: { type: Number, default: FOE_STAGE_MAX },
  // The playing round's stage (`view.beatStage`), or null: its `foes` stand
  // instead of `foes`, and its `gestures` animate them.
  stage: { type: Object, default: null },
  // The engine's foe side (`formation.foes`: `{ figures: [{ box, z }] }`),
  // or null outside a measured formation (stories, layout-free tests): the
  // slots then fall back to an unpositioned default.
  formation: { type: Object, default: null },
  // Whether a re-formed line glides (false on a resize, a reconnect, and
  // below `full`).
  glide: { type: Boolean, default: true },
  // The displayed fallen looks, identity -> "defeated" | "down" (AppClient:
  // the playing round's stage, else the committed states), or null, when
  // each foe's own `state` decides (stories, standalone use).
  fallen: { type: Object, default: null },
  // A change of look lands in the commit's frame (a reload or a reconnect).
  fallInstant: { type: Boolean, default: false },
  // The stage target step (stage-targeting.js `targetingFor`), or null
  // outside it: `{ lit, selectable, selected }` Sets of String(identity).
  targeting: { type: Object, default: null },
});

// `settled` fires when a foe that left the row has finished fading (at `off`,
// in the commit's frame), so the client can release the room it held.
// `target-pointer` (identity, "hover" | "activate") is a selectable foe's
// hit area during the stage target step.
const emit = defineEmits(["settled", "target-pointer"]);

function targetDimmed(participant) {
  if (!props.targeting) return false;
  return !props.targeting.lit.has(String(participant.identity)) && !fallenFor(participant);
}
function targetLit(participant) {
  return !!props.targeting && props.targeting.lit.has(String(participant.identity));
}
function targetSelectable(participant) {
  return !!props.targeting && props.targeting.selectable.has(String(participant.identity));
}

const shown = computed(() =>
  (props.stage ? props.stage.foes : props.foes).slice(0, Math.min(props.max, FOE_STAGE_MAX)),
);

// The raw catalog entry the participant's `portrait_ref` names: a pending
// entry keeps its own placeholder card, and a null or unknown reference
// falls to the StageActor's name placeholder. The client builds no key.
// The descriptor is read from exactly the catalog the availability panel names:
// the CURRENT committed `art` panel's catalog whenever one exists, and the held
// round's captured catalog only when no live panel is committed. A live panel
// that no longer carries an admitted reference therefore reports the local
// failure it is, instead of being concealed by retained playback data.
function entryFor(participant) {
  const ref = participant.portrait_ref;
  if (ref === null || ref === undefined) {
    return null;
  }
  const strRef = String(ref);
  const catalog = props.artPanel ? props.artPanel.portrait_catalog : props.stage?.foeCatalog;
  return catalog?.[strRef]?.artwork ?? null;
}

// The committed panel this position is judged against. The CURRENT committed
// `art` panel always wins — so a panel that is now unavailable, or a reference
// it no longer admits, is reported as the local failure it is rather than
// concealed by retained playback data. Only when no live panel is committed at
// all does the held round's own captured catalog stand in, as the available
// panel it was captured from.
function panelFor() {
  if (props.artPanel) {
    return props.artPanel;
  }
  return props.stage?.foeCatalog ? { available: true, portrait_catalog: props.stage.foeCatalog } : null;
}

// The slot's box: the engine's stage-pixel box and paint order, or nothing
// (the CSS default) without a formation.
function slotStyle(index) {
  const figure = props.formation?.figures?.[index];
  if (!figure) {
    return { "--foe-index": index, zIndex: shown.value.length - index };
  }
  const { left, top, width, height } = figure.box;
  return {
    "--foe-index": index,
    left: `${left}px`,
    top: `${top}px`,
    width: `${width}px`,
    height: `${height}px`,
    zIndex: figure.z,
    // The beat step, cut to the space before the next head (the engine's
    // `lunge`), so a foe acting in a round never leans over a neighbour's head.
    "--motion-beat-lunge": `${figure.lunge ?? 0}px`,
  };
}

// The foe's fallen look: the displayed map's entry, else its own state.
function fallenFor(participant) {
  if (props.fallen) {
    return props.fallen[String(participant.identity)] ?? null;
  }
  return fallenLook("foes", participant.state);
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
    :data-formation="formation ? 'true' : null"
    :data-glide="glide ? 'true' : 'false'"
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
        data-testid="foe-slot"
        :data-identity="p.identity"
        :data-rank="formation?.figures?.[i]?.rank ?? null"
        :data-portrait-ref="p.portrait_ref ?? ''"
        :data-beat="gestureFor(p)?.gesture ?? null"
        :data-fallen="fallenFor(p)"
        :data-target-focus="targetLit(p) ? 'true' : null"
        :data-target-motion="targeting ? (motionLevel === 'full' ? 'full' : 'static') : null"
        :style="slotStyle(i)"
      >
        <div class="formation-figure" :data-glide-key="`foe:${p.identity}`">
          <StageActor
            :artwork="entryFor(p)"
            :panel="panelFor()"
            :has-reference="p.portrait_ref !== null && p.portrait_ref !== undefined"
            :name="p.display_name"
            side="right"
            :dimmed="targetDimmed(p)"
            :motion-level="motionLevel"
            :gesture="gestureFor(p)?.gesture ?? null"
            :gesture-key="stage?.key ?? null"
            :float-amount="gestureFor(p)?.amount ?? null"
            :fallen="fallenFor(p)"
            :fall-instant="fallInstant"
          />
        </div>
        <span
          v-if="targetSelectable(p)"
          class="stage-target__hit"
          data-testid="stage-target-hit"
          :data-identity="p.identity"
          aria-hidden="true"
          @pointerenter="emit('target-pointer', p.identity, 'hover')"
          @click="emit('target-pointer', p.identity, 'activate')"
        ></span>
      </div>
    </TransitionGroup>
  </div>
</template>

<style>
/* The row spans its anchor; in combat the anchor spans the stage (HudFrame,
   `data-formation`), so slot boxes are stage coordinates. */
.foe-lineup {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

/* One foe at its formation box. A re-formed line glides every box on the
   shared travel duration and easing (the party's slots use the same rule),
   so both sides change size together; the base transition never names
   `transform`, so TransitionGroup's FLIP move stays off (a FLIP would move
   the box but jump its size). Below `full`, on a resize and on a reconnect
   the change is instant. Without a formation (a standalone story) the foes
   stand at full height leftward from the anchor's right edge. */
.foe-lineup__slot {
  position: absolute;
  right: 0;
  bottom: 0;
  height: 100%;
  aspect-ratio: 2 / 3;
  transition:
    left calc(var(--motion-actor) * var(--motion-travel)) var(--ease-standard),
    top calc(var(--motion-actor) * var(--motion-travel)) var(--ease-standard),
    width calc(var(--motion-actor) * var(--motion-travel)) var(--ease-standard),
    height calc(var(--motion-actor) * var(--motion-travel)) var(--ease-standard);
}
.foe-lineup:not([data-formation="true"]) > .foe-lineup__slot {
  right: calc(var(--foe-index, 0) * 55%);
}
.foe-lineup[data-formation="true"] > .foe-lineup__slot {
  right: auto;
  bottom: auto;
  aspect-ratio: auto;
}
.foe-lineup[data-glide="false"] > .foe-lineup__slot {
  transition: none;
}
.foe-lineup__slot > .formation-figure,
.foe-lineup__slot > .formation-figure > .stage-actor {
  height: 100%;
}
.foe-lineup__slot > .formation-figure {
  position: relative;
}
/* Depth: a foe that stands in front of another casts a soft shadow onto it,
   so overlapping figures separate even when their art shares a backdrop. */
.foe-lineup__slot:not(:last-child) .reference-artwork {
  filter: drop-shadow(calc(-10px * var(--ui-scale)) 0 calc(14px * var(--ui-scale)) rgba(4, 3, 6, 0.5));
}

/* The placeholder at the formation's scale: the ring and the initial shrink
   with the figure, so a small figure's placeholder never looks larger than
   its body; the label never drops below the 16px chrome floor
   (webclient-vue-application "Chrome type is legible and numerals are
   stable"). Where foes overlap, the label leaves: each foe's plate names it. */
.foe-lineup[data-formation="true"] .stage-actor .reference-artwork__placeholder-glyph {
  width: calc(clamp(88px * var(--ui-scale), 11vh, 132px * var(--ui-scale)) * var(--formation-scale, 1));
  font-size: calc(clamp(44px * var(--ui-scale), 5.6vh, 66px * var(--ui-scale)) * var(--formation-scale, 1));
}
.foe-lineup[data-formation="true"] .stage-actor .reference-artwork__placeholder-label {
  font-size: max(var(--text-xs), calc(var(--text-md) * var(--formation-scale, 1)));
}
.foe-lineup[data-formation="true"]:not([data-count="1"]) .reference-artwork__identity,
.foe-lineup[data-formation="true"]:not([data-count="1"]) .reference-artwork__placeholder-label {
  display: none;
}

/* Membership inside combat (design D3): a joining foe slides in from the
   right as it fades in; a fleeing foe fades where it stands while the others
   glide into their new places (a defeated foe keeps its slot). */
.foe-lineup > .foe-enter-active {
  transition:
    opacity var(--motion-actor) var(--ease-standard),
    transform var(--motion-actor) var(--ease-enter);
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
