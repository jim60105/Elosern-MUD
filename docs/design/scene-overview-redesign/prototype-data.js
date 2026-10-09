// Mock data for the scene overview redesign prototype
// (docs/superpowers/specs/2026-10-10-scene-overview-redesign-design.md).
// Reference only: a tiny self-contained world graph, not any wire payload.
//
// Coordinates follow the local-map convention: +y is north, and a bearing
// is ((atan2(dx, dy) in degrees) mod 360), clockwise from north. Only the
// `grid` and `wilderness` layers carry geographic coordinates; `interior`
// rooms do not, so their exits resolve by direction word or become portals.

const ART = {
  forest: "/art/showcase/sample-forest.webp",
  town: "/art/showcase/sample-town.webp",
  guild: "/art/showcase/sample-guild.webp",
};

export const PLAYER = { name: "艾莉莎", portrait: "/art/defaults/woman.webp" };

const AFF = {
  talk: { key: "talk", label: "交談" },
  trade: { key: "trade", label: "交易" },
  guild: { key: "guild", label: "公會服務" },
  engage: { key: "engage", label: "戰鬥" },
  look: { key: "look", label: "查看" },
};

// Wilderness cells are generated: every cell in the box links to its eight
// neighbours, except a few blocked ones; the west edge cell leads to the
// town's east gate.
const WILD_MIN_X = 61;
const WILD_MAX_X = 66;
const WILD_MIN_Y = 97;
const WILD_MAX_Y = 103;
const BLOCKED = new Set(["62,101", "64,98"]);
const OCTANTS = [
  ["north", 0, 1, "北"],
  ["northeast", 1, 1, "東北"],
  ["east", 1, 0, "東"],
  ["southeast", 1, -1, "東南"],
  ["south", 0, -1, "南"],
  ["southwest", -1, -1, "西南"],
  ["west", -1, 0, "西"],
  ["northwest", -1, 1, "西北"],
];

function wildId(x, y) {
  return `wild:${x},${y}`;
}

function wildScene(x, y) {
  const exits = [];
  for (const [word, dx, dy] of OCTANTS) {
    const nx = x + dx;
    const ny = y + dy;
    if (nx === WILD_MIN_X - 1 && ny === 100 && word === "west") {
      exits.push({ ref: `w-${word}`, label: word, dest: "town:gate" });
      continue;
    }
    if (nx < WILD_MIN_X || nx > WILD_MAX_X || ny < WILD_MIN_Y || ny > WILD_MAX_Y) {
      continue;
    }
    if (BLOCKED.has(`${nx},${ny}`)) {
      exits.push({ ref: `w-${word}`, label: word, dest: wildId(nx, ny), enabled: false, reason: "湍急的河道擋住了去路。" });
      continue;
    }
    exits.push({ ref: `w-${word}`, label: word, dest: wildId(nx, ny) });
  }
  const goblin = x === 63 && y === 100;
  return {
    id: wildId(x, y),
    name: "西部丘陵與谷地",
    layer: "wilderness",
    x,
    y,
    art: ART.forest,
    description: "谷地間河流蜿蜒，兩岸散落著手工業者的作坊與磨坊。",
    exits,
    people: goblin
      ? [{ id: "goblin", name: "哥布林", initial: "哥", portrait: "/art/defaults/monster_anon.webp", affordances: [AFF.engage, AFF.look] }]
      : [],
    bystanders: [],
    objects: x === 64 && y === 100 ? [{ id: "mill", name: "水車磨坊" }] : [],
  };
}

// The town is a `grid` layer: its rooms sit on real coordinates, so the
// exits land at irregular bearings (the gate → square is about 37°).
const TOWN = {
  "town:gate": {
    id: "town:gate",
    name: "東門",
    layer: "grid",
    x: 60,
    y: 100,
    art: ART.town,
    description: "厚重的城門半掩，衛兵倚著長戟打量往來的旅人。",
    exits: [
      { ref: "g-out", label: "east", dest: wildId(61, 100), crossLayer: true },
      { ref: "g-square", label: "市集大道", dest: "town:square" },
      { ref: "g-tower", label: "衛兵塔小徑", dest: "town:tower" },
      { ref: "g-tavern", label: "酒館門", dest: "town:tavern", enabled: false, reason: "酒館打烊了，門從裡面上了閂。" },
      { ref: "g-wall", label: "up", dest: "town:wall" },
      { ref: "g-limbo", label: "回虛境", dest: "limbo" },
    ],
    people: [
      { id: "guard", name: "城門衛兵", initial: "衛", portrait: "/art/defaults/man.webp", affordances: [AFF.talk, AFF.look] },
    ],
    bystanders: [{ id: "traveller", name: "旅人艾拉", initial: "艾" }],
    objects: [{ id: "notice", name: "告示牌" }],
  },
  "town:square": {
    id: "town:square",
    name: "市集廣場",
    layer: "grid",
    x: 57,
    y: 104,
    art: ART.town,
    description: "攤販的吆喝聲此起彼落，噴泉邊坐滿了歇腳的人。",
    exits: [
      { ref: "s-gate", label: "東門大道", dest: "town:gate" },
      { ref: "s-tower", label: "巷弄", dest: "town:tower" },
      { ref: "s-guild", label: "冒險者公會", dest: "guild:hall" },
      { ref: "s-chapel", label: "禮拜堂", dest: "town:chapel" },
    ],
    people: [
      { id: "bran", name: "布蘭", initial: "布", portrait: "/art/defaults/man.webp", affordances: [AFF.talk, AFF.trade, AFF.look] },
      { id: "elder", name: "老鐵匠", initial: "鐵", portrait: "/art/defaults/elder.webp", affordances: [AFF.talk, AFF.trade, AFF.look] },
      { id: "kid", name: "賣花的女孩", initial: "花", portrait: "/art/defaults/girl.webp", affordances: [AFF.talk, AFF.look] },
    ],
    bystanders: [{ id: "busker", name: "街頭樂師", initial: "樂" }, { id: "dog", name: "流浪狗", initial: "狗" }],
    objects: [{ id: "fountain", name: "噴泉" }, { id: "stall", name: "果物攤" }],
  },
  "town:tower": {
    id: "town:tower",
    name: "衛兵塔下",
    layer: "grid",
    x: 58,
    y: 106,
    art: ART.town,
    description: "石塔投下長長的影子，塔門上掛著換班的木牌。",
    exits: [
      { ref: "t-gate", label: "衛兵塔小徑", dest: "town:gate" },
      { ref: "t-square", label: "巷弄", dest: "town:square" },
    ],
    people: [],
    bystanders: [],
    objects: [{ id: "board", name: "換班木牌" }],
  },
  "town:chapel": {
    id: "town:chapel",
    name: "禮拜堂前",
    layer: "grid",
    x: 53,
    y: 105,
    art: ART.town,
    description: "白石台階被磨得發亮，鐘聲在廣場上空迴盪。",
    exits: [{ ref: "c-square", label: "市集廣場", dest: "town:square" }],
    people: [],
    bystanders: [],
    objects: [],
  },
  "town:wall": {
    id: "town:wall",
    name: "城牆步道",
    layer: "grid",
    x: 60,
    y: 100,
    art: ART.town,
    description: "風從垛口灌進來，遠處的丘陵一覽無遺。",
    exits: [{ ref: "wl-down", label: "down", dest: "town:gate" }],
    people: [],
    bystanders: [],
    objects: [],
  },
};

