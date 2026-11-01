<script setup>
// CampfireCard (OpenSpec change wilderness-camping; design §5): the
// presentation-only beat after a settled camp. The committed wilderness
// scene (the art panel's own descriptor, through the shared artwork
// lifecycle) is graded down to night and lit by a CSS fire with glow and
// embers; anonymous seated silhouettes sit at the fire. The party stands as
// travel medallions in an arc, far side higher, a crescent on each body that
// slept. Each 精力 bar moves from the committed before to the committed after
// value over 1.6 s, then the server's result line, interruption and due-event
// lines, and 繼續旅程 appear.
//
// Any key or click before the beat settles only finishes it (bars and lines
// at their final state) and is consumed, so it can neither dismiss the card
// nor reach the map. A later 繼續旅程, Enter or Esc emits `continue` once.
// Motion `off` renders the final state on the first frame. Nothing here
// changes the clock, a reserve or any command.
import { computed, onBeforeUnmount, onMounted, ref, useId } from "vue";
import ArtworkPreview from "../ArtworkPreview.vue";
import AvatarArtwork from "../AvatarArtwork.vue";
import { createFocusTrap } from "../focus-trap.js";

// The bars move from the committed before to the after value over 1.6 s.
const BEAT_FILL_MS = 1600;

const props = defineProps({
  // The camp result data (`explore.camp` success `data`).
  result: { type: Object, required: true },
  // The server's summary line (the result `message`).
  message: { type: String, default: "" },
  // `medallionMembers(...)` rows, matched to result members by identity.
  medallions: { type: Array, default: () => [] },
  // The committed scene descriptor and the art panel it came from.
  sceneArtwork: { type: Object, default: null },
  artPanel: { type: Object, default: null },
  motionLevel: { type: String, default: "full" },
});
const emit = defineEmits(["continue"]);

// Only the full motion level plays the fill; reduced and off show the final
// state at once (their --motion-camp-fill is 0ms).
const still = props.motionLevel !== "full";
const root = ref(null);
const go = ref(null);
const titleId = useId();
// `filled` moves the bars to their after value (the CSS transition is the
// 1.6 s animation); `settled` reveals the result lines and 繼續旅程.
const filled = ref(still);
const settled = ref(still);
let timers = [];
let trap = null;
let closed = false;

const portraits = computed(() => new Map(props.medallions.map((m) => [String(m.key), m])));

const party = computed(() => {
  const members = props.result.members ?? [];
  const n = members.length;
  return members.map((member, index) => {
    // An arc around the fire: the outer seats sit lower and nearer, the
    // middle (far side of the ring) higher.
    const t = n === 1 ? 0.5 : index / (n - 1);
    const angle = (-46 + 92 * t) * (Math.PI / 180);
    const portrait = portraits.value.get(String(member.member_id)) ?? null;
    // cos runs 0.69 (outer seats) to 1 (the far side of the ring).
    const far = (Math.cos(angle) - Math.cos((46 * Math.PI) / 180)) / (1 - Math.cos((46 * Math.PI) / 180));
    return {
      ...member,
      // The fire keeps a clear lane: no seat nearer than 15% to the middle.
      x: 50 + (n === 1 ? 0 : Math.sign(Math.sin(angle) || 1) * Math.max(15, Math.abs(Math.sin(angle) * 46))),
      y: 5 + far * 15,
      depth: Math.cos(angle),
      slept: member.wake_tick !== null || member.sleeping === true,
      portrait,
    };
  });
});

const interrupted = computed(() => props.result.interrupted === true);
const eventLines = computed(() =>
  (props.result.events ?? []).map((event) => event.text).filter((text) => typeof text === "string" && text.trim()),
);

function percent(member) {
  return filled.value ? member.after_percent : member.before_percent;
}

function finish() {
  timers.forEach(clearTimeout);
  timers = [];
  filled.value = true;
  settled.value = true;
  Promise.resolve().then(() => go.value?.focus({ preventScroll: true }));
}

function done() {
  if (closed || !settled.value) return;
  closed = true;
  emit("continue");
}

function onKeydown(event) {
  if (event.ctrlKey || event.altKey || event.metaKey || event.isComposing) return;
  if (!settled.value) {
    // An early key only finishes the beat; it is consumed entirely.
    event.preventDefault();
    event.stopPropagation();
    if (event.key !== "Tab") finish();
    return;
  }
  if (event.key === "Tab") {
    event.stopPropagation();
    trap?.onKeydown(event);
    return;
  }
  if (event.key === "Enter" || event.key === "Escape") {
    event.preventDefault();
    event.stopPropagation();
    if (!event.repeat) done();
    return;
  }
  if (event.key !== " ") event.stopPropagation();
}

