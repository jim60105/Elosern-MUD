<script setup>
// WorldMapGlyph: the world map's point glyphs, drawn by the world map and by
// the map drawer's world legend alike, so 目前位置, a district landmark, a
// place and an exact commission read the same in both. One <g> root: the
// host places it (the world map in a `translate(..) scale(uiScale)`
// group; the legend inside its sample <svg>). Hit areas stay the host's.
//
// - `here`: the player's breathing seal.
// - `landmark`: a district landmark's gilt spire.
// - `place`: a diamond (`settlement`), the capital's cored diamond, the
//   harbour's round dot, or the hidden place's dashed diamond (`placeKind`).
// - `quest`: the commission pin with its eye, haloed when `tracked`.
//
// Every stroke scales with the host's uniform scale (the world map's
// `scale(uiScale)`, the legend's viewBox): no shape opts out with a vector
// effect, and the host's own `.world-map__layer path, circle` rule reaches only
// this root <g>, never the shapes inside it.
defineProps({
  kind: { type: String, required: true },
  placeKind: { type: String, default: "settlement" },
  tracked: { type: Boolean, default: false },
});
</script>

<template>
  <g class="world-glyph">
    <template v-if="kind === 'here'">
      <circle class="world-map__here-glow" r="14" />
      <circle class="world-map__here-ring" r="10" />
      <circle class="world-map__here-dot" r="5.5" />
    </template>
    <template v-else-if="kind === 'landmark'">
      <path class="world-map__spire" d="M-5 7 L-3.2 -5 L0 -10 L3.2 -5 L5 7 Z" />
      <path class="world-map__spire-light" d="M0 -10 L1.4 -5.6 L0 -2 L-1.4 -5.6 Z" />
    </template>
    <template v-else-if="kind === 'place'">
      <template v-if="placeKind === 'capital'">
        <rect class="world-map__place-glyph" x="-7" y="-7" width="14" height="14" transform="rotate(45)" />
        <rect class="world-map__place-core" x="-2.6" y="-2.6" width="5.2" height="5.2" transform="rotate(45)" />
      </template>
      <circle v-else-if="placeKind === 'harbour'" class="world-map__place-glyph" r="5.5" />
      <rect v-else class="world-map__place-glyph" x="-5" y="-5" width="10" height="10" transform="rotate(45)" />
    </template>
    <template v-else-if="kind === 'quest'">
      <circle v-if="tracked" class="world-map__quest-halo" cy="-5" r="12" />
      <path class="world-map__quest-pin" d="M0 -16 L8.5 -5 L0 6 L-8.5 -5 Z" />
      <circle class="world-map__quest-eye" cy="-5" r="2.4" />
    </template>
  </g>
</template>

<style scoped>
.world-map__spire { fill: var(--gold-400); stroke: #15140f; stroke-width: 1.5; stroke-linejoin: round; }
.world-map__spire-light { fill: #fff3d2; fill-opacity: 0.75; }
.world-map__landmark.is-selected .world-map__spire { stroke: var(--gold-300); stroke-width: 2.4; }
.world-map__place-glyph { fill: #e7e0d1; stroke: #15140f; stroke-width: 2; }
.world-map__place.is-capital .world-map__place-glyph { fill: var(--gold-400); }
.world-map__place-core { fill: #15140f; }
.world-map__place.is-harbour .world-map__place-glyph { fill: #9cc1d2; }
.world-map__place.is-hidden .world-map__place-glyph { fill: #2a2722; stroke: #cfc4ad; stroke-width: 1.4; stroke-dasharray: 2 2; }
.world-map__place.is-selected .world-map__place-glyph { stroke: var(--gold-300); stroke-width: 2.6; stroke-dasharray: none; }

.world-map__quest-halo { fill: rgba(207, 68, 68, 0.18); stroke: rgba(224, 107, 107, 0.6); stroke-width: 1; }
.world-map__quest-pin { fill: var(--seal-500); stroke: #fff2e6; stroke-width: 1.6; stroke-linejoin: round; }
.world-map__quest-eye { fill: #fff2e6; }
.world-map__quest.is-selected .world-map__quest-pin { stroke: var(--gold-300); stroke-width: 2.6; }

.world-map__here-glow {
  fill: rgba(165, 44, 49, 0.24);
  transform-box: fill-box;
  transform-origin: center;
  animation: world-map-here-breathe var(--motion-pulse) ease-in-out infinite;
}
@keyframes world-map-here-breathe {
  0%, 100% { opacity: 0.55; transform: scale(0.86); }
  50% { opacity: 1; transform: scale(1.2); }
}
.world-map__here-ring { fill: none; stroke: #fff2e6; stroke-width: 2; }
.world-map__here-dot { fill: var(--seal-deep); stroke: #fff2e6; stroke-width: 1.5; }
</style>
