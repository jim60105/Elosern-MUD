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
// The exploration dock's own surfaces do not render here: the root is the
// exit compass's pane (an empty router menu, exploration-room-actions), a
// target's affordances are the stage's verb card (exploration-presence-rail;
// webclient-talk-open-dock retired the `nav` and `affordance` panes with
// their last producers), and the suggestions are the centred suggestions
// card (the `cards` pane left with its frame).

// The narrow combat card's inner column (webclient-combat-command-card-
// centred): a 264px host, as the card the stage stands at its dead centre.
const renderNarrow = (args) => ({
  render: () =>
    h("div", { style: "width: 264px; box-sizing: border-box; padding: 12px; display: flex; flex-direction: column; gap: 6px;" }, [
      h(DockMenu, args),
    ]),
});

export default {
  title: "Action/DockMenu",
  component: DockMenu,
};

export const TargetFrame = {
  render: renderNarrow,
  args: {
    items: TARGET_ITEMS_SAMPLE,
    focusedKey: "target-e1",
    idPrefix: "combat-row",
  },
};

export const FixedGridFrame = {
  render: renderNarrow,
  args: {
    items: EXPLORATION_AFFORDANCES_SAMPLE,
    focusedKey: null,
    gridCols: 3,
  },
};
