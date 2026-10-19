// party-window-memory (webclient-party-window-member-tab, design §6): the
// party window's session memory — its last first-level tab. It lives at
// module level so it survives the window closing and reopening, but not a
// reload, mirroring quest-drawer-memory.js. The selected member is NOT kept
// here: it is server truth (`party.viewed_member_id`, set through
// `party.view_member`), so it persists across tabs and reopenings by itself.
//
// The memory is scoped to the transport generation and presentation epoch
// (`<generation>|<epoch>`): a reconnect or a new presentation discards the
// remembered tab, as webclient-contextual-hud requires of drawers.
import { reactive } from "vue";

export const PARTY_WINDOW_DEFAULT_TAB = "member";

const memory = reactive({
  scope: null,
  tab: PARTY_WINDOW_DEFAULT_TAB,
});

function clear() {
  memory.tab = PARTY_WINDOW_DEFAULT_TAB;
}

export function syncPartyWindowMemoryScope(scope) {
  if (memory.scope !== scope) {
    clear();
    memory.scope = scope;
  }
}

// Returns the shared memory, reset first when the scope changed.
export function usePartyWindowMemory(scope) {
  syncPartyWindowMemoryScope(scope);
  return memory;
}

// An opener that names a tab (the 成員 openers) records it before the window
// mounts, so the window opens there.
export function rememberPartyWindowTab(scope, tab) {
  syncPartyWindowMemoryScope(scope);
  memory.tab = tab;
}

// The live tab of the shared memory (the open window writes it), read by
// the top navigation to mark the entry of the open tab.
export function partyWindowTab() {
  return memory.tab;
}

// Test seam: forget everything, as on a reload.
export function resetPartyWindowMemory() {
  clear();
  memory.scope = null;
}
