<script setup>
// MapCommissionGlyph: the area map's one commission diamond (委託目的地),
// drawn by the area map's point nodes, its wilderness cells and the map
// drawer's area legend alike. One <g> root; `size` is the surface's uniform
// scale, applied to the whole group so the stroke scales with the shape.
// The host positions it (a translate around the component).
defineOptions({ inheritAttrs: false });

defineProps({
  size: { type: Number, default: 1 },
});
</script>

<template>
  <g class="map-commission" :transform="size === 1 ? null : `scale(${size})`">
    <path class="area-map__quest" d="M0 -7.5 L5.5 0 L0 7.5 L-5.5 0 Z" aria-hidden="true" />
  </g>
</template>

<style scoped>
.area-map__quest { fill: var(--seal-500); stroke: #fff2e6; stroke-width: 1.3; stroke-linejoin: round; }
</style>
