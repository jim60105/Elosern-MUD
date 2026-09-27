// The AppClient wiring facade: composes the cohesive behavior groups (each
// watch stays with the state it mutates) into the single flat binding set the
// AppClient template consumes, so the SFC itself stays a thin, passive
// renderer. Group call order preserves the original watcher registration
// order (shell focus -> resync episode -> rest/wait teardown -> mode -> dock).
import { useDispatchIntent, useIntentHandlers } from "./intents.js";
import { usePanelView } from "./panel-view.js";
import { useResync } from "./use-resync.js";
import { useShellFocus, useBackdropBridge } from "./use-shell-focus.js";
import { useScene } from "./use-scene.js";
import { useDialogueChoices } from "./use-dialogue-choices.js";
import { useRestWait } from "./use-rest-wait.js";
import { useOverlays } from "./use-overlays.js";
import { useDrawers } from "./use-drawers.js";
import { useDock } from "./use-dock.js";
import { useModeChange } from "./use-mode-change.js";

export function useAppClient(store, shellRef, sceneBackdropRef) {
  // The single dispatch seam (webclient-action-feedback): every surface's
  // emitted intent routes through the one store entry.
  const { dispatchIntent } = useDispatchIntent(store);
  const { panel, panelAvailable } = usePanelView(store);
  // The live mode-change signal (webclient-mode-transitions D2): registered
  // first, so every later pre-flush watcher already sees this change's value.
  const modeChangeSignal = useModeChange(store);
  useResync(store);
  useShellFocus(store, shellRef, sceneBackdropRef);
  useBackdropBridge(sceneBackdropRef);
  const restWait = useRestWait(store, { dispatchIntent });
  const scene = useScene(store, { panel, panelAvailable, dispatchIntent });
  return {
    dispatchIntent,
    panel,
    panelAvailable,
    ...modeChangeSignal,
    ...scene,
    ...useDialogueChoices(store, shellRef, scene.dialogueVM),
    ...restWait,
    ...useOverlays(store, { panelAvailable }),
    ...useDrawers(store, { panel, panelAvailable }),
    ...useDock(store, {
      panel,
      dispatchIntent,
      openRestForm: restWait.openRestForm,
      shellRef,
    }),
    ...useIntentHandlers(store, dispatchIntent),
  };
}
