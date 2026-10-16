<script setup>
// StageActor (webclient-dialogue-stage-actors design D1): one standing
// figure on the stage. It wraps `ReferenceArtwork` (the shared figure
// renderer, which also frames the drawer's art slot) and adds the stage's own
// concerns:
// - the side it stands on (`left` for the player, `right` for the dialogue
//   host), exposed as `data-side` for directional beat gestures;
// - the speaking state: the listener is dimmed through the shared
//   `--actor-dim` token and `data-speaking` names the state for tests. The
//   dim is never the only cue (the message window's name plate names the
//   host); it eases on the motion tokens (instant below `full`);
// - stage-only artwork preserves contours and uses the descriptor's own
//   grounded alpha terminal with identity and authoritative availability when
//   no real image is available.
// Decorative art: no focusable element, no pointer events.
//
// A new portrait SOURCE (webclient-scene-transitions, design D5) — a new
// resource identity, or a switch between a real candidate and the terminal —
// crossfades: the artwork is keyed by the presented resource's own identity,
// the new one fades in above the old, and the old one is inert from the commit
// on. A geometry-only re-presentation of the SAME resource keeps the key, so
// the placement updates without a remount, a refetch or a crossfade.
//
// The combat beat gestures (webclient-combat-beat-choreography design D4;
// AVG stage design §10.2): while a combat round plays, the figure acts out
// its beat — `lunge` steps toward the stage centre and back, and `hit`
// shakes with a brief flash while a decorative `−N` rises from it. The
// gesture lives on an inner wrapper keyed by the step (`gestureKey`), so a
// new step restarts its animation (two hits in a row on one foe each shake)
// with no script-side reflow. Every duration and distance is a motion token,
// so `reduced` moves nothing and `off` never plays one. Decorative: the
// number is `aria-hidden`, and the beat's page and the numerals carry every
// value.
//
// The fallen looks (webclient-combat-defeated-foes design D1-D4): `fallen`
// names a figure that is out of the fight but keeps its slot. The pose and
// the tone live on `.stage-actor__fall`, a wrapper around the keyed beat
// wrapper, so a gesture and the fall compose and a new step never remounts
// the fall. Both poses are a pure compression about the figure's base (no
// rotation, no translation), so the transformed box never leaves its slot:
// - "defeated" (a foe): collapsed to 80% of its height, fully desaturated
//   and darkened at 0.8 opacity, with a broken seal stamped over its chest;
// - "down" (a party member): kneeling at 92%, half desaturated, no seal.
// A change of look eases over the defeat beat at `full` (the seal presses in
// after the collapse), fades its tone and seal without travel at `reduced`,
// and is instant at `off` and while the client hydrates (`fallInstant`); a
// figure that mounts already fallen renders at rest. The look sits on the
// figure wrapper, so a portrait, a placeholder card and failed art take it
// alike, and the seal is decorative (`aria-hidden`): the plate states
// 已擊破 / 倒地.
import { computed, ref, useId, watch } from "vue";
import ReferenceArtwork from "./ReferenceArtwork.vue";
import { inertWhileLeaving } from "../lib/transition_hooks.js";
import { artworkOriginal, artworkTerminalUrl } from "../lib/artwork.js";

const props = defineProps({
  // The canonical artwork descriptor of this figure position, or null.
  artwork: { type: Object, default: null },
  // The committed panel the descriptor came from, and whether that panel
  // admitted a reference for this position at all.
  panel: { type: Object, default: null },
  hasReference: { type: Boolean, default: true },
  required: { type: Boolean, default: true },
  // The display name the placeholder states when no entry exists.
  name: { type: String, default: "" },
  side: {
    type: String,
    default: "left",
    validator: (value) => value === "left" || value === "right",
  },
  // True while the other side speaks (AppClient derives it from the
  // committed mode and `view.dialogueSpeaker`).
  dimmed: { type: Boolean, default: false },
  // The EFFECTIVE motion level (`store.view.motionLevel`,
  // webclient-scene-transitions D1): at `off` the transition has no CSS
  // phase, so the final state is on screen in the commit's frame (a CSS
  // phase would outlive the commit by a double frame even at 0s).
  motionLevel: { type: String, default: "full" },
  // The combat beat gesture this figure plays (`view.beatStage`), or null.
  gesture: {
    type: String,
    default: null,
    validator: (value) => value === null || value === "lunge" || value === "hit" || value === "defeat",
  },
  // `<round>:<step>`: a new step restarts the gesture on the same figure.
  gestureKey: { type: String, default: null },
  // The damage the rising number names (a `hit` only), or null.
  floatAmount: { type: Number, default: null },
  // The fallen look (webclient-combat-defeated-foes D1): "defeated" for a
  // foe out of the fight, "down" for a party member, or null.
  fallen: {
    type: String,
    default: null,
    validator: (value) => value === null || value === "defeated" || value === "down",
  },
  // True while a change of look must land in the commit's frame (a reload
  // or a reconnect): no fall transition and no seal press.
  fallInstant: { type: Boolean, default: false },
});

