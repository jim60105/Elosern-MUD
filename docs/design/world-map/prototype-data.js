// Mock data for the world-map drawer prototype
// (docs/superpowers/specs/2026-10-22-world-map-drawer-design.md).
// Reference only: geometry follows the authored registries (mainland polygon,
// ridge passes, waterways, Altoria's metric graph) so the drawing has the real
// proportions, but nothing here is wired to a payload.
import DISTRICT_RASTER from "./prototype-districts.json";

export { DISTRICT_RASTER };

// ── World frame (km) ───────────────────────────────────────────────
export const FRAME_KM = 2700;

// The common-knowledge coastline: the authored control polygon itself.
export const COAST_KM = [
  [450, 100], [1850, 100], [2400, 450], [2600, 1350], [1930, 2250],
  [1800, 2600], [750, 2550], [200, 2050], [100, 1050], [300, 350],
];

export const RIDGE_PASSES = [[410, 425], [970, 990], [1770, 1785]];
export function ridgeCentreX(y) {
  return 1410 + ((Math.floor(y / 60) % 5) - 2) * 10;
}

export const WATERWAYS = [
  [[1150, 1060], [860, 1040], [600, 800], [310, 360]],
  [[1950, 1260], [1990, 1100], [2070, 700], [2060, 250]],
  [[2070, 700], [2200, 600], [2390, 460]],
];

// Terrain region classifier (wilderness_provider.region_for_coordinates).
export function regionAt(x, y) {
  if (y >= 2200) return "north_deep_forest";
  const c = ridgeCentreX(y);
  if (Math.abs(x - c) <= 100) return "central_mountains";
  if (x > c) return y <= 500 ? "southeast_coast" : "eastern_plains";
  if (y <= 500) return "southwest_coast";
  if (y >= 1700) return "northwest_highland_forest";
  return "western_hills_valleys";
}

export const REGION_NATION = {
  north_deep_forest: "valhalla",
  northwest_highland_forest: "valhalla",
  western_hills_valleys: "altoria",
  southwest_coast: "altoria",
  eastern_plains: "grandia",
  southeast_coast: "grandia",
  central_mountains: null,
};

export const NATIONS = {
  altoria: { name: "阿爾托利亞王國", at: [560, 760] },
  grandia: { name: "格蘭迪亞帝國", at: [2050, 900] },
  valhalla: { name: "瓦爾哈拉獸王國", at: [700, 2150] },
  neutral: { name: "中央山脈", at: [1410, 1650] },
};

// Terrain washes for lit districts (ink on parchment, low chroma).
export const REGION_WASH = {
  western_hills_valleys: "#5b5a3e",
  southwest_coast: "#5e5640",
  eastern_plains: "#66603a",
  southeast_coast: "#5e5640",
  central_mountains: "#4f4a45",
  northwest_highland_forest: "#3d4a3a",
  north_deep_forest: "#2f3d31",
};

// District names for the lit set and a few unlit neighbours (by landmark index
// in prototype-districts.json). Unlisted districts fall back to 「未探明」.
export const DISTRICT_NAMES = {
  0: { district: "王都近郊", landmark: "聖潔王都鐘樓" },
  3: { district: "暗影谷", landmark: "崩落天井" },
};

export const PLAYER_WORLD = { x: 905, y: 1092 };
export const ALTORIA_KM = [860, 1080];

// Landmarks whose districts are lit in the prototype (Altoria and its
// western-side neighbours), resolved at load by distance.
export const LIT_RADIUS_KM = 230;

// Visited wilderness cells: east out of the capital along the river road,
// a loop south, and a short probe toward the principal pass.
function walk(points) {
  const cells = [];
  for (let i = 1; i < points.length; i++) {
    const [x0, y0] = points[i - 1];
    const [x1, y1] = points[i];
    const steps = Math.max(Math.abs(x1 - x0), Math.abs(y1 - y0));
    for (let s = 0; s < steps; s++) {
      cells.push([Math.round(x0 + ((x1 - x0) * s) / steps), Math.round(y0 + ((y1 - y0) * s) / steps)]);
    }
  }
  cells.push(points[points.length - 1]);
  return cells;
}
export const TRAIL_CELLS = walk([
  [862, 1078], [880, 1084], [905, 1092], [960, 1110], [1030, 1120], [1080, 1105],
  [1060, 1060], [990, 1040], [930, 1050], [905, 1092],
]);

export const PLACES_WORLD = [
  { id: "capital_altoria", name: "聖潔王都", kind: "capital", x: 860, y: 1080 },
  { id: "capital_grandia", name: "輝煌帝都", kind: "capital", x: 1970, y: 1280 },
  { id: "capital_valhalla", name: "咆哮王城", kind: "capital", x: 780, y: 1910 },
  { id: "village_ciaran", name: "暗影谷村", kind: "hidden", x: 1340, y: 1220, visited: false },
  { id: "dungeon_arcane_ruins", name: "魔導遺跡", kind: "dungeon", x: 480, y: 1160, visited: false },
  { id: "port_sw", name: "西南港", kind: "port", x: 301, y: 350 },
];

