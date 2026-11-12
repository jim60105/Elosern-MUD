// Synthetic fixtures for the Design/GalleryWindow prototype. Reference only:
// the shapes sketch the proposed category-scoped gallery panel, not a wire
// contract. Every image is a committed built-in fallback or bundled scene.

const P = (name) => `/art/defaults/${name}.webp`;
const S = (name) => `/art/scenes/${name}.webp`;

let serial = 0;
const card = (url, extra = {}) => ({
  id: `c${++serial}`,
  label: "肖像",
  url,
  status: "card",
  isDefault: false,
  chips: [],
  date: "3 天前",
  exact: "2026年11月9日 下午2:10",
  conditions: [],
  ...extra,
});
const official = (url, label) => ({ id: `o${++serial}`, label, url, official: true });

const character = (key, name, face, extra = {}) => ({
  key,
  name,
  kind: "character",
  art: P(face),
  maxCards: null,
  cards: [],
  official: [],
  ...extra,
});

const monster = (key, name, extra = {}) => ({
  key,
  name,
  kind: "monster",
  art: P("monster_anon"),
  maxCards: 1,
  cards: [card(P("monster_anon"), { chips: ["預設臉框"], date: "5 天前" })],
  official: [],
  ...extra,
});

// A scene shows its generated image, or the bundled official one until a
// generated image exists.
const scene = (key, name, sentence, generated = true) => ({
  key,
  name,
  kind: "scene",
  art: S(key),
  maxCards: 1,
  sentence,
  cards: [
    generated
      ? card(S(key), { label: "生成圖", date: "8 天前" })
      : card(S(key), { label: "官方內建圖", bundled: true, date: "內建", exact: "" }),
  ],
  official: [],
});

const MINE = [
  character("pc:1", "夜行者", "woman", {
    current: true,
    cards: [
      card(P("woman"), {
        isDefault: true,
        chips: ["主手", "防具", "預設臉框"],
        date: "2 天前",
        conditions: ["主手：暗影劍刃", "防具：黑夜長袍"],
      }),
      card(P("woman"), { chips: ["飾品"], conditions: ["飾品：月長石墜飾"] }),
      card(P("girl"), { chips: ["預設臉框"] }),
      card(P("woman"), { date: "6 天前" }),
      card(P("woman"), { status: "pending", label: "肖像（生成中）", date: "剛剛" }),
      card(P("woman"), { status: "failed", label: "暫時無法生成，稍後再試", date: "1 小時前" }),
    ],
    official: [official(P("woman"), "官方圖片・成年女性"), official(P("girl"), "官方圖片・少女")],
  }),
  character("pc:2", "灰燼", "man", { cards: [card(P("man"), { isDefault: true, chips: ["預設臉框"] })] }),
  character("pc:3", "小鈴", "girl", { cards: [] }),
];

const PARTY = [
  character("npc:11", "艾拉", "woman", {
    cards: [
      card(P("woman"), { isDefault: true, chips: ["主手", "預設臉框"], conditions: ["主手：白樺長弓"] }),
      card(P("woman"), { chips: ["防具"], conditions: ["防具：旅人斗篷"] }),
      card(P("girl")),
      card(P("woman"), { date: "9 天前" }),
      card(P("woman"), { date: "12 天前" }),
    ],
    official: [official(P("woman"), "官方圖片・成年女性")],
  }),
  character("npc:12", "柯恩", "man", { cards: [card(P("man"), { isDefault: true }), card(P("elder"))] }),
  character("npc:13", "蜜拉", "girl", { cards: [] }),
];

const person = (key, name, face, n = 1) =>
  character(key, name, face, {
    cards: Array.from({ length: n }, (_, i) => card(P(face), { isDefault: i === 0 })),
  });

export const GALLERY = {
  categories: [
    { key: "mine", label: "我的角色", glyph: "emblem_race" },
    { key: "party", label: "隊友", glyph: "party" },
    { key: "people", label: "人物", glyph: "emblem_nation" },
    { key: "monster", label: "魔物", glyph: "emblem_monster" },
    { key: "scene", label: "背景", glyph: "emblem_region" },
  ],
  groups: {
    mine: [{ key: "mine", label: null, slots: MINE }],
    party: [{ key: "party", label: null, slots: PARTY }],
    // Second specification: people grouped by where the character last
    // interacted with them, most recent place first; one place is expanded
    // at a time.
    people: [
      {
        key: "altoria",
        label: "阿爾托利亞",
        collapsible: true,
        count: 7,
        slots: [
          person("npc:21", "薇絲妲", "woman", 2),
          person("npc:22", "鐵匠波頓", "man"),
          person("npc:23", "米菈", "girl"),
          person("npc:24", "老約翰", "elder"),
          person("npc:25", "提姆", "boy"),
          person("npc:26", "守衛長", "man"),
          person("npc:27", "藥師艾芙", "woman"),
        ],
      },
      {
        key: "southwest_coast",
        label: "西南海岸",
        collapsible: true,
        count: 3,
        slots: [person("npc:31", "燈塔看守人", "elder"), person("npc:32", "漁家少女", "girl"), person("npc:33", "船老大", "man")],
      },
      { key: "western_hills", label: "西部丘陵", collapsible: true, count: 2, slots: [person("npc:41", "牧羊人", "boy"), person("npc:42", "行腳商人", "man")] },
    ],
    monster: [
      {
        key: "low",
        label: "低階",
        discovered: 4,
        total: 14,
        slots: [monster("m:slime", "史萊姆"), monster("m:goblin", "哥布林"), monster("m:giant_rat", "巨鼠"), monster("m:crab", "潮燈蟹", { cards: [] })],
      },
      { key: "mid", label: "中階", discovered: 2, total: 18, slots: [monster("m:wolf", "魔狼"), monster("m:ogre", "食人魔")] },
      { key: "high", label: "高階", discovered: 0, total: 14, slots: [] },
      { key: "calamity", label: "災厄", discovered: 0, total: 6, slots: [] },
    ],
    scene: [
      {
        key: "scene",
        label: null,
        slots: [
          scene("forest_path", "林間小徑", "陽光穿過層疊的枝葉，灑在一條蜿蜒的林間小徑上，四周寂靜得只剩下風聲。"),
          scene("tavern_interior", "酒館內部", "爐火映照的木造酒館內，酒客的低語與杯盤碰撞聲交織成喧鬧的背景。"),
          scene("city_street", "城市街道", "鋪著石板的主要街道上人來人往，攤販的叫賣聲與馬車的輪聲此起彼落。"),
          scene("coastal_path", "海岸小徑", "海風挾著鹹味迎面吹來，浪濤拍打著岸邊的礁石，海平線延伸到視線盡頭。", false),
          scene("shrine_interior", "神殿內部", "莊嚴的神殿內燭光搖曳，香氣裊繞，虔誠的信徒在神像前低聲祈禱。", false),
        ],
      },
    ],
  },
};

// The first specification ships three categories; the other two stay on the
// rail, focusable and explained, until their own specifications land.
export const FIRST_RELEASE_DISABLED = {
  people: "人物圖庫尚未開放",
  scene: "背景圖庫尚未開放",
};
