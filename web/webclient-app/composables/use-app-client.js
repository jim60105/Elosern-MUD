// The AppClient wiring facade: composes the cohesive behavior groups (each
// watch stays with the state it mutates) into the single flat binding set the
// AppClient template consumes, so the SFC itself stays a thin, passive
// renderer. Group call order preserves the original watcher registration
// order (shell focus -> resync episode -> rest/wait teardown -> mode -> dock).
import { ref } from "vue";
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
import { useExitCompass } from "./use-exit-compass.js";
import { usePersonFocus } from "./use-person-focus.js";
import { useRoomActions } from "./use-room-actions.js";
import { useModeChange } from "./use-mode-change.js";
import { useNpcPersonaEditor } from "./use-npc-persona-editor.js";
import { useSkillUse } from "./use-skill-use.js";

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
  // The exit compass's template ref (bound by AppClient's `ref="compassRef"`).
  const compassRef = ref(null);
  const compass = useExitCompass(store, { panel, compassRef });
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
    ...useDock(store, { panel, dispatchIntent }),
    ...useIntentHandlers(store, dispatchIntent),
    // The NPC author editor (npc-persona-editor-window): its own correlated
    // read/update state machine over the single store dispatch entry.
    ...useNpcPersonaEditor(store, { shellRef }),
    // The SkillBook 施放 hand-over to the dock (skillbook-authoritative-casting).
    ...useSkillUse(store),
    // The exploration root pane's exit compass and shared readout
    // (exploration-exit-compass).
    compassRef,
    ...compass,
    // The presence rail and the person focus (exploration-presence-rail).
    ...usePersonFocus(store, {
      panel,
      compassRef,
      onRailHover: compass.onRailHover,
      showReadoutFlash: compass.showReadoutFlash,
    }),
    // The place card's room actions, the 建議 pill, the wait and suggestions
    // cards, and the exploration Tab chain (exploration-room-actions).
    ...useRoomActions(store, {
      panelAvailable,
      dispatchIntent,
      skipDisabled: restWait.skipDisabled,
      compassRef,
      onPlaceHover: compass.onPlaceHover,
      onPillHover: compass.onPillHover,
    }),
  };
}
