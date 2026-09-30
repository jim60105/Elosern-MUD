// The top navigation's 工具 group model (webclient-desktop-shell; A13
// webclient-chrome-navigation-polish). One record per tool, in bar order:
// its `key` is both the `dock-icons.js` glyph key and the key of the surface
// it opens, and its `label` is at once the control's accessible name, its
// visible tooltip, and the title of the surface's DrawerHeader, so the
// opener, its tooltip and the opened header never disagree. 圖鑑 opens the
// lore drawer; the rest open overlays.
export const NAV_TOOLS = Object.freeze([
  { key: "lineage", label: "技能系譜", testid: "nav-tool-lineage" },
  { key: "lore", label: "圖鑑", testid: "nav-tool-lore", drawer: "lore" },
  { key: "codex", label: "稱號冊", testid: "nav-tool-codex" },
  { key: "gallery", label: "角色肖像圖庫", testid: "gallery-opener" },
  { key: "help", label: "說明", testid: "nav-tool-help" },
]);

// The label of a tool key, or null when the key names no tool.
export function toolLabel(key) {
  return NAV_TOOLS.find((tool) => tool.key === key)?.label ?? null;
}
