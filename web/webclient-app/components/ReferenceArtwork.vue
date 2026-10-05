<script setup>
// ReferenceArtwork renders the committed stage portrait truthfully: the
// resolved gallery payload's URL with its face-rect crop offset, the built-in
// silhouette the server selected for a still-absent portrait, or a truthful
// placeholder when neither exists (pending generation, load failure). The
// silhouette is the committed image's own alpha mask — never its RGB texture
// — filled with the existing dark fill; the server-carried fallback identity
// (portrait.fallback) is the only source for it, and cover-mode surfaces keep
// refusing decorative stand-ins for anything the payload does not carry.
import { computed, ref } from "vue";
import { faceObjectPosition } from "./face-rect.js";
import { portraitGlyph } from "./character-identity.js";

const props = defineProps({
  portrait: { type: Object, default: null },
  // The name whose initial the placeholder draws (StageActor passes the
  // actor's name); without one the placeholder label's initial is drawn.
  initialOf: { type: String, default: "" },
  stage: { type: Boolean, default: false },
  motionLevel: { type: String, default: "full" },
});
const failedUrl = ref(null);
// The bundled mask is a CSS resource: no element event reports its failure,
// so a probe image of the same URL (served from the same cache entry) carries
// the load/error signal for it. A failure keeps the name and the truthful
// text placeholder and renders no figure at all.
const failedMaskUrl = ref(null);
const loadedMaskUrl = ref(null);
const stageVars = computed(() => ({
  "--stage-scale": props.portrait?.stage?.scale ?? 1,
  "--stage-x": props.portrait?.stage?.x ?? 0,
  "--stage-y": props.portrait?.stage?.y ?? 0,
}));
const placementStyle = computed(() => props.stage ? {
  objectPosition: "center bottom",
  ...stageVars.value,
} : { objectPosition: faceObjectPosition(props.portrait?.face_rect) });
const portraitUrl = computed(() => {
  const url = props.portrait?.url;
  return url && url !== failedUrl.value ? url : null;
});
// The silhouette the server resolved: its identity is the payload's
// decorative `fallback` field (see art-gallery-fallback), never the entry's
// own media URL. The fill paints only once the resource is known to load, so
// a failed mask can never leave a solid rectangle standing in for a figure.
const fallbackUrl = computed(() => {
  const url = props.portrait?.fallback?.url;
  return typeof url === "string" && url ? url : null;
});
const maskSource = computed(() => {
  const url = fallbackUrl.value;
  return url && url !== failedMaskUrl.value ? url : null;
});
const maskLoaded = computed(() => !!maskSource.value && loadedMaskUrl.value === maskSource.value);
function onMaskLoad() {
  if (maskSource.value) loadedMaskUrl.value = maskSource.value;
}
function onMaskError() {
  if (maskSource.value) failedMaskUrl.value = maskSource.value;
}
// The drawer frame's one state label (webclient-drawer-content-polish): the
// entry's own placeholder label, else a word derived from what the payload
// says — pending only for a pending entry, never by default.
const placeholderLabel = computed(() => {
  if (props.portrait?.placeholder?.label) return props.portrait.placeholder.label;
  if (props.portrait?.url && props.portrait.url === failedUrl.value) return "肖像載入失敗";
  if (props.portrait?.status === "pending") return "肖像生成中";
  if (props.portrait?.status === "failed") return "肖像生成失敗";
  return "無肖像";
});
const placeholderGlyph = computed(() => portraitGlyph(props.initialOf || placeholderLabel.value));
const stageState = computed(() => {
  if (portraitUrl.value) return "done";
  if (props.portrait?.url === failedUrl.value && failedUrl.value) return "load-failed";
  if (!props.portrait?.status && props.portrait?.placeholder?.kind === "unavailable") return "unavailable";
  return ["pending", "failed"].includes(props.portrait?.status) ? props.portrait.status : "missing";
});
const stageLabel = computed(() => ({
  pending: "肖像生成中", failed: "肖像生成失敗", "load-failed": "肖像載入失敗", missing: "無肖像",
  unavailable: props.portrait?.placeholder?.label || "無法提供",
})[stageState.value] || "");
const stageName = computed(() => props.initialOf || props.portrait?.context?.name || props.portrait?.alt || "");
function onImageError() {
  if (portraitUrl.value) failedUrl.value = portraitUrl.value;
}
</script>

