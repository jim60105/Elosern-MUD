<script setup>
// HoldingsStrip (webclient-window-primitives, design §3.3/§6.2/§7): one cell
// per party member for the selected item, rendered from `item_holdings` v1
// rows verbatim. A cell shows the member's held count and, when the row
// supplies one, the server delta: each change on its own line with a ▲ or ▼
// shape prefix from the sign of the server amount (never colour alone), or
// 無法裝備 (the toggle rule's stable reason code rides on `data-reason-code`
// as data, never as text). A null delta shows nothing. The strip computes no
// count and no delta.
//
// `variant="chips"` (webclient-shop-window, design §7) draws the same rows as
// small member chips — the initial, the server delta (or 無法裝備, or ±0) or
// else the held count — each a button that emits `select(memberId)`. Chips
// carry no give control and no receive reason.
//
// A give control appears only on a cell whose row carries an enabled
// receive fact; a disabled receive shows its committed reason, and the
// viewed member's own cell is marked 持有者 (in combat too, so the owner is
// never told by colour alone). In combat the strip shows counts only: no
// delta, no give control, no reason; every cell is one line, so the owner's
// 持有者 rides beside the name and the cells flow into as many columns as
// fit (webclient-party-bag-retire).
import { computed } from "vue";
import { glyphAttrs, glyphPath } from "./dock-icons.js";

const props = defineProps({
  // item_holdings rows: [{ member_id, held, equipped, delta, receive }].
  rows: { type: Array, default: () => [] },
  // Names for the member ids: [{ id, name, portrait? }].
  members: { type: Array, default: () => [] },
  // The viewed member (the panel's giver_id).
  giverId: { type: Number, default: null },
  combat: { type: Boolean, default: false },
  // How many a give moves, appended to the control (×n); null omits it.
  giveQuantity: { type: Number, default: null },
  // "cells" (the bag's strip) or "chips" (the shop's compact member chips).
  variant: { type: String, default: "cells", validator: (value) => ["cells", "chips"].includes(value) },
  // The chips variant's selected member (marked, never re-emitted).
  selectedId: { type: Number, default: null },
  ariaLabel: { type: String, default: "隊伍持有量" },
});

const emit = defineEmits(["give", "select"]);

const memberById = computed(() => new Map(props.members.map((member) => [member.id, member])));

const nameOf = (row) => memberById.value.get(row.member_id)?.name ?? `#${row.member_id}`;
const portraitOf = (row) => memberById.value.get(row.member_id)?.portrait ?? null;
const initialOf = (row) => Array.from(nameOf(row))[0] ?? "";
const isOwner = (row) => row.member_id === props.giverId;

const canGive = (row) => !props.combat && !isOwner(row) && row.receive?.enabled === true;

// The server's signed amount, written with its shape prefix and a true
// minus sign; the label is the server's.
function changeText(change) {
  const shape = change.amount < 0 ? "▼" : "▲";
  const sign = change.amount < 0 ? "−" : "+";
  return `${shape} ${change.label} ${sign}${Math.abs(change.amount)}`;
}

// One chip's fact: the server delta lines, 無法裝備, ±0, or the held count.
function chipFact(row) {
  const delta = row.delta;
  if (delta && delta.equippable === false) return { kind: "blocked", code: delta.reason ?? null };
  if (delta && Array.isArray(delta.changes)) {
    if (delta.changes.length === 0) return { kind: "same" };
    return { kind: "changes", changes: delta.changes };
  }
  return { kind: "held" };
}

function selectChip(row) {
  if (row.member_id === props.selectedId) return;
  emit("select", row.member_id);
}

function give(row) {
  if (!canGive(row)) return;
  emit("give", row.member_id);
}
</script>

