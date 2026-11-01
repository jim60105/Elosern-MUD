// The travel stage's input owner (OpenSpec change wilderness-travel-walking-ui;
// interface design §5 "Inputs" and the change design's "Input ownership"):
// TravelMap's intents and the band's 停步 reach the store's walking queue
// here, and nowhere else. The store owns the aim, the hold timer, the pending
// step and the dwell; this composable only translates DOM input.
//
// - Keyboard intents come from the focused map only (TravelMap ignores
//   modified and composing keys and native repeat), so text entries, open
//   dialogs and drawers keep their own input.
// - Pointer: hovering a known neighbour aims it; clicking one steps once
//   (neighbour single-step precedence, gateway and withheld-destination rows
//   included). Hovering a disclosed cell further away previews its route
//   (the store debounces it); clicking one locks it. The party's own cell
//   and unknown cells do nothing beyond the hover outline; a second click on
//   the locked cell departs on its current plan (wilderness-travel-route-ui).
// - Destination cursor (wilderness-travel-planning-ui): Shift+arrows move a
//   visible cursor one cell inside the current window, clear the neighbour
//   aim and preview a disclosed far cell like a hover. Enter with an aim
//   still steps; otherwise Enter on the cursor locks a disclosed non-party
//   cell (a neighbour too) and leaves cursor mode, while an unknown or party
//   cell is only inspected. Enter with neither an aim nor a cursor departs
//   on the locked current plan, exactly as 出發 does. Esc clears, in order: a walk or the aim, the
//   cursor, then the lock and preview.
// - One document keydown listener in the CAPTURE phase stops an active walk
//   before any other handler runs. The held arrows' native repeat is the
//   walk's continuation, not a new key. The stopping event is recorded, so
//   the map's own intent for that same event neither aims nor steps; the
//   listener never cancels or stops the event, so existing hotkeys and the
//   keyboard bridge still see it. A key that stopped a walk can never also
//   depart: the stopping key stays suppressed for departure until it is
//   released (Enter clicks a focused 出發 on keydown, Space on keyup), and a
//   native repeat of the key that departed is the same press, not a stop.
// - A window blur, a hidden document and the full log stop the walk too.
// - When a walk ends, focus returns to the map unless another surface
//   (a drawer, an overlay, a card, the full log, a text entry) holds it.
// - Entering the travel layout focuses the map: the compass is not mounted
//   there, so no hidden control consumes the movement keys.
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
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
  // The keyboard destination cursor: a window cell, or null outside cursor mode.
  const cursor = ref(null);
  // The physical Enter/Space keys that stopped a walk and are still held:
  // only these can both stop and depart in one press (Enter clicks a focused
  // 出發 on keydown, Space on keyup), so only they are tracked, by `code`
  // (its `key` can change between keydown and keyup). A pointer press or
  // any other key forgets them, so a lost keyup never blocks departure.
  const ACTIVATION_KEYS = new Set(["Enter", " "]);
  const stopKeys = new Set();

  function onCapture(event) {
    if (!ACTIVATION_KEYS.has(event.key) && !MODIFIER_KEYS.has(event.key)) stopKeys.clear();
    if (!walking.value) return;
    if (MODIFIER_KEYS.has(event.key) || event.isComposing || event.keyCode === 229) return;
    if (event.repeat && (ARROW_KEYS.includes(event.key) || ACTIVATION_KEYS.has(event.key))) return;
    stopping.add(event);
    if (store.stopTravel("key") && ACTIVATION_KEYS.has(event.key)) stopKeys.add(event.code || event.key);
  }

  function onKeyUp(event) {
    const id = event.code || event.key;
    if (!stopKeys.has(id)) return;
    // Space activates a focused button on keyup, after this listener: the
    // key is released for departure only once that activation has passed.
    setTimeout(() => stopKeys.delete(id), 0);
  }

  function onPointerDown() {
    stopKeys.clear();
  }

  /** Depart on the locked current plan (出發, Enter, a second locked click). */
  function depart() {
    if (stopKeys.size > 0 || active.value) return false;
    // A hovered neighbour leaves a persistent aim; the explicit departure
    // supersedes it (Enter with an aim still steps instead).
    if (travel.value?.aim) store.aimTravel(null);
    return store.departTravel?.()?.departed === true;
  }

  function swallowed(event) {
    return !!event && stopping.has(event);
  }

  function onAim(direction, event) {
    if (swallowed(event)) return;
    leaveCursor();
    store.aimTravel(direction);
  }
  function onHold(direction, event) {
    if (!swallowed(event)) store.holdTravel(direction);
  }
  function onRelease() {
    store.releaseTravel();
  }
  function onStep(event) {
    if (swallowed(event)) return;
    // An ordinary aim keeps its single step.
    if (!travel.value?.aim && cursor.value) {
      if (store.lockTravelDestination(cursor.value)) cursor.value = null;
      return;
    }
    if (!travel.value?.aim && travel.value?.lockedDestination) {
      if (!event?.repeat) depart();
      return;
    }
    store.stepTravel();
  }
  function onCancel(event) {
    if (swallowed(event)) return;
    if (active.value || travel.value?.aim) {
      store.stopTravel("cancel");
      store.aimTravel(null);
      return;
    }
    if (cursor.value) {
      leaveCursor();
      return;
    }
    store.clearTravelTarget();
  }

  function leaveCursor() {
    if (!cursor.value) return;
    cursor.value = null;
    // The cursor's own preview goes with it; a lock stays.
    store.hoverTravelCell(null);
  }

  /** Move the destination cursor by one cell, inside the current window. */
  function onCursor(dx, dy, event) {
    if (swallowed(event) || active.value) return;
    const grid = travel.value?.map ?? null;
    if (!grid || !travel.value?.mapReady) return;
    const from = cursor.value ?? travel.value.lockedDestination ?? grid.party;
    if (!from) return;
    const clamp = (v, lo, size) => Math.min(lo + size - 1, Math.max(lo, v));
    cursor.value = Object.freeze({ x: clamp(from.x + dx, grid.origin.x, grid.width), y: clamp(from.y + dy, grid.origin.y, grid.height) });
    if (travel.value.aim) store.aimTravel(null);
    // The store previews only a disclosed cell beyond the neighbours.
    store.hoverTravelCell(cursor.value);
  }

  // What the cursor stands on, for the map outline and the intent line.
  const cursorView = computed(() => {
    const c = cursor.value;
    const grid = travel.value?.map ?? null;
    if (!c || !grid) return null;
    const cell = travelCellAt(grid, c.x, c.y);
    const party = !!grid.party && grid.party.x === c.x && grid.party.y === c.y;
    const known = !!cell?.known;
    const label = known ? cell.node?.landmark?.name || cell.display?.terrain_label || null : null;
    return Object.freeze({ x: c.x, y: c.y, known, party, label, lockable: known && !party });
  });

  function neighbour(cell) {
    const grid = travel.value?.map ?? null;
    if (!grid || !cell) return null;
    const direction = directionForCell(grid.party, cell);
    const known = !!travelCellAt(grid, cell.x, cell.y)?.known;
    return direction && known ? direction : null;
  }

  function onHover(cell) {
    if (active.value) return;
    if (cell) cursor.value = null;
    const direction = neighbour(cell);
    if (direction) {
      store.hoverTravelCell(null);
      if (direction !== travel.value?.aim) store.aimTravel(direction);
      return;
    }
    // The store previews a disclosed far cell; anything else clears.
    store.hoverTravelCell(cell);
  }

  function sameCell(a, b) {
    return !!a && !!b && a.x === b.x && a.y === b.y;
  }

  function onPick(cell) {
    if (active.value) {
      store.stopTravel("pointer");
      return;
    }
    cursor.value = null;
    const direction = neighbour(cell);
    if (direction) {
      store.stepTravel(direction);
      return;
    }
    if (!cell) return;
    // A second click on the locked cell departs.
    if (sameCell(cell, travel.value?.lockedDestination)) {
      depart();
      return;
    }
    store.lockTravelDestination(cell);
  }

  // The cursor leaves with the layout, a walk, or a window that no longer holds it.
  watch(
    () => [layout.value, active.value, travel.value?.map ?? null],
    ([shown, moving, grid]) => {
      const c = cursor.value;
      if (!c) return;
      if (!shown || moving || !grid || !travelCellAt(grid, c.x, c.y)) cursor.value = null;
    },
  );

  function onStop() {
    store.stopTravel("stop");
  }

  function onDepart() {
    depart();
  }

  function onWindowBlur() {
    // A key released outside the window never reports its keyup.
    stopKeys.clear();
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
    const inControls = !!el?.closest?.('[data-testid="leg-panel"]');
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
    document.addEventListener("keyup", onKeyUp, true);
    document.addEventListener("pointerdown", onPointerDown, true);
    window.addEventListener("blur", onWindowBlur);
    document.addEventListener("visibilitychange", onVisibility);
  });
  onBeforeUnmount(() => {
    document.removeEventListener("keydown", onCapture, true);
    document.removeEventListener("keyup", onKeyUp, true);
    document.removeEventListener("pointerdown", onPointerDown, true);
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
    onTravelDepart: onDepart,
    onTravelCursor: onCursor,
    travelCursor: cursorView,
  };
}
