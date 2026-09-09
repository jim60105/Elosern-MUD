<script setup>
// ReferenceArtwork renders the committed stage portrait truthfully: the
// resolved gallery payload's URL with its face-rect crop offset, or a
// truthful placeholder when no image exists (pending generation, load
// failure). Bundled sample artwork is retired: the gallery resolution
// chain guarantees real imagery for registered subjects, and anything
// else must not be masked with decorative stand-ins.
import { computed, ref } from "vue";
import { faceObjectPosition } from "./face-rect.js";

const props = defineProps({
  portrait: { type: Object, default: null },
});
const failedUrl = ref(null);
const portraitUrl = computed(() => {
  const url = props.portrait?.url;
  return url && url !== failedUrl.value ? url : null;
});
const placeholderLabel = computed(() => props.portrait?.placeholder?.label || "肖像生成中");
function onImageError() {
  if (portraitUrl.value) failedUrl.value = portraitUrl.value;
}
</script>

<template>
  <figure class="reference-artwork" data-testid="reference-artwork">
    <img
      v-if="portraitUrl"
      :src="portraitUrl"
      :style="{ objectPosition: faceObjectPosition(portrait.face_rect) }"
      alt=""
      aria-hidden="true"
      @error="onImageError"
    />
    <div v-else class="reference-artwork__placeholder" data-testid="reference-artwork__placeholder">
      <span class="reference-artwork__placeholder-glyph">{{ placeholderLabel.slice(0, 1) }}</span>
      <span class="reference-artwork__placeholder-label">{{ placeholderLabel }}</span>
    </div>
    <figcaption :data-sample="String(!portraitUrl)">{{ portraitUrl ? (portrait.alt || "角色肖像") : placeholderLabel }}</figcaption>
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
  gap: 6px;
  background: linear-gradient(160deg, #1a1d20, #101214);
  mask-image: linear-gradient(to bottom, #000 78%, transparent 100%);
}
.reference-artwork__placeholder-glyph {
  color: var(--gold-600, #8a6d3b);
  font-family: var(--f-serif, serif);
  font-size: 42px;
  text-align: center;
}
.reference-artwork__placeholder-label {
  color: var(--paper-400, #9a958c);
  font-size: 11px;
  letter-spacing: .08em;
  text-align: center;
}
.reference-artwork figcaption {
  position: absolute;
  bottom: 18px;
  left: 16px;
  right: 16px;
  color: var(--paper-300);
  font-size: 11px;
  letter-spacing: .08em;
  text-align: center;
  text-shadow: 0 1px 4px #000;
}
</style>
