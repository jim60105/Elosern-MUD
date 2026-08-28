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

// The committed `character` v4 payload for the same actor: all eight trait
// rows (gauges carry max, statics/counters carry null max), grouped active
// and passive skills, equipped items, an active disguise whose displayed
// values differ from the true traits, guild rank/merit, wallet, persona,
// and the populated intimate status (the 設計稿's 親密狀態 values verbatim).
export const CHARACTER_PANEL_SAMPLE = {
  schema_version: 4,
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
   intimate: {
     arousal: "中等",
     wetness: "微濕",
     shame: "輕微",
     exposure: "低",
     climax_phase: "未達",
     climax_today: 2,
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
  intimate: null,
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
              usable_out_of_combat: true,
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
        {
          group: "wind",
          label: "風",
          skills: [
            {
              key: "gale_dash",
              label: "疾風突進",
              cost: { sp: 8 },
              target_spec: "self",
              usable_out_of_combat: true,
            },
          ],
        },
        {
          group: "earth",
          label: "土",
          skills: [
            {
              key: "quake",
              label: "震地",
              cost: { mp: 24 },
              target_spec: "area",
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
    {
      category: "sexual_act",
      label: "性愛行為",
      groups: [
        {
          group: "solo",
          label: "獨處",
          skills: [
            {
              key: "solace",
              label: "自我撫慰",
              cost: {},
              target_spec: "self",
              usable_out_of_combat: true,
            },
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
// services v2 — so the offline showcase asserts truthfulness: the lattice
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

// The maximal-height, minimal-width lattice (task 3.5): exactly 64 in-view
// nodes — one node per row across 64 rows, alternating the two columns
// (x = y % 2) — a schema-valid worst-case tall map sitting exactly at the
// model's 64-node bound. The renderer must scale the canvas down to fit
// the island's bounded height instead of forcing the island to scroll a
// required surface out of view. Every 16th row carries a 6-CJK label so the
// truncation path (LABEL_MAX chars + ellipsis) is exercised.
const TALL_LATTICE_ROWS = 64;
const TALL_LATTICE_NODES = Array.from({ length: TALL_LATTICE_ROWS }, (_, y) => {
  const x = y % 2;
  const isCurrent = y === 32;
  return {
    id: `grid:altoria:${x}:${y}`,
    label: y % 16 === 0 ? "霧骨渡口碼頭" : `渡口${y % 8}`,
    x,
    y,
    visibility: isCurrent ? "current" : "visible_unvisited",
    current: isCurrent,
    anchor: isCurrent,
    landmark: isCurrent,
    action: null,
  };
});

export const LOCAL_MAP_TALL_LATTICE_SAMPLE = {
  schema_version: 1,
  available: true,
  layer: "grid",
  current_node: "grid:altoria:0:32",
  title: "霧骨渡口",
  nodes: TALL_LATTICE_NODES,
  edges: [
    { source: "grid:altoria:0:32", destination: "grid:altoria:1:33", label: "北岸", known: true, traversable: true },
    { source: "grid:altoria:0:32", destination: "grid:altoria:1:31", label: "南門", known: true, traversable: false },
  ],
  legend: [
    "你目前所在的位置",
    "尚未探索的相鄰位置",
    "已經探索過的相鄰位置",
  ],
};

// The tall-lattice + long-remembered-list combination (rubber-duck blocking
// issue): 48 in-view nodes (2 cols × 48 rows) + 16 remembered far nodes =
// 64 nodes total, hitting the model's MAX_NODES bound. The island's
// dynamically measured canvas height cap must reserve space for the
// remembered list so the anchor never scrolls.
const TALL_REMEMBERED_INVIEW_NODES = Array.from({ length: 48 }, (_, y) => {
  const x = y % 2;
  const isCurrent = y === 24;
  return {
    id: `grid:altoria:${x}:${y}`,
    label: y % 16 === 0 ? "霧骨渡口碼頭" : `渡口${y % 8}`,
    x,
    y,
    visibility: isCurrent ? "current" : "visible_unvisited",
    current: isCurrent,
    anchor: isCurrent,
    landmark: isCurrent,
    action: null,
  };
});

const TALL_REMEMBERED_FAR_NODES = Array.from({ length: 16 }, (_, i) => ({
  id: `grid:altoria:${5 + i % 6}:${100 + i}`,
  label: "遠方路網",
  x: 5 + i % 6,
  y: 100 + i,
  visibility: "remembered",
  current: false,
  anchor: false,
  landmark: true,
  action: null,
}));

export const LOCAL_MAP_TALL_REMEMBERED_SAMPLE = {
  schema_version: 1,
  available: true,
  layer: "grid",
  current_node: "grid:altoria:0:24",
  title: "霧骨渡口",
  nodes: [...TALL_REMEMBERED_INVIEW_NODES, ...TALL_REMEMBERED_FAR_NODES],
  edges: [
    { source: "grid:altoria:0:24", destination: "grid:altoria:1:25", label: "北岸", known: true, traversable: true },
    { source: "grid:altoria:0:24", destination: "grid:altoria:1:23", label: "南門", known: true, traversable: false },
  ],
  legend: [
    "你目前所在的位置",
    "尚未探索的相鄰位置",
    "已經探索過的相鄰位置",
  ],
};

// The dedicated geometry-stress fixture (rubber-duck critique): horizontally
// and vertically adjacent nodes, the current 26×26 rect and the stroked
// `visible_unvisited` circle (visual half-extent 13px including stroke), 4-
// CJK labels (truncated at LABEL_MAX with an ellipsis when longer), and two
// adjacent connector edges. It pins the pre-scale non-intersection invariant
// at the renderer's own pitch constants.
export const LOCAL_MAP_GEOMETRY_STRESS_SAMPLE = {
  schema_version: 1,
  available: true,
  layer: "grid",
  current_node: "grid:altoria:1:1",
  title: "霧骨渡口",
  nodes: [
    {
      id: "grid:altoria:1:1",
      label: "霧骨渡口",
      x: 1,
      y: 1,
      visibility: "current",
      current: true,
      anchor: true,
      landmark: true,
      action: null,
    },
    {
      id: "grid:altoria:2:1",
      label: "南門街道市場",
      x: 2,
      y: 1,
      visibility: "visible_unvisited",
      current: false,
      anchor: false,
      landmark: false,
      action: { kind: "move", exit_ref: "e_altoria_1_1_e", destination: "grid:altoria:2:1" },
    },
    {
      id: "grid:altoria:1:2",
      label: "碼頭廣場舊街",
      x: 1,
      y: 2,
      visibility: "visible_unvisited",
      current: false,
      anchor: false,
      landmark: false,
      action: null,
    },
    {
      id: "grid:altoria:0:1",
      label: "旅館公會",
      x: 0,
      y: 1,
      visibility: "visible_visited",
      current: false,
      anchor: true,
      landmark: false,
      action: null,
    },
  ],
  edges: [
    { source: "grid:altoria:1:1", destination: "grid:altoria:2:1", label: "南門", known: true, traversable: true },
    { source: "grid:altoria:1:1", destination: "grid:altoria:1:2", label: "碼頭", known: true, traversable: false },
  ],
  legend: [
    "你目前所在的位置",
    "尚未探索的相鄰位置",
    "已經探索過的相鄰位置",
  ],
};

// The single-node room (delta spec scenario "A single-node room states
// orientation without any collision risk"): exactly one current node, no
// neighbors to collide with — the pitch/sizing change must produce no
// regression for the single-node case.
export const LOCAL_MAP_SINGLE_NODE_SAMPLE = {
  schema_version: 1,
  available: true,
  layer: "grid",
  current_node: "grid:altoria:1:1",
  title: "霧骨渡口",
  nodes: [
    {
      id: "grid:altoria:1:1",
      label: "霧骨渡口",
      x: 1,
      y: 1,
      visibility: "current",
      current: true,
      anchor: true,
      landmark: true,
      action: null,
    },
  ],
  edges: [],
  legend: ["你目前所在的位置"],
};

// The wilderness layer: coordinate-bearing nodes (the renderer-axis
// orientation legend 北↑ applies).
export const LOCAL_MAP_WILDERNESS_SAMPLE = {
  schema_version: 1,
  available: true,
  layer: "wilderness",
  current_node: "wild:plains:3:1",
  title: "灰鬮荒原",
  nodes: [
    {
      id: "wild:plains:3:1",
      label: "灰鬮荒原",
      x: 3,
      y: 1,
      visibility: "current",
      current: true,
      anchor: true,
      landmark: true,
      action: null,
    },
    {
      id: "wild:plains:4:1",
      label: "獵人小徑",
      x: 4,
      y: 1,
      visibility: "visible_unvisited",
      current: false,
      anchor: false,
      landmark: false,
      action: { kind: "move", exit_ref: "e_plains_3_1_e", destination: "wild:plains:4:1" },
    },
    {
      id: "wild:plains:2:2",
      label: "舊營地",
      x: 2,
      y: 2,
      visibility: "visible_visited",
      current: false,
      anchor: false,
      landmark: true,
      action: null,
    },
    {
      id: "wild:plains:7:5",
      label: "遠處山徑",
      x: 7,
      y: 5,
      visibility: "remembered",
      current: false,
      anchor: false,
      landmark: true,
      action: null,
    },
  ],
  edges: [
    { source: "wild:plains:3:1", destination: "wild:plains:4:1", label: "獵人小徑", known: true, traversable: true },
    { source: "wild:plains:3:1", destination: "wild:plains:2:2", label: "舊營地", known: true, traversable: false },
  ],
  legend: [
    "你目前所在的位置",
    "尚未探索的相鄰位置",
    "已經探索過的相鄰位置",
  ],
};

// The instance layer: the presenter's layout-index coordinates (a
// coordinate-free graph — the orientation legend is omitted).
export const LOCAL_MAP_INSTANCE_SAMPLE = {
  schema_version: 1,
  available: true,
  layer: "instance",
  current_node: "room:101",
  title: "洞窟",
  nodes: [
    {
      id: "room:101",
      label: "洞窟入口",
      x: 0,
      y: 0,
      visibility: "current",
      current: true,
      anchor: false,
      landmark: false,
      action: null,
    },
    {
      id: "room:102",
      label: "南門",
      x: 0,
      y: 1,
      visibility: "visible_visited",
      current: false,
      anchor: false,
      landmark: false,
      action: null,
    },
    {
      id: "room:103",
      label: "未探索",
      x: 1,
      y: 0,
      visibility: "visible_unvisited",
      current: false,
      anchor: false,
      landmark: false,
      action: { kind: "move", exit_ref: "e_cave_exit", destination: "room:103" },
    },
  ],
  edges: [
    { source: "room:101", destination: "room:102", label: "回程", known: true, traversable: true },
    { source: "room:101", destination: "room:103", label: "進洞窟", known: false, traversable: true },
  ],
  legend: ["你目前所在的位置", "尚未探索的相鄰位置"],
};

// The interior layer: the same layout-index coordinate shape as instance
// (coordinate-free graph — the orientation legend is omitted).
export const LOCAL_MAP_INTERIOR_SAMPLE = {
  schema_version: 1,
  available: true,
  layer: "interior",
  current_node: "room:201",
  title: "公會大廳",
  nodes: [
    {
      id: "room:201",
      label: "公會大廳",
      x: 0,
      y: 0,
      visibility: "current",
      current: true,
      anchor: false,
      landmark: false,
      action: null,
    },
    {
      id: "room:202",
      label: "訓練場",
      x: 1,
      y: 0,
      visibility: "visible_visited",
      current: false,
      anchor: false,
      landmark: false,
      action: { kind: "move", exit_ref: "e_hall_training", destination: "room:202" },
    },
  ],
  edges: [
    { source: "room:201", destination: "room:202", label: "訓練場", known: true, traversable: true },
  ],
  legend: ["你目前所在的位置"],
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
  schema_version: 3,
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
// presentation metadata (redesign-inventory-item-grid): the row set covers
// every closed `ItemIconKey`/`ItemKind` value (food, potion, weapon, armor,
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
          summary: "基本远程箭矢。",
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
  schema_version: 3,
  available: false,
  reason: { code: "services_unavailable", message: "服務選單目前無法顯示" },
};

// The reduced services payload: no host, no guild/shop/inventory sections
// (all null with zero pagination totals), a bare player summary.
export const SERVICES_PANEL_MINIMAL_SAMPLE = {
  schema_version: 3,
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

// B5 (webclient-vue-06-showcase-overlays): full-overlays fixtures. The
// `creation` panel (schema v1) mirrors web/webclient/presentation/creation.py
// exactly: presets (at most 8 cards), the custom descriptor (name/adult
// bounds, races, subraces, profiles, affinity), and the optional saved
// wizard draft (preset/custom/concept + background + affinity). The adult
// bounds advertise the 18 minimum on BOTH age and apparent_age (the
// deterministic adult gate, webclient-character-creation-ui).
const ELEMENTS = [
  { key: "fire", label: "火" },
  { key: "water", label: "水" },
  { key: "wind", label: "風" },
  { key: "earth", label: "土" },
  { key: "lightning", label: "雷" },
  { key: "ice", label: "冰" },
  { key: "light", label: "光" },
  { key: "dark", label: "暗" },
];

export const CREATION_PANEL_SAMPLE = {
  schema_version: 1,
  available: true,
  kind: "creation",
  draft: null,
  presets: [
    {
      key: "preset_wandering_blade",
      display_name: "流浪劍客",
      race: "beastfolk",
      race_description: "獸民：堅韌、忠實，長於戰技。",
      subrace: "subrace_wolf",
      emphasis: "重擊與近戰",
      background: "一位尋找冒險者公會試煉的流浪劍客。",
    },
    {
      key: "preset_lantern_scholar",
      display_name: "燈下學士",
      race: "elf",
      race_description: "精靈：長壽、敏銳，長於學藝。",
      subrace: null,
      emphasis: "法術與研究",
      background: "在燈下研讀古籍的學士。",
    },
    {
      key: "preset_harbor_hauler",
      display_name: "碼頭腳夫",
      race: "human",
      race_description: "人族：均衡、勤奮，長於商貿。",
      subrace: null,
      emphasis: "搬運與交易",
      background: "在霧骨渡口搬運貨物的腳夫。",
    },
  ],
  custom: {
    name: { min_length: 1, max_length: 64 },
    adult: {
      age_minimum: 18,
      age_maximum: 10000,
      apparent_age_minimum: 18,
      apparent_age_maximum: 10000,
    },
    races: [
      {
        key: "human",
        description: "人族：均衡、勤奮，商貿立族。",
        subraces: null,
      },
      {
        key: "beastfolk",
        description: "獸民：堅韌、忠實，戰技立族。",
        subraces: ["subrace_wolf", "subrace_bear"],
      },
      {
        key: "elf",
        description: "精靈：長壽、敏銳，學藝立族。",
        subraces: null,
      },
    ],
    subraces: {
      subrace_wolf: {
        display_name_zh: "狼裔",
        common_name_zh: "狼",
        specialty: "追獵與近戰",
      },
      subrace_bear: {
        display_name_zh: "熊裔",
        common_name_zh: "熊",
        specialty: "耐力與防護",
      },
    },
    profiles: [
      {
        race: "human",
        subrace: null,
        budget: 24,
        axes: [
          { axis: "hp", label: "生命", explanation: "承傷能力", minimum: 0, maximum: 8 },
          { axis: "mp", label: "魔力", explanation: "法術資源", minimum: 0, maximum: 4 },
          { axis: "sp", label: "精神", explanation: "精神資源", minimum: 0, maximum: 4 },
          { axis: "atk_phys", label: "攻擊", explanation: "近戰傷害", minimum: 0, maximum: 4 },
          { axis: "agility", label: "敏捷", explanation: "閃避與先攻", minimum: 0, maximum: 4 },
          { axis: "defense", label: "防禦", explanation: "傷害減輕", minimum: 0, maximum: 4 },
        ],
      },
      {
        race: "beastfolk",
        subrace: "subrace_wolf",
        budget: 26,
        axes: [
          { axis: "hp", label: "生命", explanation: "承傷能力", minimum: 0, maximum: 9 },
          { axis: "mp", label: "魔力", explanation: "法術資源", minimum: 0, maximum: 4 },
          { axis: "sp", label: "精神", explanation: "精神資源", minimum: 0, maximum: 4 },
          { axis: "atk_phys", label: "攻擊", explanation: "近戰傷害", minimum: 0, maximum: 5 },
          { axis: "agility", label: "敏捷", explanation: "閃避與先攻", minimum: 0, maximum: 4 },
          { axis: "defense", label: "防禦", explanation: "傷害減輕", minimum: 0, maximum: 4 },
        ],
      },
      {
        race: "elf",
        subrace: null,
        budget: 22,
        axes: [
          { axis: "hp", label: "生命", explanation: "承傷能力", minimum: 0, maximum: 6 },
          { axis: "mp", label: "魔力", explanation: "法術資源", minimum: 0, maximum: 6 },
          { axis: "sp", label: "精神", explanation: "精神資源", minimum: 0, maximum: 4 },
          { axis: "atk_phys", label: "攻擊", explanation: "近戰傷害", minimum: 0, maximum: 3 },
          { axis: "agility", label: "敏捷", explanation: "閃避與先攻", minimum: 0, maximum: 5 },
          { axis: "defense", label: "防禦", explanation: "傷害減輕", minimum: 0, maximum: 4 },
        ],
      },
    ],
    affinity: {
      human: { maximum: 2, elements: ELEMENTS },
      beastfolk: { maximum: 1, elements: ELEMENTS },
      elf: { maximum: 0, elements: ELEMENTS },
    },
  },
};

// The created-draft forms the wizard can resume at reconnect: the
// server-persisted stages (preset_selected, custom_filled, concept_filled),
// mirroring the wire shapes in creation.py.
export const CREATION_PANEL_PRESET_DRAFT_SAMPLE = {
  ...CREATION_PANEL_SAMPLE,
  draft: { mode: "preset", stage: "preset_selected", preset_key: "preset_lantern_scholar" },
};

export const CREATION_PANEL_CUSTOM_DRAFT_SAMPLE = {
  ...CREATION_PANEL_SAMPLE,
  draft: {
    mode: "custom",
    stage: "custom_filled",
    display_name: "林楓",
    age: 21,
    apparent_age: 21,
    race: "human",
    subrace: null,
    allocations: { hp: 8, mp: 4, sp: 4, atk_phys: 4, agility: 2, defense: 2 },
    background: "從渡口學來運貨的年輕人。",
    background_generated: false,
    affinity_elements: ["fire", "wind"],
  },
};

export const CREATION_PANEL_CONCEPT_DRAFT_SAMPLE = {
  ...CREATION_PANEL_SAMPLE,
  draft: {
    mode: "concept",
    stage: "concept_filled",
    race: "elf",
    subrace: null,
    allocations: { hp: 6, mp: 6, sp: 2, atk_phys: 2, agility: 4, defense: 2 },
    background: "燈下讀書的年輕學者。",
    background_generated: true,
  },
};

// The `creation` panel unavailable form (registry-owned reason, the common
// unavailable envelope).
export const CREATION_PANEL_UNAVAILABLE_SAMPLE = {
  schema_version: 1,
  available: false,
  reason: { code: "creation_unavailable", message: "角色創建目前無法顯示" },
};

// The onboarding guide content (help surface): the authored arrival prose,
// the South-Gate guard's scripted guidance, and the keyword Q&A set, as
// carried by the onboarding-guide capability (the game-authored help copy,
// rendered verbatim, no invented content).
export const ONBOARDING_GUIDE_SAMPLE = {
  arrival: {
    prose: "晨霧未散的聖潔王都，南城門在你身後緩緩合攏。城牆上的石磚磨出了細紋，守衛的腳步聲由遠而近。",
    prompt: "守衛低聲說：「先試試「看」，看看你身處之處。」",
  },
  guard: {
    name: "南門守衛",
    guidance: "先北行至南大道，再東行至冒險者公會外。公會可接取任務、購買物資、登記會員。",
  },
  qna: [
    { question: "看", answer: "「看」會描繪你眼前的景象，是探索的第一步。" },
    { question: "公會", answer: "冒險者公會就在南東側，是接取任務與登記會員之處。" },
    { question: "任務", answer: "公會任務榜上有可接取的任務，完成後可領取報酬。" },
    { question: "商店", answer: "公會旁的商店可購買基本物資，價格以銅幣計。" },
  ],
};
