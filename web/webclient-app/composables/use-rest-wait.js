// The rest/wait support (C4): the skip lock the wait card and the practice
// view share, and the skill-practice feedback. The wait card itself, its
// dream question, and its rest form live in use-room-actions.js
// (exploration-room-actions); no part of this group follows the router.
import { computed, ref, watch } from "vue";

export function useRestWait(store, { dispatchIntent }) {
  const practiceRequest = ref(null);
  const practiceOpen = ref(false);
  watch([() => store.view.epoch, () => store.view.generation], () => {
    practiceRequest.value = null;
  });
  const practiceFeedback = computed(() => {
    const result = store.view.lastActionResult;
    return result?.requestId === practiceRequest.value ? result?.message : "";
  });
  function onPractice(payload) {
    practiceRequest.value = dispatchIntent("explore.practice", payload);
  }
  // A time skip cannot start while the session is not live in exploration or
  // while an action is in flight or awaiting its declared revision.
  const skipDisabled = computed(() => !store.view.connected || store.view.phase !== "active"
    || store.view.mode !== "exploration" || store.view.mutationsLocked || !!store.view.dispatch?.inFlight
    || !!store.view.submitLocked);

  return {
    onPractice,
    practiceOpen,
    practiceFeedback,
    skipDisabled,
  };
}
