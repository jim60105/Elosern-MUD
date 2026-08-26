<script setup>
// CharacterStatusDrawer (H4, webclient-hud-04-reference-drawers, task 5.3):
// the 角色狀態 drawer body. It presents the committed `status` v1 payload's
// vitals (hp/mp/sp gauges) and the FULL condition roster (no 6-chip cap,
// unlike H2's ConditionChips island), plus the `character` v3 payload body
// (traits, equipment, disguise, guild, wallet, persona). In every mode the
// status sections render; when the `character` panel is unavailable the
// drawer shows the registry-owned reason and invents nothing. The 親密狀態
// (intimate) block the 設計稿 shows has no backing field, so it is absent
// (task 5.6). A single labelled control opens the skill drawer (task 5.5).
import { computed } from "vue";
import { gaugeRatio } from "./vitals.js";
import EquipmentDoll from "./EquipmentDoll.vue";

const props = defineProps({
  // The committed `status` v1 panel payload (vitals + conditions).
  status: { type: Object, required: true },
  // The committed `character` v3 panel payload (traits/equipment/disguise/...).
  character: { type: Object, required: true },
  // The derived low-HP presentation state (store view.vitals.lowHp).
  lowHp: { type: Boolean, default: false },
});

// Per-severity glyph shapes: the same non-colour-separated set H2's
// ConditionChips uses, so no two severities differ by colour alone.
const SEVERITY_GLYPHS = {
  beneficial: "▲",
  informational: "◆",
  warning: "▽",
  harmful: "▼",
  critical: "✕",
};

const SEVERITY_LABELS = {
  beneficial: "增益",
  informational: "資訊",
  warning: "警示",
  harmful: "減益",
  critical: "致命",
};

const resources = computed(() => props.status?.resources ?? null);

// The three gauge rows (hp/mp/sp). A missing gauge or non-numeric fields
// yield a null ratio (no value is invented); a non-positive maximum yields 0.
const VITALS = [
  { key: "hp", label: "生命" },
  { key: "mp", label: "氣力" },
  { key: "sp", label: "精力" },
];

function gaugeRatioPct(gauge) {
  return gaugeRatio(gauge);
}

// The full condition roster: every committed condition, each with its
// severity glyph + severity label, its label, its remaining duration (only
// when the payload supplies remaining_seconds, verbatim — never decremented
// between revisions) and every derived modifier value.
const conditions = computed(() => (Array.isArray(props.status?.conditions) ? props.status.conditions : []));

function conditionName(condition) {
  const parts = [condition.label ?? condition.code];
  if (typeof condition.remaining_seconds === "number") {
    parts.push(`剩 ${condition.remaining_seconds} 秒`);
  }
  const mods = condition.modifiers;
  if (mods && typeof mods === "object") {
    for (const [key, value] of Object.entries(mods)) {
      parts.push(`${key} ${value}`);
    }
  }
  return parts.join("，");
}

// The `character` body (task 5.3): render the trait table (true values only),
// equipment, disguise, guild and persona. When the panel is unavailable,
// show the registry-owned reason and invent no rows.
const characterAvailable = computed(() => props.character?.available !== false);
const characterReason = computed(() => (characterAvailable.value ? null : (props.character?.reason ?? null)));

const traits = computed(() => (characterAvailable.value && Array.isArray(props.character?.traits) ? props.character.traits : []));

function traitValue(row) {
  return row.max === null ? String(row.current) : `${row.current} / ${row.max}`;
}

// The equipment section is now the EquipmentDoll component (task 6.3); the
// doll reads `character.equipment` itself, so the flat list's computed is
// retired.

// The disguise section (task 5.4): the `displayed[]` values paired with the
// true trait they describe, shown as a 真值 / 顯示 side-by-side comparison,
// with the standing statement that combat always resolves on true traits.
const disguise = computed(() => (characterAvailable.value ? (props.character?.disguise ?? null) : null));
const disguiseActive = computed(() => disguise.value?.active === true);
const displayedRows = computed(() => {
  const rows = disguise.value?.displayed;
  if (!Array.isArray(rows)) return [];
  return rows.map((row) => {
    const trueRow = traits.value.find((t) => t.key === row.key);
    return {
      key: row.key,
      label: row.label,
      value: row.value,
      trueValue: trueRow ? trueRow.current : null,
    };
  });
});

