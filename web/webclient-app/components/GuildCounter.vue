<script setup>
// GuildCounter (quest-issuer-model change 11, design D2): the guild counter
// surface of the split quest drawer — what genuinely belongs to the counter
// itself: registration, the quest board (接取), and guild rank with the
// promotion examination. It is a host, not a data source: it renders only the
// committed `services` v5 payload's guild section and invents nothing.
//
// It deliberately does NOT render the guild section's `quests` rows: the
// holder's accepted quest records live in the quest book (QuestLog), so no
// quest is presented twice in one drawer.
import { computed, useId } from "vue";

const props = defineProps({
  // The committed `services` v5 panel payload.
  services: { type: Object, required: true },
});

const emit = defineEmits(["quest_register", "quest_accept", "exam_request"]);

// The registry-owned unavailable form carries only `reason` — the guild
// section is absent, so no invented board/rank content. A present panel with
// no guild section (no local clerk) renders the honest absent marker; the
// drawer composition normally gates this component on guild availability and
// renders its own markers, so these forms are the component's standalone
// honesty (stories feed them directly).
const unavailable = computed(() => props.services?.available === false);
const guild = computed(() => (unavailable.value ? null : (props.services?.guild ?? null)));
const registration = computed(() => guild.value?.registration ?? null);
const boardRows = computed(() => guild.value?.board ?? []);
const rank = computed(() => guild.value?.rank ?? null);

// The promotion line renders next_rank / next_threshold only when the
// payload carries both (nullable pair per the bounded schema); a terminal
// rank (both null) degrades to the 最高等級 treatment instead of printing a
// fabricated "null" or an empty meter.
const hasNextStep = computed(
  () => rank.value?.next_rank != null && rank.value?.next_threshold != null,
);

// The 最高等級 treatment needs a held rank: an unranked holder (no rank, no
// next step) is not "at the top".
const isTopRank = computed(() => rank.value?.rank != null && !hasNextStep.value);

const numberFormat = new Intl.NumberFormat("zh-TW");
const fmt = (n) => numberFormat.format(Number.isFinite(n) ? n : 0);

const merit = computed(() => Math.max(0, Number(rank.value?.merit) || 0));
const threshold = computed(() => (hasNextStep.value ? Math.max(1, Number(rank.value.next_threshold) || 1) : null));
// The fill is clamped to the bar: merit past the threshold reads "full",
// never an overflowing bar; aria-valuenow is clamped the same way so it stays
// inside [valuemin, valuemax] while valuetext carries the true count.
const meterNow = computed(() => (threshold.value == null ? 0 : Math.min(merit.value, threshold.value)));
const meterPercent = computed(() =>
  threshold.value == null ? 0 : Math.round((meterNow.value / threshold.value) * 1000) / 10,
);
const shortfall = computed(() => (threshold.value == null ? 0 : Math.max(0, threshold.value - merit.value)));

// merit_qualified is the server's honest merit verdict and is independent of
// whether the counter will take an exam request (exam_request.enabled).
const qualified = computed(() => rank.value?.merit_qualified === true);
const examRequest = computed(() => rank.value?.exam_request ?? null);
const examEnabled = computed(() => examRequest.value?.enabled === true);

// A disabled native button leaves the tab order, so its reason is rendered
// as visible text and also wired as the button's accessible description.
const uid = useId();
const examHintId = `guild-counter-exam-hint-${uid}`;
const examReasonId = `guild-counter-exam-reason-${uid}`;
const examDescribedBy = computed(() => {
  if (examEnabled.value) return examHintId;
  return examRequest.value?.disabled_reason ? examReasonId : undefined;
});

function requestExam() {
  if (!examEnabled.value) return;
  emit("exam_request", {
    action_id: examRequest.value.action_id,
    payload: { target_rank: rank.value.next_rank },
  });
}
</script>

