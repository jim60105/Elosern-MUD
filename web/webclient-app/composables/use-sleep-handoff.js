// The server-owned contextual sleep-control surface (align-sleep-handoff-
// and-owner-dream). The panel carries the complete companion list, the exact
// party option, the owner-only dream question and the retained continuation;
// this composable only projects it into the existing centred card primitives.
// It never chooses a companion, derives eligibility, advances time or dispatches
// a combined sleep/dream request.
import { computed, nextTick, ref, watch } from "vue";

import { BACK_ROW } from "./use-person-focus.js";

export const SLEEP_HANDOFF_LOCKED_REASON = "上一個行動尚未完成，請稍候。";
export const SLEEP_CONTINUE_LABEL = "繼續睡眠";

function digitBadge(index) {
  return index < 9 ? String(index + 1) : "·";
}

export function sleepHandoffRows(panel, locked, includeContinuation) {
  if (!panel) {
    return [];
  }
  const rows = (panel.selection?.rows || []).map((row, index) => ({
    key: `sleep:${row.kind}:${row.identity}`,
    label: row.label,
    badge: digitBadge(index),
    kind: "verb",
    enabled: !!row.enabled && !locked,
    reason: locked ? SLEEP_HANDOFF_LOCKED_REASON : row.reason,
    testId: "sleep-handoff-row",
    rowKind: row.kind,
    identity: row.identity,
  }));
  const party = panel.party || {};
  rows.push({
    key: "sleep:party",
    label: party.label,
    badge: digitBadge(rows.length),
    kind: "verb",
    enabled: !!party.enabled && !locked,
    reason: locked ? SLEEP_HANDOFF_LOCKED_REASON : party.reason,
    testId: "sleep-handoff-party",
    rowKind: "party",
    identity: null,
  });
  if (includeContinuation) {
    rows.push({
      key: "sleep:continue",
      label: SLEEP_CONTINUE_LABEL,
      badge: digitBadge(rows.length),
      kind: "verb",
      enabled: !locked,
      reason: locked ? SLEEP_HANDOFF_LOCKED_REASON : null,
      testId: "sleep-handoff-continue",
      rowKind: "continue",
      identity: null,
    });
  }
  rows.push(BACK_ROW);
  return rows;
}

export function continuationRows(panel, locked) {
  return [
    {
      key: "sleep:continue",
      label: SLEEP_CONTINUE_LABEL,
      badge: "1",
      kind: "verb",
      enabled: !locked,
      reason: locked ? SLEEP_HANDOFF_LOCKED_REASON : null,
      testId: "sleep-handoff-continue",
      rowKind: "continue",
      identity: null,
    },
    BACK_ROW,
  ];
}