// The crossfade key is the presented RESOURCE's own identity, never the
// descriptor revision: a geometry-only re-presentation of the same resource
// keeps the key (so placement updates in place), while a genuinely new
// resource — a new candidate or the switch to the terminal — re-keys it.
const portraitKey = computed(() => {
  const descriptor = props.artwork;
  if (!descriptor) {
    return `ph:${props.name}`;
  }
  const original = artworkOriginal(descriptor);
  const resource = original?.resource ?? null;
  if (resource) {
    return `${descriptor.subject_id}:${resource.resource_id}:${resource.version}`;
  }
  const terminal = artworkTerminalUrl(descriptor);
  return terminal ? `${descriptor.subject_id}:terminal:${terminal}` : `ph:${descriptor.subject_id}`;
});

const transitionCss = computed(() => props.motionLevel !== "off");
// The seal's crack mask needs a document-unique id per figure.
const sealMaskId = `stage-seal-crack-${useId()}`;
// The fall eases only at a live change above `off` (design D4).
const fallInstant = computed(() => props.fallInstant || props.motionLevel === "off");

// The gesture wrapper's key (webclient-combat-beat-choreography D4): a new
// step's gesture re-keys it, so the animation restarts. Returning to rest
// keeps the last key: the finished animation simply drops with `data-beat`,
// and the portrait inside is not remounted for the rest phase.
const restKey = ref("rest");
watch(
  () => (props.gesture ? props.gestureKey || props.gesture : null),
  (key) => {
    if (key) {
      restKey.value = key;
    }
  },
);
const beatKey = computed(() => (props.gesture ? props.gestureKey || props.gesture : restKey.value));
</script>

<template>
  <div
    class="stage-actor"
    data-testid="stage-actor"
    :data-side="side"
    :data-speaking="String(!dimmed)"
    :data-fallen="fallen"
  >
    <div
      class="stage-actor__fall"
      data-testid="stage-actor-fall"
      :data-fallen="fallen"
      :data-fall-instant="fallInstant ? 'true' : null"
    >
      <div
        :key="beatKey"
        class="stage-actor__beat"
        :data-beat="gesture || null"
      >
        <Transition name="actor-xfade" :css="transitionCss" v-bind="inertWhileLeaving">
          <ReferenceArtwork
            :key="portraitKey"
            :artwork="artwork"
            :panel="panel"
            :required="required"
            :has-reference="hasReference"
            :name="name"
            :initial-of="name"
            stage
            :motion-level="motionLevel"
          />
        </Transition>
      </div>
    </div>
    <!-- The broken seal (design D2): a seal ring with a missing wedge, split
         by a jagged crack, stamped over the collapsed chest. It stands
         outside the fall wrapper, so it keeps its round shape and its seal
         red over the greyed figure. -->
    <Transition name="stage-seal" :css="!fallInstant">
      <svg
        v-if="fallen === 'defeated'"
        class="stage-actor__seal"
        data-testid="stage-actor-seal"
        viewBox="0 0 100 100"
        aria-hidden="true"
        focusable="false"
      >
        <defs>
          <!-- The crack is cut out of the whole seal, so the figure shows
               through the split rather than a drawn line. -->
          <mask :id="sealMaskId" maskUnits="userSpaceOnUse" x="-10" y="-10" width="120" height="120">
            <rect x="-10" y="-10" width="120" height="120" fill="#fff" />
            <path class="stage-actor__seal-crack" d="M 44 -4 L 51 18 L 43 33 L 58 47 L 47 61 L 60 75 L 53 104" />
          </mask>
        </defs>
        <g :mask="`url(#${sealMaskId})`">
          <circle class="stage-actor__seal-halo" cx="50" cy="50" r="47" />
          <path class="stage-actor__seal-under" d="M 76.6 16.2 A 43 43 0 1 1 63.3 9.1" />
          <path class="stage-actor__seal-ring" d="M 76.6 16.2 A 43 43 0 1 1 63.3 9.1" />
          <circle class="stage-actor__seal-inner" cx="50" cy="50" r="34" />
          <path class="stage-actor__seal-rune" d="M 50 30 L 64 50 L 50 70 L 36 50 Z" />
          <circle class="stage-actor__seal-dot" cx="50" cy="50" r="4.5" />
        </g>
      </svg>
    </Transition>
    <span
      v-if="gesture === 'hit' && floatAmount !== null"
      :key="`float:${gestureKey}`"
      class="stage-actor__float"
      data-testid="stage-actor-float"
      aria-hidden="true"
    >−{{ floatAmount }}</span>
  </div>
