<script setup>
// ShopWindow (webclient-shop-window, design §3.2/§4.3/§7): the merchant's
// window, mounted under the `shop` drawer key. It composes the shared
// WindowFrame (the shop seal, the host's name, 營業中 / 已打烊, the first-level
// tabs 購買 and 出售, and the party purse from `services.player.wallet` in the
// header) with the MemberRail of the committed `party` rows. A merchant sells
// one kind of goods, so no category rail is used.
//
// The rail's selection is the session's viewed member, shared with the party
// window: on 購買 it is the recipient, on 出售 the seller. Activating another
// entry emits `view-member` ({ memberId, itemKey }) and the host sends one
// `party.view_member {tab: "shop", item_key}` — the shown item rides along so
// the holdings answer follows. The server republishes the `services` rows
// for that member; the rail never switches optimistically, and while the
// request is in flight the rows' member facts are dimmed and trading is off.
//
// A row selection emits `view-item` and becomes the shown row once the host
// admits the request (`pendingItemKey`) or the committed `item_holdings`
// answers it. The detail shows the item, on 購買 for equipment a comparison of
// the recipient's committed current values against the server's change lines
// (no slot is committed for a stock row, so the replaced item is never named
// and nothing is added up), and the other members' chips from
// `item_holdings`; for anything else every member's held count. The action
// bar holds the quantity entry bounded by the row descriptor's committed
// quantity, the total and the display-only remaining purse, and 買給 X or 出售,
// sending one `shop.buy {item_key, quantity, recipient_id}` or `shop.sell
// {item_key, quantity, seller_id}` naming `shop.member_id`. One price per
// view; no rule text; committed disabled reasons and a trade's committed
// refusal (`tradeNotice`, e.g. insufficient_funds) are the only state lines.
import { computed, ref, watch } from "vue";
import ActionBar from "./ActionBar.vue";
import EmptyState from "./EmptyState.vue";
import HoldingsStrip from "./HoldingsStrip.vue";
import ListDetail from "./ListDetail.vue";
import MemberRail from "./MemberRail.vue";
import ShopRows from "./ShopRows.vue";
import WindowFrame from "./WindowFrame.vue";
import { glyphAttrs, glyphPath } from "./dock-icons.js";
import { itemIconPath, kindLabel, rarityLabel, unknownItemPath } from "./item-icons.js";
import { itemGlyph } from "./party-bag-model.js";
import { panelReason, railMembers, viewedMemberId } from "./party-window-model.js";
import {
  SHOP_WINDOW_TABS,
  SHOP_WINDOW_TAB_KEYS,
  actionOf,
  clampQuantity,
  currentTraitValues,
  deltaFacts,
  formatCopper,
  quantityBounds,
  rowByKey,
  servicesPurse,
  shopHoldings,
  shopMemberId,
  shopSection,
  tradePreview,
  unitPriceOf,
  viewRows,
} from "./shop-window-model.js";

const props = defineProps({
  // The committed `services` v7 panel (or its unavailable form).
  services: { type: Object, default: null },
  // The committed `party` v3 panel (the rail and the member names).
  party: { type: Object, default: null },
  // The committed `item_holdings` v1 panel (the selected item's answer).
  itemHoldings: { type: Object, default: null },
  // The committed `character` panel (the recipient's current values).
  character: { type: Object, default: null },
  // The member whose rail request is in flight, and the in-flight item.
  pendingMemberId: { type: Number, default: null },
  pendingItemKey: { type: String, default: null },
  // The last trade's committed refusal ({ code, message }) and whether a
  // trade is in flight.
  tradeNotice: { type: Object, default: null },
  tradePending: { type: Boolean, default: false },
  // Story seam: the tab shown on open.
  initialTab: { type: String, default: "buy" },
});

const emit = defineEmits(["close", "view-member", "view-item", "trade", "clear-notice"]);

const tab = ref(SHOP_WINDOW_TAB_KEYS.has(props.initialTab) ? props.initialTab : "buy");
const view = computed(() => tab.value);

// --------------------------------------------------------------- panels

