// Story fixture slice: synthetic, schema-valid `area_map` v1 bodies for the
// real AreaMapView stories and tests (OpenSpec change render-area-map-view).
// Every body passes web/static/webclient/js/elosern/protocol/panels/
// map_panels.js `validateAreaMapPanel` (pinned in
// tests/world/area_map_view.test.js). Places, names and geometry are invented
// mechanism fixtures: no production lore and none of the design prototype's
// geography.

const gridId = (map, x, y) => `grid:${map}:${x}:${y}`;
const move = (exitRef, destination) => ({ kind: "move", exit_ref: exitRef, destination });

// ---------------------------------------------------------------------------
// Settlement (grid, metres): unequal street lengths around the current
// square — 60 m west, 120 m east, 240 m south and 360 m north — so the
// stories and tests can measure the projected gap ratios.
// ---------------------------------------------------------------------------

const TOWN = "story_town";
export const TOWN_IDS = {
  square: gridId(TOWN, 400, 300),
  west: gridId(TOWN, 340, 300),
  east: gridId(TOWN, 520, 300),
  south: gridId(TOWN, 400, 60),
  northGate: gridId(TOWN, 400, 660),
  academy: gridId(TOWN, 760, 420),
  observatory: gridId(TOWN, 900, 560),
  dyers: gridId(TOWN, 760, 180),
  mill: gridId(TOWN, 140, 300),
  shrine: gridId(TOWN, 140, 520),
};

const townNode = (id, label, x, y, visibility, extra = {}) => ({
  id,
  label,
  x,
  y,
  visibility,
  gateway: null,
  action: null,
  ...extra,
});

export function townArea(overrides = {}) {
  const T = TOWN_IDS;
  return {
    schema_version: 2,
    available: true,
    layer: "grid",
    map_id: TOWN,
    frame: { key: TOWN, unit: "m" },
    current_node: T.square,
    title: "灰岩鎮街道圖",
    nodes: [
      townNode(T.south, "河岸碼頭", 400, 60, "visited", { action: move("e_square_s", T.south) }),
      townNode(T.west, "舊井巷", 340, 300, "visited", { action: move("e_square_w", T.west) }),
      townNode(T.square, "鐘樓廣場", 400, 300, "current"),
      townNode(T.east, "銅匠街", 520, 300, "visited", { action: move("e_square_e", T.east) }),
      townNode(T.northGate, "北門", 400, 660, "seen", {
        gateway: { leads_to: "霧谷丘陵" },
        action: move("e_square_n", T.northGate),
      }),
      townNode(T.dyers, "染坊後巷", 760, 180, "seen"),
      townNode(T.academy, "學院迴廊", 760, 420, "visited"),
      townNode(T.observatory, "星辰天文塔前庭", 900, 560, "visited"),
      townNode(T.mill, "水車磨坊", 140, 300, "visited"),
      townNode(T.shrine, "聖詠者紀念碑與白石長階", 140, 520, "seen"),
    ],
    edges: [
      { source: T.square, destination: T.south },
      { source: T.square, destination: T.west },
      { source: T.square, destination: T.east },
      { source: T.square, destination: T.northGate },
      { source: T.east, destination: T.academy },
      { source: T.east, destination: T.dyers },
      { source: T.academy, destination: T.observatory },
      { source: T.west, destination: T.mill },
      { source: T.mill, destination: T.shrine },
    ],
    quest_markers: [
      { id: "q_story_ledger", title: "替學院送回借閱的星圖", tracked: true, destination: { kind: "node", node_id: T.academy } },
      { id: "q_story_far", title: "霧谷的失蹤羊群", tracked: false, destination: { kind: "bearing", bearing_deg: 12.5, distance_km: 18.4 } },
    ],
    ...overrides,
  };
}

// A crowded block: eight long, known street names within a few dozen metres,
// so the label pass must hide lower-priority names (never truncate them).
export function crowdedTownArea() {
  const base = townArea();
  const extra = [
    ["灰岩鎮公會登記處側門", 430, 330],
    ["老鐵匠的熔爐工坊", 455, 320],
    ["白楊旅店後院馬廄", 470, 280],
    ["香料商人的遮陽市集", 430, 270],
    ["月光修道院附屬藥草園", 380, 335],
    ["風鈴巷第二十三號", 365, 270],
  ].map(([label, x, y]) => townNode(gridId(TOWN, x, y), label, x, y, "visited"));
  return {
    ...base,
    nodes: [...base.nodes, ...extra],
    edges: [
      ...base.edges,
      ...extra.map((node) => ({ source: TOWN_IDS.square, destination: node.id })),
    ],
  };
}

