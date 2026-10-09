<script setup>
// QuestDetail (quest-drawer-book-tab, design Decision 2): the quest drawer's
// detail column. It renders a view model (quest-drawer-model.js `bookDetail`)
// and a resolved action set (`bookActions`), never a raw row, so the board
// tab can reuse it. Top to bottom: the hero (ribbon, title, objective and
// note, grade gem, completed/failed stamp), one-based progress, the
// rationale and deadline pair, the issuer letter, and the reward cells with
// their settlement note. The action bar is pinned to the bottom.
//
// Every action emits `action` with the exact `{action_id, payload}` the
// server descriptor (or the row's track descriptor) names. Abandon needs a
// second confirmation; the armed state belongs to one quest and disarms when
// the selection changes or the abandon descriptor goes away.
import { computed, nextTick, ref, watch } from "vue";
import GradeGem from "./GradeGem.vue";
import { glyphAttrs, glyphPath } from "./dock-icons.js";
import { ABANDON_WARNING } from "./quest-drawer-model.js";

const props = defineProps({
  // bookDetail view model, or null for an empty detail.
  detail: { type: Object, default: null },
  // { track, abandon, turnin, reason } from bookActions.
  actions: { type: Object, default: () => ({ track: null, abandon: null, turnin: null, reason: null }) },
});

const emit = defineEmits(["action"]);

const armedId = ref(null);
const armed = computed(() => !!props.detail && armedId.value === props.detail.id && !!props.actions?.abandon);

watch(
  () => [props.detail?.id ?? null, !!props.actions?.abandon],
  () => {
    if (!armed.value) armedId.value = null;
  },
);

const abandonButton = ref(null);
const cancelButton = ref(null);
const numberFormat = new Intl.NumberFormat("zh-TW");
const fmt = (value) => numberFormat.format(value);

async function arm() {
  armedId.value = props.detail.id;
  await nextTick();
  cancelButton.value?.focus();
}

async function disarm() {
  armedId.value = null;
  await nextTick();
  abandonButton.value?.focus();
}

function dispatch(descriptor) {
  if (!descriptor) return;
  emit("action", { action_id: descriptor.action_id, payload: { ...descriptor.payload } });
}

const trackButton = ref(null);

async function confirmAbandon() {
  const abandon = props.actions?.abandon;
  armedId.value = null;
  dispatch(abandon);
  // The confirm control leaves the DOM; keep focus inside the drawer on the
  // tracking toggle until the commit replaces the row.
  await nextTick();
  trackButton.value?.focus();
}

function toggleTrack() {
  const track = props.actions?.track;
  if (track?.enabled) dispatch(track);
}
</script>

