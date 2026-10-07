<script setup>
// A pure-CSS micro bar (gm-portal-s2b-dashboard). Single-value mode fills
// `value / max`; segmented mode stacks `segments` proportionally. Every tone
// also carries a fill pattern (solid / hatch / cross / outline), so a
// segment reads without colour, and the bar is decorative: the visible
// numbers next to it and the hidden `label` carry the meaning.
import { computed } from "vue";

const props = defineProps({
  value: { type: Number, default: 0 },
  max: { type: Number, default: 0 },
  segments: { type: Array, default: null },
  tone: {
    type: String,
    default: "gold",
    validator: (value) => ["ok", "warn", "crit", "neutral", "gold"].includes(value),
  },
  pattern: {
    type: String,
    default: "solid",
    validator: (value) => ["solid", "hatch", "cross", "outline"].includes(value),
  },
  label: { type: String, required: true },
  width: { type: String, default: "120px" },
});

const parts = computed(() => {
  if (Array.isArray(props.segments)) {
    const total = props.segments.reduce((sum, part) => sum + Math.max(0, part.value || 0), 0);
    return props.segments
      .filter((part) => (part.value || 0) > 0)
      .map((part) => ({
        key: part.key,
        tone: part.tone ?? "neutral",
        pattern: part.pattern ?? "solid",
        share: total ? (part.value / total) * 100 : 0,
      }));
  }
  const share = props.max > 0 ? Math.min(100, Math.max(0, (props.value / props.max) * 100)) : 0;
  return [{ key: "value", tone: props.tone, pattern: props.pattern, share }];
});

const empty = computed(() => parts.value.every((part) => part.share === 0));
</script>

<template>
  <span class="gm-meter" :style="{ '--gm-meter-width': width }">
    <span class="gm-meter__track" :class="{ 'gm-meter__track--empty': empty }" aria-hidden="true">
      <span
        v-for="part in parts"
        :key="part.key"
        class="gm-meter__fill"
        :class="[`gm-meter__fill--${part.tone}`, `gm-meter__fill--${part.pattern}`]"
        :style="{ width: `${part.share}%` }"
      ></span>
    </span>
    <span class="gm-visually-hidden">{{ label }}</span>
  </span>
</template>

<style scoped>
.gm-meter {
  display: inline-flex;
  align-items: center;
  width: var(--gm-meter-width);
  max-width: 100%;
  vertical-align: middle;
}

.gm-meter__track {
  position: relative;
  display: flex;
  width: 100%;
  height: 6px;
  overflow: hidden;
  background: var(--ink-780);
  border: 1px solid var(--ink-600);
  border-radius: var(--radius-pill);
}

/* A zero value keeps a 2px tick, so "0" never reads as "no data". */
.gm-meter__track--empty::before {
  content: "";
  width: 2px;
  background: var(--paper-500);
}

.gm-meter__fill {
  --tone: var(--gold-500);
  height: 100%;
  transition: width var(--motion-slow) var(--ease-standard);
}

.gm-meter__fill + .gm-meter__fill {
  box-shadow: inset 1px 0 0 var(--ink-950);
}

.gm-meter__fill--ok {
  --tone: var(--ok);
}
.gm-meter__fill--warn {
  --tone: var(--warn);
}
.gm-meter__fill--crit {
  --tone: var(--crit);
}
.gm-meter__fill--neutral {
  --tone: var(--paper-500);
}
.gm-meter__fill--gold {
  --tone: var(--gold-500);
}

.gm-meter__fill--solid {
  background: var(--tone);
}

.gm-meter__fill--hatch {
  background: repeating-linear-gradient(135deg, var(--tone) 0 3px, var(--ink-950) 3px 5px);
}

.gm-meter__fill--cross {
  background:
    repeating-linear-gradient(45deg, transparent 0 3px, var(--ink-950) 3px 4px),
    repeating-linear-gradient(135deg, var(--tone) 0 3px, var(--ink-950) 3px 4px);
}

.gm-meter__fill--outline {
  background: transparent;
  box-shadow: inset 0 0 0 1px var(--tone);
}
</style>
