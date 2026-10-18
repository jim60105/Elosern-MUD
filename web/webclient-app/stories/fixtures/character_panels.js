// Story fixture slices: see stories/fixtures.js (facade) for the public surface.

// One active row: identity plus the six v9 growth facts.
function activeRow(key, label, level = 1) {
  return {
    key,
    label,
    level,
    xp_into_level: 10,
    xp_to_next_level: 40,
    capped: false,
    fresh: false,
    booked: false,
  };
}

// The committed `character` v9 payload for the viewed member: all eight
// breakdown trait rows — gauges carry a non-null max with `effective == max`
// (the maximum the layers decompose), statics/counters carry a null max with
// `current == effective` — each with its server-computed `layers` in payload
// order; the adjustment-bearing equipment rows; an active disguise whose
// displayed values differ from the true traits; guild rank/merit; wallet; and
// the ordered condition rows. Persona prose and intimate state live on the
// `party_member` panel (PARTY_MEMBER_PANEL_SAMPLE). Values mirror the Python
// panel contract test's serialized sample (web/webclient/presentation/tests/
// test_character_panel/); reviewers diff both when either changes.
export const CHARACTER_PANEL_SAMPLE = {
  schema_version: 9,
  available: true,
  kind: "character",
  member_id: 42,
  traits: [
    {
      key: "hp",
      label: "生命",
      base: 390,
      current: 231,
      max: 405,
      effective: 405,
      layers: [{ source: "equipment", name: "騎士全套板甲", kind: "flat", amount: 15 }],
    },
    { key: "mp", label: "魔力", base: 420, current: 139, max: 420, effective: 420, layers: [] },
    { key: "sp", label: "耐力", base: 68, current: 68, max: 68, effective: 68, layers: [] },
    {
      key: "atk_phys",
      label: "攻擊",
      base: 20,
      current: 18,
      max: null,
      effective: 18,
      layers: [{ source: "equipment", name: "騎士全套板甲", kind: "flat", amount: -2 }],
    },
    {
      key: "agility",
      label: "敏捷",
      base: 20,
      current: 18,
      max: null,
      effective: 18,
      layers: [{ source: "equipment", name: "騎士全套板甲", kind: "pct", amount: -10 }],
    },
    // The 16-layer bound (CHARACTER_MAX_LAYERS): a full-width chip row that
    // must render every layer with wrapping and no truncation.
    {
      key: "defense",
      label: "防禦",
      base: 12,
      current: 48,
      max: null,
      effective: 48,
      layers: [
        { source: "equipment", name: "騎士全套板甲", kind: "flat", amount: 8 },
        { source: "equipment", name: "霧隱護符", kind: "flat", amount: 2 },
        { source: "skill", name: "防衛本能（2/3）", kind: "mult", amount: 1.5 },
        { source: "skill", name: "強化身體", kind: "flat", amount: 3 },
        { source: "skill", name: "鐵甲術（1/3）", kind: "pct", amount: 15 },
        { source: "skill", name: "穩步", kind: "flat", amount: 1 },
        { source: "condition", name: "護盾", kind: "flat", amount: 5 },
        { source: "condition", name: "高露出", kind: "pct", amount: -15 },
        { source: "condition", name: "失溫", kind: "flat", amount: -2 },
        { source: "condition", name: "專注", kind: "flat", amount: 1 },
        { source: "skill", name: "閃避姿勢", kind: "pct", amount: 10 },
        { source: "skill", name: "重甲適應", kind: "flat", amount: 4 },
        { source: "equipment", name: "迅捷護符", kind: "pct", amount: -5 },
        { source: "condition", name: "酒意", kind: "pct", amount: -5 },
        { source: "skill", name: "硬皮", kind: "mult", amount: 1.2 },
        { source: "condition", name: "再生", kind: "flat", amount: 1 },
      ],
    },
    { key: "magic_power", label: "魔力", base: 31, current: 31, max: null, effective: 31, layers: [] },
    { key: "guild_merit", label: "功績", base: 140, current: 140, max: null, effective: 140, layers: [] },
  ],
  conditions: [
    {
      code: "regen",
      label: "再生",
      severity: "beneficial",
      remaining_seconds: 30,
      modifiers: {},
      source: "狀態",
    },
    {
      code: "shame_exposure",
      label: "羞慾外露",
      severity: "warning",
      remaining_seconds: null,
      modifiers: { defense: -15, agility: "-10%" },
      source: "裝備、狀態",
    },
  ],
  actives: [
    {
      category: "elemental_magic",
      label: "元素魔法",
      groups: [
        {
          group: "fire",
          label: "火",
          skills: [activeRow("firebolt", "火矢"), activeRow("fireball", "火球", 2)],
        },
        {
          group: "water",
          label: "水",
          skills: [activeRow("mend_glow", "微光治癒")],
        },
      ],
    },
    {
      category: "martial_arts",
      label: "武技",
      groups: [
        {
          group: null,
          label: null,
          skills: [activeRow("basic_attack", "基本攻擊"), activeRow("light_blade", "輕劍式")],
        },
      ],
    },
  ],
  passives: [
    {
      category: "enhancement",
      label: "強化",
      groups: [
        {
          group: null,
          label: null,
          skills: [
            { key: "hardened_body", label: "強化身體" },
            { key: "guard_instinct", label: "防衛本能" },
          ],
        },
      ],
    },
  ],
  equipment: [
    { slot: "weapon_main", item_key: "short_sword_lost", display_name: "短劍 ‧ 拾遺", adjustment: "" },
    {
      slot: "armor",
      item_key: "knight_platemail",
      display_name: "騎士全套板甲",
      adjustment: "攻擊 −2｜防禦 +8｜敏捷 −10%｜生命上限 +15",
    },
    // The worn bias-bearing item: its exposure bias raises the stored base
    // 「低」 to the effective 「中等」 rendered in the intimate section; the
    // bias itself is deliberately absent from the adjustment prose (the
    // server formatter never narrates exposure_bias).
    { slot: "accessory", item_key: "sister_vestments", display_name: "修女聖袍", adjustment: "治療 +10%" },
  ],
  disguise: {
    active: true,
    description: "目前以「旅商」身分示人；顯示值只影響外觀與鑑定。",
    displayed: [
      { key: "atk_phys", label: "攻擊", value: 25 },
      { key: "magic_power", label: "魔力", value: 12 },
    ],
  },
   guild: { rank: "E", merit: 140 },
   wallet: 3240,
  // The one 技能-tab selection: lineage position plus the full ladder (rungs
  // above the member's proficiency carry their unlock level, never a cost).
  selected_skill: {
    key: "fireball",
    lineage: {
      prerequisites: [{ key: "firebolt", label: "火矢", level: 1 }],
      next: [{ key: "firestorm", label: "火風暴", min_level: 3 }],
    },
    freeform_ladder: [
      { scale: 0.25, label: "1/4", mp_cost: 4 },
      { scale: 0.5, label: "1/2", mp_cost: 7 },
      { scale: 1, label: "1", mp_cost: 14 },
      { scale: 2, label: "2", unlock_level: 6 },
      { scale: 4, label: "4", unlock_level: 10 },
    ],
  },
 };

// The same member without a disguise and without a guild — the honest
// empty-state story (displayed list must be empty, rank → 未加入公會).
export const CHARACTER_PANEL_TITLED_SAMPLE = {
  ...CHARACTER_PANEL_SAMPLE,
  full_title: "F級冒險者　苔徑新客",
};
export const CHARACTER_PANEL_UNDISGUISED_SAMPLE = {
  ...CHARACTER_PANEL_SAMPLE,
  // The honest empty state: no worn breakdown source, so every layer list
  // is empty (the traits keep their true totals without decomposition).
  traits: CHARACTER_PANEL_SAMPLE.traits.map((row) => ({ ...row, layers: [] })),
  equipment: [
    { slot: "weapon_main", item_key: "short_sword_lost", display_name: "短劍 ‧ 拾遺", adjustment: "" },
  ],
  disguise: { active: false, description: "", displayed: [] },
  guild: { rank: null, merit: 0 },
  wallet: 0,
  conditions: [],
};