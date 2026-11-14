<script setup>
// LocalMapInstrument (design prototype, reference only): the live LocalMap
// as its own instrument panel (instrument-panel.css). The minimap is a
// bounded drawing, so only its card goes (fill, border, radius, shadow,
// padding); the canvas keeps its ink ground and its four gold corner
// brackets, which already are hairline gold.
//
// The canvas stands clear of the spine (22px of right padding, the spine at
// 14px), so the brass line runs unbroken from the lozenge down past the
// footer. The ink ground holds solid under the whole canvas and title /
// footer width (240px + 22px from the right) and feathers out in a short
// 24px band to its left, so the opaque canvas never sits on thinned ink.
// That needs a column at least 282px wide; MapColumnPrototype widens the
// `map` column to it where the live column (right-column - 28px) is
// narrower, as at 1280x720.
//
// The renderer-axis legend (北↑ 東→) is not drawn: the minimap never
// rotates, so the legend carries no information.
//
// Behaviour, payload and events are the live component's own.
import LocalMap from "../../../web/webclient-app/components/LocalMap.vue";
import "./instrument-panel.css";

defineProps({
  localMap: { type: Object, required: true },
  motionLevel: { type: String, default: "full" },
});
defineEmits(["move", "open-map"]);
</script>

<template>
  <div class="icp-panel icp-map-panel">
    <LocalMap
      class="icp-map"
      :local-map="localMap"
      :motion-level="motionLevel"
      @move="$emit('move', $event)"
      @open-map="$emit('open-map', $event)"
    />
  </div>
</template>

<style scoped>
.icp-map-panel {
  --icp-pad-right: 22px;
  --icp-solid: calc(262px * var(--ui-scale));
  --icp-clear: calc(286px * var(--ui-scale));
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}
.icp-map.local-map {
  padding: 0;
  background: none;
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
  border: 0;
  border-radius: 0;
  box-shadow: none;
}
.icp-map.local-map :deep(.local-map__affordance) {
  border-radius: 0;
}
.icp-map.local-map :deep(.local-map__meta),
.icp-map.local-map :deep(.local-map__footer) {
  text-shadow: 0 1px 1px rgba(0, 0, 0, 0.8);
}
.icp-map.local-map :deep(.local-map__footer) {
  padding-inline: 0;
}
/* The minimap never rotates: the axis legend states nothing. */
.icp-map.local-map :deep(.local-map__orientation) {
  display: none;
}
/* The open-map glyph answers the hover the border used to answer. */
.icp-map.local-map :deep(.local-map__expand-icon) {
  opacity: 0.86;
  transition: opacity var(--motion-fast) var(--ease-standard);
}
.icp-map.local-map:hover :deep(.local-map__expand-icon),
.icp-map.local-map:focus-within :deep(.local-map__expand-icon) {
  opacity: 1;
}
</style>