<template>
  <article v-if="detail" :key="detail.id" class="quest-detail" data-testid="quest-drawer__detail" :data-quest-id="detail.id">
    <div class="quest-detail__scroll">
      <header class="quest-detail__hero">
        <span class="quest-detail__ribbon" data-testid="quest-drawer__ribbon">
          <svg v-if="detail.ribbon.glyph" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path :d="glyphPath(detail.ribbon.glyph)" stroke="currentColor" stroke-width="1.6" v-bind="glyphAttrs(detail.ribbon.glyph)" />
          </svg>
          {{ detail.ribbon.label }}
        </span>
        <h3 class="quest-detail__title">{{ detail.name }}</h3>
        <p class="quest-detail__objective">{{ detail.objective }}</p>
        <p v-if="detail.note" class="quest-detail__note">{{ detail.note }}</p>
        <GradeGem
          v-if="detail.grade"
          class="quest-detail__gem"
          :grade="detail.grade"
          size="lg"
          :label="`${detail.grade} 級`"
        />
        <span
          v-if="detail.stamp"
          class="quest-detail__stamp"
          :class="`quest-detail__stamp--${detail.stamp.kind}`"
          data-testid="quest-drawer__stamp"
        >{{ detail.stamp.label }}</span>
      </header>

      <section v-if="detail.progress" class="quest-detail__progress" aria-label="進度" data-testid="quest-drawer__progress">
        <div class="quest-detail__progress-meta">
          <span data-testid="quest-drawer__stage">階段 {{ detail.progress.stage }} / {{ detail.progress.stages }}</span>
          <b>{{ detail.progress.value }}<small> / {{ detail.progress.target }}</small></b>
        </div>
        <div v-if="detail.progress.mode === 'pips'" class="quest-detail__pips" data-testid="quest-drawer__pips" aria-hidden="true">
          <span v-for="i in detail.progress.target" :key="i" :class="{ 'is-on': i <= detail.progress.value }"></span>
        </div>
        <div v-else class="quest-detail__bar" data-testid="quest-drawer__bar" aria-hidden="true">
          <span :style="{ width: `${detail.progress.pct}%` }"></span>
        </div>
      </section>

      <div class="quest-detail__cond">
        <section v-if="detail.rationale" class="quest-detail__cell" data-testid="quest-drawer__rationale">
          <h4 class="quest-detail__label">評價</h4>
          <p class="quest-detail__text">{{ detail.rationale }}</p>
        </section>
        <section class="quest-detail__cell" data-testid="quest-drawer__deadline">
          <h4 class="quest-detail__label">期限</h4>
          <p class="quest-detail__line">
            <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path :d="glyphPath('deadline')" stroke="currentColor" stroke-width="1.6" v-bind="glyphAttrs('deadline')" />
            </svg>
            {{ detail.deadline.line }}
          </p>
          <p class="quest-detail__text">{{ detail.deadline.note }}</p>
        </section>
      </div>

      <section class="quest-detail__client" data-testid="quest-drawer__issuer">
        <h4 class="quest-detail__label">委託人</h4>
        <p class="quest-detail__client-name">{{ detail.issuer.label }}</p>
        <p v-if="detail.issuer.letter" class="quest-detail__letter">{{ detail.issuer.letter }}</p>
        <p v-else class="quest-detail__letter quest-detail__letter--muted">{{ detail.issuer.fallback }}</p>
        <svg class="quest-detail__mark" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path :d="glyphPath('guild_counter')" stroke="currentColor" stroke-width="1" v-bind="glyphAttrs('guild_counter')" />
        </svg>
      </section>

      <section v-if="detail.reward" class="quest-detail__reward" aria-label="報酬" data-testid="quest-drawer__reward">
        <h4 class="quest-detail__label">報酬</h4>
        <ul class="quest-detail__reward-list">
          <li v-for="cell in detail.reward.cells" :key="cell.kind === 'item' ? `item:${cell.key}` : cell.kind">
            <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path :d="glyphPath(cell.glyph)" stroke="currentColor" stroke-width="1.6" v-bind="glyphAttrs(cell.glyph)" />
            </svg>
            <template v-if="cell.kind === 'item'">
              <span>{{ cell.name }}</span><b>× {{ fmt(cell.quantity) }}</b>
            </template>
            <template v-else>
              <b>{{ fmt(cell.value) }}</b><span>{{ cell.unit }}</span>
            </template>
          </li>
        </ul>
        <p v-if="detail.reward.settlement" class="quest-detail__settle" data-testid="quest-drawer__settlement">
          {{ detail.reward.settlement }}
        </p>
      </section>
    </div>

    <footer class="quest-detail__actions" data-testid="quest-drawer__actions">
      <template v-if="armed">
        <p
          class="quest-detail__why quest-detail__why--danger"
          data-testid="quest-drawer__abandon-confirm"
          role="alert"
        >{{ ABANDON_WARNING(detail.name) }}</p>
        <button
          ref="cancelButton"
          type="button"
          class="quest-detail__btn"
          data-testid="quest-drawer__abandon-confirm-no"
          @click="disarm"
        >取消</button>
        <button
          type="button"
          class="quest-detail__btn quest-detail__btn--danger"
          data-testid="quest-drawer__abandon-confirm-yes"
          @click="confirmAbandon"
        >確認放棄</button>
      </template>
      <template v-else>
        <p v-if="actions.reason" class="quest-detail__why" data-testid="quest-drawer__action-reason">{{ actions.reason }}</p>
        <button
          v-if="actions.abandon"
          ref="abandonButton"
          type="button"
          class="quest-detail__btn quest-detail__btn--ghost"
          data-testid="quest-drawer__abandon"
          @click="arm"
        >{{ actions.abandon.label }}</button>
        <span v-if="actions.abandon || actions.track" class="quest-detail__spacer"></span>
        <button
          v-if="actions.track"
          ref="trackButton"
          type="button"
          class="quest-detail__btn"
          :class="{ 'is-on': actions.track.pressed }"
          :aria-pressed="String(actions.track.pressed)"
          :disabled="!actions.track.enabled"
          data-testid="quest-drawer__track"
          @click="toggleTrack"
        >
          <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path :d="glyphPath('track_flag')" stroke="currentColor" stroke-width="1.6" v-bind="glyphAttrs('track_flag')" />
          </svg>
          {{ actions.track.label }}
        </button>
        <button
          v-if="actions.turnin"
          type="button"
          class="quest-detail__btn quest-detail__btn--primary"
          data-testid="quest-drawer__turnin"
          @click="dispatch(actions.turnin)"
        >{{ actions.turnin.label }}</button>
      </template>
    </footer>
  </article>
  <div v-else class="quest-detail quest-detail--empty" data-testid="quest-drawer__detail-empty"></div>
</template>

<style scoped>
/* Port of the approved prototype's `.qd-detail` rules
   (docs/design/quest-drawer-redesign/QuestDrawerPrototype.vue). */
