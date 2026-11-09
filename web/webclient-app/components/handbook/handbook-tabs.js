// handbook-tabs (handbook-titles-tab, design D1; handbook-codex-tab, design
// D1): the handbook window's first-level tab model, shared by QuestDrawer
// (the tab bar) and the store's handbook route entry (which refuses a tab
// outside the mode's set). The codex (圖鑑) and titles tabs stay in combat.
export const HANDBOOK_TAB_META = Object.freeze({
  book: { label: "任務簿", glyph: "quest_book" },
  counter: { label: "公會櫃檯", glyph: "guild_counter" },
  codex: { label: "圖鑑", glyph: "lore" },
  titles: { label: "稱號", glyph: "codex" },
});

// Tab keys present for one mode, in bar order.
export function handbookTabs({ combat }) {
  return combat ? ["codex", "titles"] : ["book", "counter", "codex", "titles"];
}
