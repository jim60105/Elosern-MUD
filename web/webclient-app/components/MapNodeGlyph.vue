<script setup>
// MapNodeGlyph: the one painted node glyph of every map. The area map, the
// minimap island and the map drawer's legend all draw it, so 目前位置, a
// visited or seen place, a neighbour one road away and a gate read the same
// wherever they appear. One <g> root (place it inside a translated <g> or a
// legend <svg>); geometry comes from lib/map_marker_geometry.js.
//
// `size` is the surface's uniform scale: it lands on the root group as
// `scale(size)` around base-unit shapes, so radii, stroke widths and dash
// patterns all scale together. No shape opts out with a vector effect.
//
// The current glyph wins over a gate, and the travel halo sits under either.
// `markerClass` lands on the state's primary shape (the here ring, the gate or
// the dot), so a host can name the one element that stands for the node;
// `haloClass` lands on the travel halo, and `testIds` ({ marker, halo }) names
// the same two shapes for a host's tests.
import {
  HERE_GLOW_R,
  HERE_RING_R,
  HERE_DOT_R,
  NODE_DOT_R,
  HALO_R,
  gatePath,
} from "../lib/map_marker_geometry.js";

defineOptions({ inheritAttrs: false });

defineProps({
  // "current", "visited" or "seen".
  state: { type: String, required: true },
  gate: { type: Boolean, default: false },
  travel: { type: Boolean, default: false },
  selected: { type: Boolean, default: false },
  size: { type: Number, default: 1 },
  markerClass: { type: [String, Array, Object], default: null },
  haloClass: { type: [String, Array, Object], default: null },
  testIds: { type: Object, default: () => ({}) },
});
</script>

<template>
  <g class="map-glyph" :transform="size === 1 ? null : `scale(${size})`">
    <circle v-if="travel" class="map-glyph__halo" :class="haloClass" :data-testid="testIds.halo" :r="HALO_R" aria-hidden="true" />
    <template v-if="state === 'current'">
      <circle class="map-glyph__here-glow" :r="HERE_GLOW_R" aria-hidden="true" />
      <circle class="map-glyph__here-ring" :class="markerClass" :data-testid="testIds.marker" :r="HERE_RING_R" aria-hidden="true" />
      <circle class="map-glyph__here-dot" :r="HERE_DOT_R" aria-hidden="true" />
    </template>
    <path
      v-else-if="gate"
      class="map-glyph__gate"
      :class="[markerClass, { 'is-seen': state === 'seen', 'is-selected': selected }]"
      :data-testid="testIds.marker"
      :d="gatePath()"
      aria-hidden="true"
    />
    <circle
      v-else
      class="map-glyph__dot"
      :class="[markerClass, { 'is-seen': state === 'seen', 'is-selected': selected }]"
      :data-testid="testIds.marker"
      :r="NODE_DOT_R"
      aria-hidden="true"
    />
  </g>
</template>

<style scoped>
.map-glyph__halo {
  fill: rgba(228, 200, 142, 0.08);
  stroke: var(--gold-500);
  stroke-width: 1.2;
  stroke-dasharray: 3 3;
}
.map-glyph__here-glow {
  fill: rgba(165, 44, 49, 0.22);
  stroke: none;
  transform-box: fill-box;
  transform-origin: center;
  animation: map-glyph-here-breathe var(--motion-pulse) ease-in-out infinite;
}
@keyframes map-glyph-here-breathe {
  0%, 100% { opacity: 0.55; transform: scale(0.86); }
  50% { opacity: 1; transform: scale(1.18); }
}
@media (prefers-reduced-motion: reduce) {
  .map-glyph__here-glow { animation: none; }
}
.map-glyph__here-ring { fill: none; stroke: var(--paper-50); stroke-width: 2; }
.map-glyph__here-dot { fill: var(--seal-deep); stroke: #fff2e6; stroke-width: 1.5; }
.map-glyph__dot { fill: var(--paper-200); stroke: #15130f; stroke-width: 2; }
.map-glyph__dot.is-seen {
  fill: #2b2924;
  stroke: #948b7b;
  stroke-width: 1.6;
  stroke-dasharray: 2.2 2;
}
.map-glyph__gate { fill: #3a342a; stroke: var(--gold-400); stroke-width: 2; stroke-linejoin: round; }
.map-glyph__gate.is-seen { fill: #26231d; stroke: var(--gold-500); }
.map-glyph__gate.is-selected,
.map-glyph__dot.is-selected { stroke: var(--gold-300); stroke-width: 2.6; }
</style>
