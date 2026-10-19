// The party window's AppClient wiring (webclient-party-window-member-tab,
// design §6/§8): its openers, the one `party.view_member` dispatch per rail
// selection or bag item selection (webclient-party-bag-tab), and the pending
// entry or item while that request is in flight.
//
// Pending is correlated by request id with the store's in-flight dispatch,
// so a refused dispatch (null request id), a rejected result, or a finished
// request can never leave a sticky pending mark; the rail's selection itself
// always stays the committed `party.viewed_member_id`.
import { computed, ref } from "vue";
import { companionRows } from "../components/party-helpers.js";
import { rememberPartyWindowTab } from "../components/party-window-memory.js";

export function usePartyWindow(store, dispatchIntent, { panel }) {
  const pending = ref(null);

  const memoryScope = computed(() => `${store.view.generation}|${store.view.epoch}`);

  // The one in-flight selection request, or null once it has ended.
  const inFlight = computed(() => {
    const request = pending.value;
    if (!request) return null;
    return store.view.dispatch?.inFlight?.requestId === request.requestId ? request : null;
  });
  const pendingMemberId = computed(() => (inFlight.value && inFlight.value.itemKey === null ? inFlight.value.memberId : null));
  const pendingItemKey = computed(() => inFlight.value?.itemKey ?? null);

  // Every selection replaces the previous pending one: a rail click after an
  // item click leaves no item pending.
  function select(memberId, tab, itemKey) {
    const requestId = dispatchIntent("party.view_member", {
      member_id: memberId,
      tab,
      skill_key: null,
      item_key: itemKey,
    });
    pending.value = requestId === null ? null : { memberId, itemKey, requestId };
    return requestId;
  }

  function viewMember(memberId, tab) {
    if (!Number.isSafeInteger(memberId) || memberId <= 0) return null;
    return select(memberId, tab, null);
  }

  // A bag row selection for the viewed member (design §6.2): the server
  // stores the item and republishes `item_holdings` for it.
  function onViewItem(intent) {
    const memberId = intent?.memberId;
    const itemKey = intent?.itemKey;
    if (!Number.isSafeInteger(memberId) || memberId <= 0) return null;
    if (typeof itemKey !== "string" || itemKey === "") return null;
    return select(memberId, "bag", itemKey);
  }

  function onViewMember(intent) {
    return viewMember(intent?.memberId, intent?.tab);
  }

  // Every current opener opens the window on 成員; naming a companion (the
  // stage lineup's figure) also selects it unless it is already viewed. The
  // commander or an identity outside the committed party selects nothing.
  function openPartyWindow(memberId = null) {
    rememberPartyWindowTab(memoryScope.value, "member");
    store.openHudDrawer("party");
    if (memberId === null || memberId === undefined) return;
    const party = panel("party");
    const isCompanion = companionRows(party?.available === true ? party.slots : []).some(
      (row) => row.identity === memberId,
    );
    if (isCompanion && party.viewed_member_id !== memberId) {
      viewMember(memberId, "member");
    }
  }

  return { memoryScope, pendingMemberId, pendingItemKey, onViewMember, onViewItem, openPartyWindow };
}
