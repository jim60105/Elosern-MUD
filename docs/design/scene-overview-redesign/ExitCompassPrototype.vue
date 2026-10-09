<script setup>
// Prototype of ExitCompass (spec §3.1). Reference only.
//
// Pointer: hovering the pad aims (the knob leans toward the cursor and snaps
// to the nearest exit within ±30°; the dashed outer track snaps to the
// nearest portal bead); a click moves once; clicks while a move is in
// flight queue at most one more step; a press held for HOLD_MS walks
// continuously, re-snapping the live aim in every new room.
//
// Keyboard (one tab stop): arrows aim (two held arrows give the diagonal),
// `[` / `]` cycle every exit and portal, Enter / Space move, and holding an
// arrow or Enter for HOLD_MS walks continuously until it is released.
import { computed, onBeforeUnmount, ref, watch } from "vue";
import {
  DEAD_ZONE,
  HOLD_MS,
  STEP_DWELL_MS,
  SNAP_TOLERANCE,
  aimFromKeys,
  aimFromPointer,
  nextStep,
  normalizeAngle,
  snapAngled,
} from "./compass-model.js";

const props = defineProps({
  targets: { type: Object, required: true },
  busy: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
});
const emit = defineEmits(["move", "aim", "blocked"]);

const PAD_R = 72;
const PIP_R = 60;
const RING_R = 88;
const RING_START = 80 / PAD_R;

const svgEl = ref(null);
const aim = ref({ angle: null, target: null, zone: "none" });
const pressing = ref(false);
const walking = ref(false);
const shaking = ref(false);
const keys = new Set();
let holdTimer = null;
let pendingStep = false;
let dwellTimer = null;
let enterHeld = false;

function polar(angle, r) {
  const rad = (angle * Math.PI) / 180;
  return { x: r * Math.sin(rad), y: -r * Math.cos(rad) };
}

const knob = computed(() => {
  const a = aim.value;
  if (a.target && a.target.kind === "angled") {
    return { ...polar(a.target.angle, PAD_R * 0.48), lit: true };
  }
  if (a.target && a.target.kind === "portal") {
    return { ...polar(a.target.slot, PAD_R * 0.62), lit: true };
  }
  if (a.angle !== null) {
    return { ...polar(a.angle, PAD_R * 0.3), lit: false };
  }
  return { x: 0, y: 0, lit: false };
});

const wedge = computed(() => {
  const a = aim.value;
  if (a.zone !== "pad" || a.angle === null) {
    return null;
  }
  const p1 = polar(a.angle - SNAP_TOLERANCE, PAD_R);
  const p2 = polar(a.angle + SNAP_TOLERANCE, PAD_R);
  return `M0 0 L${p1.x} ${p1.y} A${PAD_R} ${PAD_R} 0 0 1 ${p2.x} ${p2.y} Z`;
});

function setAim(next) {
  aim.value = next;
  emit("aim", next);
}

function shake(reason) {
  shaking.value = false;
  requestAnimationFrame(() => {
    shaking.value = true;
  });
  emit("blocked", reason);
}

function commit(target) {
  if (!target) {
    shake({ kind: "no-exit" });
    return;
  }
  if (!target.enabled) {
    shake({ kind: "disabled", target });
    return;
  }
  if (props.busy) {
    pendingStep = true;
    return;
  }
  emit("move", target);
}

// --- pointer -------------------------------------------------------------

function pointerAim(event) {
  const rect = svgEl.value.getBoundingClientRect();
  const scale = rect.width / 200;
  const dx = (event.clientX - (rect.left + rect.width / 2)) / scale;
  const dy = (event.clientY - (rect.top + rect.height / 2)) / scale;
  const dist = Math.hypot(dx, dy);
  if (dist > 100) {
    return { angle: null, target: null, zone: "none" };
  }
  const angle = normalizeAngle((Math.atan2(dx, -dy) * 180) / Math.PI);
  return aimFromPointer(props.targets, dist / PAD_R, angle, RING_START);
}

function onPointerMove(event) {
  if (props.disabled) {
    return;
  }
  setAim(pointerAim(event));
}

function onPointerLeave() {
  stopWalking();
  setAim({ angle: null, target: null, zone: "none" });
}

function onPointerDown(event) {
  if (props.disabled || event.button !== 0) {
    return;
  }
  svgEl.value.parentElement.focus({ preventScroll: true });
  pressing.value = true;
  setAim(pointerAim(event));
  clearTimeout(holdTimer);
  holdTimer = setTimeout(() => {
    if (pressing.value && aim.value.target && aim.value.target.kind === "angled") {
      walking.value = true;
      commit(aim.value.target);
    }
  }, HOLD_MS);
}

function onPointerUp() {
  if (!pressing.value) {
    return;
  }
  pressing.value = false;
  clearTimeout(holdTimer);
  if (walking.value) {
    stopWalking();
    return;
  }
  commit(aim.value.target);
}

// --- keyboard ------------------------------------------------------------

