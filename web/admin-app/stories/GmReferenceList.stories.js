import { h } from "vue";
import GmReferenceList from "../components/GmReferenceList.vue";
import { MARKED_ENTRY } from "./world-fixtures.js";

// GmReferenceList: outgoing references by field path, or one inverse group of
// referrers. A dangling target is broken text with a badge, never a link.
const OUTGOING = MARKED_ENTRY.references.map((item) => ({
  registry: item.registry,
  registryLabel: item.registry_label,
  key: item.key,
  label: item.label,
  fieldPath: item.field_path,
  missing: !item.exists,
}));
const INCOMING = MARKED_ENTRY.referrers[1].items.map((item) => ({
  registry: item.registry,
  registryLabel: item.registry_label,
  key: item.key,
  label: item.label,
  fieldPath: item.field_path,
}));

export default {
  title: "GM/GmReferenceList",
  component: GmReferenceList,
  args: { items: OUTGOING, mode: "outgoing", previewCount: 8 },
  render: (args) => ({
    setup: () => () => h("div", { style: { padding: "32px", maxWidth: "520px" } }, [h(GmReferenceList, args)]),
  }),
};

export const OutgoingWithDangling = {};

export const IncomingGroup = { args: { items: INCOMING, mode: "incoming" } };

export const SingleReferrer = { args: { items: INCOMING.slice(0, 1), mode: "incoming" } };