.quest-detail {
  --quest-detail-line: rgba(185, 154, 96, 0.28);
  position: relative;
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto;
  min-width: 0;
  min-height: 0;
  height: 100%;
  box-sizing: border-box;
  font-family: var(--f-sans);
  background:
    radial-gradient(90% 60% at 100% 0%, rgba(169, 50, 42, 0.08), transparent 70%),
    #121418;
  animation: quest-detail-in var(--motion-reveal) ease-out;
}

.quest-detail--empty {
  animation: none;
}

@keyframes quest-detail-in {
  from {
    opacity: 0;
    transform: translateX(6px);
  }
}

.quest-detail__scroll {
  display: flex;
  flex-direction: column;
  gap: var(--sp-5);
  min-height: 0;
  overflow-y: auto;
  padding: var(--sp-5) var(--sp-8) var(--sp-6);
  scrollbar-width: thin;
  scrollbar-color: var(--ink-600) transparent;
}

.quest-detail__scroll > * {
  flex-shrink: 0;
}

.quest-detail__hero {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  padding-right: calc(96px * var(--ui-scale));
}

.quest-detail__ribbon {
  align-self: flex-start;
  display: inline-flex;
  align-items: center;
  gap: var(--sp-2);
  padding: 3px calc(22px * var(--ui-scale)) 3px var(--sp-3);
  color: var(--paper-50);
  font: var(--text-xs) var(--f-display);
  letter-spacing: 0.12em;
  background: linear-gradient(180deg, var(--seal-600), var(--seal-700));
  clip-path: polygon(0 0, 100% 0, calc(100% - 10px) 50%, 100% 100%, 0 100%);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.12);
}

.quest-detail__ribbon svg {
  width: 1.1em;
  height: 1.1em;
  color: var(--gold-300);
}

.quest-detail__title {
  margin: var(--sp-1) 0 0;
  color: var(--paper-50);
  font: var(--text-3xl) / 1.25 var(--f-display);
  letter-spacing: 0.04em;
  text-shadow: 0 2px 12px rgba(0, 0, 0, 0.6);
}

.quest-detail__objective {
  margin: 0;
  color: var(--gold-400);
  font: var(--text-lg) / 1.5 var(--f-serif);
}

.quest-detail__note {
  margin: 0;
  color: var(--paper-500);
  font-size: var(--text-xs);
}

.quest-detail__gem {
  position: absolute;
  top: 0;
  right: 0;
}

.quest-detail__stamp {
  position: absolute;
  right: calc(76px * var(--ui-scale));
  top: calc(54px * var(--ui-scale));
  padding: 2px var(--sp-3);
  color: var(--seal-400);
  font: var(--text-xl) var(--f-display);
  letter-spacing: 0.3em;
  border: 3px double var(--seal-500);
  border-radius: var(--radius-sm);
  transform: rotate(-12deg);
  opacity: 0.85;
  mix-blend-mode: screen;
  pointer-events: none;
}

.quest-detail__stamp--failed {
  color: var(--paper-500);
  border-color: var(--paper-700);
}

.quest-detail__label {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  margin: 0 0 var(--sp-2);
  color: var(--gold-500);
  font: var(--text-xs) var(--f-display);
  letter-spacing: 0.18em;
}

.quest-detail__label::after {
  content: "";
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, var(--quest-detail-line), transparent);
}

.quest-detail__progress {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}

.quest-detail__progress-meta {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  color: var(--paper-400);
  font-size: var(--text-xs);
}

.quest-detail__progress-meta b {
  color: var(--paper-50);
  font: 400 var(--text-xl) var(--f-num);
  font-variant-numeric: tabular-nums;
}

.quest-detail__progress-meta small {
  color: var(--paper-500);
  font-size: var(--text-xs);
}

.quest-detail__pips {
  display: flex;
  gap: var(--sp-2);
}

.quest-detail__pips span {
  flex: 1;
  max-width: calc(64px * var(--ui-scale));
  height: calc(10px * var(--ui-scale));
  background: #0b0d10;
  border: 1px solid var(--ink-600);
  clip-path: polygon(6px 0, 100% 0, calc(100% - 6px) 100%, 0 100%);
}

.quest-detail__pips span.is-on {
  background: linear-gradient(90deg, var(--gold-600), var(--gold-400));
  border-color: var(--gold-500);
  box-shadow: 0 0 8px var(--gold-glow);
}

.quest-detail__bar {
  height: 8px;
  overflow: hidden;
  background: #0b0d10;
  border: 1px solid var(--ink-600);
  border-radius: 8px;
}

.quest-detail__bar span {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, var(--gold-600), var(--gold-400));
}

.quest-detail__cond {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--sp-6);
}

.quest-detail__cell {
  min-width: 0;
}

.quest-detail__line {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  margin: 0 0 var(--sp-1);
  color: var(--paper-50);
  font-size: var(--text-md);
}

