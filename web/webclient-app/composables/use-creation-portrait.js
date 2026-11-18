// The creation portrait request owner (creation-draft-portrait; design §7.2).
//
// Holds only local UI state: whether the generation drawer is open, the one
// admitted request it is waiting for, the drawer's rejection flag and the
// focus target to return to. The committed panel's `portrait` union is the
// sole source of pending/ready/failed/unavailable; nothing here fabricates a
// portrait state.
//
// - Opening the drawer sends nothing.
// - Submit reads the CURRENT race/subrace/sex/apparent-age refs at that
//   instant plus the drawer's own prompt, and calls the return-bearing
//   dispatch prop exactly once with `creation.portrait.generate`. A gate
//   rejection (null) keeps the drawer open and editable with its rejection
//   feedback. No concept text, display name, actual age or stat travels.
// - An admitted request settles only on ITS correlated result: a non-success
//   keeps the drawer and its prompt; a success closes the drawer once the
//   store's gate releases (its declared presentation revision committed),
//   then returns focus to the slot. A gate release without a correlated
//   result (a synchronous send failure, a lost mutation) only clears the
//   local submitting state. Nothing is ever resent.
// - A new presentation context (reconnect, epoch or actor change), an
//   unavailable creation panel, leaving the custom mode or a confirmation
//   screen closes the drawer and forgets only its pending UI.
// - Status refresh is an intent: the host forwards `request-sync` to the
//   store's existing manual synchronization; no generation, no probe.
import { computed, nextTick, ref, watch } from "vue";

export const PORTRAIT_ACTION = "creation.portrait.generate";

// The free-text-only view model the shared drawer receives in creation
// context: no field selection, one free-text prompt, one card, no subject
// groups and no equipment (a pending character has none).
export const CREATION_DRAWER_MODEL = Object.freeze({
  available: true,
  capabilities: Object.freeze({ supports_field_selection: false, supports_free_text: true, max_cards: 1 }),
  groups: Object.freeze([]),
  selected: null,
  equipment_summary: null,
});

const NON_SUCCESS_OUTCOMES = ["rejected", "stale", "error"];

