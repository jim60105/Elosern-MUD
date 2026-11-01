<script setup>
// CampCard (OpenSpec change wilderness-camping; design §5): the one camp
// decision in the `choices` anchor. It renders the store's `view.camp`
// exactly: the server preview's two modes (dawn first) as radio tiles with
// their supplied wake time or refusal, the selected mode's per-member
// current-to-predicted 精力, the 進入夢境協作 checkbox only when the selected
// mode offers it, and 取消 / 全隊紮營. It derives no wake, reserve or
// eligibility of its own.
//
// Keys while the card owns focus: 1 / 2 pick the supplied modes, D toggles
// an offered checkbox, Enter confirms once, Esc cancels; Tab stays inside the
// card (the shared focus-trap contract). Every key it handles is consumed so
// the compass, walk queue and handoff keys underneath never see it.
import { computed, onMounted, ref, useId, watch } from "vue";
import { createFocusTrap } from "../focus-trap.js";

const props = defineProps({
  // `view.camp` (stores/elosern/camp.js `campView`).
  camp: { type: Object, required: true },
  // The committed place line (`<district>・<terrain>`), or null.
  place: { type: String, default: null },
  entrance: { type: Boolean, default: true },
});
const emit = defineEmits(["select", "toggle-dream", "confirm", "cancel"]);

const MODE_LABELS = Object.freeze({ "until-dawn": "睡到天亮", "until-recovered": "睡到精力全滿" });
const MODE_NOTES = Object.freeze({
  "until-dawn": "天亮時拔營，不論精力是否已滿",
  "until-recovered": "最慢恢復的成員睡滿為止",
});
const MODE_GLYPHS = Object.freeze({
  // A rising sun over the horizon, and a full crescent moon.
  "until-dawn": "M3 17h18M6.5 17a5.5 5.5 0 0 1 11 0M12 6.5v2.2M5.6 9.6l1.5 1.5M18.4 9.6l-1.5 1.5",
  "until-recovered": "M15.5 4.2A8 8 0 1 0 19.8 15 6.4 6.4 0 0 1 15.5 4.2Z",
});

const root = ref(null);
const titleId = useId();
const statusId = useId();
let trap = null;

const preview = computed(() => props.camp.preview);
const modes = computed(() => preview.value?.modes ?? []);
const selected = computed(() => props.camp.selectedMode);
const pending = computed(() => props.camp.phase === "previewPending");
const submitting = computed(() => props.camp.phase === "submitting");
const refusedWhole = computed(() => props.camp.phase === "refused");
const title = computed(() => (props.place ? `在${props.place}過夜` : "在此過夜"));
const members = computed(() => (selected.value?.available ? selected.value.members : []));

function pct(value) {
  return Math.max(0, Math.min(100, Number(value) || 0));
}

function onKeydown(event) {
  if (event.ctrlKey || event.altKey || event.metaKey || event.isComposing) return;
  const key = event.key;
  if (key === "Tab") {
    event.stopPropagation();
    trap?.onKeydown(event);
    return;
  }
  if (key === "Escape") {
    event.preventDefault();
    event.stopPropagation();
    if (!event.repeat && !submitting.value) emit("cancel");
    return;
  }
  if (key === "Enter") {
    event.preventDefault();
    event.stopPropagation();
    // A held key repeats; only its first press confirms.
    if (!event.repeat && props.camp.canConfirm) emit("confirm");
    return;
  }
  if (key === "1" || key === "2") {
    event.preventDefault();
    event.stopPropagation();
    const entry = modes.value[Number(key) - 1];
    if (entry) emit("select", entry.mode);
    return;
  }
  if (key === "d" || key === "D") {
    event.preventDefault();
    event.stopPropagation();
    if (props.camp.dreamOffered) emit("toggle-dream");
    return;
  }
  if (key === "ArrowLeft" || key === "ArrowRight" || key === "ArrowUp" || key === "ArrowDown") {
    event.preventDefault();
    event.stopPropagation();
    const index = modes.value.findIndex((entry) => entry.mode === props.camp.selected);
    if (index === -1 || modes.value.length < 2) return;
    const next = modes.value[(index + (key === "ArrowLeft" || key === "ArrowUp" ? modes.value.length - 1 : 1)) % modes.value.length];
    emit("select", next.mode);
    return;
  }
  // Space reaches the focused control natively; every other key stays here.
  if (key !== " ") event.stopPropagation();
}

function focusSelectedTile() {
  const el = root.value?.querySelector('[data-testid="camp-mode"][aria-checked="true"]');
  if (el && el !== document.activeElement) el.focus({ preventScroll: true });
}