<template>
  <section class="guild-counter" data-testid="guild-counter">
    <h3 class="guild-counter__title" data-testid="guild-counter__title">公會櫃台</h3>

    <p
      v-if="unavailable"
      class="guild-counter__unavailable"
      data-testid="guild-counter__unavailable"
      :data-reason-code="services.reason?.code"
    >
      {{ services.reason?.message }}
    </p>

    <p v-else-if="!guild" class="guild-counter__absent" data-testid="guild-counter__absent">
      尚未取得公會資料
    </p>

    <template v-if="guild">
      <p
        v-if="registration"
        class="guild-counter__registration"
        data-testid="guild-counter__registration"
        :data-registered="String(registration.registered)"
      >
        <span class="guild-counter__registration-state">
          {{ registration.registered ? "已加入公會" : "未加入公會" }}
        </span>
          <button
            v-if="registration.register && registration.register.enabled"
            type="button"
            class="guild-counter__action"
            data-testid="guild-counter__register"
            @click="emit('quest_register', { action_id: registration.register.action_id })"
          >
            {{ registration.register.label }}
          </button>
        <span
          v-if="registration.register && !registration.register.enabled && registration.register.disabled_reason"
          class="guild-counter__reason"
          data-testid="guild-counter__register-reason"
        >
          （{{ registration.register.disabled_reason.message }}）
        </span>
      </p>

      <section class="guild-counter__section" aria-label="任務板">
        <h4 class="guild-counter__section-title">任務板 — 接取</h4>
        <div
          v-for="row in boardRows"
          :key="row.definition_key"
          class="guild-counter__row"
          :data-testid="`guild-counter__board-row--${row.definition_key}`"
        >
          <div class="guild-counter__row-head">
            <span class="guild-counter__row-name">{{ row.display_name }}</span>
            <span class="guild-counter__row-rank">等級 {{ row.rank }}</span>
          </div>
          <p class="guild-counter__row-objective">{{ row.objective_summary }}</p>
          <p class="guild-counter__row-reward">獎勵：{{ row.reward_summary }}</p>
          <button
            v-if="row.accept && row.accept.enabled"
            type="button"
            class="guild-counter__action"
            data-testid="guild-counter__accept"
               @click="emit('quest_accept', { action_id: row.accept.action_id, payload: { definition_key: row.definition_key } })"
          >
            {{ row.accept.label }}
          </button>
          <span
            v-if="row.accept && !row.accept.enabled && row.accept.disabled_reason"
            class="guild-counter__reason"
            data-testid="guild-counter__accept-reason"
          >
            （{{ row.accept.disabled_reason.message }}）
          </span>
        </div>
      </section>

      <section
        v-if="rank"
        class="guild-counter__section guild-counter__rankblock"
        data-testid="guild-counter__rankblock"
        aria-label="公會等級"
        :data-top-rank="String(isTopRank)"
      >
        <h4 class="guild-counter__section-title">公會等級</h4>

        <div class="guild-counter__rank-card">
          <div class="guild-counter__rank-head">
            <span
              class="guild-counter__crest"
              :class="{ 'guild-counter__crest--top': isTopRank }"
              aria-hidden="true"
            >
              <span class="guild-counter__crest-letter">{{ rank.rank ?? "—" }}</span>
            </span>
            <div class="guild-counter__rank-text">
              <p class="guild-counter__rank-level" data-testid="guild-counter__rank-level">
                <template v-if="rank.rank != null">
                  等級 <span class="guild-counter__rank-letter">{{ rank.rank }}</span>
                </template>
                <template v-else>尚未評級</template>
              </p>
              <p v-if="hasNextStep" class="guild-counter__rank-next" data-testid="guild-counter__rank-next">
                下一階 <span class="guild-counter__rank-letter">{{ rank.next_rank }}</span> 級
              </p>
              <p v-else-if="isTopRank" class="guild-counter__rank-next guild-counter__rank-next--top" data-testid="guild-counter__rank-top">
                最高等級
              </p>
            </div>
            <p class="guild-counter__merit" data-testid="guild-counter__merit">
              <span class="guild-counter__merit-label">累積功績</span>
              <span class="guild-counter__merit-value">{{ fmt(merit) }}</span>
            </p>
          </div>

          <template v-if="hasNextStep">
            <div
              class="guild-counter__meter"
              :class="{ 'guild-counter__meter--full': qualified }"
              data-testid="guild-counter__merit-meter"
              role="progressbar"
              :aria-label="`升至 ${rank.next_rank} 級的功績`"
              aria-valuemin="0"
              :aria-valuemax="threshold"
              :aria-valuenow="meterNow"
              :aria-valuetext="`功績 ${fmt(merit)} / ${fmt(threshold)}`"
            >
              <span class="guild-counter__meter-fill" :style="{ width: `${meterPercent}%` }"></span>
            </div>
            <div class="guild-counter__meter-foot">
              <p
                class="guild-counter__merit-status"
                :class="qualified ? 'guild-counter__merit-status--met' : 'guild-counter__merit-status--short'"
                data-testid="guild-counter__merit-status"
                :data-qualified="String(qualified)"
              >
                <span class="guild-counter__merit-mark" aria-hidden="true">{{ qualified ? "◆" : "◇" }}</span>
                <template v-if="qualified">功績已達標</template>
                <template v-else>功績未達標 · 尚差 {{ fmt(shortfall) }}</template>
              </p>
              <p class="guild-counter__meter-scale">升等門檻 {{ fmt(threshold) }}</p>
            </div>
          </template>

          <div v-if="examRequest" class="guild-counter__exam-block">
            <button
              type="button"
              class="guild-counter__exam-button"
              :class="{ 'guild-counter__exam-button--ready': examEnabled && qualified }"
              data-testid="guild-counter__exam"
              :disabled="!examEnabled"
              :aria-describedby="examDescribedBy"
              @click="requestExam"
            >
              <span class="guild-counter__exam-label">{{ examRequest.label }}</span>
              <span v-if="hasNextStep" class="guild-counter__exam-target" aria-hidden="true">→ {{ rank.next_rank }} 級</span>
            </button>
            <p
              v-if="examEnabled"
              :id="examHintId"
              class="guild-counter__exam-hint"
              data-testid="guild-counter__exam-hint"
            >
              考官在公會時即可應考；不在時，櫃台會告知下次預定到場的時間。
            </p>
            <p
              v-else-if="examRequest.disabled_reason"
              :id="examReasonId"
              class="guild-counter__exam-reason"
              data-testid="guild-counter__exam-reason"
              :data-reason-code="examRequest.disabled_reason.code"
            >
              <span class="guild-counter__exam-reason-mark" aria-hidden="true">※</span>
              {{ examRequest.disabled_reason.message }}
            </p>
          </div>
        </div>
      </section>
    </template>
  </section>
