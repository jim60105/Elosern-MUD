<script setup>
// Prototype of the place card's 等待 entry redesign: a first layer of two
// choice tiles (等待 / 睡眠), then the wait form or the existing SleepForm
// under one shared header (‹ 返回上一層 at the top left, ✕ 關閉 at the top
// right). Reference only: mock data, no store, no dispatch; the intents the
// real client would send are written to the log under the stage.
//
// Keys: on the tiles, 1 / 2 pick, ← → ↑ ↓ move, Home / End jump, Enter /
// Space activate, Esc closes. On a form, Esc or ‹ steps back to the tiles
// (focus on the tile you came from); ✕ closes everything and focus returns
// to the place card's 等待 button. Tab stays inside the open card.
import { computed, nextTick, onMounted, ref } from "vue";
import PlaceCard from "../../../web/webclient-app/components/PlaceCard.vue";
import SleepForm from "../../../web/webclient-app/components/SleepForm.vue";
// The card frame (`choice-card`) is ChoiceCard's global stylesheet.
import "../../../web/webclient-app/components/ChoiceCard.vue";
import WaitFormPrototype from "./WaitFormPrototype.vue";

const LOCKED_REASON = "上一個行動尚未完成，請稍候。";

const props = defineProps({
  // "closed" | "choice" | "wait" | "sleep"
  initialStep: { type: String, default: "choice" },
  locked: { type: Boolean, default: false },
  locationLabel: { type: String, default: "亞特利亞下城區 ‧ 石橋街" },
  timeLabel: { type: String, default: "春季 3 日 ‧ 22:40" },
  // The controlled character's fatigue row ({reserve_percent, label}), or
  // null when the status panel carries none.
  fatigue: { type: Object, default: () => ({ reserve_percent: 62, label: "輕度疲勞" }) },
  // The short name of the fatigue reserve (today 精神儲備; approved 精力).
  reserveTerm: { type: String, default: "精力" },
  // The place card button label (today 等待; approved 休息).
  placeLabel: { type: String, default: "休息" },
  // The width of the stage's card anchor, to try the stacked layout.
  cardWidth: { type: Number, default: 460 },
});

const step = ref(props.initialStep);
const lastTile = ref("wait");
const log = ref([]);
const stage = ref(null);
const tileRefs = ref({});

const tiles = computed(() => [
  {
    key: "wait",
    digit: "1",
    label: "等待",
    hint: "保持清醒，讓時間流逝",
    context: props.timeLabel ? [`現在 ${props.timeLabel.split("‧").pop().trim()}`] : null,
  },
  {
    key: "sleep",
    digit: "2",
    label: "睡眠",
    hint: `入睡，恢復${props.reserveTerm}`,
    // One unbroken line: the reserve, then its stage label.
    context: props.fatigue
      ? [`${props.reserveTerm} ${props.fatigue.reserve_percent}%`, `（${props.fatigue.label}）`]
      : null,
  },
]);

const stacked = computed(() => props.cardWidth < 320);

function record(text) {
  log.value = [text, ...log.value].slice(0, 6);
}

function placeWaitButton() {
  return stage.value?.querySelector('[data-testid="place-card-wait"]');
}

async function focusTile(key) {
  await nextTick();
  tileRefs.value[key]?.focus();
}

function openChoice() {
  step.value = "choice";
  lastTile.value = "wait";
  void focusTile("wait");
}

async function closeAll() {
  step.value = "closed";
  await nextTick();
  placeWaitButton()?.focus();
}

function pick(key) {
  if (props.locked) return;
  lastTile.value = key;
  // The form autofocuses its duration input.
  step.value = key;
}

function back() {
  step.value = "choice";
  void focusTile(lastTile.value);
}

function dispatch(payload) {
  record(`explore.wait ${JSON.stringify(payload)}`);
  void closeAll();
}

function trapTab(event, root) {
  const nodes = [...root.querySelectorAll("button, input")].filter((el) => !el.disabled);
  if (nodes.length === 0) return;
  const first = nodes[0];
  const last = nodes[nodes.length - 1];
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}

function onChoiceKeydown(event) {
  const keys = tiles.value.map((tile) => tile.key);
  const current = keys.indexOf(document.activeElement?.dataset?.tile);
  if (event.key === "Escape") {
    event.preventDefault();
    void closeAll();
  } else if (event.key === "1" || event.key === "2") {
    event.preventDefault();
    pick(keys[Number(event.key) - 1]);
  } else if (["ArrowRight", "ArrowDown", "ArrowLeft", "ArrowUp"].includes(event.key)) {
    event.preventDefault();
    const delta = event.key === "ArrowRight" || event.key === "ArrowDown" ? 1 : -1;
    void focusTile(keys[(Math.max(current, 0) + delta + keys.length) % keys.length]);
  } else if (event.key === "Home" || event.key === "End") {
    event.preventDefault();
    void focusTile(event.key === "Home" ? keys[0] : keys[keys.length - 1]);
  } else if (event.key === "Tab") {
    trapTab(event, event.currentTarget);
  }
}

