<script setup>
// GuildCounter (quest-issuer-model change 11, design D2): the guild counter
// surface of the split quest drawer — what genuinely belongs to the counter
// itself: registration, the quest board (接取), and guild rank with the
// promotion examination. It is a host, not a data source: it renders only the
// committed `services` v4 payload's guild section and invents nothing.
//
// It deliberately does NOT render the guild section's `quests` rows: the
// holder's accepted quest records live in the quest book (QuestLog), so no
// quest is presented twice in one drawer.
import { computed } from "vue";

const props = defineProps({
  // The committed `services` v4 panel payload.
  services: { type: Object, required: true },
});

const emit = defineEmits(["quest_register", "quest_accept", "exam_start"]);

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
// rank (both null) degrades instead of printing a fabricated "null".
const hasNextStep = computed(
  () => rank.value?.next_rank != null && rank.value?.next_threshold != null,
);
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
        class="guild-counter__section"
        data-testid="guild-counter__rankblock"
        aria-label="公會等級"
      >
        <h4 class="guild-counter__section-title">公會等級</h4>
        <p class="guild-counter__rank-level" data-testid="guild-counter__rank-level">
          等級 {{ rank.rank }}
        </p>
          <p class="guild-counter__merit" data-testid="guild-counter__merit">
            <template v-if="hasNextStep">
              功績 {{ rank.merit }} · 升格至 {{ rank.next_rank }} 需 {{ rank.next_threshold }}
            </template>
            <template v-else>
              功績 {{ rank.merit }}（最高等級）
            </template>
          </p>
        <button
          v-if="rank.eligible"
          type="button"
          class="guild-counter__action"
          data-testid="guild-counter__exam"
          @click="
            emit('exam_start', {
              action_id: rank.exam_start?.action_id,
              payload: { target_rank: rank.next_rank },
            })
          "
        >
          {{ rank.exam_start?.label }}
        </button>
        <span
          v-if="!rank.eligible && rank.exam_start && rank.exam_start.disabled_reason"
          class="guild-counter__reason"
          data-testid="guild-counter__exam-reason"
        >
           （{{ rank.exam_start.disabled_reason.message }}）
         </span>
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
  font-size: 0.85em;
  border: 1px dashed var(--ink-700);
  border-radius: var(--radius-sm);
}

.guild-counter__registration {
  margin: 0;
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  color: var(--paper-300);
  font-size: 0.85em;
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
  font-size: 0.95em;
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
  font-family: var(--f-mono);
  font-size: 0.85em;
}

.guild-counter__row-objective,
.guild-counter__row-reward {
  margin: 0;
  color: var(--paper-300);
  font-size: 0.85em;
}

.guild-counter__action {
  align-self: flex-start;
  padding: 2px var(--sp-2);
  color: var(--paper-50);
  background: transparent;
  border: 1px solid var(--seal-600);
  border-radius: var(--radius-sm);
  font-family: var(--f-sans);
  font-size: 0.85em;
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
  font-size: 0.85em;
  font-family: var(--f-mono);
}

.guild-counter__rank {
  margin: 0;
  color: var(--paper-50);
  font-size: 0.85em;
}

.guild-counter__merit {
  margin: 0;
  color: var(--paper-300);
  font-size: 0.85em;
}
</style>
