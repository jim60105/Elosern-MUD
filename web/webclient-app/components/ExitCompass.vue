<script setup>
// ExitCompass (exploration-exit-compass; scene overview redesign §3): the
// exploration screen's movement control. Each exit sits on a circular pad at
// its bearing (angled pips) or on a dashed outer track (portal beads), and
// the player aims instead of reading a list of destination names.
//
// The component is thin over the pure `compass-model.js`. It sends nothing
// itself: it emits `aim` (for the shared readout and the minimap highlight),
// `blocked` (a refused move: no target, a disabled target, a dead end, a
// suppressed step, a halted walk), and `move(item)` with the committed exit
// row, which the pane submits through the store's exit gate.
//
// Pointer: hover aims; a press shorter than HOLD_MS moves once on release; a
// press held HOLD_MS on an angled target walks, steering with the cursor, and
// release stops it. Clicks while a move is in flight queue one more step.
//
// Keyboard (one tab stop, role="application"): arrows aim (two held arrows
// give the diagonal) and never move on a tap; `[` / `]` cycle every target;
// Enter / Space released before HOLD_MS move once; holding an arrow or Enter
// for HOLD_MS walks until every arrow and Enter is released. The compass
// consumes those keys (and Escape while it has an aim) so the document-level
// keyboard bridge never sees them; digits, `/`, and a bare Escape bubble.
//
// Continuous movement is commit-driven: after each arrival (a new
// `arrivalKey`) and at least STEP_DWELL_MS after the previous send, the live
// aim re-snaps against the new room and the next step is sent, never while
// the store gate is busy. Every stop bumps a generation counter, so a stale
// timer can never send.
import { computed, nextTick, onBeforeUnmount, ref, useId, watch } from "vue";
import {
  DEAD_ZONE,
  HOLD_MS,
  NO_AIM,
  SNAP_TOLERANCE,
  STEP_DWELL_MS,
  aimForTarget,
  aimFromKeys,
  aimFromPointer,
  cycleTarget,
  nextStep,
  normalizeAngle,
  resnapAim,
  snapAngled,
  snapPortal,
} from "./compass-model.js";

const props = defineProps({
  // `resolveTargets` output: {angled, portals, cycle}.
  targets: { type: Object, required: true },
  // True while the store gate would refuse a move (in flight or awaiting the
  // declared presentation revision).
  busy: { type: Boolean, default: false },
  // The committed room identity; a change is an arrival.
  arrivalKey: { type: [String, Number], default: null },
  // False while the compass is not the live exploration control (another
  // frame, a drawer, or an overlay is open, or the mode left exploration).
  active: { type: Boolean, default: true },
  // The effective motion level; `off` removes every animation.
  motionLevel: { type: String, default: "full" },
});

const emit = defineEmits(["aim", "blocked", "move"]);

// How long a step waits for a busy gate at an arrival commit, and how long a
// released gate may go without an arrival before the move counts as one
// that changed nothing.
const GATE_WAIT_MS = 2000;
const NO_CHANGE_MS = 1200;
const SHAKE_MS = 260;

const VIEW = 100;
const PAD_R = 72;
const PIP_R = 60;
const RING_R = 88;
const RING_START = 80 / PAD_R;

const uid = useId();
const padGradientId = `exit-compass-pad-${uid}`;
const knobGradientId = `exit-compass-knob-${uid}`;

const rootEl = ref(null);
const svgEl = ref(null);
const aim = ref(NO_AIM);
const pressing = ref(false);
const walking = ref(false);
const shaking = ref(false);

const keys = new Set();
let enterHeld = false;
let enterHoldFired = false;
let pointerHoldFired = false;
let pointerHoldTimer = null;
let arrowHoldTimer = null;
let enterHoldTimer = null;
let stepTimer = null;
let gateTimer = null;
let noChangeTimer = null;
let shakeTimer = null;
let waitingGate = false;
let queued = false;
let awaitingArrival = false;
let sentArrivalKey = null;
let lastSendAt = -Infinity;
let generation = 0;

