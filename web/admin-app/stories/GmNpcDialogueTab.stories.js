import { h } from "vue";
import GmNpcDialogueTab from "../components/GmNpcDialogueTab.vue";
import { DIALOGUE_DETAIL, DIALOGUE_ITEMS, fakeRuntimeApi } from "./runtime-fixtures.js";

// GmNpcDialogueTab: dialogue epochs and frames grouped by player. Frame rows
// with a recorded call id link to the retained S2 drawer; no dialogue context
// is assembled and no correspondence is settled to render this tab.
export default {
  title: "GM/GmNpcDialogueTab",
  component: GmNpcDialogueTab,
  args: {
    npcDbref: "12",
    api: fakeRuntimeApi({
      "/state/dialogue": { items: DIALOGUE_ITEMS, next_cursor: null },
      "/state/dialogue/t_player_a": DIALOGUE_DETAIL,
    }),
  },
  render: (args) => ({
    setup: () => () => h("div", { style: { padding: "32px" } }, [h(GmNpcDialogueTab, args)]),
  }),
};

export const GroupedByPlayer = {};

export const NoDialogueYet = {
  args: { api: fakeRuntimeApi({ "/state/dialogue": { items: [], next_cursor: null } }) },
};
