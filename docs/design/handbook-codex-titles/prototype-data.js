// Synthetic fixtures for the Handbook prototype (reference only; not imported
// by the app). Shapes follow the proposed `lore_codex` schema v2 and the
// unchanged `title_codex` v1 from
// docs/superpowers/specs/2026-11-09-handbook-codex-titles-design.md.
// Monster art uses the pipeline's own offline fallback (`monster_anon`), the
// same image a player sees before a species portrait is generated; regions and
// anchors use bundled scene illustrations.

const MONSTER_FALLBACK = "/art/defaults/monster_anon.webp";
const scene = (key) => `/art/scenes/${key}.webp`;
const P = Object.freeze({ placeholder: true });

const LOCKED_MONSTER_FIELDS = ["published_description_zh", "published_ecology_zh", "habitat_tags", "variants"];

const crab = {
  key: "tide_lamp_crab",
  title: "潮燈蟹",
  stage: "defeated",
  art: MONSTER_FALLBACK,
  card: [
    { name: "published_appearance_zh", value: "近岸蟹類。背甲上帶著隨光明滅的發光斑紋。" },
    { name: "threat_tier", value: "低階" },
    { name: "published_description_zh", value: "近岸蟹類，棲息於兩側海岸的礁隙、潮池與港外灘地。" },
    {
      name: "published_ecology_zh",
      value:
        "背甲上的發光斑紋會追隨附近燈光的明暗節奏。沿岸居民知道牠們會聚集在魔法燈附近，漁人偶爾將牠們當成潮池的位置標記。大量聚集時，不熟悉港口的小船可能誤判岸邊訊號；靠近礁洞的人也可能受到螯足攻擊。",
    },
    { name: "habitat_tags", value: ["東南海岸", "西南海岸"] },
    {
      name: "variants",
      value: [
        { name: "行灘型", grade: "E" },
        { name: "守礁型", grade: "E" },
      ],
    },
  ],
  locked_fields: [],
};

const sparrow = {
  key: "sway_whistle_sparrow",
  title: "穗鳴雀",
  stage: "defeated",
  art: MONSTER_FALLBACK,
  card: [
    { name: "published_appearance_zh", value: "麻雀類的小型群居鳥。" },
    { name: "threat_tier", value: "低階" },
    { name: "published_description_zh", value: "麻雀類的小型群居鳥，生活於東部平原的田埂、灌木與收穫後的農地。" },
    {
      name: "published_ecology_zh",
      value:
        "啄食成熟穀物前，族群會發出短促而整齊的鳴聲，接著以微弱風屬性氣流震落乾燥穀粒。穗間響起的沙沙聲，是農民辨認牠們的線索。",
    },
    { name: "habitat_tags", value: ["東部平原"] },
    { name: "variants", value: [{ name: "領群型", grade: "F" }, { name: "啄穗型", grade: "F" }] },
  ],
  locked_fields: [],
};

const hare = {
  key: "ridge_burrow_hare",
  title: "築埂兔",
  stage: "sighted",
  art: MONSTER_FALLBACK,
  card: [
    { name: "published_appearance_zh", value: "穴居兔類。後腿粗壯，耳緣沾著乾土。" },
    { name: "threat_tier", value: "低階" },
  ],
  locked_fields: LOCKED_MONSTER_FIELDS,
};

const goat = {
  key: "rock_echo_goat",
  title: "岩響山羊",
  stage: "sighted",
  art: MONSTER_FALLBACK,
  card: [
    { name: "published_appearance_zh", value: "山羊類魔獸。角面布滿敲擊留下的細痕。" },
    { name: "threat_tier", value: "中階" },
  ],
  locked_fields: LOCKED_MONSTER_FIELDS,
};

const monsterCategory = {
  key: "monster",
  label: "魔物",
  discovered: 4,
  total: 10,
  groups: [
    { key: "low", label: "低階", slots: [sparrow, crab, hare, P, P, P] },
    { key: "mid", label: "中階", slots: [goat, P, P] },
    { key: "high", label: "高階", slots: [P] },
  ],
};

const one = (key, label, slots) => ({
  key,
  label,
  discovered: slots.filter((s) => !s.placeholder).length,
  total: slots.length,
  groups: [{ key: "all", label: null, slots }],
});

const entry = (key, title, art, card) => ({ key, title, stage: null, art, card, locked_fields: [] });