function now() {
  return Date.now();
}

function polar(angle, r) {
  const rad = (angle * Math.PI) / 180;
  return { x: r * Math.sin(rad), y: -r * Math.cos(rad) };
}

function setAim(next) {
  aim.value = next;
  emit("aim", next);
}

function triggerShake() {
  if (props.motionLevel === "off") {
    return;
  }
  shaking.value = false;
  clearTimeout(shakeTimer);
  void nextTick(() => {
    shaking.value = true;
    // `animationend` normally clears it; the timer covers an animation that
    // never runs (a hidden pad, a stylesheet that drops it).
    shakeTimer = setTimeout(() => {
      shaking.value = false;
    }, SHAKE_MS + 100);
  });
}

function blocked(kind, target = null, message = null) {
  triggerShake();
  emit("blocked", { kind, target, message, angle: aim.value.angle });
}

function clearHoldTimers() {
  clearTimeout(pointerHoldTimer);
  clearTimeout(arrowHoldTimer);
  clearTimeout(enterHoldTimer);
  pointerHoldTimer = null;
  arrowHoldTimer = null;
  enterHoldTimer = null;
}

// Stop continuous movement and drop the queued step. A move already in
// flight still arrives; nothing follows it.
function stopWalking() {
  generation += 1;
  walking.value = false;
  queued = false;
  waitingGate = false;
  clearTimeout(stepTimer);
  clearTimeout(gateTimer);
  stepTimer = null;
  gateTimer = null;
}

// The single send path: one move at a time. While the gate is busy or the
// previous move has not arrived, the step is queued (at most one).
function trySend(target) {
  if (props.busy || awaitingArrival) {
    queued = true;
    return false;
  }
  queued = false;
  awaitingArrival = true;
  sentArrivalKey = props.arrivalKey;
  lastSendAt = now();
  clearTimeout(noChangeTimer);
  emit("move", target.item);
  return true;
}

function commitDiscrete(target) {
  if (!target) {
    blocked("no-exit");
    return;
  }
  if (!target.enabled) {
    blocked("disabled", target);
    return;
  }
  trySend(target);
}

// A hold on the aimed target: an enabled angled target starts a walk; a
// portal never chains (nothing is sent); no target or a disabled one says why.
function startWalk(target) {
  if (!target) {
    blocked("no-exit");
    return;
  }
  if (target.kind !== "angled") {
    return;
  }
  if (!target.enabled) {
    blocked("disabled", target);
    return;
  }
  stopWalking();
  walking.value = true;
  trySend(target);
}

function scheduleStep() {
  const token = generation;
  clearTimeout(stepTimer);
  const delay = Math.max(0, lastSendAt + STEP_DWELL_MS - now());
  stepTimer = setTimeout(() => {
    stepTimer = null;
    if (token === generation) {
      runStep(token);
    }
  }, delay);
}

function runStep(token) {
  if (token !== generation) {
    return;
  }
  if (!props.active) {
    stopWalking();
    return;
  }
  if (props.busy || awaitingArrival) {
    // The gate still holds the previous request (its presentation revision
    // has not landed): wait for it, but not forever.
    waitingGate = true;
    clearTimeout(gateTimer);
    gateTimer = setTimeout(() => {
      if (token === generation && waitingGate) {
        stopWalking();
        blocked("suppressed");
      }
    }, GATE_WAIT_MS);
    return;
  }
  waitingGate = false;
  clearTimeout(gateTimer);
  const wasWalking = walking.value;
  queued = false;
  if (!wasWalking && aim.value.zone === "ring") {
    // A queued click aimed at the outer track re-snaps to the new room's
    // portals and moves once.
    commitDiscrete(snapPortal(props.targets.portals, aim.value.angle));
    return;
  }
  const step = nextStep(props.targets, aim.value.angle);
  if (step.stop) {
    stopWalking();
    if (step.stop === "disabled") {
      blocked("disabled", step.target);
    } else {
      blocked(wasWalking ? "dead-end" : "no-exit");
    }
    return;
  }
  trySend(step.target);
}

