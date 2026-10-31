<script setup>
// The travel band log (OpenSpec change wilderness-travel-log-ui; interface
// design §9, after the prototype's docs/design/wilderness-travel/
// TravelLog.vue). In the travel layout it replaces the message window in the
// band's message region: one line per committed notice — never per step —
// grouped under day headings, newest at the bottom, in a polite log region.
//
// - Every entry is the store's (`view.travel.entries`): server-identified
//   notices with server-rendered text, plus the local refusal lines. Nothing
//   here reads room prose or decides importance.
// - Each kind carries a glyph and a spoken kind word, so kinds stay
//   distinguishable without colour.
// - Text is interpolated, never v-html. A look keeps one summary line; its
//   full prose opens below it through the narrative line renderer the full
//   log uses (the allowlist markup pipeline, no executed markup).
// - New entries follow the bottom only when the log was already there.
import { computed, nextTick, ref, watch } from "vue";
import { narrativeLineNodes } from "../../lib/narrative_line_nodes.js";

const props = defineProps({
  entries: { type: Array, default: () => [] },
});

// glyph + spoken kind word + tone (the tone only tints the glyph).
const KINDS = {
  landmark_reached: { glyph: "◆", word: "地標", tone: "landmark" },
  landmark_sighted: { glyph: "◆", word: "遠望", tone: "landmark" },
  hostile_sighted: { glyph: "▲", word: "敵蹤", tone: "hostile" },
  fatigue_stage: { glyph: "◐", word: "疲勞", tone: "fatigue" },
  dusk: { glyph: "☾", word: "天色", tone: "night" },
  nightfall: { glyph: "☾", word: "天色", tone: "night" },
  camp_result: { glyph: "⛺", word: "紮營", tone: "camp" },
  ford_crossed: { glyph: "≈", word: "渡口", tone: "ford" },
  refusal: { glyph: "·", word: "受阻", tone: "refusal" },
};
const PLAIN = { glyph: "·", word: "", tone: "plain" };
const kindOf = (entry) => KINDS[entry.kind] ?? PLAIN;

const groups = computed(() => {
  const out = [];
  for (const entry of props.entries) {
    const last = out[out.length - 1];
    if (last && (entry.day === null || entry.day === last.day)) last.items.push(entry);
    else out.push({ key: `${entry.day}:${entry.id}`, day: entry.day, items: [entry] });
  }
  return out;
});
const newestId = computed(() => props.entries.at(-1)?.id ?? null);

// The expanded look entries (local view state; an id that left the list is
// simply never rendered).
const open = ref(new Set());
function toggle(id) {
  const next = new Set(open.value);
  if (next.has(id)) next.delete(id);
  else next.add(id);
  open.value = next;
}
const proseId = (id) => `travel-log-prose-${id.replace(/[^A-Za-z0-9_-]/g, "_")}`;

// The look prose through the full log's own line renderer.
function ProseLines({ prose }) {
  return String(prose ?? "")
    .split("\n")
    .flatMap((text, index) => narrativeLineNodes({ kind: "out", text }, index));
}
ProseLines.props = ["prose"];

const scroller = ref(null);
const SLACK = 4;
let atBottom = true;
function onScroll() {
  const el = scroller.value;
  if (el) atBottom = el.scrollHeight - el.scrollTop - el.clientHeight <= SLACK;
}
watch(
  () => newestId.value,
  async () => {
    const follow = atBottom;
    await nextTick();
    const el = scroller.value;
    if (el && follow) el.scrollTop = el.scrollHeight;
  },
  { immediate: true },
);

</script>

