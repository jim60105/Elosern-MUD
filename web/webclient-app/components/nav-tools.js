// The top navigation's 工具 group model (webclient-desktop-shell; A13
// webclient-chrome-navigation-polish). One record per tool, in bar order:
// its `key` is both the `dock-icons.js` glyph key and the key of the surface
// it opens, and its `label` is at once the control's accessible name, its
// visible tooltip, and the title of the surface's DrawerHeader, so the
// opener, its tooltip and the opened header never disagree. 信件 opens its
// drawer; 圖鑑 and 稱號冊 open the 手帳 (the quest drawer) on its 圖鑑 and 稱號
// tabs through the store's handbook route request (handbook-codex-tab,
// handbook-titles-tab), so the drawer header keeps the handbook's own title;
// the rest open overlays. Skill lineage is the party
// window's 系譜 tab (隊伍 or the L hotkey), not a tool
// (webclient-main-navigation-hotkeys).
export const NAV_TOOLS = Object.freeze([
  { key: "letters", label: "信件", testid: "nav-tool-letters", drawer: "letters" },
  { key: "lore", label: "圖鑑", testid: "nav-tool-lore", handbook: "codex" },
  { key: "codex", label: "稱號冊", testid: "nav-tool-codex", handbook: "titles" },
  { key: "gallery", label: "角色肖像圖庫", testid: "gallery-opener" },
  { key: "help", label: "說明", testid: "nav-tool-help" },
]);

// 設定 stands after the tool group, at the very end of the bar, and shares
// the tools' icon form and tooltip.
export const NAV_SETTINGS = Object.freeze({ key: "settings", label: "設定", testid: "nav-settings" });

// The label of a tool key, or null when the key names no tool.
export function toolLabel(key) {
  return NAV_TOOLS.find((tool) => tool.key === key)?.label ?? (key === NAV_SETTINGS.key ? NAV_SETTINGS.label : null);
}
