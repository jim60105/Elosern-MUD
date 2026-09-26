import { h } from "vue";
import DockMenu from "../../components/DockMenu.vue";
import {
  EXPLORATION_AFFORDANCES_SAMPLE,
  TARGET_ITEMS_SAMPLE,
} from "../fixtures.js";

// DockMenu: the framed grid of action-dock cells (a root menu, a sub-menu,
// or a target selection frame). Props: items (the normalized dock items —
// action cells get `action-` item keys, target cells get `target-`),
// focusedKey (the parent-owned focus slice), idPrefix (row id prefix, e.g.
// combat-row), gridCols (fixed framed-grid columns). Events:
// focus-change(key), activate({ key, item, intent }).
//
// The exploration dock's own frames do not render here: the root is the
// SceneOverview component and a target's affordances are the DockVerbPopover
// card (webclient-talk-open-dock retired the `nav` and `affordance` panes
// with their last producers).

const renderMenu = (args) => ({
  render: () =>
    h("div", { style: "max-width: 720px;" }, [h(DockMenu, args)]),
});

export default {
  title: "Action/DockMenu",
  component: DockMenu,
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