<template>
  <section class="travel-log" data-testid="travel-log" aria-labelledby="travel-log-title">
    <header class="travel-log__head">
      <span class="travel-log__ornament" aria-hidden="true">◆</span>
      <h2 id="travel-log-title" class="travel-log__title">旅途日誌</h2>
    </header>
    <div
      ref="scroller"
      class="travel-log__scroll"
      data-testid="travel-log__scroll"
      role="log"
      aria-live="polite"
      aria-relevant="additions"
      aria-labelledby="travel-log-title"
      tabindex="0"
      @scroll.passive="onScroll"
    >
      <p v-if="!entries.length" class="travel-log__empty" data-testid="travel-log__empty">
        旅途中的見聞會記在這裡。
      </p>
      <section
        v-for="group in groups"
        :key="group.key"
        class="travel-log__day"
        data-testid="travel-log__day"
      >
        <h3 v-if="group.day !== null" class="travel-log__day-head">第 {{ group.day }} 日</h3>
        <ol class="travel-log__lines">
          <li
            v-for="entry in group.items"
            :key="entry.id"
            class="travel-log__line"
            :class="[`is-${kindOf(entry).tone}`, { 'is-newest': entry.id === newestId }]"
            data-testid="travel-log__entry"
            :data-kind="entry.kind"
            :data-entry-id="entry.id"
          >
            <time class="travel-log__time">{{ entry.time }}</time>
            <span class="travel-log__glyph" aria-hidden="true">{{ kindOf(entry).glyph }}</span>
            <span class="travel-log__body">
              <span v-if="kindOf(entry).word" class="visually-hidden">{{ kindOf(entry).word }}：</span>
              <span class="travel-log__text" data-testid="travel-log__text">{{ entry.text }}</span>
              <button
                v-if="entry.kind === 'look' && entry.params.prose"
                type="button"
                class="travel-log__more"
                data-testid="travel-log__more"
                :aria-expanded="open.has(entry.id) ? 'true' : 'false'"
                :aria-controls="proseId(entry.id)"
                @click="toggle(entry.id)"
              >{{ open.has(entry.id) ? "收起" : "全文" }}</button>
              <div
                v-if="entry.kind === 'look' && open.has(entry.id)"
                :id="proseId(entry.id)"
                class="travel-log__prose narrative"
                data-testid="travel-log__prose"
              >
                <ProseLines :prose="entry.params.prose" />
              </div>
            </span>
          </li>
        </ol>
      </section>
    </div>
  </section>
</template>

<style scoped>
.travel-log {
  position: relative;
  box-sizing: border-box;
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  /* The band's 日誌 / ⌨ controls sit in the strip's right end; the log keeps
     clear of their column instead of giving up the whole bottom strip. */
  padding: calc(12px * var(--ui-scale)) calc(116px * var(--ui-scale))
    var(--band-pad-bottom) calc(26px * var(--ui-scale));
  color: var(--paper-300);
}

.travel-log__head {
  flex: none;
  display: flex;
  align-items: center;
  gap: calc(10px * var(--ui-scale));
  margin-bottom: calc(4px * var(--ui-scale));
}

.travel-log__ornament {
  font-size: var(--text-xs);
  line-height: 1;
  color: var(--gold-500);
}

.travel-log__title {
  margin: 0;
  font: var(--text-xs) / 1.2 var(--f-display);
  font-weight: 400;
  letter-spacing: 0.32em;
  color: var(--gold-500);
}

.travel-log__head::after {
  content: "";
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, rgba(185, 154, 96, 0.42), rgba(185, 154, 96, 0) 70%);
}

.travel-log__scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-width: thin;
  scrollbar-color: var(--ink-600) transparent;
  padding-top: calc(10px * var(--ui-scale));
  -webkit-mask-image: linear-gradient(180deg, transparent 0, #000 calc(18px * var(--ui-scale)));
  mask-image: linear-gradient(180deg, transparent 0, #000 calc(18px * var(--ui-scale)));
  outline: none;
}

.travel-log__scroll:focus-visible {
  box-shadow: inset 2px 0 0 var(--gold-400);
}

.travel-log__empty {
  margin: calc(6px * var(--ui-scale)) 0 0;
  font: var(--text-sm) / 1.6 var(--f-serif);
  color: var(--paper-500);
}

.travel-log__day + .travel-log__day {
  margin-top: calc(6px * var(--ui-scale));
}

.travel-log__day-head {
  margin: 0 0 calc(2px * var(--ui-scale));
  display: flex;
  align-items: center;
  gap: calc(10px * var(--ui-scale));
  font: var(--text-xs) / 1.6 var(--f-display);
  font-weight: 400;
  letter-spacing: 0.2em;
  color: var(--gold-600);
}

.travel-log__day-head::after {
  content: "";
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, rgba(143, 113, 60, 0.45), transparent);
}

