// Deterministic offline fixtures for the core-family stories (B1). Every
// value mirrors a shape the C1 store getters will return for the same
// slice, so the offline showcase and the live views cannot drift. No live
// server, LLM, or imagegen data — fixed literals only.

export const NARRATIVE_SAMPLE = [
  { kind: "out", text: "你站在測試起點的石板廣場上，夜霧低垂，遠燈明滅。" },
  { kind: "sys", text: "—— 一則新的敘事 ——" },
  { kind: "in", text: "look" },
  {
    kind: "out",
    text:
      "<span class=\"color-033\">石板廣場</span> 夜色沉靜。" +
      "<span class=\"color-208 bgcolor-236\">霧燈</span> 在街角閃爍。",
  },
  { kind: "err", text: "冷風刮過後頸——有什麼東西在暗處移動。" },
  {
    kind: "out",
    text:
      "│  北面出口：石階  │\n" +
      "├────────────────┤\n" +
      "│  南門（wilderness）│",
  },
];

export const MARKUP_STRESS_SAMPLE = [
  {
    kind: "out",
    text:
      "<span style=\"color: #e06b6b;\">印章紅</span> 的提燈、" +
      "<span class=\"underline\">底線字樣</span>，" +
      "以及未被接受的字串 <div>原樣保留</div> 與 <i>斜體</i>。",
  },
  { kind: "out", text: "<br>換行測試：<br>第二行。" },
];

// Status/server-time slice backing the TopBar (status panel + serverTime).
export const STATUS_SLICE_SAMPLE = {
  connected: true,
  locationLabel: "測試起點",
  timeLabel: "春季 3 日 · 12:00",
};

export const PROMPT_SAMPLE = "<span class=\"color-111\">></span> ";

export const COMMAND_HISTORY_SAMPLE = ["look", "北", "talk 老周"];

// ---------------------------------------------------------------------------
// B2 action-dock family fixtures (webclient-vue-03-showcase-action).
//
// Every value mirrors a validated `context_actions` v5 slice — the exact
// server-authored shapes (the v5 exploration form's action/navigation
// affordances and the suggestions envelope) — so the offline showcase and
// the live (C1 store) views cannot drift. Fixed literals only.
// ---------------------------------------------------------------------------

// v5 exploration-form action + navigation affordances, one bounded frame:
// enabled and disabled action entries (disabled_reason carries the
// server-authored note) and a local navigation surface.
export const EXPLORATION_AFFORDANCES_SAMPLE = [
  {
    action_id: "explore.move",
    label: "走往北岸大道",
    params: { exit_ref: "north", current_node: 42 },
    freeform: false,
    navigation: false,
    enabled: true,
    disabled_reason: null,
  },
  {
    action_id: "explore.look",
    label: "觀察房間",
    params: { room: true },
    freeform: false,
    navigation: false,
    enabled: true,
    disabled_reason: null,
  },
  {
    action_id: "explore.talk_freeform",
    label: "與灰婆婆自由交談",
    params: { npc_id: 9 },
    freeform: true,
    navigation: false,
    enabled: true,
    disabled_reason: null,
  },
  {
    action_id: "explore.wait",
    label: "等待",
    params: { daypart: "dusk" },
    freeform: false,
    navigation: false,
    enabled: false,
    disabled_reason: { code: "recovery", message: "正在調息，無法行動" },
  },
  {
    surface: "guild",
    label: "公會",
    navigation: true,
    enabled: true,
    disabled_reason: null,
  },
];

// A target selection frame (`target-<identity>` item keys) — the combat
// target menu shape: identity/display_name/state derived entries.
export const TARGET_ITEMS_SAMPLE = [
  { identity: "e1", label: "灰袍盜賊", enabled: true, disabled_reason: null },
  { identity: "e2", label: "斷刃巡衛", enabled: false, disabled_reason: { code: "down", message: "已倒地" } },
  { identity: "a2", label: "同行劍士", enabled: true, disabled_reason: null },
];