onMounted(() => {
  trap = createFocusTrap(root.value, { initialFocusEl: root.value });
  trap.enter();
});

// A phase change that removes the focused control (a refusal replacing the
// tiles) keeps focus inside the card, on its always-present 取消.
watch(
  () => props.camp.phase,
  () => {
    if (typeof document === "undefined") return;
    Promise.resolve().then(() => {
      if (root.value && !root.value.contains(document.activeElement)) {
        root.value.querySelector('[data-testid="camp-card-cancel"]')?.focus({ preventScroll: true });
      }
    });
  },
  { flush: "post" },
);

// Focus follows the server preview's arrival onto the selected tile, and a
// keyboard selection keeps focus on the tile it moved to.
watch(
  () => [props.camp.phase, props.camp.selected],
  ([phase], [previous] = []) => {
    if (phase !== "choosing" || typeof document === "undefined") return;
    const inside = root.value?.contains(document.activeElement);
    if (previous !== "choosing" || inside) Promise.resolve().then(focusSelectedTile);
  },
  { flush: "post" },
);
</script>

<template>
  <section
    ref="root"
    class="choice-card camp-card"
    :class="{ 'choice-card--still': !entrance, 'is-pending': pending }"
    role="dialog"
    aria-modal="true"
    :aria-labelledby="titleId"
    :aria-describedby="statusId"
    :aria-busy="pending || submitting ? 'true' : null"
    tabindex="-1"
    data-testid="camp-card"
    :data-phase="camp.phase"
    @keydown="onKeydown"
  >
    <span class="choice-card__corners" aria-hidden="true"></span>
    <header class="camp-card__head">
      <p class="choice-card__caption camp-card__caption">紮營</p>
      <h2 :id="titleId" class="camp-card__title">{{ title }}</h2>
      <p v-if="preview" class="camp-card__now" data-testid="camp-card-now">{{ preview.current_time }}</p>
    </header>

    <div class="camp-card__body">
    <p v-if="pending" :id="statusId" class="camp-card__status" data-testid="camp-card-pending">正在打理營地…</p>

    <template v-else-if="refusedWhole">
      <p :id="statusId" class="camp-card__refusal" role="alert" data-testid="camp-card-refusal">
        <span class="camp-card__seal" aria-hidden="true">!</span>{{ camp.refusal?.message }}
      </p>
    </template>

    <template v-else>
      <div class="camp-card__modes" role="radiogroup" aria-label="睡到何時" data-testid="camp-card-modes">
        <button
          v-for="(entry, index) in modes"
          :key="entry.mode"
          type="button"
          role="radio"
          class="camp-mode"
          :class="{ 'is-refused': !entry.available }"
          :aria-checked="camp.selected === entry.mode ? 'true' : 'false'"
          :tabindex="camp.selected === entry.mode ? 0 : -1"
          :disabled="submitting"
          data-testid="camp-mode"
          :data-mode="entry.mode"
          :data-available="entry.available ? 'true' : 'false'"
          @click="emit('select', entry.mode)"
        >
          <kbd class="camp-mode__digit" aria-hidden="true">{{ index + 1 }}</kbd>
          <svg class="camp-mode__glyph" viewBox="0 0 24 24" aria-hidden="true"><path :d="MODE_GLYPHS[entry.mode]" /></svg>
          <span class="camp-mode__label">{{ MODE_LABELS[entry.mode] }}</span>
          <span v-if="entry.available" class="camp-mode__when" data-testid="camp-mode-wake">{{ entry.wake_time }} 醒來</span>
          <span v-else class="camp-mode__when camp-mode__when--refused" data-testid="camp-mode-refusal">{{ entry.refusal?.message }}</span>
          <span class="camp-mode__note">{{ MODE_NOTES[entry.mode] }}</span>
        </button>
      </div>

      <p :id="statusId" class="camp-card__sr" aria-live="polite">
        {{ selected ? (selected.available ? `${MODE_LABELS[selected.mode]}，${selected.wake_time} 醒來` : selected.refusal?.message) : "" }}
      </p>

      <ul v-if="members.length" class="camp-card__members" aria-label="醒來時的精力" data-testid="camp-card-members">
        <li v-for="row in members" :key="row.member_id" data-testid="camp-card-member" :data-member="row.member_id">
          <span class="camp-card__name">{{ row.name }}</span>
          <span class="camp-card__bar" aria-hidden="true">
            <span class="camp-card__to" :style="{ width: `${pct(row.predicted_percent)}%` }"></span>
            <span class="camp-card__from" :style="{ width: `${pct(row.current_percent)}%` }"></span>
          </span>
          <span class="camp-card__pct">{{ row.current_percent }}% <span aria-hidden="true">→</span><span class="camp-card__sr">至</span> <b>{{ row.predicted_percent }}%</b></span>
        </li>
      </ul>

    </template>
    </div>

    <footer class="camp-card__foot" :class="{ 'is-single': refusedWhole || pending, 'has-dream': camp.dreamOffered && !refusedWhole && !pending }">
      <label v-if="camp.dreamOffered && !refusedWhole && !pending" class="camp-card__dream" data-testid="camp-card-dream">
        <input
          type="checkbox"
          :checked="camp.dream"
          :disabled="submitting"
          data-testid="camp-card-dream-input"
          @change="emit('toggle-dream', $event.target.checked)"
        />
        <span class="camp-card__check" aria-hidden="true"></span>
        <span class="camp-card__dream-text">進入夢境協作</span>
        <kbd aria-hidden="true">D</kbd>
      </label>
      <button
        type="button"
        class="camp-card__btn"
        data-testid="camp-card-cancel"
        :disabled="submitting"
        @click="emit('cancel')"
      >
        取消 <kbd aria-hidden="true">Esc</kbd>
      </button>
      <button
        v-if="!refusedWhole && !pending"
        type="button"
        class="camp-card__btn camp-card__btn--primary"
        data-testid="camp-card-confirm"
        :disabled="!camp.canConfirm"
        :aria-disabled="camp.canConfirm ? null : 'true'"
        @click="camp.canConfirm && emit('confirm')"
      >
        {{ submitting ? "紮營中…" : "全隊紮營" }} <kbd aria-hidden="true">Enter</kbd>
      </button>
    </footer>
  </section>