function onKeyDown(event) {
  if (props.disabled) {
    return;
  }
  const k = event.key;
  if (k.startsWith("Arrow")) {
    event.preventDefault();
    if (event.repeat) {
      return;
    }
    keys.add(k);
    const angle = aimFromKeys(keys);
    setAim({ angle, target: angle === null ? null : snapAngled(props.targets.angled, angle), zone: "pad" });
    armKeyHold();
  } else if (k === "[" || k === "]") {
    event.preventDefault();
    cycle(k === "]" ? 1 : -1);
  } else if (k === "Enter" || k === " ") {
    event.preventDefault();
    if (event.repeat) {
      return;
    }
    enterHeld = true;
    commit(aim.value.target);
    armKeyHold();
  }
}

function onKeyUp(event) {
  const k = event.key;
  if (k.startsWith("Arrow")) {
    keys.delete(k);
  } else if (k === "Enter" || k === " ") {
    enterHeld = false;
  } else {
    return;
  }
  if (keys.size === 0 && !enterHeld) {
    clearTimeout(holdTimer);
    stopWalking();
  }
}

function armKeyHold() {
  clearTimeout(holdTimer);
  holdTimer = setTimeout(() => {
    if ((keys.size > 0 || enterHeld) && aim.value.target && aim.value.target.kind === "angled") {
      walking.value = true;
      commit(aim.value.target);
    }
  }, HOLD_MS);
}

function cycle(step) {
  const list = props.targets.cycle;
  if (list.length === 0) {
    return;
  }
  const index = list.indexOf(aim.value.target);
  const next = list[(index + step + list.length) % list.length];
  setAim({
    angle: next.kind === "angled" ? next.angle : next.slot,
    target: next,
    zone: next.kind === "angled" ? "pad" : "ring",
  });
}

function onBlur() {
  keys.clear();
  enterHeld = false;
  clearTimeout(holdTimer);
  stopWalking();
}

// --- arrival -------------------------------------------------------------

function stopWalking() {
  walking.value = false;
  pendingStep = false;
  clearTimeout(dwellTimer);
}

// A new room's targets: re-resolve the live aim against them, then decide
// whether a held press or a queued click takes the next step.
watch(
  () => props.targets,
  (targets) => {
    const a = aim.value;
    if (a.angle !== null && a.zone === "pad") {
      setAim({ ...a, target: snapAngled(targets.angled, a.angle) });
    } else {
      setAim({ angle: null, target: null, zone: "none" });
    }
    if (!walking.value && !pendingStep) {
      return;
    }
    const queued = pendingStep;
    pendingStep = false;
    clearTimeout(dwellTimer);
    dwellTimer = setTimeout(() => {
      const step = nextStep(targets, aim.value.angle);
      if (step.stop) {
        walking.value = false;
        shake({ kind: step.stop, target: step.target || null });
        return;
      }
      if (walking.value || queued) {
        emit("move", step.target);
      }
    }, STEP_DWELL_MS);
  },
);

onBeforeUnmount(() => {
  clearTimeout(holdTimer);
  clearTimeout(dwellTimer);
});

function pipPos(t) {
  return polar(t.angle, PIP_R);
}
function beadPos(p) {
  return polar(p.slot, RING_R);
}
function beadGlyph(p) {
  return p.vertical === "up" ? "⇧" : p.vertical === "down" ? "⇩" : "✦";
}
const ticks = [0, 90, 180, 270].map((a) => ({ a, p1: polar(a, PAD_R - 7), p2: polar(a, PAD_R - 1) }));
const deadR = DEAD_ZONE * PAD_R;
</script>

<template>
  <div
    class="compass"
    :class="{ 'compass--walking': walking, 'compass--disabled': disabled }"
    tabindex="0"
    role="application"
    aria-label="出口羅盤"
    @keydown="onKeyDown"
    @keyup="onKeyUp"
    @blur="onBlur"
  >
    <svg
      ref="svgEl"
      class="compass__svg"
      :class="{ 'compass__svg--shake': shaking }"
      viewBox="-100 -100 200 200"
      @pointermove="onPointerMove"
      @pointerleave="onPointerLeave"
      @pointerdown="onPointerDown"
      @pointerup="onPointerUp"
      @animationend="shaking = false"
    >
      <defs>
        <radialGradient id="compass-pad" cx="50%" cy="45%" r="60%">
          <stop offset="0%" stop-color="#2a2620" />
          <stop offset="100%" stop-color="#121418" />
        </radialGradient>
        <radialGradient id="compass-knob" cx="40%" cy="35%" r="70%">
          <stop offset="0%" stop-color="#5a4a30" />
          <stop offset="100%" stop-color="#241d14" />
        </radialGradient>
      </defs>
      <!-- hit area -->
      <circle r="100" fill="transparent" />
      <!-- portal track -->
      <circle
        v-if="targets.portals.length"
        class="compass__track"
        :class="{ 'compass__track--lit': aim.zone === 'ring' }"
        :r="RING_R"
      />
      <!-- pad -->
      <circle class="compass__pad" :r="PAD_R" fill="url(#compass-pad)" />
      <line v-for="t in ticks" :key="t.a" class="compass__tick" :x1="t.p1.x" :y1="t.p1.y" :x2="t.p2.x" :y2="t.p2.y" />
      <circle class="compass__dead" :r="deadR" />
      <path v-if="wedge" class="compass__wedge" :d="wedge" />
      <!-- angled exits -->
      <g v-for="t in targets.angled" :key="t.key">
        <line
          v-if="aim.target === t"
          class="compass__ray"
          x1="0"
          y1="0"
          :x2="pipPos(t).x"
          :y2="pipPos(t).y"
        />
        <circle
          class="compass__pip"
          :class="{
            'compass__pip--off': !t.enabled,
            'compass__pip--on': aim.target === t,
          }"
          :cx="pipPos(t).x"
          :cy="pipPos(t).y"
          :r="aim.target === t ? 7 : 5"
        />
      </g>
      <!-- portals -->
      <g
        v-for="p in targets.portals"
        :key="p.key"
        class="compass__bead"
        :class="{ 'compass__bead--on': aim.target === p, 'compass__bead--off': !p.enabled }"
        :transform="`translate(${beadPos(p).x} ${beadPos(p).y})`"
      >
        <rect x="-7.5" y="-7.5" width="15" height="15" transform="rotate(45)" />
        <text y="4.5">{{ beadGlyph(p) }}</text>
      </g>
      <!-- knob -->
      <line class="compass__stem" x1="0" y1="0" :x2="knob.x" :y2="knob.y" />
      <circle
        class="compass__knob"
        :class="{ 'compass__knob--lit': knob.lit, 'compass__knob--pressed': pressing }"
        :cx="knob.x"
        :cy="knob.y"
        r="15"
        fill="url(#compass-knob)"
      />
      <circle class="compass__here" r="3.2" />
    </svg>
  </div>