// v5 suggestions envelope, one per stream status (ready 3..5 cards,
// degraded 0..5 cards; label is 1..24 code points with at least one CJK
// character; hint is at most 60 code points or absent).
export const SUGGESTIONS_GENERATING_SAMPLE = { status: "generating" };

export const SUGGESTIONS_READY_SAMPLE = {
  status: "ready",
  cards: [
    {
      kind: "known_action",
      action_code: "explore.look",
      label: "查看房間",
      params: { room: true },
    },
    {
      kind: "known_action",
      action_code: "explore.wait",
      label: "等到黃昏",
      params: { daypart: "dusk" },
      hint: "先休息一會兒再行動",
    },
    {
      kind: "known_action",
      action_code: "explore.talk_scripted",
      label: "與灰婆婆交談",
      params: { npc_id: 7, keyword_id: "問候" },
    },
    {
      kind: "freeform",
      action_code: "explore.talk_freeform",
      label: "我們聊聊好嗎？",
      params: { npc_id: 9 },
      hint: "說任何想說的話",
    },
  ],
};

export const SUGGESTIONS_DEGRADED_EMPTY_SAMPLE = {
  status: "degraded",
  cards: [],
};

export const SUGGESTIONS_UNAVAILABLE_SAMPLE = { status: "unavailable" };

// ---------------------------------------------------------------------------
// B3 data-family fixtures (webclient-vue-04-showcase-data).
//
// Every value mirrors a validated OOB payload — the `status` panel at schema
// version 1 (web/webclient/presentation/status.py) and the `character` panel
// at schema version 3 (web/webclient/presentation/character.py) — and the
// character's skill data keeps the character payload's category/group/
// {key,label} grouping with the optional OOB skill-descriptor detail fields
// (the context_actions v5 descriptor shape: cost, target_spec,
// freeform_scales, shorthands) attached to some rows only. Fixed literals
// only, so the offline showcase and the live (C1 store) views cannot drift.
// ---------------------------------------------------------------------------

// A committed `status` v1 payload (design-draft actor at 霧骨渡口): mixed
// gauge states, one buff with a remaining duration, one deterministic
// combat-modifier condition carrying its exact applied modifiers, an active
// disguise, and no combat session.
export const STATUS_PANEL_SAMPLE = {
  schema_version: 1,
  available: true,
  actor: {
    name: "艾倫·灰誓",
    identity: "char-42",
    location: { label: "霧骨渡口", identity: "room-7" },
  },
  resources: {
    hp: { current: 231, maximum: 405 },
    mp: { current: 139, maximum: 420 },
    sp: { current: 68, maximum: 68 },
  },
  conditions: [
    {
      code: "fastwind",
      label: "疾風",
      severity: "beneficial",
      remaining_seconds: 60,
    },
    {
      code: "shame_exposure",
      label: "高露出",
      severity: "harmful",
      modifiers: { defense: -15, agility: -10 },
    },
    {
      code: "fog_veil",
      label: "霧隱",
      severity: "informational",
    },
  ],
  disguise_active: true,
  combat: null,
};

// The same actor mid-combat (guild examination), for the combat story.
export const STATUS_PANEL_COMBAT_SAMPLE = {
  ...STATUS_PANEL_SAMPLE,
  conditions: [
    {
      code: "combat_focus",
      label: "專注",
      severity: "warning",
      remaining_seconds: 10,
      modifiers: { atk_phys: 5 },
    },
  ],
  disguise_active: false,
  combat: { mode: "guild_exam", round: 3 },
};

// The compact, condition-free variant: all gauges full, nothing else.
export const STATUS_PANEL_MINIMAL_SAMPLE = {
  ...STATUS_PANEL_SAMPLE,
  resources: {
    hp: { current: 405, maximum: 405 },
    mp: { current: 420, maximum: 420 },
    sp: { current: 68, maximum: 68 },
  },
  conditions: [],
  disguise_active: false,
  combat: null,
};

