// The party window's AppClient wiring (webclient-party-window-member-tab,
// design §6/§8): its openers, the one `party.view_member` dispatch per rail
// selection or bag item selection (webclient-party-bag-tab), and the pending
// entry or item while that request is in flight. The shop window
// (webclient-shop-window) shares the same viewed-member selection: its rail
// and row selections send the same `party.view_member` with tab `shop`, and
// a rail selection carries the shown item so the holdings answer follows.
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
  const pendingMemberId = computed(() => (inFlight.value && inFlight.value.memberChange ? inFlight.value.memberId : null));
  // An item request counts only for the member it was made for: a viewed
  // member that changed meanwhile (a server fallback) shows no pending row.
  const pendingItemKey = computed(() => {
    const request = inFlight.value;
    if (!request || request.memberChange || request.itemKey === null) return null;
    return panel("party")?.viewed_member_id === request.memberId ? request.itemKey : null;
  });

  // Every admitted selection replaces the previous pending one (a rail click
  // after an item click leaves no item pending); a refused one leaves the
  // request still in flight marked.
  // `memberChange` marks a rail selection (the rail shows it pending); an
  // item selection for the current member marks only the item.
  function select(memberId, tab, itemKey, memberChange) {
    const requestId = dispatchIntent("party.view_member", {
      member_id: memberId,
      tab,
      skill_key: null,
      item_key: itemKey,
    });
    if (requestId !== null) pending.value = { memberId, itemKey, requestId, memberChange };
    return requestId;
  }

  const validId = (value) => Number.isSafeInteger(value) && value > 0;
  const validKey = (value) => typeof value === "string" && value !== "";

  function viewMember(memberId, tab, itemKey = null) {
    if (!validId(memberId)) return null;
    return select(memberId, tab, validKey(itemKey) ? itemKey : null, true);
  }

  // A bag row selection for the viewed member (design §6.2): the server
  // stores the item and republishes `item_holdings` for it.
  function onViewItem(intent) {
    const memberId = intent?.memberId;
    const itemKey = intent?.itemKey;
    if (!validId(memberId) || !validKey(itemKey)) return null;
    return select(memberId, "bag", itemKey, false);
  }

  // The shop window's rail (design §7): select the recipient or seller and
  // keep the shown item's holdings answer.
  function onViewShopMember(intent) {
    return viewMember(intent?.memberId, "shop", intent?.itemKey ?? null);
  }

  // A shop row selection: the server answers `item_holdings` for that item.
  function onViewShopItem(intent) {
    const memberId = intent?.memberId;
    const itemKey = intent?.itemKey;
    if (!validId(memberId) || !validKey(itemKey)) return null;
    return select(memberId, "shop", itemKey, false);
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

  return {
    memoryScope,
    pendingMemberId,
    pendingItemKey,
    onViewMember,
    onViewItem,
    onViewShopMember,
    onViewShopItem,
    openPartyWindow,
  };
}
