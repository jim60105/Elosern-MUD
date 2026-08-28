<script setup>
// EquipmentDoll (H4, webclient-hud-04-reference-drawers, task 6.3;
// restyle-inventory-equipment-slots): the equipment doll rendered from the
// committed `character` v4 payload's `equipment[]`. The binding design's
// compact paper-doll slot language: a two-column square grid of four stable
// positions (主手 / 副手 / 盔甲 / 飾品 summary), a fixed slot-role SVG per
// position (the off-hand position is the iconless position), an explicit
// dashed empty state, and labelled passthrough rows for any other
// server-authored slot key. No rarity borders, no per-item stats line, no
// comparison tooltip, and no use / consume / equip control (task 6.4) — the
// doll is a read-only presentation of what is equipped and held.
import { computed } from "vue";

const props = defineProps({
  // The committed `character` v4 panel payload (or the unavailable form).
  character: { type: Object, required: true },
});

const available = computed(() => props.character?.available !== false);
const equipment = computed(() =>
  available.value && Array.isArray(props.character?.equipment) ? props.character.equipment : [],
);

// The four stable positions of the binding design's `.dollslots` two-column
// square grid: the three server singleton slots plus the accessory summary
// position.
const SLOT_POSITIONS = [
  { slot: "weapon_main" },
  { slot: "weapon_off" },
  { slot: "armor" },
  { slot: "accessory" },
];

// The closed local SVG map for the four fixed equipment slot roles (task
// 1.1): a symbol represents a fixed slot role, never the item in it. The
// off-hand position is the iconless position (the binding design's dashed
// empty box), so its map entry carries a null `d`.
const SLOT_ICONS = {
  weapon_main: { label: "主手", d: "M5 19 17 7M17 7l-3 1M5 19l2-3" },
  weapon_off: { label: "副手", d: null },
  armor: { label: "盔甲", d: "M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6l-8-3Z" },
  accessory: { label: "飾品", d: "M12 4a5 5 0 1 1 0 10 5 5 0 0 1 0-10zM12 14v6" },
};

// The committed row for a fixed slot role, or null when the payload carries
// no such row (the explicit empty state, never an invented item).
function slotItem(slot) {
  return equipment.value.find((row) => row.slot === slot) || null;
}

// The Traditional Chinese slot caption for a position, falling back to the
// server-authored slot key for unrecognised slots.
function slotLabel(slot) {
  const entry = SLOT_ICONS[slot];
  return entry ? entry.label : slot;
}

// The fixed local SVG path for a position, or null for the iconless
// off-hand position.
function slotIcon(slot) {
  const entry = SLOT_ICONS[slot];
  return entry && entry.d;
}

// The accessory group: the 0..3 `accessory` rows (the retained detail list).
const accessoryRows = computed(() =>
  equipment.value.filter((row) => row.slot === "accessory"),
);
const accessoryCount = computed(() => accessoryRows.value.length);

// The labelled passthrough: any server-authored slot key outside the named
// positions and `accessory` renders a labelled row (never dropped, never a
// fabricated value).
const OTHER_SLOTS = ["weapon_main", "weapon_off", "armor", "accessory"];
const otherRows = computed(() =>
  equipment.value.filter((row) => OTHER_SLOTS.indexOf(row.slot) === -1),
);

