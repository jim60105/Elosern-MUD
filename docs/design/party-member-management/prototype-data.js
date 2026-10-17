// Approved visual prototype of the party window, shop, and navigation
// (docs/superpowers/specs/2026-10-18-party-member-management-ui-design.md).
// Reference only: self-contained mock data, not wired to any payload.
// Shapes follow the design's proposed panels: party v3 summaries,
// party_member, character v6, party_inventory, the item holdings query,
// the structured shop rows, and lineage v2 graphs.

export const PURSE = 1240;
export const GENERAL_QUOTA = { used: 2, limit: 3 };

// party v3 summary rows; the commander is always row 0.
export const MEMBERS = [
  { id: 1, name: "莉瑟", initial: "莉", art: "/art/defaults/woman.webp", title: "流浪劍士", hp: [96, 120], mp: [16, 40], sp: [42, 60], knocked_out: false, unread: false, commander: true },
  { id: 2, name: "艾拉", initial: "艾", art: "/art/defaults/girl.webp", title: "月下的見習祭司", hp: [44, 80], mp: [106, 120], sp: [35, 50], knocked_out: false, unread: true, commander: false },
  { id: 3, name: "卡恩", initial: "卡", art: "/art/defaults/man.webp", title: "沉默的傭兵", hp: [0, 140], mp: [4, 20], sp: [12, 80], knocked_out: true, unread: false, commander: false },
];

// party_member detail.
export const MEMBER_DETAIL = {
  1: {
    persona: [
      { label: "個性", text: "話少但心軟，對弱者沒有辦法視而不見。" },
      { label: "生平", text: "北境邊村的鐵匠之女，為了尋找失蹤的兄長而踏上旅途。" },
      { label: "習慣", text: "總是穿著洗舊的旅行斗篷，睡前會擦拭長劍。" },
      { label: "背景", text: "在阿爾托利亞的公會打聽兄長最後的委託紀錄。" },
    ],
    intimate: [
      { label: "敏感度", value: "Lv 2" },
      { label: "今日高潮", value: "0 次" },
      { label: "狀態", value: "平靜" },
    ],
  },
  2: {
    bond: { stage: "信賴", step: 3, steps: 5 },
    membership: { general: true, commissions: ["護送商隊 ‧ 護衛"] },
    intimate: [
      { label: "敏感度", value: "Lv 3" },
      { label: "今日高潮", value: "1 次" },
      { label: "狀態", value: "微醺" },
    ],
    possessed: false,
  },
  3: {
    bond: { stage: "熟識", step: 2, steps: 5 },
    membership: { general: true, commissions: [] },
    intimate: [
      { label: "敏感度", value: "Lv 1" },
      { label: "今日高潮", value: "0 次" },
      { label: "狀態", value: "昏迷" },
    ],
    possessed: false,
  },
};

export const INVITE = { target: "旅店女侍 蜜拉", enabled: false, reason: "蜜拉的好感還不足以同行。" };

// Item registry presentation (kind, icon, rarity, summary).
export const ITEMS = {
  potion_heal: { name: "治療藥水", kind: "消耗品", icon: "potion", rarity: "common", summary: "恢復 40 點 HP。" },
  potion_mana: { name: "魔力藥水", kind: "消耗品", icon: "potion", rarity: "common", summary: "恢復 30 點 MP。" },
  ration: { name: "乾糧", kind: "消耗品", icon: "ration", rarity: "common", summary: "旅途中的簡單一餐。" },
  steel_shortsword: { name: "鋼製短劍", kind: "武器", slot: "主手", icon: "sword", rarity: "uncommon", summary: "攻擊 +6，傷害倍率 ×1.15。" },
  iron_longsword: { name: "鐵製長劍", kind: "武器", slot: "主手", icon: "sword", rarity: "common", summary: "攻擊 +4，傷害倍率 ×1.10。" },
  warhammer: { name: "戰錘", kind: "武器", slot: "主手", icon: "hammer", rarity: "rare", summary: "攻擊 +10，傷害倍率 ×1.25，敏捷 −2。" },
  shortbow: { name: "短弓", kind: "武器", slot: "主手", icon: "bow", rarity: "common", summary: "攻擊 +3。" },
  oak_shield: { name: "橡木圓盾", kind: "盾牌", slot: "副手", icon: "shield", rarity: "common", summary: "防禦 +3。" },
  leather_armor: { name: "皮革胸甲", kind: "盔甲", slot: "盔甲", icon: "armor", rarity: "common", summary: "防禦 +4。" },
  linen_robe: { name: "亞麻長袍", kind: "盔甲", slot: "盔甲", icon: "armor", rarity: "common", summary: "防禦 +4，MP 上限 +10。" },
  birch_staff: { name: "樺木法杖", kind: "武器", slot: "主手", icon: "staff", rarity: "common", summary: "魔力 +4。" },
  moonstone: { name: "月石墜", kind: "飾品", slot: "飾品", icon: "amulet", rarity: "uncommon", summary: "魔力 +2。" },
  ward_charm: { name: "守護護符", kind: "飾品", slot: "飾品", icon: "amulet", rarity: "common", summary: "防禦 +1。" },
  herb_notes: { name: "草藥筆記", kind: "雜物", icon: "scroll", rarity: "common", summary: "艾拉的手抄筆記，無法出售。" },
  rusty_sword: { name: "生鏽短劍", kind: "武器", slot: "主手", icon: "sword", rarity: "common", summary: "攻擊 +1。從盜賊身上撿來的。" },
  torn_leather: { name: "破損皮甲", kind: "盔甲", slot: "盔甲", icon: "armor", rarity: "common", summary: "防禦 +1。" },
  moon_herb: { name: "月光草", kind: "素材", icon: "herb", rarity: "common", summary: "夜間採集的藥草。" },
};

