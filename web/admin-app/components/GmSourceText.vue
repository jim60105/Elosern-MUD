<script setup>
// Read-only, line-numbered source text (gm-portal-s4-world-data §4.3).
//
// One ``<li id="L{n}">`` per line with a sticky gutter whose numbers are real
// anchors, so ``#L42`` can be shared and the line is highlighted and centred.
// The only syntax treatment is dimming YAML comment lines, which keeps a long
// rulebook calm to read. Text is always interpolated, never v-html.
import { computed, nextTick, onMounted, ref, watch } from "vue";
import GmCodeBlock from "./GmCodeBlock.vue";
import GmEmpty from "./GmEmpty.vue";

const props = defineProps({
  text: { type: String, default: "" },
  name: { type: String, required: true },
  // The 1-based line to highlight (from ``#L42``).
  highlight: { type: Number, default: null },
});

const emit = defineEmits(["select-line"]);

const lines = computed(() => {
  if (!props.text) return [];
  const split = props.text.replace(/\r\n?/g, "\n").split("\n");
  if (split.length > 1 && split[split.length - 1] === "") split.pop();
  // A ``#`` inside a block scalar (``key: |`` / ``>-`` …) is text, not a
  // comment: track the block by the indentation of the line that opened it.
  let blockIndent = null;
  return split.map((content, index) => {
    const blank = content.trim() === "";
    const indent = content.length - content.trimStart().length;
    if (blockIndent !== null && !blank && indent <= blockIndent) blockIndent = null;
    const comment = blockIndent === null && /^\s*#/.test(content);
    if (blockIndent === null && !comment && /:\s*[|>][+-]?\d*\s*(#.*)?$/.test(content)) blockIndent = indent;
    return { number: index + 1, content, comment, blank };
  });
});
const gutterWidth = computed(() => `${String(Math.max(lines.value.length, 1)).length + 1}ch`);
const wrap = ref(false);
const body = ref(null);

async function reveal() {
  if (!props.highlight) return;
  await nextTick();
  const line = body.value?.querySelector?.(`#L${props.highlight}`);
  line?.scrollIntoView?.({ block: "center" });
}

onMounted(reveal);
watch(() => [props.highlight, props.text], reveal);
</script>

<template>
  <figure class="gm-source">
    <figcaption class="gm-source__caption">
      <span class="gm-source__name gm-mono" :title="name">{{ name }}</span>
      <span class="gm-source__count">共 <span class="gm-num">{{ lines.length }}</span> 行</span>
      <span class="gm-source__tools">
        <button
          type="button"
          class="ui-btn ui-btn--ghost ui-btn--sm"
          :aria-pressed="wrap ? 'true' : 'false'"
          @click="wrap = !wrap"
        >
          自動換行
        </button>
        <GmCodeBlock v-if="text" :text="text" copy-only copy-label="複製全文" />
      </span>
    </figcaption>
    <GmEmpty v-if="lines.length === 0" title="檔案是空的" message="這個檔案目前沒有任何內容。" />
    <div
      v-else
      ref="body"
      class="gm-source__body"
      :class="{ 'is-wrapped': wrap }"
      :style="{ '--gutter': gutterWidth }"
      tabindex="0"
      role="region"
      :aria-label="`${name} 原始內容`"
    >
      <ol class="gm-source__lines">
        <li
          v-for="line in lines"
          :id="`L${line.number}`"
          :key="line.number"
          class="gm-source__line"
          :class="{ 'is-comment': line.comment, 'is-highlight': line.number === highlight }"
        >
          <a
            class="gm-source__number"
            :href="`#L${line.number}`"
            :aria-label="`第 ${line.number} 行`"
            @click="emit('select-line', line.number)"
          >{{ line.number }}</a>
          <span class="gm-source__text">{{ line.blank ? " " : line.content }}</span>
        </li>
      </ol>
    </div>
  </figure>
</template>

<style scoped>
.gm-source {
  display: grid;
  gap: 0;
  min-width: 0;
  margin: 0;
  background: var(--ink-950);
  border: var(--line);
  border-radius: var(--radius);
  box-shadow: inset 0 1px 0 color-mix(in srgb, var(--gold-500) 10%, transparent);
}

.gm-source__caption {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--sp-2) var(--sp-4);
  padding: var(--sp-2) var(--sp-4);
  background: var(--ink-860);
  border-bottom: var(--line);
  border-radius: var(--radius) var(--radius) 0 0;
}

.gm-source__name {
  min-width: 0;
  overflow: hidden;
  font-size: var(--text-sm);
  color: var(--paper-100);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.gm-source__count {
  font-size: var(--text-xs);
  color: var(--paper-500);
}

.gm-source__tools {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--sp-2);
  margin-left: auto;
}

.gm-source__body {
  max-height: min(72vh, 960px);
  overflow: auto;
  overscroll-behavior: contain;
  border-radius: 0 0 var(--radius) var(--radius);
}

.gm-source__body:focus-visible {
  box-shadow: var(--focus);
  outline: none;
}

.gm-source__lines {
  min-width: max-content;
  margin: 0;
  padding: var(--sp-2) 0;
  list-style: none;
}

.gm-source__body.is-wrapped .gm-source__lines {
  min-width: 0;
}

.gm-source__line {
  display: grid;
  grid-template-columns: calc(var(--gutter) + var(--sp-4)) minmax(0, 1fr);
  font-family: var(--f-mono);
  font-size: var(--text-sm);
  /* Source is shown verbatim: no programming ligatures (``|-`` stays two glyphs). */
  font-variant-ligatures: none;
  font-feature-settings: "liga" 0, "calt" 0;
  line-height: 1.6;
  color: var(--paper-200);
}

.gm-source__line:hover {
  background: color-mix(in srgb, var(--ink-820) 70%, transparent);
}

.gm-source__number {
  position: sticky;
  left: 0;
  padding: 0 var(--sp-3) 0 var(--sp-2);
  font-variant-numeric: tabular-nums;
  color: var(--paper-500);
  text-align: end;
  text-decoration: none;
  user-select: none;
  background: var(--ink-950);
  border-right: 1px solid var(--ink-700);
}

.gm-source__number:hover {
  color: var(--gold-300);
}

.gm-source__number:focus-visible {
  box-shadow: var(--focus);
  outline: none;
}

.gm-source__text {
  padding: 0 var(--sp-4) 0 var(--sp-3);
  white-space: pre;
  tab-size: 2;
}

.gm-source__body.is-wrapped .gm-source__text {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.gm-source__line.is-comment .gm-source__text {
  font-style: italic;
  color: var(--paper-500);
}

.gm-source__line.is-highlight {
  background: var(--gold-glow);
  box-shadow: inset 2px 0 var(--gold-500);
}

.gm-source__line.is-highlight .gm-source__number {
  color: var(--gold-300);
  background: color-mix(in srgb, var(--gold-500) 14%, var(--ink-950));
}
</style>