const guild = computed(() => (characterAvailable.value ? (props.character?.guild ?? null) : null));

function formatCopper(value) {
  return String(value ?? 0).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}
const wallet = computed(() => (characterAvailable.value ? Math.max(0, props.character?.wallet ?? 0) : 0));
const personaBackground = computed(() => (characterAvailable.value ? (props.character?.persona?.background ?? null) : null));
</script>

<template>
  <section class="character-status-drawer" data-testid="character-status-drawer">
    <h3 class="character-status-drawer__title" data-testid="character-status-drawer__title">角色狀態</h3>

    <!-- The single labelled control that opens the skill drawer (task 5.5). -->
    <button
      type="button"
      class="character-status-drawer__skill-link"
      data-testid="character-status-drawer__open-skill"
      @click="$emit('open-skill')"
    >
      技能書
    </button>

    <!-- Vitals: the three gauges, rendered directly from status.resources. -->
    <section class="character-status-drawer__section" data-testid="character-status-drawer__vitals" aria-label="生命指標">
      <div
        v-for="v in VITALS"
        :key="v.key"
        class="character-status-drawer__vital"
        :data-testid="`character-status-drawer__vital--${v.key}`"
        :data-low="String(v.key === 'hp' && lowHp)"
      >
        <span class="character-status-drawer__vital-key">{{ v.label }}</span>
        <span class="character-status-drawer__vital-track" aria-hidden="true">
          <span
            class="character-status-drawer__vital-fill"
            :style="{ width: (gaugeRatioPct(resources?.[v.key]) ?? 0) + '%' }"
          ></span>
        </span>
        <span v-if="v.key === 'hp' && lowHp" class="character-status-drawer__vital-danger" data-testid="character-status-drawer__vital-danger">
          危險
        </span>
        <span class="character-status-drawer__vital-value" :data-testid="`character-status-drawer__vital-value--${v.key}`">
          {{ resources?.[v.key]?.current ?? "—" }} / {{ resources?.[v.key]?.maximum ?? "—" }}
        </span>
      </div>
    </section>

    <!-- The full condition roster (no cap, unlike H2's island). -->
    <section class="character-status-drawer__section" data-testid="character-status-drawer__conditions" aria-label="狀態">
      <p v-if="conditions.length === 0" class="character-status-drawer__empty" data-testid="character-status-drawer__conditions-empty">
        無狀態
      </p>
      <div
        v-for="condition in conditions"
        :key="condition.code"
        class="character-status-drawer__condition"
        :data-testid="`character-status-drawer__condition--${condition.code}`"
        :data-severity="condition.severity"
      >
        <span class="character-status-drawer__condition-glyph" aria-hidden="true">
          {{ SEVERITY_GLYPHS[condition.severity] ?? "◆" }}
        </span>
        <span class="character-status-drawer__condition-severity">{{ SEVERITY_LABELS[condition.severity] ?? condition.severity }}</span>
        <span class="character-status-drawer__condition-label">{{ condition.label ?? condition.code }}</span>
        <span
          v-if="typeof condition.remaining_seconds === 'number'"
          class="character-status-drawer__condition-timer"
          :data-testid="`character-status-drawer__condition-timer--${condition.code}`"
        >
          剩 {{ condition.remaining_seconds }} 秒
        </span>
        <span
          v-for="(value, key) in (condition.modifiers || {})"
          :key="key"
          class="character-status-drawer__condition-mod"
          :data-testid="`character-status-drawer__condition-mod--${condition.code}-${key}`"
        >
          {{ key }} {{ value }}
        </span>
      </div>
    </section>

    <!-- The character body (task 5.3): the character-backed sections. When the
         panel is unavailable, the registry-owned reason is shown and nothing
         is fabricated. -->
    <p
      v-if="!characterAvailable && characterReason"
      class="character-status-drawer__unavailable"
      data-testid="character-status-drawer__unavailable"
      :data-reason-code="characterReason.code"
    >
      {{ characterReason.message }}
    </p>

    <template v-if="characterAvailable">
      <section class="character-status-drawer__section" data-testid="character-status-drawer__traits" aria-label="屬性">
        <div
          v-for="row in traits"
          :key="row.key"
          class="character-status-drawer__trait"
          :data-testid="`character-status-drawer__trait--${row.key}`"
        >
          <span class="character-status-drawer__trait-key">{{ row.label }}</span>
          <span class="character-status-drawer__trait-value">{{ traitValue(row) }}</span>
        </div>
      </section>

      <!-- H4 (task 6.3): the equipment doll replaces the old flat equipment
           list — the named 主手/副手/盔甲 boxes, the accessory group, and the
           labelled passthrough row for other server-authored slot keys. -->
      <EquipmentDoll :character="character" />

      <!-- The disguise section (task 5.4): 真值 / 顯示 comparison. -->
      <section class="character-status-drawer__section" data-testid="character-status-drawer__disguise" :data-active="String(disguiseActive)" aria-label="偽裝">
        <template v-if="disguiseActive">
          <p class="character-status-drawer__disguise-description" data-testid="character-status-drawer__disguise-description">
            {{ disguise.description }}
          </p>
          <div
            v-for="row in displayedRows"
            :key="row.key"
            class="character-status-drawer__disguise-row"
            :data-testid="`character-status-drawer__disguise--${row.key}`"
          >
            <span class="character-status-drawer__disguise-key">{{ row.label }}</span>
            <span v-if="row.trueValue !== null" class="character-status-drawer__disguise-true" data-testid="character-status-drawer__disguise-true">
              真 {{ row.trueValue }}
            </span>
            <span class="character-status-drawer__disguise-displayed" data-testid="character-status-drawer__disguise-displayed">
              顯 {{ row.value }}
            </span>
          </div>
          <p class="character-status-drawer__disguise-note" data-testid="character-status-drawer__disguise-note">
            戰鬥永遠以真值決算，顯示值只影響外觀、公會登記與鑑定。
          </p>
        </template>
        <p v-else class="character-status-drawer__disguise-inactive" data-testid="character-status-drawer__disguise-inactive">
          目前沒有偽裝狀態。
        </p>
      </section>

      <section class="character-status-drawer__section" data-testid="character-status-drawer__guild" aria-label="公會">
        <div class="character-status-drawer__guild-row" data-testid="character-status-drawer__guild-rank">
          <span class="character-status-drawer__guild-key">階級</span>
          <span class="character-status-drawer__guild-value">{{ guild?.rank ?? "未加入公會" }}</span>
        </div>
        <div class="character-status-drawer__guild-row" data-testid="character-status-drawer__guild-merit">
          <span class="character-status-drawer__guild-key">功績</span>
          <span class="character-status-drawer__guild-value">{{ guild?.merit ?? 0 }}</span>
        </div>
      </section>

      <p class="character-status-drawer__wallet" data-testid="character-status-drawer__wallet">
        錢包：{{ formatCopper(wallet) }} 銅
      </p>

      <section
        v-if="personaBackground"
        class="character-status-drawer__section"
        data-testid="character-status-drawer__persona"
        aria-label="背景"
      >
        <p class="character-status-drawer__persona-background" data-testid="character-status-drawer__persona-background">
          {{ personaBackground }}
        </p>
      </section>
    </template>
  </section>
</template>

<style scoped>
.character-status-drawer {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
  box-sizing: border-box;
  padding: var(--sp-3) var(--sp-4);
  font-family: var(--f-sans);
}

.character-status-drawer__title {
  margin: 0;
  color: var(--paper-100);
  font-family: var(--f-display);
  font-size: 1em;
}

.character-status-drawer__skill-link {
  align-self: flex-start;
  padding: 3px var(--sp-3);
  color: var(--paper-500);
  background: none;
  border: var(--line);
  border-radius: var(--radius-sm);
  font-size: 0.85em;
  cursor: pointer;
}

.character-status-drawer__skill-link:hover {
  color: var(--paper-50);
  border-color: var(--seal-600);
}

.character-status-drawer__section {
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
  padding-top: var(--sp-2);
  border-top: var(--line);
}

.character-status-drawer__vital {
  display: grid;
  grid-template-columns: 3.5em 1fr auto auto;
  align-items: center;
  gap: var(--sp-2);
  font-size: 0.9em;
}

.character-status-drawer__vital-key {
  color: var(--paper-300);
}

.character-status-drawer__vital-track {
  height: 6px;
  background: var(--ink-800);
  border-radius: 3px;
  overflow: hidden;
  display: block;
}

.character-status-drawer__vital-fill {
  display: block;
  height: 100%;
  background: var(--seal-500);
}

.character-status-drawer__vital-danger {
  color: var(--crit);
  font-family: var(--f-mono);
  font-size: 0.8em;
  font-weight: 700;
}

.character-status-drawer__vital-value {
  color: var(--paper-50);
  font-family: var(--f-mono);
}

.character-status-drawer__condition {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--sp-2);
  padding: var(--sp-1) 0;
  font-size: 0.9em;
}

