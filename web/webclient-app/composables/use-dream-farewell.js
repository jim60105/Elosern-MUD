// The dream stage's farewell hold (dream-farewell-beat). The server commits a
// departure at once: the dream panel's state closes on the same publication
// and carries the goddess's closing line in `ending`. This composable keeps a
// copy of that closed state so the stage can stay mounted for the farewell,
// until the stage releases it.
//
// Only a live departure is held: the committed state changed from open to
// closed for the same session and carries an ending text. A state that is
// already closed when first seen (a fresh page, a reconnect) is never held,
// a disconnect drops a held farewell, and a newly committed open dream
// replaces it. The hold is presentation only and gates no committed state.
import { computed, getCurrentScope, onScopeDispose, ref, watch } from "vue";

const copy = (value) => JSON.parse(JSON.stringify(value));

export function useDreamFarewell(store) {
  const live = computed(() => store.view?.panels?.dream?.state ?? null);
  const held = ref(null);
  // Bumped when a newly committed open dream discards a held farewell, so the
  // host can mount a fresh stage for it instead of reusing the leaving one.
  const generation = ref(0);

  // Synchronous: the hold is in place before any other watcher or render can
  // observe the closed state without it, so the surfaces that yield to an
  // open dream never see a gap between the dream and its farewell.
  watch(
    () => [live.value?.session_id ?? null, !!live.value?.open],
    ([session, open], [previousSession, previousOpen]) => {
      if (open) {
        if (held.value) {
          held.value = null;
          generation.value += 1;
        }
        return;
      }
      if (previousOpen && session === previousSession && live.value?.ending) {
        held.value = copy(live.value);
      }
    },
    { flush: "sync" },
  );
  watch(
    () => store.view?.connected,
    (connected) => {
      if (connected === false) held.value = null;
    },
    { flush: "sync" },
  );

  const state = computed(() => (live.value?.open ? live.value : held.value));
  const active = computed(() => !!state.value);

  function release() {
    held.value = null;
  }

  // The travel layout reads the store, not this composable: the store carries
  // the signal so its own travel projection yields while the stage is held.
  watch(active, (value) => store.setDreamFarewellActive?.(value), { immediate: true });
  if (getCurrentScope()) {
    onScopeDispose(() => store.setDreamFarewellActive?.(false));
  }

  return { state, held, active, release, generation };
}
