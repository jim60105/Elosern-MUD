import DesktopNavigation from "../../components/DesktopNavigation.vue";

export default {
  title: "Core/DesktopNavigation",
  component: DesktopNavigation,
  parameters: { layout: "fullscreen" },
};

const renderNavigation = (args) => ({
  components: { DesktopNavigation },
  setup: () => ({ args }),
  template: '<div style="position:relative;height:100px;--left-column:16px;--header-h:48px"><DesktopNavigation v-bind="args" /></div>',
});

// Exploration carries the five primary controls; Combat keeps only the
// combat root's 背包 beside 設定 in the same fixed-width region.
export const Exploration = {
  render: renderNavigation,
  args: {
    mode: "exploration",
    items: [
      { key: "character", label: "角色狀態", enabled: true },
      { key: "inventory", label: "背包", enabled: true },
      { key: "quests", label: "任務", enabled: true },
    ],
  },
};

export const Combat = {
  render: renderNavigation,
  args: { mode: "combat", items: [{ key: "bag", label: "背包", enabled: true }] },
};

export const WithGallery = {
  render: renderNavigation,
  args: {
    mode: "exploration",
    galleryAvailable: true,
    items: [
      { key: "character", label: "角色狀態", enabled: true },
      { key: "inventory", label: "背包", enabled: true },
      { key: "quests", label: "任務", enabled: true },
    ],
  },
};

// The quest panel is unavailable: the quest entry is absent (no
// placeholder), and 設定 and the tool group keep their places because the
// primary region keeps its width (webclient-chrome-navigation-polish).
export const QuestsUnavailable = {
  render: renderNavigation,
  args: {
    mode: "exploration",
    items: [
      { key: "character", label: "角色狀態", enabled: true },
      { key: "inventory", label: "背包", enabled: true },
    ],
  },
};