const servicesReason = computed(() => panelReason(props.services));
const shop = computed(() => shopSection(props.services));
const purse = computed(() => servicesPurse(props.services));
// The exact merchant this surface was read for; a trade without it would be
// refused server-side, so the row stays untradeable instead.
const providerId = computed(() => {
  const value = shop.value?.provider_id;
  return Number.isSafeInteger(value) && value > 0 ? value : null;
});
const title = computed(() => {
  const name = props.services?.available === true ? props.services.host?.display_name : null;
  return typeof name === "string" && name.trim() !== "" ? name : "商店";
});
const subtitle = computed(() => (shop.value ? (shop.value.open ? "營業中" : "已打烊") : ""));

// --------------------------------------------------------------- members

const members = computed(() => railMembers(props.party));
const viewedId = computed(() => viewedMemberId(props.party));
const memberId = computed(() => shopMemberId(shop.value));
const railSelected = computed(() => viewedId.value ?? memberId.value);
const memberName = computed(() => members.value.find((entry) => entry.id === memberId.value)?.name ?? null);
// The rows describe `shop.member_id`; a rail that names someone else (a
// transient republish) or a rail request in flight keeps trading off.
const consistent = computed(() => viewedId.value === null || viewedId.value === memberId.value);
const memberPending = computed(() => props.pendingMemberId !== null);

function onRailSelect(id) {
  if (typeof id !== "number" || id === railSelected.value) return;
  emit("view-member", { memberId: id, itemKey: activeKey.value });
}

// --------------------------------------------------------------- selection

const rows = computed(() => viewRows(shop.value, view.value));
const committedKey = computed(() => {
  const holdings = props.itemHoldings;
  if (!holdings || holdings.available !== true || holdings.giver_id !== memberId.value) return null;
  return typeof holdings.item_key === "string" ? holdings.item_key : null;
});
// The last admitted or committed item; shown only while the open view lists
// it, so a tab switch keeps it when both views carry the item.
const selectedKey = ref(committedKey.value);
watch(
  () => props.pendingItemKey,
  (key) => {
    if (key !== null) selectedKey.value = key;
  },
);
watch(committedKey, (key) => {
  if (key !== null && props.pendingItemKey === null) selectedKey.value = key;
});
// A request that ended without its answer (rejected or failed) hands the
// selection back to the committed item, so the detail never shows a row
// whose holdings belong to another item.
watch(
  () => props.pendingItemKey,
  (key, previous) => {
    if (key === null && previous !== null && committedKey.value !== selectedKey.value) {
      selectedKey.value = committedKey.value;
    }
  },
);
const activeRow = computed(() => rowByKey(shop.value, view.value, selectedKey.value));
const activeKey = computed(() => activeRow.value?.item_key ?? null);

function onRowSelect(key) {
  if (memberId.value === null) return;
  if (key === activeKey.value || key === props.pendingItemKey) return;
  emit("view-item", { memberId: memberId.value, itemKey: key });
}

// --------------------------------------------------------------- detail

const iconPath = (row) => {
  const glyph = itemGlyph(row);
  if (glyph) return glyphPath(glyph);
  return (row?.presentation && itemIconPath(row.presentation.icon_key)) || unknownItemPath();
};
const iconAttrs = (row) => {
  const glyph = itemGlyph(row);
  return glyph ? glyphAttrs(glyph) : {};
};
const kindWord = computed(() => (activeRow.value?.presentation ? kindLabel(activeRow.value.presentation.kind) : null));
const rarityWord = computed(() => (activeRow.value?.presentation ? rarityLabel(activeRow.value.presentation.rarity) : null));

// The recipient's committed delta for the shown stock row (services v7
// `viewed.delta`); null for anything that is not equipment.
const recipientFacts = computed(() => (view.value === "buy" ? deltaFacts(activeRow.value?.viewed?.delta) : { kind: "none" }));
const isEquipment = computed(() => recipientFacts.value.kind !== "none");
const currentValues = computed(() =>
  recipientFacts.value.kind === "changes" ? currentTraitValues(props.character, memberId.value, recipientFacts.value.changes) : [],
);

