<script setup>
// QuestDetail (quest-drawer-book-tab, design Decision 2): the quest drawer's
// detail column. It renders a view model (quest-drawer-model.js `bookDetail`)
// and a resolved action set (`bookActions`), never a raw row, so the board
// tab can reuse it. Top to bottom: the hero (ribbon, title, objective and
// note, grade gem, completed/failed stamp), one-based progress, the
// rationale and deadline pair, the issuer letter, and the reward cells with
// their settlement note. The action footer (DetailFooter) is pinned to the
// bottom.
//
// A guild board offer (quest-drawer-guild-board-tab, `offerDetail` /
// `offerActions`) uses the same layout: no progress or stamp, the 接取條件
// cell in place of 評價, and the accept descriptor as the primary action. A
// disabled accept stays focusable (aria-disabled) beside its reason and
// emits nothing.
//
// Every action emits `action` with the exact `{action_id, payload}` the
// server descriptor (or the row's track descriptor) names. Abandon needs a
// second confirmation; the armed state belongs to one quest and disarms when
// the selection changes or the abandon descriptor goes away.
import { computed, nextTick, ref, watch } from "vue";
import DetailFooter from "./DetailFooter.vue";
import GradeGem from "./GradeGem.vue";
import { glyphAttrs, glyphPath } from "./dock-icons.js";
import { ABANDON_WARNING } from "./quest-drawer-model.js";

const props = defineProps({
  // bookDetail view model, or null for an empty detail.
  detail: { type: Object, default: null },
  // { track, abandon, turnin, reason } from bookActions.
  actions: { type: Object, default: () => ({ track: null, abandon: null, turnin: null, accept: null, reason: null }) },
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

// The pinned footer (handbook-primitives, design D1) renders through the
// shared DetailFooter; focus moves through its exposed `focus(key)`.
const footerRef = ref(null);
const numberFormat = new Intl.NumberFormat("zh-TW");
const fmt = (value) => numberFormat.format(value);

async function arm() {
  armedId.value = props.detail.id;
  await nextTick();
  footerRef.value?.focus("cancel");
}

async function disarm() {
  armedId.value = null;
  await nextTick();
  footerRef.value?.focus("abandon");
}

function dispatch(descriptor) {
  if (!descriptor) return;
  emit("action", { action_id: descriptor.action_id, payload: { ...descriptor.payload } });
}

async function confirmAbandon() {
  const abandon = props.actions?.abandon;
  armedId.value = null;
  dispatch(abandon);
  // The confirm control leaves the DOM; keep focus inside the drawer on the
  // tracking toggle until the commit replaces the row.
  await nextTick();
  footerRef.value?.focus("track");
}

function accept() {
  const descriptor = props.actions?.accept;
  if (descriptor?.enabled) dispatch(descriptor);
}

function toggleTrack() {
  const track = props.actions?.track;
  if (track?.enabled) dispatch(track);
}

// The footer descriptor. Armed: the danger warning (role alert) with cancel
// and confirm. Otherwise: the action reason, then abandon, the tracking
// toggle, turn-in and accept. The spacer rides the tracking toggle; the
// panel contract (quest_log.py) gives every row a track descriptor, so an
// abandon never appears without the toggle that carries the spacer.
const footer = computed(() => {
  if (armed.value) {
    return {
      reason: ABANDON_WARNING(props.detail.name),
      reasonTone: "danger",
      reasonRole: "alert",
      reasonTestid: "quest-drawer__abandon-confirm",
      buttons: [
        { key: "cancel", label: "取消", tone: "plain", testid: "quest-drawer__abandon-confirm-no" },
        { key: "confirm", label: "確認放棄", tone: "danger", testid: "quest-drawer__abandon-confirm-yes" },
      ],
    };
  }
  const actions = props.actions ?? {};
  const buttons = [];
  if (actions.abandon) {
    buttons.push({ key: "abandon", label: actions.abandon.label, tone: "ghost", testid: "quest-drawer__abandon" });
  }
  if (actions.track) {
    buttons.push({
      key: "track",
      label: actions.track.label,
      tone: "plain",
      pressed: !!actions.track.pressed,
      enabled: !!actions.track.enabled,
      glyph: "track_flag",
      spacerBefore: true,
      testid: "quest-drawer__track",
    });
  }
  if (actions.turnin) {
    buttons.push({ key: "turnin", label: actions.turnin.label, tone: "primary", testid: "quest-drawer__turnin" });
  }
  if (actions.accept) {
    buttons.push({
      key: "accept",
      label: actions.accept.label,
      tone: "primary",
      enabled: !!actions.accept.enabled,
      describedByReason: true,
      testid: "quest-drawer__accept",
    });
  }
  return {
    reason: actions.reason ?? null,
    reasonTone: "plain",
    reasonRole: null,
    reasonTestid: "quest-drawer__action-reason",
    buttons,
  };
});

const PRESS = {
  cancel: disarm,
  confirm: confirmAbandon,
  abandon: arm,
  track: toggleTrack,
  turnin: () => dispatch(props.actions?.turnin),
  accept,
};

function onPress(key) {
  PRESS[key]?.();
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
        <section v-if="detail.condition" class="quest-detail__cell" data-testid="quest-drawer__condition">
          <h4 class="quest-detail__label">接取條件</h4>
          <p class="quest-detail__line">{{ detail.condition.line }}</p>
          <p v-if="detail.condition.text" class="quest-detail__text">{{ detail.condition.text }}</p>
        </section>
        <section v-else-if="detail.rationale" class="quest-detail__cell" data-testid="quest-drawer__rationale">
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

    <DetailFooter ref="footerRef" testid="quest-drawer__actions" v-bind="footer" @press="onPress" />
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

@media (prefers-reduced-motion: reduce) {
  .quest-detail {
    animation: none;
  }
}
</style>
