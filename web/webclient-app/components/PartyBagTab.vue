<script setup>
// PartyBagTab (webclient-party-bag-tab, design §6.2): the party window's 背包
// tab for the viewed member. The list column is the committed equipment doll
// (主手, 副手, 盔甲, 飾品 n/limit) above the `party_inventory` bag rows; a doll
// slot filters the rows to that slot. The detail column shows the selected
// row's ribbon, name and summary over the `HoldingsStrip` of the committed
// `item_holdings` answer, and the pinned action bar holds the give quantity
// stepper, 使用… (after a labelled confirmation) and 裝備 / 卸下 naming the
// replaced singleton.
//
// The item selection is server state: selecting a row emits `select-item`
// (the host sends one `party.view_member` with that `item_key`). The
// requested row shows only while that request is in flight; otherwise the
// committed `item_holdings.item_key` is the selection, so a refused or
// rejected request never leaves a sticky row. The holdings strip renders
// only an answer for exactly the shown item and viewed member, and nothing
// is counted or compared here.
//
// Every mutation names the viewed member: `party.transfer` as the giver,
// `inventory.use` / `inventory.toggle_equip` as the `actor_id`. Every
// enablement and reason is a committed descriptor. In combat the strip shows
// counts only, no give control or stepper is offered, the bar shows the
// committed give reason, and the combat-draft use is not offered here (its
// route lands with webclient-party-bag-retire); toggles keep their
// descriptors. The tab has no possession input.
import { computed, nextTick, ref, watch } from "vue";
import ActionBar from "./ActionBar.vue";
import HoldingsStrip from "./HoldingsStrip.vue";
import ListDetail from "./ListDetail.vue";
import { glyphAttrs, glyphPath } from "./dock-icons.js";
import { focusableElements } from "./focus-trap.js";
import { itemIconPath, kindLabel, rarityLabel, unknownItemPath } from "./item-icons.js";
import {
  bagRows,
  clampQuantity,
  dollCells,
  giveBound,
  holdingsFor,
  itemGlyph,
  rowByKey,
  slotLabel,
  toggleLabel,
} from "./party-bag-model.js";
import { panelReason } from "./party-window-model.js";

const props = defineProps({
  // The committed `party_inventory` v1 panel (the viewed member's bag).
  partyInventory: { type: Object, default: null },
  // The committed `item_holdings` v1 panel (the selected item's answer).
  itemHoldings: { type: Object, default: null },
  // The rail's plain members ({ id, name }) naming the holdings cells.
  members: { type: Array, default: () => [] },
  // The viewed member (`party.viewed_member_id`).
  memberId: { type: Number, default: null },
  // The window-local requested item key and the in-flight request's key.
  selectedItemKey: { type: String, default: null },
  pendingItemKey: { type: String, default: null },
  // The window-local give quantity.
  quantity: { type: Number, default: 1 },
  combat: { type: Boolean, default: false },
});

const emit = defineEmits(["select-item", "set-quantity", "action"]);

const root = ref(null);

// ---------------------------------------------------------------- panel

const inventoryReason = computed(() => panelReason(props.partyInventory));
// The bag is shown only for the member it describes: a transient
// disagreement renders no rows rather than another member's.
const inventory = computed(() => {
  const panel = props.partyInventory;
  if (!panel || panel.available !== true || panel.member_id !== props.memberId) return null;
  return panel;
});
const doll = computed(() => dollCells(inventory.value));

// ---------------------------------------------------------------- filter

const slotFilter = ref(null);
watch(
  () => props.memberId,
  () => {
    slotFilter.value = null;
  },
);
function toggleSlot(key) {
  slotFilter.value = slotFilter.value === key ? null : key;
}
const allRows = computed(() => bagRows(inventory.value));
const rows = computed(() => (slotFilter.value ? allRows.value.filter((row) => row.slot === slotFilter.value) : allRows.value));
const filterLabel = computed(() => slotLabel(slotFilter.value));

// ---------------------------------------------------------------- selection

const committedKey = computed(() => {
  const holdings = props.itemHoldings;
  if (!inventory.value || !holdings || holdings.available !== true || holdings.giver_id !== props.memberId) return null;
  return rowByKey(inventory.value, holdings.item_key) ? holdings.item_key : null;
});
const activeKey = computed(() => {
  const requested = props.selectedItemKey;
  if (requested !== null && requested === props.pendingItemKey && rowByKey(inventory.value, requested)) return requested;
  return committedKey.value;
});
const activeRow = computed(() => rowByKey(inventory.value, activeKey.value));
const isEquipment = computed(() => activeRow.value?.slot != null);

