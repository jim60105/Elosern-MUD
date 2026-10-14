<script setup>
// ReferenceArtwork — the shared figure renderer (change
// unified-portrait-image-contract).
//
// It consumes one canonical artwork descriptor through the shared ordered
// attempt lifecycle (`useArtwork`) and owns no selector, no failed-URL cache
// and no fallback policy of its own. Three positions read from that one state:
//
//   * stage  — the standing figure on the stage band: contain fit, floor
//     aligned, the descriptor's own placement triple;
//   * cover  — a framed portrait: the shared rect-driven cover crop;
//   * avatar — the small real-only position (roster thumbnails, presence
//     medallions, party rows, combat participant rows): the successful
//     candidate's own face-rect zoom crop, and never the alpha terminal,
//     because a silhouette is not an avatar.
//
// Both FIGURE layouts permit the descriptor's terminal alpha mask: when no
// real portrait succeeds, the committed silhouette is painted by the shared
// ArtworkAlpha primitive, and only after that same resource itself reported a
// successful load, so a broken mask can never leave a solid rectangle standing
// in for a figure. A reached fault keeps its persistent accessible marker even
// after a lower source succeeds. Real and terminal geometry stay separate, and
// a geometry-only revision applies immediately without a remount.
import { computed, onBeforeUnmount } from "vue";

import ArtworkAlpha from "./ArtworkAlpha.vue";
import ArtworkFailure from "./ArtworkFailure.vue";
import { faceCropStyle, faceObjectPosition } from "./face-rect.js";
import { portraitGlyph } from "./character-identity.js";
import { artworkAvailability, artworkGeometry, artworkTerminalGeometry, artworkTerminalUrl } from "../lib/artwork.js";
import { useArtwork } from "../composables/useArtwork.js";

const props = defineProps({
  // The canonical descriptor of this position, or null for a position whose
  // committed panel admits no reference at all.
  artwork: { type: Object, default: null },
  // The committed panel the descriptor came from (its `available` is the
  // availability fact this position is judged against).
  panel: { type: Object, default: null },
  // Whether the committed mode requires this surface at all.
  required: { type: Boolean, default: true },
  // Whether the committed payload intentionally admits this reference.
  hasReference: { type: Boolean, default: true },
  viewSubjectId: { type: String, default: null },
  // The identity text the placeholder states.
  name: { type: String, default: "" },
  // The name whose first grapheme the placeholder draws; without one the
  // identity text's own first grapheme is drawn.
  initialOf: { type: String, default: "" },
  // The stage band layout (contain, floor aligned, the placement triple).
  stage: { type: Boolean, default: false },
  // The small real-only avatar position.
  avatar: { type: Boolean, default: false },
  // The hooks the OWNING surface publishes for the avatar position: the
  // loaded face image and the identity-glyph fallback. They name that
  // surface's own frozen contract hooks while this one renderer owns the load.
  faceTestId: { type: String, default: null },
  initialTestId: { type: String, default: null },
  motionLevel: { type: String, default: "full" },
});

const availability = computed(() => artworkAvailability({
  panel: props.panel,
  required: props.required,
  hasReference: props.hasReference,
  artwork: props.artwork,
  viewSubjectId: props.viewSubjectId,
}));
// The avatar position is a real-only consumer: its load request permits no
// terminal image, because a silhouette is not an avatar. Both FIGURE layouts
// take the descriptor's terminal.
const { attempt, phase, reachedFaults, panelUnavailable, onImageLoad, onImageError, dispose } = useArtwork(
  () => props.artwork,
  availability,
  { terminal: !props.avatar },
);

// The terminal alpha resource, told apart from a real original by its own URL
// rather than by re-deriving source order.
const terminalUrl = computed(() => artworkTerminalUrl(props.artwork));
const probeUrl = computed(() => attempt.value?.url ?? null);
const silhouette = computed(() => !!probeUrl.value && probeUrl.value === terminalUrl.value);
const alphaResult = computed(() => (
  silhouette.value && phase.value === "success" ? { url: probeUrl.value, phase: "success" } : null
));
const realImage = computed(() => !!probeUrl.value && !silhouette.value && phase.value === "success");
// The crop always follows the LIVE descriptor: the presented resource's own
// geometry, so a geometry-only re-presentation applies as soon as it lands.
const geometry = computed(() => (
  silhouette.value ? artworkTerminalGeometry(props.artwork) : artworkGeometry(props.artwork)
));
const faceRect = computed(() => geometry.value?.face_rect ?? null);
const stageVars = computed(() => ({
  "--stage-scale": geometry.value?.stage?.scale ?? 1,
  "--stage-x": geometry.value?.stage?.x ?? 0,
  "--stage-y": geometry.value?.stage?.y ?? 0,
}));
const placementStyle = computed(() => {
  if (props.stage) {
    return { objectPosition: "center bottom", ...stageVars.value };
  }
  if (props.avatar) {
    return faceCropStyle(faceRect.value, faceObjectPosition(faceRect.value));
  }
  return { objectPosition: faceObjectPosition(faceRect.value) };
});

