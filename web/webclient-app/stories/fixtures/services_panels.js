// Story fixture slices: see stories/fixtures.js (facade) for the public surface.

// The full `services` v6 payload (guild, shop, and inventory sections all
// present). Every entry mirrors the exact bounded schema; the integer
// copper currency is display-formatted, never float money.
export const SERVICES_PANEL_SAMPLE = {
  schema_version: 6,
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
    branch_label: "埃洛西恩冒險者公會 阿爾托利亞分會",
    rank_ladder: ["F", "E", "D", "C", "B", "A", "S"],
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
        definition_key: "eastern_plains_sway_whistle_sparrow",
        display_name: "驅除東部平原穗鳴雀",
        category: "defeat",
        objective_summary: "在東部大平原討伐 2 隻穗鳴雀",
        objective_note: "計數變體：啄穗型、領群型",
        deadline_line: null,
        rationale: "低階群居鳥類，較強個體會自不同方向干擾驅趕者；個體不難應付，但數量分散，取巧不易。",
        flavor: "收穫已近尾聲，東側田區每天清晨仍有成群穗鳴雀來訪。農戶請公會處理持續侵入的族群，以免今年最後一批穀物留不下來。",
        reward: { copper: 50, merit: 25, items: [] },
        rank: "F",
        accept: { action_id: "guild.quest_accept", label: "接取任務", enabled: true, disabled_reason: null, quantity: null },
      },
      {
        definition_key: "southwest_coast_tide_lamp_crab",
        display_name: "清理西南海岸潮燈蟹",
        category: "defeat",
        objective_summary: "在西南海岸討伐 1 隻潮燈蟹",
        objective_note: "計數變體：行灘型、守礁型",
        deadline_line: null,
        rationale: "低階甲殼類，但守礁型占據狹窄洞口，防禦遠高於同階個體；礁隙與潮池讓隊伍無法展開，只能逐處清理。",
        flavor: "港外的候船燈附近聚集了一批潮燈蟹，已有夜歸小船認錯泊岸方向。碼頭請公會清理這處聚集地，恢復燈號辨識。",
        reward: { copper: 120, merit: 45, items: [] },
        rank: "E",
        accept: { action_id: "guild.quest_accept", label: "接取任務", enabled: true, disabled_reason: null, quantity: null },
      },
      {
        definition_key: "northwest_highland_forest_fog_mane_lynx",
        display_name: "討伐西北高地森林霧鬃山貓",
        category: "defeat",
        objective_summary: "在西北高地森林討伐 1 隻霧鬃山貓",
        objective_note: "計數變體：潛林型、逐徑型",
        deadline_line: null,
        rationale: "中階獵食者會反覆試探隊伍邊緣，避開完整隊列；高地森林的晨霧讓接近方向難以判斷，落單的人風險明顯上升。",
        flavor: "高地運輸隊連續在晨霧中失去馱獸，獵人找到的足跡始終沿道路外緣移動。部族請公會處理已開始追逐運輸隊的個體。",
        reward: { copper: 500, merit: 100, items: [] },
        rank: "D",
        accept: { action_id: "guild.quest_accept", label: "接取任務", enabled: true, disabled_reason: null, quantity: null },
      },
      {
        // Story-only deadline variation of the real introductory offer.
        definition_key: "introductory_hunt",
        display_name: "討伐低階魔物",
        category: "defeat",
        objective_summary: "討伐 1 隻低階魔物",
        objective_note: null,
        deadline_line: "接取後 3 日",
        rationale: null,
        flavor: null,
        reward: { copper: 50, merit: 25, items: [{ item_key: "healing_potion", display_name: "治療藥水", quantity: 2 }] },
        rank: "F",
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
      merit_qualified: false,
      exam_request: { action_id: "guild.exam_request", label: "預約升等考核", enabled: true, disabled_reason: null, quantity: null },
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
    board_total: 4,
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
  schema_version: 6,
  available: false,
  reason: { code: "services_unavailable", message: "服務選單目前無法顯示" },
};