</template>

<style>
/* The camp card: the shared card frame (ink panel, gold hairline, corner
   ticks) holding one decision. The two tiles read like the leg panel's pace
   choice; the selected one is lit gold and carries a second inner rim, so the
   choice never rests on colour alone. Text never drops under --text-xs. */
.camp-card.choice-card {
  position: relative;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: calc(10px * var(--ui-scale));
  align-self: center;
  width: min(100%, calc(600px * var(--ui-scale)));
  max-height: 100%;
  padding: 0 calc(22px * var(--ui-scale)) calc(16px * var(--ui-scale));
  overflow: hidden;
  background:
    radial-gradient(90% 46% at 50% 0%, rgba(228, 200, 142, 0.09), transparent 70%),
    radial-gradient(120% 60% at 50% 100%, rgba(216, 120, 60, 0.07), transparent 72%),
    linear-gradient(180deg, rgba(20, 20, 25, 0.98), rgba(11, 12, 16, 0.98));
  border: 1px solid rgba(185, 154, 96, 0.5);
  border-radius: var(--radius);
  box-shadow:
    var(--shadow-lg),
    0 0 0 100vmax rgba(6, 7, 10, 0.34),
    inset 0 0 0 1px rgba(0, 0, 0, 0.55);
  outline: none;
  pointer-events: auto;
}
.camp-card.choice-card:focus-visible {
  box-shadow: var(--shadow-lg), 0 0 0 100vmax rgba(6, 7, 10, 0.34), var(--focus);
}
/* The head and the footer stay put; only the body scrolls when the stage is
   short, so 全隊紮營 is always on screen. */
