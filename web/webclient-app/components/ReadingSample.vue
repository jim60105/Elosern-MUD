<script setup>
// ReadingSample (webclient-settings-reading-preview): the settings overlay's
// live reading preview. One fixed line of prose set like a message-window
// page — the page face, the page size times the chosen prose scale, the page
// leading — typed at the rate the message window would use for the chosen
// text speed and the effective motion level (`effectiveCps`, the shared
// rule: any level other than 完整 shows it at once).
//
// It is local and isolated: it reads only its three props, owns its own
// typewriter clock, and touches no store, narrative log, reader position or
// action. It plays once when mounted and restarts once whenever the prose
// scale, the text speed or the motion level changes (from the prop watcher,
// so the restart always reads the new rate); 重播 plays it again. It never
// loops. Unmounting — closing the settings overlay — stops its clock, so no
// preview work outlives the overlay.
//
// The whole line is always laid out: the unrevealed tail keeps its place
// with `visibility: hidden` (the message window's reveal technique), so the
// sample never re-wraps or changes height while it types. Assistive
// technology reads the complete line once from a visually hidden copy; both
// visual spans are `aria-hidden`, so a half-typed sentence is never read.
import { computed, onMounted, watch } from "vue";
import { useTypewriter } from "../composables/use-typewriter.js";
import { MOTION_LEVELS } from "../lib/motion_level.js";
import { TEXT_SPEED_CPS, TEXT_SPEEDS, effectiveCps } from "../lib/message_reveal.js";

// The fixed sample: narration then a line of speech, so the preview shows
// both the page's prose and its corner-bracket quotation.
const SAMPLE_TEXT = "晨霧自河面升起，鐘樓敲過第七聲。櫃檯後的書記抬起頭：「今天也來接委託嗎？」";
// Reveal units are code points, the unit the typewriter counts.
const SAMPLE_UNITS = Array.from(SAMPLE_TEXT);

const SPEED_LABELS = { slow: "慢", normal: "標準", fast: "快", instant: "瞬間" };
const MOTION_LABELS = { reduced: "減少", off: "關閉" };

const props = defineProps({
  fontScale: { type: Number, default: 1 },
  textSpeed: { type: String, default: "normal" },
  motionLevel: {
    type: String,
    default: "full",
    validator: (value) => MOTION_LEVELS.includes(value),
  },
});

// Read by the typewriter at each `start()` (never cached), so a restart from
// the prop watcher always types at the new rate.
const rate = computed(() => effectiveCps(props.motionLevel, props.textSpeed));

const typewriter = useTypewriter({
  units: () => SAMPLE_UNITS.length,
  cps: () => rate.value,
});

const shown = computed(() => SAMPLE_UNITS.slice(0, typewriter.typed.value).join(""));
const hidden = computed(() => SAMPLE_UNITS.slice(typewriter.typed.value).join(""));
const complete = computed(() => !typewriter.typing.value);

// The caption names the rule in force, in the reader's words.
const caption = computed(() => {
  if (props.motionLevel !== "full") {
    return `動態效果「${MOTION_LABELS[props.motionLevel]}」· 立即顯示`;
  }
  const speed = TEXT_SPEEDS.includes(props.textSpeed) ? props.textSpeed : "normal";
  if (speed === "instant") {
    return "瞬間 · 立即顯示";
  }
  return `${SPEED_LABELS[speed]} · 每秒 ${TEXT_SPEED_CPS[speed]} 字`;
});

function play() {
  typewriter.start(0);
}

onMounted(play);

// One restart per change; same-tick changes collapse into one.
watch(() => [props.fontScale, props.textSpeed, props.motionLevel], play);
</script>

