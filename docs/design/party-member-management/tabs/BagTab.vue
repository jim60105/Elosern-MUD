<script setup>
// Approved visual prototype (party member management §6.2): the 背包 tab.
// Equipment doll above the viewed member's bag; the detail's HoldingsStrip
// shows every member's count (consumables) or stat delta (equipment), and
// each non-owner cell gives to that member. In combat: counts only, no
// transfer, use becomes the member's round command, toggles stay free.
import { computed, ref, watch } from "vue";
import PmGlyph from "../PmGlyph.vue";
import { ACCESSORY_SLOTS, DELTAS, INVENTORY, ITEMS, MEMBERS } from "../prototype-data.js";

const props = defineProps({
  member: { type: Object, required: true },
  combat: { type: Boolean, default: false },
  initialItem: { type: String, default: null },
});

const SLOTS = ["主手", "副手", "盔甲", "飾品"];
const SLOT_GLYPH = { 主手: "sword", 副手: "shield", 盔甲: "armor", 飾品: "amulet" };

const inv = computed(() => INVENTORY[props.member.id]);
const slotFilter = ref(null);
const selected = ref(props.initialItem);
const qty = ref(1);

function equippedKeys(id) {
  const eq = INVENTORY[id].equipment;
  return new Set([eq.主手, eq.副手, eq.盔甲, ...eq.飾品].filter(Boolean));
}
const rows = computed(() => {
  const equipped = equippedKeys(props.member.id);
  return inv.value.bag
    .map(([key, held]) => ({ key, held, item: ITEMS[key], equipped: equipped.has(key) }))
    .filter((r) => !slotFilter.value || r.item.slot === slotFilter.value);
});
watch(
  () => [props.member.id, slotFilter.value],
  () => {
    if (!rows.value.some((r) => r.key === selected.value)) selected.value = rows.value[0]?.key ?? null;
    qty.value = 1;
  },
  { immediate: true },
);
const row = computed(() => rows.value.find((r) => r.key === selected.value) ?? null);
const isEquipment = computed(() => Boolean(row.value?.item.slot));
const maxQty = computed(() => (isEquipment.value ? 1 : row.value?.held ?? 1));

function heldBy(id, key) {
  return INVENTORY[id].bag.find(([k]) => k === key)?.[1] ?? 0;
}
function deltaClass(text) {
  if (!text || text === "±0") return "pm-none";
  if (text === "無法裝備") return "pm-none";
  return text.includes("−") ? "pm-down" : "pm-up";
}
const occupant = computed(() => {
  if (!row.value?.item.slot || row.value.item.slot === "飾品") return null;
  const key = inv.value.equipment[row.value.item.slot];
  return key && key !== row.value.key ? ITEMS[key].name : null;
});
function slotLabel(slot) {
  const eq = inv.value.equipment;
  if (slot === "飾品") return eq.飾品.length ? eq.飾品.map((k) => ITEMS[k].name).join("、") : null;
  return eq[slot] ? ITEMS[eq[slot]].name : null;
}
function toggleSlot(slot) {
  slotFilter.value = slotFilter.value === slot ? null : slot;
}
</script>

