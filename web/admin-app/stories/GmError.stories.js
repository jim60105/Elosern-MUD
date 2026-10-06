import { h } from "vue";
import GmError from "../components/GmError.vue";

// GmError: the server's zh-TW message plus its stable code, verbatim; actions
// stay neutral (seal-red is reserved for destructive actions).
export default {
  title: "GM/GmError",
  component: GmError,
  args: {
    title: "無法取得健康狀態",
    message: "資料庫目前無法讀取。",
    code: "database_unreadable",
  },
  render: (args) => ({
    setup: () => () =>
      h("div", { style: { padding: "32px", maxWidth: "560px" } }, [
        h(GmError, args, { actions: () => h("button", { class: "ui-btn ui-btn--sm" }, "重試") }),
      ]),
  }),
};

export const ServerError = {};
export const NetworkFailure = {
  args: { title: "無法連線", message: "無法連線到伺服器，請確認服務是否運作中。", code: "network_error" },
};
export const MalformedResponse = {
  args: { title: "載入失敗", message: "伺服器回應的格式不正確。", code: "malformed_response" },
};
