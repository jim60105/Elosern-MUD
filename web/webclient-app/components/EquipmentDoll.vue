<script setup>
// EquipmentDoll (H4, webclient-hud-04-reference-drawers, task 6.3):
// the equipment doll rendered from the committed `character` v3 payload's
// `equipment[]`. It lays out the three named slot boxes (主手 / 副手 / 盔甲),
// an accessory group for the 0..3 `accessory` rows, and a labelled
// passthrough row for any other server-authored slot key. No rarity borders,
// no per-item stats line, no comparison tooltip, and no use / consume / equip
// control (task 6.4) — the doll is a read-only presentation of what is
// equipped and held.
import { computed } from "vue";

const props = defineProps({
  // The committed `character` v3 panel payload (or the unavailable form).
  character: { type: Object, required: true },
});

const available = computed(() => props.character?.available !== false);
const equipment = computed(() =>
  available.value && Array.isArray(props.character?.equipment) ? props.character.equipment : [],
);

// The three named slot boxes. Each shows the equipped item's display name or
// an explicit empty state.
const NAMED_SLOTS = [
  { slot: "weapon_main", label: "主手" },
  { slot: "weapon_off", label: "副手" },
  { slot: "armor", label: "盔甲" },
];

function slotItem(slot) {
  return equipment.value.find((row) => row.slot === slot) || null;
}

// The accessory group: the 0..3 `accessory` rows.
const accessoryRows = computed(() =>
  equipment.value.filter((row) => row.slot === "accessory"),
);

// The labelled passthrough: any server-authored slot key outside the named
// slots and `accessory` renders a labelled row (never dropped, never a
// fabricated value).
const OTHER_SLOTS = ["weapon_main", "weapon_off", "armor", "accessory"];
const otherRows = computed(() =>
  equipment.value.filter((row) => OTHER_SLOTS.indexOf(row.slot) === -1),
);

function slotLabel(slot) {
  const known = { weapon_main: "主手", weapon_off: "副手", armor: "盔甲", accessory: "飾品" };
  return known[slot] ?? slot;
}
</script>

<template>
  <section class="equipment-doll" data-testid="equipment-doll">
    <h3 class="equipment-doll__title" data-testid="equipment-doll__title">裝備人偶</h3>

    <p
      v-if="!available"
      class="equipment-doll__unavailable"
      data-testid="equipment-doll__unavailable"
      :data-reason-code="character.reason?.code"
    >
      {{ character.reason?.message }}
    </p>

    <template v-else>
      <!-- The three named slot boxes with an explicit empty state. -->
      <div class="equipment-doll__slots">
        <div
          v-for="s in NAMED_SLOTS"
          :key="s.slot"
          class="equipment-doll__slot-box"
          :data-testid="`equipment-doll__slot--${s.slot}`"
          :data-empty="String(slotItem(s.slot) === null)"
        >
          <p class="equipment-doll__slot-label">{{ s.label }}</p>
          <p v-if="slotItem(s.slot)" class="equipment-doll__slot-item">
            {{ slotItem(s.slot).display_name }}
          </p>
          <p v-else class="equipment-doll__slot-empty" :data-testid="`equipment-doll__slot-empty--${s.slot}`">
            未裝備
          </p>
        </div>
      </div>

      <!-- The accessory group (0..3 accessory rows). -->
      <section
        v-if="accessoryRows.length > 0"
        class="equipment-doll__section"
        data-testid="equipment-doll__accessories"
        aria-label="飾品"
      >
        <p class="equipment-doll__section-title">飾品</p>
        <div
          v-for="(row, index) in accessoryRows"
          :key="`${row.item_key}-${index}`"
          class="equipment-doll__row"
          :data-testid="`equipment-doll__accessory--${row.item_key}`"
        >
          <span class="equipment-doll__row-name">{{ row.display_name }}</span>
          <span class="equipment-doll__row-held">{{ row.held }}</span>
        </div>
      </section>

      <!-- The labelled passthrough row for other server-authored slot keys. -->
      <section
        v-if="otherRows.length > 0"
        class="equipment-doll__section"
        data-testid="equipment-doll__other-slots"
        aria-label="其他槽位"
      >
        <div
          v-for="(row, index) in otherRows"
          :key="`${row.slot}-${index}`"
          class="equipment-doll__row"
          :data-testid="`equipment-doll__slot-row--${row.slot}`"
          :data-slot="row.slot"
        >
          <span class="equipment-doll__row-slot">{{ slotLabel(row.slot) }}</span>
          <span class="equipment-doll__row-name">{{ row.display_name }}</span>
          <span class="equipment-doll__row-held">{{ row.held }}</span>
        </div>
      </section>

      <p v-if="equipment.length === 0" class="equipment-doll__empty" data-testid="equipment-doll__empty">
        目前沒有裝備任何物品。
      </p>
    </template>
  </section>
</template>

<style scoped>
.equipment-doll {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
  font-family: var(--f-sans);
}

.equipment-doll__title {
  margin: 0;
  color: var(--paper-100);
  font-family: var(--f-display);
  font-size: 1em;
}

.equipment-doll__unavailable {
  margin: 0;
  padding: var(--sp-1) var(--sp-2);
  color: var(--paper-500);
  font-size: 0.85em;
  border: 1px dashed var(--ink-700);
  border-radius: var(--radius-sm);
}

.equipment-doll__slots {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--sp-2);
}

.equipment-doll__slot-box {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: var(--sp-2);
  background: var(--panel-hi);
  border: var(--line);
  border-radius: var(--radius-sm);
}

.equipment-doll__slot-label {
  margin: 0;
  color: var(--paper-500);
  font-size: 0.75em;
}

.equipment-doll__slot-item {
  margin: 0;
  color: var(--paper-50);
  font-size: 0.9em;
}

.equipment-doll__slot-empty {
  margin: 0;
  color: var(--paper-500);
  font-size: 0.85em;
}

.equipment-doll__section {
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
  padding-top: var(--sp-2);
  border-top: var(--line);
}

.equipment-doll__section-title {
  margin: 0;
  color: var(--paper-300);
  font-size: 0.85em;
}

.equipment-doll__row {
  display: grid;
  grid-template-columns: minmax(4em, auto) 1fr auto;
  align-items: center;
  gap: var(--sp-2);
  padding: 2px 0;
  font-size: 0.9em;
}

.equipment-doll__row-slot {
  color: var(--paper-500);
  font-size: 0.85em;
}

.equipment-doll__row-name {
  color: var(--paper-50);
}

.equipment-doll__row-held {
  color: var(--paper-500);
  font-family: var(--f-mono);
  text-align: right;
}

.equipment-doll__empty {
  margin: 0;
  color: var(--paper-500);
  font-size: 0.85em;
}
</style>