// The committed `character` v3 payload for the same actor: all eight trait
// rows (gauges carry max, statics/counters carry null max), grouped active
// and passive skills, equipped items, an active disguise whose displayed
// values differ from the true traits, guild rank/merit, wallet, and persona.
export const CHARACTER_PANEL_SAMPLE = {
  schema_version: 3,
  available: true,
  kind: "character",
  traits: [
    { key: "hp", label: "生命", current: 231, max: 405 },
    { key: "mp", label: "魔力", current: 139, max: 420 },
    { key: "sp", label: "耐力", current: 68, max: 68 },
    { key: "atk_phys", label: "攻擊", current: 18, max: null },
    { key: "agility", label: "敏捷", current: 20, max: null },
    { key: "defense", label: "防禦", current: 12, max: null },
    { key: "magic_level", label: "魔法階級", current: 31, max: null },
    { key: "guild_merit", label: "功績", current: 140, max: null },
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
    { slot: "weapon_main", item_key: "short_sword_lost", display_name: "短劍 · 拾遺" },
    { slot: "armor", item_key: "leather_armor", display_name: "皮甲" },
    { slot: "accessory", item_key: "fog_talisman", display_name: "霧隱護符" },
  ],
  disguise: {
    active: true,
    description: "目前以「旅商」身分示人；顯示值只影響外觀與鑑定。",
    displayed: [
      { key: "atk_phys", label: "攻擊", value: 25 },
      { key: "magic_level", label: "魔法階級", value: 12 },
    ],
  },
  guild: { rank: "E", merit: 140 },
  wallet: 3240,
  persona: {
    background: "渡口成長起來的灰誓成員，習慣在黃昏開張前巡完整條街。",
  },
};

// The same actor without a disguise, no guild, no persona background — the
// honest empty-state story (displayed list must be empty, rank → 未加入公會,
// persona renders nothing).
export const CHARACTER_PANEL_UNDISGUISED_SAMPLE = {
  ...CHARACTER_PANEL_SAMPLE,
  equipment: [
    { slot: "weapon_main", item_key: "short_sword_lost", display_name: "短劍 · 拾遺" },
  ],
  disguise: { active: false, description: "", displayed: [] },
  guild: { rank: null, merit: 0 },
  wallet: 0,
  persona: { background: null },
};

