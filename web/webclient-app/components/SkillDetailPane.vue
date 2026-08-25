<script setup>
// SkillDetailPane (H3 webclient-hud-03-action-dock, task 6.5): the
// draft's `.skdetail` pane — the focused skill's name, description, cost,
// target spec and disabled reason, rendered into the preserved
// `data-testid="combat-detail"` pane. No `戰鬥外` badge is rendered
// (design D14: the flag is serialized by no presenter, so the pane must not
// invent one).
//
// The pane is passive: it renders the committed focused-skill model and the
// client-local selection (the `✓` AREA marker) — it never mutates state.
import { computed } from "vue";

const props = defineProps({
  // The focused skill model (the store's `combat.skillByKey[focusSkillKey]`):
  // `label`, `description`, `costText`, `targetSpec`, `enabled`,
  // `disabledReason`, `selected` (AREA identities).
  skill: { type: Object, default: null },
  // The client-local AREA selection (the `✓` marker source, task 6.6).
  selected: { type: Array, default: () => [] },
  // The 威力 scale step (task 6.6): the draft's `.scales` row — the
  // server-computed `mp_cost`, ascending, `1` preselected.
  scales: { type: Array, default: () => [] },
  // The chosen 威力 (the client-local selection state).
  scale: { type: Number, default: 1 },
});

const emit = defineEmits(["choose-scale", "choose-shorthand"]);

const costText = computed(() => props.skill ? props.skill.costText || "" : "");
const targetSpec = computed(() => (props.skill && props.skill.targetSpec) || "");
const reason = computed(
  () =>
    (props.skill && props.skill.disabledReason && props.skill.disabledReason.message) || null,
);

function onScale(entry) {
  emit("choose-scale", { scale: entry.scale });
}
</script>

<template>
  <aside
    class="skill-detail-pane"
    data-testid="combat-detail"
    v-if="skill"
    aria-label="技能詳情"
  >
    <div class="skill-detail-pane__name">
      <span>{{ skill.label }}</span>
      <span v-if="skill.element" class="skill-detail-pane__rank">{{ skill.element }}</span>
    </div>
    <p v-if="skill.description" class="skill-detail-pane__desc">{{ skill.description }}</p>
    <div v-if="costText" class="skill-detail-pane__cost">
      <span class="skill-detail-pane__label">消耗</span>
      {{ costText }}
    </div>
    <div v-if="targetSpec" class="skill-detail-pane__target">
      <span class="skill-detail-pane__label">目標類型</span>
      {{ targetSpec }}
    </div>
    <p v-if="reason" class="skill-detail-pane__disabled">{{ reason }}</p>

    <!-- The 威力 step (task 6.6): the `.scales` row — ascending, the
         server-computed `mp_cost`, `1` preselected. No `戰鬥外` badge
         (design D14). -->
    <div v-if="scales.length" class="skill-detail-pane__scales">
      <button
        v-for="entry in scales"
        :key="entry.scale"
        type="button"
        class="skill-detail-pane__scale"
        :class="{ 'skill-detail-pane__scale--on': entry.scale === scale }"
        :aria-pressed="entry.scale === scale"
        @click="onScale(entry)"
      >
        <span>{{ entry.label || entry.scale }}</span>
        <span v-if="entry.mp_cost != null" class="skill-detail-pane__scale-cost">MP {{ entry.mp_cost }}</span>
      </button>
    </div>
  </aside>
</template>

<style scoped>
/* The draft's `.skdetail` pane. */
.skill-detail-pane {
  background: var(--panel);
  border: var(--line);
  border-radius: 10px;
  padding: 12px;
  font-family: var(--f-sans);
  font-size: var(--text-sm);
  color: var(--paper-100);
  flex: 1 1 260px;
  min-width: 220px;
  overflow-y: auto;
}

.skill-detail-pane__name {
  font-size: 15px;
  color: var(--paper-50);
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.skill-detail-pane__rank {
  font-size: 10.5px;
  color: var(--gold-400);
  font-family: var(--f-mono);
  font-weight: 400;
}

.skill-detail-pane__desc {
  font-size: 11.5px;
  color: var(--paper-500);
  margin: 6px 0 11px;
  line-height: 1.5;
}

.skill-detail-pane__label {
  display: block;
  font-size: 10px;
  letter-spacing: 0.1em;
  color: var(--paper-500);
  margin-bottom: 6px;
}

.skill-detail-pane__cost,
.skill-detail-pane__target {
  font-size: 11.5px;
  color: var(--paper-300);
  margin-bottom: 8px;
}

.skill-detail-pane__disabled {
  color: var(--warn);
  font-size: 11px;
  margin-top: 8px;
}

.skill-detail-pane__scales {
  display: flex;
  gap: 6px;
  margin-top: 10px;
}

.skill-detail-pane__scale {
  flex: 1;
  font-family: var(--f-mono);
  font-size: 12px;
  padding: 7px;
  border-radius: 8px;
  background: var(--ink-780);
  border: 1px solid var(--ink-600);
  color: var(--paper-300);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.skill-detail-pane__scale--on {
  background: var(--seal-600);
  border-color: var(--seal-500);
  color: #fff;
}

.skill-detail-pane__scale-cost {
  font-size: 10px;
  color: var(--paper-500);
}
</style>
