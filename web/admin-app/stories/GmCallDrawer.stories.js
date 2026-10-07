import { h } from "vue";
import GmCallDrawer from "../components/GmCallDrawer.vue";
import { CALL_DETAIL, fakeApi } from "./fixtures.js";
import { GmApiError } from "../lib/api.js";

const CALL = "0c".repeat(16);

// GmCallDrawer: the modal payload sheet for one guarded LLM call. Each story
// binds the synthetic transcript lookup result through `args.detail`.
export default {
  title: "GM/GmCallDrawer",
  component: GmCallDrawer,
  args: { callId: CALL, detail: CALL_DETAIL },
  render: (args) => ({
    setup: () => () =>
      h("div", { style: { minHeight: "100vh" } }, [
        h(GmCallDrawer, { callId: args.callId, api: fakeApi(() => args.detail) }),
      ]),
  }),
};

export const MultipleAttempts = {};
export const OutcomeOnly = {
  args: { detail: { outcome: { ...CALL_DETAIL.outcome, reason: "profile_disabled", attempts: [] }, exchanges: [] } },
};
export const ExchangesWithoutOutcome = { args: { detail: { outcome: null, exchanges: CALL_DETAIL.exchanges } } };
export const Expired = {
  args: {
    detail: new GmApiError("transcript_not_found", {
      status: 404,
      message: "找不到此呼叫的 transcript 紀錄（可能已超過保留期限）。",
    }),
  },
};
export const Disabled = {
  args: {
    detail: new GmApiError("transcript_disabled", { status: 409, message: "LLM transcript 已停用，無法查詢呼叫內容。" }),
  },
};
