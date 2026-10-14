<script setup>
// ArtworkFailure — the shared local failure/loading indicator for one image
// position (change unified-image-loading-core).
//
// It is a presentation primitive only: it consumes a closed reason code and a
// kind, never a raw exception/path/prompt, and it renders a persistent
// non-modal explanation through the shared bounded category mapping. A reached
// failure keeps its error marker even after a lower source succeeds; expected
// absence and in-progress loading carry no error styling (and expected absence
// renders nothing at all).
import { computed } from "vue";
import { artworkFailureCategory, isArtworkAvailabilityFailure } from "../lib/artwork-failure.js";

const props = defineProps({
  // "failure" (a reached fault), "loading" (in progress), "expected" (a
  // deliberate absence) or null (nothing to say).
  kind: { type: String, default: null },
  // One code from the closed artwork reason vocabulary.
  reason: { type: String, default: null },
});

const failure = computed(() => props.kind === "failure" && !!props.reason);
const text = computed(() => artworkFailureCategory(props.reason));
const availability = computed(() => isArtworkAvailabilityFailure(props.reason));
</script>

<template>
  <p
    v-if="failure"
    class="artwork-failure"
    :class="{ 'artwork-failure--availability': availability }"
    role="status"
    data-testid="artwork-failure"
  >
    <span class="artwork-failure__mark" aria-hidden="true">⚠</span>
    <span class="artwork-failure__text">{{ text }}</span>
  </p>
  <p
    v-else-if="kind === 'loading'"
    class="artwork-failure artwork-failure--loading"
    role="status"
    data-testid="artwork-loading"
  >
    <span class="artwork-failure__text">圖片載入中…</span>
  </p>
</template>

<style scoped>
.artwork-failure {
  display: flex;
  align-items: center;
  gap: calc(6px * var(--ui-scale));
  margin: 0;
  padding: calc(8px * var(--ui-scale)) calc(10px * var(--ui-scale));
  border: 1px solid #ed7e8255;
  border-radius: var(--radius-sm);
  background: #2a1a1ecc;
  color: #f3b9bc;
  font-size: var(--text-xs);
  text-align: left;
}
.artwork-failure__mark { flex: none; }
.artwork-failure--loading {
  border-color: #a5967755;
  background: #1a1c24cc;
  color: var(--paper-400, #9a958c);
}
/* An availability failure is a panel-level fact, not a broken image: it keeps
   its own bounded text and never borrows the per-image error styling. */
.artwork-failure--availability {
  border-color: #a5967755;
  background: #1a1c24cc;
  color: var(--paper-300);
}
</style>