const holdingsRows = computed(() => shopHoldings(props.itemHoldings, memberId.value, activeKey.value));
const otherRows = computed(() => (holdingsRows.value ? holdingsRows.value.filter((row) => row.member_id !== memberId.value) : null));
const holdingsPending = computed(() => activeKey.value !== null && props.pendingItemKey === activeKey.value);
const holdingsReason = computed(() => (holdingsPending.value ? null : panelReason(props.itemHoldings)));

// --------------------------------------------------------------- quantity

const action = computed(() => actionOf(activeRow.value, view.value));
const bounds = computed(() => quantityBounds(action.value));
const quantity = ref(1);
const draft = ref("1");
function resetQuantity() {
  quantity.value = bounds.value ? bounds.value.min : 1;
  draft.value = String(quantity.value);
}
watch([activeKey, view, memberId], resetQuantity, { immediate: true });
// A republish can lower the bound under the entry: keep the shown value in it.
watch(bounds, (next) => {
  if (!next) return;
  const clamped = clampQuantity(quantity.value, next);
  if (clamped !== quantity.value) {
    quantity.value = clamped;
    draft.value = String(clamped);
  }
});
function commitDraft() {
  if (!bounds.value) return;
  quantity.value = clampQuantity(String(draft.value ?? ""), bounds.value, quantity.value);
  draft.value = String(quantity.value);
}
function step(delta) {
  if (!bounds.value) return;
  const next = quantity.value + delta;
  if (next < bounds.value.min || next > bounds.value.max) return;
  quantity.value = next;
  draft.value = String(next);
}
// The value a trade would send: the typed entry only when it is a whole
// number inside the committed bounds (an out-of-bounds entry sends nothing).
const sendQuantity = computed(() => {
  if (!bounds.value) return null;
  const raw = String(draft.value ?? "").trim();
  const typed = raw === "" ? NaN : Number(raw);
  return Number.isInteger(typed) && typed >= bounds.value.min && typed <= bounds.value.max ? typed : null;
});
// The preview follows the entry and is hidden while it holds no valid count.
const preview = computed(() =>
  sendQuantity.value === null ? null : tradePreview(purse.value, unitPriceOf(activeRow.value, view.value), sendQuantity.value, view.value),
);

// --------------------------------------------------------------- trade

const canTrade = computed(
  () =>
    !!activeRow.value &&
    action.value?.enabled === true &&
    !!bounds.value &&
    sendQuantity.value !== null &&
    memberId.value !== null &&
    providerId.value !== null &&
    consistent.value &&
    !memberPending.value &&
    !props.tradePending,
);
const tradeLabel = computed(() => {
  if (view.value === "sell") return "出售";
  return memberName.value ? `買給${memberName.value}` : "購買";
});
const barActions = computed(() => {
  if (!activeRow.value) return [];
  const committed = action.value;
  return [
    {
      key: "trade",
      label: tradeLabel.value,
      tone: "primary",
      enabled: canTrade.value,
      busy: props.tradePending,
      reason: committed && committed.enabled !== true ? (committed.disabled_reason ?? null) : null,
    },
  ];
});

function onBarAction(key) {
  if (key !== "trade" || !canTrade.value) return;
  const qty = sendQuantity.value;
  if (qty === null) return;
  const row = activeRow.value;
  const field = view.value === "sell" ? "seller_id" : "recipient_id";
  emit("trade", {
    action_id: action.value.action_id,
    payload: {
      item_key: row.item_key,
      quantity: qty,
      [field]: memberId.value,
      npc_id: providerId.value,
    },
  });
}

// A stated refusal belongs to the trade it answered: a new member, tab or row
// drops it.
watch([activeKey, view, memberId], () => {
  if (props.tradeNotice) emit("clear-notice");
});

const listTitle = computed(() => {
  if (view.value === "sell") return memberName.value ? `${memberName.value}可出售的物品` : "可出售的物品";
  return memberName.value ? `為${memberName.value}挑選` : "貨架";
});
</script>