// The character's skill data as the SkillBook consumes it: the character
// payload's actives/passives grouping, with the rows the C1 getter backs from
// a committed `context_actions` v5 skill descriptor extended with that
// descriptor's display subset — `cost` (a bounded object, the empty object
// being the v5 free form), `target_spec`, the optional `freeform_scales`
// array, and `shorthands`. Rows the getter has no descriptor for stay the
// character payload's own `{key, label}` shape: `flee` shows the free-cost
// form, and the unregistered-key `legacy_stance` row (the character payload's
// own unknown-key degradation) proves detail cells render only when the
// backing data provides the field.
export const SKILLS_SLICE_SAMPLE = {
  actives: [
    {
      category: "elemental_magic",
      label: "元素魔法",
      groups: [
        {
          group: "fire",
          label: "火",
          skills: [
            {
              key: "firebolt",
              label: "火矢",
              cost: { mp: 10 },
              target_spec: "single",
            },
            {
              key: "fireball",
              label: "火球",
              cost: { mp: 14 },
              target_spec: "single",
              freeform_scales: [
                { scale: 0.25, label: "1/4", mp_cost: 4 },
                { scale: 0.5, label: "1/2", mp_cost: 7 },
                { scale: 1, label: "1", mp_cost: 14 },
                { scale: 2, label: "2", mp_cost: 28 },
                { scale: 4, label: "4", mp_cost: 56 },
              ],
            },
            {
              key: "firestorm",
              label: "火風暴",
              cost: { mp: 30, sp: 5 },
              target_spec: "area",
              shorthands: ["all-enemies", "all"],
            },
          ],
        },
        {
          group: "water",
          label: "水",
          skills: [
            {
              key: "mend_glow",
              label: "微光治癒",
              cost: { mp: 11 },
              target_spec: "self",
            },
          ],
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
          skills: [
            {
              key: "basic_attack",
              label: "基本攻擊",
              cost: {},
              target_spec: "single",
            },
            {
              key: "light_blade",
              label: "輕劍式",
              cost: { sp: 6 },
              target_spec: "single",
            },
          ],
        },
      ],
    },
    {
      category: "movement",
      label: "移動",
      groups: [
        {
          group: null,
          label: null,
          skills: [
            {
              key: "flee",
              label: "逃跑",
              cost: {},
              target_spec: "none",
            },
            { key: "legacy_stance", label: "legacy_stance" },
          ],
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
    {
      category: "innate_gift",
      label: "天賦",
      groups: [{ group: null, label: null, skills: [{ key: "elf_longevity", label: "精靈長壽" }] }],
    },
  ],
};

// ---------------------------------------------------------------------------
// B4 (webclient-vue-05-showcase-world): world + services family fixtures.
// Mirror the bounded OOB panel payloads — local_map v1, art v1, and
// services v1 — so the offline showcase asserts truthfulness: the lattice
// states, the art placeholder contract, the services-backed shop/quest/
// lore/inventory surfaces, and the equipped-only inventory (no full bag,
// no party panel — both deferred, roadmap §7). No live server, LLM, or
// imagegen data; every value is a fixed literal.
// ---------------------------------------------------------------------------

// The `local_map` v1 lattice: exactly one current node; adjacent nodes
// marked unvisited/visited, a remembered far node, edges with traversable
// states, the legend explaining every visibility state, and an actionable
// adjacent node whose `action` carries the OOB move intent.
export const LOCAL_MAP_SAMPLE = {
  schema_version: 1,
  available: true,
  layer: "grid",
  current_node: "grid:altoria:1:2",
  title: "霧骨渡口",
  nodes: [
    {
      id: "grid:altoria:1:2",
      label: "霧骨渡口",
      x: 1,
      y: 2,
      visibility: "current",
      current: true,
      anchor: true,
      landmark: true,
      action: null,
    },
    {
      id: "grid:altoria:2:2",
      label: "南門",
      x: 2,
      y: 2,
      visibility: "visible_unvisited",
      current: false,
      anchor: false,
      landmark: false,
      action: { kind: "move", exit_ref: "e_altoria_1_2_e", destination: "grid:altoria:2:2" },
    },
    {
      id: "grid:altoria:0:2",
      label: "碼頭",
      x: 0,
      y: 2,
      visibility: "visible_visited",
      current: false,
      anchor: true,
      landmark: false,
      action: null,
    },
    {
      id: "grid:altoria:5:5",
      label: "舊街區",
      x: 5,
      y: 5,
      visibility: "remembered",
      current: false,
      anchor: false,
      landmark: true,
      action: null,
    },
  ],
  edges: [
    { source: "grid:altoria:1:2", destination: "grid:altoria:2:2", label: "南門", known: true, traversable: true },
    { source: "grid:altoria:1:2", destination: "grid:altoria:0:2", label: "碼頭", known: true, traversable: false },
    { source: "grid:altoria:1:2", destination: "grid:altoria:5:5", label: "遠方路網", known: false, traversable: false },
  ],
  legend: [
    "你目前所在的位置",
    "尚未探索的相鄰位置",
    "已經探索過的相鄰位置",
    "曾經到過、但不在附近的遠方位置",
  ],
};

// The reduced lattice state: current node plus a single unvisited adjacent
// node (no action, one legend line) — the minimal truthful map.
export const LOCAL_MAP_MINIMAL_SAMPLE = {
  schema_version: 1,
  available: true,
  layer: "grid",
  current_node: "grid:altoria:1:2",
  title: "霧骨渡口",
  nodes: [
    {
      id: "grid:altoria:1:2",
      label: "霧骨渡口",
      x: 1,
      y: 2,
      visibility: "current",
      current: true,
      anchor: true,
      landmark: true,
      action: null,
    },
    {
      id: "grid:altoria:1:1",
      label: "北岸",
      x: 1,
      y: 1,
      visibility: "visible_unvisited",
      current: false,
      anchor: false,
      landmark: false,
      action: null,
    },
  ],
  edges: [
    { source: "grid:altoria:1:2", destination: "grid:altoria:1:1", label: "北岸", known: false, traversable: true },
  ],
  legend: ["你目前所在的位置"],
};

// The registry-owned unavailable form for the map (a broken presenter, or
// a layer the player has not explored yet).
export const LOCAL_MAP_UNAVAILABLE_SAMPLE = {
  schema_version: 1,
  available: false,
  reason: { code: "map_unavailable", message: "區域地圖目前無法顯示" },
};

// The `art` payload when the scene asset is generated: the 16:9 scene
// renders cover-style and the 3:4 portrait catalog carries contextual
// names/roles; labels and alt text stay DOM nodes outside the bitmaps.
export const ART_PANEL_SAMPLE = {
  schema_version: 1,
  available: true,
  kind: "scene",
  scene: {
    archetype: "river_dawn",
    label: "河畔清晨",
    subject_key: "scene_river_dawn",
    status: "done",
    url: "/art/scenes/scene_river_dawn.png",
    aspect_ratio: "16:9",
    alt: "河畔清晨的場景",
    placeholder: null,
  },
  portrait_catalog: {
    "101": {
      subject_key: "port_harbor_master",
      status: "done",
      url: "/art/portraits/port_harbor_master.png",
      aspect_ratio: "3:4",
      alt: "碼頭船長的肖像",
      placeholder: null,
      context: { name: "老周", role: "對話對象" },
    },
    "217": {
      subject_key: "port_river_ogre",
      status: "done",
      url: "/art/portraits/port_river_ogre.png",
      aspect_ratio: "3:4",
      alt: "河灣巨魔的肖像",
      placeholder: null,
      context: { name: "河灣巨魔", role: "敵方" },
    },
  },
};

// The art panel while the scene asset is still generating: the scene is
// pending, there is no prior image (url/subject_key null), and the panel
// degrades to the truthful "missing" placeholder — no invented bitmap.
export const ART_PANEL_PENDING_SAMPLE = {
  schema_version: 1,
  available: true,
  kind: "scene",
  scene: {
    archetype: "river_dawn",
    label: "河畔清晨",
    subject_key: null,
    status: "pending",
    url: null,
    aspect_ratio: null,
    alt: "河畔清晨的場景",
    placeholder: { kind: "missing", label: "場景圖像尚未生成" },
  },
  portrait_catalog: {
    "101": {
      subject_key: "port_harbor_master",
      status: "pending",
      url: null,
      aspect_ratio: null,
      alt: "碼頭船長的肖像",
      placeholder: { kind: "missing", label: "肖像圖像尚未生成" },
      context: { name: "老周", role: "對話對象" },
    },
  },
};

// The registry-owned unavailable form for the art panel.
export const ART_PANEL_UNAVAILABLE_SAMPLE = {
  schema_version: 1,
  available: false,
  reason: { code: "art_unavailable", message: "場景圖像目前無法顯示" },
};

// The full `services` payload (guild, shop, and inventory sections all
// present). Every entry mirrors the exact bounded schema; the integer
// copper currency is display-formatted, never float money.
export const SERVICES_PANEL_SAMPLE = {
  schema_version: 1,
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
      { item_key: "item_iron_sword", display_name: "鐵劍", held: 1, equipped: true },
      { item_key: "item_leather_armor", display_name: "皮甲", held: 1, equipped: true },
      { item_key: "item_heal_potion", display_name: "治療劑", held: 4, equipped: false },
    ],
    wallet: 3240,
  },
  pagination: {
    board_total: 2,
    quest_total: 1,
    stock_total: 2,
    sellable_total: 1,
    inventory_total: 3,
  },
};

// The registry-owned unavailable form for the services panel: the common
// `{available: false, reason}` envelope (webclient-oob-protocol), carrying
// the panel-stable reason — no invented sections or default values.
export const SERVICES_PANEL_UNAVAILABLE_SAMPLE = {
  schema_version: 1,
  available: false,
  reason: { code: "services_unavailable", message: "服務選單目前無法顯示" },
};

// The reduced services payload: no host, no guild/shop/inventory sections
// (all null with zero pagination totals), a bare player summary.
export const SERVICES_PANEL_MINIMAL_SAMPLE = {
  schema_version: 1,
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
