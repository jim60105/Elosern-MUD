import DesktopNavigation from "../../components/DesktopNavigation.vue";

export default {
  title: "Core/DesktopNavigation",
  component: DesktopNavigation,
  parameters: { layout: "fullscreen" },
};

const renderNavigation = (args) => ({
  components: { DesktopNavigation },
  setup: () => ({ args }),
  template: '<div style="position:relative;height:100px;--left-column:16px;--header-h:80px"><DesktopNavigation v-bind="args" /></div>',
});

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