<template>
  <WindowFrame
    v-model="tab"
    :title="title"
    :subtitle="subtitle"
    seal="shop"
    drawer-key="shop"
    tabs-label="交易"
    :tabs="SHOP_WINDOW_TABS"
    @close="emit('close')"
  >
    <template #extras>
      <span v-if="purse !== null" class="shop-window__purse" data-testid="shop-window__purse">
        <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path :d="glyphPath('reward_copper')" stroke="currentColor" stroke-width="1.6" v-bind="glyphAttrs('reward_copper')" />
        </svg>{{ formatCopper(purse) }} 銅
      </span>
    </template>

    <div class="shop-window" data-testid="shop-window" :data-tab="tab" :data-open="shop ? String(shop.open) : undefined">
      <p
        v-if="servicesReason || !services"
        class="shop-window__reason"
        data-testid="shop-window__unavailable"
        :data-reason-code="servicesReason?.code || undefined"
      >{{ servicesReason?.message || "商店資訊目前無法顯示" }}</p>

      <p v-else-if="!shop" class="shop-window__reason" data-testid="shop-window__absent">這裡沒有營業中的商店。</p>

      <ListDetail v-else :list-label="tab === 'sell' ? '可出售的物品' : '貨架'" detail-label="商品詳情">
        <template v-if="members.length" #rail>
          <MemberRail
            :members="members"
            :selected="railSelected"
            :pending="pendingMemberId"
            :aria-label="tab === 'sell' ? '出售者' : '購買對象'"
            @select="onRailSelect"
          />
        </template>

        <template #list>
          <h4 class="shop-window__sech">
            <span data-testid="shop-window__list-title">{{ listTitle }}</span>
            <span class="shop-window__sech-count" data-testid="shop-window__count">{{ rows.length }}</span>
          </h4>
          <ShopRows
            v-if="rows.length"
            :rows="rows"
            :view="tab"
            :selected-key="activeKey"
            :pending-key="pendingItemKey"
            :facts-stale="memberPending"
            :label="tab === 'sell' ? '可出售的物品' : '貨架'"
            @select="onRowSelect"
          />
          <EmptyState
            v-else
            class="shop-window__empty"
            data-testid="shop-window__empty"
            :glyph="tab === 'sell' ? 'inventory' : 'shop'"
            :headline="tab === 'sell' ? '沒有可出售的物品' : '貨架上沒有商品'"
          />
        </template>

        <template #detail>
          <template v-if="activeRow">
            <div class="shop-window__hero" :data-rarity="activeRow.presentation?.rarity || 'unknown'">
              <span class="shop-window__hero-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none"><path :d="iconPath(activeRow)" stroke="currentColor" stroke-width="1.2" v-bind="iconAttrs(activeRow)" /></svg>
              </span>
              <div class="shop-window__hero-text">
                <span v-if="kindWord" class="shop-window__ribbon"><svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path :d="iconPath(activeRow)" stroke="currentColor" stroke-width="1.8" v-bind="iconAttrs(activeRow)" /></svg><span data-testid="shop-window__ribbon">{{ kindWord }}</span></span>
                <h3 class="shop-window__title" data-testid="shop-window__title">{{ activeRow.display_name }}</h3>
                <p class="shop-window__facts">
                  <span v-if="rarityWord" class="shop-window__rarity" :data-rarity="activeRow.presentation.rarity">{{ rarityWord }}</span>
                  <span v-if="tab === 'buy'" data-testid="shop-window__stock">{{ activeRow.stock === 0 ? "售完" : `庫存 ${activeRow.stock} / ${activeRow.max_stock}` }}</span>
                  <span v-else data-testid="shop-window__held">持有 {{ activeRow.held }}</span>
                </p>
              </div>
            </div>
            <p v-if="activeRow.presentation" class="shop-window__summary" data-testid="shop-window__summary">{{ activeRow.presentation.summary }}</p>

            <template v-if="tab === 'buy' && isEquipment">
              <h4 class="shop-window__label">裝備比較</h4>
              <div class="shop-window__vs" :class="{ 'is-stale': memberPending }" data-testid="shop-window__comparison">
                <div class="shop-window__box" data-testid="shop-window__current">
                  <span class="shop-window__box-head">目前</span>
                  <b class="shop-window__box-item">{{ memberName ?? "—" }}</b>
                  <template v-if="currentValues.length">
                    <span v-for="entry in currentValues" :key="entry.key" class="shop-window__stat">
                      <span>{{ entry.label }}</span><b>{{ entry.value ?? "—" }}</b>
                    </span>
                  </template>
                  <span v-else class="shop-window__stat shop-window__stat--none">—</span>
                </div>
                <svg class="shop-window__vs-arrow" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path :d="glyphPath('give')" stroke="currentColor" stroke-width="1.6" v-bind="glyphAttrs('give')" />
                </svg>
                <div class="shop-window__box is-new" data-testid="shop-window__after">
                  <span class="shop-window__box-head">換上後變化</span>
                  <b class="shop-window__box-item">{{ activeRow.display_name }}</b>
                  <span
                    v-if="recipientFacts.kind === 'blocked'"
                    class="shop-window__change shop-window__change--none"
                    :data-reason-code="recipientFacts.code || undefined"
                  >無法裝備</span>
                  <span v-else-if="recipientFacts.kind === 'same'" class="shop-window__change shop-window__change--none">±0</span>
                  <template v-else>
                    <span
                      v-for="change in recipientFacts.changes"
                      :key="change.key"
                      class="shop-window__change"
                      :class="`is-${change.tone}`"
                    >{{ change.text }}</span>
                  </template>
                </div>
              </div>
            </template>

            <h4 class="shop-window__label">{{ tab === "buy" && isEquipment ? "其他成員" : "隊伍持有量" }}</h4>
            <HoldingsStrip
              v-if="holdingsRows && (tab !== 'buy' || !isEquipment || otherRows.length)"
              variant="chips"
              :rows="tab === 'buy' && isEquipment ? otherRows : holdingsRows"
              :members="members"
              :selected-id="memberId"
              :aria-label="tab === 'buy' && isEquipment ? '其他成員' : '隊伍持有量'"
              @select="onRailSelect"
            />
            <p
              v-else-if="holdingsReason"
              class="shop-window__reason shop-window__reason--inline"
              data-testid="shop-window__holdings-unavailable"
              :data-reason-code="holdingsReason.code || undefined"
            >{{ holdingsReason.message }}</p>
            <div v-else-if="!holdingsRows" class="shop-window__holdings-wait" aria-busy="true" data-testid="shop-window__holdings-wait">
              <i v-for="member in members" :key="member.id"></i>
            </div>
          </template>
          <div v-else class="shop-window__idle" data-testid="shop-window__idle">
            <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path :d="glyphPath('shop')" stroke="currentColor" stroke-width="1.2" v-bind="glyphAttrs('shop')" />
            </svg>
            <p>{{ rows.length ? "選擇一件商品。" : "" }}</p>
          </div>
        </template>

        <template #actions>
          <ActionBar v-if="activeRow" :actions="barActions" :reason="tradeNotice" @action="onBarAction">
            <template #lead>
              <div v-if="bounds" class="shop-window__trade">
                <div class="shop-window__stepper" role="group" :aria-label="tab === 'sell' ? '出售數量' : '購買數量'" data-testid="shop-window__stepper">
                  <button
                    type="button"
                    aria-label="減少"
                    data-testid="shop-window__stepper-down"
                    :aria-disabled="quantity <= bounds.min ? 'true' : undefined"
                    @click="step(-1)"
                  >
                    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path :d="glyphPath('minus')" stroke="currentColor" stroke-width="1.8" /></svg>
                  </button>
                  <input
                    v-model="draft"
                    class="shop-window__qty"
                    type="number"
                    inputmode="numeric"
                    :min="bounds.min"
                    :max="bounds.max"
                    step="1"
                    :aria-label="tab === 'sell' ? '出售數量' : '購買數量'"
                    data-testid="shop-window__quantity"
                    @change="commitDraft"
                    @blur="commitDraft"
                    @keydown.enter.prevent="commitDraft"
                  />
                  <button
                    type="button"
                    aria-label="增加"
                    data-testid="shop-window__stepper-up"
                    :aria-disabled="quantity >= bounds.max ? 'true' : undefined"
                    @click="step(1)"
                  >
                    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path :d="glyphPath('plus')" stroke="currentColor" stroke-width="1.8" /></svg>
                  </button>
                  <span class="shop-window__stepper-max" data-testid="shop-window__quantity-max">/ {{ bounds.max }}</span>
                </div>
                <p v-if="preview" class="shop-window__sum" data-testid="shop-window__sum">
                  <span>{{ tab === "sell" ? "得到" : "花費" }} <b data-testid="shop-window__total">{{ formatCopper(preview.total) }}</b></span>
                  <span v-if="preview.remaining !== null" class="shop-window__remain" data-testid="shop-window__remaining">剩餘 {{ formatCopper(preview.remaining) }} 銅</span>
                </p>
              </div>
            </template>
          </ActionBar>
        </template>
      </ListDetail>
    </div>
  </WindowFrame>
