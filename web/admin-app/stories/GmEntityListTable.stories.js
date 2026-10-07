import { h } from "vue";
import GmEntityListTable from "../components/GmEntityListTable.vue";
import { DIALOGUE_ITEMS, LIST_PAGE, MEMORY_ITEMS, MONSTER_ITEMS } from "./runtime-fixtures.js";

// GmEntityListTable: the one list table of the runtime pages — the entity name
// links to its page, one column per field label the rows actually carry, and an
// optional trailing expander column for the narrative tabs.
export default {
  title: "GM/GmEntityListTable",
  component: GmEntityListTable,
  args: { rows: LIST_PAGE.items, kind: "npcs", caption: "NPC 清單" },
  render: (args) => ({
    setup: () => () =>
      h("div", { style: { padding: "32px", maxWidth: "1040px" } }, [h(GmEntityListTable, args)]),
  }),
};

export const KindList = {};

export const Monsters = { args: { rows: MONSTER_ITEMS.items, kind: "monsters", caption: "魔物清單" } };

export const WithExpander = {
  args: {
    rows: MEMORY_ITEMS,
    kind: "memories",
    caption: "記憶紀錄",
    extraColumn: "展開",
  },
  render: (args) => ({
    setup: () => () =>
      h("div", { style: { padding: "32px", maxWidth: "1040px" } }, [
        h(GmEntityListTable, args, {
          extra: () => h("button", { type: "button", class: "ui-btn ui-btn--ghost ui-btn--sm" }, "展開修訂"),
        }),
      ]),
  }),
};

export const GroupedDialogueRows = {
  args: { rows: DIALOGUE_ITEMS, kind: "dialogue", caption: "對話紀元（依玩家分組）", extraColumn: "展開" },
  render: (args) => ({
    setup: () => () =>
      h("div", { style: { padding: "32px", maxWidth: "1040px" } }, [
        h(GmEntityListTable, args, {
          extra: () => h("button", { type: "button", class: "ui-btn ui-btn--ghost ui-btn--sm" }, "展開紀元"),
        }),
      ]),
  }),
};

export const Empty = {
  args: {
    rows: [],
    kind: "npcs",
    caption: "NPC 清單",
    emptyTitle: "沒有符合條件的項目",
    emptyMessage: "調整篩選條件，或確認這個種類是否已經有資料。",
  },
};
