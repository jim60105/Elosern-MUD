<script setup>
// HoldingsStrip (webclient-window-primitives, design §3.3/§6.2/§7): one cell
// per party member for the selected item, rendered from `item_holdings` v1
// rows verbatim. A cell shows the member's held count and, when the row
// supplies one, the server delta: each change on its own line with a ▲ or ▼
// shape prefix from the sign of the server amount (never colour alone), or
// 無法裝備 with the toggle rule's reason. A null delta shows nothing. The
// strip computes no count and no delta.
//
// A give control appears only on a cell whose row carries an enabled
// receive fact; a disabled receive shows its committed reason, and the
// viewed member's own cell is marked 持有者. In combat the strip shows counts
// only: no delta, no give control, no reason.
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
});

const emit = defineEmits(["give"]);

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

function give(row) {
  if (!canGive(row)) return;
  emit("give", row.member_id);
}
</script>

<template>
  <div class="holdings-strip" data-testid="holdings-strip" :data-combat="String(combat)" role="list" aria-label="隊伍持有量">
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
      <span class="holdings-strip__name">{{ nameOf(row) }}<span v-if="!combat && row.equipped" class="holdings-strip__tag">裝備中</span></span>
      <span class="holdings-strip__count" data-testid="holdings-strip__count" :aria-label="`持有 ${row.held}`">{{ row.held }}</span>
      <template v-if="!combat">
        <span
          v-if="row.delta && row.delta.equippable === false"
          class="holdings-strip__delta holdings-strip__delta--none"
          data-testid="holdings-strip__delta"
          :title="row.delta.reason"
        >無法裝備</span>
        <span
          v-else-if="row.delta && row.delta.changes.length"
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
        <span v-if="isOwner(row)" class="holdings-strip__foot holdings-strip__foot--owner">持有者</span>
        <button
          v-else-if="canGive(row)"
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
.holdings-strip {
  --holdings-line: rgba(185, 154, 96, 0.28);
  --holdings-line-soft: rgba(185, 154, 96, 0.14);
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--sp-2);
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
  min-width: 0;
  overflow: hidden;
  color: var(--paper-100);
  font-size: var(--text-sm);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.holdings-strip__tag {
  margin-left: var(--sp-1);
  padding: 0 var(--sp-1);
  color: var(--gold-400);
  font-size: var(--text-xs);
  border: calc(1px * var(--ui-scale)) solid var(--gold-600);
  border-radius: calc(2px * var(--ui-scale));
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
  color: var(--paper-700);
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
  .holdings-strip__give {
    transition: none;
  }
}
</style>