function onFormKeydown(event) {
  // The form itself claims Escape (and stops propagation); this catches the
  // header buttons.
  if (event.key === "Escape") {
    event.preventDefault();
    back();
  } else if (event.key === "Tab") {
    trapTab(event, event.currentTarget);
  }
}

onMounted(() => {
  // The real PlaceCard hard-codes 等待; the prototype relabels it in place
  // (the proposal would change the component's text).
  const label = stage.value?.querySelector(".place-card__action--wait .place-card__action-label");
  if (label) label.textContent = props.placeLabel;
  if (step.value === "choice") void focusTile("wait");
});
</script>

<template>
  <div ref="stage" class="proto-stage">
    <div class="proto-stage__map">
      <PlaceCard
        :location-label="locationLabel"
        :time-label="timeLabel"
        actions-enabled
        @wait="openChoice"
      />
    </div>

    <div class="proto-stage__anchor" :style="{ width: `calc(${cardWidth}px * var(--ui-scale))` }">
      <!-- First layer: two choice tiles. -->
      <section
        v-if="step === 'choice'"
        class="choice-card proto-choice"
        :class="{ 'proto-choice--stacked': stacked }"
        role="dialog"
        aria-modal="true"
        aria-labelledby="proto-choice-title"
        @keydown="onChoiceKeydown"
      >
        <span class="choice-card__corners" aria-hidden="true"></span>
        <h2 id="proto-choice-title" class="proto-visually-hidden">等待或睡眠</h2>
        <div class="choice-card__caption" aria-hidden="true">度過時間</div>
        <button
          type="button"
          class="proto-choice__close"
          aria-label="關閉並回到探索"
          title="關閉"
          @click="closeAll"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true">
            <path d="M7 7l10 10M17 7L7 17" />
          </svg>
        </button>
        <div class="proto-choice__tiles">
          <button
            v-for="tile in tiles"
            :key="tile.key"
            :ref="(el) => (tileRefs[tile.key] = el)"
            type="button"
            class="proto-tile"
            :class="`proto-tile--${tile.key}`"
            :data-tile="tile.key"
            :aria-disabled="locked ? 'true' : null"
            :aria-describedby="`proto-tile-${tile.key}-hint${locked ? ' proto-choice-locked' : ''}`"
            @click="pick(tile.key)"
          >
            <span class="proto-tile__badge" aria-hidden="true">{{ tile.digit }}</span>
            <svg
              v-if="tile.key === 'wait'"
              class="proto-tile__icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.6"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <path d="M2.5 12s3.5-6.5 9.5-6.5S21.5 12 21.5 12s-3.5 6.5-9.5 6.5S2.5 12 2.5 12z" />
              <circle cx="12" cy="12" r="3" />
            </svg>
            <svg
              v-else
              class="proto-tile__icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.6"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z" />
              <path d="M16 3.5v3M14.5 5h3" />
            </svg>
            <span class="proto-tile__label">{{ tile.label }}</span>
            <span :id="`proto-tile-${tile.key}-hint`" class="proto-tile__text">
              <span class="proto-tile__hint">{{ tile.hint }}</span>
              <span v-if="tile.context" class="proto-tile__context">
                <span v-for="part in tile.context" :key="part" class="proto-tile__segment">{{ part }}</span>
              </span>
            </span>
          </button>
        </div>
        <p v-if="locked" id="proto-choice-locked" class="proto-choice__locked" role="status">{{ LOCKED_REASON }}</p>
      </section>

      <!-- Second layer: one shell for both forms. -->
      <section
        v-else-if="step === 'wait' || step === 'sleep'"
        class="choice-card proto-form-card"
        role="dialog"
        aria-modal="true"
        aria-labelledby="proto-form-title"
        @keydown="onFormKeydown"
      >
        <span class="choice-card__corners" aria-hidden="true"></span>
        <div id="proto-form-title" class="choice-card__caption">{{ step === "wait" ? "等待" : "睡眠" }}</div>
        <WaitFormPrototype
          v-if="step === 'wait'"
          :disabled="locked"
          @dawn="dispatch({ daypart: 'dawn' })"
          @submit="(seconds) => dispatch({ seconds })"
          @close="back"
        />
        <SleepForm
          v-else
          class="proto-sleep-form"
          :disabled="locked"
          @recover="dispatch({ sleep: true })"
          @submit="(seconds) => dispatch({ sleep: true, sleep_mode: 'duration', seconds })"
          @close="back"
        />
        <!-- After the form in the DOM, so Tab walks the form first. -->
        <button
          type="button"
          class="proto-form-card__corner proto-form-card__corner--back"
          aria-label="返回上一層"
          title="返回上一層"
          @click="back"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M14.5 6l-6 6 6 6" />
          </svg>
        </button>
        <button
          type="button"
          class="proto-form-card__corner proto-form-card__corner--close"
          aria-label="關閉並回到探索"
          title="關閉"
          @click="closeAll"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true">
            <path d="M7 7l10 10M17 7L7 17" />
          </svg>
        </button>
      </section>
    </div>

    <ol class="proto-log" aria-label="送出紀錄（原型）">
      <li v-if="log.length === 0" class="proto-log__empty">尚未送出任何行動。按地點卡的「{{ placeLabel }}」開啟。</li>
      <li v-for="(line, index) in log" :key="`${index}:${line}`">{{ line }}</li>
    </ol>
  </div>