</template>

<style scoped>
.guild-counter {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
  box-sizing: border-box;
  padding: var(--sp-3) var(--sp-4);
  background: var(--panel);
  border: var(--line);
  border-radius: var(--radius);
  font-family: var(--f-sans);
}

.guild-counter__title {
  margin: 0;
  color: var(--paper-100);
  font-family: var(--f-display);
  font-size: 1em;
}

.guild-counter__absent,
.guild-counter__unavailable {
  margin: 0;
  padding: var(--sp-1) var(--sp-2);
  color: var(--paper-500);
  font-size: max(var(--text-xs), 0.85em);
  border: 1px dashed var(--ink-700);
  border-radius: var(--radius-sm);
}

.guild-counter__registration {
  margin: 0;
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  color: var(--paper-300);
  font-size: max(var(--text-xs), 0.85em);
}

.guild-counter__section {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  padding-top: var(--sp-2);
  border-top: var(--line);
}

.guild-counter__section-title {
  margin: 0;
  color: var(--seal-400);
  font-family: var(--f-display);
  font-size: max(var(--text-xs), 0.95em);
}

.guild-counter__row {
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
  padding: var(--sp-2);
  border: var(--line);
  border-radius: var(--radius-sm);
  background: var(--panel-hi);
}

.guild-counter__row-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--sp-2);
}

.guild-counter__row-name {
  color: var(--paper-50);
  font-family: var(--f-display);
}

.guild-counter__row-rank {
  color: var(--gold-400);
  font-family: var(--f-num);
  font-size: max(var(--text-xs), 0.85em);
  font-variant-numeric: tabular-nums lining-nums;
}

.guild-counter__row-objective,
.guild-counter__row-reward {
  margin: 0;
  color: var(--paper-300);
  font-size: max(var(--text-xs), 0.85em);
}

