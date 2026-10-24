<script setup>
// WorldHatchPattern: the one definition of the world map's unlit hatching
// (an 8 x 8 user-space tile rotated 45 degrees, with its hatch line and the
// line's paint). The world map and the map drawer's world legend each place
// it in their own <defs> under their own unique `id`, and fill with
// `url(#id)`; neither declares the pattern geometry itself.
defineProps({
  id: { type: String, required: true },
});
</script>

<template>
  <pattern :id="id" patternUnits="userSpaceOnUse" width="8" height="8" patternTransform="rotate(45)">
    <line class="world-map__hatch-line" x1="0" y1="0" x2="0" y2="8" />
  </pattern>
</template>

<style scoped>
.world-map__hatch-line { stroke: #8a7f68; stroke-width: 1.1; stroke-opacity: 0.34; }
</style>
