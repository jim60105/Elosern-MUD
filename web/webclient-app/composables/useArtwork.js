// useArtwork.js — the canonical descriptor binding (change
// unified-gallery-image-contract).
//
// It is the ONLY gallery-side entry to the shared ordered-attempt lifecycle:
// it lifts one canonical panel descriptor into the internal load request and
// hands that request to the loading-core driver, so no surface builds its own
// resource list, keeps its own failed-URL cache or selects its own fallback.
//
// The request is derived from the descriptor's own ordered facts: the stable
// subject identity (which is also the resolution epoch, so a different subject
// retires the old callbacks), the attempts verbatim and the permitted
// terminal. A null descriptor is not a request at all.
//
// The public result is `{subjectId, revision, phase, selected, reachedFaults,
// exhausted}` plus the driver's element handlers. Consumers may keep their own
// display content, but they cannot set load success and cannot clear a reached
// fault.
//
// `options.terminal === false` drops the descriptor's terminal from the load
// request: the preview surfaces take it, the editors that measure the exact
// original do not.

import { computed, toValue } from "vue";

import { useImageAttempts } from "./useImageAttempts.js";

function requestFor(descriptor, permitTerminal) {
  if (!descriptor || typeof descriptor !== "object") {
    return null;
  }
  return {
    subjectId: descriptor.subject_id ?? null,
    // The resolution epoch is the descriptor's stable subject identity: a
    // genuinely different subject retires every callback of the old one, while
    // a re-presentation of the SAME subject keeps its known outcomes. The
    // revision is deliberately not the epoch — it covers geometry, and the
    // driver's own fact key already restarts resolution whenever the attempt
    // ORDER changes, so a geometry-only revision must not invalidate a decoded
    // resource.
    epoch: descriptor.subject_id ?? null,
    attempts: Array.isArray(descriptor.attempts) ? descriptor.attempts : [],
    // A preview surface permits the descriptor's terminal alpha mask; an
    // editor that MEASURES the exact original does not, because a silhouette
    // is not a geometry reference (design: "avatars and original editors
    // consume the same descriptor but their load request permits no terminal
    // image").
    terminal: permitTerminal ? descriptor.terminal ?? null : null,
  };
}

export function useArtwork(artwork, availability, options = {}) {
  const permitTerminal = options.terminal !== false;
  const descriptor = computed(() => toValue(artwork) ?? null);
  const request = computed(() => requestFor(descriptor.value, permitTerminal));
  const load = useImageAttempts(request, availability, options);

  return {
    ...load,
    subjectId: computed(() => descriptor.value?.subject_id ?? null),
    revision: computed(() => descriptor.value?.revision ?? null),
  };
}
