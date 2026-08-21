import { h } from "vue";
import DockMenuItem from "../../components/DockMenuItem.vue";

// DockMenuItem: one action-dock cell. Props: itemKey (the preserved
// `action-`/`target-` key), label, enabled, reason (the disabled note),
// focused (the parent-owned focus slice), rowId. Events: focus (itemKey) on
// any pointer click, activate (itemKey) on pointer activation of an enabled
// cell.

const renderCell = (args) => ({
  render: () =>
    h("div", {
      style:
        "display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 7px; max-width: 480px;",
    }, [h(DockMenuItem, args)]),
});

export default {
  title: "Action/DockMenuItem",
  component: DockMenuItem,
};

export const Default = {
  render: renderCell,
  args: {
    itemKey: "action-explore.move",
    label: "走往北岸大道",
    enabled: true,
    focused: false,
    rowId: "dock-row-0",
  },
};

export const Focused = {
  render: renderCell,
  args: {
    itemKey: "action-explore.move",
    label: "走往北岸大道",
    enabled: true,
    focused: true,
    rowId: "dock-row-0",
  },
};

export const Disabled = {
  render: renderCell,
  args: {
    itemKey: "target-e2",
    label: "斷刃巡衛",
    enabled: false,
    reason: "已倒地",
    focused: false,
    rowId: "combat-row-1",
  },
};
