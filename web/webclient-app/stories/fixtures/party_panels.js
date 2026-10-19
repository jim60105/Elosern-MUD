// Story fixture slices: see stories/fixtures.js (facade) for the public surface.

import { fixtureDigest } from "./art_panels.js";

// ---------------------------------------------------------------------------
// webclient-align-05-party-hud: party panel fixtures.
// ---------------------------------------------------------------------------
// Version-3 rows: row 0 is the commander (the player's own row, with no bond
// stage or membership), then one row per companion. Every fixture companion is
// a general member; membership metadata and the separate general quota are part
// of the extended payload.
const companion = (row) => ({
  role: "companion",
  mp_current: 0,
  mp_maximum: 0,
  sp_current: 0,
  sp_maximum: 0,
  knocked_out: false,
  unread: false,
  ...row,
  membership: row.membership ?? { general: true, temporary_commissions: [] },
});
const commander = (row) => ({
  role: "commander",
  portrait_ref: null,
  knocked_out: false,
  unread: false,
  bond_stage: null,
  membership: null,
  ...row,
});
const COMMANDER_ROW = commander({
  identity: 42,
  display_name: "影行者",
  hp_current: 80,
  hp_maximum: 100,
  mp_current: 30,
  mp_maximum: 50,
  sp_current: 12,
  sp_maximum: 40,
});

export const PARTY_PANEL_EMPTY_SAMPLE = {
  schema_version: 3,
  available: true,
  general_quota: { used: 0, limit: 4 },
  viewed_member_id: COMMANDER_ROW.identity,
  slots: [COMMANDER_ROW],
};

export const PARTY_PANEL_SAMPLE = {
  schema_version: 3,
  available: true,
  general_quota: { used: 2, limit: 4 },
  viewed_member_id: 101,
  slots: [
    COMMANDER_ROW,
    companion({
      identity: 101,
      display_name: "蕾娜",
      portrait_ref: "101",
      hp_current: 180,
      hp_maximum: 220,
      mp_current: 60,
      mp_maximum: 80,
      sp_current: 24,
      sp_maximum: 40,
      bond_stage: "親睦",
    }),
    companion({
      identity: 102,
      display_name: "幽",
      portrait_ref: null,
      hp_current: 144,
      hp_maximum: 160,
      mp_current: 90,
      mp_maximum: 120,
      sp_current: 10,
      sp_maximum: 30,
      bond_stage: "信賴",
    }),
  ],
};

export const PARTY_PANEL_FULL_SAMPLE = {
  schema_version: 3,
  available: true,
  general_quota: { used: 4, limit: 4 },
  viewed_member_id: 102,
  slots: [
    COMMANDER_ROW,
    companion({
      identity: 101,
      display_name: "蕾娜",
      portrait_ref: "101",
      hp_current: 180,
      hp_maximum: 220,
      mp_current: 60,
      mp_maximum: 80,
      sp_current: 24,
      sp_maximum: 40,
      bond_stage: "親睦",
    }),
    companion({
      identity: 102,
      display_name: "幽",
      portrait_ref: null,
      hp_current: 144,
      hp_maximum: 160,
      mp_current: 90,
      mp_maximum: 120,
      sp_current: 10,
      sp_maximum: 30,
      bond_stage: "信賴",
      unread: true,
    }),
    companion({
      identity: 103,
      display_name: "艾德蒙",
      portrait_ref: null,
      hp_current: 250,
      hp_maximum: 250,
      mp_current: 40,
      mp_maximum: 60,
      sp_current: 30,
      sp_maximum: 50,
      bond_stage: "熟稔",
    }),
    companion({
      identity: 104,
      display_name: "雪莉",
      portrait_ref: null,
      hp_current: 95,
      hp_maximum: 110,
      mp_current: 70,
      mp_maximum: 100,
      sp_current: 18,
      sp_maximum: 30,
      bond_stage: "初識",
    }),
  ],
};

