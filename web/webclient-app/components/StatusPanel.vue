<script setup>
// StatusPanel (B3 data family): the expanded status surface. It renders the
// committed `status` panel payload (schema version 1) — gauges, conditions
// with their derived modifiers, the disguise flag, and the combat session —
// and the `character` panel payload's counters/static-traits/wallet subset.
// Nothing is conveyed by color alone: gauges pair a symbol with an explicit
// current/maximum value, counters and static traits render their numeric
// values, and each condition pairs a severity glyph (a DOM node, per
// severity) with its label and every numeric/modifier value the payload
// provides. Absent conditional payload fields render nothing (design D4);
// the intimate/adult block the 設計稿 shows has no backing field and is not
// built.
import { computed } from "vue";

const props = defineProps({
  // The committed `status` v1 panel payload.
  status: { type: Object, required: true },
  // The committed `character` v3 panel payload (counters, statics, wallet).
  character: { type: Object, required: true },
});

const GAUGES = [
  { key: "hp", symbol: "♥", label: "生命" },
  { key: "mp", symbol: "❖", label: "魔力" },
  { key: "sp", symbol: "⚡", label: "耐力" },
];

const TRAIT_KEYS = ["atk_phys", "agility", "defense", "magic_level", "guild_merit"];

// The severity glyph is rendered as a DOM node (not a CSS pseudo-element)
// so state is not conveyed by color or border style alone.
const SEVERITY_GLYPHS = {
  beneficial: "▲",
  informational: "◆",
  warning: "▲",
  harmful: "▼",
  critical: "✕",
};

const COMBAT_MODES = {
  hostile: "敵對",
  guild_exam: "公會考核",
};