// ---------------------------------------------------------------- arrival

watch(
  () => props.arrivalKey,
  () => {
    awaitingArrival = false;
    clearTimeout(noChangeTimer);
    setAim(resnapAim(props.targets, aim.value));
    if (walking.value || queued) {
      scheduleStep();
    }
  },
);

watch(
  () => props.busy,
  (busy) => {
    if (busy) {
      clearTimeout(noChangeTimer);
      return;
    }
    if (waitingGate) {
      waitingGate = false;
      clearTimeout(gateTimer);
      runStep(generation);
      return;
    }
    if (awaitingArrival && props.arrivalKey === sentArrivalKey) {
      // The gate released without an arrival: allow a lagging panel commit a
      // bounded grace, then treat the move as one that changed nothing.
      clearTimeout(noChangeTimer);
      noChangeTimer = setTimeout(() => {
        if (!awaitingArrival || props.busy) {
          return;
        }
        awaitingArrival = false;
        const wasMoving = walking.value || queued;
        stopWalking();
        if (wasMoving) {
          blocked("no-change");
        }
      }, NO_CHANGE_MS);
    }
  },
);

watch(
  () => props.active,
  (active) => {
    if (!active) {
      stopWalking();
      clearHoldTimers();
      keys.clear();
      enterHeld = false;
      pressing.value = false;
      setAim(NO_AIM);
    }
  },
);

// The pane's report that the store refused or the server rejected the
// compass's move: the walk stops and, with a message, the reason shows.
function halt(message = null) {
  awaitingArrival = false;
  clearTimeout(noChangeTimer);
  stopWalking();
  if (message) {
    blocked("rejected", null, message);
  }
}

function focus() {
  rootEl.value?.focus({ preventScroll: true });
}

defineExpose({ halt, focus, stop: stopWalking });

// ---------------------------------------------------------------- pointer

function pointerAim(event) {
  const svg = svgEl.value;
  if (!svg) {
    return NO_AIM;
  }
  const rect = svg.getBoundingClientRect();
  if (!rect.width) {
    return NO_AIM;
  }
  const scale = rect.width / (2 * VIEW);
  const dx = (event.clientX - (rect.left + rect.width / 2)) / scale;
  const dy = (event.clientY - (rect.top + rect.height / 2)) / scale;
  const dist = Math.hypot(dx, dy);
  if (dist > VIEW) {
    return NO_AIM;
  }
  const angle = normalizeAngle((Math.atan2(dx, -dy) * 180) / Math.PI);
  return aimFromPointer(props.targets, dist / PAD_R, angle, RING_START);
}

function onPointerMove(event) {
  if (!props.active) {
    return;
  }
  setAim(pointerAim(event));
}

function onPointerLeave() {
  pressing.value = false;
  clearTimeout(pointerHoldTimer);
  pointerHoldTimer = null;
  stopWalking();
  setAim(NO_AIM);
}

function onPointerDown(event) {
  if (!props.active || event.button !== 0) {
    return;
  }
  focus();
  pressing.value = true;
  pointerHoldFired = false;
  setAim(pointerAim(event));
  clearTimeout(pointerHoldTimer);
  pointerHoldTimer = setTimeout(() => {
    pointerHoldTimer = null;
    if (!pressing.value) {
      return;
    }
    pointerHoldFired = true;
    startWalk(aim.value.target);
  }, HOLD_MS);
}

function onPointerUp() {
  if (!pressing.value) {
    return;
  }
  pressing.value = false;
  clearTimeout(pointerHoldTimer);
  pointerHoldTimer = null;
  if (pointerHoldFired) {
    // A held press never also produces a discrete move: release only stops.
    stopWalking();
    return;
  }
  commitDiscrete(aim.value.target);
}