// Existing bundled fixture art only; production never constructs these refs.
// Each catalog value is exactly `{artwork, context}` — the complete canonical
// descriptor plus its bounded display context — and the descriptor carries the
// committed built-in silhouette as its own alpha terminal
// (builtin-silhouette-stage-fallback).
// The companion rows alone: row 0 is the commander's own row and is never a
// lineup figure, drawer companion or catalog subject.
export const PARTY_COMPANION_ROWS = PARTY_PANEL_FULL_SAMPLE.slots.filter(
  (row) => row.role === "companion",
);
export const COMPANION_PORTRAIT_CATALOG = Object.fromEntries(
  PARTY_COMPANION_ROWS.map((row, index) => {
    const key = ["woman", "elder", "man", "girl"][index];
    return [String(row.identity), {
      artwork: {
        subject_id: `portrait:character:t_companion_${index}`,
        revision: fixtureDigest(`companion-${index}`),
        generation_subject: `portrait:character:t_companion_${index}`,
        generation_state: "done",
        attempts: [{
          type: "image",
          source_id: `portrait.default:t_companion_${index}`,
          rank: 30,
          resource: {
            resource_id: `defaults/${key}.webp`,
            version: fixtureDigest(`companion-resource-${index}`),
            url: `/art/defaults/${key}.webp`,
            origin: "runtime",
            geometry: {
              image_size: null,
              face_rect: { x: 0.25, y: 0.06, w: 0.5, h: 0.5 },
              stage: { scale: 1, x: 0, y: 0 },
              aspect_ratio: "3:4",
            },
          },
        }],
        terminal: {
          kind: "alpha_mask",
          source_id: `portrait.alpha:${key}`,
          rank: 100,
          resource: {
            resource_id: `defaults/${key}.webp`,
            version: fixtureDigest(`companion-terminal-${index}`),
            url: `/art/defaults/${key}.webp`,
            origin: "silhouette",
            geometry: {
              image_size: null,
              face_rect: { x: 0.35, y: 0.03, w: 0.29, h: 0.16 },
              stage: null,
              aspect_ratio: "3:4",
            },
          },
        },
        retention_sources: [],
      },
      context: { name: row.display_name, role: "隊友" },
    }];
  }),
);

export const PARTY_COMBAT_PARTICIPANTS_SAMPLE = [
  { identity: 101, token: "a2", display_name: "蕾娜", team: "party", state: "active" },
  { identity: 102, token: "a3", display_name: "幽", team: "party", state: "active" },
];

export const PARTY_INTERACT_TARGETS_SAMPLE = [
  {
    identity: 201,
    display_name: "對話精靈",
    affordances: [
      {
        kind: "action",
        action_id: "explore.party_invite",
        label: "邀請",
        enabled: true,
        disabled_reason: null,
      },
    ],
  },
  {
    identity: 101,
    display_name: "蕾娜",
    affordances: [
      {
        kind: "action",
        action_id: "explore.party_leave",
        label: "解散",
        enabled: true,
        disabled_reason: null,
      },
    ],
  },
];