export const CODEX_POPULATED = {
  schema_version: 2,
  available: true,
  discovered_total: 9,
  total: 52,
  categories: [
    monsterCategory,
    one("race", "種族", [
      entry("human", "人類", null, [
        { name: "description", value: "適應力最強的短命種，散居於大陸各地，以城邦與王國為主要聚落。" },
      ]),
      P,
      P,
      P,
    ]),
    one("nation", "國家", [P, P, P]),
    one("region", "地域", [
      entry("eastern_plains", "東部大平原", scene("wilderness_path"), [
        { name: "terrain_flavor_zh", value: "收穫季節金浪翻湧的寬闊平原，田埂與灌木縱橫交錯，偶有群鳥起落。" },
      ]),
      entry("western_hills_valleys", "西部丘陵", scene("mountain_path"), [
        { name: "terrain_flavor_zh", value: "岩坡與採石地交錯的起伏丘陵，山麓的運料道狹窄而曲折。" },
      ]),
      P,
      P,
      P,
    ]),
    one("anchor", "地點", [
      entry("capital_altoria", "聖潔王都", scene("city_street"), [
        { name: "description", value: "阿爾托利亞王國的首都，坐落於西部河谷與丘陵之間，河岸以下是繁忙的碼頭區。" },
      ]),
      P,
      P,
      P,
      P,
      P,
      P,
      P,
    ]),
    one("element", "元素", [
      entry("wind", "風", null, [{ name: "description", value: "流動與輕盈的屬性，擅長擾動、加速與震落。" }]),
      P,
      P,
      P,
      P,
      P,
    ]),
    one("magic", "魔法", [P, P, P, P]),
    one("guild", "公會", [
      entry("f_rank", "F 級", null, [{ name: "description", value: "冒險者公會的起點等級，可承接最基本的委託。" }]),
      P,
      P,
      P,
      P,
      P,
      P,
    ]),
  ],
};

const emptyCategory = (cat) => ({
  ...cat,
  discovered: 0,
  groups: cat.groups.map((g) => ({ ...g, slots: g.slots.map(() => P) })),
});

export const CODEX_EMPTY = {
  ...CODEX_POPULATED,
  discovered_total: 0,
  categories: CODEX_POPULATED.categories.map(emptyCategory),
};

// The unchanged `title_codex` v1 panel.
export const TITLES = {
  schema_version: 1,
  available: true,
  fixed_rows: [
    { key: "g_f_rank", display: "F級冒險者", category: "guild", hint: "", flavor: "公會註冊的起點。", unlocked: true, granted_tick: 120 },
    { key: "g_e_rank", display: "E級冒險者", category: "guild", hint: "通過 E 級升級測驗。", flavor: "", unlocked: false, granted_tick: 0 },
    { key: "g_d_rank", display: "D級冒險者", category: "guild", hint: "通過 D 級升級測驗。", flavor: "", unlocked: false, granted_tick: 0 },
    { key: "g_c_rank", display: "C級冒險者", category: "guild", hint: "通過 C 級升級測驗。", flavor: "", unlocked: false, granted_tick: 0 },
    { key: "g_b_rank", display: "B級冒險者", category: "guild", hint: "通過 B 級升級測驗。", flavor: "", unlocked: false, granted_tick: 0 },
    { key: "g_a_rank", display: "A級冒險者", category: "guild", hint: "通過 A 級升級測驗。", flavor: "", unlocked: false, granted_tick: 0 },
    { key: "g_s_rank", display: "S級冒險者", category: "guild", hint: "通過 S 級升級測驗。", flavor: "", unlocked: false, granted_tick: 0 },
    { key: "c_first_blood", display: "初陣", category: "combat", hint: "", flavor: "第一次在戰鬥中取勝。", unlocked: true, granted_tick: 98 },
    { key: "c_hundred", display: "百戰", category: "combat", hint: "累計取得一百場戰鬥勝利。", flavor: "", unlocked: false, granted_tick: 0 },
    { key: "c_giant_slayer", display: "屠巨者", category: "combat", hint: "擊敗一頭高階魔物。", flavor: "", unlocked: false, granted_tick: 0 },
    { key: "e_wayfarer", display: "行旅者", category: "explore", hint: "", flavor: "踏上三個不同地域。", unlocked: true, granted_tick: 140 },
    { key: "e_cartographer", display: "繪圖師", category: "explore", hint: "探明一整個地區。", flavor: "", unlocked: false, granted_tick: 0 },
    { key: "s_apprentice", display: "見習術士", category: "spell", hint: "習得第一個法術。", flavor: "", unlocked: false, granted_tick: 0 },
    { key: "r_admirer", display: "多情客", category: "romance", hint: "與三位人物建立親密關係。", flavor: "", unlocked: false, granted_tick: 0 },
  ],
  epithet_rows: [
    { display: "破城先鋒", basis: "攻打舊堡時率先破門。", granted_tick: 121, equipped: false, can_remove: true },
    { display: "苔徑新客", basis: "初次走入苔徑。", granted_tick: 120, equipped: true, can_remove: false },
    { display: "燈下拾蟹人", basis: "在港外燈下連續擊退潮燈蟹群。", granted_tick: 133, equipped: false, can_remove: true },
  ],
  equipped: { fixed: "g_f_rank", epithet: "苔徑新客" },
  full_title: "F級冒險者　苔徑新客",
  unlocked: 3,
  total: 14,
  pending_ballot: [
    { display: "夜襲之人", basis: "夜半三度出入敵陣。" },
    { display: "不屈之壁", basis: "重傷仍守住隘口。" },
  ],
};

export const TITLES_NO_BALLOT = { ...TITLES, pending_ballot: [] };
