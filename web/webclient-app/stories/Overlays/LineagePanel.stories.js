import { h } from "vue";
import OverlayHost from "../../components/OverlayHost.vue";
import LineagePanel from "../../components/LineagePanel.vue";

export default {
  title: "Overlays/LineagePanel",
  component: LineagePanel,
};

const renderLineage = (args) => ({
  render: () => h(OverlayHost, { overlay: "lineage" }, {
    default: () => h(LineagePanel, args),
  }),
});

const lineage = {
  schema_version: 2,
  available: true,
  kind: "lineage",
  completed_count: 0,
  total_count: 2,
  graphs: [
    {
      graph_id: "fire_arrow", group_label_zh: "火", root_keys: ["fire_arrow"],
      owned_count: 1, total_count: 2, consumed: false,
      nodes: [
        { skill_key: "fire_arrow", display_name_zh: "火焰箭", owned: true, usable: true, ready: false, level: 1, xp_into_level: 23, xp_to_next_level: 27, capped: false, prereq_text_zh: "", depth: 0 },
        { skill_key: "scorching_wave", display_name_zh: "灼熱波動", owned: false, usable: false, ready: false, level: 0, xp_into_level: 0, xp_to_next_level: 50, capped: false, prereq_text_zh: "需「火球術 Lv.3」", depth: 1 },
      ],
      edges: [{ from_key: "fire_arrow", to_key: "scorching_wave", min_level: 3 }],
    },
    {
      graph_id: "wind_lance", group_label_zh: "風", root_keys: ["wind_lance"],
      owned_count: 1, total_count: 1, consumed: false,
      nodes: [
        { skill_key: "wind_lance", display_name_zh: "風之槍", owned: true, usable: true, ready: false, level: 1, xp_into_level: 23, xp_to_next_level: 27, capped: false, prereq_text_zh: "", depth: 0 },
      ],
      edges: [],
    },
  ],
};

export const ProgressAndPrerequisites = { render: renderLineage, args: { lineage } };
export const Empty = { render: renderLineage, args: { lineage: { ...lineage, completed_count: 0, total_count: 0, graphs: [] } } };
export const Unavailable = {
  render: renderLineage,
  args: { lineage: { available: false, reason: { message: "技能系譜目前無法顯示" } } },
};

// Two graphs sharing one element label (webclient-contextual-hud): each row
// carries its supplied root-node name beside the label, and its owned/total
// count sits right after that identity.
const sameElement = {
  ...lineage,
  completed_count: 1,
  total_count: 4,
  graphs: [
    ...lineage.graphs,
    {
      graph_id: "fire_bolt", group_label_zh: "火", root_keys: ["fire_bolt"],
      owned_count: 1, total_count: 1, consumed: false,
      nodes: [
        { skill_key: "fire_bolt", display_name_zh: "火球術", owned: true, usable: true, ready: false, level: 3, xp_into_level: 40, xp_to_next_level: 10, capped: false, prereq_text_zh: "", depth: 0 },
      ],
      edges: [],
    },
    {
      graph_id: "blade_dance", group_label_zh: "劍舞流", root_keys: ["blade_dance"],
      owned_count: 1, total_count: 1, consumed: true,
      nodes: [
        { skill_key: "blade_dance", display_name_zh: "迴旋斬", owned: true, usable: true, ready: false, level: 5, xp_into_level: 0, xp_to_next_level: 0, capped: true, prereq_text_zh: "", depth: 0 },
      ],
      edges: [],
    },
  ],
};
export const SameElementGraphs = { render: renderLineage, args: { lineage: sameElement } };
