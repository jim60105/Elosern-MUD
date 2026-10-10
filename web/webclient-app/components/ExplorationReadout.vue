<script setup>
// ExplorationReadout (exploration-exit-compass design D4; scene overview
// redesign §5.3): the exploration command panel's single explanation line —
// a polite live region with a gold left rule, a small lead line, and one to
// two lines of text. It renders what the pane's priority helper
// (`exploration-readout.js`) chose: a blocked-move flash (warn tone), the
// compass aim, or the idle summary (quiet tone). At the `off` motion level
// the flash is a static seal-red rule with no animation.
defineProps({
  lead: { type: String, default: "" },
  text: { type: String, default: "" },
  // normal | warn | quiet
  tone: { type: String, default: "normal" },
  flash: { type: Boolean, default: false },
  motionLevel: { type: String, default: "full" },
});
</script>

<template>
  <div
    class="exploration-readout"
    :class="[
      `exploration-readout--${tone}`,
      { 'exploration-readout--flash': flash, 'exploration-readout--animated': flash && motionLevel !== 'off' },
    ]"
    aria-live="polite"
    data-testid="exploration-readout"
    :data-tone="tone"
    :data-flash="flash ? 'true' : 'false'"
    :data-motion-level="motionLevel"
  >
    <span class="exploration-readout__lead" data-testid="exploration-readout-lead">{{ lead }}</span>
    <p class="exploration-readout__text" data-testid="exploration-readout-text">{{ text }}</p>
  </div>
</template>

<style scoped>
.exploration-readout {
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: calc(2px * var(--ui-scale));
  min-width: 0;
  min-height: calc(64px * var(--ui-scale));
  padding: calc(4px * var(--ui-scale)) calc(10px * var(--ui-scale));
  border-left: 2px solid var(--gold-500);
  background: linear-gradient(90deg, rgba(185, 154, 96, 0.08), transparent 70%);
  font-family: var(--f-sans);
}

.exploration-readout__lead {
  min-height: 1.4em;
  color: var(--gold-400);
  font-size: var(--text-xs);
  letter-spacing: 0.08em;
  line-height: 1.4;
}

.exploration-readout__text {
  margin: 0;
  color: var(--paper-100);
  font-size: var(--text-sm);
  line-height: 1.45;
  /* One to two lines; a longer server reason is clipped, never reflowed
     out of the panel. */
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  overflow-wrap: anywhere;
}

.exploration-readout--quiet .exploration-readout__lead,
.exploration-readout--quiet .exploration-readout__text {
  color: var(--paper-400);
}

.exploration-readout--warn {
  border-left-color: var(--seal-500);
  background: linear-gradient(90deg, rgba(160, 52, 44, 0.14), transparent 70%);
}
.exploration-readout--warn .exploration-readout__lead {
  color: var(--seal-light);
}

.exploration-readout--animated {
  animation: exploration-readout-flash var(--motion-base) var(--ease-standard);
}

@keyframes exploration-readout-flash {
  from {
    background-color: rgba(160, 52, 44, 0.32);
  }
  to {
    background-color: transparent;
  }
}
</style>