</template>

<style>
.stage-actor {
  position: relative;
  height: 100%;
  pointer-events: none;
}
.stage-actor__fall,
.stage-actor__beat {
  position: relative;
  height: 100%;
}
.stage-actor__beat > .reference-artwork {
  height: 100%;
  overflow: visible;
}
/* The listener (design D1): one shared dim token. The change of speaker
   eases (webclient-scene-transitions D5); below `full` it is instant. */
.stage-actor {
  transition: filter var(--motion-base) var(--ease-standard);
}
.stage-actor[data-speaking="false"] {
  filter: brightness(var(--actor-dim));
}

/* The portrait crossfade (webclient-scene-transitions, design D5): the new
   figure fades in above the old one on a fast-rising curve while the old one
   thins on a slow-starting curve, so the pair never shows the stage through
   a half-transparent body. The leaving copy is lifted out of flow onto the
   same box. */
.stage-actor__beat > .actor-xfade-enter-active {
  position: relative;
  z-index: 1;
  transition: opacity var(--motion-portrait) var(--ease-standard);
}
.stage-actor__beat > .actor-xfade-leave-active {
  position: absolute;
  inset: 0;
  z-index: 0;
  transition: opacity var(--motion-portrait) var(--ease-exit);
}
.stage-actor__beat > .actor-xfade-enter-from,
.stage-actor__beat > .actor-xfade-leave-to {
  opacity: 0;
}

/* The combat beat gestures (webclient-combat-beat-choreography D4): each
   plays once per step on the keyed wrapper. The step leans toward the stage
   centre, so the player (left) steps right and a foe (right) steps left. */
.stage-actor[data-side="left"] > .stage-actor__fall > [data-beat="lunge"] {
  animation: elosern-beat-lunge-right var(--motion-beat-step) var(--ease-standard) 1;
}
.stage-actor[data-side="right"] > .stage-actor__fall > [data-beat="lunge"] {
  animation: elosern-beat-lunge-left var(--motion-beat-step) var(--ease-standard) 1;
}
.stage-actor > .stage-actor__fall > [data-beat="hit"] {
  animation: elosern-beat-hit var(--motion-beat-hit) linear 1;
}
/* The rising damage number: the seal red of a wound, set large in the
   display face, with an ink outline painted under the fill and a dark halo,
   so it reads over pale robes and dark art alike. It starts and ends
   invisible, so at `reduced` and `off` (0ms) it never shows; the beat's page
   and the numerals carry the value. */
.stage-actor__float {
  position: absolute;
  top: 30%;
  left: 50%;
  z-index: 2;
  opacity: 0;
  color: var(--seal-400);
  font-family: var(--f-num);
  font-variant-numeric: tabular-nums lining-nums;
  font-size: calc(var(--message-text) * 1.5);
  font-weight: 700;
  line-height: 1;
  letter-spacing: 0.02em;
  white-space: nowrap;
  -webkit-text-stroke: calc(4px * var(--ui-scale)) rgba(14, 8, 10, 0.92);
  paint-order: stroke fill;
  text-shadow:
    0 2px calc(12px * var(--ui-scale)) rgba(10, 6, 8, 0.9),
    0 0 calc(26px * var(--ui-scale)) var(--seal-glow);
  pointer-events: none;
  animation: elosern-beat-float var(--motion-beat-float) var(--ease-exit) 1 forwards;
}
/* The number leans toward the stage centre from the figure's face, so it
   stays in the open stage and clear of the island column on the figure's
   own side (the vitals on the left, the participant frame on the right). */
