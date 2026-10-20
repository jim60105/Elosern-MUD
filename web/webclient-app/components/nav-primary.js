// The top navigation's labelled primary entries (webclient-main-navigation-
// hotkeys; design §8 of the party member management design): 隊伍, 任務 and
// 地圖, in that fixed order, each with the window hotkey it shares with
// `composables/use-window-hotkeys.js`. The bar packs the present entries
// against the trailing edge of a region sized for all three, so the 工具
// group and 設定 never move when a mode drops an entry.
export const NAV_PRIMARY = Object.freeze([
  Object.freeze({ key: "party", label: "隊伍", glyph: "party", hotkey: "P" }),
  Object.freeze({ key: "quests", label: "任務", glyph: "quests", hotkey: "J" }),
  Object.freeze({ key: "map", label: "地圖", glyph: "map", hotkey: "M" }),
]);

// The glyph count of each entry's label sizes its control, so the region's
// width is the same whichever entries a mode supplies.
export const NAV_PRIMARY_GLYPHS = NAV_PRIMARY.reduce((sum, entry) => sum + Array.from(entry.label).length, 0);

// The entries present for one committed state, in bar order. 隊伍 follows the
// committed `party` panel (client-mapped, in every playing mode); 任務 is the
// server's `quests` navigation row (absent while the quest surface is
// unavailable and in combat, whose root carries no quest row); 地圖 is
// client-local and absent in combat. A missing entry is simply absent —
// never a disabled or hidden stand-in.
export function primaryEntries({ mode, partyAvailable, items }) {
  if (mode === "creation") return [];
  const quests = mode === "combat" ? null : (items || []).find((item) => item && item.key === "quests") || null;
  const present = {
    party: partyAvailable ? { enabled: true } : null,
    quests: quests ? { enabled: quests.enabled !== false, reason: quests.disabled_reason?.message ?? null } : null,
    map: mode === "combat" ? null : { enabled: true },
  };
  return NAV_PRIMARY.filter((entry) => present[entry.key]).map((entry) => ({
    ...entry,
    glyphs: Array.from(entry.label).length,
    enabled: present[entry.key].enabled,
    reason: present[entry.key].reason ?? null,
  }));
}
