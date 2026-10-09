// quest-drawer-memory (quest-drawer-book-tab, design Decision 3): the quest
// drawer's session memory — the last first-level tab, the last book state,
// and the selected row per tab. It lives at module level so it survives the
// drawer closing and reopening, but not a reload. It holds only keys: the
// drawer computes the effective tab, state, and row, so a remembered key that
// is now disabled or gone falls back without being overwritten.
//
// The memory is scoped to the transport generation and presentation epoch
// (`<generation>|<epoch>`): a reconnect or a new presentation discards every
// remembered selection, as webclient-contextual-hud requires of drawers.
import { reactive } from "vue";

const memory = reactive({
  scope: null,
  top: "book",
  bookState: "in_progress",
  selectedByTab: {},
});

function clear() {
  memory.top = "book";
  memory.bookState = "in_progress";
  memory.selectedByTab = {};
}

// Returns the shared memory, reset first when the scope changed.
export function useQuestDrawerMemory(scope) {
  syncQuestDrawerMemoryScope(scope);
  return memory;
}

export function syncQuestDrawerMemoryScope(scope) {
  if (memory.scope !== scope) {
    clear();
    memory.scope = scope;
  }
}

// Test seam: forget everything, as on a reload.
export function resetQuestDrawerMemory() {
  clear();
  memory.scope = null;
}
