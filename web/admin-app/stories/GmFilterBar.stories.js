import { h } from "vue";
import GmFilterBar from "../components/GmFilterBar.vue";
import { RUNTIME_KIND_BY_KEY } from "../lib/runtime.js";

// GmFilterBar: the declarative filter vocabulary of one runtime kind. Any
// committed change restarts pagination; the parent owns that.
export default {
  title: "GM/GmFilterBar",
  component: GmFilterBar,
  args: {
    fields: RUNTIME_KIND_BY_KEY.narrative.filters,
    modelValue: {},
    caption: "敘事紀錄篩選",
  },
  render: (args) => ({
    setup: () => () =>
      h("div", { style: { padding: "32px", maxWidth: "1040px" } }, [h(GmFilterBar, args)]),
  }),
};

export const NarrativeFilters = {};

export const Applied = {
  args: {
    fields: RUNTIME_KIND_BY_KEY.monsters.filters,
    modelValue: { species: "t_whisper_quail", region: "t_bramble_wold" },
    caption: "魔物篩選",
  },
};

export const RequiredOwner = {
  args: {
    fields: RUNTIME_KIND_BY_KEY.quests.filters,
    modelValue: {},
    caption: "任務篩選",
  },
};

export const Busy = {
  args: {
    fields: RUNTIME_KIND_BY_KEY.art.filters,
    modelValue: { status: "failed" },
    busy: true,
    caption: "美術資產篩選",
  },
};