export function useCreationPortrait(props, form, emit) {
  const { race, subrace, sex, apparentAge, name, mode } = form;

  const drawerOpen = ref(false);
  const requestId = ref(null);
  const submitting = ref(false);
  const succeeded = ref(false);
  const rejected = ref(false);
  // The slot component instance (CreationOverlay binds the ref); its
  // `focusHome()` is the fallback focus target.
  const portraitSlot = ref(null);
  let opener = null;

  const portrait = computed(() => {
    const value = props.creation?.portrait;
    return value && typeof value.status === "string" ? value : { status: "empty" };
  });
  const portraitUnavailableReason = computed(() => (
    portrait.value.status === "unavailable" ? portrait.value.reason ?? "" : ""
  ));
  const gateHeld = computed(() => Boolean(props.dispatchState && props.dispatchState.inFlight));
  const portraitSlotDisabled = computed(() => submitting.value || gateHeld.value);
  const portraitDrawerDisabled = computed(() => submitting.value || gateHeld.value);
  const portraitPreview = computed(() => {
    if (portrait.value.status !== "ready" || !portrait.value.artwork) return null;
    const label = (name.value ?? "").trim();
    return {
      artwork: portrait.value.artwork,
      image_id: portrait.value.artwork.generation_subject ?? null,
      label: label ? `${label}的肖像` : "角色肖像",
    };
  });

  function forgetRequest() {
    requestId.value = null;
    submitting.value = false;
    succeeded.value = false;
  }

  function openPortraitDrawer() {
    opener = typeof document !== "undefined" ? document.activeElement : null;
    rejected.value = false;
    drawerOpen.value = true;
  }

  // Focus goes back after the drawer has unmounted: the opener when it can
  // still take focus, else the slot's own fallback.
  async function returnFocus() {
    await nextTick();
    await nextTick();
    const target = opener;
    opener = null;
    if (target && target.isConnected && !target.disabled && typeof target.focus === "function") {
      target.focus();
      if (document.activeElement === target) return;
    }
    portraitSlot.value?.focusHome?.();
  }

  // The drawer's own close (Escape, ✕, scrim, 取消): HudDrawer's trap has
  // already restored focus to its opener. A request still waiting keeps no
  // armed success: its later gate release cannot close anything.
  function closePortraitDrawer() {
    drawerOpen.value = false;
    rejected.value = false;
    forgetRequest();
  }

  function closeAfterSuccess() {
    drawerOpen.value = false;
    rejected.value = false;
    forgetRequest();
    returnFocus();
  }

  // Settle the admitted request from the current state (not from watcher
  // edges), so a result or gate release committed during the dispatch call
  // itself is seen as well.
  function reconcile() {
    if (!submitting.value) return;
    const r = props.result;
    if (!succeeded.value && r && r.requestId === requestId.value) {
      if (r.outcome === "success") {
        succeeded.value = true;
      } else if (NON_SUCCESS_OUTCOMES.indexOf(r.outcome) !== -1) {
        rejected.value = true;
        forgetRequest();
        return;
      }
    }
    const inFlight = props.dispatchState ? props.dispatchState.inFlight : null;
    const holding = Boolean(inFlight && inFlight.requestId === requestId.value);
    if (holding) return;
    if (succeeded.value) {
      closeAfterSuccess();
    } else if (!props.dispatchState || !inFlight || inFlight.requestId !== requestId.value) {
      // The gate released (or moved on) without this request's result: a
      // synchronous send failure or a lost mutation. Clear, never resend.
      if (props.dispatchState) forgetRequest();
    }
  }

  function submitPortrait(event) {
    if (submitting.value) return;
    // No client-side availability check: the drawer already disables submit
    // from the committed unavailable state, and a stale client's submission
    // is refused by the server, which stays authoritative.
    const age = apparentAge.value;
    const payload = {
      race: race.value ?? null,
      subrace: subrace.value ?? null,
      sex: sex.value ?? null,
      apparent_age: age === "" || age === null || age === undefined ? null : Number(age),
      custom_prompt: typeof event?.custom_prompt === "string" ? event.custom_prompt : "",
    };
    const envelope = { action_id: PORTRAIT_ACTION, payload };
    rejected.value = false;
    if (typeof props.dispatch === "function") {
      const id = props.dispatch(envelope);
      if (id === null || id === undefined) {
        rejected.value = true;
        return;
      }
      requestId.value = id;
      succeeded.value = false;
      submitting.value = true;
      // The store published synchronously inside the dispatch, but this
      // component's props only follow on the next render: reconcile then, so
      // a stale pre-dispatch gate snapshot is never read as a release.
      nextTick(reconcile);
    } else {
      // Standalone mounts (stories/tests without the store): the event seam.
      emit("action", envelope);
    }
  }

  function requestPortraitSync() {
    emit("request-sync");
  }

  function openPortraitLog() {
    emit("log");
  }

  watch([() => props.result, () => props.dispatchState], reconcile);

  // Any lifecycle change that leaves this drawer meaningless closes it and
  // forgets only its local pending UI; the server state is read afresh.
  const contextKey = () => {
    const c = props.presentationContext ?? null;
    return c ? `${c.generation ?? ""}|${c.epoch ?? ""}` : "";
  };
  watch(contextKey, () => {
    if (drawerOpen.value || submitting.value) closePortraitDrawer();
  });
  watch(
    () => props.creation?.available === true && mode.value === "custom" && props.stage?.stage !== "confirm",
    (usable) => {
      if (!usable && (drawerOpen.value || submitting.value)) closePortraitDrawer();
    },
  );

  return {
    portrait,
    portraitSlot,
    portraitDrawerOpen: drawerOpen,
    portraitSubmitting: submitting,
    portraitRejected: rejected,
    portraitUnavailableReason,
    portraitSlotDisabled,
    portraitDrawerDisabled,
    portraitPreview,
    portraitDrawerModel: CREATION_DRAWER_MODEL,
    openPortraitDrawer,
    closePortraitDrawer,
    submitPortrait,
    requestPortraitSync,
    openPortraitLog,
  };
}