<template>
  <div class="pm-col pm-list">
    <div class="pm-sech">裝備</div>
    <div class="bt-doll">
      <button
        v-for="slot in SLOTS"
        :key="slot"
        type="button"
        class="bt-slot"
        :class="{ 'is-empty': !slotLabel(slot), 'is-selected': slotFilter === slot }"
        :aria-pressed="slotFilter === slot"
        @click="toggleSlot(slot)"
      >
        <span class="bt-slot__head"><PmGlyph :name="SLOT_GLYPH[slot]" />{{ slot }}<template v-if="slot === '飾品'"> {{ inv.equipment.飾品.length }}/{{ ACCESSORY_SLOTS }}</template></span>
        <b>{{ slotLabel(slot) ?? "—" }}</b>
      </button>
    </div>
    <div class="pm-sech">背包<span class="pm-sech__count">{{ slotFilter ? `${slotFilter} ‧ ` : "" }}{{ rows.length }} 種</span></div>
    <div role="listbox" aria-label="背包物品">
      <button
        v-for="r in rows"
        :key="r.key"
        type="button"
        role="option"
        class="pm-row"
        :class="{ 'is-selected': r.key === selected }"
        :aria-selected="r.key === selected"
        @click="selected = r.key; qty = 1"
      >
        <span class="pm-icon" :class="`pm-icon--${r.item.rarity}`"><PmGlyph :name="r.item.icon" /></span>
        <span class="pm-row__name">{{ r.item.name }}<span v-if="r.equipped" class="pm-tag">裝備中</span></span>
        <span class="pm-row__end">×{{ r.held }}</span>
      </button>
    </div>
  </div>

  <div class="pm-col pm-detail">
    <template v-if="row">
      <div class="pm-detail__scroll">
        <span class="pm-ribbon"><PmGlyph :name="row.item.icon" />{{ row.item.kind }}<template v-if="row.item.slot"> ‧ {{ row.item.slot }}</template></span>
        <h3 class="pm-hero__title">{{ row.item.name }}</h3>
        <p class="pm-hero__summary">{{ row.item.summary }}</p>

        <div class="pm-label">隊伍持有量</div>
        <div class="pm-hold">
          <div v-for="m in MEMBERS" :key="m.id" class="pm-hold__cell" :class="{ 'is-owner': m.id === member.id }">
            <span class="pm-avatar pm-avatar--sm">{{ m.initial }}</span>
            <span class="pm-hold__name">{{ m.name }}</span>
            <span class="pm-hold__count">{{ heldBy(m.id, row.key) }}</span>
            <span v-if="isEquipment && DELTAS[row.key]" class="pm-hold__delta" :class="deltaClass(DELTAS[row.key][m.id])">{{ DELTAS[row.key][m.id] }}</span>
            <template v-if="!combat">
              <span v-if="m.id === member.id" class="pm-hold__owner">持有者</span>
              <button v-else-if="row.equipped" type="button" class="pm-hold__give" aria-disabled="true" style="color: var(--paper-700)">需先卸下</button>
              <button v-else type="button" class="pm-hold__give"><PmGlyph name="give" />交給{{ m.name }}<template v-if="!isEquipment"> ×{{ qty }}</template></button>
            </template>
          </div>
        </div>
      </div>

      <div class="pm-bar">
        <template v-if="combat">
          <span class="pm-bar__reason">戰鬥中無法交換物品</span>
          <button v-if="isEquipment" type="button" class="pm-btn pm-btn--primary">{{ row.equipped ? "卸下" : occupant ? `裝備（替換${occupant}）` : "裝備" }}</button>
          <button v-else type="button" class="pm-btn pm-btn--primary">設為{{ member.name }}本回合的行動…</button>
        </template>
        <template v-else>
          <div v-if="!isEquipment" class="pm-stepper" role="group" aria-label="數量">
            <button type="button" aria-label="減少" @click="qty = Math.max(1, qty - 1)"><PmGlyph name="minus" /></button>
            <output>{{ qty }}</output>
            <button type="button" aria-label="增加" @click="qty = Math.min(maxQty, qty + 1)"><PmGlyph name="plus" /></button>
          </div>
          <button v-if="isEquipment" type="button" class="pm-btn pm-btn--primary">{{ row.equipped ? "卸下" : occupant ? `裝備（替換${occupant}）` : "裝備" }}</button>
          <button v-else type="button" class="pm-btn pm-btn--primary" :aria-disabled="member.knocked_out">使用…</button>
        </template>
      </div>
    </template>
  </div>
</template>

<style scoped>
.bt-doll { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: var(--sp-2); }
.bt-slot {
  display: grid;
  gap: 2px;
  padding: var(--sp-2);
  text-align: left;
  color: var(--paper-500);
  font-size: var(--text-xs);
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid var(--pm-line);
  border-radius: var(--radius-sm);
  cursor: pointer;
  min-width: 0;
}
.bt-slot__head { display: flex; align-items: center; gap: var(--sp-1); }
.bt-slot b { color: var(--paper-100); font: 500 var(--text-sm) var(--f-serif); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.bt-slot.is-empty { border-style: dashed; }
.bt-slot.is-empty b { color: var(--paper-700); }
.bt-slot.is-selected { border-color: var(--seal-500); box-shadow: 0 0 0 1px var(--seal-700); }
</style>
