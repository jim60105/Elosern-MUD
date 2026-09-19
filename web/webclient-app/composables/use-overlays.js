// The overlay and full-log surfaces (H1/H5): the opener-captured full-screen
// overlay open/close routes, the bounded full-log overlay, and the stage
// open-surface registry. Extracted verbatim from AppClient.vue so the SFC
// stays a passive renderer.
import { computed, nextTick, ref, watch } from "vue";

export function useOverlays(store, { panelAvailable }) {
  // H1 contextual HUD (design D4/D9): the bounded caption card's `完整日誌`
  // control opens the full-log overlay; the overlay presents the complete
  // retained narrative through the same markup renderer (one markup path).
  const fullLogOpen = ref(false);
  const fullLogRef = ref(null);

  function openFullLog() {
    fullLogOpen.value = true;
    void nextTick().then(() => fullLogRef.value?.focusSelf());
  }

  function closeFullLog(restoreFocus) {
    fullLogOpen.value = false;
    if (restoreFocus) {
      // Focus is restored to the caption card's control (the opener) by the
      // overlay itself (it remembers the opener element internally); the
      // shell's mode watcher routes focus to the dock when a mode change hides
      // a focused surface.
    }
  }

  // The open-surface registry (design D9): a single reactive set of open
  // surfaces drives the stage recession; the mark clears only when no
  // surface remains open. The registry carries the full-log overlay and the
  // mounted creation overlay; H4's drawers will register into the same set.
  const openSurfaces = computed(() => {
    const surfaces = [];
    if (fullLogOpen.value) {
      surfaces.push("full-log");
    }
    if (panelAvailable("creation")) {
      surfaces.push("creation");
    }
    // H4 (task 3.4): the open reference drawer registers into the same
    // open-surface set so the stage recession (H1) applies without a second
    // mechanism.
    if (store.view.hudDrawer) {
      surfaces.push(store.view.hudDrawer);
    }
    // H5 (task 5.4): the open full-screen overlay registers into the same
    // open-surface set; the stage's recession mark clears only when no
    // surface remains open.
    if (store.view.hudOverlay) {
      surfaces.push(store.view.hudOverlay);
    }
    return surfaces;
  });

  // A mode transition into creation closes the full-log overlay (a
  // non-creation surface must not persist into creation) — task 5.8. The
  // shell's mode watcher handles the focus rescue to the dock.
  watch(
    () => store.view.mode,
    (mode) => {
      if (mode === "creation" && fullLogOpen.value) {
        fullLogOpen.value = false;
      }
    },
  );

  // H5 (webclient-hud-05-overlays-and-command-line, tasks 5.2/6.4): the
  // overlay opener is captured at open time (the focused element before the
  // overlay renders). Closing the host restores focus to the trigger that
  // opened it; when a second overlay replaces the first, the host
  // re-initializes its focus trap with the new opener (design D7).
  function openOverlayByName(name) {
    const opener = document.activeElement;
    store.openOverlay(name, opener);
  }

  // The command line's 設定/說明 utility controls (design D10) open the
  // settings / help overlays through the same opener-captured path.
  function onOpenOverlay(name) {
    openOverlayByName(name);
  }

  // The minimap island's 展開全地圖 control (task 6.2) opens the map surface.
  function onMapExpand() {
    openOverlayByName("map");
  }

  // The host's close control and Escape both route here (task 5.2): the host
  // restores focus to the opener before emitting.
  function onOverlayClose() {
    store.closeOverlay();
  }

  return {
    closeFullLog,
    fullLogOpen,
    fullLogRef,
    onMapExpand,
    onOpenOverlay,
    onOverlayClose,
    openFullLog,
    openOverlayByName,
    openSurfaces,
  };
}
