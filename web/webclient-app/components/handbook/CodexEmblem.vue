<script setup>
// CodexEmblem (handbook-primitives, design D3): one stroked emblem in the
// dock-icons.js 24-unit style, drawn from the `emblem_<name>` glyph. It is a
// medal face, a ribbon glyph and the hero fallback. A name without a glyph
// falls back to `emblem_unknown`. Always decorative (aria-hidden) beside the
// text that names the entry.
import { computed } from "vue";
import { glyphAttrs, glyphPath } from "../dock-icons.js";

const props = defineProps({
  name: { type: String, default: null },
  strokeWidth: { type: Number, default: 1.6 },
});

const glyphKey = computed(() => {
  const key = `emblem_${props.name}`;
  return glyphPath(key) ? key : "emblem_unknown";
});
</script>

<template>
  <svg class="codex-emblem" viewBox="0 0 24 24" fill="none" aria-hidden="true" :data-emblem="glyphKey">
    <path :d="glyphPath(glyphKey)" stroke="currentColor" :stroke-width="strokeWidth" v-bind="glyphAttrs(glyphKey)" />
  </svg>
</template>

<style scoped>
.codex-emblem {
  display: block;
  width: 100%;
  height: 100%;
}
</style>