</template>

<style scoped>
.compass {
  position: relative;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  outline: none;
  touch-action: none;
}
.compass:focus-visible {
  box-shadow: 0 0 0 2px var(--gold-500), 0 0 calc(18px * var(--ui-scale)) var(--gold-glow);
}
.compass--disabled {
  opacity: 0.4;
  pointer-events: none;
}
.compass__svg {
  display: block;
  width: 100%;
  height: 100%;
  cursor: crosshair;
  user-select: none;
}
.compass__svg--shake {
  animation: compass-shake 260ms var(--ease-standard);
}
@keyframes compass-shake {
  20% { transform: translateX(-3px); }
  45% { transform: translateX(3px); }
  70% { transform: translateX(-2px); }
}
.compass__track {
  fill: none;
  stroke: #5c5446;
  stroke-width: 1.2;
  stroke-dasharray: 3 5;
  transition: stroke 120ms;
}
.compass__track--lit {
  stroke: var(--gold-500);
}
.compass__pad {
  stroke: #8a7550;
  stroke-width: 1.4;
}
.compass--walking .compass__pad {
  stroke: var(--gold-400);
  stroke-width: 2;
}
.compass__tick {
  stroke: #6b604c;
  stroke-width: 1.4;
}
.compass__dead {
  fill: none;
  stroke: #3a352d;
  stroke-dasharray: 1 3;
}
.compass__wedge {
  fill: var(--gold-400);
  opacity: 0.1;
  pointer-events: none;
}
.compass__ray {
  stroke: var(--gold-400);
  stroke-width: 1.5;
  opacity: 0.5;
}
.compass__pip {
  fill: var(--gold-500);
  transition: r 100ms;
}
.compass__pip--on {
  fill: var(--gold-300);
  stroke: #fff6dd;
  stroke-width: 1.5;
  filter: drop-shadow(0 0 4px rgba(228, 200, 142, 0.8));
}
.compass__pip--off {
  fill: none;
  stroke: #8c826e;
  stroke-width: 1.4;
  stroke-dasharray: 2 2;
}
.compass__pip--off.compass__pip--on {
  stroke: var(--seal-400);
  filter: none;
}
.compass__bead rect {
  fill: #221c2a;
  stroke: #9b84c4;
  stroke-width: 1.3;
}
.compass__bead text {
  fill: #e1d4f5;
  font-size: 12px;
  text-anchor: middle;
  font-family: var(--f-sans);
  pointer-events: none;
}
.compass__bead--on rect {
  fill: #3a2d4d;
  stroke: #e4d6ff;
  stroke-width: 2;
  filter: drop-shadow(0 0 4px rgba(190, 160, 240, 0.8));
}
.compass__bead--off rect {
  stroke-dasharray: 2 2;
  fill: transparent;
}
.compass__bead--off.compass__bead--on rect {
  stroke: var(--seal-400);
}
.compass__stem {
  stroke: var(--gold-500);
  stroke-width: 3;
  stroke-linecap: round;
  opacity: 0.55;
}
.compass__knob {
  stroke: #8a7550;
  stroke-width: 1.8;
  transition: cx 90ms var(--ease-standard), cy 90ms var(--ease-standard);
}
.compass__knob--lit {
  stroke: var(--gold-300);
  stroke-width: 2.2;
}
.compass__knob--pressed {
  stroke: #fff6dd;
}
.compass__here {
  fill: var(--seal-500);
  pointer-events: none;
}
</style>