function onPointer(event) {
  if (settled.value) return;
  event.preventDefault();
  event.stopPropagation();
  finish();
}

onMounted(() => {
  trap = createFocusTrap(root.value, { initialFocusEl: still ? go.value : root.value });
  trap.enter();
  if (!still) {
    // One frame at the before values, then the 1.6 s fill, then the lines.
    timers.push(setTimeout(() => (filled.value = true), 60));
    timers.push(setTimeout(() => finish(), 60 + BEAT_FILL_MS));
  }
});
onBeforeUnmount(() => timers.forEach(clearTimeout));
</script>

<template>
  <section
    ref="root"
    class="choice-card campfire-card"
    :class="{ 'is-still': still, 'is-settled': settled, 'is-interrupted': interrupted }"
    role="dialog"
    aria-modal="true"
    :aria-labelledby="titleId"
    tabindex="-1"
    data-testid="campfire-card"
    :data-settled="settled ? 'true' : 'false'"
    :data-phase="result.phase"
    @keydown="onKeydown"
    @pointerdown.capture="onPointer"
  >
    <span class="choice-card__corners" aria-hidden="true"></span>
    <div class="campfire-card__scene" data-testid="campfire-card-scene">
      <div class="campfire-card__art" :class="{ 'is-empty': !sceneArtwork }" aria-hidden="true">
        <ArtworkPreview v-if="sceneArtwork" :artwork="sceneArtwork" :panel="artPanel" alt="" />
      </div>
      <div class="campfire-card__night" aria-hidden="true"></div>
      <div class="campfire-card__stars" aria-hidden="true"></div>
      <div class="campfire-card__glow" aria-hidden="true"></div>
      <div class="campfire-card__sitters" aria-hidden="true">
        <span class="campfire-card__sitter is-left"></span>
        <span class="campfire-card__sitter is-right"></span>
      </div>
      <div class="campfire-card__fire" aria-hidden="true">
        <span></span><span></span><span></span>
        <i v-for="k in 9" :key="k" :style="{ '--k': k }"></i>
      </div>
      <div class="campfire-card__logs" aria-hidden="true"></div>
      <p :id="titleId" class="campfire-card__caption">
        <span>營火</span>
        <b v-if="result.timing.wake_time">{{ result.timing.wake_time }}</b>
        <b v-else>{{ result.timing.result_time }}</b>
      </p>
      <ul class="campfire-card__party" aria-label="隊伍的精力">
        <li
          v-for="member in party"
          :key="member.member_id"
          class="campfire-card__member"
          :class="{ 'is-asleep': member.slept }"
          :style="{ left: `${member.x}%`, bottom: `${member.y}%`, zIndex: Math.round(20 - member.depth * 10) }"
          data-testid="campfire-member"
          :data-member="member.member_id"
          :data-percent="percent(member)"
        >
          <span class="campfire-card__sr">{{ member.name }}：精力 {{ member.before_percent }}% 至 {{ member.after_percent }}%</span>
          <span class="campfire-card__ring" aria-hidden="true">
            <span class="campfire-card__face">
              <AvatarArtwork
                v-if="member.portrait"
                :artwork="member.portrait.artwork"
                :panel="member.portrait.panel"
                :has-reference="member.portrait.hasReference"
                :name="member.name"
                :failure-text-id="`campfire-${member.member_id}-failure`"
              />
              <span v-else class="campfire-card__initial">{{ member.name.slice(0, 1) }}</span>
            </span>
            <span v-if="member.slept" class="campfire-card__moon" data-testid="campfire-moon"></span>
          </span>
          <span class="campfire-card__name" aria-hidden="true">{{ member.name }}</span>
          <span class="campfire-card__bar" aria-hidden="true">
            <span :style="{ width: `${percent(member)}%` }"></span>
          </span>
          <span class="campfire-card__pct" aria-hidden="true">{{ percent(member) }}%</span>
        </li>
      </ul>
    </div>
    <footer class="campfire-card__foot">
      <div class="campfire-card__lines" aria-live="polite" data-testid="campfire-lines">
        <template v-if="settled">
          <p class="campfire-card__result" data-testid="campfire-result">{{ message }}</p>
          <p v-for="(line, index) in eventLines" :key="index" class="campfire-card__event" data-testid="campfire-event">
            <span aria-hidden="true">◆</span> {{ line }}
          </p>
        </template>
        <p v-else class="campfire-card__hint">按任意鍵略過</p>
      </div>
      <button
        ref="go"
        type="button"
        class="campfire-card__go"
        data-testid="campfire-continue"
        :disabled="!settled"
        @click="done"
      >
        繼續旅程 <kbd aria-hidden="true">Enter</kbd>
      </button>
    </footer>
  </section>
