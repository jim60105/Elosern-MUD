// Story fixture slices: see stories/fixtures.js (facade) for the public surface.

// ---------------------------------------------------------------------------
// webclient-shop-window: the shop window's committed panels, after the
// approved prototype (docs/design/party-member-management/ShopPrototype.vue):
// the smith 鐵匠鋪 sells weapons; the rail is the commander 莉瑟, the
// companion 艾拉 and the knocked-out companion 卡恩. Every panel is an exact
// committed payload (validated by tests/world/shop_window.test.js).
// ---------------------------------------------------------------------------
import { CHARACTER_PANEL_SAMPLE } from "./character_panels.js";
import { SERVICES_PANEL_SHOP_ROWS_SAMPLE } from "./services_panels.js";

const member = (row) => ({
  portrait_ref: null,
  mp_current: 20,
  mp_maximum: 40,
  sp_current: 20,
  sp_maximum: 30,
  knocked_out: false,
  unread: false,
  ...row,
});

export const SHOP_COMMANDER_ID = 42;
export const SHOP_ELLA_ID = 102;
export const SHOP_KAHN_ID = 103;

const SHOP_PARTY_SLOTS = [
  member({
    identity: SHOP_COMMANDER_ID,
    display_name: "莉瑟",
    role: "commander",
    hp_current: 96,
    hp_maximum: 120,
    bond_stage: null,
    membership: null,
  }),
  member({
    identity: SHOP_ELLA_ID,
    display_name: "艾拉",
    role: "companion",
    hp_current: 140,
    hp_maximum: 160,
    bond_stage: "信賴",
    membership: { general: true, temporary_commissions: [] },
  }),
  member({
    identity: SHOP_KAHN_ID,
    display_name: "卡恩",
    role: "companion",
    hp_current: 0,
    hp_maximum: 220,
    bond_stage: "親睦",
    knocked_out: true,
    membership: { general: true, temporary_commissions: [] },
  }),
];

// 艾拉 is the viewed member (selected in the party window, so the shop's
// default recipient).
export const SHOP_PARTY_SAMPLE = {
  schema_version: 3,
  available: true,
  general_quota: { used: 2, limit: 4 },
  viewed_member_id: SHOP_ELLA_ID,
  slots: SHOP_PARTY_SLOTS,
};

// The same party viewing 卡恩 (the 出售 story's seller).
export const SHOP_PARTY_SELLER_SAMPLE = { ...SHOP_PARTY_SAMPLE, viewed_member_id: SHOP_KAHN_ID };

// The smith's services for 艾拉: the stock rows carry her deltas (or 無法裝備
// with its stable code) and the potion's held count; the purse is 1,240.
export const SHOP_SERVICES_SAMPLE = {
  ...SERVICES_PANEL_SHOP_ROWS_SAMPLE,
  host: { identity: "smith_hagar", display_name: "鐵匠鋪" },
  player: { ...SERVICES_PANEL_SHOP_ROWS_SAMPLE.player, wallet: 1240 },
  shop: { ...SERVICES_PANEL_SHOP_ROWS_SAMPLE.shop, member_id: SHOP_ELLA_ID },
};

// The smith's services for the seller 卡恩: his unequipped copies.
const sellAction = (max) => ({ action_id: "shop.sell", label: "出售", enabled: true, disabled_reason: null, quantity: { min: 1, max } });
export const SHOP_SERVICES_SELLER_SAMPLE = {
  ...SHOP_SERVICES_SAMPLE,
  shop: {
    ...SHOP_SERVICES_SAMPLE.shop,
    member_id: SHOP_KAHN_ID,
    sellable: [
      {
        item_key: "potion_heal",
        display_name: "治療藥水",
        presentation: { kind: "potion", icon_key: "potion", rarity: "common", summary: "回復少量生命。" },
        sell_copper: 15,
        held: 1,
        sell: sellAction(1),
      },
      {
        item_key: "rusty_sword",
        display_name: "生鏽的劍",
        presentation: { kind: "weapon", icon_key: "weapon", rarity: "common", summary: "刃口滿是鏽斑的舊劍。" },
        sell_copper: 45,
        held: 2,
        sell: sellAction(2),
      },
      {
        item_key: "iron_buckler",
        display_name: "鐵製小圓盾",
        presentation: { kind: "armor", icon_key: "armor", rarity: "uncommon", summary: "邊緣包鐵的小圓盾。" },
        sell_copper: 70,
        held: 1,
        sell: { action_id: "shop.sell", label: "出售", enabled: false, disabled_reason: { code: "stock_overflow", message: "商店收購上限已滿。" }, quantity: null },
      },
    ],
  },
  pagination: { ...SHOP_SERVICES_SAMPLE.pagination, sellable_total: 3 },
};

