import { h } from "vue";
import GmTable from "../components/GmTable.vue";
import GmPanel from "../components/GmPanel.vue";
import GmStatusBadge from "../components/GmStatusBadge.vue";
import { HEALTH_COLUMNS, HEALTH_ROWS } from "./fixtures.js";

// GmTable: a ledger table; `mono` columns keep identifiers verbatim.
export default {
  title: "GM/GmTable",
  component: GmTable,
  args: {
    columns: HEALTH_COLUMNS,
    rows: HEALTH_ROWS,
    rowKey: "key",
    caption: "各項檢查的即時結果",
    flush: true,
  },
  render: renderTable,
};

export const Content = {};

export const Identifiers = {
  args: {
    columns: [
      { key: "key", label: "登錄鍵", mono: true },
      { key: "label", label: "名稱" },
      { key: "count", label: "數量", mono: true, align: "end" },
    ],
    rows: [
      { key: "monster:ash_wolf", label: "灰燼狼", count: "12" },
      { key: "item:potion.minor_heal", label: "初級治療藥水", count: "340" },
      { key: "quest:Q-0007_guild-trial", label: "公會試煉", count: "1" },
    ],
    caption: "登錄資料（識別碼原樣顯示）",
    flush: true,
  },
  render: (args) => ({
    setup: () => () =>
      h("div", { style: { padding: "32px", maxWidth: "880px" } }, [
        h(GmPanel, { title: "登錄資料", flush: true }, () => [h(GmTable, args)]),
      ]),
  }),
};

export const Empty = {
  args: { rows: [], emptyTitle: "目前沒有資料", emptyMessage: "檢查結果會列在這裡。" },
};

// Declared after the default export: the coverage gate reads the first
// `title:` in the file as the story title.
function renderTable(args) {
  return {
    setup: () => () =>
      h("div", { style: { padding: "32px", maxWidth: "880px" } }, [
        h(GmPanel, { title: "系統健康", flush: true }, () => [
          h(GmTable, args, {
            "cell-status": ({ row }) => h(GmStatusBadge, row.status),
          }),
        ]),
      ]),
  };
}
