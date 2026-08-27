<script setup>
// LoreDrawer (B4 services family): the "圖鑑抽屜" (codex drawer). It
// surfaces the world lore the player has learned, rendered only from the
// committed `services` v2 payload (design D2: a host, not a data source) —
// the host line and the guild lore (quest-board objective/reward summaries
// + the active quest's story detail). H4 (task 5.2) removed the duplicated
// wallet line and player-summary rows; the wallet and guild summary now live
// in the CharacterStatusDrawer. The 8-category codex has no OOB read model in
// this payload, so the drawer never fabricates codex cards (a deliberate
// skip); unknown lore never leaks its existence.
import { computed } from "vue";

const props = defineProps({
  // The committed `services` v2 panel payload.
  services: { type: Object, required: true },
});

// The registry-owned unavailable form (available: false) carries only the
// reason — the host/player/guild blocks are hidden, so no invented values.
const unavailable = computed(() => props.services?.available === false);

const host = computed(() => (unavailable.value ? null : (props.services?.host ?? null)));
const guild = computed(() => (unavailable.value ? null : (props.services?.guild ?? null)));
const boardLoreRows = computed(() => guild.value?.board ?? []);
const activeQuestRows = computed(() => guild.value?.quests ?? []);

// Quest state labels — the server's bounded quest states (presentation
// services.py: in_progress / completed / failed), rendered as text.
const QUEST_STATES = {
  in_progress: "進行中",
  completed: "已完成",
  failed: "失敗",
};

function questStateLabel(state) {
  return QUEST_STATES[state] ?? state;
}
</script>

<template>
  <aside class="lore-drawer" data-testid="lore-drawer">
    <h3 class="lore-drawer__title" data-testid="lore-drawer__title">世界圖鑑</h3>

    <p
      v-if="unavailable"
      class="lore-drawer__unavailable"
      data-testid="lore-drawer__unavailable"
      :data-reason-code="services.reason?.code"
    >
      {{ services.reason?.message }}
    </p>

    <p v-if="!unavailable && host" class="lore-drawer__host" data-testid="lore-drawer__host">
      <span class="lore-drawer__host-name">{{ host.display_name }}</span>
      <span class="lore-drawer__host-identity" data-testid="lore-drawer__host-identity">
        {{ host.identity }}
      </span>
    </p>

    <!-- H4 (task 5.2): the duplicated wallet line and player-summary rows
         are removed; the wallet and guild summary now live in the
         CharacterStatusDrawer (the single wallet rendering, task 7.7). -->

    <section
      v-if="guild"
      class="lore-drawer__guild"
      data-testid="lore-drawer__guild"
      aria-label="公會圖鑑"
    >
      <h4 class="lore-drawer__section-title" data-testid="lore-drawer__guild-title">公會圖鑑</h4>
      <div
        v-for="row in boardLoreRows"
        :key="row.definition_key"
        class="lore-drawer__lore-row"
        :data-testid="`lore-drawer__board-lore--${row.definition_key}`"
      >
        <span class="lore-drawer__lore-objective">{{ row.objective_summary }}</span>
        <span class="lore-drawer__lore-reward">{{ row.reward_summary }}</span>
      </div>
      <div
        v-for="quest in activeQuestRows"
        :key="quest.quest_id"
        class="lore-drawer__lore-row"
        :data-testid="`lore-drawer__quest-detail--${quest.quest_id}`"
      >
        <div class="lore-drawer__lore-head">
          <span class="lore-drawer__lore-objective">{{ quest.display_name }}</span>
          <span class="lore-drawer__lore-state">{{ questStateLabel(quest.state) }}</span>
        </div>
        <span class="lore-drawer__lore-stage">
          第 {{ quest.stage_index }} 階段 · 進度 {{ quest.stage_progress }}
        </span>
        <p class="lore-drawer__lore-detail-text">{{ quest.detail }}</p>
      </div>
    </section>
    <p v-if="!unavailable && !guild" class="lore-drawer__absent" data-testid="lore-drawer__absent">
      尚無公會圖鑑資料
    </p>
  </aside>
</template>

<style scoped>
.lore-drawer {
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

.lore-drawer__title {
  margin: 0;
  color: var(--paper-100);
  font-family: var(--f-display);
  font-size: 1em;
}

.lore-drawer__host {
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
  color: var(--paper-300);
  font-size: 0.85em;
}

.lore-drawer__host-name {
  color: var(--paper-50);
  font-family: var(--f-display);
  font-size: 1.1em;
}

.lore-drawer__host-identity {
  color: var(--paper-500);
  font-family: var(--f-mono);
  font-size: 0.8em;
}

.lore-drawer__summary {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  padding-top: var(--sp-2);
  border-top: var(--line);
}

.lore-drawer__line {
  display: flex;
  justify-content: space-between;
  gap: var(--sp-2);
  font-size: 0.85em;
}

.lore-drawer__line-key {
  color: var(--paper-300);
}

.lore-drawer__line-value {
  color: var(--paper-50);
  font-family: var(--f-mono);
}

.lore-drawer__guild {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  padding-top: var(--sp-2);
  border-top: var(--line);
}

.lore-drawer__section-title {
  margin: 0;
  color: var(--seal-400);
  font-family: var(--f-display);
  font-size: 0.95em;
}

.lore-drawer__lore-row {
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
  padding: var(--sp-2);
  border: var(--line);
  border-radius: var(--radius-sm);
  background: var(--panel-hi);
}

.lore-drawer__lore-head {
  display: flex;
  justify-content: space-between;
  gap: var(--sp-2);
}

.lore-drawer__lore-objective {
  color: var(--paper-300);
  font-size: 0.85em;
}

.lore-drawer__lore-reward {
  color: var(--paper-500);
  font-family: var(--f-mono);
  font-size: 0.8em;
}

.lore-drawer__lore-state {
  color: var(--gold-400);
  font-family: var(--f-mono);
  font-size: 0.85em;
}

.lore-drawer__lore-stage {
  color: var(--paper-300);
  font-family: var(--f-mono);
  font-size: 0.8em;
}

.lore-drawer__lore-detail-text {
  margin: 0;
  color: var(--paper-100);
  font-family: var(--f-serif);
  font-size: 0.9em;
  line-height: var(--lh-dialog);
}

.lore-drawer__absent,
.lore-drawer__unavailable {
  margin: 0;
  padding: var(--sp-1) var(--sp-2);
  color: var(--paper-500);
  font-size: 0.85em;
  border: 1px dashed var(--ink-700);
  border-radius: var(--radius-sm);
}
</style>
