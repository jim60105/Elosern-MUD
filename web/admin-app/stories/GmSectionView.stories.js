import { h } from "vue";
import GmSectionView from "../components/GmSectionView.vue";
import { NPC_DETAIL } from "./runtime-fixtures.js";

// GmSectionView: the one curated-section renderer. Every section type the
// readers emit is shown here, plus the isolated error slot a failed source
// produces — the remaining panels of a page stay readable.
const sectionOf = (key) => NPC_DETAIL.sections.find((section) => section.key === key);

export default {
  title: "GM/GmSectionView",
  component: GmSectionView,
  args: { section: sectionOf("identity") },
  render: (args) => ({
    setup: () => () =>
      h("div", { style: { padding: "32px", maxWidth: "560px" } }, [h(GmSectionView, args)]),
  }),
};

export const LedgerWithLinks = {};

export const Tiles = { args: { section: sectionOf("resources") } };

export const Table = { args: { section: sectionOf("services") } };

export const Groups = { args: { section: sectionOf("persona") } };

export const Chips = { args: { section: sectionOf("links") } };

export const EmptyPayload = { args: { section: { key: "schedule", title: "今日排程", type: "empty", note: "此 NPC 目前沒有排程。" } } };

export const TreePayload = {
  args: {
    section: { key: "content", title: "內容", type: "tree", value: { note: "合成記憶", subject: "t_subject" } },
  },
};

export const TextPayload = {
  args: { section: { key: "prompt", title: "來源敘述", type: "text", text: "一頭在合成礁石上休息的合成禽鳥。" } },
};

// A section whose source failed: only this slot carries the diagnostic error.
export const IsolatedErrorMessage = { args: { section: sectionOf("wallet") } };