.character-status-drawer__condition-glyph {
  font-size: 1em;
}

.character-status-drawer__condition-severity {
  color: var(--paper-500);
  font-size: 0.8em;
}

.character-status-drawer__condition-label {
  color: var(--paper-50);
  font-weight: 600;
}

.character-status-drawer__condition-timer,
.character-status-drawer__condition-mod {
  color: var(--paper-300);
  font-family: var(--f-mono);
  font-size: 0.85em;
}

.character-status-drawer__empty,
.character-status-drawer__unavailable {
  margin: 0;
  color: var(--paper-500);
  font-size: 0.85em;
  padding: var(--sp-1) var(--sp-2);
  border: 1px dashed var(--ink-700);
  border-radius: var(--radius-sm);
}

.character-status-drawer__trait,
.character-status-drawer__guild-row,
.character-status-drawer__equipment-item {
  display: flex;
  justify-content: space-between;
  gap: var(--sp-2);
  font-size: 0.9em;
}

.character-status-drawer__trait-key,
.character-status-drawer__guild-key,
.character-status-drawer__equipment-slot {
  color: var(--paper-300);
  min-width: 3.5em;
}

.character-status-drawer__trait-value,
.character-status-drawer__guild-value {
  color: var(--paper-50);
  font-family: var(--f-mono);
}