</template>

<style>
/* The campfire beat: the event-card width (wider than the camp card), a
   16:9 night scene and a quiet ink footer for the server's lines. The fire
   is pure CSS until a dedicated illustration exists; every animation stops
   at motion `off` and under reduced motion. */
.campfire-card.choice-card {
  position: relative;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  align-self: center;
  width: min(100%, calc(760px * var(--ui-scale)));
  max-height: 100%;
  padding: 0;
  overflow: hidden;
  background: linear-gradient(180deg, rgba(12, 12, 16, 0.99), rgba(9, 9, 12, 0.99));
  border: 1px solid rgba(185, 154, 96, 0.5);
  border-radius: var(--radius);
  box-shadow: var(--shadow-lg), 0 0 0 100vmax rgba(4, 5, 8, 0.5), inset 0 0 0 1px rgba(0, 0, 0, 0.55);
  outline: none;
  pointer-events: auto;
}
.campfire-card__scene {
  position: relative;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  background: radial-gradient(80% 70% at 50% 100%, #1d140f, #07080c 70%);
}
.campfire-card__art {
  position: absolute;
  inset: -4%;
  filter: brightness(0.38) saturate(0.55) hue-rotate(-14deg) blur(0.6px);
  transform: scale(1.04);
}
.campfire-card__art .artwork-preview,
.campfire-card__art img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: 50% 70%;
}
.campfire-card__night {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(180deg, rgba(8, 14, 32, 0.82), rgba(10, 12, 22, 0.25) 48%, rgba(7, 5, 5, 0.82)),
    radial-gradient(70% 55% at 50% 100%, transparent, rgba(4, 5, 9, 0.75));
}
.campfire-card__stars {
  position: absolute;
  inset: 0 0 55% 0;
  background-image:
    radial-gradient(1px 1px at 12% 22%, rgba(230, 236, 255, 0.8), transparent),
    radial-gradient(1px 1px at 27% 12%, rgba(230, 236, 255, 0.6), transparent),
    radial-gradient(1.5px 1.5px at 41% 30%, rgba(230, 236, 255, 0.7), transparent),
    radial-gradient(1px 1px at 63% 16%, rgba(230, 236, 255, 0.55), transparent),
    radial-gradient(1.5px 1.5px at 78% 26%, rgba(230, 236, 255, 0.7), transparent),
    radial-gradient(1px 1px at 90% 10%, rgba(230, 236, 255, 0.5), transparent);
  animation: cf-twinkle var(--motion-pulse) ease-in-out infinite;
}
.campfire-card__glow {
  position: absolute;
  left: 50%;
  bottom: -6%;
  width: 96%;
  aspect-ratio: 1.6;
  transform: translateX(-50%);
  background: radial-gradient(closest-side, rgba(255, 176, 86, 0.55), rgba(220, 110, 40, 0.22) 45%, transparent 74%);
  mix-blend-mode: screen;
  animation: cf-glow calc(var(--motion-campfire) * 2.7) ease-in-out infinite;
}
.campfire-card__sitters {
  position: absolute;
  left: 50%;
  bottom: 31%;
  width: 46%;
  height: 15%;
  transform: translateX(-50%);
  opacity: 0.9;
  filter: blur(0.5px);
}
/* Anonymous seated silhouettes: a hooded head over a hunched shoulder line,
   rim-lit on the fire side. No portrait, no identity. */
