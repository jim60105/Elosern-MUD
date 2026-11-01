// The camp card and campfire beat wiring (OpenSpec change wilderness-camping;
// design §5). The store (`stores/elosern/camp.js`) owns the state machine and
// every request; this composable only projects `view.camp` into the two
// cards' open flags and handlers, and returns focus to the control that
// opened the card when it closes. It derives no rule, wake or reserve.
import { computed, nextTick, watch } from "vue";

const OPENERS = Object.freeze({
  leg: '#action-dock [data-testid="leg-camp"]',
  handoff: '[data-anchor="choices"] [data-testid="sleep-handoff-card"] [data-testid="sleep-handoff-camp"]',
});

const CLOSED = Object.freeze({ phase: "closed", open: false, opener: null, openCount: 0 });

function focusable(el) {
  return !!el && el.isConnected && !el.disabled && !el.closest?.('[inert], [hidden], [aria-hidden="true"]');
}

export function useCamp(store, { compassRef } = {}) {
  const camp = computed(() => store.view?.camp ?? CLOSED);
  const campCardOpen = computed(() => camp.value.open === true && camp.value.phase !== "beat");
  const campBeatOpen = computed(() => camp.value.phase === "beat" && !!camp.value.result);
  const campOpen = computed(() => campCardOpen.value || campBeatOpen.value);

  function openCamp(opener = "leg") {
    return store.openTravelCamp?.(opener) === true;
  }
  function closeCamp() {
    return store.closeCamp?.() === true;
  }
  function selectMode(mode) {
    return store.selectCampMode?.(mode) === true;
  }
  function toggleDream(value) {
    return store.toggleCampDream?.(value) === true;
  }
  function confirmCamp() {
    return store.confirmCamp?.() === true;
  }
  // The beat finishes its own animation on an early key or click; finishing
  // is presentation-only and never reaches the store.
  function finishBeat() {
    return false;
  }
  function continueTravel() {
    return store.continueCampTravel?.() === true;
  }

  // Focus returns to the opener (the leg's 紮營, or the handoff row the
  // shortcut lives on); when it is gone, the compass, then the dock.
  let lastOpener = null;
  watch(
    () => [campOpen.value, camp.value.opener],
    async ([open, opener]) => {
      if (open) {
        lastOpener = opener;
        return;
      }
      const from = lastOpener;
      lastOpener = null;
      if (!from || typeof document === "undefined") return;
      await nextTick();
      const active = document.activeElement;
      if (active && active !== document.body && active.isConnected && !active.closest?.('[data-anchor="choices"]')) return;
      const target = document.querySelector(OPENERS[from] ?? "");
      if (focusable(target)) {
        target.focus({ preventScroll: true });
        return;
      }
      if (from === "handoff") {
        // The handoff card autofocuses its own rows when it remounts.
        const card = document.querySelector('[data-anchor="choices"] [data-testid="sleep-handoff-card"]');
        if (card) return;
      }
      if (compassRef?.value?.focus) {
        compassRef.value.focus();
        if (document.activeElement && document.activeElement !== document.body) return;
      }
      document.getElementById("action-dock")?.focus({ preventScroll: true });
    },
    { flush: "post" },
  );

  return {
    camp,
    campCardOpen,
    campBeatOpen,
    campOpen,
    openCamp,
    closeCamp,
    selectMode,
    toggleDream,
    confirmCamp,
    finishBeat,
    continueTravel,
  };
}