// ---------------------------------------------------------------- keyboard

function consume(event) {
  event.preventDefault();
  event.stopPropagation();
}

function isArrow(key) {
  return key === "ArrowUp" || key === "ArrowDown" || key === "ArrowLeft" || key === "ArrowRight";
}

function isMoveKey(key) {
  return key === "Enter" || key === " " || key === "Spacebar";
}

function armArrowHold() {
  if (walking.value) {
    return;
  }
  clearTimeout(arrowHoldTimer);
  arrowHoldTimer = setTimeout(() => {
    arrowHoldTimer = null;
    if (keys.size > 0 && !walking.value) {
      startWalk(aim.value.target);
    }
  }, HOLD_MS);
}

function onKeyDown(event) {
  if (!props.active || event.ctrlKey || event.metaKey || event.altKey || event.isComposing) {
    return;
  }
  const key = event.key;
  if (isArrow(key)) {
    consume(event);
    if (event.repeat || keys.has(key)) {
      return;
    }
    keys.add(key);
    const angle = aimFromKeys(keys);
    setAim(
      angle === null
        ? { angle: null, target: null, zone: "none" }
        : { angle, target: snapAngled(props.targets.angled, angle), zone: "pad" },
    );
    armArrowHold();
    return;
  }
  if (key === "[" || key === "]") {
    consume(event);
    setAim(aimForTarget(cycleTarget(props.targets, aim.value.target, key === "]" ? 1 : -1)));
    return;
  }
  if (isMoveKey(key)) {
    consume(event);
    if (event.repeat || enterHeld) {
      return;
    }
    enterHeld = true;
    enterHoldFired = false;
    clearTimeout(enterHoldTimer);
    enterHoldTimer = setTimeout(() => {
      enterHoldTimer = null;
      if (!enterHeld) {
        return;
      }
      enterHoldFired = true;
      if (!walking.value) {
        startWalk(aim.value.target);
      }
    }, HOLD_MS);
    return;
  }
  if (key === "Escape" && (aim.value.angle !== null || aim.value.target || walking.value)) {
    consume(event);
    stopWalking();
    clearHoldTimers();
    setAim(NO_AIM);
  }
}

function stopWhenReleased() {
  if (keys.size === 0 && !enterHeld && !pressing.value && walking.value) {
    stopWalking();
  }
}

function onKeyUp(event) {
  const key = event.key;
  if (key === "[" || key === "]") {
    consume(event);
    return;
  }
  if (isArrow(key)) {
    consume(event);
    keys.delete(key);
    if (keys.size === 0) {
      clearTimeout(arrowHoldTimer);
      arrowHoldTimer = null;
    }
    stopWhenReleased();
    return;
  }
  if (isMoveKey(key)) {
    consume(event);
    if (!enterHeld) {
      return;
    }
    enterHeld = false;
    clearTimeout(enterHoldTimer);
    enterHoldTimer = null;
    if (!enterHoldFired && !walking.value) {
      // A press shorter than HOLD_MS is one discrete move.
      commitDiscrete(aim.value.target);
    }
    stopWhenReleased();
  }
}

function onBlur() {
  keys.clear();
  enterHeld = false;
  clearHoldTimers();
  stopWalking();
  if (!pressing.value) {
    setAim(NO_AIM);
  }
}

onBeforeUnmount(() => {
  stopWalking();
  clearHoldTimers();
  clearTimeout(noChangeTimer);
  clearTimeout(shakeTimer);
});

// ---------------------------------------------------------------- drawing

const knob = computed(() => {
  const a = aim.value;
  if (a.target && a.target.kind === "angled") {
    return { ...polar(a.target.angle, PAD_R * 0.48), lit: true };
  }
  if (a.target && a.target.kind === "portal") {
    return { ...polar(a.target.slot, PAD_R * 0.62), lit: true };
  }
  if (a.angle !== null && a.angle !== undefined) {
    return { ...polar(a.angle, PAD_R * 0.3), lit: false };
  }
  return { x: 0, y: 0, lit: false };
});

