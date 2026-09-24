// The shell command-field focus routing and the SceneBackdrop harness
// registration, extracted verbatim from AppClient.vue so the SFC stays a
// passive renderer.
import { onMounted, watch } from "vue";

export function useShellFocus(store, shellRef, sceneBackdropRef) {
  // The shell instance handle (webclient-collapsible-command-line design D2):
  // `/` and the store-driven freeform dialogue borrow request command-line
  // expansion and field focus through the exposed AppShell
  // `focusCommandField` method.
  watch(
    () => store.view.drawerRequest,
    (request) => {
      if (request > 0) {
        shellRef.value?.focusCommandField();
      }
    },
  );
  // A successful dock-borrowed send (freeform dialogue) restores action-dock
  // focus and collapses the command line through `releaseCommandField(true)`
  // (webclient-collapsible-command-line design D2/D3).
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