// party_inventory per member: equipment doll plus bag rows.
export const INVENTORY = {
  1: {
    equipment: { 主手: "iron_longsword", 副手: "oak_shield", 盔甲: "leather_armor", 飾品: [] },
    bag: [
      ["potion_heal", 6], ["potion_mana", 2], ["steel_shortsword", 1],
      ["iron_longsword", 1], ["oak_shield", 1], ["leather_armor", 1], ["ward_charm", 1], ["ration", 4],
    ],
  },
  2: {
    equipment: { 主手: "birch_staff", 副手: null, 盔甲: "linen_robe", 飾品: ["moonstone"] },
    bag: [["potion_mana", 3], ["birch_staff", 1], ["linen_robe", 1], ["moonstone", 1], ["herb_notes", 1], ["moon_herb", 5]],
  },
  3: {
    equipment: { 主手: "warhammer", 副手: null, 盔甲: "torn_leather", 飾品: [] },
    bag: [["potion_heal", 1], ["warhammer", 1], ["torn_leather", 1], ["rusty_sword", 2], ["ration", 2]],
  },
};

export const ACCESSORY_SLOTS = 5;

// Item holdings query: per-member stat delta against the current slot
// occupant (server-computed; equipment only).
export const DELTAS = {
  steel_shortsword: { 1: "攻擊 +2", 2: "攻擊 +6", 3: "攻擊 −4" },
  iron_longsword: { 1: "±0", 2: "攻擊 +4", 3: "攻擊 −6" },
  warhammer: { 1: "攻擊 +6", 2: "無法裝備", 3: "±0" },
  shortbow: { 1: "攻擊 −1", 2: "攻擊 +3", 3: "攻擊 −7" },
  rusty_sword: { 1: "攻擊 −3", 2: "攻擊 +1", 3: "攻擊 −9" },
  torn_leather: { 1: "防禦 −3", 2: "防禦 −3", 3: "±0" },
};

// character v6 for each member: traits with breakdown layers, conditions,
// disguise, guild.
export const CHARACTER = {
  1: {
    guild: { rank: "E", merit: 140 },
    traits: [
      { key: "atk_phys", label: "物理攻擊", base: 12, effective: 16, layers: [{ source: "equipment", name: "鐵製長劍", kind: "flat", amount: 4 }] },
      { key: "agility", label: "敏捷", base: 10, effective: 10, layers: [] },
      { key: "defense", label: "防禦", base: 6, effective: 13, layers: [{ source: "equipment", name: "橡木圓盾", kind: "flat", amount: 3 }, { source: "equipment", name: "皮革胸甲", kind: "flat", amount: 4 }] },
      { key: "magic_power", label: "魔力", base: 4, effective: 4, layers: [] },
    ],
    conditions: [],
    disguise: null,
  },
  2: {
    guild: { rank: "F", merit: 20 },
    traits: [
      { key: "atk_phys", label: "物理攻擊", base: 6, effective: 6, layers: [] },
      { key: "agility", label: "敏捷", base: 12, effective: 10, layers: [{ source: "condition", name: "輕微疲勞", kind: "flat", amount: -2 }] },
      { key: "defense", label: "防禦", base: 5, effective: 9, layers: [{ source: "equipment", name: "亞麻長袍", kind: "flat", amount: 4 }] },
      { key: "magic_power", label: "魔力", base: 18, effective: 27, layers: [
        { source: "equipment", name: "樺木法杖", kind: "flat", amount: 4 },
        { source: "equipment", name: "月石墜", kind: "flat", amount: 2 },
        { source: "skill", name: "冥想", kind: "flat", amount: 1 },
        { source: "condition", name: "月之祝福", kind: "pct", amount: 15 },
      ] },
    ],
    conditions: [
      { code: "moon_blessing", label: "月之祝福", severity: "buff", remaining: "2 小時", modifiers: "魔力 +15%", source: "祭壇祈禱" },
      { code: "fatigue", label: "輕微疲勞", severity: "debuff", remaining: "40 分", modifiers: "敏捷 −2", source: "連續行軍" },
    ],
    disguise: { description: "旅行的藥草師", displayed: [["魔力", 12], ["物理攻擊", 8]] },
  },
  3: {
    guild: { rank: null, merit: 0 },
    traits: [
      { key: "atk_phys", label: "物理攻擊", base: 18, effective: 28, layers: [{ source: "equipment", name: "戰錘", kind: "flat", amount: 10 }] },
      { key: "agility", label: "敏捷", base: 8, effective: 6, layers: [{ source: "equipment", name: "戰錘", kind: "flat", amount: -2 }] },
      { key: "defense", label: "防禦", base: 10, effective: 11, layers: [{ source: "equipment", name: "破損皮甲", kind: "flat", amount: 1 }] },
      { key: "magic_power", label: "魔力", base: 2, effective: 2, layers: [] },
    ],
    conditions: [{ code: "knocked_out", label: "倒地", severity: "debuff", remaining: null, modifiers: "無法行動", source: "戰鬥" }],
    disguise: null,
  },
};

