<script setup>
// TravelGlyph (OpenSpec change wilderness-travel-map-ui): the one painted
// source of the travel stage's own map concepts — the landmark ornament, the
// eight neighbour targets, a live-sight hostile and the route step marks.
// The party seal is MapNodeGlyph's "party" state. One <g> root, base-unit
// geometry from lib/map_glyphs.js `TRAVEL_GLYPHS`, scaled as a whole by
// `size` (strokes and dashes included), so every consumer differs only by
// that uniform scale. Each state differs by shape as well as colour.
import { TRAVEL_GLYPHS as G } from "../../lib/map_glyphs.js";

defineOptions({ inheritAttrs: false });

defineProps({
  // "landmark" | "neighbour" | "hostile" | "route"
  kind: { type: String, required: true },
  // neighbour: "open" | "aimed" | "blocked" | "unknown";
  // route: "normal" | "light" | "moderate" | "severe".
  state: { type: String, default: null },
  size: { type: Number, default: 1 },
  testId: { type: String, default: null },
});

const diamond = (h) => `M0 ${-h} L${h} 0 L0 ${h} L${-h} 0 Z`;
const chevron = (c) => `M${-c} ${c * 0.78} L0 ${-c} L${c} ${c * 0.78}`;
</script>

<template>
  <g
    class="travel-glyph"
    :class="[`travel-glyph--${kind}`, state ? `is-${state}` : null]"
    :data-testid="testId"
    :data-glyph="kind"
    :data-state="state"
    :transform="size === 1 ? null : `scale(${size})`"
    aria-hidden="true"
  >
    <template v-if="kind === 'landmark'">
      <path class="travel-glyph__diamond" :d="diamond(G.landmark.half)" :stroke-width="G.landmark.stroke" />
      <circle class="travel-glyph__dot" :r="G.landmark.dotR" />
    </template>
    <template v-else-if="kind === 'neighbour'">
      <circle
        class="travel-glyph__target"
        :r="state === 'aimed' ? G.neighbour.aimedR : state === 'unknown' ? G.neighbour.unknownR : G.neighbour.openR"
      />
    </template>
    <template v-else-if="kind === 'hostile'">
      <circle class="travel-glyph__halo" :r="G.hostile.haloR" />
      <circle class="travel-glyph__seal" :r="G.hostile.sealR" />
      <path class="travel-glyph__chevron" :d="chevron(G.hostile.chevron)" />
    </template>
    <template v-else-if="kind === 'route'">
      <circle v-if="state === 'normal'" class="travel-glyph__step" :r="G.route.dotR" />
      <path v-else-if="state === 'light'" class="travel-glyph__step" :d="diamond(G.route.diamond)" />
      <template v-else>
        <circle class="travel-glyph__ring" :r="G.route.ringR" />
        <circle v-if="state === 'severe'" class="travel-glyph__core" :r="G.route.innerR" />
      </template>
    </template>
  </g>
</template>

<style scoped>
.travel-glyph__diamond { fill: #0f0c12; stroke: var(--gold-400); stroke-linejoin: miter; }
.travel-glyph__dot { fill: var(--gold-400); }

.travel-glyph__target { fill: #0f0c12; stroke: var(--gold-400); stroke-width: 1.2; }
.travel-glyph--neighbour.is-aimed .travel-glyph__target { fill: var(--gold-400); stroke: var(--gold-300); stroke-width: 1.4; }
.travel-glyph--neighbour.is-blocked .travel-glyph__target { fill: none; stroke: var(--paper-500); stroke-dasharray: 2 2; }
.travel-glyph--neighbour.is-unknown .travel-glyph__target { fill: none; stroke: rgba(201, 196, 185, 0.45); stroke-width: 1; stroke-dasharray: 1 2.2; }

.travel-glyph__halo { fill: rgba(207, 68, 68, 0.22); stroke: none; }
.travel-glyph__seal { fill: #2a1416; stroke: var(--seal-500); stroke-width: 1.8; }
.travel-glyph__chevron { fill: none; stroke: var(--seal-light); stroke-width: 1.8; stroke-linejoin: round; stroke-linecap: round; }

.travel-glyph--route.is-normal .travel-glyph__step { fill: var(--gold-400); }
.travel-glyph--route.is-light .travel-glyph__step { fill: var(--warn); }
.travel-glyph__ring { fill: none; stroke: #d0705a; stroke-width: 2; }
.travel-glyph__core { fill: #d0705a; }
</style>