// The same settlement seen from 銅匠街: the square is now visited and remote
// nodes keep no travel action (only the current node's exits carry one).
export function townFromEastArea() {
  const T = TOWN_IDS;
  const base = townArea();
  return {
    ...base,
    current_node: T.east,
    nodes: base.nodes.map((node) => {
      if (node.id === T.east) return { ...node, visibility: "current", action: null };
      if (node.id === T.square) return { ...node, visibility: "visited", action: move("e_east_w", T.square) };
      if (node.id === T.academy) return { ...node, action: move("e_east_ne", T.academy) };
      if (node.id === T.dyers) return { ...node, action: move("e_east_se", T.dyers) };
      return { ...node, action: null };
    }),
  };
}

// ---------------------------------------------------------------------------
// Instance (coordinate-free room graph): a dungeon whose deeper branch is
// absent from the payload. ABSENT_DUNGEON_ROOMS never appear in any body;
// the commission marker still names one of them by identity only.
// ---------------------------------------------------------------------------

export const DUNGEON_IDS = {
  entry: "room:41",
  hall: "room:42",
  crypt: "room:43",
  well: "room:44",
  stair: "room:45",
  frontier: "room:46",
  exit: "room:12",
};
export const ABSENT_DUNGEON_ROOMS = [
  { id: "room:58", label: "沉睡王座廳" },
  { id: "room:59", label: "骸骨祭壇" },
];

const room = (id, label, visibility, extra = {}) => ({ id, label, visibility, gateway: null, action: null, ...extra });