function select(key) {
  // The shown row (committed or in flight) is already selected.
  if (key === activeKey.value || key === props.pendingItemKey) return;
  emit("select-item", key);
}

// The listbox keeps one tab stop (the shown row, else the first) and moves
// focus with the arrow keys, Home and End; Enter, Space and click select.
const listbox = ref(null);
const focusKey = computed(() => (rows.value.some((row) => row.item_key === activeKey.value) ? activeKey.value : (rows.value[0]?.item_key ?? null)));
function onListKeydown(event) {
  const options = [...(listbox.value?.querySelectorAll('[role="option"]') ?? [])];
  const index = options.indexOf(document.activeElement);
  if (index === -1) return;
  let next = null;
  if (event.key === "ArrowDown") next = Math.min(index + 1, options.length - 1);
  else if (event.key === "ArrowUp") next = Math.max(index - 1, 0);
  else if (event.key === "Home") next = 0;
  else if (event.key === "End") next = options.length - 1;
  if (next === null) return;
  event.preventDefault();
  options[next].focus();
}

// ---------------------------------------------------------------- detail

const holdingsRows = computed(() => holdingsFor(props.itemHoldings, props.memberId, activeKey.value));
const holdingsReason = computed(() => panelReason(props.itemHoldings));

// The row's glyph: the bag's local glyph for its committed icon key, else
// the shared item icon (or the neutral unknown icon).
function iconPath(row) {
  const glyph = itemGlyph(row);
  if (glyph) return glyphPath(glyph);
  return (row?.presentation && itemIconPath(row.presentation.icon_key)) || unknownItemPath();
}
function iconAttrs(row) {
  const glyph = itemGlyph(row);
  return glyph ? glyphAttrs(glyph) : {};
}
const kindWord = computed(() => (activeRow.value?.presentation ? kindLabel(activeRow.value.presentation.kind) : null));
const rarityWord = computed(() => (activeRow.value?.presentation ? rarityLabel(activeRow.value.presentation.rarity) : null));
const ribbonText = computed(() => {
  const parts = [kindWord.value, slotLabel(activeRow.value?.slot)].filter(Boolean);
  return parts.length ? parts.join(" ‧ ") : null;
});

// ---------------------------------------------------------------- quantity

const bound = computed(() => giveBound(activeRow.value));
const shownQuantity = computed(() => clampQuantity(props.quantity, bound.value));
watch(
  () => [activeKey.value, props.memberId],
  () => emit("set-quantity", 1),
);
watch(shownQuantity, (value) => {
  if (value !== props.quantity) emit("set-quantity", value);
});
const stepperShown = computed(() => !props.combat && !!activeRow.value && !isEquipment.value && activeRow.value.give.enabled === true);
function step(delta) {
  const next = shownQuantity.value + delta;
  if (next < 1 || next > bound.value) return;
  emit("set-quantity", next);
}
const giveQuantity = computed(() => (isEquipment.value ? null : shownQuantity.value));

function onGive(receiverId) {
  const row = activeRow.value;
  if (props.combat || !row || row.give.enabled !== true || bound.value < 1) return;
  emit("action", {
    action_id: "party.transfer",
    payload: {
      giver_id: props.memberId,
      receiver_id: receiverId,
      item_key: row.item_key,
      quantity: isEquipment.value ? 1 : shownQuantity.value,
    },
  });
}

// ---------------------------------------------------------------- actions

const useOffered = computed(() => !props.combat && activeRow.value?.use?.route === "field_use");

const barActions = computed(() => {
  const row = activeRow.value;
  if (!row) return [];
  const list = [];
  if (useOffered.value) {
    list.push({
      key: "use",
      label: "使用…",
      tone: row.toggle ? "gold" : "primary",
      enabled: row.use.enabled === true,
      reason: row.use.enabled === true ? null : row.use.reason,
    });
  }
  if (row.toggle) {
    list.push({
      key: "toggle",
      label: toggleLabel(inventory.value, row),
      tone: "primary",
      enabled: row.toggle.enabled === true,
      reason: row.toggle.enabled === true ? null : row.toggle.reason,
    });
  }
  return list;
});
// The committed give reason (戰鬥中無法交換物品。 in combat, or why this row
// cannot be given) is state feedback in the bar's lead.
const barReason = computed(() => {
  const give = activeRow.value?.give;
  return give && give.enabled !== true ? give.reason : null;
});

