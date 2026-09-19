// The concept-apply and name-roll dispatch seams plus the settlement
// watchers (extracted verbatim from CreationOverlay.vue so the SFC stays a
// passive renderer). Registers the fifth and sixth watchers (the result
// settlement and the global-gate safety net), after the form/proposal groups.
import { computed, ref, watch } from "vue";

export function useCreationDispatch(props, form, emit) {
  const { conceptPending, conceptText, name, race, subrace, sex } = form;

  // -- Concept state -----------------------------------------------------------
  function applyConcept() {
    // Admission-gated pending (retool-concept-fill-navigation D1a): with the
    // return-bearing dispatch prop, pending flips ONLY when the store admits
    // the mutation — a gate-rejected apply never creates a waiting state.
    // Without the prop (standalone mounts/tests) the emit path sets pending
    // optimistically; the gate-release safety net still settles it.
    if (typeof props.dispatch === "function") {
      if (props.dispatch({ action_id: "creation.concept", payload: { concept: conceptText.value } }) === null) {
        return;
      }
      conceptPending.value = true;
    } else {
      conceptPending.value = true;
      emit("action", { action_id: "creation.concept", payload: { concept: conceptText.value } });
    }
  }

  // -- Name roll ---------------------------------------------------------------
  // The dice button shares the store's single-mutation gate: like the concept
  // apply, the loading state flips ONLY after admission (a gate-held click
  // never shows a spinner and never double-dispatches, retool-concept-fill-
  // navigation D1a semantics reused).
  const rollPending = ref(false);
  const rollRequestId = ref(null);

  function rollName() {
    const payload = {
      race: race.value ?? null,
      subrace: subrace.value ?? null,
      // The DISPLAYED selection is always sent: the select model is a concrete
      // key (D11), so a fresh roll carries the mirrored default.
      sex: sex.value ?? null,
    };
    if (typeof props.dispatch === "function") {
      const requestId = props.dispatch({ action_id: "creation.roll_name", payload });
      if (requestId === null) return;
      rollPending.value = true;
      rollRequestId.value = requestId;
    } else {
      rollPending.value = true;
      rollRequestId.value = null;
      emit("action", { action_id: "creation.roll_name", payload });
    }
  }

  // Shared dispatch gate: any in-flight mutation (this roll, a save, a concept
  // apply) disables the dice button through the store's dispatch slice.
  const rollDisabled = computed(
    () =>
      rollPending.value ||
      Boolean(props.dispatchState && props.dispatchState.inFlight !== null),
  );

  // Failure settlement (D1): this request's non-success result settles the
  // loading window. The guard comes first — a standalone mount carrying a
  // foreign result and no dispatch state must never deref.
  const NON_SUCCESS_OUTCOMES = ["rejected", "stale", "error"];
  watch(
    () => props.result,
    (r) => {
      if (!props.dispatchState || !r) return;
      // Name-roll settlement (namegen-creation-ui D6): the backfill happens
      // ONLY for the request this overlay submitted, with a success outcome
      // and a usable data slot; anything else just settles the in-flight
      // state and never touches the name the player may have typed since.
      if (rollPending.value && r.requestId === rollRequestId.value) {
        rollPending.value = false;
        if (
          r.outcome === "success" &&
          r.data &&
          typeof r.data.display_name === "string" &&
          r.data.display_name !== ""
        ) {
          name.value = r.data.display_name;
        }
      }
      if (!conceptPending.value) return;
      if (
        NON_SUCCESS_OUTCOMES.indexOf(r.outcome) !== -1 &&
        r.requestId === props.dispatchState.submittedRequestId
      ) {
        conceptPending.value = false;
      }
    },
  );

  // Global-gate safety net (D1c): a synchronous sender failure or a lost
  // mutation releases the store gate WITHOUT any settlement this overlay can
  // observe; the release itself settles the loading window (never a
  // premature clear — during a healthy wait the gate stays held until the
  // result commits and its presentation revision is reached).
  watch(
    () => props.dispatchState,
    (d) => {
      if (!d || d.inFlight === null) {
        conceptPending.value = false;
        rollPending.value = false;
      }
    },
  );

  return { applyConcept, rollPending, rollName, rollDisabled };
}
