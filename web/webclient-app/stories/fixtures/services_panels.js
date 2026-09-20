// Story fixture slices: see stories/fixtures.js (facade) for the public surface.

// The full `services` payload (guild, shop, and inventory sections all
// present). Every entry mirrors the exact bounded schema; the integer
// copper currency is display-formatted, never float money.
export const SERVICES_PANEL_SAMPLE = {
  schema_version: 4,
  available: true,
  kind: "services",
  host: { identity: "host_altoria", display_name: "霧骨渡口的服務門戶" },
  player: {
    wallet: 3240,
    guild_registered: true,
    guild_rank: "C",
    guild_merit: 140,
    next_rank: "B",
    next_threshold: 300,
  },
  guild: {
    registration: {
      registered: true,
      register: {
        action_id: "guild.register",
        label: "加入公會",
        enabled: false,
        disabled_reason: { code: "already_registered", message: "你已經是公會成員" },
        quantity: null,
      },
    },
    board: [
      {
        definition_key: "quest_mill_grain",
        display_name: "磨坊糧運",
        objective_summary: "將十袋糧食運往磨坊",
        reward_summary: "400 銅＋公會功績 25",
        rank: "C",
        accept: { action_id: "guild.quest_accept", label: "接取任務", enabled: true, disabled_reason: null, quantity: null },
      },
      {
        definition_key: "quest_harbor_light",
        display_name: "燈塔值守",
        objective_summary: "為渡口燈塔補足燈油",
        reward_summary: "220 銅＋公會功績 15",
        rank: "B",
        accept: { action_id: "guild.quest_accept", label: "接取任務", enabled: true, disabled_reason: null, quantity: null },
      },
    ],
    quests: [
      {
        quest_id: "q_1042",
        definition_key: "quest_mill_grain",
        display_name: "磨坊糧運",
        state: "in_progress",
        stage_index: 1,
        stage_progress: 3,
        objective_summary: "將十袋糧食運往磨坊",
        deadline_line: "剩餘 2 日",
        detail: "老周把三袋糧食交給你，要求天亮前送到磨坊。",
        abandon: { action_id: "guild.quest_abandon", label: "放棄任務", enabled: true, disabled_reason: null, quantity: null },
        turnin: { action_id: "guild.quest_turnin", label: "交派任務", enabled: false, disabled_reason: { code: "quest_not_ready", message: "任務目標尚未完成" }, quantity: null },
        tracked: true,
      },
    ],
    rank: {
      rank: "C",
      merit: 140,
      next_rank: "B",
      next_threshold: 300,
      eligible: true,
      exam_start: { action_id: "guild.exam_start", label: "開始考核", enabled: true, disabled_reason: null, quantity: null },
    },
  },
  shop: {
    open: true,
    stock: [
      {
        item_key: "item_iron_sword",
        display_name: "鐵劍",
        buy_copper: 120,
        sell_copper: 80,
        stock: 8,
        max_stock: 24,
        buy: { action_id: "shop.buy", label: "購買鐵劍", enabled: true, disabled_reason: null, quantity: { min: 1, max: 8 } },
      },
      {
        item_key: "item_heal_potion",
        display_name: "治療劑",
        buy_copper: 45,
        sell_copper: 30,
        stock: 30,
        max_stock: 30,
        buy: { action_id: "shop.buy", label: "購買治療劑", enabled: false, disabled_reason: { code: "insufficient_funds", message: "錢包餘額不足" }, quantity: { min: 1, max: 30 } },
      },
    ],
    sellable: [
      {
        item_key: "item_herb_moon",
        display_name: "月光草",
        sell_copper: 25,
        held: 3,
        sell: { action_id: "shop.sell", label: "賣出月光草", enabled: true, disabled_reason: null, quantity: { min: 1, max: 3 } },
      },
    ],
  },
  inventory: {
    rows: [
      { item_key: "item_iron_sword", display_name: "鐵劍", held: 1, equipped: true, presentation: null, action: null },
      { item_key: "item_leather_armor", display_name: "皮甲", held: 1, equipped: true, presentation: null, action: null },
      { item_key: "item_heal_potion", display_name: "治療劑", held: 4, equipped: false, presentation: null, action: null },
      {
        item_key: "healing_potion",
        display_name: "治療藥水",
        held: 2,
        equipped: false,
        action: null,
        presentation: {
          kind: "potion",
          icon_key: "potion",
          rarity: "rare",
          summary: "盛裝於小瓶中的治療藥水。",
        },
      },
    ],
    wallet: 3240,
  },
  pagination: {
    board_total: 2,
    quest_total: 1,
    stock_total: 2,
    sellable_total: 1,
    inventory_total: 4,
  },
};