function onBarAction(key) {
  const row = activeRow.value;
  if (!row || !Number.isSafeInteger(props.memberId)) return;
  if (key === "toggle" && row.toggle?.enabled === true) {
    emit("action", { action_id: "inventory.toggle_equip", payload: { item_key: row.item_key, actor_id: props.memberId } });
  } else if (key === "use" && useOffered.value && row.use.enabled === true) {
    openConfirm(row);
  }
}

// ---------------------------------------------------------------- confirm

// The labelled use confirmation (the old bag's pattern), drawn inside the
// window so the window's focus trap keeps holding: its keys never bubble to
// the window, the content behind it is inert, and a close attempt cancels it.
const confirming = ref(null);
const dialogEl = ref(null);

function openConfirm(row) {
  // The confirmation names who uses the item: the viewed member.
  const member = props.members.find((entry) => entry.id === props.memberId);
  confirming.value = { itemKey: row.item_key, displayName: row.display_name, memberName: member?.name ?? null };
  nextTick(() => dialogEl.value?.querySelector("[data-confirm-focus]")?.focus());
}

function closeConfirm(restoreFocus = true) {
  if (!confirming.value) return;
  confirming.value = null;
  if (!restoreFocus) return;
  nextTick(() => root.value?.querySelector('[data-testid="action-bar__btn--use"]')?.focus());
}

function confirmUse() {
  const held = confirming.value;
  const row = activeRow.value;
  closeConfirm();
  if (!held || !row || row.item_key !== held.itemKey || !useOffered.value || row.use.enabled !== true) return;
  emit("action", { action_id: "inventory.use", payload: { item_key: held.itemKey, actor_id: props.memberId } });
}

// The confirmation binds the member, the item and the descriptor it opened
// against: any change retires it without sending.
watch(
  () => [props.memberId, activeKey.value, useOffered.value, activeRow.value?.use?.enabled === true],
  () => closeConfirm(false),
);

function onDialogKeydown(event) {
  event.stopPropagation();
  if (event.key === "Escape") {
    event.preventDefault();
    closeConfirm();
    return;
  }
  if (event.key !== "Tab" || !dialogEl.value) return;
  const controls = focusableElements(dialogEl.value);
  if (controls.length === 0) return;
  event.preventDefault();
  const index = controls.indexOf(document.activeElement);
  const next = event.shiftKey ? (index <= 0 ? controls.length - 1 : index - 1) : (index + 1) % controls.length;
  controls[next].focus();
}

// The window's close guard: a close attempt while confirming cancels it.
function guardClose() {
  if (!confirming.value) return false;
  closeConfirm();
  return true;
}

defineExpose({ guardClose });
</script>

