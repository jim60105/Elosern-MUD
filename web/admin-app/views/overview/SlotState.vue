<script setup>
// One dashboard slot's three states (gm-portal-s2b-dashboard): skeleton
// before the first snapshot, a compact local error when the slot carries
// `{error}`, otherwise the default slot with the data. A slot error never
// reaches its siblings, and it is not re-announced on every poll.
import { computed } from "vue";
import GmError from "../../components/GmError.vue";
import { slotError } from "../../lib/dashboard.js";

const props = defineProps({
  value: { type: [Object, Array], default: null },
  rows: { type: Number, default: 3 },
});

const error = computed(() => slotError(props.value));
const widths = ["62%", "38%", "74%", "46%", "58%", "30%"];
</script>

<template>
  <div v-if="value == null" class="gm-slot-skeleton" aria-hidden="true">
    <span v-for="row in rows" :key="row" class="gm-skeleton" :style="{ width: widths[(row - 1) % widths.length] }"></span>
  </div>
  <GmError
    v-else-if="error"
    compact
    live="off"
    title="此區塊無法載入"
    :message="error.message"
    :code="error.code"
    data-testid="gm-slot-error"
  />
  <slot v-else :data="value" />
</template>

<style scoped>
.gm-slot-skeleton {
  display: grid;
  gap: var(--sp-3);
  padding: var(--sp-2) 0;
}
</style>