const wedge = computed(() => {
  const a = aim.value;
  if (a.zone !== "pad" || a.angle === null || a.angle === undefined) {
    return null;
  }
  const p1 = polar(a.angle - SNAP_TOLERANCE, PAD_R);
  const p2 = polar(a.angle + SNAP_TOLERANCE, PAD_R);
  return `M0 0 L${p1.x} ${p1.y} A${PAD_R} ${PAD_R} 0 0 1 ${p2.x} ${p2.y} Z`;
});

const aimedKey = computed(() => (aim.value.target ? aim.value.target.key : null));
const aimRef = computed(() => (aim.value.target ? aim.value.target.exitRef : null));

const pips = computed(() =>
  props.targets.angled.map((target) => ({ target, ...polar(target.angle, PIP_R) })),
);
const beads = computed(() =>
  props.targets.portals.map((target) => ({ target, ...polar(target.slot, RING_R) })),
);
const ticks = [0, 90, 180, 270].map((a) => ({ a, p1: polar(a, PAD_R - 7), p2: polar(a, PAD_R - 1) }));
const deadR = DEAD_ZONE * PAD_R;
</script>

<template>
  <div
    ref="rootEl"
    class="exit-compass"
    :class="{
      'exit-compass--walking': walking,
      'exit-compass--inactive': !active,
    }"
    tabindex="0"
    role="application"
    aria-label="出口羅盤"
    data-testid="exit-compass"
    :data-walking="walking ? 'true' : 'false'"
    :data-aim-ref="aimRef"
    :data-motion-level="motionLevel"
    @keydown="onKeyDown"
    @keyup="onKeyUp"
    @blur="onBlur"
  >
    <svg
      ref="svgEl"
      class="exit-compass__svg"
      :class="{ 'exit-compass__svg--shake': shaking }"
      viewBox="-100 -100 200 200"
      aria-hidden="true"
      data-testid="exit-compass-pad"
      @pointermove="onPointerMove"
      @pointerleave="onPointerLeave"
      @pointercancel="onPointerLeave"
      @pointerdown="onPointerDown"
      @pointerup="onPointerUp"
      @animationend="shaking = false"
    >
      <defs>
        <radialGradient :id="padGradientId" cx="50%" cy="45%" r="60%">
          <stop offset="0%" class="exit-compass__pad-hi" />
          <stop offset="100%" class="exit-compass__pad-lo" />
        </radialGradient>
        <radialGradient :id="knobGradientId" cx="40%" cy="35%" r="70%">
          <stop offset="0%" class="exit-compass__knob-hi" />
          <stop offset="100%" class="exit-compass__knob-lo" />
        </radialGradient>
      </defs>
      <!-- The hit area. -->
      <circle r="100" fill="transparent" />
      <circle
        v-if="targets.portals.length"
        class="exit-compass__track"
        :class="{ 'exit-compass__track--lit': aim.zone === 'ring' }"
        data-testid="exit-compass-track"
        :r="RING_R"
      />
      <circle class="exit-compass__pad" :r="PAD_R" :fill="`url(#${padGradientId})`" />
      <line
        v-for="t in ticks"
        :key="t.a"
        class="exit-compass__tick"
        :x1="t.p1.x"
        :y1="t.p1.y"
        :x2="t.p2.x"
        :y2="t.p2.y"
      />
      <circle class="exit-compass__dead" :r="deadR" />
      <path v-if="wedge" class="exit-compass__wedge" data-testid="exit-compass-wedge" :d="wedge" />
      <g v-for="pip in pips" :key="pip.target.key">
        <line
          v-if="aimedKey === pip.target.key"
          class="exit-compass__ray"
          x1="0"
          y1="0"
          :x2="pip.x"
          :y2="pip.y"
        />
        <circle
          class="exit-compass__pip"
          :class="{
            'exit-compass__pip--off': !pip.target.enabled,
            'exit-compass__pip--on': aimedKey === pip.target.key,
          }"
          data-testid="exit-compass-pip"
          :data-exit-ref="pip.target.exitRef"
          :data-enabled="pip.target.enabled ? 'true' : 'false'"
          :data-aimed="aimedKey === pip.target.key ? 'true' : 'false'"
          :cx="pip.x"
          :cy="pip.y"
          :r="aimedKey === pip.target.key ? 7 : 5"
        />
      </g>
      <g
        v-for="bead in beads"
        :key="bead.target.key"
        class="exit-compass__bead"
        :class="{
          'exit-compass__bead--on': aimedKey === bead.target.key,
          'exit-compass__bead--off': !bead.target.enabled,
        }"
        data-testid="exit-compass-portal"
        :data-exit-ref="bead.target.exitRef"
        :data-enabled="bead.target.enabled ? 'true' : 'false'"
        :data-aimed="aimedKey === bead.target.key ? 'true' : 'false'"
        :transform="`translate(${bead.x} ${bead.y})`"
      >
        <rect x="-7.5" y="-7.5" width="15" height="15" transform="rotate(45)" />
        <text y="4.5">{{ bead.target.glyph }}</text>
      </g>
      <line class="exit-compass__stem" x1="0" y1="0" :x2="knob.x" :y2="knob.y" />
      <circle
        class="exit-compass__knob"
        :class="{ 'exit-compass__knob--lit': knob.lit, 'exit-compass__knob--pressed': pressing }"
        data-testid="exit-compass-knob"
        :cx="knob.x"
        :cy="knob.y"
        r="15"
        :fill="`url(#${knobGradientId})`"
      />
      <circle class="exit-compass__here" r="3.2" />
    </svg>
  </div>
