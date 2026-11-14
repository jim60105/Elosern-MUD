<script setup>
// MapColumnStack (design prototype, reference only): the stage's `map`
// anchor as the live client lays it out, a right-hand column that stacks its
// islands top-down. It paints nothing: each island carries its own
// instrument chrome (instrument-panel.css), because the place, the minimap
// and the objective share a position, not a subject. The column only owns
// the reveal, which drops out of the top edge it is anchored to.
import "./instrument-panel.css";

defineProps({
  visible: { type: Boolean, default: true },
  motionLevel: { type: String, default: "full" },
});
</script>

<template>
  <Transition name="icp-reveal" :css="motionLevel !== 'off'">
    <div v-show="visible" class="icp-column" data-testid="map-column">
      <slot />
    </div>
  </Transition>
</template>

<style scoped>
.icp-column {
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  /* Clear air between instruments: the feathered grounds never touch. */
  gap: calc(10px * var(--ui-scale));
  width: 100%;
  min-width: 0;
  color: var(--paper-100);
  font-family: var(--f-sans);
}

/* The reveal: a top-anchored column drops out of its anchored edge. */
.icp-reveal-enter-active {
  transition:
    opacity var(--motion-reveal) var(--ease-enter),
    transform var(--motion-reveal) var(--ease-enter);
}
.icp-reveal-leave-active {
  transition:
    opacity var(--motion-reveal) var(--ease-exit),
    transform var(--motion-reveal) var(--ease-exit);
}
.icp-reveal-enter-from,
.icp-reveal-leave-to {
  opacity: 0;
  transform: translateY(calc(-1 * var(--motion-shift-sm) * var(--motion-travel)));
}
</style>
