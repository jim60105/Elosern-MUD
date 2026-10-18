<script setup>
// PartyWindow (webclient-party-window-member-tab, design §3.2/§6): the one
// party window, mounted under the `party` drawer key. It composes the shared
// WindowFrame (seal, 隊伍, the first-level tabs 成員/背包/狀態/技能/系譜, the
// party purse) with a MemberRail of the committed `party` v3 rows (the
// commander first) plus a 空位 entry while the general quota has room.
//
// Selection is server truth: the rail's selected entry is
// `party.viewed_member_id`. Activating another entry emits `view-member`
// ({memberId, tab}) — AppClient dispatches one `party.view_member` — and the
// rail only marks that entry pending until the server's update arrives; it
// never switches optimistically. When the server's viewed member changes
// (a selection adopted, or a departed member's fallback to the commander)
// the window resets its local item selection and quantity. 空位 is the one
// local selection: it has no member id, so selecting it sends nothing and
// opens the 成員 tab's invite view.
//
// The window remembers its last tab for the session (party-window-memory.js).
// It has no possession input: the rail, the tabs and their content render
// identically whether or not the player is possessing, and no "you" marker
// exists. The 背包/狀態/技能/系譜 tabs land in the next changes; until then
// each shows only its backing panel's committed unavailable reason, or
// whatever the host passes through the tab's scoped slot, and invents nothing.
import { computed, ref, watch } from "vue";
import ListDetail from "./ListDetail.vue";
import MemberRail, { EMPTY_SLOT } from "./MemberRail.vue";
import PartyMemberTab from "./PartyMemberTab.vue";
import WindowFrame from "./WindowFrame.vue";
import { glyphAttrs, glyphPath } from "./dock-icons.js";
import { usePartyWindowMemory, PARTY_WINDOW_DEFAULT_TAB } from "./party-window-memory.js";
import {
  PARTY_WINDOW_TABS,
  PARTY_WINDOW_TAB_KEYS,
  TAB_BACKING_PANEL,
  formatPurse,
  hasFreeSlot,
  panelReason,
  railMembers,
  rowById,
  viewedMemberId,
} from "./party-window-model.js";

const props = defineProps({
  // The committed `party` v3 panel.
  party: { type: Object, default: null },
  // The committed `party_member` v1 panel (the 成員 tab).
  partyMember: { type: Object, default: null },
  // The committed `party_inventory` v1 panel (the purse; the 背包 tab).
  partyInventory: { type: Object, default: null },
  // The committed `character` panel (the 狀態 and 技能 tabs).
  character: { type: Object, default: null },
  // The committed `lineage` panel (the 系譜 tab).
  lineage: { type: Object, default: null },
  // The committed `art` panel (the 成員 nameplate).
  artPanel: { type: Object, default: null },
  // The committed `exploration.interact` targets (the 空位 invite).
  interactTargets: { type: Array, default: () => [] },
  // The member whose `party.view_member` is in flight, or null.
  pendingMemberId: { type: Number, default: null },
  // `<generation>|<epoch>`: the session memory's scope.
  memoryScope: { type: String, default: "" },
});

const emit = defineEmits(["close", "view-member", "action", "open-npc-persona", "persona-edit"]);

const memory = usePartyWindowMemory(props.memoryScope);
// The memory is one module-level reactive object: re-syncing the scope
// resets it in place, so `memory` above stays the live reference.
watch(
  () => props.memoryScope,
  (scope) => usePartyWindowMemory(scope),
);

const tab = computed({
  get: () => (PARTY_WINDOW_TAB_KEYS.has(memory.tab) ? memory.tab : PARTY_WINDOW_DEFAULT_TAB),
  set: (key) => {
    if (PARTY_WINDOW_TAB_KEYS.has(key)) memory.tab = key;
  },
});

const partyAvailable = computed(() => props.party?.available === true);
const partyReason = computed(() => panelReason(props.party));
const members = computed(() => railMembers(props.party));
const viewedId = computed(() => viewedMemberId(props.party));
const freeSlot = computed(() => hasFreeSlot(props.party));

// --------------------------------------------------------------- selection

const emptySelected = ref(false);
watch(freeSlot, (free) => {
  if (!free) emptySelected.value = false;
});
watch(tab, (key) => {
  if (key !== "member") emptySelected.value = false;
});

const railSelected = computed(() => (emptySelected.value && freeSlot.value ? EMPTY_SLOT : viewedId.value));
const selectedRow = computed(() => (railSelected.value === EMPTY_SLOT ? null : rowById(props.party, viewedId.value)));