// The committed `party_member` v1 panel for the commander form: the four
// persona prose keys, the intimate level words, and the one server-authored
// persona-edit descriptor. `character` v8 no longer carries either section, so
// the character-status drawer reads them here.
export const PARTY_MEMBER_PANEL_SAMPLE = {
  schema_version: 1,
  available: true,
  kind: "party_member",
  member_id: 42,
  role: "commander",
  companion: null,
  commander: {
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
    actions: [
      {
        action_id: "character.persona.update",
        params: {},
        enabled: true,
        reason: null,
      },
    ],
  },
};
// ---------------------------------------------------------------------------
// webclient-party-window-member-tab: the party window's 成員 tab fixtures.
// ---------------------------------------------------------------------------
// A party of the commander, one general companion (蕾娜), one knocked-out
// general companion (幽) and one temporary escort (蓋文, outside the general
// quota). The general quota still has room, so the rail ends in 空位.
export const PARTY_WINDOW_PANEL_SAMPLE = {
  schema_version: 3,
  available: true,
  general_quota: { used: 2, limit: 4 },
  viewed_member_id: 101,
  slots: [
    COMMANDER_ROW,
    companion({
      identity: 101,
      display_name: "蕾娜",
      portrait_ref: "101",
      hp_current: 180,
      hp_maximum: 220,
      mp_current: 60,
      mp_maximum: 80,
      sp_current: 24,
      sp_maximum: 40,
      bond_stage: "親睦",
    }),
    companion({
      identity: 102,
      display_name: "幽",
      portrait_ref: null,
      hp_current: 0,
      hp_maximum: 160,
      mp_current: 90,
      mp_maximum: 120,
      sp_current: 10,
      sp_maximum: 30,
      bond_stage: "信賴",
      knocked_out: true,
      unread: true,
    }),
    companion({
      identity: 103,
      display_name: "蓋文",
      portrait_ref: null,
      hp_current: 120,
      hp_maximum: 120,
      mp_current: 20,
      mp_maximum: 20,
      sp_current: 30,
      sp_maximum: 30,
      bond_stage: "初識",
      membership: {
        general: false,
        temporary_commissions: [{ quest_id: "escort_caravan", role_id: "guard", label: "護送商隊 ‧ 護衛" }],
      },
    }),
  ],
};

const descriptor = (action_id, npc_id, reason = null) => ({
  action_id,
  params: npc_id === null ? {} : { npc_id },
  enabled: reason === null,
  reason,
});

const NO_INTIMATE = null;

// The viewed companion 蕾娜: every action enabled.
export const PARTY_MEMBER_COMPANION_SAMPLE = {
  schema_version: 1,
  available: true,
  kind: "party_member",
  member_id: 101,
  role: "companion",
  commander: null,
  companion: {
    bond: { stage: "親睦", step: 3, steps: 7 },
    membership: { general: true, temporary_commissions: [] },
    intimate: {
      arousal: "平靜",
      wetness: "乾燥",
      shame: "輕微",
      exposure: "極低",
      climax_phase: "未達",
      climax_today: 0,
    },
    actions: [
      descriptor("explore.possess", 101),
      descriptor("explore.party_leave", 101),
      descriptor("npc.persona.read", 101),
    ],
  },
};

// 蕾娜 while the player possesses her: the possession slot is the release.
export const PARTY_MEMBER_POSSESSED_SAMPLE = {
  ...PARTY_MEMBER_COMPANION_SAMPLE,
  companion: {
    ...PARTY_MEMBER_COMPANION_SAMPLE.companion,
    actions: [
      descriptor("explore.possess_release", 101),
      descriptor("explore.party_leave", 101, "請先解除附身，再請同伴離隊。"),
      descriptor("npc.persona.read", 101, "附身期間無法這麼做。"),
    ],
  },
};

// The knocked-out companion 幽: possession gated with its committed reason.
export const PARTY_MEMBER_KNOCKED_OUT_SAMPLE = {
  schema_version: 1,
  available: true,
  kind: "party_member",
  member_id: 102,
  role: "companion",
  commander: null,
  companion: {
    bond: { stage: "信賴", step: 4, steps: 7 },
    membership: { general: true, temporary_commissions: [] },
    intimate: NO_INTIMATE,
    actions: [
      descriptor("explore.possess", 102, "對方已失去意識，無法附身。"),
      descriptor("explore.party_leave", 102),
      descriptor("npc.persona.read", 102),
    ],
  },
};

// The temporary escort 蓋文: the leave descriptor carries the escort reason.
export const PARTY_MEMBER_ESCORT_SAMPLE = {
  schema_version: 1,
  available: true,
  kind: "party_member",
  member_id: 103,
  role: "companion",
  commander: null,
  companion: {
    bond: { stage: "初識", step: 1, steps: 7 },
    membership: {
      general: false,
      temporary_commissions: [{ quest_id: "escort_caravan", role_id: "guard", label: "護送商隊 ‧ 護衛" }],
    },
    intimate: NO_INTIMATE,
    actions: [
      descriptor("explore.possess", 103),
      descriptor("explore.party_leave", 103, "此同伴受委託護送中（escort_caravan），無法請其離隊。"),
      descriptor("npc.persona.read", 103),
    ],
  },
};

