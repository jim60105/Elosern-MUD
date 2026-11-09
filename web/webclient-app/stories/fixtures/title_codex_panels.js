// Synthetic title_codex v1 panels for the handbook titles tab stories and
// tests (handbook-titles-tab). Every key, display, basis, hint and flavor is invented test data:
// no shipped title appears here.
export function fixedRow(overrides = {}) {
  return {
    key: "t_alpha",
    display: "甲稱號",
    category: "combat",
    hint: "",
    flavor: "甲稱號的合成風味。",
    unlocked: true,
    granted_tick: 10,
    ...overrides,
  };
}

export function epithetRow(overrides = {}) {
  return {
    display: "合成異名甲",
    basis: "合成事蹟甲。",
    granted_tick: 11,
    equipped: false,
    can_remove: true,
    ...overrides,
  };
}

export function titleCodex(overrides = {}) {
  return {
    schema_version: 1,
    available: true,
    kind: "title_codex",
    fixed_rows: [
      fixedRow(),
      fixedRow({ key: "t_beta", display: "乙稱號", unlocked: false, flavor: "", hint: "完成合成條件乙。", granted_tick: 0 }),
      fixedRow({ key: "t_gamma", display: "丙稱號", unlocked: false, flavor: "", hint: "完成合成條件丙。", granted_tick: 0 }),
      fixedRow({ key: "g_x_rank", display: "合成公會甲", category: "guild", flavor: "合成公會風味。" }),
      fixedRow({ key: "t_guild_odd", display: "合成公會乙", category: "guild", unlocked: false, flavor: "", hint: "合成公會條件。", granted_tick: 0 }),
    ],
    epithet_rows: [
      epithetRow(),
      epithetRow({ display: "合成異名乙", basis: "合成事蹟乙。", equipped: true, can_remove: false }),
    ],
    equipped: { fixed: "t_alpha", epithet: "合成異名乙" },
    full_title: "甲稱號　合成異名乙",
    unlocked: 2,
    total: 5,
    pending_ballot: [],
    ...overrides,
  };
}

export const BALLOT = [
  { display: "合成提名甲", basis: "合成提名事蹟甲。" },
  { display: "合成提名乙", basis: "合成提名事蹟乙。" },
];

export const UNAVAILABLE_CODEX = {
  schema_version: 1,
  available: false,
  reason: { code: "codex_unavailable", message: "合成的稱號冊不可用原因" },
};
