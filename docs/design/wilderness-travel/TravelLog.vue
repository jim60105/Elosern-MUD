<script setup>
// The travel log (prototype): the band's message region in travel mode. One
// line per noteworthy event — never per step — grouped under day headings,
// newest at the bottom. Tones mark what kind of event a line is, always
// paired with a glyph so colour is never the only cue.
import { computed, nextTick, ref, watch } from "vue";

const props = defineProps({
  entries: { type: Array, required: true },
});

const scroller = ref(null);

const GLYPH = { landmark: "◆", hostile: "▲", fatigue: "◐", night: "☾", camp: "⛺", ford: "≈", plain: "·" };

const groups = computed(() => {
  const out = [];
  for (const e of props.entries) {
    const last = out[out.length - 1];
    if (!last || last.day !== e.day) out.push({ day: e.day, items: [e] });
    else last.items.push(e);
  }
  return out;
});

watch(
  () => props.entries.length,
  async () => {
    await nextTick();
    const el = scroller.value;
    if (el) el.scrollTop = el.scrollHeight;
  },
  { immediate: true },
);
</script>

<template>
  <section class="travel-log" aria-label="旅途日誌">
    <header class="travel-log__head">旅途日誌</header>
    <div ref="scroller" class="travel-log__scroll" aria-live="polite">
      <template v-for="g in groups" :key="g.day">
        <p class="travel-log__day">第 {{ g.day }} 日</p>
        <p v-for="(e, i) in g.items" :key="`${g.day}-${i}`" class="travel-log__line" :class="`is-${e.tone ?? 'plain'}`">
          <time class="travel-log__time">{{ e.time }}</time>
          <span class="travel-log__glyph" aria-hidden="true">{{ GLYPH[e.tone ?? "plain"] }}</span>
          <span class="travel-log__text" v-html="e.html ?? e.text"></span>
        </p>
      </template>
    </div>
  </section>
</template>

<style>
.travel-log {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: calc(14px * var(--ui-scale)) calc(26px * var(--ui-scale)) calc(10px * var(--ui-scale));
  box-sizing: border-box;
}
.travel-log__head {
  flex: none;
  font: var(--text-xs)/1.2 var(--f-display);
  letter-spacing: 0.3em;
  color: var(--gold-500);
  margin-bottom: calc(6px * var(--ui-scale));
}
.travel-log__scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  scrollbar-width: thin;
  mask-image: linear-gradient(180deg, transparent 0, #000 calc(22px * var(--ui-scale)));
  padding-top: calc(10px * var(--ui-scale));
}
.travel-log__day {
  margin: calc(6px * var(--ui-scale)) 0 calc(2px * var(--ui-scale));
  font: var(--text-xs)/1.3 var(--f-sans);
  letter-spacing: 0.18em;
  color: var(--gold-600);
  display: flex;
  align-items: center;
  gap: calc(10px * var(--ui-scale));
}
.travel-log__day::after {
  content: "";
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, rgba(143, 113, 60, 0.45), transparent);
}
.travel-log__line {
  margin: 0;
  display: grid;
  grid-template-columns: calc(52px * var(--ui-scale)) calc(18px * var(--ui-scale)) 1fr;
  align-items: baseline;
  font: var(--text-md)/1.65 var(--f-serif);
  color: var(--paper-300);
}
.travel-log__time {
  font: var(--text-xs)/1 var(--f-sans);
  color: var(--paper-700);
  font-variant-numeric: tabular-nums;
}
.travel-log__glyph {
  font-size: var(--text-xs);
  color: var(--paper-700);
}
.travel-log__text b {
  font-weight: 600;
  color: var(--paper-50);
}
.travel-log__line:last-child {
  color: var(--paper-100);
}
.travel-log__line.is-landmark .travel-log__glyph,
.travel-log__line.is-landmark em {
  color: var(--gold-400);
  font-style: normal;
}
.travel-log__line.is-hostile .travel-log__glyph,
.travel-log__line.is-hostile em {
  color: var(--seal-light);
  font-style: normal;
}
.travel-log__line.is-fatigue .travel-log__glyph,
.travel-log__line.is-fatigue em {
  color: var(--warn);
  font-style: normal;
}
.travel-log__line.is-night .travel-log__glyph,
.travel-log__line.is-night em {
  color: #b9c7e6;
  font-style: normal;
}
.travel-log__line.is-camp .travel-log__glyph,
.travel-log__line.is-ford .travel-log__glyph {
  color: var(--gold-500);
}
</style>