// The reduced services payload: no host, no guild/shop/inventory sections
// (all null with zero pagination totals), a bare player summary.
export const SERVICES_PANEL_MINIMAL_SAMPLE = {
  schema_version: 6,
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
// Guild rank-block variants (services v6): each swaps only the guild
// section's `rank` object (and, for the unregistered holder, the
// registration row) on top of the full sample. `merit_qualified` is the
// merit verdict; `exam_request.enabled` is independent of it.
const examRequest = (enabled, disabledReason = null) => ({
  action_id: "guild.exam_request",
  label: "預約升等考核",
  enabled,
  disabled_reason: disabledReason,
  quantity: null,
});

const withGuildRank = (rank, guildOverrides = {}) => ({
  ...SERVICES_PANEL_SAMPLE,
  guild: { ...SERVICES_PANEL_SAMPLE.guild, ...guildOverrides, rank },
});

// Merit already meets the threshold: the counter takes the request.
export const SERVICES_PANEL_GUILD_MERIT_QUALIFIED_SAMPLE = withGuildRank({
  rank: "C",
  merit: 325,
  next_rank: "B",
  next_threshold: 300,
  merit_qualified: true,
  exam_request: examRequest(true),
});

// S rank: no next rank and no threshold; the request is disabled.
export const SERVICES_PANEL_GUILD_TOP_RANK_SAMPLE = withGuildRank({
  rank: "S",
  merit: 128450,
  next_rank: null,
  next_threshold: null,
  merit_qualified: false,
  exam_request: examRequest(false, { code: "top_rank", message: "你已是最高階級，沒有下一場升等考核。" }),
});

// The clerk is occupied: the request is disabled with her schedule reason.
export const SERVICES_PANEL_GUILD_COUNTER_BUSY_SAMPLE = withGuildRank({
  rank: "C",
  merit: 140,
  next_rank: "B",
  next_threshold: 300,
  merit_qualified: false,
  exam_request: examRequest(false, { code: "schedule_blocked", message: "她現在正忙著，沒有理會你。" }),
});

// An unregistered holder: no rank (so no next rank or threshold either),
// registration offered, the request disabled until the holder joins.
export const SERVICES_PANEL_GUILD_UNREGISTERED_SAMPLE = withGuildRank(
  {
    rank: null,
    merit: 0,
    next_rank: null,
    next_threshold: null,
    merit_qualified: false,
    exam_request: examRequest(false, { code: "unregistered", message: "你尚未註冊為冒險者。" }),
  },
  {
    registration: {
      registered: false,
      register: {
        action_id: "guild.register",
        label: "加入公會",
        enabled: true,
        disabled_reason: null,
        quantity: null,
      },
    },
  },
);

// The counter can settle the holder's completed q_0301 right now: its guild
// quest row carries an enabled turn-in (quest-drawer-book-tab's hot
// completed badge). q_1042 keeps its in-progress row.
export const SERVICES_PANEL_GUILD_TURNIN_READY_SAMPLE = {
  ...SERVICES_PANEL_SAMPLE,
  guild: {
    ...SERVICES_PANEL_SAMPLE.guild,
    quests: [
      ...SERVICES_PANEL_SAMPLE.guild.quests,
      {
        quest_id: "q_0301",
        definition_key: "quest_mill_grain",
        display_name: "磨坊糧運",
        state: "completed",
        stage_index: 2,
        stage_progress: 10,
        objective_summary: "將十袋糧食運往磨坊",
        deadline_line: null,
        detail: "糧食已送達磨坊，等著回去回報。",
        abandon: { action_id: "guild.quest_abandon", label: "放棄任務", enabled: false, disabled_reason: { code: "quest_not_active", message: "任務已結束" }, quantity: null },
        turnin: { action_id: "guild.quest_turnin", label: "交付委託", enabled: true, disabled_reason: null, quantity: null },
        tracked: false,
      },
    ],
  },
  pagination: { ...SERVICES_PANEL_SAMPLE.pagination, quest_total: 2 },
};

// The grade-tabbed guild board (quest-drawer-guild-board-tab), after the
// approved prototype: an E-rank holder whose board lists two F and two E
// offers (the server lists none above the holder's rank). The second E offer
// is already held, so its accept descriptor is disabled with the server's
// reason. The fourth row is a story-only variation of the hare offer.
const boardOffer = (key) => SERVICES_PANEL_SAMPLE.guild.board.find((row) => row.definition_key === key);

export const SERVICES_PANEL_GUILD_BOARD_SAMPLE = {
  ...SERVICES_PANEL_SAMPLE,
  player: { ...SERVICES_PANEL_SAMPLE.player, guild_rank: "E", guild_merit: 140, next_rank: "D", next_threshold: 500 },
  guild: {
    ...SERVICES_PANEL_SAMPLE.guild,
    board: [
      boardOffer("eastern_plains_sway_whistle_sparrow"),
      boardOffer("introductory_hunt"),
      boardOffer("southwest_coast_tide_lamp_crab"),
      {
        definition_key: "western_hills_ridge_hare",
        display_name: "清理西部丘陵築埂兔",
        category: "defeat",
        objective_summary: "在西部丘陵討伐 3 隻築埂兔",
        objective_note: "計數變體：築巢型、護巢型",
        deadline_line: "接取後 3 日",
        rationale: "平原鬆土讓牠們容易鑽回洞道，護巢型又會加固入口；個體不強，逐一找出田埂間的巢口才是難處。",
        flavor: "平原邊緣的鬆土帶出現新的築埂兔巢，坑洞妨礙農具與牲畜通行。農戶請公會清除這一帶的族群，讓田間作業恢復。",
        reward: { copper: 150, merit: 50, items: [{ item_key: "healing_potion", display_name: "治療藥水", quantity: 2 }] },
        rank: "E",
        accept: {
          action_id: "guild.quest_accept",
          label: "接取任務",
          enabled: false,
          disabled_reason: { code: "quest_already_active", message: "這個任務已經在進行中了。" },
          quantity: null,
        },
      },
    ],
    rank: {
      rank: "E",
      merit: 140,
      next_rank: "D",
      next_threshold: 500,
      merit_qualified: false,
      exam_request: examRequest(true),
    },
  },
  pagination: { ...SERVICES_PANEL_SAMPLE.pagination, board_total: 4 },
};