// The services v2 panel whose inventory rows all carry committed
// presentation metadata (redesign-inventory-item-grid): the row set originally
// covered every closed `ItemIconKey`/`ItemKind` value (food, potion, weapon, armor,
// accessory, ammunition, tool, material, misc) and every closed rarity
// (common, uncommon, rare, epic, legendary). The presentation objects mirror
// the server's registry (`world/lore/items.py`).
export const SERVICES_PANEL_PRESENTATION_SAMPLE = {
  ...SERVICES_PANEL_SAMPLE,
  inventory: {
    rows: [
      {
        item_key: "meal",
        display_name: "普通餐食",
        held: 5,
        equipped: false,
        action: null,
        presentation: {
          kind: "food",
          icon_key: "food",
          rarity: "common",
          summary: "供旅人充飢的普通餐食。",
        },
      },
      {
        item_key: "healing_potion",
        display_name: "治療藥水",
        held: 3,
        equipped: false,
        action: null,
        presentation: {
          kind: "potion",
          icon_key: "potion",
          rarity: "rare",
          summary: "盛裝於小瓶中的治療藥水。",
        },
      },
      {
        item_key: "plain_sword",
        display_name: "普通劍",
        held: 1,
        equipped: true,
        action: null,
        presentation: {
          kind: "weapon",
          icon_key: "weapon",
          rarity: "common",
          summary: "鍛鐵打造的普通劍。",
        },
      },
      {
        item_key: "leather_armor",
        display_name: "皮甲",
        held: 1,
        equipped: true,
        action: null,
        presentation: {
          kind: "armor",
          icon_key: "armor",
          rarity: "uncommon",
          summary: "縫製的皮革盔甲。",
        },
      },
      {
        item_key: "mist_amulet",
        display_name: "霧隱護符",
        held: 2,
        equipped: true,
        action: null,
        presentation: {
          kind: "accessory",
          icon_key: "accessory",
          rarity: "epic",
          summary: "可短暫隱形的小型護符。",
        },
      },
      {
        item_key: "leather_arrows",
        display_name: "皮箭",
        held: 12,
        equipped: false,
        action: null,
        presentation: {
          kind: "ammunition",
          icon_key: "ammunition",
          rarity: "common",
          summary: "基本遠程箭矢。",
        },
      },
      {
        item_key: "candle",
        display_name: "燭",
        held: 4,
        equipped: false,
        action: null,
        presentation: {
          kind: "tool",
          icon_key: "tool",
          rarity: "common",
          summary: "供照明的蠟燭。",
        },
      },
      {
        item_key: "iron_ingot",
        display_name: "鐵錠",
        held: 2,
        equipped: false,
        action: null,
        presentation: {
          kind: "material",
          icon_key: "material",
          rarity: "uncommon",
          summary: "可鍛造的鐵材。",
        },
      },
      {
        item_key: "travel_pack",
        display_name: "行囊",
        held: 1,
        equipped: false,
        action: null,
        presentation: {
          kind: "misc",
          icon_key: "misc",
          rarity: "legendary",
          summary: "旅人的多用途行囊。",
        },
      },
    ],
    wallet: 3240,
  },
  pagination: { ...SERVICES_PANEL_SAMPLE.pagination, inventory_total: 9 },
};

// The registry-owned unavailable form for the services panel: the common
// `{available: false, reason}` envelope (webclient-oob-protocol), carrying
// the panel-stable reason — no invented sections or default values.
export const SERVICES_PANEL_UNAVAILABLE_SAMPLE = {
  schema_version: 4,
  available: false,
  reason: { code: "services_unavailable", message: "服務選單目前無法顯示" },
};

// The reduced services payload: no host, no guild/shop/inventory sections
// (all null with zero pagination totals), a bare player summary.
export const SERVICES_PANEL_MINIMAL_SAMPLE = {
  schema_version: 4,
  available: true,
  kind: "services",
  host: null,
  player: {
    wallet: 0,
    guild_registered: false,
    guild_rank: null,
    guild_merit: 0,
    next_rank: null,
    next_threshold: null,
  },
  guild: null,
  shop: null,
  inventory: null,
    pagination: {
      board_total: 0,
      quest_total: 0,
      stock_total: 0,
      sellable_total: 0,
      inventory_total: 0,
    },
};