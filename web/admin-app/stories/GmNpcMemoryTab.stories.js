import { h } from "vue";
import GmNpcMemoryTab from "../components/GmNpcMemoryTab.vue";
import {
  MEMORY_DETAIL,
  MEMORY_ITEMS,
  RECALL_RESULT,
  SNAPSHOT_DETAIL,
  SNAPSHOT_ITEMS,
  fakeRuntimeApi,
} from "./runtime-fixtures.js";

// GmNpcMemoryTab: filtered effective memories with their complete revision
// history on demand, the newest ten context snapshots with their token
// accounting and S2 evidence links, and the read-only recall preview.
const memoryApi = fakeRuntimeApi({
  "/state/memories": { items: MEMORY_ITEMS, next_cursor: "t_cursor_1" },
  "/state/memories/31": MEMORY_DETAIL,
  "/state/snapshots": { items: SNAPSHOT_ITEMS, next_cursor: null },
  "/state/snapshots/t_snapshot_2": SNAPSHOT_DETAIL,
  "/state/npc/12/recall": RECALL_RESULT,
});

export default {
  title: "GM/GmNpcMemoryTab",
  component: GmNpcMemoryTab,
  args: { npcDbref: "12", api: memoryApi },
  render: (args) => ({
    setup: () => () => h("div", { style: { padding: "32px" } }, [h(GmNpcMemoryTab, args)]),
  }),
};

export const MemoriesAndSnapshots = {};

export const EmptyOwner = {
  args: {
    api: fakeRuntimeApi({
      "/state/memories": { items: [], next_cursor: null },
      "/state/snapshots": { items: [], next_cursor: null },
    }),
  },
};