// The closed smith: every trade carries the committed closed reason.
const CLOSED = { code: "closed", message: "商店目前沒有營業。" };
export const SHOP_SERVICES_CLOSED_SAMPLE = {
  ...SHOP_SERVICES_SAMPLE,
  shop: {
    ...SHOP_SERVICES_SAMPLE.shop,
    open: false,
    stock: SHOP_SERVICES_SAMPLE.shop.stock.map((row) => ({
      ...row,
      buy: { ...row.buy, enabled: false, disabled_reason: CLOSED, quantity: null },
    })),
    sellable: SHOP_SERVICES_SAMPLE.shop.sellable.map((row) => ({
      ...row,
      sell: { ...row.sell, enabled: false, disabled_reason: CLOSED, quantity: null },
    })),
  },
};

const noReceive = { enabled: false, reason: null };
const canReceive = { enabled: true, reason: null };
const gain = (key, label, amount) => ({ key, label, amount });
const delta = (...changes) => ({ equippable: true, changes });

// 鋼製短劍 selected for 艾拉: every member's server delta against their own
// main hand.
export const SHOP_HOLDINGS_EQUIPMENT = {
  schema_version: 1,
  available: true,
  kind: "item_holdings",
  item_key: "steel_shortsword",
  giver_id: SHOP_ELLA_ID,
  rows: [
    { member_id: SHOP_COMMANDER_ID, held: 0, equipped: false, delta: delta(gain("atk_phys", "攻擊", 2)), receive: canReceive },
    { member_id: SHOP_ELLA_ID, held: 0, equipped: false, delta: delta(gain("atk_phys", "攻擊", 6)), receive: noReceive },
    { member_id: SHOP_KAHN_ID, held: 0, equipped: false, delta: delta(gain("atk_phys", "攻擊", -4)), receive: canReceive },
  ],
};

// 治療藥水 selected for 艾拉: held counts only.
export const SHOP_HOLDINGS_POTION = {
  schema_version: 1,
  available: true,
  kind: "item_holdings",
  item_key: "potion_heal",
  giver_id: SHOP_ELLA_ID,
  rows: [
    { member_id: SHOP_COMMANDER_ID, held: 3, equipped: false, delta: null, receive: canReceive },
    { member_id: SHOP_ELLA_ID, held: 2, equipped: false, delta: null, receive: noReceive },
    { member_id: SHOP_KAHN_ID, held: 1, equipped: false, delta: null, receive: canReceive },
  ],
};

// 生鏽的劍 selected on 出售 for the seller 卡恩.
export const SHOP_HOLDINGS_SELL = {
  schema_version: 1,
  available: true,
  kind: "item_holdings",
  item_key: "rusty_sword",
  giver_id: SHOP_KAHN_ID,
  rows: [
    { member_id: SHOP_COMMANDER_ID, held: 0, equipped: false, delta: delta(gain("atk_phys", "攻擊", -3)), receive: canReceive },
    { member_id: SHOP_ELLA_ID, held: 1, equipped: false, delta: delta(gain("atk_phys", "攻擊", -1)), receive: canReceive },
    { member_id: SHOP_KAHN_ID, held: 3, equipped: true, delta: delta(), receive: noReceive },
  ],
};

// 艾拉's committed `character` panel (the comparison's current values).
export const SHOP_CHARACTER_SAMPLE = { ...CHARACTER_PANEL_SAMPLE, member_id: SHOP_ELLA_ID };