<template>
  <figure class="reference-artwork" :class="{ 'reference-artwork--stage': stage }"
    :data-status="stage ? stageState : null" :data-motion="stage ? motionLevel : null"
    data-testid="reference-artwork">
    <span v-if="stage" class="reference-artwork__ground" aria-hidden="true"></span>
    <img
      v-if="portraitUrl"
      :src="portraitUrl"
      :style="placementStyle"
      alt=""
      aria-hidden="true"
      @error="onImageError"
    />
    <div v-else-if="stage" class="reference-artwork__silhouette" data-testid="reference-artwork__placeholder" aria-hidden="true">
      <!-- The server-selected built-in silhouette: the committed image's own
           alpha mask, dark-filled and floor-aligned. The probe image shares
           the mask's URL, so the frame learns about a missing bundled
           resource and keeps the name and the truthful label instead. -->
      <div v-if="maskSource" class="reference-artwork__mask" data-testid="reference-artwork__mask" aria-hidden="true" :style="stageVars">
        <span v-if="maskLoaded" class="reference-artwork__mask-fill" :style="{ '--silhouette-mask': `url('${maskSource}')` }"></span>
        <img class="reference-artwork__mask-probe" :src="maskSource" alt="" aria-hidden="true" @load="onMaskLoad" @error="onMaskError" />
      </div>
      <!-- No built-in identity is carried (e.g. a roster portrait): the
           grounded standing silhouette stands unchanged. A failed bundled
           mask leaves the name and the truthful text label alone. -->
      <svg v-else-if="!fallbackUrl" viewBox="0 0 240 360" preserveAspectRatio="none" aria-hidden="true" focusable="false">
        <path d="M120 8c-19 0-30 15-30 34 0 17 8 29 16 34l-4 14-33 13c-13 7-20 25-23 44L30 239l19 5 24-81-1 89-9 106h47l10-91 10 91h47l-9-106-1-89 24 81 19-5-16-92c-3-19-10-37-23-44l-33-13-4-14c8-5 16-17 16-34 0-19-11-34-30-34Z" />
      </svg>
      <div class="reference-artwork__chest">
        <span class="reference-artwork__placeholder-glyph">{{ portraitGlyph(stageName) }}</span>
        <span class="reference-artwork__identity">{{ stageName }}</span>
        <span class="reference-artwork__placeholder-label">{{ stageLabel }}</span>
      </div>
    </div>
    <div v-else class="reference-artwork__placeholder" data-testid="reference-artwork__placeholder">
      <span class="reference-artwork__placeholder-glyph">{{ placeholderGlyph }}</span>
      <span class="reference-artwork__placeholder-label">{{ placeholderLabel }}</span>
    </div>
    <figcaption v-if="stage" class="reference-artwork__stage-caption">{{ stageName }}{{ stageName && stageLabel ? "，" : "" }}{{ stageLabel }}</figcaption>
    <!-- The drawer frame captions only a shown image; a placeholder's label
         is already its one visible state line. -->
    <figcaption v-else-if="portraitUrl">{{ portrait.alt || "角色肖像" }}</figcaption>
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
.reference-artwork img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
  mask-image: linear-gradient(to bottom, #000 78%, transparent 100%);
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
.reference-artwork--stage { height: 100%; overflow: visible; }
.reference-artwork--stage img {
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
.reference-artwork__silhouette svg {
  width: 100%; height: 100%;
  fill: #17191f;
  stroke: rgba(185, 154, 96, .3);
  stroke-width: 1;
  filter: drop-shadow(0 calc(3px * var(--ui-scale)) calc(7px * var(--ui-scale)) #07070b);
}
/* The server-selected built-in silhouette: the committed image's own alpha
   mask over the existing dark fill, using the stage editor's mask idiom
   (mask + -webkit-mask, contain, bottom center). mask-mode is named
   explicitly: coverage comes from the image's alpha channel, never from its
   RGB. The fill paints only once the probe has loaded it, so a missing
   bundled resource can never stand as a solid rectangle. */
.reference-artwork__mask {
  --stage-scale: 1;
  --stage-x: 0;
  --stage-y: 0;
  position: absolute;
  inset: 0;
  transform: translate(calc(var(--stage-x) * 100%), calc(var(--stage-y) * 100%)) scale(var(--stage-scale));
  transform-origin: 50% 100%;
  filter: drop-shadow(0 calc(3px * var(--ui-scale)) calc(7px * var(--ui-scale)) #07070b);
}
.reference-artwork__mask-fill {
  /* The committed built-in identity the inline binding supplies. Its default
     is a fully transparent 1×1 mask, so the fill can never paint an unmasked
     rectangle: without a resolved identity the element paints nothing. */
  --silhouette-mask: url("data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7");
  position: absolute;
  inset: 0;
  background: #17191f;
  mask: var(--silhouette-mask) bottom center / contain no-repeat;
  -webkit-mask: var(--silhouette-mask) bottom center / contain no-repeat;
  mask-mode: alpha;
}
/* The load/error probe for the mask resource: an image of the same URL, never
   painted, so the figure keeps one request and one cache entry. */
.reference-artwork__mask-probe {
  position: absolute;
  width: 1px;
  height: 1px;
  opacity: 0;
  pointer-events: none;
}
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
.reference-artwork--stage[data-status="pending"][data-motion="full"] .reference-artwork__mask,
.reference-artwork--stage[data-status="pending"][data-motion="full"] .reference-artwork__silhouette svg {
  animation: actor-pending var(--motion-pending) ease-in-out infinite;
}
@keyframes actor-pending { 50% { opacity: .55; } }
@media (prefers-reduced-motion: reduce) {
  :root:not([data-motion]) .reference-artwork--stage[data-status="pending"][data-motion="full"] .reference-artwork__mask,
  :root:not([data-motion]) .reference-artwork--stage[data-status="pending"][data-motion="full"] .reference-artwork__silhouette svg { animation: none; }
}
</style>
