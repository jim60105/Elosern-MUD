// Story fixture slices: see stories/fixtures.js (facade) for the public surface.

// The committed `character` v7 payload for the same actor: all eight
// breakdown trait rows — gauges carry a non-null max with `effective == max`
// (the maximum the layers decompose), statics/counters carry a null max with
// `current == effective` — each with its server-computed `layers` in payload
// order; the adjustment-bearing equipment rows; an active disguise whose
// displayed values differ from the true traits; guild rank/merit; wallet;
// persona; and the populated intimate status. The exposure row carries the
// EFFECTIVE ordinal 「中等」: the worn 修女聖袍 biases the stored base 「低」
// upward, and the stored base is NEVER carried on the wire (P6 read-model
// contract — the component test asserts the effective ordinal renders and
// the stored-base word is absent). Values mirror the Python panel contract
// test's serialized sample (web/webclient/presentation/tests/
// test_character_panel.py); reviewers diff both when either changes.
export const CHARACTER_PANEL_SAMPLE = {
  schema_version: 7,
  available: true,
  kind: "character",
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
  actives: [
    {
      category: "elemental_magic",
      label: "元素魔法",
      groups: [
        {
          group: "fire",
          label: "火",
          skills: [{ key: "firebolt", label: "火矢" }, { key: "fireball", label: "火球" }],
        },
        {
          group: "water",
          label: "水",
          skills: [{ key: "mend_glow", label: "微光治癒" }],
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
          skills: [{ key: "basic_attack", label: "基本攻擊" }, { key: "light_blade", label: "輕劍式" }],
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
    { slot: "weapon_main", item_key: "short_sword_lost", display_name: "短劍 · 拾遺", adjustment: "" },
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
   persona: {
     background: "渡口成長起來的灰誓成員，習慣在黃昏開張前巡完整條街。",
     personality: "沉穩寡言，對生人保持距離。",
     life_story: "在渡口碼頭長大，十六歲跟著商隊上了路。",
     habit: "清晨練劍，黃昏沿著主街巡一圈。",
   },
   intimate: {
     arousal: "中等",
     wetness: "微濕",
     shame: "輕微",
    exposure: "中等",
     climax_phase: "未達",
     climax_today: 2,
   },
 };

// The same actor without a disguise, no guild, no persona background — the
// honest empty-state story (displayed list must be empty, rank → 未加入公會,
// persona renders nothing).
export const CHARACTER_PANEL_TITLED_SAMPLE = {
  ...CHARACTER_PANEL_SAMPLE,
  full_title: "F級冒險者　南門新客",
};
export const CHARACTER_PANEL_UNDISGUISED_SAMPLE = {
  ...CHARACTER_PANEL_SAMPLE,
  // The honest empty state: no worn breakdown source, so every layer list
  // is empty (the traits keep their true totals without decomposition).
  traits: CHARACTER_PANEL_SAMPLE.traits.map((row) => ({ ...row, layers: [] })),
  equipment: [
    { slot: "weapon_main", item_key: "short_sword_lost", display_name: "短劍 · 拾遺", adjustment: "" },
  ],
  disguise: { active: false, description: "", displayed: [] },
  guild: { rank: null, merit: 0 },
  wallet: 0,
  persona: { background: null, personality: null, life_story: null, habit: null },
  intimate: null,
};