function onSelect(key) {
  if (key === EMPTY_SLOT) {
    emptySelected.value = true;
    tab.value = "member";
    return;
  }
  if (key === viewedId.value) {
    emptySelected.value = false;
    return;
  }
  // 空位 stays selected until the server adopts the requested member (the
  // watch below), so the rail never flips back to the previous member.
  emit("view-member", { memberId: key, tab: tab.value });
}
watch(viewedId, () => {
  emptySelected.value = false;
});

// The local item selection and quantity (the 背包 tab's state, owned here so
// a changed viewed member resets them in one place).
const selectedItemKey = ref(null);
const quantity = ref(1);
watch(viewedId, () => {
  selectedItemKey.value = null;
  quantity.value = 1;
});
function setItem(key) {
  selectedItemKey.value = key ?? null;
}
function setQuantity(value) {
  quantity.value = Number.isSafeInteger(value) && value > 0 ? value : 1;
}

// --------------------------------------------------------------- header

const purse = computed(() => {
  const panel = props.partyInventory;
  if (!panel || panel.available !== true) return null;
  return Number.isSafeInteger(panel.purse) && panel.purse >= 0 ? panel.purse : null;
});
const quota = computed(() => (partyAvailable.value ? props.party.general_quota : null));

// --------------------------------------------------------------- tabs

const backingPanels = computed(() => ({
  party_inventory: props.partyInventory,
  character: props.character,
  lineage: props.lineage,
}));
const tabReason = computed(() => {
  const name = TAB_BACKING_PANEL[tab.value];
  return name ? panelReason(backingPanels.value[name]) : null;
});

// The 成員 tab's armed leave and unsaved persona draft: a close attempt
// (Escape, ✕, the scrim) first cancels the confirmation or warns about the
// draft, sends nothing and keeps the window; the next attempt closes.
const memberTab = ref(null);
function closeGuard() {
  return !memberTab.value?.guardClose?.();
}
</script>

<template>
  <WindowFrame
    v-model="tab"
    title="隊伍"
    seal="party"
    drawer-key="party"
    tabs-label="隊伍分頁"
    :tabs="PARTY_WINDOW_TABS"
    :close-guard="closeGuard"
    @close="emit('close')"
  >
    <template #extras>
      <span
        v-if="tab === 'member' && quota"
        class="party-window__quota"
        data-testid="party-window__quota"
      >同伴 {{ quota.used }} / {{ quota.limit }}</span>
      <span v-if="purse !== null" class="party-window__purse" data-testid="party-window__purse">
        <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path :d="glyphPath('reward_copper')" stroke="currentColor" stroke-width="1.6" v-bind="glyphAttrs('reward_copper')" />
        </svg>{{ formatPurse(purse) }} 銅
      </span>
    </template>

    <div class="party-window" data-testid="party-window" :data-tab="tab">
      <p
        v-if="!partyAvailable"
        class="party-window__reason"
        data-testid="party-window__unavailable"
        :data-reason-code="partyReason?.code || undefined"
      >{{ partyReason?.message || "隊伍資訊目前無法顯示" }}</p>

      <PartyMemberTab
        v-else-if="tab === 'member'"
        ref="memberTab"
        :member="selectedRow"
        :party-member="partyMember"
        :art-panel="artPanel"
        :interact-targets="interactTargets"
        @action="(intent) => emit('action', intent)"
        @open-npc-persona="(id) => emit('open-npc-persona', id)"
        @persona-edit="(intent) => emit('persona-edit', intent)"
      >
        <template #rail>
          <MemberRail :members="members" :selected="railSelected" :pending="pendingMemberId" :empty-slot="freeSlot" @select="onSelect" />
        </template>
      </PartyMemberTab>

      <ListDetail v-else :list-label="PARTY_WINDOW_TABS.find((t) => t.key === tab)?.label">
        <template #rail>
          <MemberRail :members="members" :selected="railSelected" :pending="pendingMemberId" :empty-slot="freeSlot" @select="onSelect" />
        </template>
        <template #list>
          <p
            v-if="tabReason"
            class="party-window__reason"
            data-testid="party-window__tab-unavailable"
            :data-reason-code="tabReason.code || undefined"
          >{{ tabReason.message }}</p>
          <slot
            v-else
            :name="tab"
            :member-id="viewedId"
            :selected-item-key="selectedItemKey"
            :quantity="quantity"
            :set-item="setItem"
            :set-quantity="setQuantity"
          />
        </template>
      </ListDetail>
    </div>
  </WindowFrame>
</template>

<style scoped>
.party-window {
  display: flex;
  flex: 1;
  min-width: 0;
  min-height: 0;
  height: 100%;
}

.party-window__reason {
  margin: var(--sp-4) var(--sp-5);
  color: var(--paper-500);
  font-size: var(--text-sm);
}

.party-window__quota {
  color: var(--paper-400);
}

.party-window__purse {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-1);
}

.party-window__purse svg {
  width: 1em;
  height: 1em;
}
</style>