// character v6 skill groups for each member. `scales` is the freeform
// 威力 ladder (progression.yaml freeform_cast_scales: 1/4, 1/2, 1, 2, 4),
// present only when the member owns the element's mastery; a rung with
// `level` is still locked behind that skill's own proficiency.
export const SKILLS = {
  1: {
    active: [
      { category: "劍術", skills: [
        { key: "slash", name: "斬擊", icon: "sword", level: 3, progress: 0.4, target: "單體敵方", cost: "SP 6", field: false, scales: null, path: ["—", "斬擊", "雙重斬"] },
        { key: "guard_break", name: "破防擊", icon: "sword", level: 1, progress: 0.15, target: "單體敵方", cost: "SP 10", field: false, scales: null, path: ["斬擊", "破防擊", "—"], fresh: false },
      ] },
    ],
    passive: [{ category: "體能", skills: [{ key: "endurance", name: "耐力", icon: "skills", level: 2, progress: 0.5, target: "—", cost: "—", field: false, scales: null, path: ["—", "耐力", "—"] }] }],
  },
  2: {
    active: [
      { category: "神聖 ‧ 治療", skills: [
        { key: "healing_light", name: "治癒之光", icon: "holy", level: 2, progress: 0.62, target: "單體友方", cost: "MP 8", field: true, scales: null, path: ["祈禱", "治癒之光", "聖光庇護"] },
        { key: "mass_heal", name: "群體治癒", icon: "holy", level: 1, progress: 0.02, target: "全體友方", cost: "MP 20", field: true, scales: null, path: ["治癒之光", "群體治癒", "—"], fresh: true },
      ] },
      { category: "冰 ‧ 魔法", skills: [
        { key: "ice_shard", name: "冰錐術", icon: "ice", level: 2, progress: 0.3, target: "單體敵方", cost: "MP 6", field: false, scales: [{ label: "1/4", mp: 2 }, { label: "1/2", mp: 3 }, { label: "1", mp: 6 }, { label: "2", mp: 12, level: 6 }, { label: "4", mp: 24, level: 10 }], path: ["—", "冰錐術", "冰槍"] },
        { key: "frost_touch", name: "寒霜之觸", icon: "ice", level: 3, progress: 1, capped: true, target: "單體敵方", cost: "MP 4", field: false, scales: null, path: ["—", "寒霜之觸", "冰霜護甲"] },
      ] },
    ],
    passive: [{ category: "冥想", skills: [{ key: "meditation", name: "冥想", icon: "skills", level: 1, progress: 0.7, target: "—", cost: "—", field: false, scales: null, path: ["—", "冥想", "—"] }] }],
  },
  3: {
    active: [{ category: "錘術", skills: [{ key: "crush", name: "粉碎", icon: "hammer", level: 2, progress: 0.8, target: "單體敵方", cost: "SP 12", field: false, scales: null, path: ["—", "粉碎", "震地"] }] }],
    passive: [],
  },
};

