// useOriginalEligibility.js — the exact-original save gate both gallery
// original editors share (change unified-gallery-original-editors).
//
// An original editor may dispatch geometry only for the exact original it is
// showing, and only after that very resource decoded with usable dimensions.
// The proof is therefore taken from the driver's OWN successful observation —
// the selected resource's source layer, resource identity and version — and
// never from the editor's live descriptor: an observation that settled while the
// descriptor had already moved on names the original that really decoded, and
// the comparison below refuses it.
//
// The LIVE descriptor still has to carry that same original, which adds the
// *synchronous* half of the rule: a subject, card or resource replacement
// retires eligibility in the same tick — before the driver's own pre-flush
// restart can run — while a geometry-only revision (the same original) keeps the
// decoded proof and its save.
//
// A silhouette, another card, a scene background or the fixed adult ruler is
// never part of this proof: the editors request the exact original with no
// terminal, and only the original's own driver is handed to this gate.

import { computed, ref, toValue, watch } from "vue";

import { artworkOriginalIdentity, artworkSelectedIdentity } from "../lib/artwork.js";
import { LOAD_PHASE } from "../lib/image-attempts.js";

// A decoded size only counts while it is a real, positive pixel size: an
// unobserved or zero-size result can never be a geometry reference.
function usableDimensions(value) {
  return !!value && Number(value.width) > 0 && Number(value.height) > 0;
}

export function useOriginalEligibility(artwork, phase, selected, panelUnavailable = null) {
  // The exact original whose decode is proven: the identity of the resource the
  // driver actually resolved, recorded the moment its phase reported success.
  const proven = ref(null);
  watch(phase, () => {
    proven.value = phase.value === LOAD_PHASE.success
      ? artworkSelectedIdentity(toValue(selected))
      : null;
  }, { flush: "sync", immediate: true });
  // A decode authorizes a save only while it still belongs to the original the
  // descriptor states, and only with that same observation's own decoded size.
  const decoded = computed(() => {
    const observation = toValue(selected);
    return proven.value !== null
      && proven.value === artworkOriginalIdentity(toValue(artwork))
      && usableDimensions(observation?.dimensions);
  });
  const saveReady = computed(() => (
    decoded.value && !(panelUnavailable && toValue(panelUnavailable))
  ));
  return { decoded, saveReady };
}