// The guild hall is an `interior` layer: no geographic coordinates, so the
// exits resolve by direction word (北) or fall to the portal ring.
const GUILD = {
  "guild:hall": {
    id: "guild:hall",
    name: "冒險者公會大廳",
    layer: "interior",
    art: ART.guild,
    description: "長桌邊的冒險者高聲談笑，櫃台後的委託板貼滿了羊皮紙。",
    exits: [
      { ref: "h-out", label: "出口", dest: "town:square" },
      { ref: "h-yard", label: "北", dest: "guild:yard" },
      { ref: "h-up", label: "上", dest: "guild:loft" },
      { ref: "h-cellar", label: "下", dest: "guild:cellar", enabled: false, reason: "地窖的鑰匙在會長手上。" },
      { ref: "h-back", label: "後門", dest: "town:tower" },
    ],
    people: [
      { id: "grian", name: "葛里安・衛登", initial: "葛", portrait: null, affordances: [AFF.talk, AFF.guild, AFF.look] },
      { id: "clerk", name: "櫃台小姐", initial: "櫃", portrait: "/art/defaults/woman.webp", affordances: [AFF.talk, AFF.guild, AFF.look] },
      { id: "brawler", name: "醉醺醺的傭兵", initial: "傭", portrait: "/art/defaults/man.webp", affordances: [AFF.talk, AFF.engage, AFF.look] },
      { id: "bard", name: "吟遊詩人", initial: "吟", portrait: "/art/defaults/boy.webp", affordances: [AFF.talk, AFF.look] },
      { id: "elderm", name: "退休的老冒險者", initial: "老", portrait: "/art/defaults/elder.webp", affordances: [AFF.talk, AFF.look] },
    ],
    bystanders: [{ id: "ela", name: "旅人艾拉", initial: "艾" }, { id: "cat", name: "公會的貓", initial: "貓" }],
    objects: [{ id: "board", name: "委託板" }, { id: "hearth", name: "壁爐" }],
  },
  "guild:yard": {
    id: "guild:yard",
    name: "公會訓練場",
    layer: "interior",
    art: ART.guild,
    description: "木樁上滿是刀痕，沙地被踩得結實。",
    exits: [{ ref: "y-hall", label: "南", dest: "guild:hall" }],
    people: [],
    bystanders: [],
    objects: [{ id: "dummy", name: "木樁" }],
  },
  "guild:loft": {
    id: "guild:loft",
    name: "公會二樓迴廊",
    layer: "interior",
    art: ART.guild,
    description: "迴廊俯瞰著大廳，牆上掛著歷代會長的肖像。",
    exits: [{ ref: "l-down", label: "下", dest: "guild:hall" }],
    people: [],
    bystanders: [],
    objects: [],
  },
};

const LIMBO = {
  limbo: {
    id: "limbo",
    name: "虛境",
    layer: "instance",
    art: ART.forest,
    description: "灰白的霧沒有邊際，腳下的地面像是不存在。",
    exits: [{ ref: "lb-back", label: "回東門", dest: "town:gate" }],
    people: [],
    bystanders: [],
    objects: [],
  },
};

export function sceneById(id) {
  if (id.startsWith("wild:")) {
    const [x, y] = id.slice(5).split(",").map(Number);
    return wildScene(x, y);
  }
  return TOWN[id] || GUILD[id] || LIMBO[id] || null;
}

export const SUGGESTIONS = [
  { key: "s1", label: "向布蘭打聽北方商路的消息" },
  { key: "s2", label: "去冒險者公會看看委託板" },
  { key: "s3", label: "在噴泉邊休息到傍晚" },
];

export const WAIT_OPTIONS = [
  { key: "dawn", label: "等待直到黎明" },
  { key: "sleep", label: "睡眠至完全恢復" },
  { key: "rest", label: "休息 N 小時" },
];

export const START_SCENES = {
  wilderness: wildId(63, 100),
  town: "town:gate",
  square: "town:square",
  guild: "guild:hall",
};