<template>
  <figure
    class="reading-sample"
    data-testid="settings-sample"
    :data-typing="complete ? 'false' : 'true'"
    :style="{ '--prose-scale': fontScale }"
  >
    <figcaption class="reading-sample__head">
      <span class="reading-sample__title">閱讀預覽</span>
      <span class="reading-sample__rule" data-testid="settings-sample-caption">{{ caption }}</span>
    </figcaption>
    <p class="reading-sample__page" data-testid="settings-sample-page">
      <span class="reading-sample__sr">{{ SAMPLE_TEXT }}</span>
      <span aria-hidden="true" data-testid="settings-sample-text"
        >{{ shown }}<span class="reading-sample__tail">{{ hidden }}</span
        ><span class="reading-sample__marker" :class="{ 'is-shown': complete }">■</span></span
      >
    </p>
    <button
      type="button"
      class="reading-sample__replay"
      data-testid="settings-sample-replay"
      @click="play"
    >
      <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
        <path d="M13 8a5 5 0 1 1-1.46-3.54" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" />
        <path d="M11.9 1.6v3.2H8.7" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
      重播
    </button>
  </figure>
</template>

<style scoped>
/* A miniature message window: the band's deep ink ground under its fine gold
   edge with the central lozenge, the page text on a reading column. */
.reading-sample {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  grid-template-areas:
    "head head"
    "page replay";
  align-items: end;
  column-gap: 24px;
  row-gap: 10px;
  margin: 0;
  padding: 18px 24px 16px;
  border: 1px solid var(--band-edge-dim);
  border-top-color: var(--band-edge);
  border-radius: var(--radius);
  background:
    radial-gradient(120% 140% at 50% -40%, rgba(185, 154, 96, 0.08), transparent 60%),
    linear-gradient(180deg, #0e0f15 0%, #13101a 45%, #0e0b12 100%);
  box-shadow: inset 0 1px 0 rgba(228, 200, 142, 0.08), 0 10px 24px rgba(0, 0, 0, 0.28);
}

.reading-sample::before {
  content: "";
  position: absolute;
  top: -6px;
  left: 50%;
  width: 30px;
  height: 11px;
  transform: translateX(-50%);
  background: var(--band-ornament) center / contain no-repeat;
  pointer-events: none;
}

.reading-sample__head {
  grid-area: head;
  display: flex;
  align-items: baseline;
  gap: 12px;
  font-family: var(--f-sans);
}

.reading-sample__title {
  color: var(--gold-400);
  font-size: var(--text-sm);
  letter-spacing: 0.12em;
}

.reading-sample__rule {
  color: var(--paper-300);
  font-size: var(--text-sm);
  font-variant-numeric: tabular-nums lining-nums;
}

/* The page text: the message window's face, size and leading, so the scale
   step reads here exactly as it will on the band. */
.reading-sample__page {
  grid-area: page;
  max-width: 42em;
  margin: 0;
  font-family: var(--f-serif);
  font-size: calc(var(--message-text) * var(--prose-scale));
  line-height: var(--message-line-height);
  color: var(--paper-100);
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.55);
  text-autospace: normal;
  text-spacing-trim: trim-start;
  line-break: strict;
  text-wrap: balance;
}

.reading-sample__tail {
  visibility: hidden;
}

/* The message window's end-of-response mark, shown once the line is out. */
.reading-sample__marker {
  display: inline-block;
  margin-left: 0.4em;
  color: var(--gold-400);
  font-size: 0.5em;
  vertical-align: 0.25em;
  visibility: hidden;
}

.reading-sample__marker.is-shown {
  visibility: visible;
}

.reading-sample__sr {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}

.reading-sample__replay {
  grid-area: replay;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 36px;
  padding: 0 14px;
  color: var(--paper-300);
  background: transparent;
  border: var(--line);
  border-radius: var(--radius-sm);
  font: var(--text-sm) var(--f-sans);
  cursor: pointer;
  transition: color var(--motion-fast) var(--ease-standard), border-color var(--motion-fast) var(--ease-standard);
}

.reading-sample__replay:hover,
.reading-sample__replay:focus-visible {
  color: var(--gold-400);
  border-color: var(--gold-500);
}

.reading-sample__replay:focus-visible {
  outline: 2px solid var(--gold-400);
  outline-offset: 2px;
}
</style>