.travel-log__lines {
  margin: 0;
  padding: 0;
  list-style: none;
}

.travel-log__line {
  position: relative;
  display: grid;
  grid-template-columns: calc(54px * var(--ui-scale)) calc(22px * var(--ui-scale)) minmax(0, 1fr);
  align-items: baseline;
  padding: calc(1px * var(--ui-scale)) 0;
  font: var(--text-md) / 1.65 var(--f-serif);
  color: var(--paper-300);
}

/* The newest line reads brighter, with the band ornament's gold tick. */
.travel-log__line.is-newest {
  color: var(--paper-50);
}

.travel-log__line.is-newest::before {
  content: "";
  position: absolute;
  left: calc(-12px * var(--ui-scale));
  top: 0.5em;
  bottom: 0.5em;
  width: 2px;
  border-radius: 1px;
  background: linear-gradient(180deg, transparent, var(--gold-400), transparent);
}

.travel-log__time {
  font: var(--text-xs) / 1 var(--f-sans);
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.04em;
  color: var(--paper-500);
}

.travel-log__glyph {
  font-size: var(--text-xs);
  font-family: var(--f-sans);
  text-align: center;
  color: var(--paper-500);
}

.travel-log__body {
  min-width: 0;
  overflow-wrap: anywhere;
}

.travel-log__line.is-landmark .travel-log__glyph { color: var(--gold-400); }
.travel-log__line.is-hostile .travel-log__glyph { color: var(--seal-light); }
.travel-log__line.is-fatigue .travel-log__glyph { color: var(--warn); }
.travel-log__line.is-night .travel-log__glyph { color: var(--paper-200); }
.travel-log__line.is-ford .travel-log__glyph { color: var(--gold-500); }
/* The tent keeps its own pitched silhouette (a text-form tent reads as the
   hostile triangle at this size), toned down to the ink-and-gold palette. */
.travel-log__line.is-camp .travel-log__glyph {
  filter: grayscale(1) sepia(0.7) brightness(0.95) contrast(0.9);
}
.travel-log__line.is-landmark .travel-log__text { color: var(--gold-300); }

/* A refused step: the server's own reason, set back from the notices. */
.travel-log__line.is-refusal .travel-log__text {
  color: var(--paper-400);
}

.travel-log__more {
  margin-left: calc(10px * var(--ui-scale));
  padding: 0 calc(8px * var(--ui-scale));
  min-height: calc(26px * var(--ui-scale));
  border: var(--line);
  border-radius: var(--radius-sm);
  background: var(--panel-solid);
  color: var(--paper-400);
  font: var(--text-xs) / 1 var(--f-sans);
  letter-spacing: 0.08em;
  vertical-align: 0.1em;
  cursor: pointer;
  transition: color var(--motion-fast) var(--ease-standard), border-color var(--motion-fast) var(--ease-standard);
}

.travel-log__more:hover,
.travel-log__more[aria-expanded="true"] {
  color: var(--gold-400);
  border-color: var(--gold-500);
}

.travel-log__more:focus-visible {
  outline: 2px solid var(--gold-400);
  outline-offset: 2px;
}

.travel-log__prose {
  margin: calc(6px * var(--ui-scale)) 0 calc(4px * var(--ui-scale));
  padding: calc(8px * var(--ui-scale)) calc(12px * var(--ui-scale));
  max-height: calc(180px * var(--ui-scale));
  overflow-y: auto;
  scrollbar-width: thin;
  border-left: 2px solid var(--ink-600);
  background: rgba(16, 18, 22, 0.55);
  font: var(--text-xs) / 1.6 var(--f-mono);
  color: var(--paper-200);
  white-space: pre-wrap;
}

.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  margin: -1px;
  padding: 0;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
  border: 0;
}
</style>
