import { h } from "vue";
import { referenceLinks } from "../lib/world.js";
import { MARKED_ENTRY } from "./world-fixtures.js";
import GmJsonTree from "../components/GmJsonTree.vue";
import { NPC_RAW } from "./runtime-fixtures.js";

// GmJsonTree: the sole JSON-tree renderer, shared by the raw tab and the S2
// payload drawer. References become links; values JSON cannot carry become a
// distinct bounded marker instead of breaking the inventory.
export default {
  title: "GM/GmJsonTree",
  component: GmJsonTree,
  args: { value: NPC_RAW.raw, openDepth: 3 },
  render: (args) => ({
    setup: () => () =>
      h("div", { style: { padding: "32px", maxWidth: "1040px" } }, [h(GmJsonTree, args)]),
  }),
};

export const RawInventoryWithLinks = {};

export const UnserializableValue = {
  args: {
    value: {
      t_marker: { $unserializable: "set", repr: "{'t_a', 't_b'}" },
      t_nested: { inner: { $unserializable: "bytearray", repr: "bytearray(b'\\x00\\x01\\x02')" } },
    },
  },
};

export const Collapsed = { args: { value: NPC_RAW.raw, openDepth: 1 } };

export const EmptyContainers = { args: { value: { attributes: [], tags: {}, components: [] } } };

export const ScalarOnly = { args: { value: { dbref: 12, key: "合成守衛", active: true, note: null } } };

// An authored world-data entry (gm-portal-s4): declared references link at
// their exact field path; a dangling target stays visible as broken text.
export const AuthoredEntryWithReferences = {
  args: { value: MARKED_ENTRY.fields, links: referenceLinks(MARKED_ENTRY.references), openDepth: 4 },
};
