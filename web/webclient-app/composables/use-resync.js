// C4: one-sync-per-episode resync (the legacy requestResync contract), extracted
// from AppClient so the SFC stays a passive renderer. The real "renderer cannot
// render" signal is the committed view's `protocolError` (set when the server
// reports a panel/presentation error, e.g. `malformed_envelope` /
// `unsupported_version`). When it transitions null -> set while connected, the
// renderer auto-requests exactly one `ui_sync` for the failure episode; the
// bridge's guard blocks a second request in the same transport generation. When
// the error clears (the server re-synced / reconnected), the episode re-arms.
import { computed, watch } from "vue";

// A `ui_protocol_error` is only auto-resynced when it is recoverable: a
// version mismatch (`unsupported_version`) or a reload-required error cannot
// be fixed by a fresh sync, so no request is sent for those (the graphical
// controls stay locked and the text fallback carries the game).
const RESYNCABLE_ERROR_CODES = new Set([
  "malformed_envelope",
  "presentation_unavailable",
  "no_puppet",
  "internal_error",
]);

function isResyncableError(error) {
  return (
    !!error &&
    RESYNCABLE_ERROR_CODES.has(error.code) &&
    error.reloadRequired !== true
  );
}

export function useResync(store) {
  function resyncActions() {
    return (window.Elosern && window.Elosern.actions) || null;
  }

  // The combined "renderer cannot render" failure state: true when EITHER a
  // locally-rejected malformed presentation (`lastPanelRejection`) OR a
  // recoverable server `ui_protocol_error` is active. A single shared
  // one-sync-per-episode guard ("presentation") is re-armed only when BOTH
  // signals are cleared, so the guard truly represents one whole-presentation
  // failure episode (one sync per episode, no premature re-arm).
  const presentationFailure = computed(() => {
    const resyncableError = isResyncableError(store.view.protocolError);
    return !!store.lastPanelRejection || resyncableError;
  });

  watch(
    presentationFailure,
    (failing, prevFailing) => {
      const actions = resyncActions();
      if (!actions || !store.view.connected) {
        return;
      }
      if (failing && !prevFailing) {
        // A failure signal just became active (a malformed presentation was
        // rejected, or a recoverable protocol error committed): request one
        // ui_sync for this whole-presentation failure episode. The bridge's
        // one-sync-per-episode guard blocks a second request in the same
        // transport generation.
        actions.requestResync("presentation");
      }
      if (!failing && prevFailing) {
        // Both failure signals cleared (a fresh snapshot accepted AND no active
        // recoverable protocol error): re-arm the episode so the next failure
        // can request once more.
        actions.resetResyncEpisode("presentation");
      }
    }
  );

  return { presentationFailure };
}
