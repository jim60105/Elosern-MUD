import { h } from "vue";
import GmServiceCard from "../components/GmServiceCard.vue";

// GmServiceCard: one external service; status by text, glyph and rule style.
export default {
  title: "GM/GmServiceCard",
  component: GmServiceCard,
  args: {
    name: "SD 繪圖",
    status: "ok",
    statusLabel: "正常",
    detail: "sd-webui 可連線",
    meta: [
      { label: "主機", value: "sd.local.test", mono: true },
      { label: "檢查於", value: "14:31:23（快取）", mono: true },
    ],
  },
  render: (args) => ({
    setup: () => () => h("div", { style: { padding: "32px", maxWidth: "320px" } }, [h(GmServiceCard, args)]),
  }),
};

export const Ok = {};
export const Warn = {
  args: {
    name: "翻譯",
    status: "warn",
    statusLabel: "最近失敗",
    detail: "後端已啟用，但緩衝區內有失敗紀錄",
    meta: [
      { label: "實作類別", value: "CTranslate2Backend", mono: true },
      { label: "最近失敗", value: "art_translate_failed · 6 分前", mono: true },
    ],
  },
};
export const Offline = {
  args: {
    status: "crit",
    statusLabel: "離線",
    detail: "無法連線至 sd-webui；生成會在服務恢復後繼續",
    meta: [
      { label: "主機", value: "sd.local.test", mono: true },
      { label: "錯誤代碼", value: "sd_connection_refused", mono: true },
    ],
  },
};
export const SlotError = { args: { error: { code: "sd_unavailable", message: "無法取得 sd-webui 連線狀態。" } } };
