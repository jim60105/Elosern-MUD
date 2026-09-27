<script setup>
// StageActor (webclient-dialogue-stage-actors design D1): one standing
// portrait on the stage. It wraps `ReferenceArtwork` (which stays the plain
// frame of the drawer's art slot) and adds the stage's own concerns:
// - the side it stands on (`left` for the player, `right` for the dialogue
//   host), exposed as `data-side` so the soft edge masks can mirror;
// - the speaking state: the listener is dimmed through the shared
//   `--actor-dim` token and `data-speaking` names the state for tests. The
//   dim is never the only cue (the message window's name plate names the
//   host); it eases on the motion tokens (instant below `full`);
// - the truthful placeholder: with no catalog or roster entry the actor
//   draws the name's initial and the name (never a stock image); a
//   placeholder entry keeps its own label (肖像生成中, 無肖像) with the
//   name's initial in the ring; with no name at all, `ReferenceArtwork`
//   keeps its own `肖像生成中` card.
// Decorative art: no focusable element, no pointer events.
//
// A new portrait source (webclient-scene-transitions, design D5) — a new
// image URL, or a switch between an image and a placeholder — crossfades:
// the artwork is keyed by its source, the new one fades in above the old,
// and the old one is inert from the commit on. A same-URL refresh keeps the
// key, so it never fades.
//
// The combat beat gestures (webclient-combat-beat-choreography design D4;
// AVG stage design §10.2): while a combat round plays, the figure acts out
// its beat — `lunge` steps toward the stage centre and back, `hit` shakes
// with a brief flash while a decorative `−N` rises from it, and `defeat`
// fades and drops the figure. The gesture lives on an inner wrapper keyed by
// the step (`gestureKey`), so a new step restarts its animation (two hits in
// a row on one foe each shake) with no script-side reflow. Every duration
// and distance is a motion token, so `reduced` keeps only the defeat fade
// and `off` never plays one. Decorative: the number is `aria-hidden`, and
// the beat's page and the numerals carry every value.
import { computed, ref, watch } from "vue";
import ReferenceArtwork from "./ReferenceArtwork.vue";
import { inertWhileLeaving } from "../lib/transition_hooks.js";

const props = defineProps({
  // A roster portrait or an `art` panel `portrait_catalog` entry, or null.
  portrait: { type: Object, default: null },
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
});

const shown = computed(() => {
  if (props.portrait) {
    return props.portrait;
  }
  return props.name ? { placeholder: { kind: "missing", label: props.name } } : null;
});

const portraitKey = computed(() => {
  const entry = shown.value;
  if (entry?.url) {
    return entry.url;
  }
  return entry ? `ph:${entry.placeholder?.label ?? ""}` : "none";
});

const transitionCss = computed(() => props.motionLevel !== "off");

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
  >
    <div
      :key="beatKey"
      class="stage-actor__beat"
      :data-beat="gesture || null"
    >
      <Transition name="actor-xfade" :css="transitionCss" v-bind="inertWhileLeaving">
        <ReferenceArtwork :key="portraitKey" :portrait="shown" :initial-of="name" />
      </Transition>
    </div>
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
.stage-actor[data-side="left"] > [data-beat="lunge"] {
  animation: elosern-beat-lunge-right var(--motion-beat-step) var(--ease-standard) 1;
}
.stage-actor[data-side="right"] > [data-beat="lunge"] {
  animation: elosern-beat-lunge-left var(--motion-beat-step) var(--ease-standard) 1;
}
.stage-actor > [data-beat="hit"] {
  animation: elosern-beat-hit var(--motion-beat-hit) linear 1;
}
.stage-actor > [data-beat="defeat"] {
  animation: elosern-beat-defeat var(--motion-beat-defeat) var(--ease-exit) 1 forwards;
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
  font-family: var(--f-display);
  font-size: calc(var(--message-text) * 1.5);
  font-weight: 700;
  line-height: 1;
  letter-spacing: 0.02em;
  white-space: nowrap;
  -webkit-text-stroke: 4px rgba(14, 8, 10, 0.92);
  paint-order: stroke fill;
  text-shadow:
    0 2px 12px rgba(10, 6, 8, 0.9),
    0 0 26px var(--seal-glow);
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

/* The figure dissolves into the stage instead of ending in a rectangle (a
   generated portrait carries its own flat backdrop): an elliptical mask
   centred on the figure, nudged towards the stage centre and mirrored with
   the side, intersected with a long fade at the feet into the band it
   stands on. The ellipse is exactly as wide as the box and the vertical
   fade opens with a short rise at the top, so no edge of the box survives
   as a visible seam — on a dark scene, or where the combat foes overlap one
   another. The placeholder card takes the same silhouette. */
.stage-actor .reference-artwork img,
.stage-actor .reference-artwork__placeholder {
  --actor-mask-shape: radial-gradient(ellipse 50% 62% at 51% 46%, #000 58%, transparent 100%);
  --actor-mask-feet: linear-gradient(transparent, #000 5%, #000 70%, transparent 97%);
  -webkit-mask-image: var(--actor-mask-shape), var(--actor-mask-feet);
  -webkit-mask-composite: source-in;
  mask-image: var(--actor-mask-shape), var(--actor-mask-feet);
  mask-composite: intersect;
}
.stage-actor[data-side="right"] .reference-artwork img,
.stage-actor[data-side="right"] .reference-artwork__placeholder {
  --actor-mask-shape: radial-gradient(ellipse 50% 62% at 49% 46%, #000 58%, transparent 100%);
}
.stage-actor .reference-artwork img {
  object-position: center 12%;
}

/* The truthful placeholder at stage scale: a quiet ink silhouette field with
   the initial set large in the display face inside a hairline gold ring, and
   the label under it — it reads as "someone stands here", never as art. */
.stage-actor .reference-artwork__placeholder {
  place-content: center stretch;
  gap: 18px;
  background:
    radial-gradient(46% 34% at 50% 40%, rgba(185, 154, 96, 0.14), transparent 72%),
    radial-gradient(70% 60% at 50% 58%, #1c1a1f, #0f1013 78%);
}
.stage-actor .reference-artwork__placeholder-glyph {
  display: grid;
  place-items: center;
  width: clamp(88px, 11vh, 132px);
  aspect-ratio: 1;
  margin: 0 auto;
  border: 1px solid rgba(185, 154, 96, 0.55);
  border-radius: 50%;
  box-shadow:
    0 0 0 6px rgba(185, 154, 96, 0.08),
    inset 0 0 28px rgba(0, 0, 0, 0.55);
  color: var(--gold-400);
  font-family: var(--f-display);
  font-size: clamp(44px, 5.6vh, 66px);
  line-height: 1;
  text-shadow: 0 0 18px var(--gold-glow);
}
.stage-actor .reference-artwork__placeholder-label {
  max-width: 78%;
  margin: 0 auto;
  text-align: center;
  color: var(--paper-300);
  font-family: var(--f-serif);
  font-size: 14px;
  letter-spacing: 0.24em;
  overflow-wrap: anywhere;
}
/* The placeholder already states its label on the figure itself; the host's
   caption is the message window's name plate, so in a conversation neither
   figure carries a caption. */
.stage-actor .reference-artwork figcaption[data-sample="true"],
.stage-actor[data-side="right"] .reference-artwork figcaption,
[data-elosern-mode="dialogue"] .stage-actor .reference-artwork figcaption {
  display: none;
}
</style>
