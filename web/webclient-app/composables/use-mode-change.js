// The live mode-change signal (webclient-mode-transitions, design D2; the AVG
// stage design §9.2 "only a live mode change animates").
//
// The stage animates a mode change only when it is live: a committed change
// between two known modes. The shell's `mode` prop is coerced
// (`store.view.mode || 'exploration'`), so it cannot tell a live change from
// a reconnect, whose transport reset nulls the raw mode and whose resync
// snapshot sets it again. This composable reads the RAW committed mode.
//
// - `modeChange` names the last live transition (`exploration-combat`,
//   `dialogue-exploration`, ...). A null endpoint (a transport reset, the
//   first snapshot) clears it, so the stage's CSS transitions, keyed on the
//   attribute's presence, play nothing across a reconnect. A same-mode
//   resync keeps it.
// - `modeHydrating` is true from any null edge (the reset that clears the
//   mode, or a mount before the first snapshot) until the frame that renders
//   the arriving mode has flushed. The Vue `<Transition>`s that follow the
//   mode (the host actor, the name plate) and the choice list's entrance read
//   it, so neither edge of a reconnect slides, fades, or staggers anything.
import { ref, watch } from "vue";

// Pure: the next `modeChange` value for a committed change `from -> to`.
export function nextModeChange(previous, from, to) {
  if (from == null || to == null) {
    return null;
  }
  if (from === to) {
    return previous;
  }
  return `${from}-${to}`;
}

export function useModeChange(store) {
  const modeChange = ref(null);
  const modeHydrating = ref(store.view.mode == null);
  // Pre-flush: both refs change in the same patch as the mode itself. This
  // assumes a transport reset (mode -> null) and its resync snapshot
  // (null -> mode) land in separate ticks, as the transport delivers them;
  // a same-tick `X -> null -> Y` would be coalesced into a live-looking
  // `X -> Y` by the watcher.
  watch(
    () => store.view.mode,
    (to, from) => {
      modeChange.value = nextModeChange(modeChange.value, from, to);
      if (from == null || to == null) {
        modeHydrating.value = true;
      }
    },
  );
  // Post-flush: the arriving mode has rendered with no transition, so the
  // next live change may animate again.
  watch(
    () => store.view.mode,
    (to, from) => {
      if (from == null && to != null) {
        modeHydrating.value = false;
      }
    },
    { flush: "post" },
  );
  return { modeChange, modeHydrating };
}
