<script setup>
// The landmark event card (prototype): standing on a district landmark. The
// scene illustration, the name, the district it lights, and its prose.
// Enter or Esc continues.
import { onMounted, ref } from "vue";

defineProps({
  landmark: { type: Object, required: true },
  litDistrict: { type: String, default: null },
});
const emit = defineEmits(["done"]);
const card = ref(null);

function onKey(event) {
  if (event.key === "Enter" || event.key === " " || event.key === "Escape") {
    event.preventDefault();
    emit("done");
  }
}

onMounted(() => card.value?.focus({ preventScroll: true }));
</script>

<template>
  <section ref="card" class="choice-card landmark-card" tabindex="-1" role="dialog" :aria-label="landmark.name" @keydown="onKey">
    <div class="landmark-card__art" :style="{ backgroundImage: `url(${landmark.art})` }">
      <p class="landmark-card__kicker">抵達地標</p>
    </div>
    <div class="landmark-card__body">
      <h2 class="landmark-card__title">{{ landmark.name }}</h2>
      <p v-if="litDistrict" class="landmark-card__lit"><span aria-hidden="true">◆</span> {{ litDistrict }}已探明</p>
      <p class="landmark-card__prose">{{ landmark.prose }}</p>
      <button type="button" class="leg-btn leg-btn--primary landmark-card__go" @click="emit('done')">繼續 <kbd>Enter</kbd></button>
    </div>
  </section>
</template>

<style>
.landmark-card {
  overflow: hidden auto;
  padding: 0;
}
.landmark-card__art {
  position: relative;
  aspect-ratio: 16 / 6;
  flex: none;
  background-size: cover;
  background-position: center 40%;
}
.landmark-card__art::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(12, 13, 17, 0) 40%, rgba(12, 13, 17, 0.96));
}
.landmark-card__kicker {
  position: absolute;
  left: calc(22px * var(--ui-scale));
  top: calc(16px * var(--ui-scale));
  z-index: 1;
  margin: 0;
  font: var(--text-xs)/1 var(--f-sans);
  letter-spacing: 0.3em;
  color: var(--gold-300);
  text-shadow: 0 1px 4px #000;
}
.landmark-card__body {
  display: grid;
  gap: calc(8px * var(--ui-scale));
  padding: 0 calc(24px * var(--ui-scale)) calc(20px * var(--ui-scale));
  margin-top: calc(-34px * var(--ui-scale));
  position: relative;
}
.landmark-card__title {
  margin: 0;
  font: var(--text-3xl)/1.2 var(--f-display);
  color: var(--paper-50);
  text-shadow: 0 2px 8px #000;
}
.landmark-card__lit {
  margin: 0;
  font: var(--text-sm)/1.3 var(--f-sans);
  color: var(--gold-400);
  letter-spacing: 0.08em;
}
.landmark-card__prose {
  margin: 0;
  font: var(--text-md)/var(--lh-narrative) var(--f-serif);
  color: var(--paper-200);
}
.landmark-card__go {
  justify-self: end;
  min-width: calc(160px * var(--ui-scale));
}
</style>