.guild-counter__action {
  align-self: flex-start;
  padding: 2px var(--sp-2);
  color: var(--paper-50);
  background: transparent;
  border: 1px solid var(--seal-600);
  border-radius: var(--radius-sm);
  font-family: var(--f-sans);
  font-size: max(var(--text-xs), 0.85em);
  cursor: pointer;
}

.guild-counter__action:hover {
  border-color: var(--seal-400);
  color: var(--seal-400);
}

.guild-counter__action:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  border-color: var(--ink-600);
  color: var(--paper-700);
}

.guild-counter__reason {
  color: var(--warn);
  font-size: max(var(--text-xs), 0.85em);
  font-family: var(--f-num);
  font-variant-numeric: tabular-nums lining-nums;
}

/* ---- Guild rank / promotion examination -------------------------------
   The exam button and rank card use their own class names (not
   guild-counter__action) so the shared `.elosern-root .guild-counter__action`
   skin in styles/app-shell.css does not override them; the gold-ruled
   button below follows that same live idiom. */
.guild-counter__rank-card {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  padding: var(--sp-3) var(--sp-4);
  border: 1px solid var(--ink-600);
  border-radius: var(--radius-sm);
  background:
    linear-gradient(110deg, var(--gold-glow), transparent 45%),
    var(--panel-hi);
}

.guild-counter__rank-head {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--sp-4);
}

/* Rank crest: a diamond seal (rotated square) carrying the rank letter
   upright. Double gold rule on a seal-red field, as a wax guild stamp. */
.guild-counter__crest {
  position: relative;
  display: grid;
  place-items: center;
  width: calc(var(--text-4xl) * 1.5);
  height: calc(var(--text-4xl) * 1.5);
  margin: var(--sp-1);
  flex: none;
}

.guild-counter__crest::before {
  content: "";
  position: absolute;
  inset: 14%;
  transform: rotate(45deg);
  border: 1px solid var(--gold-500);
  border-radius: var(--radius-sm);
  background: radial-gradient(circle at 50% 35%, var(--seal-600), var(--seal-700) 60%, var(--ink-900));
  box-shadow:
    inset 0 0 0 3px var(--ink-900),
    inset 0 0 0 4px var(--gold-600),
    0 0 var(--sp-3) var(--seal-glow);
}

.guild-counter__crest--top::before {
  border-color: var(--gold-400);
  box-shadow:
    inset 0 0 0 3px var(--ink-900),
    inset 0 0 0 4px var(--gold-400),
    0 0 var(--sp-4) var(--gold-glow);
}

.guild-counter__crest-letter {
  position: relative;
  color: var(--gold-300);
  font-family: var(--f-display);
  font-size: var(--text-2xl);
  line-height: 1;
  text-shadow: 0 1px 0 var(--ink-950);
}

.guild-counter__rank-text {
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
  min-width: 0;
}

.guild-counter__rank-level {
  margin: 0;
  color: var(--paper-50);
  font-family: var(--f-display);
  font-size: var(--text-lg);
  line-height: 1.2;
}

.guild-counter__rank-letter {
  color: var(--gold-400);
}

.guild-counter__rank-next {
  margin: 0;
  color: var(--paper-400);
  font-size: max(var(--text-xs), 0.85em);
  font-variant-numeric: tabular-nums lining-nums;
}

.guild-counter__rank-next--top {
  align-self: flex-start;
  padding: 0 var(--sp-2);
  color: var(--gold-300);
  border: 1px solid var(--gold-600);
  border-radius: var(--radius-pill);
  background: var(--gold-glow);
}

.guild-counter__merit {
  margin: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  text-align: right;
  min-width: 0;
}

.guild-counter__merit-label {
  color: var(--paper-500);
  font-size: max(var(--text-xs), 0.8em);
}

.guild-counter__merit-value {
  color: var(--gold-300);
  font-family: var(--f-num);
  font-size: var(--text-xl);
  font-variant-numeric: tabular-nums lining-nums;
  line-height: 1.15;
  overflow-wrap: anywhere;
}