// The one state label this position states. Generation truth comes from the
// descriptor's own `generation_state`; a reached load/decode fault is the
// local fact that overrides it, and a missing required panel is its own
// availability fact — never a generation claim.
const failure = computed(() => reachedFaults.value[reachedFaults.value.length - 1] ?? null);
const failureKind = computed(() => (panelUnavailable.value || failure.value ? "failure" : null));
const failureReason = computed(() => (
  panelUnavailable.value ? "panel_unavailable" : failure.value?.reason ?? null
));
const state = computed(() => {
  if (realImage.value) return "done";
  if (panelUnavailable.value) return "unavailable";
  if (failure.value?.reason === "image_load_failed") return "load-failed";
  if (failure.value?.reason === "image_decode_failed") return "load-failed";
  const generation = props.artwork?.generation_state ?? null;
  if (generation === "pending") return "pending";
  if (generation === "failed") return "failed";
  return "missing";
});
const STATE_LABELS = {
  pending: "肖像生成中",
  failed: "肖像生成失敗",
  "load-failed": "肖像載入失敗",
  missing: "無肖像",
  unavailable: "無法提供",
};
const stateLabel = computed(() => STATE_LABELS[state.value] ?? "");
const glyphSource = computed(() => props.initialOf || props.name || stateLabel.value);
const glyph = computed(() => portraitGlyph(glyphSource.value));
</script>

<template>
  <figure
    class="reference-artwork"
    :class="{ 'reference-artwork--stage': stage, 'reference-artwork--avatar': avatar }"
    :data-status="stage ? state : null"
    :data-motion="stage ? motionLevel : null"
    data-testid="reference-artwork"
  >
    <span v-if="stage" class="reference-artwork__ground" aria-hidden="true"></span>
    <img
      v-if="probeUrl"
      :key="attempt.token"
      class="reference-artwork__figure"
      :class="{ 'reference-artwork__figure--probe': silhouette }"
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
    <div v-if="stage && !realImage" class="reference-artwork__silhouette" data-testid="reference-artwork__placeholder" aria-hidden="true">
      <!-- The descriptor's own terminal alpha mask, dark-filled and
           floor-aligned: painted only once that resource itself loaded, so a
           missing bundled resource leaves the name and the truthful label
           instead of a solid rectangle. -->
      <ArtworkAlpha v-if="alphaResult" :result="alphaResult" />
      <div class="reference-artwork__chest">
        <span class="reference-artwork__placeholder-glyph">{{ glyph }}</span>
        <span class="reference-artwork__identity">{{ name }}</span>
        <span class="reference-artwork__placeholder-label">{{ stateLabel }}</span>
      </div>
    </div>
    <div v-else-if="!stage && !avatar && !realImage" class="reference-artwork__placeholder" data-testid="reference-artwork__placeholder">
      <span class="reference-artwork__placeholder-glyph">{{ glyph }}</span>
      <span class="reference-artwork__placeholder-label">{{ stateLabel }}</span>
    </div>
    <span v-else-if="avatar && !realImage" class="reference-artwork__avatar-glyph" :data-testid="initialTestId ?? 'reference-artwork__placeholder'" aria-hidden="true">{{ glyph }}</span>
    <figcaption v-if="stage" class="reference-artwork__stage-caption">{{ name }}{{ name && stateLabel ? "，" : "" }}{{ stateLabel }}</figcaption>
    <!-- A framed portrait captions only a shown image; a placeholder's label
         is already its one visible state line, and an avatar carries none. -->
    <figcaption v-else-if="realImage && !avatar">{{ name || "角色肖像" }}</figcaption>
    <ArtworkFailure :kind="failureKind" :reason="failureReason" />
  </figure>
</template>

