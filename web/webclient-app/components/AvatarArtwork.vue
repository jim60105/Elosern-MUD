<script setup>
// AvatarArtwork — the shared small-avatar renderer (change
// unified-avatar-rendering).
//
// ONE renderer owns every small avatar: the top-bar roster/switcher
// thumbnails, the presence medallions, the party drawer's companion rows and
// the combat participant rows. It consumes the canonical artwork descriptor
// through the same shared ordered attempt lifecycle as the figure renderer,
// with the avatar's own policy:
//
//   * REAL-ONLY: the load request never permits the descriptor's terminal
//     alpha mask, because a silhouette is not an avatar. No avatar surface
//     ever requests one, and no avatar surface changes generation state.
//   * The crop follows the SUCCEEDING candidate's own geometry (never the
//     highest-ranked candidate's) and ignores the descriptor's `stage` triple.
//   * With no real image the avatar draws the first grapheme of the trimmed
//     name — the shared `portraitGlyph` helper, with a neutral symbol for an
//     empty name — never a silhouette and never a broken image element.
//   * A reached fault keeps a persistent, compact, keyboard-usable explanation
//     through the shared bounded failure-category mapping. Expected absence and
//     in-progress loading carry no error styling at all.
//
// The compact explanation has two ownership shapes, because the surfaces it is
// embedded in differ:
//
//   * standalone (party rows, combat rows): the avatar owns a focusable
//     `<button>` marker whose accessible name IS the bounded category
//     sentence, so a keyboard user reaches the explanation with no hover.
//   * hosted (`failureTextId` set): the avatar is embedded in the OWNING
//     surface's own focusable control (the switcher's pill/row buttons) or in
//     a roving-tabindex composite (the presence rail's listbox). A second
//     focusable control there would break that control's keyboard contract, so
//     the marker stays inert and the bounded sentence renders in a
//     visually-hidden node the host references through `aria-describedby`.
import { computed, onBeforeUnmount, useId } from "vue";

import { faceCropStyle, faceObjectPosition } from "./face-rect.js";
import { portraitGlyph } from "./character-identity.js";
import { artworkAvailability } from "../lib/artwork.js";
import { artworkFailureCategory } from "../lib/artwork-failure.js";
import { useArtwork } from "../composables/useArtwork.js";

const props = defineProps({
  // The canonical descriptor of this avatar's subject, or null for a position
  // whose committed panel admits no reference at all.
  artwork: { type: Object, default: null },
  // The committed panel the descriptor came from (its `available` is the
  // availability fact this avatar is judged against).
  panel: { type: Object, default: null },
  // Whether the committed mode requires this surface at all.
  required: { type: Boolean, default: true },
  // Whether the committed payload intentionally admits this reference.
  hasReference: { type: Boolean, default: true },
  viewSubjectId: { type: String, default: null },
  // The identity text this avatar stands for.
  name: { type: String, default: "" },
  // The name whose first grapheme the avatar draws; without one the identity
  // text's own first grapheme is drawn.
  initialOf: { type: String, default: "" },
  // The avatar crop policy: "zoom" enlarges and anchors the marked rectangle
  // (the roster/presence/party thumbnails), "recenter" keeps the recenters-only
  // cover crop the combat participant row uses.
  crop: {
    type: String,
    default: "zoom",
    validator: (value) => value === "zoom" || value === "recenter",
  },
  // The hooks the OWNING surface publishes for this avatar position, naming its
  // own frozen contract hooks while this renderer owns the load.
  faceTestId: { type: String, default: "avatar-artwork__face" },
  initialTestId: { type: String, default: "avatar-artwork__initial" },
  // When set, this avatar is hosted by the caller's own focusable control: the
  // bounded explanation renders with this id for that control's
  // `aria-describedby`, and the compact mark itself is inert.
  failureTextId: { type: String, default: null },
});

const availability = computed(() => artworkAvailability({
  panel: props.panel,
  required: props.required,
  hasReference: props.hasReference,
  artwork: props.artwork,
  viewSubjectId: props.viewSubjectId,
}));
// Real-only: the avatar's load request never permits the descriptor's terminal
// alpha mask (a silhouette is not an avatar).
const {
  attempt,
  phase,
  selected,
  reachedFaults,
  panelUnavailable,
  onImageLoad,
  onImageError,
  dispose,
} = useArtwork(() => props.artwork, availability, { terminal: false });
onBeforeUnmount(dispose);

