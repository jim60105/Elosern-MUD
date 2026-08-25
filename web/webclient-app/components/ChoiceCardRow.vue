<script setup>
// ChoiceCardRow (B2 action family): the row of OptionCards for one
// suggestion set — the choice-card frame shared by the dock suggestions
// section and the narrative choice-point (one card renderer, so size,
// labels, and click paths cannot diverge). Pure presentation: renders the
// exact server-authored `cards` slice and re-emits each card's `action`
// intent untouched.
import OptionCard from "./OptionCard.vue";

defineProps({
  cards: { type: Array, required: true },
});

const emit = defineEmits(["action"]);
</script>

<template>
  <div
    class="choice-card-row"
    role="group"
    aria-label="建議動作"
    data-testid="choice-card-row"
  >
    <OptionCard
      v-for="(card, index) in cards"
      :key="index"
      :card="card"
      @action="(intent) => emit('action', intent)"
    />
  </div>
</template>

<style scoped>
/* H3 (task 5.7): the draft's `.sugs` grid — auto-fill cards, so the
   choice-card frame and the dock suggestions pane share the identical card
   renderer (one card renderer, no divergence). */
.choice-card-row {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
  gap: 10px;
}
</style>