<template>
  <div ref="root" class="party-bag-tab" data-testid="party-bag-tab" :data-member="memberId ?? undefined">
    <ListDetail list-label="背包" detail-label="物品詳情" :inert="confirming ? true : undefined">
      <template #rail><slot name="rail" /></template>

      <template #list>
        <p
          v-if="inventoryReason"
          class="party-bag-tab__reason"
          data-testid="party-window__tab-unavailable"
          :data-reason-code="inventoryReason.code || undefined"
        >{{ inventoryReason.message }}</p>

        <template v-else-if="inventory">
          <h4 class="party-bag-tab__sech">裝備</h4>
          <div class="party-bag-tab__doll" role="group" aria-label="裝備欄位" data-testid="party-bag-tab__doll">
            <button
              v-for="cell in doll"
              :key="cell.key"
              type="button"
              class="party-bag-tab__slot"
              :class="{ 'is-empty': cell.keys.length === 0, 'is-selected': slotFilter === cell.key }"
              :data-rarity="cell.rarity || undefined"
              :data-testid="`party-bag-tab__slot--${cell.key}`"
              :aria-pressed="slotFilter === cell.key ? 'true' : 'false'"
              @click="toggleSlot(cell.key)"
            >
              <span class="party-bag-tab__slot-head">
                <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path :d="glyphPath(cell.glyph)" stroke="currentColor" stroke-width="1.6" v-bind="glyphAttrs(cell.glyph)" />
                </svg>{{ cell.label }}<span v-if="cell.count" class="party-bag-tab__slot-count" :data-testid="`party-bag-tab__slot-count--${cell.key}`">{{ cell.count }}</span>
              </span>
              <b class="party-bag-tab__slot-name" :data-testid="`party-bag-tab__slot-name--${cell.key}`">{{ cell.names.length ? cell.names.join("、") : "—" }}</b>
            </button>
          </div>

          <h4 class="party-bag-tab__sech">背包<span class="party-bag-tab__sech-count" data-testid="party-bag-tab__count">{{ filterLabel ? `${filterLabel} ‧ ` : "" }}{{ rows.length }} 種</span></h4>
          <div
            v-if="rows.length"
            ref="listbox"
            class="party-bag-tab__rows"
            role="listbox"
            aria-label="背包物品"
            data-testid="party-bag-tab__rows"
            @keydown="onListKeydown"
          >
            <button
              v-for="row in rows"
              :key="row.item_key"
              type="button"
              role="option"
              class="party-bag-tab__row"
              :class="{ 'is-selected': row.item_key === activeKey, 'is-pending': row.item_key === pendingItemKey }"
              :data-testid="`party-bag-tab__row--${row.item_key}`"
              :aria-selected="row.item_key === activeKey ? 'true' : 'false'"
              :aria-busy="row.item_key === pendingItemKey ? 'true' : undefined"
              :tabindex="row.item_key === focusKey ? 0 : -1"
              @click="select(row.item_key)"
            >
              <span class="party-bag-tab__icon" :data-rarity="row.presentation?.rarity || 'unknown'" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none"><path :d="iconPath(row)" stroke="currentColor" stroke-width="1.5" v-bind="iconAttrs(row)" /></svg>
              </span>
              <span class="party-bag-tab__row-name">{{ row.display_name }}<span v-if="row.equipped_count > 0" class="party-bag-tab__tag">裝備中</span></span>
              <span class="party-bag-tab__row-held" :data-testid="`party-bag-tab__held--${row.item_key}`">×{{ row.held }}</span>
            </button>
          </div>
          <p v-else class="party-bag-tab__empty" data-testid="party-bag-tab__empty">{{ filterLabel ? `沒有${filterLabel}的物品。` : "背包裡沒有物品。" }}</p>
        </template>
      </template>

      <template #detail>
        <template v-if="activeRow">
          <div class="party-bag-tab__hero" :data-rarity="activeRow.presentation?.rarity || 'unknown'">
            <span class="party-bag-tab__hero-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none"><path :d="iconPath(activeRow)" stroke="currentColor" stroke-width="1.2" v-bind="iconAttrs(activeRow)" /></svg>
            </span>
            <div class="party-bag-tab__hero-text">
              <span v-if="ribbonText" class="party-bag-tab__ribbon"><svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path :d="iconPath(activeRow)" stroke="currentColor" stroke-width="1.8" v-bind="iconAttrs(activeRow)" /></svg><span data-testid="party-bag-tab__ribbon">{{ ribbonText }}</span></span>
              <h3 class="party-bag-tab__title" data-testid="party-bag-tab__title">{{ activeRow.display_name }}</h3>
              <p class="party-bag-tab__facts">
                <span v-if="rarityWord" class="party-bag-tab__rarity" :data-rarity="activeRow.presentation.rarity" data-testid="party-bag-tab__rarity">{{ rarityWord }}</span>
                <span>持有 {{ activeRow.held }}</span>
                <span v-if="activeRow.equipped_count > 0">裝備中</span>
              </p>
            </div>
          </div>
          <p v-if="activeRow.presentation" class="party-bag-tab__summary" data-testid="party-bag-tab__summary">{{ activeRow.presentation.summary }}</p>

          <h4 class="party-bag-tab__label">隊伍持有量</h4>
          <HoldingsStrip
            v-if="holdingsRows"
            :rows="holdingsRows"
            :members="members"
            :giver-id="memberId"
            :combat="combat"
            :give-quantity="giveQuantity"
            @give="onGive"
          />
          <p
            v-else-if="holdingsReason"
            class="party-bag-tab__reason"
            data-testid="party-bag-tab__holdings-unavailable"
            :data-reason-code="holdingsReason.code || undefined"
          >{{ holdingsReason.message }}</p>
          <div v-else class="party-bag-tab__holdings-wait" aria-busy="true" data-testid="party-bag-tab__holdings-wait">
            <i v-for="member in members" :key="member.id"></i>
          </div>
        </template>
        <div v-else-if="inventory && rows.length" class="party-bag-tab__idle" data-testid="party-bag-tab__idle">
          <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path :d="glyphPath('inventory')" stroke="currentColor" stroke-width="1.2" v-bind="glyphAttrs('inventory')" />
          </svg>
          <p>選擇一件物品。</p>
        </div>
      </template>

      <template #actions>
        <ActionBar v-if="activeRow" :actions="barActions" :reason="barReason" @action="onBarAction">
          <template v-if="stepperShown" #default>
            <div class="party-bag-tab__stepper" role="group" aria-label="交給數量" data-testid="party-bag-tab__stepper">
              <button
                type="button"
                aria-label="減少"
                data-testid="party-bag-tab__stepper-down"
                :aria-disabled="shownQuantity <= 1 ? 'true' : undefined"
                @click="step(-1)"
              >
                <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path :d="glyphPath('minus')" stroke="currentColor" stroke-width="1.8" /></svg>
              </button>
              <output aria-live="polite" data-testid="party-bag-tab__quantity">{{ shownQuantity }}</output>
              <button
                type="button"
                aria-label="增加"
                data-testid="party-bag-tab__stepper-up"
                :aria-disabled="shownQuantity >= bound ? 'true' : undefined"
                @click="step(1)"
              >
                <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path :d="glyphPath('plus')" stroke="currentColor" stroke-width="1.8" /></svg>
              </button>
              <span class="party-bag-tab__stepper-max">/ {{ bound }}</span>
            </div>
          </template>
        </ActionBar>
      </template>
    </ListDetail>

    <div v-if="confirming" class="party-bag-tab__confirm" data-testid="party-bag-tab__confirm" @keydown="onDialogKeydown">
      <div class="party-bag-tab__confirm-scrim" data-testid="party-bag-tab__confirm-scrim" @click="closeConfirm()"></div>
      <div
        ref="dialogEl"
        class="party-bag-tab__dialog"
        role="dialog"
        aria-modal="true"
        :aria-label="`使用 ${confirming.displayName}`"
        data-testid="party-bag-tab__confirm-dialog"
      >
        <h3 class="party-bag-tab__dialog-title">使用物品</h3>
        <p class="party-bag-tab__dialog-text" data-testid="party-bag-tab__confirm-text">確定要<template v-if="confirming.memberName">讓<b>{{ confirming.memberName }}</b></template>使用「{{ confirming.displayName }}」？</p>
        <div class="party-bag-tab__dialog-actions">
          <button type="button" class="party-bag-tab__dialog-btn" data-testid="party-bag-tab__confirm-cancel" @click="closeConfirm()">取消</button>
          <button
            type="button"
            class="party-bag-tab__dialog-btn party-bag-tab__dialog-btn--primary"
            data-confirm-focus
            data-testid="party-bag-tab__confirm-ok"
            @click="confirmUse"
          >使用</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* The approved prototype's 背包 tab (docs/design/party-member-management/
   tabs/BagTab.vue and prototype.css `.pm-sech`, `.pm-row`, `.pm-icon`,
   `.pm-ribbon`, `.pm-hero`, `.pm-label`, `.pm-stepper`). Rarity is carried
   by the border style as well as its colour, and the detail spells it. */