</template>

<style scoped>
.proto-stage {
  position: relative;
  min-height: calc(100vh - var(--header-h));
  display: grid;
  place-items: center;
  padding: calc(24px * var(--ui-scale));
  box-sizing: border-box;
  background:
    linear-gradient(180deg, rgba(11, 13, 16, 0.35), rgba(11, 13, 16, 0.75)),
    url("/art/scenes/city_street.webp") center / cover no-repeat;
}
.proto-stage__map {
  position: absolute;
  top: calc(16px * var(--ui-scale));
  right: calc(16px * var(--ui-scale));
  width: calc(230px * var(--ui-scale));
}
.proto-stage__anchor {
  max-width: 100%;
  display: flex;
  justify-content: center;
}
.proto-visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}

/* --- first layer ---------------------------------------------------------- */
.proto-choice {
  width: 100%;
  padding: 0 calc(14px * var(--ui-scale)) calc(14px * var(--ui-scale));
  gap: calc(10px * var(--ui-scale));
}
.proto-choice__tiles {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: calc(10px * var(--ui-scale));
}
.proto-choice--stacked .proto-choice__tiles {
  grid-template-columns: 1fr;
}
.proto-tile {
  position: relative;
  display: grid;
  grid-template-rows: auto auto 1fr;
  justify-items: center;
  gap: calc(6px * var(--ui-scale));
  min-height: calc(132px * var(--ui-scale));
  padding: calc(16px * var(--ui-scale)) calc(12px * var(--ui-scale)) calc(12px * var(--ui-scale));
  color: var(--paper-100);
  text-align: center;
  background: linear-gradient(180deg, rgba(185, 154, 96, 0.08), rgba(185, 154, 96, 0.02));
  border: 1px solid rgba(185, 154, 96, 0.35);
  border-radius: var(--radius);
  cursor: pointer;
  transition:
    border-color var(--motion-fast) var(--ease-standard),
    background var(--motion-fast) var(--ease-standard);
}
.proto-choice--stacked .proto-tile {
  grid-template-columns: auto 1fr;
  grid-template-rows: auto auto;
  justify-items: start;
  align-items: center;
  column-gap: calc(12px * var(--ui-scale));
  min-height: calc(76px * var(--ui-scale));
  text-align: left;
}
.proto-choice--stacked .proto-tile__icon {
  grid-row: 1 / 3;
}
.proto-tile:hover,
.proto-tile:focus-visible {
  border-color: var(--gold-500);
  background: linear-gradient(180deg, rgba(185, 154, 96, 0.28), rgba(185, 154, 96, 0.08));
  outline: none;
}
.proto-tile:focus-visible {
  box-shadow: 0 0 0 2px var(--gold-400);
}
.proto-tile__badge {
  position: absolute;
  top: calc(8px * var(--ui-scale));
  left: calc(8px * var(--ui-scale));
  display: grid;
  place-items: center;
  width: calc(22px * var(--ui-scale));
  height: calc(22px * var(--ui-scale));
  border: 1px solid rgba(185, 154, 96, 0.7);
  border-radius: var(--radius);
  background: rgba(185, 154, 96, 0.08);
  color: var(--gold-400);
  font: var(--text-sm)/1 var(--f-mono);
}
.proto-tile:focus-visible .proto-tile__badge {
  border-color: var(--gold-400);
  background: linear-gradient(180deg, var(--gold-400), var(--gold-500));
  color: var(--ink-950);
}
.proto-choice--stacked .proto-tile__badge {
  top: 50%;
  left: auto;
  right: calc(10px * var(--ui-scale));
  transform: translateY(-50%);
}
.proto-tile__icon {
  width: calc(30px * var(--ui-scale));
  height: calc(30px * var(--ui-scale));
  color: var(--gold-400);
}
.proto-tile__label {
  font: var(--text-xl)/1.2 var(--f-sans);
  letter-spacing: 0.2em;
  color: var(--paper-50);
}
.proto-tile__text {
  display: grid;
  gap: calc(6px * var(--ui-scale));
  align-content: start;
}
.proto-tile__hint {
  font: var(--text-sm)/1.5 var(--f-sans);
  color: var(--paper-300);
}
.proto-tile__context {
  padding-top: calc(6px * var(--ui-scale));
  border-top: 1px solid rgba(185, 154, 96, 0.2);
  font: var(--text-xs)/1.4 var(--f-mono);
  color: var(--gold-400);
}
/* One line, never split: the numerals keep the mono face, the stage
   label reads in the sans face so the line fits the tile. */