.camp-card__head,
.camp-card__foot {
  flex: none;
}
.camp-card__body {
  display: flex;
  flex-direction: column;
  gap: calc(10px * var(--ui-scale));
  flex: 1 1 auto;
  min-height: 0;
  overflow: hidden auto;
  margin: 0 calc(-6px * var(--ui-scale));
  padding: calc(2px * var(--ui-scale)) calc(6px * var(--ui-scale));
  scrollbar-width: thin;
}
.camp-card__head {
  display: grid;
  justify-items: center;
  gap: calc(2px * var(--ui-scale));
  text-align: center;
}
.camp-card__caption.choice-card__caption {
  margin: 0;
  padding: calc(12px * var(--ui-scale)) 0 0;
}
.camp-card__title {
  margin: 0;
  font: var(--text-xl)/1.25 var(--f-display);
  color: var(--paper-50);
  text-shadow: 0 1px 0 #000;
}
.camp-card__now {
  margin: 0;
  font: var(--text-xs)/1.4 var(--f-sans);
  color: var(--paper-400);
  font-variant-numeric: tabular-nums;
}
.camp-card__status {
  margin: calc(6px * var(--ui-scale)) 0;
  text-align: center;
  font: var(--text-sm)/1.6 var(--f-serif);
  color: var(--paper-300);
  animation: camp-card-breathe var(--motion-pending) ease-in-out infinite;
}
.camp-card__refusal {
  display: flex;
  align-items: flex-start;
  gap: calc(10px * var(--ui-scale));
  margin: 0;
  padding: calc(12px * var(--ui-scale)) calc(14px * var(--ui-scale));
  border: 1px solid rgba(178, 74, 58, 0.55);
  border-radius: calc(6px * var(--ui-scale));
  background: rgba(60, 20, 16, 0.45);
  font: var(--text-sm)/1.6 var(--f-serif);
  color: var(--paper-100);
}
.camp-card__seal {
  flex: none;
  display: grid;
  place-items: center;
  width: calc(22px * var(--ui-scale));
  height: calc(22px * var(--ui-scale));
  border-radius: 50%;
  background: #8c2f24;
  color: var(--paper-50);
  font: 700 var(--text-xs)/1 var(--f-sans);
}
.camp-card__modes {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: calc(10px * var(--ui-scale));
}
.camp-mode {
  position: relative;
  display: grid;
  grid-template-columns: auto 1fr;
  grid-template-areas: "glyph label" "when when" "note note";
  align-items: center;
  column-gap: calc(8px * var(--ui-scale));
  row-gap: calc(3px * var(--ui-scale));
  padding: calc(10px * var(--ui-scale)) calc(12px * var(--ui-scale));
  border: 1px solid rgba(143, 113, 60, 0.45);
  border-radius: calc(6px * var(--ui-scale));
  background: rgba(11, 13, 16, 0.6);
  color: var(--paper-300);
  text-align: left;
  cursor: pointer;
  transition:
    border-color var(--motion-fast) var(--ease-standard),
    background var(--motion-fast) var(--ease-standard),
    transform var(--motion-fast) var(--ease-standard);
}
.camp-mode:hover {
  border-color: rgba(228, 200, 142, 0.7);
}
.camp-mode[aria-checked="true"] {
  border-color: var(--gold-400);
  background: linear-gradient(180deg, rgba(185, 154, 96, 0.24), rgba(143, 113, 60, 0.08));
  box-shadow: inset 0 0 0 1px rgba(228, 200, 142, 0.28), 0 0 calc(18px * var(--ui-scale)) -6px rgba(228, 200, 142, 0.45);
  color: var(--paper-100);
}
.camp-mode:focus-visible {
  outline: none;
  box-shadow: var(--focus);
}
.camp-mode.is-refused {
  border-style: dashed;
  background: rgba(11, 13, 16, 0.4);
}
.camp-mode.is-refused[aria-checked="true"] {
  border-color: rgba(178, 74, 58, 0.7);
  background: rgba(50, 18, 14, 0.35);
}
.camp-mode__digit {
  position: absolute;
  right: calc(10px * var(--ui-scale));
  top: calc(8px * var(--ui-scale));
  font: var(--text-xs)/1 var(--f-sans);
  color: var(--paper-500);
}
.camp-mode__glyph {
  grid-area: glyph;
  width: calc(22px * var(--ui-scale));
  height: calc(22px * var(--ui-scale));
  fill: none;
  stroke: var(--gold-400);
  stroke-width: 1.5;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.camp-mode.is-refused .camp-mode__glyph {
  stroke: var(--paper-500);
}
.camp-mode__label {
  grid-area: label;
  font: var(--text-lg)/1.2 var(--f-serif);
  color: var(--paper-50);
}
.camp-mode__when {
  grid-area: when;
  font: var(--text-sm)/1.3 var(--f-sans);
  color: var(--gold-300);
  font-variant-numeric: tabular-nums;
}
.camp-mode__when--refused {
  color: #e7a596;
}
.camp-mode__note {
  grid-area: note;
  font: var(--text-xs)/1.4 var(--f-sans);
  color: var(--paper-400);
}
.camp-card__members {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(calc(200px * var(--ui-scale)), 1fr));
  gap: calc(6px * var(--ui-scale)) calc(18px * var(--ui-scale));
  margin: 0;
  padding: calc(8px * var(--ui-scale)) calc(4px * var(--ui-scale));
  border-top: 1px solid rgba(185, 154, 96, 0.22);
  border-bottom: 1px solid rgba(185, 154, 96, 0.22);
  list-style: none;
}
.camp-card__members li {
  display: grid;
  grid-template-columns: calc(44px * var(--ui-scale)) 1fr auto;
  align-items: center;
  gap: calc(10px * var(--ui-scale));
  font: var(--text-xs)/1.3 var(--f-sans);
  color: var(--paper-400);
}
.camp-card__name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: var(--f-serif);
  color: var(--paper-100);
}
.camp-card__bar {
  position: relative;
  height: calc(7px * var(--ui-scale));
  border-radius: 999px;
  background: rgba(36, 38, 42, 0.95);
  box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.6);
  overflow: hidden;
}
.camp-card__to,
.camp-card__from {
  position: absolute;
  inset: 0 auto 0 0;
  border-radius: inherit;
}
.camp-card__to {
  background: repeating-linear-gradient(90deg, rgba(228, 200, 142, 0.55) 0 4px, rgba(228, 200, 142, 0.22) 4px 7px);
}
.camp-card__from {
  z-index: 1;
  background: linear-gradient(90deg, #a98432, var(--vit-sp));
}
.camp-card__pct {
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.camp-card__pct b {
  color: var(--gold-300);
  font-weight: 600;
}
.camp-card__dream {
  position: relative;
  display: flex;
  align-items: center;
  gap: calc(10px * var(--ui-scale));
  align-self: center;
  padding: calc(4px * var(--ui-scale)) calc(8px * var(--ui-scale)) calc(4px * var(--ui-scale)) 0;
  border-radius: calc(6px * var(--ui-scale));
  font: var(--text-sm)/1.2 var(--f-serif);
  color: var(--paper-200, var(--paper-100));
  cursor: pointer;
}
.camp-card__dream input {
  position: absolute;
  opacity: 0;
  width: 1px;
  height: 1px;
}
.camp-card__dream kbd {
  font: var(--text-xs)/1 var(--f-sans);
  color: var(--paper-500);
}
.camp-card__check {
  display: grid;
  place-items: center;
  width: calc(20px * var(--ui-scale));
  height: calc(20px * var(--ui-scale));
  border-radius: 4px;
  border: 1px solid var(--gold-500);
  background: rgba(11, 13, 16, 0.7);
}
.camp-card__dream input:checked + .camp-card__check {
  background: rgba(185, 154, 96, 0.25);
}
.camp-card__dream input:checked + .camp-card__check::after {
  content: "";
  width: 55%;
  height: 30%;
  border-left: 2px solid var(--gold-300);
  border-bottom: 2px solid var(--gold-300);
  transform: rotate(-45deg) translate(1px, -1px);
}
.camp-card__dream input:focus-visible + .camp-card__check {
  box-shadow: var(--focus);
}
.camp-card__foot {
  display: grid;
  grid-template-columns: 1fr 1.6fr;
  gap: calc(10px * var(--ui-scale));
}
.camp-card__foot.has-dream {
  grid-template-columns: auto 1fr 1.4fr;
  align-items: center;
}
.camp-card__foot.is-single {
  grid-template-columns: 1fr;
}
.camp-card__btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: calc(8px * var(--ui-scale));
  min-height: calc(40px * var(--ui-scale));
  padding: 0 calc(14px * var(--ui-scale));
  border: 1px solid rgba(185, 154, 96, 0.5);
  border-radius: calc(6px * var(--ui-scale));
  background: rgba(11, 13, 16, 0.7);
  color: var(--paper-100);
  font: var(--text-sm)/1 var(--f-serif);
  cursor: pointer;
  transition: border-color var(--motion-fast) var(--ease-standard), background var(--motion-fast) var(--ease-standard);
}
.camp-card__btn kbd {
  font: var(--text-xs)/1 var(--f-sans);
  color: var(--paper-500);
}
.camp-card__btn:hover:not(:disabled) {
  border-color: var(--gold-400);
}
.camp-card__btn:focus-visible {
  outline: none;
  box-shadow: var(--focus);
}
.camp-card__btn--primary {
  border-color: var(--gold-400);
  background: linear-gradient(180deg, rgba(228, 200, 142, 0.32), rgba(185, 154, 96, 0.16));
  color: var(--paper-50);
}
.camp-card__btn--primary kbd {
  color: var(--gold-300);
}
.camp-card__btn:disabled {
  cursor: not-allowed;
  opacity: 0.5;
  border-style: dashed;
}
.camp-card__sr {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}
.camp-card__pct .camp-card__sr {
  position: absolute;
}
@keyframes camp-card-breathe {
  50% {
    opacity: 0.55;
  }
}
@media (prefers-reduced-motion: reduce) {
  .camp-card__status {
    animation: none;
  }
}
</style>
