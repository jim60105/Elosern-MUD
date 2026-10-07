<script setup>
// Verbatim content with copy (gm-portal-s2b-dashboard). Objects render as
// two-space JSON, strings as-is, always through text interpolation (never
// v-html: transcript payloads are untrusted). Long content collapses to
// `maxLines` with a toggle; copying never throws — an unavailable clipboard
// (non-secure origin) falls back to making the block select-all.
import { computed, ref } from "vue";

const props = defineProps({
  text: { type: [String, Object, Array, Number, Boolean], default: "" },
  label: { type: String, default: "" },
  copyLabel: { type: String, default: "複製" },
  maxLines: { type: Number, default: 24 },
  copyable: { type: Boolean, default: true },
  // Render only the copy control (the content is shown elsewhere).
  copyOnly: { type: Boolean, default: false },
});

const rendered = computed(() => {
  if (typeof props.text === "string") return props.text;
  try {
    return JSON.stringify(props.text, null, 2) ?? "";
  } catch {
    return String(props.text);
  }
});

const lineCount = computed(() => rendered.value.split("\n").length);
const collapsible = computed(() => props.maxLines > 0 && lineCount.value > props.maxLines);
const expanded = ref(false);
const collapsed = computed(() => collapsible.value && !expanded.value);

const copyState = ref("idle");
let resetTimer = null;

async function copy() {
  clearTimeout(resetTimer);
  try {
    const clipboard = globalThis.navigator?.clipboard;
    if (!clipboard?.writeText) throw new Error("clipboard unavailable");
    await clipboard.writeText(rendered.value);
    copyState.value = "copied";
  } catch {
    copyState.value = "failed";
  }
  resetTimer = setTimeout(() => (copyState.value = "idle"), 2000);
}

const copyText = computed(() => {
  if (copyState.value === "copied") return "已複製";
  if (copyState.value === "failed") return "複製失敗，請手動選取";
  return props.copyLabel;
});
</script>

<template>
  <button
    v-if="copyOnly"
    type="button"
    class="ui-btn ui-btn--ghost ui-btn--sm gm-code-block__copy"
    :data-copy-state="copyState"
    @click="copy"
  >
    {{ copyText }}
  </button>
  <figure
    v-else
    class="gm-code-block"
    :class="{ 'is-collapsed': collapsed, 'is-select-all': copyState === 'failed', 'is-overlay': copyable && !label }"
  >
    <figcaption v-if="label || copyable" class="gm-code-block__bar">
      <span v-if="label" class="gm-code-block__label">{{ label }}</span>
      <button
        v-if="copyable"
        type="button"
        class="ui-btn ui-btn--ghost ui-btn--sm gm-code-block__copy"
        :data-copy-state="copyState"
        @click="copy"
      >
        {{ copyText }}
      </button>
    </figcaption>
    <pre
      class="gm-code-block__pre"
      :style="collapsed ? { '--gm-code-lines': maxLines } : null"
      :aria-label="label || null"
      tabindex="0"
    >{{ rendered }}</pre>
    <button
      v-if="collapsible"
      type="button"
      class="ui-btn ui-btn--ghost ui-btn--sm gm-code-block__toggle"
      :aria-expanded="expanded ? 'true' : 'false'"
      @click="expanded = !expanded"
    >
      {{ expanded ? "收合" : `顯示全部（${lineCount} 行）` }}
    </button>
  </figure>
</template>

<style scoped>
.gm-code-block {
  position: relative;
  display: grid;
  gap: var(--sp-1);
  min-width: 0;
  margin: 0;
}

.gm-code-block__bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-2);
  min-height: 28px;
}

.gm-code-block__label {
  font-size: var(--text-xs);
  letter-spacing: 0.08em;
  color: var(--paper-500);
}

.gm-code-block__copy {
  margin-left: auto;
}

/* Unlabelled blocks float the copy control inside the block's corner. */
.is-overlay .gm-code-block__bar {
  position: absolute;
  top: var(--sp-1);
  right: var(--sp-1);
  z-index: 1;
  min-height: 0;
}

.is-overlay .gm-code-block__copy {
  background: color-mix(in srgb, var(--ink-950) 85%, transparent);
}

.is-overlay .gm-code-block__pre {
  padding-right: 5.5em;
}

.gm-code-block__copy[data-copy-state="copied"] {
  color: var(--ok);
}

.gm-code-block__copy[data-copy-state="failed"] {
  color: var(--warn);
}

.gm-code-block__pre {
  position: relative;
  max-width: 100%;
  margin: 0;
  padding: var(--sp-3);
  overflow: auto;
  font-family: var(--f-mono);
  font-size: var(--text-sm);
  line-height: 1.55;
  color: var(--paper-200);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  background: var(--ink-950);
  border: var(--line);
  border-radius: var(--radius-sm);
}

.gm-code-block__pre:focus-visible {
  box-shadow: var(--focus);
  outline: none;
}

.is-collapsed .gm-code-block__pre {
  max-height: calc(var(--gm-code-lines) * 1.55em + 2 * var(--sp-3));
  overflow: hidden;
  mask-image: linear-gradient(to bottom, #000 calc(100% - 3em), transparent);
}

.is-select-all .gm-code-block__pre {
  user-select: all;
}

.gm-code-block__toggle {
  justify-self: start;
}
</style>
