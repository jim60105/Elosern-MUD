// The message window's typewriter clock (docs/superpowers/specs/2026-09-23-
// webclient-avg-stage-redesign-design.md §6.4; OpenSpec change
// webclient-typewriter-reading-prefs, design D3).
//
// One `requestAnimationFrame` loop drives both the typed count and the
// auto-advance wait, so the two never drift. Each frame adds at most 100ms,
// and a hidden tab gets no frames, so time spent there never counts. The
// loop runs only while there is work (a page typing or a wait armed).
//
//   useTypewriter({ units, snap, cps, held })
//     units() — the page's reveal units; snap(n) — the map-art snap;
//     cps() — characters per second (`Infinity` = instant);
//     held() — true pauses the auto-advance wait.
//
// The typed count is `snap(min(units, from + floor(elapsed × rate / 1000)))`,
// where `rate` is `cps()` sampled once at `start()`: a speed change applies
// from the next page, so the page on screen never changes pace or un-reveals
// a character. With `Infinity` cps a `start()` completes synchronously, with
// no frame.
import { computed, onBeforeUnmount, ref } from "vue";

// The longest step one frame may add (a long gap never counts in full).
export const FRAME_CLAMP_MS = 100;

function requestFrame(callback) {
  if (typeof globalThis.requestAnimationFrame === "function") {
    return { raf: true, id: globalThis.requestAnimationFrame(callback) };
  }
  return {
    raf: false,
    id: setTimeout(() => callback(globalThis.performance ? globalThis.performance.now() : Date.now()), 16),
  };
}

function cancelFrame(handle) {
  if (!handle) {
    return;
  }
  if (handle.raf) {
    globalThis.cancelAnimationFrame?.(handle.id);
  } else {
    clearTimeout(handle.id);
  }
}

export function useTypewriter({ units, snap = (n) => n, cps, held = () => false }) {
  const typed = ref(0);
  const typing = computed(() => typed.value < units());

  let running = false;
  let rate = Infinity;
  let from = 0;
  let elapsed = 0;
  let advance = null;
  let frame = null;
  let last = null;

  function clampUnits(n) {
    const total = units();
    if (typeof n !== "number" || !(n > 0)) {
      return 0;
    }
    return Math.min(total, Math.floor(n));
  }

  function schedule() {
    if (running || advance) {
      if (frame === null) {
        frame = requestFrame(tick);
      }
      return;
    }
    cancelFrame(frame);
    frame = null;
    last = null;
  }

  function tick(now) {
    frame = null;
    const dt = last === null ? 0 : Math.min(Math.max(now - last, 0), FRAME_CLAMP_MS);
    last = now;
    if (running) {
      elapsed += dt;
      const total = units();
      const next = rate === Infinity ? total : Math.min(total, from + Math.floor((elapsed * rate) / 1000));
      typed.value = Math.max(typed.value, Math.min(total, snap(next)));
      if (typed.value >= total) {
        running = false;
      }
    } else if (advance) {
      if (!held()) {
        advance.waited += dt;
      }
      if (advance.waited >= advance.ms) {
        const due = advance.onDue;
        advance = null;
        due();
      }
    }
    schedule();
  }

  // Type from `fromUnits` (units before it show at once).
  function start(fromUnits = 0) {
    const total = units();
    from = Math.min(total, snap(clampUnits(fromUnits)));
    elapsed = 0;
    rate = cps();
    if (rate === Infinity || from >= total) {
      typed.value = total;
      running = false;
    } else {
      typed.value = from;
      running = true;
    }
    schedule();
  }

  // Show the page in full now.
  function complete() {
    typed.value = units();
    running = false;
    schedule();
  }

  // Arm the auto-advance wait: `onDue` runs once `ms` of unheld, non-typing
  // frame time has passed. Re-arming restarts the wait.
  function armAdvance(ms, onDue) {
    advance = { ms, onDue, waited: 0 };
    schedule();
  }

  function disarmAdvance() {
    advance = null;
    schedule();
  }

  function stop() {
    running = false;
    advance = null;
    schedule();
  }

  onBeforeUnmount(stop);

  return {
    typed,
    typing,
    start,
    complete,
    stop,
    armAdvance,
    disarmAdvance,
    get advanceArmed() {
      return advance !== null;
    },
  };
}
