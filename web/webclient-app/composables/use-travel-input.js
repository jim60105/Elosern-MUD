// The travel stage's input owner (OpenSpec change wilderness-travel-walking-ui;
// interface design §5 "Inputs" and the change design's "Input ownership"):
// TravelMap's intents and the band's 停步 reach the store's walking queue
// here, and nowhere else. The store owns the aim, the hold timer, the pending
// step and the dwell; this composable only translates DOM input.
//
// - Keyboard intents come from the focused map only (TravelMap ignores
//   modified and composing keys and native repeat), so text entries, open
//   dialogs and drawers keep their own input.
// - Pointer: hovering a known neighbour aims it; clicking one steps once.
//   The party's own cell, unknown cells and cells further away do nothing
//   here (the route slices own those).
// - One document keydown listener in the CAPTURE phase stops an active walk
//   before any other handler runs. The held arrows' native repeat is the
//   walk's continuation, not a new key. The stopping event is recorded, so
//   the map's own intent for that same event neither aims nor steps; the
//   listener never cancels or stops the event, so existing hotkeys and the
//   keyboard bridge still see it.
// - A window blur, a hidden document and the full log stop the walk too.
// - When a walk ends, focus returns to the map unless another surface
//   (a drawer, an overlay, a card, the full log, a text entry) holds it.
// - Entering the travel layout focuses the map: the compass is not mounted
//   there, so no hidden control consumes the movement keys.
import { computed, nextTick, onBeforeUnmount, onMounted, watch } from "vue";
import { ARROW_KEYS, directionForCell } from "../components/travel/travel-walk-model.js";
import { travelCellAt } from "../lib/travel-grid.js";
import { isTextEntry } from "./use-window-hotkeys.js";

const MODIFIER_KEYS = new Set(["Shift", "Control", "Alt", "Meta", "AltGraph", "CapsLock", "Fn", "OS"]);

export function useTravelInput(store, { mapRef, fullLogOpen = () => false }) {
  const travel = computed(() => store.view.travel ?? null);
  const layout = computed(() => !!travel.value?.layout);
  const walking = computed(() => !!travel.value?.walking);
  const active = computed(() => walking.value || !!travel.value?.holding);
  // Events that already stopped a walk in the capture phase.
  const stopping = new WeakSet();

  function onCapture(event) {
    if (!walking.value) return;
    if (MODIFIER_KEYS.has(event.key) || event.isComposing || event.keyCode === 229) return;
    if (event.repeat && ARROW_KEYS.includes(event.key)) return;
    stopping.add(event);
    store.stopTravel("key");
  }

  function swallowed(event) {
    return !!event && stopping.has(event);
  }

  function onAim(direction, event) {
    if (!swallowed(event)) store.aimTravel(direction);
  }
  function onHold(direction, event) {
    if (!swallowed(event)) store.holdTravel(direction);
  }
  function onRelease() {
    store.releaseTravel();
  }
  function onStep(event) {
    if (!swallowed(event)) store.stepTravel();
  }
  function onCancel(event) {
    if (swallowed(event)) return;
    store.stopTravel("cancel");
    store.aimTravel(null);
  }

  function neighbour(cell) {
    const grid = travel.value?.map ?? null;
    if (!grid || !cell) return null;
    const direction = directionForCell(grid.party, cell);
    const known = !!travelCellAt(grid, cell.x, cell.y)?.known;
    return direction && known ? direction : null;
  }

  function onHover(cell) {
    if (active.value) return;
    const direction = neighbour(cell);
    if (direction && direction !== travel.value?.aim) store.aimTravel(direction);
  }

  function onPick(cell) {
    if (active.value) {
      store.stopTravel("pointer");
      return;
    }
    const direction = neighbour(cell);
    if (direction) store.stepTravel(direction);
  }

  function onStop() {
    store.stopTravel("stop");
  }

  function onWindowBlur() {
    if (active.value) store.stopTravel("blur");
  }
  function onVisibility() {
    if (document.visibilityState === "hidden" && active.value) store.stopTravel("blur");
  }

  watch(fullLogOpen, (open) => {
    if (open && active.value) store.stopTravel("surface");
  });

  // Another surface holds focus: a stop leaves it there.
  function surfaceOwnsFocus() {
    const v = store.view;
    if (v.hudDrawer || v.hudOverlay || v.presenceCard || v.roomCard || v.partyExitConfirm || fullLogOpen()) return true;
    return isTextEntry(document.activeElement);
  }

  function lost(el) {
    return !el || el === document.body || el === document.documentElement || !el.isConnected;
  }

  function focusMap() {
    mapRef.value?.focus?.();
  }

  watch(active, async (now, was) => {
    if (now || !was) return;
    await nextTick();
    if (!layout.value || store.view.mode !== "exploration" || surfaceOwnsFocus()) return;
    const el = document.activeElement;
    const mapEl = mapRef.value?.el?.() ?? null;
    const inControls = !!el?.closest?.('[data-testid="travel-walk-controls"]');
    if (lost(el) || el === mapEl || inControls) focusMap();
  });

  // Entering the layout: the map takes focus from nowhere, the dock (the
  // compass-unmount rescue's target) or the band's own controls.
  watch(
    layout,
    async (shown) => {
      if (!shown) return;
      await nextTick();
      await nextTick();
      if (!layout.value || surfaceOwnsFocus()) return;
      const el = document.activeElement;
      const dock = document.getElementById("action-dock");
      if (lost(el) || el === dock || !!el?.closest?.('[data-testid="exploration-root"]')) focusMap();
    },
    { immediate: true, flush: "post" },
  );

  onMounted(() => {
    document.addEventListener("keydown", onCapture, true);
    window.addEventListener("blur", onWindowBlur);
    document.addEventListener("visibilitychange", onVisibility);
  });
  onBeforeUnmount(() => {
    document.removeEventListener("keydown", onCapture, true);
    window.removeEventListener("blur", onWindowBlur);
    document.removeEventListener("visibilitychange", onVisibility);
  });

  return {
    onTravelAim: onAim,
    onTravelHold: onHold,
    onTravelRelease: onRelease,
    onTravelStep: onStep,
    onTravelCancel: onCancel,
    onTravelHover: onHover,
    onTravelPick: onPick,
    onTravelStop: onStop,
  };
}
