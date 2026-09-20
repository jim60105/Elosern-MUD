// Story fixture slices: see stories/fixtures.js (facade) for the public surface.

// B5 (webclient-vue-06-showcase-overlays): full-overlays fixtures. The
// `creation` panel (schema v5) mirrors web/webclient/presentation/creation.py
// exactly: presets (at most 8 cards), the custom descriptor (name/age
// bounds, races, subraces, profiles, affinity, sex), and the optional saved
// wizard draft (preset/custom + background + affinity + persona + sex) plus
// the optional transient concept proposal slot. The age
// bounds advertise the 0 minimum on BOTH age and apparent_age (the
// deterministic age bounds gate, webclient-character-creation-ui).
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
  schema_version: 5,
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
    age: {
      age_minimum: 0,
      age_maximum: 10000,
      apparent_age_minimum: 0,
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
        budget: 28,
        axes: [
          { axis: "hp", label: "生命", explanation: "承傷能力", minimum: 0, maximum: 8 },
          { axis: "mp", label: "魔力", explanation: "法術資源", minimum: 0, maximum: 4 },
          { axis: "sp", label: "精神", explanation: "精神資源", minimum: 0, maximum: 4 },
          { axis: "atk_phys", label: "攻擊", explanation: "近戰傷害", minimum: 0, maximum: 4 },
          { axis: "agility", label: "敏捷", explanation: "閃避與先攻", minimum: 0, maximum: 4 },
          { axis: "defense", label: "防禦", explanation: "傷害減輕", minimum: 0, maximum: 4 },
          { axis: "magic_power", label: "魔力", explanation: "魔法傷害", minimum: 0, maximum: 4 },
        ],
      },
      {
        race: "beastfolk",
        subrace: "subrace_wolf",
        budget: 30,
        axes: [
          { axis: "hp", label: "生命", explanation: "承傷能力", minimum: 0, maximum: 9 },
          { axis: "mp", label: "魔力", explanation: "法術資源", minimum: 0, maximum: 4 },
          { axis: "sp", label: "精神", explanation: "精神資源", minimum: 0, maximum: 4 },
          { axis: "atk_phys", label: "攻擊", explanation: "近戰傷害", minimum: 0, maximum: 5 },
          { axis: "agility", label: "敏捷", explanation: "閃避與先攻", minimum: 0, maximum: 4 },
          { axis: "defense", label: "防禦", explanation: "傷害減輕", minimum: 0, maximum: 4 },
          { axis: "magic_power", label: "魔力", explanation: "魔法傷害", minimum: 0, maximum: 4 },
        ],
      },
      {
        race: "elf",
        subrace: null,
        budget: 26,
        axes: [
          { axis: "hp", label: "生命", explanation: "承傷能力", minimum: 0, maximum: 6 },
          { axis: "mp", label: "魔力", explanation: "法術資源", minimum: 0, maximum: 6 },
          { axis: "sp", label: "精神", explanation: "精神資源", minimum: 0, maximum: 4 },
          { axis: "atk_phys", label: "攻擊", explanation: "近戰傷害", minimum: 0, maximum: 3 },
          { axis: "agility", label: "敏捷", explanation: "閃避與先攻", minimum: 0, maximum: 5 },
          { axis: "defense", label: "防禦", explanation: "傷害減輕", minimum: 0, maximum: 4 },
          { axis: "magic_power", label: "魔力", explanation: "魔法傷害", minimum: 0, maximum: 4 },
        ],
      },
    ],
    affinity: {
      human: { maximum: 2, elements: ELEMENTS },
      beastfolk: { maximum: 1, elements: ELEMENTS },
      elf: { maximum: 0, elements: ELEMENTS },
    },
    // Server-labelled sex options in SEX_VALUES order (namegen-creation-ui
    // D4); the browser renders these labels verbatim.
    sex: [
      { key: "female", label: "女性" },
      { key: "male", label: "男性" },
      { key: "other", label: "其他" },
    ],
  },
};

// The created-draft forms the wizard can resume at reconnect: the
// server-persisted stages (preset_selected, custom_filled — the concept
// stage was retired by retool-concept-transient-fill), mirroring the wire
// shapes in creation.py.
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
    allocations: { hp: 8, mp: 4, sp: 4, atk_phys: 4, agility: 2, defense: 2, magic_power: 4 },
    background: "從渡口學來運貨的年輕人。",
    affinity_elements: ["fire", "wind"],
    sex: "male",
    persona: {
      personality: "沉穩寡言",
      life_story: "在霧骨渡口搬運貨物長大的年輕人。",
      habit: "每天清晨沿河岸慢跑。",
    },
  },
};

// The session-transient concept proposal slot (retool-concept-transient-fill
// D1): the optional top-level key a same-session panel carries after a
// concept apply, with the exact five-key shape including a revision number.
export const CREATION_PANEL_PROPOSAL_SAMPLE = {
  ...CREATION_PANEL_SAMPLE,
  proposal: {
    revision: 1,
    race: "elf",
    subrace: null,
    allocations: { hp: 6, mp: 6, sp: 2, atk_phys: 2, agility: 4, defense: 2, magic_power: 4 },
    persona: {
      personality: "沉穩內斂",
      life_story: "燈下研讀古籍的年輕學者。",
      habit: "睡前必整理書架。",
    },
  },
};

// The expanded v3 proposal shape (bump-creation-panel-proposal-v3 +
// retool-concept-fill-navigation): the five-key persona payload plus the
// five transient-fill keys. The race is human so the affinity cap (2) is
// visible, and the wire carries three elements — the form must keep only
// the first two (registered keys, cap-trimmed). The ages and prose are the
// generation layer's already-normalized values (range-clamped, truncated).
export const CREATION_PANEL_PROPOSAL_TRANSIENT_SAMPLE = {
  ...CREATION_PANEL_SAMPLE,
  proposal: {
    revision: 1,
    race: "human",
    subrace: null,
    allocations: { hp: 6, mp: 4, sp: 4, atk_phys: 4, agility: 4, defense: 3, magic_power: 3 },
    persona: {
      personality: "沉穩內斂",
      life_story: "燈下研讀古籍的年輕學者。",
      habit: "睡前必整理書架。",
    },
    display_name: "莉雅",
    age: 26,
    apparent_age: 24,
    background: "燈下抄書的女學徒。",
    affinity_elements: ["fire", "wind", "water"],
  },
};

// The `creation` panel unavailable form (registry-owned reason, the common
// unavailable envelope).
export const CREATION_PANEL_UNAVAILABLE_SAMPLE = {
  schema_version: 5,
  available: false,
  reason: { code: "creation_unavailable", message: "角色創建目前無法顯示" },
};