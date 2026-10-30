<script setup>
// The campfire beat (prototype, sub-project 3). A night scene with a fire
// (the real game needs one new campfire illustration with anonymous seated
// silhouettes; the prototype grades an existing path painting down to night
// and lights it with a CSS fire), the party as medallions in an arc whose
// 精力 bars fill from the pre-sleep to the post-sleep value, then the result
// line. Any key or click finishes the beat early; Enter continues.
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { RESERVE_FULL } from "./travel-model.js";

const props = defineProps({
  members: { type: Array, required: true },
  result: { type: String, required: true },
  art: { type: String, default: "/art/scenes/forest_path.webp" },
  motion: { type: String, default: "full" },
});
const emit = defineEmits(["done"]);

const filled = ref(props.motion === "off");
const settled = ref(props.motion === "off");
const card = ref(null);
let timers = [];

function pct(r) {
  return Math.round((r / RESERVE_FULL) * 100);
}

const arc = computed(() => {
  const n = props.members.length;
  return props.members.map((m, i) => {
    const t = n === 1 ? 0.5 : i / (n - 1);
    const angle = (-38 + 76 * t) * (Math.PI / 180);
    // Seated around the fire: the far side of the ring stands higher.
    return { ...m, x: 50 + Math.sin(angle) * 36, y: 40 - (1 - Math.cos(angle)) * 80 };
  });
});

function finish() {
  timers.forEach(clearTimeout);
  filled.value = true;
  settled.value = true;
}

function onKey(event) {
  event.preventDefault();
  if (!settled.value) finish();
  else if (event.key === "Enter" || event.key === " " || event.key === "Escape") emit("done");
}

onMounted(() => {
  card.value?.focus({ preventScroll: true });
  if (props.motion !== "off") {
    timers.push(setTimeout(() => (filled.value = true), 450));
    timers.push(setTimeout(() => (settled.value = true), 2100));
  }
});
onBeforeUnmount(() => timers.forEach(clearTimeout));
</script>

<template>
  <section
    ref="card"
    class="choice-card campfire-card"
    :class="{ 'is-still': motion === 'off' }"
    tabindex="-1"
    role="dialog"
    aria-label="營火"
    @keydown="onKey"
    @click="settled ? null : finish()"
  >
    <div class="campfire-card__scene">
      <div class="campfire-card__art" :style="{ backgroundImage: `url(${art})` }"></div>
      <div class="campfire-card__night"></div>
      <div class="campfire-card__glow"></div>
      <div class="campfire-card__fire" aria-hidden="true">
        <span></span><span></span><span></span>
        <i v-for="k in 7" :key="k" :style="{ '--k': k }"></i>
      </div>
      <div class="campfire-card__logs" aria-hidden="true"></div>
      <ul class="campfire-card__party">
        <li
          v-for="m in arc"
          :key="m.id"
          :style="{ left: `${m.x}%`, bottom: `${m.y}%` }"
          :aria-label="`${m.name}：精力 ${pct(m.from)}% → ${pct(m.to)}%`"
        >
          <span class="campfire-card__face" :style="{ backgroundImage: `url(${m.portrait})` }">
            <span class="campfire-card__moon"></span>
          </span>
          <span class="campfire-card__bar">
            <span :style="{ width: `${filled ? pct(m.to) : pct(m.from)}%` }"></span>
          </span>
          <span class="campfire-card__pct">{{ filled ? pct(m.to) : pct(m.from) }}%</span>
        </li>
      </ul>
    </div>
    <footer class="campfire-card__foot" :class="{ 'is-shown': settled }">
      <p class="campfire-card__result" aria-live="polite">{{ settled ? result : "　" }}</p>
      <button type="button" class="leg-btn leg-btn--primary" :disabled="!settled" @click.stop="emit('done')">
        繼續旅程 <kbd>Enter</kbd>
      </button>
    </footer>
  </section>
</template>

