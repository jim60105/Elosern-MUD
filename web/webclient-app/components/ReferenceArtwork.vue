<script setup>
// Bundled style samples are decorative, never an authoritative art payload.
import { computed, ref } from "vue";
import adventurer from "../assets/redesign/sample-adventurer.webp";
import clerk from "../assets/redesign/sample-clerk.webp";
import wolf from "../assets/redesign/sample-wolf.webp";

const props = defineProps({
  subject: { type: String, default: "adventurer" },
  portrait: { type: Object, default: null },
});
const images = { adventurer, clerk, wolf };
const failedUrl = ref(null);
const portraitUrl = computed(() => {
  const url = props.portrait?.url;
  return url && url !== failedUrl.value ? url : null;
});

function onImageError() {
  if (portraitUrl.value) failedUrl.value = portraitUrl.value;
}
</script>

<template>
  <figure class="reference-artwork" data-testid="reference-artwork">
    <img :src="portraitUrl || images[subject] || adventurer" alt="" aria-hidden="true" @error="onImageError" />
    <figcaption :data-sample="String(!portraitUrl)">{{ portraitUrl ? (portrait.alt || "角色肖像") : "範例美術 · 非目前對象的實際肖像" }}</figcaption>
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
  object-position: center 18%;
  mask-image: linear-gradient(to bottom, #000 78%, transparent 100%);
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
