<script setup>
// ExplorationReadout (exploration-exit-compass design D4; scene overview
// redesign §5.3): the exploration command panel's single explanation line —
// a polite live region with a gold left rule, a small lead line, and one to
// two lines of text. It renders what the pane's priority helper
// (`exploration-readout.js`) chose: a blocked-move flash (warn tone), the
// compass aim, or the idle summary (quiet tone). At the `off` motion level
// the flash is a static seal-red rule with no animation.
//
// A monster's lead carries its variant tag (monster-individual-names): the
// client-composed `tag` pill beside the name, and a named individual's name in
// the gold display face between two fading hairlines (`named`). The lead line
// has one fixed height, so a tag or the display face never moves the text line.
defineProps({
  lead: { type: String, default: "" },
  tag: { type: String, default: null },
  named: { type: Boolean, default: false },
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
    <span class="exploration-readout__lead" data-testid="exploration-readout-lead" :data-named="named ? 'true' : null"
      ><span class="exploration-readout__name" data-testid="exploration-readout-name">{{ lead }}</span
      ><span v-if="tag" class="exploration-readout__tag" data-testid="exploration-readout-tag" :title="tag">{{ tag }}</span></span
    >
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
  display: flex;
  align-items: center;
  gap: calc(8px * var(--ui-scale));
  min-width: 0;
  /* One fixed line: the tag pill and the named display face sit inside it. */
  height: calc(20px * var(--ui-scale));
  color: var(--gold-400);
  font-size: var(--text-xs);
  letter-spacing: 0.08em;
  line-height: calc(20px * var(--ui-scale));
  white-space: nowrap;
}
/* The name never shrinks (a monster name is at most five code points); in the
   narrow command column the detail tag gives way first. */
.exploration-readout__name {
  flex: none;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
}
.exploration-readout__tag {
  flex: 0 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  box-sizing: border-box;
  padding: 0 calc(6px * var(--ui-scale));
  border: 1px solid rgba(185, 154, 96, 0.55);
  border-radius: var(--radius-sm);
  background: rgba(185, 154, 96, 0.1);
  color: var(--gold-300);
  font-family: var(--f-sans);
  line-height: calc(16px * var(--ui-scale));
  letter-spacing: 0.04em;
}
/* A named individual: rank language (design D6), the name between two
   fading gold hairlines drawn as background layers. */
.exploration-readout__lead[data-named] .exploration-readout__name {
  padding: 0 calc(8px * var(--ui-scale));
  margin: 0 calc(-8px * var(--ui-scale));
  background:
    linear-gradient(90deg, transparent, var(--gold-400) 22%, var(--gold-400) 78%, transparent) top / 100% 1px no-repeat,
    linear-gradient(90deg, transparent, var(--gold-400) 22%, var(--gold-400) 78%, transparent) bottom / 100% 1px no-repeat;
  color: var(--gold-400);
  font-family: var(--f-display);
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