.party-bag-tab {
  --party-bag-line: rgba(185, 154, 96, 0.28);
  --party-bag-line-soft: rgba(185, 154, 96, 0.14);
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

.party-bag-tab__reason {
  margin: 0;
  color: var(--paper-500);
  font-size: var(--text-sm);
}

.party-bag-tab__sech {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  margin: var(--sp-5) 0 var(--sp-2);
  color: var(--gold-300);
  font: var(--text-base) var(--f-display);
  letter-spacing: 0.06em;
}

.party-bag-tab__sech:first-child {
  margin-top: 0;
}

.party-bag-tab__sech::after {
  content: "";
  flex: 1;
  height: calc(1px * var(--ui-scale));
  background: linear-gradient(90deg, var(--party-bag-line), transparent);
}

.party-bag-tab__sech-count {
  order: 3;
  color: var(--paper-500);
  font: var(--text-xs) var(--f-num);
  letter-spacing: 0;
}

/* ── doll ─────────────────────────────────────────────────────── */
.party-bag-tab__doll {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--sp-2);
}

.party-bag-tab__slot {
  position: relative;
  display: grid;
  gap: calc(4px * var(--ui-scale));
  min-width: 0;
  padding: var(--sp-2) var(--sp-3);
  color: var(--paper-500);
  font: var(--text-xs) var(--f-sans);
  text-align: left;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.03), rgba(0, 0, 0, 0.22));
  border: calc(1px * var(--ui-scale)) solid var(--party-bag-line);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: border-color var(--motion-fast) ease, background-color var(--motion-fast) ease, color var(--motion-fast) ease;
}