<template>
  <div v-if="variant === 'chips'" class="holdings-chips" data-testid="holdings-strip" data-variant="chips" role="group" :aria-label="ariaLabel">
    <button
      v-for="row in rows"
      :key="row.member_id"
      type="button"
      class="holdings-chips__chip"
      :class="{ 'is-selected': row.member_id === selectedId }"
      :data-testid="`holdings-strip__chip--${row.member_id}`"
      :aria-pressed="row.member_id === selectedId ? 'true' : 'false'"
      @click="selectChip(row)"
    >
      <span class="holdings-strip__avatar holdings-chips__avatar" aria-hidden="true">
        <img v-if="portraitOf(row)" :src="portraitOf(row)" alt="" />
        <template v-else>{{ initialOf(row) }}</template>
      </span>
      <span class="holdings-chips__name">{{ nameOf(row) }}</span>
      <span
        v-if="chipFact(row).kind === 'blocked'"
        class="holdings-chips__fact holdings-strip__delta--none"
        :data-reason-code="chipFact(row).code || undefined"
        data-testid="holdings-strip__delta"
      >無法裝備</span>
      <span v-else-if="chipFact(row).kind === 'same'" class="holdings-chips__fact holdings-strip__delta--none" data-testid="holdings-strip__delta">±0</span>
      <span v-else-if="chipFact(row).kind === 'changes'" class="holdings-chips__fact" data-testid="holdings-strip__delta">
        <span
          v-for="change in chipFact(row).changes"
          :key="change.key"
          class="holdings-strip__change"
          :class="change.amount < 0 ? 'is-down' : 'is-up'"
        >{{ changeText(change) }}</span>
      </span>
      <span v-else class="holdings-chips__fact holdings-chips__held"><span class="holdings-strip__sr">持有 </span><span data-testid="holdings-strip__count">{{ row.held }}</span></span>
    </button>
  </div>
  <div v-else class="holdings-strip" data-testid="holdings-strip" :data-combat="String(combat)" role="list" aria-label="隊伍持有量">
    <div
      v-for="row in rows"
      :key="row.member_id"
      class="holdings-strip__cell"
      :class="{ 'is-owner': isOwner(row) }"
      role="listitem"
      :data-testid="`holdings-strip__cell--${row.member_id}`"
    >
      <span class="holdings-strip__avatar" aria-hidden="true">
        <img v-if="portraitOf(row)" :src="portraitOf(row)" alt="" />
        <template v-else>{{ initialOf(row) }}</template>
      </span>
      <span class="holdings-strip__name"><span class="holdings-strip__label">{{ nameOf(row) }}</span><span v-if="!combat && row.equipped" class="holdings-strip__tag">裝備中</span><span
        v-if="combat && isOwner(row)"
        class="holdings-strip__tag holdings-strip__tag--owner"
      >持有者</span></span>
      <span class="holdings-strip__count"><span class="holdings-strip__sr">持有 </span><span data-testid="holdings-strip__count">{{ row.held }}</span></span>
      <template v-if="!combat">
        <span
          v-if="row.delta && row.delta.equippable === false"
          class="holdings-strip__delta holdings-strip__delta--none"
          data-testid="holdings-strip__delta"
          :data-reason-code="row.delta.reason || undefined"
        >無法裝備</span>
        <span
          v-else-if="row.delta?.changes?.length"
          class="holdings-strip__delta"
          data-testid="holdings-strip__delta"
        >
          <span
            v-for="change in row.delta.changes"
            :key="change.key"
            class="holdings-strip__change"
            :class="change.amount < 0 ? 'is-down' : 'is-up'"
          >{{ changeText(change) }}</span>
        </span>
      </template>
      <span v-if="!combat && isOwner(row)" class="holdings-strip__foot holdings-strip__foot--owner">持有者</span>
      <template v-if="!combat && !isOwner(row)">
        <button
          v-if="canGive(row)"
          type="button"
          class="holdings-strip__give"
          :data-testid="`holdings-strip__give--${row.member_id}`"
          @click="give(row)"
        >
          <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path :d="glyphPath('give')" stroke="currentColor" stroke-width="1.6" v-bind="glyphAttrs('give')" />
          </svg>交給{{ nameOf(row) }}<template v-if="giveQuantity != null"> ×{{ giveQuantity }}</template>
        </button>
        <span
          v-else-if="row.receive?.reason"
          class="holdings-strip__foot"
          data-testid="holdings-strip__reason"
        >{{ row.receive.reason }}</span>
      </template>
    </div>
  </div>
</template>

<style scoped>
/* The approved prototype's `.pm-hold` (docs/design/party-member-management/
   prototype.css). Signs carry a shape prefix, so the buff/debuff colours are
   never the only cue. */
.holdings-strip,
.holdings-chips {
  --holdings-line: rgba(185, 154, 96, 0.28);
  --holdings-line-soft: rgba(185, 154, 96, 0.14);
}

.holdings-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--sp-2);
}

/* Counts only: compact one-line cells, as many per row as fit. */
.holdings-strip[data-combat="true"] {
  grid-template-columns: repeat(auto-fit, minmax(calc(150px * var(--ui-scale)), 1fr));
}

.holdings-strip__cell {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: var(--sp-1) var(--sp-2);
  align-items: center;
  box-sizing: border-box;
  padding: var(--sp-2) var(--sp-3);
  font-size: var(--text-xs);
  background: rgba(0, 0, 0, 0.18);
  border: calc(1px * var(--ui-scale)) solid var(--holdings-line);
  border-radius: var(--radius-sm);
}