</template>

<style scoped>
/* The approved prototype's shop window (docs/design/party-member-management/
   ShopPrototype.vue and prototype.css `.pm-sech`, `.pm-ribbon`, `.pm-hero`,
   `.pm-label`, `.pm-stepper`, `.pm-bar__sum`, `.sh-vs`, `.sh-box`). */
.shop-window {
  --shop-window-line: rgba(185, 154, 96, 0.28);
  --shop-window-line-soft: rgba(185, 154, 96, 0.14);
  --rarity-common: #6b665c;
  --rarity-uncommon: #8fb07c;
  --rarity-rare: #6f95e6;
  --rarity-epic: #b27fdb;
  --rarity-legendary: var(--gold-500);
  position: relative;
  display: flex;
  flex: 1;
  min-width: 0;
  min-height: 0;
  height: 100%;
}

.shop-window__purse {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-1);
}

.shop-window__purse svg {
  width: 1em;
  height: 1em;
}

.shop-window__reason {
  margin: var(--sp-4) var(--sp-5);
  color: var(--paper-500);
  font-size: var(--text-sm);
}

.shop-window__reason--inline {
  margin: 0;
}

.shop-window__sech {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  margin: 0 0 var(--sp-2);
  color: var(--gold-300);
  font: var(--text-base) var(--f-display);
  letter-spacing: 0.06em;
}

