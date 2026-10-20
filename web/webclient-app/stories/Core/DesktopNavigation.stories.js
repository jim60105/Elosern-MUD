import DesktopNavigation from "../../components/DesktopNavigation.vue";

export default {
  title: "Core/DesktopNavigation",
  component: DesktopNavigation,
  parameters: { layout: "fullscreen" },
};

// The bar over a strip of the shell's own top-bar ink, so the key chips,
// the separators and the hover glow read as they do in the client.
const renderNavigation = (args) => ({
  components: { DesktopNavigation },
  setup: () => ({ args }),
  template:
    '<div style="position:relative;height:100px;--left-column:16px;--header-h:calc(48px * var(--ui-scale, 1));' +
    'background:linear-gradient(180deg,#0a0b0df2 0 48px,transparent 48px)"><DesktopNavigation v-bind="args" /></div>',
});

// The exploration panel's navigation rows: the bar reads only `quests`.
const EXPLORATION_ITEMS = [
  { key: "character", label: "角色狀態", enabled: true },
  { key: "quests", label: "任務", enabled: true },
  { key: "inventory", label: "背包", enabled: true },
];

// Exploration carries 隊伍, 任務 and 地圖 with their hotkey chips, the tool
// group, then 設定 last (webclient-main-navigation-hotkeys).
export const Exploration = {
  render: renderNavigation,
  args: { mode: "exploration", items: EXPLORATION_ITEMS, partyAvailable: true },
};

// Combat keeps only 隊伍 in the same fixed-width region: the tool group and
// 設定 stand where they stood in exploration.
export const Combat = {
  render: renderNavigation,
  args: { mode: "combat", items: [{ key: "bag", label: "背包", enabled: true }], partyAvailable: true },
};

export const WithGallery = {
  render: renderNavigation,
  args: { mode: "exploration", galleryAvailable: true, items: EXPLORATION_ITEMS, partyAvailable: true },
};

// The party window is open: 隊伍 is current whichever tab it shows.
export const PartyWindowOpen = {
  render: renderNavigation,
  args: { mode: "exploration", galleryAvailable: true, items: EXPLORATION_ITEMS, partyAvailable: true, drawer: "party" },
};

// Possession changes nothing in the bar: the component takes no possession
// input, so a possessed session renders exactly the WithGallery bar (the
// approved prototype's MainNavigationPossessing pair).
export const Possessing = {
  render: renderNavigation,
  args: { ...WithGallery.args },
};

// The quest panel is unavailable: the quest entry is absent (no
// placeholder), and the tool group and 設定 keep their places because the
// primary region keeps its width (webclient-chrome-navigation-polish).
export const QuestsUnavailable = {
  render: renderNavigation,
  args: {
    mode: "exploration",
    partyAvailable: true,
    items: [
      { key: "character", label: "角色狀態", enabled: true },
      { key: "inventory", label: "背包", enabled: true },
    ],
  },
};
