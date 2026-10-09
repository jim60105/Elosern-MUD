<script setup>
// GradeGem (quest-drawer-ui-primitives, design Decision 5): the rotated-square
// grade seal carrying the upright grade letter. `sm` (30px) sits in list
// rows, `md` (34px) in the grade rail, `lg` (64px) in the detail hero. The
// material comes from the grade-materials.js ladder; an unknown grade gets
// iron. It is decorative (`aria-hidden`) beside the text that names the
// grade, unless a `label` is passed, which makes it an image with that name.
import { computed } from "vue";
import { gradeMaterial } from "./grade-materials.js";

const props = defineProps({
  grade: { type: String, default: null },
  size: {
    type: String,
    default: "md",
    validator: (value) => ["sm", "md", "lg"].includes(value),
  },
  label: { type: String, default: null },
});

const material = computed(() => gradeMaterial(props.grade));
</script>

<template>
  <span
    class="grade-gem"
    :class="`grade-gem--${size}`"
    :style="material"
    :data-grade="grade ?? undefined"
    :aria-hidden="label ? undefined : 'true'"
    :role="label ? 'img' : undefined"
    :aria-label="label || undefined"
  >
    <span class="grade-gem__letter">{{ grade ?? "—" }}</span>
  </span>
</template>

<style scoped>
/* The iron (F) material is the default; the inline material from
   grade-materials.js overrides these per grade. */
.grade-gem {
  --gem: calc(34px * var(--ui-scale));
  --gem-hi: #3b3d42;
  --gem-lo: #1a1b1f;
  --gem-rim: #6d6a62;
  --gem-ink: #c9c4b9;
  --gem-inner: rgba(185, 154, 96, 0.35);
  position: relative;
  display: grid;
  place-items: center;
  flex: none;
  width: var(--gem);
  height: var(--gem);
}

.grade-gem::before {
  content: "";
  position: absolute;
  inset: 15%;
  transform: rotate(45deg);
  border: 1px solid var(--gem-rim);
  border-radius: calc(3px * var(--ui-scale));
  background: radial-gradient(circle at 50% 30%, var(--gem-hi), var(--gem-lo) 75%);
  box-shadow:
    inset 0 0 0 calc(2px * var(--ui-scale)) var(--ink-950),
    inset 0 0 0 calc(3px * var(--ui-scale)) var(--gem-inner);
}

.grade-gem__letter {
  position: relative;
  color: var(--gem-ink);
  font: calc(15px * var(--ui-scale)) / 1 var(--f-display);
  text-shadow: 0 1px 0 #000;
}

.grade-gem--sm {
  --gem: calc(30px * var(--ui-scale));
}

.grade-gem--sm .grade-gem__letter {
  font-size: calc(13px * var(--ui-scale));
}

.grade-gem--lg {
  --gem: calc(64px * var(--ui-scale));
}

.grade-gem--lg .grade-gem__letter {
  font-size: var(--text-2xl);
}
</style>
