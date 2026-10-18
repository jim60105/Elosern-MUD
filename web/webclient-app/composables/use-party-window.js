// The party window's AppClient wiring (webclient-party-window-member-tab,
// design §6/§8): its openers, the one `party.view_member` dispatch per rail
// selection, and the pending entry while that request is in flight.
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

  const pendingMemberId = computed(() => {
    const request = pending.value;
    if (!request) return null;
    return store.view.dispatch?.inFlight?.requestId === request.requestId ? request.memberId : null;
  });

  function viewMember(memberId, tab) {
    if (!Number.isSafeInteger(memberId) || memberId <= 0) return null;
    const requestId = dispatchIntent("party.view_member", {
      member_id: memberId,
      tab,
      skill_key: null,
      item_key: null,
    });
    pending.value = requestId === null ? null : { memberId, requestId };
    return requestId;
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

  return { memoryScope, pendingMemberId, onViewMember, openPartyWindow };
}
