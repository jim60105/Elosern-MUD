import { h } from "vue";
import ActionDock from "../../components/ActionDock.vue";
import DockMenu from "../../components/DockMenu.vue";
import {
  EXPLORATION_AFFORDANCES_SAMPLE,
  SUGGESTIONS_DEGRADED_EMPTY_SAMPLE,
  SUGGESTIONS_GENERATING_SAMPLE,
  SUGGESTIONS_READY_SAMPLE,
  SUGGESTIONS_UNAVAILABLE_SAMPLE,
} from "../fixtures.js";

// ActionDock: the non-closable bottom action surface. Props: mode (the
// preserved #action-dock data-mode), guidancePrefix (per-surface guidance
// prefix, rendered on its own line and by the breadcrumb; the shortcut
// legend is the tab bar's static draft hint), suggestions (the committed
// context_actions v5 suggestions envelope). Slot: the active menu frame (a
// DockMenu). Event: action (the exact OOB action intent for a card
// activation or the dismiss control).

const renderDock = (args) => ({
  render: () =>
    h("div", { style: "border: 1px solid var(--ink-700); border-radius: 12px; overflow: hidden;" }, [
      h("div", { style: "padding: 8px; font-family: var(--f-mono); color: var(--paper-500); font-size: 13px;" },
        "（上方為敘事區域）"),
      h(ActionDock, args, {
        default: () => [
          h(DockMenu, {
            items: EXPLORATION_AFFORDANCES_SAMPLE,
            focusedKey: "action-explore.move",
            idPrefix: "dock-row",
          }),
        ],
      }),
    ]),
});

export default {
  title: "Action/ActionDock",
  component: ActionDock,
};

export const ExplorationDock = {
  render: renderDock,
  args: {
    mode: "exploration",
    guidancePrefix: "附近動作",
    suggestions: SUGGESTIONS_READY_SAMPLE,
  },
};

export const GeneratingSuggestions = {
  render: renderDock,
  args: {
    mode: "exploration",
    guidancePrefix: "附近動作",
    suggestions: SUGGESTIONS_GENERATING_SAMPLE,
  },
};

export const DegradedEmptySuggestions = {
  render: renderDock,
  args: {
    mode: "exploration",
    guidancePrefix: "附近動作",
    suggestions: SUGGESTIONS_DEGRADED_EMPTY_SAMPLE,
  },
};

export const UnavailableSuggestions = {
  render: renderDock,
  args: {
    mode: "exploration",
    guidancePrefix: "附近動作",
    suggestions: SUGGESTIONS_UNAVAILABLE_SAMPLE,
  },
};