.shop-window__sech::after {
  content: "";
  flex: 1;
  height: calc(1px * var(--ui-scale));
  background: linear-gradient(90deg, var(--shop-window-line), transparent);
}

.shop-window__sech-count {
  order: 3;
  color: var(--paper-500);
  font: var(--text-xs) var(--f-num);
  letter-spacing: 0;
}

.shop-window__empty {
  margin-top: var(--sp-3);
}

/* ── detail ───────────────────────────────────────────────────── */
.shop-window__hero {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: var(--sp-4);
  align-items: center;
}

.shop-window__hero-icon {
  display: grid;
  place-items: center;
  box-sizing: border-box;
  width: calc(68px * var(--ui-scale));
  height: calc(68px * var(--ui-scale));
  color: var(--gold-300);
  background: radial-gradient(circle at 50% 38%, rgba(228, 200, 142, 0.16), rgba(0, 0, 0, 0.35) 72%);
  border: calc(1px * var(--ui-scale)) solid var(--hero-rarity, var(--rarity-common));
  border-radius: var(--radius-sm);
  box-shadow: inset 0 0 calc(18px * var(--ui-scale)) rgba(0, 0, 0, 0.5);
}

.shop-window__hero-icon svg {
  width: calc(38px * var(--ui-scale));
  height: calc(38px * var(--ui-scale));
}

