import { h, ref } from "vue";
import GmConfirmDialog from "../components/GmConfirmDialog.vue";

// GmConfirmDialog: a modal decision. `danger` paints the confirm control in
// seal ink; the control names its consequence instead of a generic 確定.
export default {
  title: "GM/GmConfirmDialog",
  component: GmConfirmDialog,
  args: { title: "刪除存檔？", confirmLabel: "永久刪除", danger: true, busy: false },
  render: (args) => ({
    setup() {
      const open = ref(true);
      return () =>
        h("div", { style: { padding: "32px" } }, [
          h("button", { class: "ui-btn", onClick: () => (open.value = true) }, "開啟對話框"),
          h(
            GmConfirmDialog,
            { ...args, open: open.value, onCancel: () => (open.value = false), onConfirm: () => (open.value = false) },
            {
              default: () => [
                h("p", { style: { color: "var(--paper-50)" } }, "「港口初到」20261006T090000-77aa11"),
                h("p", "資料庫與美術兩半都會刪除，此動作無法復原。"),
              ],
            },
          ),
        ]);
    },
  }),
};

export const Danger = {};
export const Busy = { args: { busy: true } };
export const Neutral = { args: { title: "確認操作？", confirmLabel: "繼續", danger: false } };