.quest-detail__line svg {
  flex: none;
  width: 1.1em;
  height: 1.1em;
  color: var(--gold-500);
}

.quest-detail__text {
  margin: 0;
  color: var(--paper-300);
  font-size: var(--text-sm);
  line-height: 1.75;
}

.quest-detail__client {
  position: relative;
  overflow: hidden;
  padding: var(--sp-4) var(--sp-5) var(--sp-5);
  background: linear-gradient(135deg, rgba(185, 154, 96, 0.09), rgba(185, 154, 96, 0.02) 60%);
  border: 1px solid var(--quest-detail-line);
  border-left: 3px solid var(--gold-500);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
}

.quest-detail__client-name {
  margin: 0 0 var(--sp-2);
  color: var(--paper-50);
  font: var(--text-md) var(--f-serif);
}

.quest-detail__letter {
  position: relative;
  z-index: 1;
  max-width: 40em;
  margin: 0;
  color: var(--paper-200);
  font: var(--text-sm) / 1.9 var(--f-serif);
}

.quest-detail__letter--muted {
  color: var(--paper-500);
}

.quest-detail__mark {
  position: absolute;
  right: calc(-8px * var(--ui-scale));
  bottom: calc(-18px * var(--ui-scale));
  width: calc(130px * var(--ui-scale));
  height: calc(130px * var(--ui-scale));
  color: var(--gold-500);
  opacity: 0.09;
}

.quest-detail__reward-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.quest-detail__reward-list li {
  display: inline-flex;
  align-items: baseline;
  gap: var(--sp-2);
  padding: var(--sp-2) var(--sp-4);
  color: var(--paper-300);
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid var(--ink-700);
  border-radius: var(--radius-sm);
}

.quest-detail__reward-list svg {
  align-self: center;
  width: calc(18px * var(--ui-scale));
  height: calc(18px * var(--ui-scale));
  color: var(--gold-400);
}

.quest-detail__reward-list b {
  color: var(--paper-50);
  font: 400 var(--text-md) var(--f-num);
  font-variant-numeric: tabular-nums;
}

.quest-detail__settle {
  margin: var(--sp-2) 0 0;
  color: var(--paper-500);
  font-size: var(--text-xs);
}

.quest-detail__actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--sp-3);
  box-sizing: border-box;
  min-height: calc(64px * var(--ui-scale));
  padding: var(--sp-3) var(--sp-8);
  background: linear-gradient(180deg, rgba(0, 0, 0, 0.15), rgba(0, 0, 0, 0.4));
  border-top: 1px solid var(--quest-detail-line);
}

.quest-detail__spacer {
  flex: 1;
}

.quest-detail__why {
  margin: 0 auto 0 0;
  color: var(--paper-400);
  font-size: var(--text-sm);
}

.quest-detail__why--danger {
  color: var(--seal-400);
}

.quest-detail__btn {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-2);
  padding: var(--sp-2) var(--sp-5);
  color: var(--paper-100);
  font: var(--text-md) var(--f-display);
  letter-spacing: 0.08em;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--ink-600);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: border-color var(--motion-fast) ease, color var(--motion-fast) ease, background-color var(--motion-fast) ease;
}

.quest-detail__btn svg {
  width: 1em;
  height: 1em;
}

.quest-detail__btn:hover:not(:disabled) {
  color: var(--paper-50);
  border-color: var(--gold-500);
}

.quest-detail__btn:focus-visible {
  outline: none;
  box-shadow: var(--focus);
}

.quest-detail__btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.quest-detail__btn.is-on {
  color: var(--gold-300);
  background: var(--gold-glow);
  border-color: var(--gold-500);
}

.quest-detail__btn.is-on svg {
  fill: rgba(228, 200, 142, 0.35);
}

.quest-detail__btn--primary {
  justify-content: center;
  min-width: calc(160px * var(--ui-scale));
  color: var(--paper-50);
  background: linear-gradient(180deg, var(--seal-600), var(--seal-700));
  border-color: var(--gold-500);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.14), 0 0 14px var(--seal-glow);
}

.quest-detail__btn--primary:hover:not(:disabled) {
  background: linear-gradient(180deg, var(--seal-500), var(--seal-600));
}

.quest-detail__btn--ghost {
  color: var(--paper-400);
  background: transparent;
  border-color: transparent;
}

.quest-detail__btn--ghost:hover:not(:disabled) {
  color: var(--seal-400);
  border-color: rgba(207, 68, 68, 0.4);
}

.quest-detail__btn--danger {
  color: var(--paper-50);
  background: var(--seal-700);
  border-color: var(--seal-500);
}

@media (prefers-reduced-motion: reduce) {
  .quest-detail {
    animation: none;
  }

  .quest-detail__btn {
    transition: none;
  }
}
</style>
