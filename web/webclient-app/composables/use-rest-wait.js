// The rest/wait surface (C4): the bounded rest-duration form open/close state,
// the waiting-screen cards, and the skill-practice feedback. The
// `restFormOpen` mark is driven from three routes — the store's rest-form
// request, the dock's `explore.wait` activation, and the wait-frame teardown —
// all kept with the state they mutate. Extracted verbatim from AppClient.vue.
import { computed, ref, watch } from "vue";

export function useRestWait(store, { dispatchIntent }) {
  // C4: the rest-duration form opens when the activated dock item is the
  // `explore.wait` rest item (the legacy `openRestForm` behavior).
  const restFormOpen = ref(false);
  const restFormError = ref(null);
  // The wait/rest entry point (openRestForm) requests the bounded rest-duration
  // form open (the exploration rest form, `exploration-rest-form`).
  watch(
    () => store.view.restFormRequest,
    (request) => {
      if (request > 0) {
        restFormOpen.value = true;
        restFormError.value = null;
      }
    },
  );
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
  const waitOpen = computed(() => store.view.dockSource === "exploration.wait");
  watch(waitOpen, (open) => {
    if (!open) restFormOpen.value = false;
  });
  const skipDisabled = computed(() => !store.view.connected || store.view.phase !== "active"
    || store.view.mode !== "exploration" || store.view.mutationsLocked || !!store.view.dispatch?.inFlight);
  function activateWait(key) {
    store.focusItemByKey(key);
    store.focusConfirm("pointer");
  }

  function onRestFormSubmit(seconds) {
    restFormOpen.value = false;
    restFormError.value = null;
    // One dispatch through the single store entry (the bounded `explore.wait`
    // payload the server validates).
    dispatchIntent("explore.wait", { seconds });
  }

  function onRestFormClose() {
    restFormOpen.value = false;
    document.querySelector(".action-dock")?.focus();
  }

  function onRestFormError(message) {
    restFormError.value = message;
  }

  // The dock route into the form (the sole local UI exception to router
  // confirmation): confirming the `explore.wait` action opens the form before
  // any OOB action is dispatched.
  function openRestForm() {
    restFormOpen.value = true;
    restFormError.value = null;
  }

  return {
    activateWait,
    onPractice,
    onRestFormClose,
    onRestFormError,
    onRestFormSubmit,
    openRestForm,
    practiceOpen,
    practiceFeedback,
    restFormError,
    restFormOpen,
    skipDisabled,
    waitOpen,
  };
}