<style>
.reference-artwork {
  position: relative;
  margin: 0;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  pointer-events: none;
}
.reference-artwork .reference-artwork__figure {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
  mask-image: linear-gradient(to bottom, #000 78%, transparent 100%);
}
/* The terminal probe is never painted: its only job is to carry the load or
   error signal for the alpha mask, which then paints the shape itself. */
.reference-artwork__figure--probe {
  visibility: hidden;
}
.reference-artwork__placeholder {
  position: absolute;
  inset: 0;
  display: grid;
  place-content: center;
  gap: calc(6px * var(--ui-scale));
  background: linear-gradient(160deg, #1a1d20, #101214);
  mask-image: linear-gradient(to bottom, #000 78%, transparent 100%);
}
.reference-artwork__placeholder-glyph {
  color: var(--gold-600, #8a6d3b);
  font-family: var(--f-serif, serif);
  font-size: var(--text-initial);
  text-align: center;
}
.reference-artwork__placeholder-label {
  color: var(--paper-400, #9a958c);
  font-size: var(--text-xs);
  letter-spacing: .08em;
  text-align: center;
}
.reference-artwork figcaption {
  position: absolute;
  bottom: calc(18px * var(--ui-scale));
  left: calc(16px * var(--ui-scale));
  right: calc(16px * var(--ui-scale));
  color: var(--paper-300);
  font-size: var(--text-xs);
  letter-spacing: .08em;
  text-align: center;
  text-shadow: 0 1px calc(4px * var(--ui-scale)) #000;
}
/* A reached fault (or a panel-availability failure) is a persistent, locally
   accessible marker: it stacks over the figure band and never becomes a
   rectangular fill standing in for the artwork. */
.reference-artwork > .artwork-failure {
  position: absolute;
  right: calc(4px * var(--ui-scale));
  bottom: calc(4px * var(--ui-scale));
  left: calc(4px * var(--ui-scale));
  z-index: 1;
}
.reference-artwork--stage { height: 100%; overflow: visible; }
.reference-artwork--stage .reference-artwork__figure {
  --stage-scale: 1;
  --stage-x: 0;
  --stage-y: 0;
  transform: translate(calc(var(--stage-x) * 100%), calc(var(--stage-y) * 100%)) scale(var(--stage-scale));
  transform-origin: 50% 100%;
  object-fit: contain;
  mask-image: none;
  filter: drop-shadow(0 calc(5px * var(--ui-scale)) calc(9px * var(--ui-scale)) rgba(0, 0, 0, .55));
}
.reference-artwork__ground {
  position: absolute;
  bottom: -1%;
  left: 14%;
  width: 72%;
  height: 5%;
  border-radius: 50%;
  background: radial-gradient(ellipse, rgba(3, 3, 7, .75), transparent 70%);
}
.reference-artwork__silhouette { position: absolute; inset: 0; }
.reference-artwork__silhouette > .artwork-alpha { position: absolute; inset: 0; }
.reference-artwork__chest {
  position: absolute;
  top: 32%;
  left: var(--actor-label-left, 18%);
  right: 12%;
  display: grid;
  gap: calc(5px * var(--ui-scale));
  text-align: center;
  overflow-wrap: anywhere;
  color: var(--paper-100);
  text-shadow: 0 1px calc(4px * var(--ui-scale)) #000;
}
.reference-artwork__identity { font-size: var(--text-md); }
.reference-artwork__chest .reference-artwork__placeholder-glyph { font-size: var(--text-initial); }
.reference-artwork__chest .reference-artwork__placeholder-label { color: var(--paper-300); }
.reference-artwork--stage .reference-artwork__stage-caption {
  position: absolute;
  width: 1px; height: 1px;
  padding: 0; margin: -1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}
.reference-artwork--stage[data-status="pending"][data-motion="full"] .reference-artwork__silhouette {
  animation: actor-pending var(--motion-pending) ease-in-out infinite;
}
@keyframes actor-pending { 50% { opacity: .55; } }
@media (prefers-reduced-motion: reduce) {
  :root:not([data-motion]) .reference-artwork--stage[data-status="pending"][data-motion="full"] .reference-artwork__silhouette { animation: none; }
}

/* The avatar position: a square real-only crop with the identity glyph as its
   only fallback — no caption, no fade mask, no silhouette. */
.reference-artwork--avatar {
  width: 100%;
  height: 100%;
}
.reference-artwork--avatar .reference-artwork__figure {
  position: absolute;
  top: 0;
  mask-image: none;
}
.reference-artwork--avatar .reference-artwork__avatar-glyph {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: var(--paper-300);
  font-family: var(--f-serif, serif);
  font-size: var(--text-sm);
}
</style>
