// Story fixture slices: the party window's 系譜 tab (webclient-party-lineage-tab).
//
// The committed `lineage` v2 payload for the companion 蕾娜 (member 101 of
// PARTY_WINDOW_PANEL_SAMPLE), shaped like the approved prototype's ledger
// (docs/design/party-member-management/prototype-data.js LINEAGE[2]). Every
// owned node is a skill of CHARACTER_SKILL_COMPANION_SAMPLE, so selecting it
// lands on a real row of the 技能 tab:
//   * 水 — a seven-node graph with two roots (寒霜之觸 capped, 冰錐術 owned),
//     a ready 冰霜護甲, a locked 冰槍, the merge node 冰晶風暴 requiring
//     冰霜護甲 Lv 2 and 冰槍 Lv 2, and two leaves under it;
//   * 神聖 — two graphs in one group: the four-node 祈禱 line and the
//     single-node, fully capped 聖水祝福 (the one consumed graph);
//   * 杖術 — a three-node graph whose 迴旋杖 is ready to unlock.
// The growth facts are the server's: `xp_to_next_level` is what remains of
// the node's level band, and the counts describe the full view.

function node(skill_key, display_name_zh, depth, facts = {}) {
  const owned = Boolean(facts.owned);
  const capped = Boolean(facts.capped);
  return {
    skill_key,
    display_name_zh,
    owned,
    usable: owned,
    ready: Boolean(facts.ready),
    level: facts.level ?? 0,
    xp_into_level: facts.into ?? 0,
    xp_to_next_level: capped ? 0 : (facts.toNext ?? 50),
    capped,
    prereq_text_zh: facts.prereq ?? "",
    depth,
  };
}

const edge = (from_key, to_key, min_level) => ({ from_key, to_key, min_level });

export const LINEAGE_ICE_GRAPH = {
  graph_id: "frost_touch",
  group_label_zh: "水",
  root_keys: ["frost_touch", "ice_shard"],
  owned_count: 2,
  total_count: 7,
  consumed: false,
  nodes: [
    node("frost_touch", "寒霜之觸", 0, { owned: true, capped: true, level: 10 }),
    node("ice_shard", "冰錐術", 0, { owned: true, level: 2, into: 18, toNext: 42 }),
    node("frost_armor", "冰霜護甲", 1, { ready: true }),
    node("ice_lance", "冰槍", 1, { prereq: "需「冰錐術 Lv.3」" }),
    node("ice_storm", "冰晶風暴", 2, { prereq: "需「冰霜護甲 Lv.2」「冰槍 Lv.2」" }),
    node("absolute_zero", "絕對零度", 3, { prereq: "需「冰晶風暴 Lv.2」" }),
    node("ice_mirror", "冰晶鏡", 3, { prereq: "需「冰晶風暴 Lv.3」" }),
  ],
  edges: [
    edge("frost_touch", "frost_armor", 2),
    edge("ice_shard", "ice_lance", 3),
    edge("frost_armor", "ice_storm", 2),
    edge("ice_lance", "ice_storm", 2),
    edge("ice_storm", "absolute_zero", 2),
    edge("ice_storm", "ice_mirror", 3),
  ],
};

export const LINEAGE_PRAYER_GRAPH = {
  graph_id: "prayer",
  group_label_zh: "神聖",
  root_keys: ["prayer"],
  owned_count: 3,
  total_count: 4,
  consumed: false,
  nodes: [
    node("prayer", "祈禱", 0, { owned: true, level: 4, into: 12, toNext: 68 }),
    node("healing_light", "治癒之光", 1, { owned: true, level: 2, into: 31, toNext: 19 }),
    node("mass_heal", "群體治癒", 2, { owned: true, level: 1, into: 1, toNext: 59 }),
    node("sanctuary", "聖光庇護", 2, { prereq: "需「治癒之光 Lv.3」" }),
  ],
  edges: [edge("prayer", "healing_light", 1), edge("healing_light", "mass_heal", 2), edge("healing_light", "sanctuary", 3)],
};

export const LINEAGE_HOLY_WATER_GRAPH = {
  graph_id: "holy_water",
  group_label_zh: "神聖",
  root_keys: ["holy_water"],
  owned_count: 1,
  total_count: 1,
  consumed: true,
  nodes: [node("holy_water", "聖水祝福", 0, { owned: true, capped: true, level: 3 })],
  edges: [],
};

export const LINEAGE_STAFF_GRAPH = {
  graph_id: "staff_strike",
  group_label_zh: "杖術",
  root_keys: ["staff_strike"],
  owned_count: 1,
  total_count: 3,
  consumed: false,
  nodes: [
    node("staff_strike", "杖擊", 0, { owned: true, level: 2, into: 4.5, toNext: 35.5 }),
    node("staff_spin", "迴旋杖", 1, { ready: true }),
    node("staff_thrust", "突刺", 1, { prereq: "需「杖擊 Lv.3」" }),
  ],
  edges: [edge("staff_strike", "staff_spin", 2), edge("staff_strike", "staff_thrust", 3)],
};

export const LINEAGE_COMPANION_SAMPLE = {
  schema_version: 2,
  available: true,
  kind: "lineage",
  completed_count: 1,
  total_count: 4,
  graphs: [LINEAGE_ICE_GRAPH, LINEAGE_PRAYER_GRAPH, LINEAGE_HOLY_WATER_GRAPH, LINEAGE_STAFF_GRAPH],
};

export const LINEAGE_EMPTY_SAMPLE = { ...LINEAGE_COMPANION_SAMPLE, completed_count: 0, total_count: 0, graphs: [] };

export const LINEAGE_UNAVAILABLE_SAMPLE = {
  schema_version: 2,
  available: false,
  reason: { code: "lineage_unavailable", message: "技能系譜目前無法顯示" },
};
