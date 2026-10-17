<script setup>
// Approved visual prototype (party member management). A decorative 24x24
// stroke glyph; the surrounding control carries the accessible name.
import { computed } from "vue";
import { pathFor } from "./glyphs.js";

const props = defineProps({ name: { type: String, required: true } });
const d = computed(() => pathFor(props.name));
</script>

<template>
  <svg v-if="d" class="pm-glyph" viewBox="0 0 24 24" aria-hidden="true"><path :d="d" /></svg>
</template>

<style scoped>
.pm-glyph {
  width: 1em;
  height: 1em;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.6;
  stroke-linecap: round;
  stroke-linejoin: round;
  flex: none;
}
</style>
