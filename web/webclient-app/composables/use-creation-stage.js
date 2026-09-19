// The wizard mode/preset actions, the store-driven dock-stage mirror and the
// frame/confirm actions (extracted verbatim from CreationOverlay.vue so the
// SFC stays a passive renderer). Registers the seventh (last) watcher — the
// stage mirror — after the form/proposal/dispatch groups.
import { watch } from "vue";

export function useCreationStage(props, form, emit) {
  const { mode, conceptPending, selectedPresetKey, latchedStage } = form;

  // -- Preset state -----------------------------------------------------------
  function selectPreset(card) {
    selectedPresetKey.value = card.key;
    emit("action", { action_id: "creation.preset", payload: { preset_key: card.key } });
  }

  // -- Frame actions -----------------------------------------------------------
  // Activation and the destructive reset always traverse the confirmation
  // screen (the legacy creation dock contract): the store opens the confirm
  // stage after a successful save or on a reset request, and only the confirm
  // screen's 確認 button dispatches `creation.activate` / `creation.reset`.
  function requestReset() {
    emit("request-reset");
  }

  // The store-driven creation dock stage mirrors the wizard's mode so keyboard
  // and pointer share one flow: root/presets -> preset, custom -> custom,
  // concept -> concept, confirm -> the confirmation screen overlays the body.
  // Only a stage VALUE change re-syncs (a pointer tab click must not be
  // overridden by an unchanged root stage re-publish).
  let lastStage = null;
  watch(
    () => props.stage,
    (s) => {
      const value = s ? s.stage : null;
      if (value === null || value === lastStage) {
        return;
      }
      // The in-flight pin and the completion-publish pin (D2/D3): while a
      // concept apply is pending, the store's stage signal never moves the
      // presented tab (a republish — including the dispatch's own re-emitted
      // root — must not kick the player off the concept tab); and the stage
      // object of the publish whose completion navigation this overlay already
      // performed is recognized as stale, so it cannot overwrite the landing
      // on the custom tab. The pin is exactly one publish: any later publish
      // (new object identity) mirrors normally, keeping keyboard navigation
      // intact.
      if (conceptPending.value) {
        lastStage = value;
        return;
      }
      if (s === latchedStage.value) {
        lastStage = value;
        return;
      }
      lastStage = value;
      if (value === "custom") {
        mode.value = "custom";
      } else if (value === "concept") {
        mode.value = "concept";
      } else if (value === "root" || value === "presets") {
        mode.value = "preset";
      }
    },
  );

  function confirmCurrent() {
    const actionId = props.stage && props.stage.confirmAction;
    if (actionId) {
      emit("action", { action_id: actionId, payload: {} });
    }
  }

  function cancelConfirm() {
    emit("cancel-confirm");
  }

  return { selectPreset, requestReset, confirmCurrent, cancelConfirm };
}