// The party purse (`party_inventory` v1 with an empty bag, for the header).
export const PARTY_INVENTORY_PURSE_SAMPLE = {
  schema_version: 1,
  available: true,
  kind: "party_inventory",
  member_id: 42,
  purse: 1240,
  equipment: { weapon_main: null, weapon_off: null, armor: null, accessories: [], accessory_limit: 5 },
  rows: [],
};

// The 空位's committed invite affordances: an innkeeper whose invite is gated.
export const PARTY_WINDOW_INVITE_DISABLED_TARGETS = [
  {
    identity: 301,
    display_name: "旅店老闆娘",
    affordances: [
      {
        kind: "action",
        action_id: "explore.party_invite",
        label: "邀請",
        enabled: false,
        disabled_reason: { code: "bond_too_low", message: "羈絆不足，對方不願同行。" },
      },
    ],
  },
];

// ---------------------------------------------------------------------------
// webclient-party-bag-tab: the party window's 背包 tab fixtures.
// ---------------------------------------------------------------------------
// The viewed companion 蕾娜 (101) wields an iron longsword, wears a
// traveller's robe and one silver ring, and carries potions, bread, herbs and
// a spare steel shortsword. Every descriptor is a committed server fact: an
// equipped row cannot be given (`item_equipped`), the full-MP potion's use is
// gated, and herbs have no use at all. Valid `party_inventory` v1.
const present = (kind, icon_key, rarity, summary) => ({ kind, icon_key, rarity, summary });
const fieldUse = (reason = null) => ({ route: "field_use", enabled: reason === null, reason });
const toggle = (reason = null) => ({ route: "toggle", enabled: reason === null, reason });
const give = (max_quantity, reason = null) => ({ enabled: reason === null, reason, max_quantity });
const EQUIPPED_GIVE_REASON = "已裝備的物品無法交換；請先卸下。";
export const TRANSFER_IN_COMBAT_REASON = "戰鬥中無法交換物品。";

const bagRow = (row) => ({ equipped_count: 0, slot: null, use: null, toggle: null, ...row });

export const PARTY_BAG_INVENTORY_SAMPLE = {
  schema_version: 1,
  available: true,
  kind: "party_inventory",
  member_id: 101,
  purse: 1240,
  equipment: {
    weapon_main: "iron_longsword",
    weapon_off: null,
    armor: "traveler_robe",
    accessories: ["silver_ring"],
    accessory_limit: 5,
  },
  rows: [
    bagRow({
      item_key: "potion_heal",
      display_name: "苦艾藥水",
      held: 5,
      presentation: present("potion", "potion", "common", "以苦艾與蜂蜜調成的紅色藥水，飲下後傷口會慢慢癒合。"),
      use: fieldUse(),
      give: give(5),
    }),
    bagRow({
      item_key: "potion_mana",
      display_name: "魔力藥水",
      held: 2,
      presentation: present("potion", "potion", "uncommon", "泛著藍光的清澈藥水，能讓疲憊的心神重新聚起魔力。"),
      use: fieldUse("魔力已經是滿的。"),
      give: give(2),
    }),
    bagRow({
      item_key: "rye_bread",
      display_name: "黑麥麵包",
      held: 3,
      presentation: present("food", "food", "common", "旅店烤的黑麥麵包，耐放又頂飽。"),
      use: fieldUse(),
      give: give(3),
    }),
    bagRow({
      item_key: "moon_herb",
      display_name: "月光草",
      held: 4,
      presentation: present("material", "material", "common", "只在月夜綻放的藥草，藥師收購它來調配藥水。"),
      give: give(4),
    }),
    bagRow({
      item_key: "iron_longsword",
      display_name: "鐵製長劍",
      held: 1,
      equipped_count: 1,
      slot: "weapon_main",
      presentation: present("weapon", "weapon", "common", "鐵匠鋪最常見的長劍，劍身厚重、用得順手。"),
      toggle: toggle(),
      give: give(0, EQUIPPED_GIVE_REASON),
    }),
    bagRow({
      item_key: "steel_shortsword",
      display_name: "鋼製短劍",
      held: 1,
      slot: "weapon_main",
      presentation: present("weapon", "weapon", "uncommon", "以精鋼打造的短劍，輕巧鋒利，適合靈活的劍士。"),
      toggle: toggle(),
      give: give(1),
    }),
    bagRow({
      item_key: "traveler_robe",
      display_name: "旅人長袍",
      held: 1,
      equipped_count: 1,
      slot: "armor",
      presentation: present("armor", "armor", "common", "厚實的羊毛長袍，擋得住山路上的風雨。"),
      toggle: toggle(),
      give: give(0, EQUIPPED_GIVE_REASON),
    }),
    bagRow({
      item_key: "silver_ring",
      display_name: "銀月戒指",
      held: 1,
      equipped_count: 1,
      slot: "accessory",
      presentation: present("accessory", "accessory", "rare", "內側刻著月紋的銀戒，戴上時心神格外清明。"),
      toggle: toggle(),
      give: give(0, EQUIPPED_GIVE_REASON),
    }),
  ],
};

