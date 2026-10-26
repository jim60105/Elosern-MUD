// C4 (webclient-vue-10-wire-views-browser): the renderer's automatic complete
// repair, extracted from AppClient so the SFC stays a passive renderer.
//
// webclient-sync-recovery: the reducer is the single authority on a failure
// episode. Every failure source (exact-base mismatch, an invalid or
// incomplete publication, an assembly failure/expiry, a recoverable server
// protocol error, or a matching action result claiming an unadopted revision)
// records one `recovery: needed` state and locks graphical mutations there.
// This composable reacts to that one signal and asks the bridge's gate for the
// single `ui_sync` of the episode; the bridge/store gate coalesces every
// request source, so no second failure can start a second sync. The episode
// ends only through the reducer (a valid complete snapshot, the claimed
// revision being adopted, an explicit player synchronize or a new transport
// generation), so there is nothing to re-arm here.
import { computed, watch } from "vue";

export function useResync(store) {
  function resyncActions() {
    return (window.Elosern && window.Elosern.actions) || null;
  }

  // The whole-presentation failure state: true exactly while the reducer holds
  // an unrequested repair need.
  const presentationFailure = computed(
    () => store.view.recovery.status === "needed",
  );

  watch(presentationFailure, (failing, prevFailing) => {
    if (!failing || prevFailing) {
      return;
    }
    const actions = resyncActions();
    if (!actions) {
      return;
    }
    // One automatic complete repair for this failure episode. A disconnected
    // transport or a failed episode declines inside the gate.
    actions.requestResync("presentation");
  });

  return { presentationFailure };
}
