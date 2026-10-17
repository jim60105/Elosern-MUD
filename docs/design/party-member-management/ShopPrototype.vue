<script setup>
// Approved visual prototype of the shop window
// (docs/superpowers/specs/2026-10-18-party-member-management-ui-design.md §7).
// Reference only: self-contained mock data, not wired to any payload.
// The member rail selects the recipient (購買) or the seller (出售); one
// price per view; the party purse pays and receives.
import { computed, ref, watch } from "vue";
import "./prototype.css";
import PmGlyph from "./PmGlyph.vue";
import MemberRail from "./MemberRail.vue";
import { DELTAS, INVENTORY, ITEMS, MEMBERS, PURSE, SHOP } from "./prototype-data.js";

const props = defineProps({
  initialTab: { type: String, default: "buy" },
  initialMember: { type: Number, default: 2 },
});

const tab = ref(props.initialTab);
const memberId = ref(props.initialMember);
const member = computed(() => MEMBERS.find((m) => m.id === memberId.value));
const qty = ref(1);
const selected = ref(null);

function equippedKeys(id) {
  const eq = INVENTORY[id].equipment;
  return new Set([eq.主手, eq.副手, eq.盔甲, ...eq.飾品].filter(Boolean));
}
function heldBy(id, key) {
  return INVENTORY[id].bag.find(([k]) => k === key)?.[1] ?? 0;
}
const stock = computed(() => SHOP.stock.map((r) => ({ ...r, key: r.item, data: ITEMS[r.item] })));
const sellable = computed(() => {
  const equipped = equippedKeys(memberId.value);
  return INVENTORY[memberId.value].bag
    .map(([key, held]) => ({ key, data: ITEMS[key], held: held - (equipped.has(key) ? 1 : 0), sell: Math.floor((SHOP.stock.find((s) => s.item === key)?.buy ?? sellBase(key)) / 2) }))
    .filter((r) => r.held > 0 && r.key !== "herb_notes");
});
function sellBase(key) {
  return { rusty_sword: 90, torn_leather: 120, warhammer: 540, potion_heal: 30, ration: 8, moon_herb: 16, potion_mana: 24, birch_staff: 140, linen_robe: 120, moonstone: 260 }[key] ?? 20;
}
const rows = computed(() => (tab.value === "buy" ? stock.value : sellable.value));
watch(
  () => [tab.value, memberId.value],
  () => {
    if (!rows.value.some((r) => r.key === selected.value)) selected.value = rows.value.find((r) => tab.value !== "buy" || r.stock > 0)?.key ?? null;
    qty.value = 1;
  },
  { immediate: true },
);
const row = computed(() => rows.value.find((r) => r.key === selected.value) ?? null);

function deltaFor(key, id) {
  return DELTAS[key]?.[id] ?? null;
}
// A row's delta with a shape cue beside the color: ▲ gain, ▼ loss.
function arrowed(text) {
  if (!text || text === "±0" || text === "無法裝備") return text;
  return `${text.includes("−") ? "▼" : "▲"} ${text}`;
}
function deltaClass(text) {
  if (!text || text === "±0" || text === "無法裝備") return "pm-none";
  return text.includes("−") ? "pm-down" : "pm-up";
}
const current = computed(() => {
  if (!row.value?.data.slot) return null;
  const key = INVENTORY[memberId.value].equipment[row.value.data.slot];
  return key ? ITEMS[key] : null;
});
const maxQty = computed(() => (tab.value === "buy" ? row.value?.stock ?? 1 : row.value?.held ?? 1));
const total = computed(() => (row.value ? (tab.value === "buy" ? row.value.buy : row.value.sell) * qty.value : 0));
const after = computed(() => (tab.value === "buy" ? PURSE - total.value : PURSE + total.value));
const fmt = (n) => n.toLocaleString("en-US");
</script>