.proto-tile__context {
  white-space: nowrap;
}
.proto-tile__segment + .proto-tile__segment {
  font-family: var(--f-sans);
}
.proto-choice--stacked .proto-tile__context {
  padding-top: 0;
  border-top: 0;
}
.proto-tile[aria-disabled="true"] {
  cursor: not-allowed;
  border-style: dashed;
  border-color: rgba(185, 154, 96, 0.3);
  background: transparent;
}
.proto-tile[aria-disabled="true"] .proto-tile__icon,
.proto-tile[aria-disabled="true"] .proto-tile__label {
  color: var(--paper-400);
}
.proto-tile[aria-disabled="true"] .proto-tile__badge {
  border-style: dashed;
  background: transparent;
  color: var(--paper-400);
}
.proto-choice__locked {
  margin: 0;
  font: var(--text-sm)/1.4 var(--f-sans);
  color: var(--paper-400);
  text-align: center;
}

/* --- corner buttons (QuestionCard's .question-card__close) ------------------ */
.proto-choice__close,
.proto-form-card__corner {
  position: absolute;
  top: calc(8px * var(--ui-scale));
  z-index: 2;
  display: grid;
  place-items: center;
  width: calc(28px * var(--ui-scale));
  height: calc(28px * var(--ui-scale));
  padding: 0;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--paper-400);
  cursor: pointer;
}
.proto-choice__close,
.proto-form-card__corner--close {
  right: calc(8px * var(--ui-scale));
}
.proto-form-card__corner--back {
  left: calc(8px * var(--ui-scale));
}
.proto-choice__close svg,
.proto-form-card__corner svg {
  width: calc(14px * var(--ui-scale));
  height: calc(14px * var(--ui-scale));
}
.proto-form-card__corner--back svg {
  width: calc(16px * var(--ui-scale));
  height: calc(16px * var(--ui-scale));
}
.proto-choice__close:hover,
.proto-choice__close:focus-visible,
.proto-form-card__corner:hover,
.proto-form-card__corner:focus-visible {
  border-color: var(--gold-500);
  color: var(--paper-50);
  outline: none;
}

/* --- second layer ------------------------------------------------------------ */
.proto-form-card {
  width: min(100%, calc(360px * var(--ui-scale)));
  padding: 0 calc(14px * var(--ui-scale)) calc(14px * var(--ui-scale));
  gap: calc(8px * var(--ui-scale));
}
/* The shared header names the form, so SleepForm's own 睡眠模式 line goes
   (the proposed change; hidden here instead of editing the component), and
   the form sits flat in the card like the rest form does. */
.proto-sleep-form {
  background: transparent;
  border: 0;
  padding: calc(4px * var(--ui-scale)) calc(6px * var(--ui-scale)) 0;
}
.proto-sleep-form :deep(.exploration-sleep-caption) {
  display: none;
}
/* The duration reads centred in its field (approved). */
.proto-sleep-form :deep(input) {
  text-align: center;
}

/* --- prototype log ------------------------------------------------------------ */
.proto-log {
  position: absolute;
  left: calc(16px * var(--ui-scale));
  bottom: calc(16px * var(--ui-scale));
  margin: 0;
  padding: calc(8px * var(--ui-scale)) calc(12px * var(--ui-scale));
  list-style: none;
  font: var(--text-xs)/1.6 var(--f-mono);
  color: var(--paper-300);
  background: rgba(11, 13, 16, 0.7);
  border: 1px dashed rgba(185, 154, 96, 0.35);
  border-radius: var(--radius-sm);
}
.proto-log__empty {
  color: var(--paper-400);
}
</style>