</template>

<style scoped>
/* The shake rides the command-panel motion token (about 250 ms) and its
   travel scales with `--motion-travel`, so `reduced` keeps no movement.
   Geometry and colours follow the redesign prototype
   (docs/design/scene-overview-redesign/ExitCompassPrototype.vue). The pad's
   inner ground and the portal violet have no design token; they are kept as
   component-local custom properties so they live in one place. */
.exit-compass {
  --compass-pad-hi: #2a2620;
  --compass-pad-lo: #121418;
  --compass-rim: #8a7550;
  --compass-tick: #6b604c;
  --compass-dead: #3a352d;
  --compass-track: #5c5446;
  --compass-off: #8c826e;
  --compass-portal-fill: #221c2a;
  --compass-portal-rim: #9b84c4;
  --compass-portal-text: #e1d4f5;
  --compass-portal-on-fill: #3a2d4d;
  --compass-portal-on-rim: #e4d6ff;
  --compass-knob-hi: #5a4a30;
  --compass-knob-lo: #241d14;
  --compass-highlight: #fff6dd;
  position: relative;
  box-sizing: border-box;
  height: 100%;
  aspect-ratio: 1 / 1;
  max-width: 100%;
  border-radius: 50%;
  outline: none;
  touch-action: none;
}

.exit-compass:focus-visible {
  box-shadow:
    0 0 0 2px var(--gold-500),
    0 0 calc(18px * var(--ui-scale)) var(--gold-glow);
}

.exit-compass--inactive {
  pointer-events: none;
}

.exit-compass__svg {
  display: block;
  width: 100%;
  height: 100%;
  cursor: crosshair;
  user-select: none;
}

.exit-compass__svg--shake {
  animation: exit-compass-shake var(--motion-panel) var(--ease-standard);
}

@keyframes exit-compass-shake {
  20% {
    transform: translateX(calc(-3px * var(--motion-travel)));
  }
  45% {
    transform: translateX(calc(3px * var(--motion-travel)));
  }
  70% {
    transform: translateX(calc(-2px * var(--motion-travel)));
  }
}