.holdings-strip__cell.is-owner {
  background: rgba(207, 68, 68, 0.08);
  border-color: var(--seal-700);
}

.holdings-strip__avatar {
  display: grid;
  place-items: center;
  flex: none;
  box-sizing: border-box;
  width: calc(28px * var(--ui-scale));
  height: calc(28px * var(--ui-scale));
  overflow: hidden;
  color: var(--paper-100);
  font: var(--text-xs) / 1 var(--f-serif);
  background: radial-gradient(circle at 50% 30%, #3a332a, #16181c);
  border: calc(1px * var(--ui-scale)) solid var(--gold-600);
  border-radius: 50%;
}

.holdings-strip__avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center top;
}

.holdings-strip__name {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: calc(2px * var(--ui-scale)) 0;
  min-width: 0;
  color: var(--paper-100);
  font-size: var(--text-sm);
  white-space: nowrap;
}

/* The name yields first; a state tag beside it is never clipped. */
.holdings-strip__label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}

.holdings-strip__tag {
  flex: none;
  margin-left: var(--sp-1);
  padding: 0 var(--sp-1);
  color: var(--gold-400);
  font-size: var(--text-xs);
  border: calc(1px * var(--ui-scale)) solid var(--gold-600);
  border-radius: calc(2px * var(--ui-scale));
}

.holdings-strip__tag--owner {
  color: var(--seal-400);
  border-color: var(--seal-700);
}

.holdings-strip__count {
  color: var(--paper-50);
  font: 600 var(--text-lg) var(--f-num);
  font-variant-numeric: tabular-nums;
}

.holdings-strip__delta {
  grid-column: 1 / -1;
  display: grid;
  gap: calc(2px * var(--ui-scale));
}

.holdings-strip__delta--none {
  color: var(--paper-500);
}

/* ── chips (the shop's other members) ─────────────────────────── */
.holdings-chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-2);
}

.holdings-chips__chip {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-2);
  min-width: 0;
  padding: calc(3px * var(--ui-scale)) var(--sp-3) calc(3px * var(--ui-scale)) calc(3px * var(--ui-scale));
  color: var(--paper-200);
  font: var(--text-xs) var(--f-sans);
  background: rgba(0, 0, 0, 0.2);
  border: calc(1px * var(--ui-scale)) solid var(--holdings-line);
  border-radius: var(--radius-pill);
  cursor: pointer;
  transition: border-color var(--motion-fast) ease, background-color var(--motion-fast) ease;
}

.holdings-chips__chip:hover {
  border-color: var(--gold-500);
  background: rgba(185, 154, 96, 0.08);
}

.holdings-chips__chip:focus-visible {
  outline: none;
  box-shadow: var(--focus);
}

.holdings-chips__chip.is-selected {
  border-color: var(--seal-500);
  background: rgba(207, 68, 68, 0.1);
  cursor: default;
}

.holdings-chips__avatar {
  width: calc(22px * var(--ui-scale));
  height: calc(22px * var(--ui-scale));
}

.holdings-chips__name {
  color: var(--paper-300);
}

.holdings-chips__fact {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 0 var(--sp-2);
  font-family: var(--f-num);
  font-variant-numeric: tabular-nums lining-nums;
}

.holdings-chips__held {
  color: var(--paper-50);
}

.holdings-strip__sr {
  position: absolute;
  width: calc(1px * var(--ui-scale));
  height: calc(1px * var(--ui-scale));
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}

.holdings-strip__change.is-up {
  color: var(--buff);
}

.holdings-strip__change.is-down {
  color: var(--debuff);
}

.holdings-strip__give,
.holdings-strip__foot {
  grid-column: 1 / -1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--sp-1);
  padding-top: var(--sp-1);
  font-size: var(--text-xs);
  text-align: center;
  border-top: calc(1px * var(--ui-scale)) dashed var(--holdings-line-soft);
}

.holdings-strip__give {
  color: var(--gold-300);
  font-family: inherit;
  background: transparent;
  border-right: 0;
  border-bottom: 0;
  border-left: 0;
  cursor: pointer;
  transition: color var(--motion-fast) ease;
}

.holdings-strip__give svg {
  width: 1em;
  height: 1em;
}

.holdings-strip__give:hover {
  color: var(--paper-50);
}

.holdings-strip__give:focus-visible {
  outline: none;
  box-shadow: var(--focus);
}

.holdings-strip__foot {
  color: var(--paper-500);
}

.holdings-strip__foot--owner {
  color: var(--paper-700);
}

@media (prefers-reduced-motion: reduce) {
  .holdings-strip__give,
  .holdings-chips__chip {
    transition: none;
  }
}
</style>