/* Merit meter: an inset ink track with a gold fill, clamped to 100%. */
.guild-counter__meter {
  position: relative;
  height: var(--sp-2);
  margin-top: var(--sp-1);
  overflow: hidden;
  border: 1px solid var(--ink-600);
  border-radius: var(--radius-pill);
  background: var(--ink-900);
  box-shadow: inset 0 1px 2px var(--ink-950);
}

.guild-counter__meter-fill {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--gold-600), var(--gold-500));
  transition: width 400ms ease-out;
}

.guild-counter__meter--full {
  border-color: var(--gold-600);
}

.guild-counter__meter--full .guild-counter__meter-fill {
  background: linear-gradient(90deg, var(--gold-500), var(--gold-300));
  box-shadow: 0 0 var(--sp-2) var(--gold-glow);
}

.guild-counter__meter-foot {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: baseline;
  gap: var(--sp-1) var(--sp-3);
}

.guild-counter__meter-scale {
  margin: 0 0 0 auto;
  color: var(--paper-500);
  font-family: var(--f-num);
  font-size: max(var(--text-xs), 0.8em);
  font-variant-numeric: tabular-nums lining-nums;
}

.guild-counter__merit-status {
  margin: 0;
  display: flex;
  align-items: baseline;
  gap: var(--sp-2);
  font-size: max(var(--text-sm), 0.85em);
  font-variant-numeric: tabular-nums lining-nums;
}

/* Met vs short is carried by label and glyph shape (◆ filled / ◇ hollow),
   not color alone; the text stays on high-contrast paper while only the
   glyph takes the --ok hue (it sits near 4.5:1 on this card). */
.guild-counter__merit-status--met {
  color: var(--paper-100);
}

.guild-counter__merit-status--short {
  color: var(--paper-300);
}

.guild-counter__merit-mark {
  color: var(--gold-400);
}

.guild-counter__merit-status--met .guild-counter__merit-mark {
  color: var(--ok);
}

.guild-counter__exam-block {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--sp-2);
  margin-top: var(--sp-1);
  padding-top: var(--sp-3);
  border-top: var(--line);
}

.guild-counter__exam-button {
  display: inline-flex;
  align-items: baseline;
  gap: var(--sp-2);
  padding: var(--sp-2) var(--sp-5);
  color: var(--gold-300);
  background: linear-gradient(var(--gold-glow), transparent);
  border: 1px solid var(--gold-500);
  border-radius: var(--radius-sm);
  font-family: var(--f-display);
  font-size: var(--text-md);
  cursor: pointer;
  transition: border-color 150ms ease, background-color 150ms ease, color 150ms ease;
}

.guild-counter__exam-button:hover:not(:disabled) {
  color: var(--paper-50);
  border-color: var(--gold-400);
  background-color: var(--gold-glow);
}

.guild-counter__exam-button:focus-visible {
  outline: none;
  box-shadow: var(--focus);
}

/* Merit already met and the counter will take the request: the seal-red
   ground marks it as the ready, primary call. */
.guild-counter__exam-button--ready {
  color: var(--paper-50);
  border-color: var(--gold-400);
  background: linear-gradient(var(--seal-600), var(--seal-700));
}

.guild-counter__exam-button--ready:hover:not(:disabled) {
  background: linear-gradient(var(--seal-500), var(--seal-600));
}

/* Disabled is a different shape, not just a dimmer copy: dashed ink rule,
   no fill, muted text. */
.guild-counter__exam-button:disabled {
  color: var(--paper-500);
  background: transparent;
  border: 1px dashed var(--ink-600);
  cursor: not-allowed;
}

.guild-counter__exam-target {
  font-family: var(--f-num);
  font-size: max(var(--text-xs), 0.85em);
  opacity: 0.85;
}

.guild-counter__exam-hint,
.guild-counter__exam-reason {
  margin: 0;
  font-size: max(var(--text-sm), 0.85em);
  line-height: 1.6;
}

.guild-counter__exam-hint {
  color: var(--paper-400);
}

.guild-counter__exam-reason {
  display: flex;
  align-items: baseline;
  gap: var(--sp-1);
  color: var(--warn);
}

@media (prefers-reduced-motion: reduce) {
  .guild-counter__meter-fill,
  .guild-counter__exam-button {
    transition: none;
  }
}
</style>