// Integer copper, thousands-separated for display only (no float money).
function formatCopper(value) {
  return String(value).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

const actorName = computed(() => props.status.actor?.name ?? "");
const locationLabel = computed(() => props.status.actor?.location?.label ?? "");

const resources = computed(() => props.status.resources ?? {});
function gauge(key) {
  const r = resources.value[key];
  return r
    ? {
        current: r.current,
        maximum: r.maximum,
        ratio: r.maximum > 0 ? (r.current / r.maximum) * 100 : 0,
      }
    : null;
}

// Counters and static traits, kept in the character payload's own order.
const traitRows = computed(() =>
  (props.character.traits ?? []).filter((row) =>
    TRAIT_KEYS.includes(row.key),
  ),
);

const wallet = computed(() => Math.max(0, props.character.wallet ?? 0));

const conditions = computed(() =>
  Array.isArray(props.status.conditions) ? props.status.conditions : [],
);

const disguiseActive = computed(() => props.status.disguise_active === true);

const combat = computed(() =>
  props.status.combat &&
  typeof props.status.combat.round === "number"
    ? props.status.combat
    : null,
);

function severityGlyph(severity) {
  return SEVERITY_GLYPHS[severity] ?? "◆";
}

function conditionMods(condition) {
  const mods = condition.modifiers;
  if (!mods || typeof mods !== "object") return [];
  return Object.keys(mods).map((key) => ({
    key,
    text: `${key} ${mods[key]}`,
  }));
}

function combatLabel(mode) {
  return COMBAT_MODES[mode] ?? mode;
}
</script>

<template>
  <aside class="status-panel" data-testid="status-panel">
    <h3 class="status-panel__title" data-testid="status-panel__title">角色狀態</h3>

    <p class="status-panel__actor" data-testid="status-panel__actor">
      {{ actorName }}
      <span v-if="locationLabel" class="status-panel__location">
        · {{ locationLabel }}
      </span>
    </p>

    <section class="status-panel__section" data-testid="status-panel__vitals" aria-label="生命量">
      <div
        v-for="g in GAUGES"
        :key="g.key"
        class="status-gauge"
        :data-testid="`status-panel__gauge--${g.key}`"
      >
        <span class="status-gauge__symbol" aria-hidden="true">{{ g.symbol }}</span>
        <span class="status-gauge__label">{{ g.label }}</span>
        <span
          class="status-gauge__value"
          :data-testid="`status-panel__gauge-value--${g.key}`"
          >{{ gauge(g.key)?.current ?? 0 }} / {{ gauge(g.key)?.maximum ?? 0 }}</span
        >
        <span class="status-gauge__bar" aria-hidden="true">
          <span class="status-gauge__fill" :style="{ width: `${gauge(g.key)?.ratio ?? 0}%` }" />
        </span>
      </div>
    </section>

    <section class="status-panel__section" data-testid="status-panel__traits" aria-label="計數與屬性">
      <div
        v-for="row in traitRows"
        :key="row.key"
        class="status-panel__trait"
        :data-testid="`status-panel__trait--${row.key}`"
      >
        <span class="status-panel__trait-key">{{ row.label }}</span>
        <span class="status-panel__trait-value">{{ row.current }}</span>
      </div>
      <div class="status-panel__trait" data-testid="status-panel__wallet">
        <span class="status-panel__trait-key">錢包</span>
        <span class="status-panel__trait-value">{{ formatCopper(wallet) }} 銅</span>
      </div>
    </section>

    <section class="status-panel__section" data-testid="status-panel__conditions" aria-label="條件">
      <template v-if="conditions.length > 0">
        <span
          v-for="condition in conditions"
          :key="condition.code"
          class="status-panel__condition"
          :class="`status-panel__condition--${condition.severity}`"
          :data-testid="`status-panel__condition--${condition.code}`"
          :data-severity="condition.severity"
          :data-code="condition.code"
        >
          <span class="status-panel__condition-glyph" aria-hidden="true">
            {{ severityGlyph(condition.severity) }}
          </span>
          {{ condition.label }}
          <template v-if="typeof condition.remaining_seconds === 'number'">
            <span class="status-panel__condition-timer" data-testid="status-panel__condition-timer"
              >{{ condition.remaining_seconds }} s</span
            >
          </template>
          <span
            v-for="mod in conditionMods(condition)"
            :key="mod.key"
            class="status-panel__condition-mod"
            :data-testid="`status-panel__condition-mod--${mod.key}`"
          >
            {{ mod.text }}
          </span>
        </span>
      </template>
      <p v-else class="status-panel__conditions-empty" data-testid="status-panel__conditions-empty">
        無條件
      </p>
    </section>

    <p
      class="status-panel__disguise"
      data-testid="status-panel__disguise"
      :data-active="String(disguiseActive)"
    >
      {{ disguiseActive ? "目前有偽裝" : "無偽裝" }}
    </p>

    <p
      v-if="combat"
      class="status-panel__combat"
      data-testid="status-panel__combat"
      :data-mode="combat.mode"
    >
      戰鬥中（{{ combatLabel(combat.mode) }}）· 第 {{ combat.round }} 回合
    </p>
  </aside>
</template>

<style scoped>
.status-panel {
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

.status-panel__title {
  margin: 0;
  color: var(--paper-100);
  font-family: var(--f-display);
  font-size: 1em;
}

.status-panel__actor {
  margin: 0;
  color: var(--paper-300);
  font-size: 0.85em;
}

.status-panel__section {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  padding-top: var(--sp-2);
  border-top: var(--line);
}

.status-gauge {
  display: grid;
  grid-template-columns: 1.2em 3em 1fr;
  align-items: center;
  gap: var(--sp-2);
}

.status-gauge__symbol {
  color: var(--paper-300);
  text-align: center;
}

.status-gauge__label {
  color: var(--paper-300);
  font-size: 0.85em;
}

.status-gauge__value {
  color: var(--paper-50);
  font-family: var(--f-mono);
  font-size: 0.9em;
  text-align: right;
}

.status-gauge__bar {
  grid-column: 1 / -1;
  height: 4px;
  background: var(--ink-700);
  border-radius: 2px;
  overflow: hidden;
}

.status-gauge__fill {
  display: block;
  height: 100%;
  background: var(--vit-hp);
}

.status-gauge[data-testid="status-panel__gauge--mp"] .status-gauge__fill {
  background: var(--vit-mp);
}

.status-gauge[data-testid="status-panel__gauge--sp"] .status-gauge__fill {
  background: var(--vit-sp);
}

.status-panel__trait {
  display: flex;
  justify-content: space-between;
  gap: var(--sp-2);
  font-size: 0.9em;
}

.status-panel__trait-key {
  color: var(--paper-300);
}

.status-panel__trait-value {
  color: var(--paper-50);
  font-family: var(--f-mono);
}

.status-panel__condition {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-1);
  align-self: flex-start;
  border: var(--line);
  border-radius: var(--radius-sm);
  padding: 2px var(--sp-2);
  font-family: var(--f-mono);
  font-size: var(--text-sm);
}

.status-panel__condition--beneficial {
  color: var(--buff);
  border-color: var(--buff);
}

.status-panel__condition--informational {
  color: var(--paper-300);
  border-color: var(--paper-700);
}

.status-panel__condition--warning {
  color: var(--warn);
  border-color: var(--warn);
  border-style: dashed;
}

.status-panel__condition--harmful {
  color: var(--debuff);
  border-color: var(--debuff);
  border-style: dotted;
}

.status-panel__condition--critical {
  color: var(--crit);
  border-color: var(--crit);
  border-style: double;
}

.status-panel__condition-timer,
.status-panel__condition-mod {
  color: var(--paper-500);
  font-size: 0.9em;
}

.status-panel__conditions-empty {
  margin: 0;
  color: var(--paper-500);
  font-size: 0.85em;
}

.status-panel__disguise {
  margin: 0;
  color: var(--warn);
  font-size: 0.85em;
}

.status-panel__disguise[data-active="false"] {
  color: var(--paper-500);
}

.status-panel__combat {
  margin: 0;
  padding: var(--sp-1) var(--sp-2);
  color: var(--seal-400);
  border: 1px dashed var(--seal-600);
  border-radius: var(--radius-sm);
  font-size: 0.85em;
}
</style>