<template>
  <section class="pm" role="dialog" :aria-label="SHOP.name">
    <header class="pm-head">
      <span class="pm-head__seal"><PmGlyph name="shop" /></span>
      <h2 class="pm-head__title">{{ SHOP.name }}<small>{{ SHOP.host }} ‧ 營業中</small></h2>
      <div class="pm-top" role="tablist" aria-label="交易">
        <button type="button" role="tab" class="pm-top__tab" :class="{ 'is-active': tab === 'buy' }" :aria-selected="tab === 'buy'" @click="tab = 'buy'"><PmGlyph name="reward_copper" /><span class="pm-top__label">購買</span></button>
        <button type="button" role="tab" class="pm-top__tab" :class="{ 'is-active': tab === 'sell' }" :aria-selected="tab === 'sell'" @click="tab = 'sell'"><PmGlyph name="give" /><span class="pm-top__label">出售</span></button>
      </div>
      <span class="pm-head__extra"><PmGlyph name="reward_copper" />{{ fmt(PURSE) }} 銅</span>
      <button type="button" class="pm-head__close" aria-label="關閉"><PmGlyph name="close" /></button>
    </header>

    <div class="pm-body">
      <MemberRail :members="MEMBERS" :selected="memberId" @select="memberId = $event" />

      <div class="pm-col pm-list">
        <div class="pm-sech">{{ tab === "buy" ? `為${member.name}挑選` : `${member.name}可出售的物品` }}<span class="pm-sech__count">{{ rows.length }}</span></div>
        <div role="listbox" :aria-label="tab === 'buy' ? '貨架' : '可出售的物品'">
          <button
            v-for="r in rows"
            :key="r.key"
            type="button"
            role="option"
            class="pm-row"
            :class="{ 'is-selected': r.key === selected, 'is-dim': tab === 'buy' && r.stock === 0 }"
            :aria-selected="r.key === selected"
            @click="selected = r.key; qty = 1"
          >
            <span class="pm-icon" :class="`pm-icon--${r.data.rarity}`"><PmGlyph :name="r.data.icon" /></span>
            <span class="pm-row__name">{{ r.data.name }}
              <span class="pm-row__sub" v-if="tab === 'buy'">{{ r.stock ? `庫存 ${r.stock}` : "售完" }}</span>
              <span class="pm-row__sub" v-else>持有 {{ r.held }}</span>
            </span>
            <span class="pm-row__end">
              <span class="pm-row__price">{{ fmt(tab === "buy" ? r.buy : r.sell) }}</span>
              <span v-if="tab === 'buy' && r.data.slot" class="pm-row__sub" :class="deltaClass(deltaFor(r.key, memberId))">{{ arrowed(deltaFor(r.key, memberId)) }}</span>
              <span v-else-if="tab === 'buy'" class="pm-row__sub">持有 {{ heldBy(memberId, r.key) }}</span>
            </span>
          </button>
        </div>
      </div>

      <div class="pm-col pm-detail">
        <template v-if="row">
          <div class="pm-detail__scroll">
            <span class="pm-ribbon"><PmGlyph :name="row.data.icon" />{{ row.data.kind }}<template v-if="row.data.slot"> ‧ {{ row.data.slot }}</template></span>
            <h3 class="pm-hero__title">{{ row.data.name }}</h3>
            <p class="pm-hero__summary">{{ row.data.summary }}</p>

            <template v-if="tab === 'buy' && row.data.slot">
              <div class="pm-label">{{ member.name }}的{{ row.data.slot }}</div>
              <div class="sh-vs">
                <div class="sh-box">目前<b>{{ current ? current.name : "（空）" }}</b><span v-if="current">{{ current.summary }}</span></div>
                <PmGlyph name="give" />
                <div class="sh-box is-new">換上後<b>{{ row.data.name }}</b><span :class="deltaClass(deltaFor(row.key, memberId))">{{ deltaFor(row.key, memberId) }}</span></div>
              </div>
              <div class="pm-label">其他成員</div>
              <div class="sh-chips">
                <button v-for="m in MEMBERS.filter((x) => x.id !== memberId)" :key="m.id" type="button" class="sh-chip" @click="memberId = m.id">
                  <span class="pm-avatar pm-avatar--xs">{{ m.initial }}</span><span :class="deltaClass(deltaFor(row.key, m.id))">{{ deltaFor(row.key, m.id) }}</span>
                </button>
              </div>
            </template>
            <template v-else-if="tab === 'buy'">
              <div class="pm-label">隊伍持有量</div>
              <div class="pm-hold">
                <button v-for="m in MEMBERS" :key="m.id" type="button" class="pm-hold__cell" :class="{ 'is-selected': m.id === memberId }" @click="memberId = m.id">
                  <span class="pm-avatar pm-avatar--sm">{{ m.initial }}</span><span class="pm-hold__name">{{ m.name }}</span><span class="pm-hold__count">{{ heldBy(m.id, row.key) }}</span>
                </button>
              </div>
            </template>
          </div>

          <div class="pm-bar">
            <div class="pm-stepper" role="group" aria-label="數量">
              <button type="button" aria-label="減少" @click="qty = Math.max(1, qty - 1)"><PmGlyph name="minus" /></button>
              <output>{{ qty }}</output>
              <button type="button" aria-label="增加" @click="qty = Math.min(maxQty, qty + 1)"><PmGlyph name="plus" /></button>
            </div>
            <span class="pm-bar__sum">{{ tab === "buy" ? "花費" : "得到" }} <b>{{ fmt(total) }}</b> ‧ 剩餘 {{ fmt(after) }} 銅</span>
            <button type="button" class="pm-btn pm-btn--primary" :aria-disabled="tab === 'buy' && row.stock === 0">{{ tab === "buy" ? `買給${member.name}` : "出售" }}</button>
          </div>
        </template>
      </div>
    </div>
  </section>
</template>

<style scoped>
.sh-vs { display: grid; grid-template-columns: 1fr auto 1fr; gap: var(--sp-3); align-items: center; color: var(--paper-500); font-size: var(--text-xs); }
.sh-box { display: grid; gap: 2px; padding: var(--sp-2) var(--sp-3); border: 1px solid var(--pm-line); border-radius: var(--radius-sm); }
.sh-box b { color: var(--paper-50); font: 500 var(--text-md) var(--f-serif); }
.sh-box.is-new { border-color: var(--seal-700); background: rgba(207, 68, 68, 0.08); }
.sh-chips { display: flex; flex-wrap: wrap; gap: var(--sp-2); }
.sh-chip { display: inline-flex; align-items: center; gap: var(--sp-2); padding: 2px var(--sp-3) 2px 2px; font-size: var(--text-xs); background: transparent; border: 1px solid var(--pm-line); border-radius: var(--radius-pill); cursor: pointer; }
</style>
