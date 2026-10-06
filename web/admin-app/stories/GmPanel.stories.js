import { h } from "vue";
import GmPanel from "../components/GmPanel.vue";

// GmPanel: the titled ledger card every GM page is built from.
export default {
  title: "GM/GmPanel",
  component: GmPanel,
  args: { title: "操作者工作階段", description: "目前登入的帳號、權限與伺服器資訊" },
  render: (args) => ({
    setup: () => () =>
      h("div", { style: { padding: "32px", maxWidth: "560px" } }, [
        h(GmPanel, args, {
          default: () =>
            h("p", { style: { color: "var(--paper-300)" } }, "面板內容區：表格、清單或說明文字。"),
          actions: () => h("button", { class: "ui-btn ui-btn--ghost ui-btn--sm" }, "重新整理"),
        }),
      ]),
  }),
};

export const Default = {};
export const TitleOnly = { args: { title: "系統健康", description: "" } };