const probeUrl = computed(() => attempt.value?.url ?? null);
// A shown real image: the attempt settled successfully on a real resource.
const realImage = computed(() => !!probeUrl.value && phase.value === "success");
// An attempt is in flight: the identity initial never paints over an image the
// browser is still loading (it stands once every permitted source is spent).
const loading = computed(() => phase.value === "loading");
// The crop always follows the candidate that is actually being shown: the
// in-flight attempt's own resource while it loads, then the SUCCEEDING
// candidate's own geometry once it settles (never the highest-ranked
// candidate's, which is what a failed first source would otherwise lend out).
// The shared lifecycle refreshes the selected geometry in place on a
// geometry-only revision, so a re-presentation applies without a remount.
const geometry = computed(() => (
  selected.value?.geometry ?? attempt.value?.resource?.geometry ?? null
));
const faceRect = computed(() => geometry.value?.face_rect ?? null);
const placementStyle = computed(() => (
  props.crop === "recenter"
    ? { objectPosition: faceObjectPosition(faceRect.value) }
    : faceCropStyle(faceRect.value, faceObjectPosition(faceRect.value))
));
const glyph = computed(() => portraitGlyph(props.initialOf || props.name));

// The one local fact this avatar states: a reached load/decode fault, or a
// required panel that could not supply its data. A missing or pending
// generation is expected absence and carries no marker.
const failure = computed(() => reachedFaults.value[reachedFaults.value.length - 1] ?? null);
const failureReason = computed(() => (
  panelUnavailable.value ? "panel_unavailable" : failure.value?.reason ?? null
));
const failureText = computed(() => (failureReason.value ? artworkFailureCategory(failureReason.value) : ""));
const failed = computed(() => failureText.value !== "");
const idPrefix = useId();
const explanationId = computed(() => props.failureTextId || `${idPrefix}-explanation`);
</script>

<template>
  <figure class="avatar-artwork" data-testid="avatar-artwork">
    <!-- The attempt owns its own element, keyed by its token, so a late event
         from a retired element can never settle a newer attempt. -->
    <img
      v-if="probeUrl"
      :key="attempt.token"
      class="avatar-artwork__figure"
      :src="probeUrl"
      :data-attempt-token="attempt.token"
      :data-testid="faceTestId"
      :style="placementStyle"
      alt=""
      aria-hidden="true"
      draggable="false"
      @load="onImageLoad"
      @error="onImageError"
    >
    <!-- The identity initial is the only fallback: never a silhouette, never a
         broken image element. -->
    <span
      v-if="!realImage && !loading"
      class="avatar-artwork__initial"
      :data-testid="initialTestId"
      aria-hidden="true"
    >{{ glyph }}</span>
    <template v-if="failed">
      <!-- Standalone: the marker itself is the keyboard route to the bounded
           explanation (its accessible name is the whole sentence). -->
      <button
        v-if="!failureTextId"
        type="button"
        class="avatar-artwork__failure"
        data-testid="artwork-failure"
      >
        <span class="avatar-artwork__failure-mark" aria-hidden="true">⚠</span>
        <span class="avatar-artwork__failure-text">{{ failureText }}</span>
      </button>
      <!-- Hosted: the caller's own control carries the explanation, so the
           compact mark stays inert and the sentence is exposed to it. -->
      <template v-else>
        <span class="avatar-artwork__failure" data-testid="artwork-failure" aria-hidden="true">⚠</span>
        <span :id="explanationId" class="visually-hidden" role="status">{{ failureText }}</span>
      </template>
    </template>
  </figure>
</template>

<style scoped>
.avatar-artwork {
  position: relative;
  display: block;
  width: 100%;
  height: 100%;
  margin: 0;
  overflow: hidden;
}
.avatar-artwork__figure {
  position: absolute;
  top: 0;
  left: 0;
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.avatar-artwork__initial {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: var(--paper-300);
  font-family: var(--f-serif, serif);
  font-size: var(--text-sm);
}
/* The compact explanation: a bounded corner mark. Its meaning is carried by
   shape and text, never by color alone. */
.avatar-artwork__failure {
  position: absolute;
  right: 0;
  bottom: 0;
  display: grid;
  place-items: center;
  width: calc(13px * var(--ui-scale));
  height: calc(13px * var(--ui-scale));
  margin: 0;
  padding: 0;
  border: 1px solid #ed7e82;
  border-radius: 3px;
  background: #2a1a1ecc;
  color: #f3b9bc;
  font-family: var(--f-sans, sans-serif);
  font-size: calc(8px * var(--ui-scale));
  line-height: 1;
}
/* The bounded sentence is the marker's accessible name; it is never painted. */
.avatar-artwork__failure-text,
.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}
.avatar-artwork__failure:focus-visible {
  outline: 2px solid var(--gold-400, #e2c06a);
  outline-offset: 1px;
}
</style>