<style>
.campfire-card {
  overflow: hidden;
  padding: 0;
}
.campfire-card__scene {
  position: relative;
  aspect-ratio: 16 / 9;
  overflow: hidden;
}
.campfire-card__art {
  position: absolute;
  inset: -4%;
  background-size: cover;
  background-position: 50% 70%;
  filter: brightness(0.42) saturate(0.6) hue-rotate(-12deg) blur(0.8px);
  transform: scale(1.04);
}
.campfire-card__night {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(180deg, rgba(10, 16, 34, 0.75), rgba(10, 12, 20, 0.2) 45%, rgba(8, 6, 6, 0.75)),
    radial-gradient(60% 50% at 50% 100%, transparent, rgba(5, 6, 10, 0.7));
}
.campfire-card__glow {
  position: absolute;
  left: 50%;
  bottom: -18%;
  width: 90%;
  aspect-ratio: 1.6;
  transform: translateX(-50%);
  background: radial-gradient(closest-side, rgba(255, 176, 86, 0.55), rgba(220, 110, 40, 0.22) 45%, transparent 74%);
  mix-blend-mode: screen;
  animation: cf-glow 2.4s ease-in-out infinite;
}
.campfire-card__fire {
  position: absolute;
  left: 50%;
  bottom: 14%;
  width: 12%;
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
  animation: cf-flame 0.9s ease-in-out infinite alternate;
}
.campfire-card__fire span:nth-child(2) {
  width: 52%;
  height: 78%;
  translate: -90% 0;
  animation-duration: 1.15s;
  opacity: 0.85;
}
.campfire-card__fire span:nth-child(3) {
  width: 48%;
  height: 70%;
  translate: -10% 0;
  animation-duration: 0.75s;
  opacity: 0.8;
}
.campfire-card__fire i {
  position: absolute;
  left: calc(30% + var(--k) * 6%);
  bottom: 60%;
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: #ffcf7a;
  box-shadow: 0 0 6px #ff9a3c;
  animation: cf-ember calc(1.6s + var(--k) * 0.27s) linear infinite;
  animation-delay: calc(var(--k) * -0.4s);
}
.campfire-card__logs {
  position: absolute;
  left: 50%;
  bottom: 12%;
  width: 15%;
  height: 3.2%;
  transform: translateX(-50%);
  background:
    linear-gradient(12deg, transparent 40%, #2a1a12 41% 60%, transparent 61%),
    linear-gradient(-12deg, transparent 40%, #3a2416 41% 60%, transparent 61%);
  filter: drop-shadow(0 0 4px rgba(255, 140, 60, 0.6));
}
.campfire-card__party {
  position: absolute;
  inset: 0;
  margin: 0;
  padding: 0;
  list-style: none;
}
.campfire-card__party li {
  position: absolute;
  transform: translateX(-50%);
  display: grid;
  justify-items: center;
  gap: calc(4px * var(--ui-scale));
}
.campfire-card__face {
  position: relative;
  width: calc(64px * var(--ui-scale));
  height: calc(64px * var(--ui-scale));
  border-radius: 50%;
  background-size: 220%;
  background-position: 50% 9%;
  border: 1.5px solid rgba(255, 190, 110, 0.75);
  box-shadow: 0 0 0 3px rgba(8, 6, 6, 0.85), 0 0 22px rgba(255, 150, 60, 0.35);
  filter: saturate(0.8) sepia(0.15);
}
.campfire-card__moon {
  position: absolute;
  right: -4px;
  top: -4px;
  width: calc(20px * var(--ui-scale));
  height: calc(20px * var(--ui-scale));
  border-radius: 50%;
  background: radial-gradient(circle at 65% 40%, #10131c 46%, transparent 47%), #c8d4ee;
  box-shadow: 0 0 0 2px #0a0b0f;
}
.campfire-card__bar {
  width: calc(72px * var(--ui-scale));
  height: calc(6px * var(--ui-scale));
  border-radius: 3px;
  background: rgba(20, 16, 14, 0.9);
  overflow: hidden;
}
.campfire-card__bar span {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, #a98432, #f0c870);
  transition: width 1.6s var(--ease-standard);
}
.campfire-card.is-still .campfire-card__bar span {
  transition: none;
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
  padding: calc(14px * var(--ui-scale)) calc(20px * var(--ui-scale));
  border-top: 1px solid rgba(185, 154, 96, 0.3);
}
.campfire-card__result {
  margin: 0;
  font: var(--text-md)/1.6 var(--f-serif);
  color: var(--paper-100);
  opacity: 0;
  transition: opacity var(--motion-reveal) var(--ease-standard);
}
.campfire-card__foot.is-shown .campfire-card__result {
  opacity: 1;
}
.campfire-card.is-still *,
.campfire-card.is-still *::before {
  animation: none !important;
}
@media (prefers-reduced-motion: reduce) {
  .campfire-card *,
  .campfire-card *::before {
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
    transform: translate(calc((var(--k) - 4) * 6px), -160px);
    opacity: 0;
  }
}
</style>
