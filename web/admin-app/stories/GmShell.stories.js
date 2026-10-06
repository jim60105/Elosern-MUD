import { h } from "vue";
import GmShell from "../components/GmShell.vue";
import GmPanel from "../components/GmPanel.vue";
import GmTable from "../components/GmTable.vue";
import GmStatusBadge from "../components/GmStatusBadge.vue";
import { GM_SECTIONS } from "../lib/sections.js";
import { HEALTH_COLUMNS, HEALTH_ROWS, SESSION } from "./fixtures.js";

// GmShell: the desktop-first ledger layout (side navigation, page header,
// panel/table content). Below 860px it collapses to one column.
export default {
  title: "GM/GmShell",
  component: GmShell,
  parameters: { layout: "fullscreen" },
  args: {
    sections: GM_SECTIONS,
    activeKey: "overview",
    title: "總覽",
    eyebrow: "ELOSERN · 營運者介面",
    account: SESSION.account_name,
    permissionLevel: SESSION.permission_level,
    logoutUrl: "/auth/logout/",
  },
  render: (args) => ({
    setup: () => () =>
      h(GmShell, { ...args, onNavigate: () => {} }, () => [
        h("div", { style: { display: "grid", gap: "24px" } }, [
          h(GmPanel, { title: "系統健康", flush: true }, () => [
            h(
              GmTable,
              { columns: HEALTH_COLUMNS, rows: HEALTH_ROWS, rowKey: "key", caption: "各項檢查的即時結果", captionHidden: true, flush: true },
              { "cell-status": ({ row }) => h(GmStatusBadge, row.status) },
            ),
          ]),
        ]),
      ]),
  }),
};

export const Overview = {};
export const SignedOutHeader = { args: { account: "", permissionLevel: "" } };