.shop-window__hero[data-rarity="uncommon"] { --hero-rarity: var(--rarity-uncommon); }
.shop-window__hero[data-rarity="rare"] { --hero-rarity: var(--rarity-rare); }
.shop-window__hero[data-rarity="epic"] { --hero-rarity: var(--rarity-epic); }
.shop-window__hero[data-rarity="legendary"] { --hero-rarity: var(--rarity-legendary); }
.shop-window__hero[data-rarity="uncommon"] .shop-window__hero-icon { border-width: calc(2px * var(--ui-scale)); border-style: dotted; }
.shop-window__hero[data-rarity="rare"] .shop-window__hero-icon { border-width: calc(2px * var(--ui-scale)); border-style: dashed; }
.shop-window__hero[data-rarity="epic"] .shop-window__hero-icon { border-width: calc(3px * var(--ui-scale)); border-style: double; }
.shop-window__hero[data-rarity="legendary"] .shop-window__hero-icon { border-width: calc(3px * var(--ui-scale)); border-style: ridge; }

.shop-window__hero-text {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  min-width: 0;
}

.shop-window__ribbon {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-1);
  margin-bottom: var(--sp-2);
  padding: calc(3px * var(--ui-scale)) var(--sp-5) calc(3px * var(--ui-scale)) var(--sp-3);
  color: var(--paper-50);
  font-size: var(--text-xs);
  letter-spacing: 0.08em;
  background: var(--seal-600);
  clip-path: polygon(0 0, 100% 0, calc(100% - calc(10px * var(--ui-scale))) 50%, 100% 100%, 0 100%);
}

.shop-window__ribbon svg {
  width: 1.1em;
  height: 1.1em;
}

.shop-window__title {
  margin: 0;
  color: var(--paper-50);
  font: var(--text-3xl) var(--f-display);
  letter-spacing: 0.04em;
}

.shop-window__facts {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-1) var(--sp-3);
  margin: var(--sp-1) 0 0;
  color: var(--paper-400);
  font-size: var(--text-xs);
  font-variant-numeric: tabular-nums;
}

.shop-window__rarity[data-rarity="common"] { color: var(--paper-400); }
.shop-window__rarity[data-rarity="uncommon"] { color: var(--rarity-uncommon); }
.shop-window__rarity[data-rarity="rare"] { color: var(--rarity-rare); }
.shop-window__rarity[data-rarity="epic"] { color: var(--rarity-epic); }
.shop-window__rarity[data-rarity="legendary"] { color: var(--rarity-legendary); }

.shop-window__summary {
  max-width: 42em;
  margin: var(--sp-4) 0 0;
  padding-left: var(--sp-3);
  color: var(--paper-300);
  font: var(--text-md) / 1.8 var(--f-serif);
  border-left: calc(2px * var(--ui-scale)) solid var(--shop-window-line);
}

.shop-window__label {
  margin: var(--sp-5) 0 var(--sp-2);
  color: var(--gold-400);
  font: 400 var(--text-xs) var(--f-sans);
  letter-spacing: 0.14em;
}

/* The comparison: the recipient's committed current values beside the
   server's change lines (the new side carries the seal tint). */
.shop-window__vs {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  gap: var(--sp-3);
  align-items: stretch;
  max-width: calc(620px * var(--ui-scale));
  transition: opacity var(--motion-fast) ease;
}

.shop-window__vs.is-stale {
  opacity: 0.4;
}

.shop-window__vs-arrow {
  align-self: center;
  width: calc(18px * var(--ui-scale));
  height: calc(18px * var(--ui-scale));
  color: var(--gold-500);
}

.shop-window__box {
  display: flex;
  flex-direction: column;
  gap: calc(3px * var(--ui-scale));
  min-width: 0;
  padding: var(--sp-2) var(--sp-3);
  background: rgba(0, 0, 0, 0.18);
  border: calc(1px * var(--ui-scale)) solid var(--shop-window-line);
  border-radius: var(--radius-sm);
}

.shop-window__box.is-new {
  background: linear-gradient(160deg, rgba(207, 68, 68, 0.12), rgba(207, 68, 68, 0.03));
  border-color: var(--seal-700);
}

.shop-window__box-head {
  margin-bottom: calc(2px * var(--ui-scale));
  color: var(--paper-500);
  font-size: var(--text-xs);
  letter-spacing: 0.08em;
}

