// useOriginalEligibility.js — the exact-original save gate both gallery
// original editors share (change unified-gallery-original-editors).
//
// An original editor may dispatch geometry only for the exact original it is
// showing, and only after that very resource decoded with usable dimensions.
// The shared driver already scopes every observation to its own attempt element
// and clears its result on a restart; this composable adds the *synchronous*
// half of the same rule: it records the exact original identity a successful
// decode proved and requires the LIVE descriptor to still carry that same
// original. A subject, card or resource replacement therefore retires
// eligibility in the same tick — before the driver's pre-flush restart can run
// — while a geometry-only revision (the same original) keeps the decoded proof
// and its save.
//
// A silhouette, another card, a scene background or the fixed adult ruler is
// never part of this proof: the editors request the exact original with no
// terminal, and only the original's own driver is handed to this gate.

import { computed, ref, toValue, watch } from "vue";

import { artworkOriginalIdentity } from "../lib/artwork.js";
import { LOAD_PHASE } from "../lib/image-attempts.js";

// A decoded size only counts while it is a real, positive pixel size: an
// unobserved or zero-size result can never be a geometry reference.
function usableDimensions(value) {
  return !!value && Number(value.width) > 0 && Number(value.height) > 0;
}

export function useOriginalEligibility(artwork, phase, dimensions, panelUnavailable = null) {
  // The exact original whose decode is proven: the identity recorded at the
  // moment the driver observed a successful decode.
  const proven = ref(null);
  watch(phase, () => {
    proven.value = phase.value === LOAD_PHASE.success
      ? artworkOriginalIdentity(toValue(artwork))
      : null;
  }, { flush: "sync", immediate: true });
  // A decode authorizes a save only while it still belongs to the original the
  // editor is displaying, and only with the driver's own observed dimensions.
  const decoded = computed(() => (
    proven.value !== null
    && proven.value === artworkOriginalIdentity(toValue(artwork))
    && usableDimensions(toValue(dimensions))
  ));
  const saveReady = computed(() => (
    decoded.value && !(panelUnavailable && toValue(panelUnavailable))
  ));
  return { decoded, saveReady };
}