.campfire-card__sitter {
  position: absolute;
  bottom: 0;
  width: 16%;
  height: 78%;
  background:
    radial-gradient(circle at 50% 22%, #0a0807 19%, transparent 20%),
    radial-gradient(120% 90% at 50% 100%, #0a0807 52%, transparent 53%);
  filter: drop-shadow(0 0 0 transparent);
}
.campfire-card__sitter.is-left {
  left: 0;
  transform: rotate(6deg);
  filter: drop-shadow(2px 0 3px rgba(255, 140, 60, 0.55));
}
.campfire-card__sitter.is-right {
  right: 0;
  transform: rotate(-6deg) scaleX(-1);
  filter: drop-shadow(2px 0 3px rgba(255, 140, 60, 0.55));
}
.campfire-card__fire {
  position: absolute;
  left: 50%;
  bottom: 26%;
  width: 11%;
  aspect-ratio: 0.8;
  transform: translateX(-50%);
  filter: blur(0.6px);
}
.campfire-card__fire span {
  position: absolute;
  left: 50%;
  bottom: 0;
  width: 70%;
  height: 100%;
  border-radius: 50% 50% 45% 45% / 70% 70% 30% 30%;
  transform-origin: 50% 100%;
  translate: -50% 0;
  background: radial-gradient(60% 70% at 50% 85%, #fff4c8, #ffbe52 38%, #e8622a 70%, transparent 72%);
  mix-blend-mode: screen;
  animation: cf-flame var(--motion-campfire) ease-in-out infinite alternate;
}
.campfire-card__fire span:nth-child(2) {
  width: 52%;
  height: 78%;
  translate: -90% 0;
  animation-duration: calc(var(--motion-campfire) * 1.28);
  opacity: 0.85;
}
.campfire-card__fire span:nth-child(3) {
  width: 48%;
  height: 70%;
  translate: -10% 0;
  animation-duration: calc(var(--motion-campfire) * 0.83);
  opacity: 0.8;
}
.campfire-card__fire i {
  position: absolute;
  left: calc(26% + var(--k) * 5%);
  bottom: 60%;
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: #ffcf7a;
  box-shadow: 0 0 6px #ff9a3c;
  animation: cf-ember calc(var(--motion-campfire) * (1.8 + var(--k) * 0.3)) linear infinite;
  animation-delay: calc(var(--motion-campfire) * var(--k) * -0.45);
}
.campfire-card__logs {
  position: absolute;
  left: 50%;
  bottom: 24.5%;
  width: 15%;
  height: 3.4%;
  transform: translateX(-50%);
  background:
    linear-gradient(12deg, transparent 40%, #2a1a12 41% 60%, transparent 61%),
    linear-gradient(-12deg, transparent 40%, #3a2416 41% 60%, transparent 61%);
  filter: drop-shadow(0 0 4px rgba(255, 140, 60, 0.6));
}
.campfire-card__caption {
  position: absolute;
  top: calc(12px * var(--ui-scale));
  left: calc(16px * var(--ui-scale));
  display: flex;
  align-items: baseline;
  gap: calc(10px * var(--ui-scale));
  margin: 0;
  font: var(--text-xs)/1 var(--f-sans);
  letter-spacing: 0.3em;
  color: var(--gold-500);
  text-shadow: 0 1px 3px #000;
}
.campfire-card__caption b {
  font-weight: 500;
  letter-spacing: 0.05em;
  color: var(--paper-300);
  font-variant-numeric: tabular-nums;
}
.campfire-card__party {
  position: absolute;
  inset: 0;
  margin: 0;
  padding: 0;
  list-style: none;
}
.campfire-card__member {
  position: absolute;
  display: grid;
  justify-items: center;
  gap: calc(4px * var(--ui-scale));
  transform: translateX(-50%);
}
.campfire-card__ring {
  position: relative;
  display: block;
}
.campfire-card__face {
  position: relative;
  display: grid;
  place-items: center;
  width: calc(54px * var(--ui-scale));
  height: calc(54px * var(--ui-scale));
  border-radius: 50%;
  overflow: hidden;
  background: var(--ink-860);
  border: 1.5px solid rgba(255, 190, 110, 0.75);
  box-shadow: 0 0 0 3px rgba(8, 6, 6, 0.85), 0 0 22px rgba(255, 150, 60, 0.38);
  filter: saturate(0.82) sepia(0.12);
}
.campfire-card__face .avatar-artwork,
.campfire-card__face img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.campfire-card__initial {
  font: var(--text-xl)/1 var(--f-display);
  color: var(--gold-300);
}
.campfire-card__moon {
  position: absolute;
  right: calc(-5px * var(--ui-scale));
  top: calc(-5px * var(--ui-scale));
  width: calc(21px * var(--ui-scale));
  height: calc(21px * var(--ui-scale));
  border-radius: 50%;
  background: radial-gradient(circle at 66% 38%, var(--ink-900) 46%, transparent 47.5%), #cdd7ee;
  box-shadow: 0 0 0 calc(2px * var(--ui-scale)) var(--ink-950), 0 0 calc(12px * var(--ui-scale)) rgba(170, 190, 230, 0.5);
}
.campfire-card__name {
  max-width: calc(96px * var(--ui-scale));
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font: var(--text-xs)/1.2 var(--f-serif);
  color: #f3e3c4;
  text-shadow: 0 1px 3px #000, 0 0 8px #000;
}
.campfire-card__bar {
  width: calc(76px * var(--ui-scale));
  height: calc(6px * var(--ui-scale));
  border-radius: 999px;
  background: rgba(20, 16, 14, 0.92);
  box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.6);
  overflow: hidden;
}
.campfire-card__bar span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #a98432, #f0c870);
  transition: width var(--motion-camp-fill) var(--ease-standard);
}
.campfire-card__pct {
  font: var(--text-xs)/1 var(--f-sans);
  color: #f3e3c4;
  text-shadow: 0 1px 3px #000;
  font-variant-numeric: tabular-nums;
}
.campfire-card__foot {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: center;
  gap: calc(16px * var(--ui-scale));
  min-height: calc(76px * var(--ui-scale));
  padding: calc(14px * var(--ui-scale)) calc(20px * var(--ui-scale));
  border-top: 1px solid rgba(185, 154, 96, 0.3);
  background: radial-gradient(70% 140% at 50% 0%, rgba(216, 120, 60, 0.08), transparent 70%);
}
.campfire-card__lines {
  display: grid;
  gap: calc(4px * var(--ui-scale));
}
.campfire-card__result {
  margin: 0;
  font: var(--text-md)/1.6 var(--f-serif);
  color: var(--paper-100);
  animation: cf-line-in var(--motion-reveal) var(--ease-standard) backwards;
}
.campfire-card.is-interrupted .campfire-card__result {
  color: #f0c2b4;
}
.campfire-card__event {
  margin: 0;
  font: var(--text-xs)/1.5 var(--f-sans);
  color: var(--paper-400);
  animation: cf-line-in var(--motion-reveal) var(--ease-standard) backwards;
}
.campfire-card__event span {
  color: var(--gold-500);
}
.campfire-card__hint {
  margin: 0;
  font: var(--text-xs)/1.5 var(--f-sans);
  color: var(--paper-500);
}
.campfire-card__go {
  display: inline-flex;
  align-items: center;
  gap: calc(8px * var(--ui-scale));
  min-height: calc(44px * var(--ui-scale));
  padding: 0 calc(18px * var(--ui-scale));
  border: 1px solid var(--gold-400);
  border-radius: calc(6px * var(--ui-scale));
  background: linear-gradient(180deg, rgba(228, 200, 142, 0.32), rgba(185, 154, 96, 0.16));
  color: var(--paper-50);
  font: var(--text-sm)/1 var(--f-serif);
  cursor: pointer;
}
.campfire-card__go kbd {
  font: var(--text-xs)/1 var(--f-sans);
  color: var(--gold-300);
}
.campfire-card__go:disabled {
  opacity: 0;
  pointer-events: none;
}
.campfire-card__go:focus-visible {
  outline: none;
  box-shadow: var(--focus);
}
.campfire-card__sr {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}
.campfire-card.is-still *,
.campfire-card.is-still *::before,
.campfire-card.is-still *::after {
  animation: none !important;
  transition: none !important;
}
@media (prefers-reduced-motion: reduce) {
  .campfire-card *,
  .campfire-card *::before,
  .campfire-card *::after {
    animation: none !important;
  }
}
@keyframes cf-flame {
  from {
    transform: scale(1, 1) skewX(-2deg);
  }
  to {
    transform: scale(0.92, 1.12) skewX(3deg);
  }
}
@keyframes cf-glow {
  50% {
    opacity: 0.8;
    transform: translateX(-50%) scale(0.97);
  }
}
@keyframes cf-ember {
  from {
    transform: translate(0, 0);
    opacity: 1;
  }
  to {
    transform: translate(calc((var(--k) - 5) * 6px), -170px);
    opacity: 0;
  }
}
@keyframes cf-twinkle {
  50% {
    opacity: 0.6;
  }
}
@keyframes cf-line-in {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
}
</style>
