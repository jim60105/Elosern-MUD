import { h } from "vue";
import DockMenu from "../../components/DockMenu.vue";
import {
  EXPLORATION_AFFORDANCES_SAMPLE,
  TARGET_ITEMS_SAMPLE,
} from "../fixtures.js";

// DockMenu: the framed grid of action-dock cells (a root menu, a sub-menu,
// or a target selection frame). Props: items (the context_actions v5
// affordance/target entries — action cells get `action-` item keys, target
// cells get `target-`), focusedKey (the parent-owned focus slice), idPrefix
// (row id prefix, e.g. combat-row), gridCols (fixed framed-grid columns).
// Events: focus-change(key), activate({ key, item, intent }).

const renderMenu = (args) => ({
  render: () =>
    h("div", { style: "max-width: 720px;" }, [h(DockMenu, args)]),
});

export default {
  title: "Action/DockMenu",
  component: DockMenu,
};

export const ExplorationFrame = {
  render: renderMenu,
  args: {
    items: EXPLORATION_AFFORDANCES_SAMPLE,
    focusedKey: "action-explore.talk_freeform",
  },
};

export const TargetFrame = {
  render: renderMenu,
  args: {
    items: TARGET_ITEMS_SAMPLE,
    focusedKey: "target-e1",
    idPrefix: "combat-row",
  },
};

export const FixedGridFrame = {
  render: renderMenu,
  args: {
    items: EXPLORATION_AFFORDANCES_SAMPLE,
    focusedKey: null,
    gridCols: 3,
  },
};