/* A worn item above common rarity marks the cell's leading edge (the
   detail spells the rarity word). */
.party-bag-tab__slot::after {
  content: "";
  position: absolute;
  top: var(--sp-2);
  bottom: var(--sp-2);
  left: calc(-1px * var(--ui-scale));
  width: calc(2px * var(--ui-scale));
  background: var(--slot-rarity, transparent);
  border-radius: 0 calc(2px * var(--ui-scale)) calc(2px * var(--ui-scale)) 0;
}

.party-bag-tab__slot[data-rarity="uncommon"] { --slot-rarity: var(--rarity-uncommon); }
.party-bag-tab__slot[data-rarity="rare"] { --slot-rarity: var(--rarity-rare); }
.party-bag-tab__slot[data-rarity="epic"] { --slot-rarity: var(--rarity-epic); }
.party-bag-tab__slot[data-rarity="legendary"] { --slot-rarity: var(--rarity-legendary); }

.party-bag-tab__slot:hover {
  color: var(--paper-300);
  border-color: var(--gold-600);
}

.party-bag-tab__slot:focus-visible {
  outline: none;
  box-shadow: var(--focus);
}

.party-bag-tab__slot-head {
  display: flex;
  align-items: center;
  gap: var(--sp-1);
  letter-spacing: 0.08em;
}

.party-bag-tab__slot-head svg {
  flex: none;
  width: 1.2em;
  height: 1.2em;
  color: var(--gold-500);
}

.party-bag-tab__slot-count {
  margin-left: auto;
  color: var(--paper-400);
  font-family: var(--f-num);
  letter-spacing: 0;
}