.stage-actor[data-side="left"] > .stage-actor__float {
  --float-x: -20%;
}
.stage-actor[data-side="right"] > .stage-actor__float {
  --float-x: -80%;
}

/* The fallen looks (webclient-combat-defeated-foes design D1/D4). The pose
   compresses about the base, so the feet stay planted and the transformed
   box stays inside the slot; the tone and the opacity ease on the defeat
   beat's duration and exit curve, and the pose takes the same duration times
   the travel factor, so `reduced` lands the pose at once and only fades. */
.stage-actor__fall {
  transform-origin: 50% 100%;
  transition:
    transform calc(var(--motion-beat-defeat) * var(--motion-travel)) var(--ease-exit),
    filter var(--motion-beat-defeat) var(--ease-exit),
    opacity var(--motion-beat-defeat) var(--ease-exit);
}
.stage-actor__fall[data-fallen="defeated"] {
  transform: scaleY(var(--fall-defeated-squash));
  filter: var(--fall-defeated-tone);
  opacity: var(--fall-defeated-opacity);
}
.stage-actor__fall[data-fallen="down"] {
  transform: scaleY(var(--fall-down-squash));
  filter: var(--fall-down-tone);
  opacity: var(--fall-down-opacity);
}
.stage-actor__fall[data-fall-instant="true"] {
  transition: none;
}

/* The broken seal: 28% of the figure's width, centred over the chest of the
   collapsed figure (42% down the figure from its lowered head). A dark under
   stroke and halo keep the seal-red ring legible over pale robes and dark
   art alike; the crack is cut through ring, rune and halo by a mask. */
.stage-actor__seal {
  position: absolute;
  left: 50%;
  top: calc((1 - var(--fall-defeated-squash) + var(--fall-seal-chest) * var(--fall-defeated-squash)) * 100%);
  z-index: 1;
  width: var(--fall-seal-size);
  aspect-ratio: 1;
  overflow: visible;
  transform: translate(-50%, -50%) rotate(-8deg);
  pointer-events: none;
  filter: drop-shadow(0 0 calc(10px * var(--ui-scale)) var(--seal-glow));
}
.stage-actor__seal-halo {
  fill: rgba(14, 8, 10, 0.38);
}
.stage-actor__seal-under {
  fill: none;
  stroke: rgba(10, 6, 8, 0.8);
  stroke-width: 10;
}
.stage-actor__seal-ring {
  fill: none;
  stroke: var(--seal-400);
  stroke-width: 5.5;
}
.stage-actor__seal-inner {
  fill: none;
  stroke: var(--seal-500);
  stroke-width: 1.4;
}
.stage-actor__seal-rune {
  fill: none;
  stroke: var(--seal-400);
  stroke-width: 3.2;
  stroke-linejoin: miter;
}
.stage-actor__seal-dot {
  fill: var(--seal-400);
}
.stage-actor__seal-crack {
  fill: none;
  stroke: #000;
  stroke-width: 6;
  stroke-linecap: round;
  stroke-linejoin: miter;
}
/* The seal presses in after the collapse: it fades in from a slightly larger
   stamp, delayed by the collapse at `full`; at `reduced` (no travel) it only
   fades, at once, within the defeat token's 150ms. */
.stage-actor__seal.stage-seal-enter-active {
  transition:
    opacity var(--motion-beat-defeat) var(--ease-standard) calc(var(--motion-beat-defeat) * var(--motion-travel)),
    transform var(--motion-beat-defeat) var(--ease-enter) calc(var(--motion-beat-defeat) * var(--motion-travel));
}
.stage-actor__seal.stage-seal-enter-from {
  opacity: 0;
  transform: translate(-50%, -50%) rotate(-8deg) scale(calc(1 + 0.35 * var(--motion-travel)));
}
.stage-actor__seal.stage-seal-leave-active {
  transition: opacity var(--motion-beat-defeat) var(--ease-exit);
}
.stage-actor__seal.stage-seal-leave-to {
  opacity: 0;
}
</style>