export const QUESTS = [
  {
    id: "q_wolves",
    title: "驅逐河谷狼群",
    rank: "E",
    target: "河谷狼巢",
    x: 790, y: 1150,
    precise: true,
    note: "公會委託 · 期限剩 3 天",
  },
  {
    id: "q_escort",
    title: "護送商隊前往帝都",
    rank: "D",
    target: "輝煌帝都",
    x: 1970, y: 1280,
    precise: false,
    note: "目的地所在分區未探明，只標示大致方位",
  },
  {
    id: "q_herbs",
    title: "採集銀葉草",
    rank: "F",
    target: "銀葉坡",
    x: 1340, y: 1220,
    precise: false,
    note: "委託人只說在「山脈西側的深谷」",
  },
];

// ── Area map: Altoria (metres, authored layout) ────────────────────
export const ALTORIA_NODES = {
  south_gate: { name: "南門", x: 3050, y: 150, gateway: "西部丘陵與谷地" },
  quay: { name: "碼頭埠", x: 1250, y: 760 },
  riverbank_road: { name: "河岸道", x: 2150, y: 920 },
  south_avenue: { name: "南大道", x: 3140, y: 1050 },
  inn_lane: { name: "客棧巷", x: 3970, y: 1120 },
  bath_forecourt: { name: "浴場前", x: 4830, y: 970 },
  old_wall_ruins: { name: "舊城牆遺跡", x: 2350, y: 1900 },
  north_avenue: { name: "大道北段", x: 3350, y: 1980 },
  craft_alley: { name: "工匠巷", x: 1300, y: 2600 },
  market_street: { name: "市場街", x: 2420, y: 2700 },
  central_plaza: { name: "中央廣場", x: 3500, y: 2850, landmark: true },
  guild_forecourt: { name: "公會前", x: 4380, y: 3000 },
  east_market: { name: "東市", x: 5380, y: 2850 },
  east_gate: { name: "東門", x: 6500, y: 3010, gateway: "西部丘陵與谷地" },
  training_ground: { name: "校場外", x: 2300, y: 3820 },
  holy_steps: { name: "聖階", x: 3480, y: 3700 },
  great_temple: { name: "大神殿前", x: 4560, y: 3920 },
  noble_quarter: { name: "貴族區前", x: 3500, y: 4850 },
  upper_gate: { name: "上城門", x: 4690, y: 5010 },
  academy: { name: "學院前", x: 5650, y: 5200 },
  palace_forecourt: { name: "王宮前庭", x: 4500, y: 6350 },
};

export const ALTORIA_ROADS = [
  ["south_gate", "south_avenue"], ["south_avenue", "north_avenue"], ["north_avenue", "central_plaza"],
  ["south_avenue", "riverbank_road"], ["south_avenue", "inn_lane"], ["riverbank_road", "quay"],
  ["riverbank_road", "old_wall_ruins"], ["old_wall_ruins", "market_street"], ["old_wall_ruins", "north_avenue"],
  ["inn_lane", "bath_forecourt"], ["market_street", "craft_alley"], ["craft_alley", "training_ground"],
  ["market_street", "central_plaza"], ["central_plaza", "holy_steps"], ["central_plaza", "guild_forecourt"],
  ["holy_steps", "training_ground"], ["holy_steps", "noble_quarter"], ["holy_steps", "great_temple"],
  ["guild_forecourt", "great_temple"], ["guild_forecourt", "east_market"], ["great_temple", "upper_gate"],
  ["great_temple", "east_market"], ["noble_quarter", "upper_gate"], ["upper_gate", "palace_forecourt"],
  ["upper_gate", "academy"], ["east_market", "east_gate"],
];

export const ALTORIA_VISITED = [
  "south_gate", "south_avenue", "north_avenue", "central_plaza", "guild_forecourt",
  "market_street", "riverbank_road", "old_wall_ruins",
];
export const ALTORIA_CURRENT = "central_plaza";

// An area-map quest pin (a node the player has seen) and one that lies
// outside this map, which the area map shows as an edge pointer only.
export const AREA_QUESTS = [
  { id: "q_temple", title: "向大神殿呈交證物", node: "great_temple" },
  { id: "q_wolves", title: "驅逐河谷狼群", outside: { bearingDeg: 75, label: "城外 · 約 170 km" } },
];

// ── Area map in the wilderness: the local 1 km neighbourhood ───────
export const WILD_LOCAL_SPAN = 15;