.exit-compass__pad-hi {
  stop-color: var(--compass-pad-hi);
}
.exit-compass__pad-lo {
  stop-color: var(--compass-pad-lo);
}
.exit-compass__knob-hi {
  stop-color: var(--compass-knob-hi);
}
.exit-compass__knob-lo {
  stop-color: var(--compass-knob-lo);
}

.exit-compass__track {
  fill: none;
  stroke: var(--compass-track);
  stroke-width: 1.2;
  stroke-dasharray: 3 5;
  transition: stroke var(--motion-fast);
}
.exit-compass__track--lit {
  stroke: var(--gold-500);
}

.exit-compass__pad {
  stroke: var(--compass-rim);
  stroke-width: 1.4;
}
.exit-compass--walking .exit-compass__pad {
  stroke: var(--gold-400);
  stroke-width: 2;
}

.exit-compass__tick {
  stroke: var(--compass-tick);
  stroke-width: 1.4;
}

.exit-compass__dead {
  fill: none;
  stroke: var(--compass-dead);
  stroke-dasharray: 1 3;
}

.exit-compass__wedge {
  fill: var(--gold-400);
  opacity: 0.1;
  pointer-events: none;
}

.exit-compass__ray {
  stroke: var(--gold-400);
  stroke-width: 1.5;
  opacity: 0.5;
}

.exit-compass__pip {
  fill: var(--gold-500);
  transition: r var(--motion-fast);
}
.exit-compass__pip--on {
  fill: var(--gold-300);
  stroke: var(--compass-highlight);
  stroke-width: 1.5;
  filter: drop-shadow(0 0 4px rgba(228, 200, 142, 0.8));
}
.exit-compass__pip--off {
  fill: none;
  stroke: var(--compass-off);
  stroke-width: 1.4;
  stroke-dasharray: 2 2;
}
.exit-compass__pip--off.exit-compass__pip--on {
  stroke: var(--seal-400);
  filter: none;
}

.exit-compass__bead rect {
  fill: var(--compass-portal-fill);
  stroke: var(--compass-portal-rim);
  stroke-width: 1.3;
}
.exit-compass__bead text {
  fill: var(--compass-portal-text);
  font-size: 12px;
  text-anchor: middle;
  font-family: var(--f-sans);
  pointer-events: none;
}
.exit-compass__bead--on rect {
  fill: var(--compass-portal-on-fill);
  stroke: var(--compass-portal-on-rim);
  stroke-width: 2;
  filter: drop-shadow(0 0 4px rgba(190, 160, 240, 0.8));
}
.exit-compass__bead--off rect {
  stroke-dasharray: 2 2;
  fill: transparent;
}
.exit-compass__bead--off.exit-compass__bead--on rect {
  stroke: var(--seal-400);
}

.exit-compass__stem {
  stroke: var(--gold-500);
  stroke-width: 3;
  stroke-linecap: round;
  opacity: 0.55;
}

.exit-compass__knob {
  stroke: var(--compass-rim);
  stroke-width: 1.8;
  transition:
    cx var(--motion-fast) var(--ease-standard),
    cy var(--motion-fast) var(--ease-standard);
}
.exit-compass__knob--lit {
  stroke: var(--gold-300);
  stroke-width: 2.2;
}
.exit-compass__knob--pressed {
  stroke: var(--compass-highlight);
}

.exit-compass__here {
  fill: var(--seal-500);
  pointer-events: none;
}

/* The `off` motion level: every transition resolves in the commit frame and
   the pad never shakes (the readout's static flash carries the signal). */
.exit-compass[data-motion-level="off"] .exit-compass__svg--shake {
  animation: none;
}
.exit-compass[data-motion-level="off"] .exit-compass__knob,
.exit-compass[data-motion-level="off"] .exit-compass__pip,
.exit-compass[data-motion-level="off"] .exit-compass__track {
  transition: none;
}
</style>
