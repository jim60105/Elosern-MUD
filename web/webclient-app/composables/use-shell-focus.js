// The shell command-field focus routing and the SceneBackdrop harness
// registration, extracted verbatim from AppClient.vue so the SFC stays a
// passive renderer.
import { onMounted, watch } from "vue";

export function useShellFocus(store, shellRef, sceneBackdropRef) {
  // The shell instance handle (H5, design D1/D6): the store-driven freeform
  // dialogue entry point (a freeform affordance) requests command-line field
  // focus through the exposed AppShell method — the field is permanently
  // present, so there is no open/closed state to toggle.
  watch(
    () => store.view.drawerRequest,
    (request) => {
      if (request > 0) {
        shellRef.value?.focusCommandField();
      }
    },
  );
  // A successful dock-borrowed send (freeform dialogue) restores action-dock
  // focus (webclient-desktop-shell: the borrowed send returns focus to the
  // dock). The field is never closed, so the completion signal is the focus
  // return, not a surface close (H5, design D6).
  watch(
    () => store.view.drawerCloseRequest,
    (request) => {
      if (request > 0) {
        shellRef.value?.releaseCommandField(true);
      }
    },
  );
}

// Register the SceneBackdrop instance (its exposed interface) on the window
// bridge so the managed-browser pending-scene journey can seed the
// client-local prior-image memory (webclient-contextual-hud: a pending scene
// keeps its prior image dimmed and labelled, never presented as current).
export function useBackdropBridge(sceneBackdropRef) {
  onMounted(() => {
    const bridge = window.__elosernBridge;
    if (bridge) {
      bridge.backdrop = sceneBackdropRef.value;
    }
  });
}
