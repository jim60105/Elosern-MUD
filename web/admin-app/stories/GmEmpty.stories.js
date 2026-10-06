import { h } from "vue";
import GmEmpty from "../components/GmEmpty.vue";
import GmPanel from "../components/GmPanel.vue";

// GmEmpty: an actual "no data" state of a panel or table.
export default {
  title: "GM/GmEmpty",
  component: GmEmpty,
  args: { title: "目前沒有資料", message: "符合條件的紀錄會列在這裡。" },
};

export const Default = {};

export const InPanel = {
  args: { title: "沒有符合的項目", message: "請調整篩選條件後再試一次。" },
  render: (args) => ({
    setup: () => () =>
      h("div", { style: { padding: "32px", maxWidth: "560px" } }, [
        h(GmPanel, { title: "查詢結果" }, () => [
          h(GmEmpty, args, { actions: () => h("button", { class: "ui-btn ui-btn--sm" }, "清除篩選") }),
        ]),
      ]),
  }),
};
