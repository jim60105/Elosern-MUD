<script setup>
// CharacterPanel (B3 data family): the read-only expanded character surface.
// It renders the committed `character` panel payload (schema version 3)
// verbatim: the full eight-row trait table (true values only), the equipped
// items, the disguise block (displayed values kept distinct from the true
// traits they describe), guild rank/merit, wallet, and the persona
// background. Disguised statistics are display-only and never substitute for
// the true trait rows. The intimate/adult block the 設計稿 shows has no
// backing field in this payload and is not built.
import { computed } from "vue";

const props = defineProps({
  // The committed `character` v3 panel payload.
  character: { type: Object, required: true },
});

// Display-only slot captions (the payload carries the raw slot key).
const SLOT_LABELS = {
  weapon_main: "主手",
  weapon_off: "副手",
  armor: "盔甲",
  accessory: "飾品",
};

const traits = computed(() =>
  Array.isArray(props.character.traits) ? props.character.traits : [],
);

// One trait row: gauges report "current / max"; statics and counters report
// the bare value (max null), mirroring the legacy character-menu model.
function traitValue(row) {
  return row.max === null ? String(row.current) : `${row.current} / ${row.max}`;
}

const equipment = computed(() =>
  Array.isArray(props.character.equipment) ? props.character.equipment : [],
);

function slotLabel(row) {
  return SLOT_LABELS[row.slot] ?? row.slot;
}

const disguise = computed(() => props.character.disguise ?? null);
const disguiseActive = computed(() => disguise.value?.active === true);

// Displayed values paired with the true trait they describe (when the trait
// table carries the same key) — shown side by side, never merged.
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

const guild = computed(() => props.character.guild ?? null);

function formatCopper(value) {
  return String(value).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

const wallet = computed(() => Math.max(0, props.character.wallet ?? 0));

const personaBackground = computed(() => props.character.persona?.background ?? null);
</script>

<template>
  <aside class="character-panel" data-testid="character-panel">
    <h3 class="character-panel__title" data-testid="character-panel__title">角色</h3>

    <section class="character-panel__section" data-testid="character-panel__traits" aria-label="屬性">
      <div
        v-for="row in traits"
        :key="row.key"
        class="character-panel__trait"
        :data-testid="`character-panel__trait--${row.key}`"
      >
        <span class="character-panel__trait-key">{{ row.label }}</span>
        <span class="character-panel__trait-value">{{ traitValue(row) }}</span>
      </div>
    </section>

    <section
      v-if="equipment.length > 0"
      class="character-panel__section"
      data-testid="character-panel__equipment"
      aria-label="裝備"
    >
      <div
        v-for="(row, index) in equipment"
        :key="`${row.slot}-${index}`"
        class="character-panel__equipment-item"
        data-testid="character-panel__equipment-item"
        :data-slot="row.slot"
      >
        <span class="character-panel__equipment-slot">{{ slotLabel(row) }}</span>
        <span class="character-panel__equipment-name">{{ row.display_name }}</span>
      </div>
    </section>

    <section
      class="character-panel__section"
      data-testid="character-panel__disguise"
      :data-active="String(disguiseActive)"
      aria-label="偽裝"
    >
      <template v-if="disguiseActive">
        <p class="character-panel__disguise-description" data-testid="character-panel__disguise-description">
          {{ disguise.description }}
        </p>
        <div
          v-for="row in displayedRows"
          :key="row.key"
          class="character-panel__disguise-row"
          :data-testid="`character-panel__disguise--${row.key}`"
          data-role="display"
        >
          <span class="character-panel__disguise-key">{{ row.label }}</span>
          <span v-if="row.trueValue !== null" class="character-panel__disguise-true" data-testid="character-panel__disguise-true">
            真 {{ row.trueValue }}
          </span>
          <span class="character-panel__disguise-displayed" data-testid="character-panel__disguise-displayed">
            顯 {{ row.value }}
          </span>
        </div>
      </template>
      <p v-else class="character-panel__disguise-inactive" data-testid="character-panel__disguise-inactive">
        目前沒有偽裝狀態。偽裝只影響顯示／公會登記／鑑定，戰鬥永遠用真值。
      </p>
    </section>

    <section class="character-panel__section" data-testid="character-panel__guild" aria-label="公會">
      <div class="character-panel__guild-row" data-testid="character-panel__guild-rank">
        <span class="character-panel__guild-key">階級</span>
        <span class="character-panel__guild-value"
          >{{ guild?.rank ?? "未加入公會" }}</span
        >
      </div>
      <div class="character-panel__guild-row" data-testid="character-panel__guild-merit">
        <span class="character-panel__guild-key">功績</span>
        <span class="character-panel__guild-value">{{ guild?.merit ?? 0 }}</span>
      </div>
    </section>

    <p class="character-panel__wallet" data-testid="character-panel__wallet">
      錢包：{{ formatCopper(wallet) }} 銅
    </p>

    <section
      v-if="personaBackground"
      class="character-panel__section"
      data-testid="character-panel__persona"
      aria-label="背景"
    >
      <p class="character-panel__persona-background" data-testid="character-panel__persona-background">
        {{ personaBackground }}
      </p>
    </section>
  </aside>
</template>

<style scoped>
.character-panel {
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

.character-panel__title {
  margin: 0;
  color: var(--paper-100);
  font-family: var(--f-display);
  font-size: 1em;
}

.character-panel__section {
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
  padding-top: var(--sp-2);
  border-top: var(--line);
}

.character-panel__trait,
.character-panel__guild-row,
.character-panel__equipment-item {
  display: flex;
  justify-content: space-between;
  gap: var(--sp-2);
  font-size: 0.9em;
}

.character-panel__trait-key,
.character-panel__guild-key,
.character-panel__equipment-slot {
  color: var(--paper-300);
  min-width: 3.5em;
}

.character-panel__trait-value,
.character-panel__guild-value {
  color: var(--paper-50);
  font-family: var(--f-mono);
}

.character-panel__equipment-name {
  color: var(--paper-100);
  text-align: right;
}

.character-panel__disguise-description {
  margin: 0 0 var(--sp-1);
  color: var(--paper-500);
  font-size: 0.8em;
  line-height: 1.5;
}

.character-panel__disguise-row {
  display: flex;
  gap: var(--sp-2);
  font-size: 0.9em;
}

.character-panel__disguise-key {
  color: var(--paper-300);
  min-width: 3.5em;
}

.character-panel__disguise-true {
  color: var(--paper-500);
  font-family: var(--f-mono);
}

.character-panel__disguise-displayed {
  margin-left: auto;
  color: var(--warn);
  font-family: var(--f-mono);
}

.character-panel__disguise-inactive {
  margin: 0;
  color: var(--paper-500);
  font-size: 0.8em;
  line-height: 1.5;
}

.character-panel__wallet {
  margin: 0;
  color: var(--paper-300);
  font-size: 0.9em;
}

.character-panel__persona-background {
  margin: 0;
  color: var(--paper-300);
  font-size: 0.85em;
  line-height: 1.6;
}
</style>
