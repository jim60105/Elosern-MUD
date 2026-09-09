import { h } from "vue";
import OverlayHost from "../../components/OverlayHost.vue";
import LineagePanel from "../../components/LineagePanel.vue";

export default {
  title: "Overlays/LineagePanel",
  component: LineagePanel,
};

const renderLineage = (args) => ({
  render: () => h(OverlayHost, { open: "lineage" }, {
    default: () => h(LineagePanel, args),
  }),
});

const lineage = {
  schema_version: 1,
  available: true,
  kind: "lineage",
  completed_count: 0,
  total_count: 2,
  chains: [
    {
      root_skill_key: "fire_arrow", element_or_style_zh: "火", consumed: false, meter: 0.46,
      nodes: [
        { skill_key: "fire_arrow", display_name_zh: "火焰箭", owned: true, usable: true, level: 1, xp_into_level: 23, xp_to_next_level: 27, capped: false, prereq_text_zh: "" },
        { skill_key: "scorching_wave", display_name_zh: "灼熱波動", owned: false, usable: false, level: 0, xp_into_level: 0, xp_to_next_level: 50, capped: false, prereq_text_zh: "需「火球術 Lv.3」" },
      ],
    },
    {
      root_skill_key: "wind_lance", element_or_style_zh: "風", consumed: false, meter: 0.25,
      nodes: [
        { skill_key: "wind_lance", display_name_zh: "風之槍", owned: true, usable: true, level: 1, xp_into_level: 23, xp_to_next_level: 27, capped: false, prereq_text_zh: "" },
      ],
    },
  ],
};

export const ProgressAndPrerequisites = { render: renderLineage, args: { lineage } };
export const Empty = { render: renderLineage, args: { lineage: { ...lineage, completed_count: 0, total_count: 0, chains: [] } } };
export const Unavailable = {
  render: renderLineage,
  args: { lineage: { available: false, reason: { message: "技能系譜目前無法顯示" } } },
};
