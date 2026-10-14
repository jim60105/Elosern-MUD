<script setup>
// ArtworkPreview — one canonical descriptor position, rendered through the
// shared ordered-attempt lifecycle (change unified-gallery-image-contract).
//
// It owns no selector, no failed-URL cache and no fallback policy. It loads
// exactly the descriptor's ordered candidates through useArtwork; when the
// exact requested original cannot be loaded, the descriptor's permitted
// terminal alpha mask becomes the current attempt and is painted by the shared
// ArtworkAlpha primitive — and only after that same resource itself reported a
// successful load, so a broken mask can never leave a solid rectangle standing
// in for a figure. A reached fault keeps its persistent accessible marker even
// after a lower source (or the silhouette) succeeds; the component never
// changes a card status, never selects another original and never enables an
// action.
import { computed, onBeforeUnmount } from "vue";

import ArtworkAlpha from "./ArtworkAlpha.vue";
import ArtworkFailure from "./ArtworkFailure.vue";
import { artworkAvailability, artworkGeometry, artworkTerminalUrl } from "../lib/artwork.js";
import { useArtwork } from "../composables/useArtwork.js";
import { faceObjectPosition } from "./face-rect.js";

const props = defineProps({
  // The canonical descriptor, or null for a position with no artwork at all.
  artwork: { type: Object, default: null },
  // The committed panel the descriptor came from (its `available` is the
  // availability fact this position is judged against).
  panel: { type: Object, default: null },
  // Whether the committed mode requires this surface at all.
  required: { type: Boolean, default: true },
  // Whether the committed payload intentionally admits this reference.
  hasReference: { type: Boolean, default: true },
  viewSubjectId: { type: String, default: null },
  alt: { type: String, default: "" },
});

const availability = computed(() => artworkAvailability({
  panel: props.panel,
  required: props.required,
  hasReference: props.hasReference,
  artwork: props.artwork,
  viewSubjectId: props.viewSubjectId,
}));
const { attempt, phase, selected, reachedFaults, panelUnavailable, onImageLoad, onImageError, dispose } = useArtwork(
  () => props.artwork,
  availability,
);

// The descriptor's terminal alpha resource, told apart from the exact
// original by its own URL rather than by re-deriving source order.
const terminalUrl = computed(() => artworkTerminalUrl(props.artwork));
const probeUrl = computed(() => attempt.value?.url ?? null);
const silhouette = computed(() => !!probeUrl.value && probeUrl.value === terminalUrl.value);
const alphaResult = computed(() => (
  silhouette.value && phase.value === "success" ? { url: probeUrl.value, phase: "success" } : null
));
// The crop follows the resource actually selected; before any load it falls
// back to the descriptor's exact-original geometry.
const objectPosition = computed(() => faceObjectPosition(
  (selected.value?.geometry ?? artworkGeometry(props.artwork))?.face_rect,
));
const loading = computed(() => phase.value === "loading");
const failure = computed(() => reachedFaults.value[reachedFaults.value.length - 1] ?? null);
const failureKind = computed(() => (
  panelUnavailable.value || failure.value ? "failure" : null
));
const failureReason = computed(() => (
  panelUnavailable.value ? "panel_unavailable" : failure.value?.reason ?? null
));

onBeforeUnmount(dispose);
</script>

<template>
  <div class="artwork-preview" data-testid="artwork-preview">
    <img
      v-if="probeUrl"
      :key="attempt.token"
      class="artwork-preview__figure"
      :class="{ 'artwork-preview__figure--probe': silhouette }"
      :src="probeUrl"
      :data-attempt-token="attempt.token"
      :alt="silhouette ? '' : alt"
      :aria-hidden="silhouette ? 'true' : null"
      :style="{ objectPosition }"
      draggable="false"
      @load="onImageLoad"
      @error="onImageError"
    >
    <ArtworkAlpha v-if="alphaResult" :result="alphaResult" />
    <ArtworkFailure :kind="failureKind" :reason="failureReason" />
  </div>
</template>

<style scoped>
.artwork-preview {
  position: relative;
  display: block;
  width: 100%;
  height: 100%;
  min-width: 0;
  overflow: hidden;
}
.artwork-preview__figure {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
/* The silhouette probe is never painted: its only job is to carry the load or
   error signal for the alpha mask, which then paints the shape itself. */
.artwork-preview__figure--probe {
  visibility: hidden;
}
.artwork-preview > .artwork-alpha {
  position: absolute;
  inset: 0;
}
/* A reached fault (or a panel-availability failure) is a persistent, locally
   accessible marker: it stacks over the image band and never becomes a
   rectangular fill standing in for the artwork. */
.artwork-preview > .artwork-failure {
  position: absolute;
  right: calc(6px * var(--ui-scale));
  bottom: calc(6px * var(--ui-scale));
  left: calc(6px * var(--ui-scale));
  z-index: 1;
}
</style>
