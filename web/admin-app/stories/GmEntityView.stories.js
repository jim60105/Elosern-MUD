import { h } from "vue";
import GmEntityView from "../components/GmEntityView.vue";
import { ART_DETAIL, NPC_DETAIL, NPC_RAW, fakeRuntimeApi } from "./runtime-fixtures.js";
import { GmApiError } from "../lib/api.js";

// GmEntityView: the runtime entity shell — header with the display name and the
// verbatim identifiers, 概要/原始資料 tabs, NPC 記憶/對話 tabs, and a manual
// 重新載入 (never a polling timer).
const npcApi = fakeRuntimeApi({
  "/state/npcs/12": NPC_DETAIL,
  "/state/object/12/raw": NPC_RAW,
  "/state/memories": { items: [], next_cursor: null },
  "/state/snapshots": { items: [], next_cursor: null },
  "/state/dialogue": { items: [], next_cursor: null },
});

export default {
  title: "GM/GmEntityView",
  component: GmEntityView,
  args: { kind: "npcs", id: "12", owner: "", api: npcApi },
  render: (args) => ({
    setup: () => () =>
      h("div", { style: { padding: "32px" } }, [h(GmEntityView, { key: `${args.kind}/${args.id}`, ...args })]),
  }),
};

export const NpcSummary = {};

export const RecordBackedRaw = {
  args: {
    kind: "art",
    id: "art:t_subject",
    api: fakeRuntimeApi({ "/state/art/art%3At_subject": ART_DETAIL }),
  },
};

export const UncuratedObject = {
  args: {
    kind: "object",
    id: "7",
    api: fakeRuntimeApi({
      "/state/object/7/raw": { ...NPC_RAW, id: "7", dbref: 7, raw: { ...NPC_RAW.raw, dbref: 7, key: "t_plain" } },
    }),
  },
};

export const LookupError = {
  args: {
    kind: "npcs",
    id: "999999",
    api: fakeRuntimeApi({
      "/state/npcs/999999": new GmApiError("object_not_found", {
        status: 404,
        message: "找不到指定的物件。",
      }),
    }),
  },
};