export function useSleepHandoff(store, { dispatchIntent, skipDisabled, compassRef }) {
  // Client-local dismissal of the selection chrome only. It is keyed by the
  // server's control-view identity, so a new view asks again while an
  // unchanged reconnect keeps the already-shown surface settled.
  const dismissedKey = ref(null);
  const wasOpen = ref(false);

  const panel = computed(() => {
    const value = store.view?.panels?.sleep_handoff || null;
    return value && value.available === true ? value : null;
  });
  const dreamOpen = computed(() => !!store.view?.panels?.dream?.state?.open);
  const viewKey = computed(() => {
    if (!panel.value) {
      return null;
    }
    const owner = panel.value.owner_sleep;
    return `${panel.value.transition_id}:${owner ? owner.generation : ""}`;
  });

  const dismissed = computed(
    () => viewKey.value !== null && dismissedKey.value === viewKey.value,
  );
  const dreamPending = computed(() => !!panel.value?.owner_sleep?.dream_pending);
  const selectionAvailable = computed(
    () => !!panel.value?.selection?.available,
  );
  const continuationAvailable = computed(
    () =>
      !!panel.value?.owner_sleep?.continuation_available ||
      (!!panel.value?.controlled_sleep && !panel.value?.owner_sleep),
  );

  const selectionOpen = computed(
    () =>
      !!panel.value &&
      !dreamOpen.value &&
      selectionAvailable.value &&
      !dismissed.value,
  );
  const questionOpen = computed(
    () =>
      !!panel.value &&
      !dreamOpen.value &&
      dreamPending.value &&
      (!selectionAvailable.value || dismissed.value),
  );
  const continuationOpen = computed(
    () =>
      !!panel.value &&
      !dreamOpen.value &&
      !selectionOpen.value &&
      !questionOpen.value &&
      !dreamPending.value &&
      continuationAvailable.value &&
      !dismissed.value,
  );
  const anyOpen = computed(
    () => selectionOpen.value || questionOpen.value || continuationOpen.value,
  );

  const selectionRows = computed(() =>
    sleepHandoffRows(
      panel.value,
      skipDisabled.value,
      !dreamPending.value && continuationAvailable.value,
    ),
  );
  const continuation = computed(() =>
    continuationRows(panel.value, skipDisabled.value),
  );
  const caption = computed(() => "睡眠與交接");
  const questionCaption = computed(() => "睡眠夢境");

  function identityForContinue() {
    const controlled = panel.value?.controlled_sleep;
    const owner = panel.value?.owner_sleep;
    const source = owner || controlled;
    if (!source) {
      return null;
    }
    return { sleep_id: source.sleep_id, revision: source.revision };
  }

  function dismiss() {
    dismissedKey.value = viewKey.value;
  }

  function onPick(key) {
    if (!panel.value || skipDisabled.value) {
      return;
    }
    if (key === "back") {
      dismiss();
      return;
    }
    const row = selectionRows.value.find((item) => item.key === key);
    if (!row || !row.enabled) {
      return;
    }
    const controlled = panel.value.controlled_body_id;
    if (row.rowKind === "party") {
      dispatchIntent("explore.sleep_party", {});
    } else if (row.rowKind === "continue") {
      const identity = identityForContinue();
      if (identity) {
        dispatchIntent("explore.sleep_continue", identity);
      }
    } else if (row.rowKind === "return") {
      dispatchIntent("explore.possess_release", { npc_id: controlled });
    } else {
      dispatchIntent("explore.possess", { npc_id: row.identity });
    }
  }

  function onContinuationPick(key) {
    if (key === "back") {
      dismissedKey.value = viewKey.value;
      return;
    }
    const identity = identityForContinue();
    if (identity && !skipDisabled.value) {
      dispatchIntent("explore.sleep_continue", identity);
    }
  }

  function answer(decision) {
    const owner = panel.value?.owner_sleep;
    if (!owner || skipDisabled.value) {
      return;
    }
    dispatchIntent("explore.sleep_dream", {
      sleep_id: owner.sleep_id,
      revision: owner.revision,
      generation: owner.generation,
      decision,
    });
  }

  // The question's close control is the negative answer, exactly like the
  // text `dream decline`; it is not a local dismissal.
  function onQuestionYes() {
    answer("enter");
  }

  function onQuestionNo() {
    answer("decline");
  }

  function onQuestionClose() {
    answer("decline");
  }

  function focusLost(active) {
    return (
      !active ||
      active === document.body ||
      active === document.documentElement ||
      !active.isConnected ||
      !!active.closest?.('[data-anchor="choices"]')
    );
  }

  watch(anyOpen, async (open, previous) => {
    if (open) {
      // The contextual surface owns the single modal focus; a client-local
      // room card must not stay open beneath it.
      store.closeRoomCard?.();
      wasOpen.value = true;
      return;
    }
    if (!previous || !wasOpen.value) {
      return;
    }
    wasOpen.value = false;
    await nextTick();
    if (typeof document === "undefined") {
      return;
    }
    if (!focusLost(document.activeElement)) {
      return;
    }
    if (compassRef?.value) {
      compassRef.value.focus();
      if (!focusLost(document.activeElement)) {
        return;
      }
    }
    document.getElementById("action-dock")?.focus({ preventScroll: true });
  });

  watch(viewKey, (value, previous) => {
    if (value !== previous) {
      dismissedKey.value = null;
    }
  });

  return {
    sleepHandoffPanel: panel,
    sleepHandoffSelectionOpen: selectionOpen,
    sleepHandoffQuestionOpen: questionOpen,
    sleepHandoffContinuationOpen: continuationOpen,
    sleepHandoffRows: selectionRows,
    sleepHandoffContinuationRows: continuation,
    sleepHandoffCaption: caption,
    sleepHandoffQuestionCaption: questionCaption,
    onSleepHandoffPick: onPick,
    onSleepContinuationPick: onContinuationPick,
    onSleepQuestionYes: onQuestionYes,
    onSleepQuestionNo: onQuestionNo,
    onSleepQuestionClose: onQuestionClose,
  };
}