.party-bag-tab__slot-name {
  overflow: hidden;
  color: var(--paper-100);
  font: 500 var(--text-sm) var(--f-serif);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.party-bag-tab__slot.is-empty {
  background: transparent;
  border-style: dashed;
}

.party-bag-tab__slot.is-empty .party-bag-tab__slot-name {
  color: var(--paper-700);
}

.party-bag-tab__slot.is-empty .party-bag-tab__slot-head svg {
  color: var(--paper-700);
}

.party-bag-tab__slot.is-selected {
  color: var(--paper-200);
  background: linear-gradient(180deg, rgba(207, 68, 68, 0.16), rgba(0, 0, 0, 0.2));
  border-color: var(--seal-500);
  box-shadow: 0 0 0 calc(1px * var(--ui-scale)) var(--seal-700);
}

/* ── rows ─────────────────────────────────────────────────────── */
.party-bag-tab__rows {
  display: flex;
  flex-direction: column;
}

.party-bag-tab__row {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: var(--sp-3);
  align-items: center;
  width: 100%;
  padding: var(--sp-2) var(--sp-3);
  color: var(--paper-100);
  font: var(--text-sm) var(--f-sans);
  text-align: left;
  background: transparent;
  border: calc(1px * var(--ui-scale)) solid transparent;
  border-bottom: calc(1px * var(--ui-scale)) dashed var(--party-bag-line-soft);
  border-radius: 0;
  cursor: pointer;
  transition: background-color var(--motion-fast) ease, border-color var(--motion-fast) ease;
}

.party-bag-tab__row:hover {
  background: rgba(255, 255, 255, 0.03);
}

.party-bag-tab__row:focus-visible {
  outline: none;
  box-shadow: var(--focus);
}

.party-bag-tab__row.is-selected {
  background: linear-gradient(90deg, rgba(207, 68, 68, 0.22), rgba(228, 200, 142, 0.06));
  border: calc(1px * var(--ui-scale)) solid var(--seal-700);
  border-radius: var(--radius-sm);
  box-shadow: inset calc(3px * var(--ui-scale)) 0 0 var(--seal-500);
}

.party-bag-tab__row.is-pending {
  opacity: 0.75;
  border-style: dashed;
}

.party-bag-tab__icon {
  display: grid;
  place-items: center;
  box-sizing: border-box;
  width: calc(34px * var(--ui-scale));
  height: calc(34px * var(--ui-scale));
  color: var(--gold-400);
  background: radial-gradient(circle at 50% 35%, rgba(185, 154, 96, 0.12), rgba(0, 0, 0, 0.3) 75%);
  border: calc(1px * var(--ui-scale)) solid var(--rarity-common);
  border-radius: var(--radius-sm);
}

.party-bag-tab__icon svg {
  width: calc(20px * var(--ui-scale));
  height: calc(20px * var(--ui-scale));
}

.party-bag-tab__icon[data-rarity="uncommon"] { border: calc(1px * var(--ui-scale)) dotted var(--rarity-uncommon); }
.party-bag-tab__icon[data-rarity="rare"] { border: calc(1px * var(--ui-scale)) dashed var(--rarity-rare); }
.party-bag-tab__icon[data-rarity="epic"] { border: calc(3px * var(--ui-scale)) double var(--rarity-epic); }
.party-bag-tab__icon[data-rarity="legendary"] { border: calc(2px * var(--ui-scale)) ridge var(--rarity-legendary); }

.party-bag-tab__row-name {
  overflow: hidden;
  font-family: var(--f-serif);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.party-bag-tab__tag {
  display: inline-block;
  margin-left: var(--sp-2);
  padding: 0 var(--sp-1);
  color: var(--gold-400);
  font: var(--text-xs) var(--f-sans);
  vertical-align: calc(1px * var(--ui-scale));
  border: calc(1px * var(--ui-scale)) solid var(--gold-600);
  border-radius: calc(2px * var(--ui-scale));
}

.party-bag-tab__row-held {
  color: var(--paper-300);
  font: var(--text-sm) var(--f-num);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.party-bag-tab__empty {
  margin: var(--sp-3) 0 0;
  color: var(--paper-500);
  font-size: var(--text-sm);
}

/* ── detail ───────────────────────────────────────────────────── */
.party-bag-tab__hero {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: var(--sp-4);
  align-items: center;
}

.party-bag-tab__hero-icon {
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

.party-bag-tab__hero-icon svg {
  width: calc(38px * var(--ui-scale));
  height: calc(38px * var(--ui-scale));
}

.party-bag-tab__hero[data-rarity="uncommon"] { --hero-rarity: var(--rarity-uncommon); }
.party-bag-tab__hero[data-rarity="rare"] { --hero-rarity: var(--rarity-rare); }
.party-bag-tab__hero[data-rarity="epic"] { --hero-rarity: var(--rarity-epic); }
.party-bag-tab__hero[data-rarity="legendary"] { --hero-rarity: var(--rarity-legendary); }

.party-bag-tab__hero-text {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  min-width: 0;
}

.party-bag-tab__ribbon {
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

.party-bag-tab__ribbon svg {
  width: 1.1em;
  height: 1.1em;
}

.party-bag-tab__title {
  margin: 0;
  color: var(--paper-50);
  font: var(--text-3xl) var(--f-display);
  letter-spacing: 0.04em;
}

.party-bag-tab__facts {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-1) var(--sp-3);
  margin: var(--sp-1) 0 0;
  color: var(--paper-400);
  font-size: var(--text-xs);
  font-variant-numeric: tabular-nums;
}

.party-bag-tab__rarity[data-rarity="common"] { color: var(--paper-400); }
.party-bag-tab__rarity[data-rarity="uncommon"] { color: var(--rarity-uncommon); }
.party-bag-tab__rarity[data-rarity="rare"] { color: var(--rarity-rare); }
.party-bag-tab__rarity[data-rarity="epic"] { color: var(--rarity-epic); }
.party-bag-tab__rarity[data-rarity="legendary"] { color: var(--rarity-legendary); }

.party-bag-tab__summary {
  max-width: 42em;
  margin: var(--sp-4) 0 0;
  padding-left: var(--sp-3);
  color: var(--paper-300);
  font: var(--text-md) / 1.8 var(--f-serif);
  border-left: calc(2px * var(--ui-scale)) solid var(--party-bag-line);
}

.party-bag-tab__label {
  margin: var(--sp-5) 0 var(--sp-2);
  color: var(--gold-400);
  font: 400 var(--text-xs) var(--f-sans);
  letter-spacing: 0.14em;
}

.party-bag-tab__holdings-wait {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--sp-2);
}

.party-bag-tab__holdings-wait i {
  height: calc(64px * var(--ui-scale));
  background: rgba(0, 0, 0, 0.18);
  border: calc(1px * var(--ui-scale)) dashed var(--party-bag-line-soft);
  border-radius: var(--radius-sm);
}

.party-bag-tab__idle {
  display: grid;
  place-items: center;
  align-content: center;
  gap: var(--sp-2);
  height: 100%;
  color: var(--paper-700);
  font-size: var(--text-sm);
}

.party-bag-tab__idle svg {
  width: calc(48px * var(--ui-scale));
  height: calc(48px * var(--ui-scale));
}

.party-bag-tab__idle p {
  margin: 0;
}

/* ── stepper ──────────────────────────────────────────────────── */
.party-bag-tab__stepper {
  display: inline-flex;
  align-items: stretch;
  align-self: stretch;
  border: calc(1px * var(--ui-scale)) solid var(--ink-600);
  border-radius: var(--radius-sm);
}

.party-bag-tab__stepper button {
  display: grid;
  place-items: center;
  padding: 0 var(--sp-2);
  color: var(--paper-300);
  background: transparent;
  border: 0;
  cursor: pointer;
  transition: color var(--motion-fast) ease;
}

.party-bag-tab__stepper button svg {
  width: calc(14px * var(--ui-scale));
  height: calc(14px * var(--ui-scale));
}

.party-bag-tab__stepper button:hover {
  color: var(--paper-50);
}

.party-bag-tab__stepper button:focus-visible {
  outline: none;
  box-shadow: var(--focus);
}

.party-bag-tab__stepper button[aria-disabled="true"] {
  color: var(--paper-700);
  cursor: not-allowed;
}

.party-bag-tab__stepper output {
  min-width: calc(40px * var(--ui-scale));
  padding: var(--sp-1) var(--sp-2);
  color: var(--paper-50);
  font: var(--text-sm) var(--f-num);
  font-variant-numeric: tabular-nums;
  text-align: center;
  border-right: calc(1px * var(--ui-scale)) solid var(--ink-600);
  border-left: calc(1px * var(--ui-scale)) solid var(--ink-600);
}

.party-bag-tab__stepper-max {
  display: flex;
  align-items: center;
  padding: 0 var(--sp-2);
  color: var(--paper-500);
  font: var(--text-xs) var(--f-num);
  border-left: calc(1px * var(--ui-scale)) solid var(--ink-600);
}

/* ── confirmation ─────────────────────────────────────────────── */
.party-bag-tab__confirm {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: grid;
  place-items: center;
}

.party-bag-tab__confirm-scrim {
  position: absolute;
  inset: 0;
  background: rgba(8, 9, 12, 0.62);
}

.party-bag-tab__dialog {
  position: relative;
  box-sizing: border-box;
  width: min(calc(380px * var(--ui-scale)), 90%);
  padding: var(--sp-5);
  background: linear-gradient(180deg, #1b1d23, #121418);
  border: calc(1px * var(--ui-scale)) solid rgba(185, 154, 96, 0.45);
  border-radius: var(--radius);
  box-shadow: 0 calc(18px * var(--ui-scale)) calc(48px * var(--ui-scale)) rgba(0, 0, 0, 0.6);
}

.party-bag-tab__dialog-title {
  margin: 0 0 var(--sp-2);
  color: var(--gold-300);
  font: var(--text-lg) var(--f-display);
  letter-spacing: 0.06em;
}

.party-bag-tab__dialog-text {
  margin: 0;
  color: var(--paper-200);
  font: var(--text-md) / 1.7 var(--f-serif);
}

.party-bag-tab__dialog-text b {
  color: var(--gold-300);
  font-weight: 500;
}

.party-bag-tab__dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--sp-3);
  margin-top: var(--sp-5);
}

.party-bag-tab__dialog-btn {
  padding: var(--sp-2) var(--sp-4);
  color: var(--paper-200);
  font: var(--text-sm) var(--f-sans);
  background: transparent;
  border: calc(1px * var(--ui-scale)) solid var(--ink-600);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: border-color var(--motion-fast) ease, background-color var(--motion-fast) ease;
}

.party-bag-tab__dialog-btn:hover {
  border-color: var(--gold-500);
}

.party-bag-tab__dialog-btn:focus-visible {
  outline: none;
  box-shadow: var(--focus);
}

.party-bag-tab__dialog-btn--primary {
  color: var(--paper-50);
  background: var(--seal-500);
  border-color: var(--seal-500);
}

.party-bag-tab__dialog-btn--primary:hover {
  background: var(--seal-400);
  border-color: var(--seal-400);
}

@media (prefers-reduced-motion: reduce) {
  .party-bag-tab__slot,
  .party-bag-tab__row,
  .party-bag-tab__stepper button,
  .party-bag-tab__dialog-btn {
    transition: none;
  }
}
</style>