.character-status-drawer__equipment-name {
  color: var(--paper-100);
  text-align: right;
}

.character-status-drawer__disguise-description {
  margin: 0 0 var(--sp-1);
  color: var(--paper-500);
  font-size: 0.8em;
  line-height: 1.5;
}

.character-status-drawer__disguise-row {
  display: flex;
  gap: var(--sp-2);
  font-size: 0.9em;
}

.character-status-drawer__disguise-key {
  color: var(--paper-300);
  min-width: 3.5em;
}

.character-status-drawer__disguise-true {
  color: var(--paper-500);
  font-family: var(--f-mono);
}

.character-status-drawer__disguise-displayed {
  margin-left: auto;
  color: var(--warn);
  font-family: var(--f-mono);
}

.character-status-drawer__disguise-note {
  margin: var(--sp-1) 0 0;
  color: var(--paper-300);
  font-size: 0.75em;
}

.character-status-drawer__disguise-inactive {
  margin: 0;
  color: var(--paper-500);
  font-size: 0.8em;
  line-height: 1.5;
}

.character-status-drawer__wallet {
  margin: 0;
  color: var(--paper-300);
  font-size: 0.9em;
}

.character-status-drawer__persona-background {
  margin: 0;
  color: var(--paper-300);
  font-size: 0.85em;
  line-height: 1.6;
}
</style>