// lineage v2: connected skill graphs with unique nodes and leveled edges.
// state: "capped" | "owned" | "locked"; depth/col place the node.
export const LINEAGE = {
  2: [
    {
      id: "ice", group: "冰", element: "ice", roots: ["寒霜之觸", "冰錐術"],
      nodes: [
        { key: "frost_touch", name: "寒霜之觸", state: "capped", level: 3, progress: 1, depth: 0, col: 0 },
        { key: "ice_shard", name: "冰錐術", state: "owned", level: 2, progress: 0.3, depth: 0, col: 1 },
        { key: "frost_armor", name: "冰霜護甲", state: "owned", level: 1, progress: 0.08, depth: 1, col: 0, current: true },
        { key: "ice_lance", name: "冰槍", state: "locked", prereq: "冰錐術 Lv 3", depth: 1, col: 1 },
        { key: "ice_storm", name: "冰晶風暴", state: "locked", prereq: "冰霜護甲 Lv 2 ‧ 冰槍 Lv 2", depth: 2, col: 0.5 },
        { key: "absolute_zero", name: "絕對零度", state: "locked", prereq: "冰晶風暴 Lv 2", depth: 3, col: 0.5 },
      ],
      edges: [
        ["frost_touch", "frost_armor", 2], ["ice_shard", "ice_lance", 3],
        ["frost_armor", "ice_storm", 2], ["ice_lance", "ice_storm", 2], ["ice_storm", "absolute_zero", 2],
      ],
    },
    {
      id: "holy_prayer", group: "神聖", element: "holy", roots: ["祈禱"],
      nodes: [
        { key: "prayer", name: "祈禱", state: "owned", level: 2, progress: 0.9, depth: 0, col: 0 },
        { key: "healing_light", name: "治癒之光", state: "owned", level: 2, progress: 0.62, depth: 1, col: 0 },
        { key: "sanctuary", name: "聖光庇護", state: "locked", prereq: "治癒之光 Lv 3", depth: 2, col: 0 },
      ],
      edges: [["prayer", "healing_light", 1], ["healing_light", "sanctuary", 3]],
    },
    {
      id: "holy_water", group: "神聖", element: "holy", roots: ["聖水祝福"],
      nodes: [{ key: "holy_water", name: "聖水祝福", state: "capped", level: 3, progress: 1, depth: 0, col: 0 }],
      edges: [],
    },
    {
      id: "wind", group: "風", element: "wind", roots: ["風之槍"],
      nodes: [
        { key: "wind_lance", name: "風之槍", state: "owned", level: 1, progress: 0.46, depth: 0, col: 0 },
        { key: "gale_lance", name: "疾風連槍", state: "locked", prereq: "風之槍 Lv 3", depth: 1, col: 0 },
      ],
      edges: [["wind_lance", "gale_lance", 3]],
    },
    {
      id: "staff_strike", group: "杖術", element: "staff", roots: ["敲擊"],
      nodes: [{ key: "strike", name: "敲擊", state: "owned", level: 1, progress: 0.2, depth: 0, col: 0 }],
      edges: [],
    },
    {
      id: "staff_spin", group: "杖術", element: "staff", roots: ["迴旋杖", "突刺"],
      nodes: [
        { key: "spin", name: "迴旋杖", state: "locked", prereq: "敲擊 Lv 2", depth: 0, col: 0 },
        { key: "thrust", name: "突刺", state: "locked", prereq: "敲擊 Lv 2", depth: 0, col: 1 },
        { key: "whirl_thrust", name: "旋突", state: "locked", prereq: "迴旋杖 Lv 2 ‧ 突刺 Lv 2", depth: 1, col: 0.5 },
      ],
      edges: [["spin", "whirl_thrust", 2], ["thrust", "whirl_thrust", 2]],
    },
  ],
  1: [
    {
      id: "sword", group: "劍術", element: "staff", roots: ["斬擊"],
      nodes: [
        { key: "slash", name: "斬擊", state: "owned", level: 3, progress: 0.4, depth: 0, col: 0.5 },
        { key: "guard_break", name: "破防擊", state: "owned", level: 1, progress: 0.15, depth: 1, col: 0 },
        { key: "double_slash", name: "雙重斬", state: "locked", prereq: "", depth: 1, col: 1 },
      ],
      edges: [["slash", "guard_break", 1], ["slash", "double_slash", 3]],
    },
  ],
  3: [
    {
      id: "hammer", group: "錘術", element: "staff", roots: ["粉碎"],
      nodes: [
        { key: "crush", name: "粉碎", state: "owned", level: 2, progress: 0.8, depth: 0, col: 0 },
        { key: "quake", name: "震地", state: "locked", prereq: "粉碎 Lv 3", depth: 1, col: 0 },
      ],
      edges: [["crush", "quake", 3]],
    },
  ],
};

// Structured shop rows (single-kind merchant, at most 12 rows).
export const SHOP = {
  name: "鐵匠鋪",
  host: "哈格的鍛爐",
  open: true,
  stock: [
    { item: "steel_shortsword", buy: 320, stock: 3, max: 5 },
    { item: "iron_longsword", buy: 280, stock: 2, max: 4 },
    { item: "warhammer", buy: 540, stock: 1, max: 2 },
    { item: "shortbow", buy: 260, stock: 0, max: 3 },
  ],
};