export function dungeonArea(overrides = {}) {
  const D = DUNGEON_IDS;
  return {
    schema_version: 2,
    available: true,
    layer: "instance",
    map_id: "instance:41",
    frame: { key: "instance:41", unit: "none" },
    current_node: D.hall,
    title: "灰燼地窖空間平面圖",
    nodes: [
      room(D.entry, "坍塌的入口", "visited", { action: move("e_hall_w", D.entry) }),
      room(D.hall, "回聲大廳", "current"),
      room(D.crypt, "未探索", "seen", { action: move("e_hall_e", D.crypt) }),
      room(D.well, "乾涸的井室", "visited", { action: move("e_hall_s", D.well) }),
      room(D.stair, "螺旋石階", "visited"),
      room(D.frontier, "未探索", "seen"),
      room(D.exit, "灰岩鎮外的山徑", "seen", { gateway: { leads_to: "灰岩鎮外的山徑" } }),
    ],
    edges: [
      { source: D.entry, destination: D.hall },
      { source: D.hall, destination: D.crypt },
      { source: D.hall, destination: D.well },
      { source: D.well, destination: D.stair },
      { source: D.stair, destination: D.frontier },
      { source: D.entry, destination: D.exit },
    ],
    quest_markers: [
      // Points into fog: the identity only, never a node, label or exit.
      { id: "q_story_throne", title: "取回沉睡王的冠冕", tracked: true, destination: { kind: "node", node_id: ABSENT_DUNGEON_ROOMS[0].id } },
    ],
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Interior (coordinate-free): a guild house with a door back to the street.
// ---------------------------------------------------------------------------

export function interiorArea() {
  return {
    schema_version: 2,
    available: true,
    layer: "interior",
    map_id: "room:120",
    frame: { key: "room:120", unit: "none" },
    current_node: "room:120",
    title: "冒險者公會平面圖",
    nodes: [
      room("room:120", "公會大廳", "current"),
      room("room:121", "委託告示室", "visited", { action: move("e_guild_board", "room:121") }),
      room("room:122", "會長辦公室", "seen", { action: move("e_guild_office", "room:122") }),
      room("room:123", "地下訓練場", "visited"),
      room("room:7", "鐘樓廣場", "seen", {
        gateway: { leads_to: "鐘樓廣場" },
        action: move("e_guild_door", "room:7"),
      }),
    ],
    edges: [
      { source: "room:120", destination: "room:121" },
      { source: "room:120", destination: "room:122" },
      { source: "room:121", destination: "room:123" },
      { source: "room:120", destination: "room:7" },
    ],
    quest_markers: [],
  };
}

// ---------------------------------------------------------------------------
// Wilderness (schema 2, cell-centre kilometres): the 41 x 41 window around
// cell (100, 200) in daylight with ground sight 4. The revealed ground is the
// union of the sight discs along a short trail in from the south-west, one
// lone old camp to the north-west and the current cell; everything else is
// unknown. A river with one ford runs north of the player, a pond lies west,
// a ridge wall and its mountain flank close the far west, woodland fills the
// north-west, hills rise to the south-east, and the town's footprint stands
// north-east. The north-east step is the town's south gate room; one approach
// cell names the town. Two wolves and a traveller stand in live sight, and
// three distant sightings sit beyond it.
// ---------------------------------------------------------------------------

export const WILD_CENTRE = { x: 100, y: 200 };
export const WILD_GATE_ID = gridId(TOWN, 400, 60);
export const WILD_QUEST_CELL = { x: 104, y: 197 };
/** A revealed cell no node stands on (seen, never visited). */
export const WILD_REMEMBERED_CELL = { x: 101, y: 196 };
/** A visited trail cell with no step from the current cell. */
export const WILD_TRAIL_CELL = { x: 97, y: 197 };
const POND = new Set(["96:199", "96:200", "97:200", "96:201", "95:200"]);
const FOOTPRINT = (x, y) => x >= 103 && x <= 105 && y >= 203 && y <= 205;
const APPROACH = { x: 102, y: 202 };
const WILD_VISITS = [
  [100, 200, 4],
  [99, 199, 4],
  [98, 198, 4],
  [97, 197, 3],
  [97, 196, 3],
  [96, 195, 2],
  [95, 195, 2],
  [104, 197, 2],
  [89, 208, 3],
];
const WILD_STEPS = [
  ["n", 0, 1],
  ["ne", 1, 1],
  ["e", 1, 0],
  ["se", 1, -1],
  ["s", 0, -1],
  ["sw", -1, -1],
  ["w", -1, 0],
  ["nw", -1, 1],
];

const wildId = (x, y) => `wild:elosern:${x}:${y}`;

function riverRow(x) {
  return 203 + Math.round((x - 100) * 0.5);
}

/** The synthetic terrain facts of one cell (independent of reveal). */
function wildTerrain(x, y) {
  const noise = (x * 7 + y * 13) % 3;
  let terrain = "open_ground";
  let band = 2 + noise;
  let tier = 0;
  let ford = false;
  if (x >= 108 && y <= 194) {
    terrain = "sea";
    band = 0;
  } else if (FOOTPRINT(x, y)) {
    terrain = "settlement";
    band = 3;
  } else if (x === 93 && y >= 194 && y <= 207) {
    terrain = "ridge";
    band = 12;
  } else if (x <= 92) {
    terrain = "mountain";
    band = 9 + noise;
    tier = noise === 2 ? 3 : 1;
  } else if (POND.has(`${x}:${y}`) || (y === riverRow(x) && x !== 99)) {
    terrain = "water";
    band = 1;
  } else if (y === riverRow(x) && x === 99) {
    ford = true;
    band = 1;
  } else if (x <= 95 && y >= 197) {
    terrain = "woodland";
    band = 3 + (noise > 0 ? 1 : 0);
  } else if (x >= 103 && y <= 198) {
    terrain = "hills";
    band = 5 + noise;
    tier = (x + y) % 5 === 0 ? 2 : 1;
  }
  const passable = !["water", "ridge", "sea", "settlement"].includes(terrain);
  return { terrain, passable, band, tier, road: false, ford };
}

function revealedAt(x, y) {
  return WILD_VISITS.some(([vx, vy, r]) => (x - vx) ** 2 + (y - vy) ** 2 <= (r + 0.5) ** 2);
}

function wildRows(minX, minY) {
  const rows = [];
  for (let row = 0; row < 41; row += 1) {
    const runs = [];
    for (let col = 0; col < 41; col += 1) {
      const x = minX + col;
      const y = minY + row;
      const run = revealedAt(x, y) ? { length: 1, kind: "terrain", ...wildTerrain(x, y) } : { length: 1, kind: "unknown" };
      const last = runs[runs.length - 1];
      const same = last && JSON.stringify({ ...last, length: 0 }) === JSON.stringify({ ...run, length: 0 });
      if (same) last.length += 1;
      else runs.push(run);
    }
    rows.push(runs);
  }
  return rows;
}

export function wildernessArea({ cellKm = 1 } = {}) {
  const { x: cx, y: cy } = WILD_CENTRE;
  const centre = (value) => (value + 0.5) * cellKm;
  const current = wildId(cx, cy);
  const cells = new Map();
  const node = (x, y, fields) => ({
    id: wildId(x, y),
    label: "灰鬃荒原",
    x: centre(x),
    y: centre(y),
    visibility: "seen",
    visited: false,
    gateway: null,
    action: null,
    ...fields,
  });
  for (const [x, y] of WILD_VISITS) {
    const isCurrent = x === cx && y === cy;
    cells.set(`${x}:${y}`, node(x, y, { visibility: isCurrent ? "current" : "visited", visited: true }));
  }
  cells.set(`${APPROACH.x}:${APPROACH.y}`, node(APPROACH.x, APPROACH.y, { label: "灰岩鎮" }));
  const edges = [];
  for (const [dir, dx, dy] of WILD_STEPS) {
    const x = cx + dx;
    const y = cy + dy;
    if (dir === "ne") {
      cells.set(`${x}:${y}`, {
        id: WILD_GATE_ID,
        label: "河岸碼頭",
        x: centre(x),
        y: centre(y),
        visibility: "seen",
        visited: false,
        gateway: { leads_to: "灰岩鎮" },
        action: move(`e_wild_${dir}`, WILD_GATE_ID),
      });
      edges.push({ source: current, destination: WILD_GATE_ID });
      continue;
    }
    if (!wildTerrain(x, y).passable) continue;
    const existing = cells.get(`${x}:${y}`) ?? node(x, y, {});
    existing.action = move(`e_wild_${dir}`, existing.id);
    cells.set(`${x}:${y}`, existing);
    edges.push({ source: current, destination: existing.id });
  }
  const nodes = [...cells.entries()]
    .sort(([a], [b]) => {
      const [ax, ay] = a.split(":").map(Number);
      const [bx, by] = b.split(":").map(Number);
      return ay - by || ax - bx;
    })
    .map(([, value]) => value);
  const minX = cx - 20;
  const minY = cy - 20;
  return {
    schema_version: 2,
    available: true,
    layer: "wilderness",
    map_id: "elosern",
    frame: { key: "elosern", unit: "km" },
    current_node: current,
    title: "灰鬃荒原",
    nodes,
    edges,
    quest_markers: [
      { id: "q_story_wolves", title: "驅離荒原狼群", tracked: true, destination: { kind: "node", node_id: wildId(WILD_QUEST_CELL.x, WILD_QUEST_CELL.y) } },
    ],
    district_name: "灰鬃荒原東麓",
    cell_km: cellKm,
    window: { min_x: minX, min_y: minY, width: 41, height: 41 },
    rows: wildRows(minX, minY),
    light_phase: "day",
    ground_radius: 4,
    entities: [
      { id: "a1b2c3d4e5f60718", cell: { x: 102, y: 198 }, kind: "hostile", hostile: true, label: "荒原狼" },
      { id: "b2c3d4e5f6071829", cell: { x: 103, y: 199 }, kind: "hostile", hostile: true, label: "荒原狼" },
      { id: "c3d4e5f60718293a", cell: { x: 101, y: 197 }, kind: "npc", hostile: false, label: "行腳商人" },
    ],
    sightings: [
      { bearing: "北北東", distance_km: 25, silhouette_zh: "一座石塔", name: null },
      { bearing: "西", distance_km: 15, silhouette_zh: "孤立的瞭望台", name: "風鳴丘" },
      { bearing: "東南", distance_km: 40, silhouette_zh: "地平線上的城牆與高塔", name: null },
    ],
  };
}

/** The same window at night: ground sight shrinks and only lights carry. */
export function wildernessNightArea() {
  const area = wildernessArea();
  return {
    ...area,
    light_phase: "night",
    ground_radius: 1,
    entities: area.entities.filter((e) => (e.cell.x - 100) ** 2 + (e.cell.y - 200) ** 2 <= 1.5 ** 2),
    sightings: [{ bearing: "東南", distance_km: 40, silhouette_zh: "地平線上連成一片的城鎮燈火", name: null }],
  };
}