// Duplicate committed rows for a recognised singleton slot: the square grid
// consumes the first row per slot; any further row with the same slot
// renders as a labelled overflow row (the no-drop guarantee — the character
// panel validator accepts duplicate slot rows).
const SINGLETON_SLOTS = ["weapon_main", "weapon_off", "armor"];
const duplicateRows = computed(() => {
  const seen = {};
  const duplicates = [];
  for (const row of equipment.value) {
    if (SINGLETON_SLOTS.indexOf(row.slot) === -1) {
      continue;
    }
    if (seen[row.slot]) {
      duplicates.push(row);
    }
    seen[row.slot] = true;
  }
  return duplicates;
});
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
      <!-- The binding design's `.dollslots` grid: two columns of 74px square
           cells. Each position renders its fixed slot-role symbol (selected
           by slot identity only); the off-hand position is iconless; empty
           singleton slots render the dashed explicit empty state. -->
      <div class="equipment-doll__slots">
        <div
          v-for="p in SLOT_POSITIONS"
          :key="p.slot"
          class="equipment-doll__slot"
          :data-testid="`equipment-doll__slot--${p.slot}`"
        >
          <div
            class="equipment-doll__box"
            :class="{ 'equipment-doll__box--empty': p.slot !== 'accessory' && slotItem(p.slot) === null }"
          >
            <template v-if="p.slot === 'accessory'">
              <svg
                v-if="slotIcon('accessory')"
                class="equipment-doll__icon"
                width="32"
                height="32"
                viewBox="0 0 24 24"
                fill="none"
                aria-hidden="true"
              >
                <path :d="slotIcon('accessory')" stroke="currentColor" stroke-width="1.6" />
              </svg>
              <p class="equipment-doll__accessory-count" data-testid="equipment-doll__accessory-count">
                {{ accessoryCount }} 件
              </p>
            </template>
            <template v-else>
              <svg
                v-if="slotItem(p.slot) && slotIcon(p.slot)"
                class="equipment-doll__icon"
                width="32"
                height="32"
                viewBox="0 0 24 24"
                fill="none"
                aria-hidden="true"
              >
                <path :d="slotIcon(p.slot)" stroke="currentColor" stroke-width="1.6" />
              </svg>
              <p
                v-else-if="slotItem(p.slot) === null"
                class="equipment-doll__slot-empty"
                :data-testid="`equipment-doll__slot-empty--${p.slot}`"
              >
                未裝備
              </p>
            </template>
          </div>
          <p class="equipment-doll__caption">{{ slotLabel(p.slot) }}</p>
          <p
            v-if="p.slot !== 'accessory' && slotItem(p.slot)"
            class="equipment-doll__slot-item"
          >{{ slotItem(p.slot).display_name }}</p>
        </div>
      </div>

      <!-- The retained accessory detail group (0..3 accessory rows). -->
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

      <!-- Duplicate rows for a recognised singleton slot: the square grid
           shows only the first row per slot, so every further committed row
           for that slot renders as a labelled overflow row. -->
      <section
        v-if="duplicateRows.length > 0"
        class="equipment-doll__section"
        data-testid="equipment-doll__duplicates"
        aria-label="重複槽位列"
      >
        <div
          v-for="(row, index) in duplicateRows"
          :key="`${row.slot}-${index}`"
          class="equipment-doll__row"
          :data-testid="`equipment-doll__duplicate-row--${row.slot}-${index}`"
          :data-slot="row.slot"
        >
          <span class="equipment-doll__row-slot">{{ slotLabel(row.slot) }}</span>
          <span class="equipment-doll__row-name">{{ row.display_name }}</span>
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

/* The binding design's `.dollslots`: a two-column grid of 74px square cells
   with a 9px gap — the fixed cell size fits the 560px drawer with the item
   grid present. */
.equipment-doll__slots {
  display: grid;
  grid-template-columns: repeat(2, 74px);
  gap: 9px;
}

.equipment-doll__slot {
  display: flex;
  flex-direction: column;
  gap: 5px;
  width: 74px;
}

/* The binding design's `.dslot .box`: a square cell with the fixed slot-role
   symbol; the `.empty` variant uses a dashed outline for the explicit
   empty state. */
.equipment-doll__box {
  width: 74px;
  height: 74px;
  border: 1px solid var(--ink-600);
  border-radius: var(--radius-sm);
  background: var(--ink-820);
  display: grid;
  place-items: center;
  gap: 2px;
}

.equipment-doll__box--empty {
  border-style: dashed;
  color: var(--paper-700);
}

/* The binding design's `.dslot .box .ic`: a 32px gold slot-role symbol,
   selected by slot identity (never by the item in the slot). */
.equipment-doll__icon {
  width: 32px;
  height: 32px;
  color: var(--gold-400);
}

.equipment-doll__slot-empty {
  margin: 0;
  color: var(--paper-700);
  font-size: 10px;
}

/* The binding design's `.dslot .cap`: the visible slot caption below the
   cell; the committed item name wraps below the caption (long names never
   expand the square cells or overflow the drawer horizontally). */
.equipment-doll__caption {
  margin: 0;
  font-size: 10px;
  color: var(--paper-500);
  text-align: center;
}

.equipment-doll__slot-item {
  margin: 0;
  color: var(--paper-50);
  font-size: 0.9em;
  overflow-wrap: break-word;
}

/* The accessory summary cell: the committed accessory count in the gold
   mono numerals. */
.equipment-doll__accessory-count {
  margin: 0;
  font-family: var(--f-mono);
  font-size: 10px;
  color: var(--gold-400);
}

/* The retained accessory detail group and the unknown-slot labelled
   fallback rows (the no-drop guarantee). */
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
  align-items: center;
  gap: var(--sp-2);
  padding: 2px 0;
  font-size: 0.9em;
}

.equipment-doll__accessories .equipment-doll__row {
  grid-template-columns: 1fr auto;
}

.equipment-doll__other-slots .equipment-doll__row {
  grid-template-columns: minmax(4em, auto) 1fr auto;
}

.equipment-doll__duplicates .equipment-doll__row {
  grid-template-columns: minmax(4em, auto) 1fr;
}

.equipment-doll__row-slot {
  color: var(--paper-500);
  font-size: 0.85em;
}

.equipment-doll__row-name {
  color: var(--paper-50);
  overflow-wrap: break-word;
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