// The same bag during combat: every give carries the committed combat reason
// and uses route to the member's combat draft.
export const PARTY_BAG_INVENTORY_COMBAT_SAMPLE = {
  ...PARTY_BAG_INVENTORY_SAMPLE,
  rows: PARTY_BAG_INVENTORY_SAMPLE.rows.map((row) => ({
    ...row,
    use: row.use ? { ...row.use, route: "combat_draft" } : null,
    give: { ...row.give, enabled: false, reason: TRANSFER_IN_COMBAT_REASON },
  })),
};

const hold = (member_id, held, receive, extra = {}) => ({ member_id, held, equipped: false, delta: null, receive, ...extra });
const canReceive = { enabled: true, reason: null };
const ownRow = { enabled: false, reason: null };
const absent = { enabled: false, reason: "對方不在這裡。" };

// 苦艾藥水 selected on 蕾娜's bag: the commander and the knocked-out 幽 can
// receive (transfer only reorganizes bags), the escort 蓋文 is elsewhere.
export const PARTY_BAG_HOLDINGS_CONSUMABLE = {
  schema_version: 1,
  available: true,
  kind: "item_holdings",
  item_key: "potion_heal",
  giver_id: 101,
  rows: [hold(42, 2, canReceive), hold(101, 5, ownRow), hold(102, 0, canReceive), hold(103, 1, absent)],
};

// 鋼製短劍 selected: each member's delta against their own main-hand occupant.
const delta = (...changes) => ({ equippable: true, changes: changes.map(([key, label, amount]) => ({ key, label, amount })) });
export const PARTY_BAG_HOLDINGS_EQUIPMENT = {
  schema_version: 1,
  available: true,
  kind: "item_holdings",
  item_key: "steel_shortsword",
  giver_id: 101,
  rows: [
    hold(42, 0, canReceive, { delta: delta(["atk_phys", "攻擊", 6]) }),
    hold(101, 1, ownRow, { delta: delta(["atk_phys", "攻擊", -2], ["agility", "敏捷", 3]) }),
    hold(102, 0, canReceive, { delta: { equippable: false, reason: "幽無法使用這類武器。" } }),
    hold(103, 0, absent, { delta: delta(["atk_phys", "攻擊", 4]) }),
  ],
};

export const PARTY_BAG_HOLDINGS_COMBAT = {
  ...PARTY_BAG_HOLDINGS_CONSUMABLE,
  rows: PARTY_BAG_HOLDINGS_CONSUMABLE.rows.map((row) =>
    row.member_id === 101 ? row : { ...row, receive: { enabled: false, reason: TRANSFER_IN_COMBAT_REASON } },
  ),
};

// No item selected yet.
export const PARTY_BAG_HOLDINGS_NONE = {
  schema_version: 1,
  available: true,
  kind: "item_holdings",
  item_key: null,
  giver_id: 101,
  rows: [],
};
