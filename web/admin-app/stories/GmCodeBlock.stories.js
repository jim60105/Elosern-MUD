import { h } from "vue";
import GmCodeBlock from "../components/GmCodeBlock.vue";
import { CALL_DETAIL } from "./fixtures.js";

// GmCodeBlock: verbatim text or JSON with copy and a long-content collapse.
export default {
  title: "GM/GmCodeBlock",
  component: GmCodeBlock,
  args: { text: "旅人：請問北方的森林最近安全嗎？", label: "使用者訊息" },
  render: (args) => ({
    setup: () => () => h("div", { style: { padding: "32px", maxWidth: "720px" } }, [h(GmCodeBlock, args)]),
  }),
};

export const ShortText = {};
export const Json = { args: { label: "回應", text: CALL_DETAIL.exchanges[0].response } };
export const LongCollapsed = { args: { label: "請求", text: CALL_DETAIL.exchanges[0], maxLines: 8 } };
