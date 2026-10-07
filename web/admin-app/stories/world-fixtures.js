// Synthetic authored world-data payloads (gm-portal-s4-world-data) shared by
// the stories and the Vitest suites. Names are fixture-only (``t_*``), never
// shipped registry keys.

export const WORLD_INVENTORY = {
  groups: ["世界", "生物", "物品與經濟", "聚落", "人物", "技能", "任務", "規則書"],
  items: [
    { name: "t_hollows", label: "合成窪地", group: "世界", entry_count: 2, source_path: "fixtures/t_hollows.py", summary_fields: ["display_name_zh"] },
    { name: "t_realms", label: "合成國度", group: "世界", entry_count: 0, source_path: "fixtures/t_realms.py", summary_fields: [] },
    { name: "t_critters", label: "合成小獸", group: "生物", entry_count: 62, source_path: "fixtures/critters", summary_fields: ["display_name_zh", "home_key"] },
    { name: "t_trinkets", label: "合成飾品", group: "物品與經濟", entry_count: 1, source_path: "fixtures/t_trinkets.py", summary_fields: ["label_text"] },
  ],
};

export const WORLD_SOURCES = {
  items: [
    { name: "prompts/t_voice.yaml", group: "prompts", source_path: "prompts/t_voice.yaml", size_bytes: 40, reloadable: true },
    { name: "rulebook/t_rules.yaml", group: "rulebook", source_path: "world/rules/rulebook/t_rules.yaml", size_bytes: 30, reloadable: false },
    { name: "rulebook/commerce/t_rules.yaml", group: "commerce", source_path: "world/rules/rulebook/commerce/t_rules.yaml", size_bytes: 20, reloadable: false },
  ],
};

export const WORLD_SEARCH = {
  items: [
    { registry: "t_critters", key: "t_marked" },
    { registry: "t_critters", key: "t_moonlit" },
    { registry: "t_trinkets", key: "t_trinket_moon" },
  ],
};

export const CRITTER_PAGE = {
  items: [
    {
      key: "t_critter_00",
      label: "小獸零號",
      summary: [
        { field: "display_name_zh", value: "小獸零號" },
        { field: "home_key", value: "t_hollow_east" },
      ],
    },
    {
      key: "t_marked",
      label: "斑紋獸",
      summary: [
        { field: "display_name_zh", value: "斑紋獸" },
        { field: "home_key", value: "t_hollow_west" },
      ],
    },
  ],
  next_cursor: "t_next",
  registry: WORLD_INVENTORY.items[2],
  q: "",
  total: 62,
};

export const MARKED_ENTRY = {
  registry: WORLD_INVENTORY.items[2],
  key: "t_marked",
  label: "斑紋獸",
  type: "Critter",
  fields: {
    key: "t_marked",
    display_name_zh: "斑紋獸",
    home_key: "t_hollow_west",
    roams: ["t_hollow_east", "t_hollow_west"],
    markings: [{ note: "銀色月光的紋路", hollow_key: "t_hollow_gone" }],
  },
  references: [
    { field_path: "home_key", registry: "t_hollows", registry_label: "合成窪地", key: "t_hollow_west", label: "西窪", exists: true, inverse: "residents" },
    { field_path: "roams[0]", registry: "t_hollows", registry_label: "合成窪地", key: "t_hollow_east", label: "東窪", exists: true, inverse: "roamers" },
    { field_path: "roams[1]", registry: "t_hollows", registry_label: "合成窪地", key: "t_hollow_west", label: "西窪", exists: true, inverse: "roamers" },
    { field_path: "markings[0].hollow_key", registry: "t_hollows", registry_label: "合成窪地", key: "t_hollow_gone", label: null, exists: false, inverse: "marked_by" },
  ],
  referrers: [
    {
      inverse: "rivals",
      items: [{ registry: "t_critters", registry_label: "合成小獸", key: "t_critter_03", label: "小獸三號", field_path: "rival_key" }],
    },
    {
      inverse: "trophies",
      items: Array.from({ length: 11 }, (_, index) => ({
        registry: "t_trinkets",
        registry_label: "合成飾品",
        key: `t_trinket_${String(index).padStart(2, "0")}`,
        label: `飾品 ${index}`,
        field_path: `trophies[${index}]`,
      })),
    },
  ],
};

export const RULE_SOURCE = {
  name: "rulebook/t_rules.yaml",
  group: "rulebook",
  source_path: "world/rules/rulebook/t_rules.yaml",
  size_bytes: 64,
  line_count: 5,
  reloadable: false,
  text: "# 合成規則書\nschema_version: 1\nrules:\n  t_rule:\n    weight: 3\n",
};

export const PROMPT_SOURCE = {
  name: "prompts/t_voice.yaml",
  group: "prompts",
  source_path: "prompts/t_voice.yaml",
  size_bytes: 72,
  line_count: 4,
  reloadable: true,
  text: "schema_version: 1\nprompts:\n  t_voice.system: |\n    你是合成的說書人。\n",
};

export const RELOAD_OK = { outcome: "ok", available: 12, total: 12, root: "prompts", unavailable: [] };

export const RELOAD_DEGRADED = {
  outcome: "degraded",
  available: 10,
  total: 12,
  root: "prompts",
  unavailable: [
    { key: "t_voice.system", file: "t_voice.yaml", problem: "prompt text is empty" },
    { key: "t_voice.user", file: "t_voice.yaml", problem: "unknown placeholder 't_name'; allowed: <none>" },
  ],
};
