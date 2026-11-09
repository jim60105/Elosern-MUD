// handbook-tabs (handbook-titles-tab, design D1): the handbook window's
// first-level tab model, shared by QuestDrawer (the tab bar) and the store's
// handbook route entry (which refuses a tab outside the mode's set).
export const HANDBOOK_TAB_META = Object.freeze({
  book: { label: "任務簿", glyph: "quest_book" },
  counter: { label: "公會櫃檯", glyph: "guild_counter" },
  titles: { label: "稱號", glyph: "codex" },
});

// Tab keys present for one mode, in bar order.
export function handbookTabs({ combat }) {
  return combat ? ["titles"] : ["book", "counter", "titles"];
}