.shop-window__box-item {
  overflow: hidden;
  color: var(--paper-50);
  font: 500 var(--text-md) var(--f-serif);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.shop-window__stat {
  display: flex;
  justify-content: space-between;
  gap: var(--sp-3);
  color: var(--paper-400);
  font-size: var(--text-sm);
}

.shop-window__stat b {
  color: var(--paper-50);
  font: 500 var(--text-sm) var(--f-num);
  font-variant-numeric: tabular-nums lining-nums;
}

.shop-window__stat--none {
  color: var(--paper-700);
}

.shop-window__change {
  font: var(--text-sm) var(--f-num);
  font-variant-numeric: tabular-nums lining-nums;
}

.shop-window__change.is-up {
  color: var(--buff);
}

.shop-window__change.is-down {
  color: var(--debuff);
}

.shop-window__change--none {
  color: var(--paper-500);
}

.shop-window__holdings-wait {
  display: flex;
  gap: var(--sp-2);
}

.shop-window__holdings-wait i {
  width: calc(96px * var(--ui-scale));
  height: calc(28px * var(--ui-scale));
  background: rgba(0, 0, 0, 0.18);
  border: calc(1px * var(--ui-scale)) dashed var(--shop-window-line-soft);
  border-radius: var(--radius-pill);
}

.shop-window__idle {
  display: grid;
  place-items: center;
  align-content: center;
  gap: var(--sp-2);
  height: 100%;
  color: var(--paper-700);
  font-size: var(--text-sm);
}

.shop-window__idle svg {
  width: calc(48px * var(--ui-scale));
  height: calc(48px * var(--ui-scale));
}

.shop-window__idle p {
  margin: 0;
}

/* ── action bar ───────────────────────────────────────────────── */
.shop-window__trade {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--sp-2) var(--sp-4);
}

.shop-window__stepper {
  display: inline-flex;
  align-items: stretch;
  border: calc(1px * var(--ui-scale)) solid var(--ink-600);
  border-radius: var(--radius-sm);
}

.shop-window__stepper button {
  display: grid;
  place-items: center;
  padding: 0 var(--sp-2);
  color: var(--paper-300);
  background: transparent;
  border: 0;
  cursor: pointer;
  transition: color var(--motion-fast) ease;
}

.shop-window__stepper button svg {
  width: calc(14px * var(--ui-scale));
  height: calc(14px * var(--ui-scale));
}

.shop-window__stepper button:hover {
  color: var(--paper-50);
}

.shop-window__stepper button:focus-visible,
.shop-window__qty:focus-visible {
  outline: none;
  box-shadow: var(--focus);
}

.shop-window__stepper button[aria-disabled="true"] {
  color: var(--paper-700);
  cursor: not-allowed;
}

.shop-window__qty {
  box-sizing: border-box;
  width: calc(52px * var(--ui-scale));
  padding: var(--sp-1) var(--sp-2);
  color: var(--paper-50);
  font: var(--text-sm) var(--f-num);
  font-variant-numeric: tabular-nums;
  text-align: center;
  background: transparent;
  border: 0;
  border-right: calc(1px * var(--ui-scale)) solid var(--ink-600);
  border-left: calc(1px * var(--ui-scale)) solid var(--ink-600);
  appearance: textfield;
  -moz-appearance: textfield;
}

.shop-window__qty::-webkit-outer-spin-button,
.shop-window__qty::-webkit-inner-spin-button {
  margin: 0;
  -webkit-appearance: none;
}

.shop-window__stepper-max {
  display: flex;
  align-items: center;
  padding: 0 var(--sp-2);
  color: var(--paper-500);
  font: var(--text-xs) var(--f-num);
  border-left: calc(1px * var(--ui-scale)) solid var(--ink-600);
}

.shop-window__sum {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0 var(--sp-2);
  margin: 0;
  color: var(--paper-400);
  font-size: var(--text-xs);
  font-variant-numeric: tabular-nums;
}

.shop-window__sum b {
  color: var(--gold-300);
  font: 600 var(--text-md) var(--f-num);
}

.shop-window__remain::before {
  content: "‧";
  margin-right: var(--sp-2);
  color: var(--paper-700);
}

@media (prefers-reduced-motion: reduce) {
  .shop-window__vs,
  .shop-window__stepper button {
    transition: none;
  }
}
</style>
