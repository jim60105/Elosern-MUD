// Synthetic full-fact wilderness windows for the wilderness travel stories
// (wilderness-travel-map-ui; converted to exact schema-4 bodies by
// wilderness-travel-window-ui). Each fixture is an `area_map` body that the
// real wire validator accepts and the real decoder (lib/travel-grid.js)
// turns into the painted grid, so the stories show the production path:
// elevation band, prominence tier, road and ford flags, display annotations,
// a lit landmark, live hostiles with their threat, distant sightings, the
// light phase and the ground radius. Every value is a deterministic function
// of world coordinates; nothing here is shipped geography or a production
// rule (reveal is a fixed list of synthetic visit discs).

import Protocol from "../../lib/protocol.js";
import { decodeTravelGrid } from "../../lib/travel-grid.js";

const SIZE = 41;
const HALF = 20;

function band(x, y) {
  const hill = 6.5 * Math.exp(-(((x - 113) ** 2) + ((y - 212) ** 2)) / 70);
  const ridge = 4.2 * Math.exp(-(((x - 90) ** 2) / 30 + ((y - 214) ** 2) / 160));
  const swell = 1.4 * Math.sin(x * 0.23 + y * 0.07) + 1.1 * Math.cos(y * 0.19 - x * 0.05);
  const valley = -2.2 * Math.exp(-((y - riverY(x)) ** 2) / 6);
  return Math.max(0, Math.min(15, Math.round(4 + hill + ridge + swell + valley)));
}

function riverY(x) {
  return 193.5 + 3.4 * Math.sin(x * 0.21) + 1.2 * Math.sin(x * 0.53 + 1);
}

function roadY(x) {
  return Math.round(200 + (x - 100) * 0.42 + 1.2 * Math.sin(x * 0.3));
}

function isRiver(x, y) {
  return Math.abs(y - riverY(x)) < 0.62;
}

function isRoad(x, y) {
  if (x < 82 || x > 118) return false;
  const here = roadY(x);
  const next = roadY(x + 1);
  return (y >= Math.min(here, next) && y <= Math.max(here, next) && y !== Math.max(here, next)) || y === here;
}

function isSettlement(x, y) {
  return x >= 82 && x <= 86 && y >= 187 && y <= 190;
}

function woodland(x, y) {
  const patch = Math.sin(x * 0.37 + 1.3) * Math.cos(y * 0.29 - 0.4) + 0.55 * Math.sin((x + y) * 0.19);
  return patch > 0.62 || ((x - 106) ** 2 + (y - 203) ** 2 < 9);
}

function terrainOf(x, y) {
  if (isSettlement(x, y)) return "settlement";
  if (isRiver(x, y)) return "water";
  const b = band(x, y);
  if (b >= 12) return "ridge";
  if (b >= 10) return "mountain";
  if (woodland(x, y) && !isRoad(x, y)) return "woodland";
  if (b >= 7) return "hills";
  return "open_ground";
}

function tierOf(x, y, terrain) {
  if (terrain === "woodland" || terrain === "water") return 0;
  const b = band(x, y);
  const around = [-1, 0, 1].flatMap((dx) => [-1, 0, 1].map((dy) => band(x + dx * 2, y + dy * 2)));
  const mean = around.reduce((a, v) => a + v, 0) / around.length;
  const rise = b - mean;
  return rise > 1.6 ? 3 : rise > 1.0 ? 2 : rise > 0.55 ? 1 : 0;
}

const DISTRICTS = {
  east: { key: "synthetic_east", name: "合成東麓" },
  west: { key: "synthetic_west", name: "合成西坡" },
};

function displayOf(x, y, terrain) {
  const district = x >= 104 ? DISTRICTS.east : DISTRICTS.west;
  const labels = {
    open_ground: "曠野",
    hills: "丘陵",
    mountain: "山地",
    ridge: "山脊",
    woodland: "林地",
    water: "河川",
    settlement: "聚落",
  };
  return Object.freeze({
    terrain_label: labels[terrain],
    district_key: district.key,
    district_name: district.name,
    settlement: terrain === "settlement",
    ford_label: isRiver(x, y) && isRoad(x, y) ? "合成渡口" : null,
  });
}

// Synthetic visits along the walked road and a detour north: each reveals a
// disc. Fixture data only; the server owns reveal.
function revealed(visits, x, y) {
  return visits.some(([vx, vy, r]) => (x - vx) ** 2 + (y - vy) ** 2 <= (r + 0.5) ** 2);
}

const NEIGHBOURS = [
  ["north", "n", 0, 1],
  ["northeast", "ne", 1, 1],
  ["east", "e", 1, 0],
  ["southeast", "se", 1, -1],
  ["south", "s", 0, -1],
  ["southwest", "sw", -1, -1],
  ["west", "w", -1, 0],
  ["northwest", "nw", -1, 1],
];
const BLOCKED = new Set(["water", "ridge", "sea", "settlement"]);
const wildId = (x, y) => `wild:elosern:${x}:${y}`;

function runFacts(x, y) {
  const terrain = terrainOf(x, y);
  return {
    kind: "terrain",
    terrain,
    passable: !BLOCKED.has(terrain),
    band: band(x, y),
    tier: tierOf(x, y, terrain),
    road: isRoad(x, y),
    ford: isRiver(x, y) && isRoad(x, y),
    display: displayOf(x, y, terrain),
  };
}

function sameFacts(a, b) {
  return JSON.stringify({ ...a, length: 0 }) === JSON.stringify({ ...b, length: 0 });
}

// A synthetic 5 km coarse overview of the district around the party: every
// sampled owned cell carries terrain, band and passability, the rest is
// unknown. Fixture data only; the server owns ownership.
const OVERVIEW_KM = 5;
function overviewFor(party) {
  const cellKm = OVERVIEW_KM;
  const centreX = Math.floor(party.x / cellKm);
  const centreY = Math.floor(party.y / cellKm);
  const minX = centreX - 4;
  const minY = centreY - 4;
  const size = 9;
  const rows = [];
  for (let row = 0; row < size; row += 1) {
    const runs = [];
    for (let col = 0; col < size; col += 1) {
      const sampleX = (minX + col) * cellKm + Math.floor(cellKm / 2);
      const sampleY = (minY + row) * cellKm + Math.floor(cellKm / 2);
      const terrain = sampleX >= 82 && sampleX <= 130 ? terrainOf(sampleX, sampleY) : null;
      const run =
        terrain && terrain !== "sea"
          ? { kind: "terrain", terrain, band: band(sampleX, sampleY), passable: !BLOCKED.has(terrain) }
          : { kind: "unknown" };
      const entry = { length: 1, ...run };
      const last = runs[runs.length - 1];
      if (last && sameFacts(last, entry)) last.length += 1;
      else runs.push(entry);
    }
    rows.push(runs);
  }
  return {
    key: "synthetic_east",
    name_zh: "合成東麓",
    cell_km: cellKm,
    window: { min_x: minX, min_y: minY, width: size, height: size },
    rows,
  };
}

/**
 * One synthetic schema-4 wilderness `area_map` body centred on the party at
 * `party` (default the morning camp on the road), at `lightPhase` with
 * `groundRadius`, carrying `entities` and `sightings` as given. `landmarks`
 * name lit landmark cells (each must be revealed by a visit); `overview` is
 * the coarse district record (a synthetic one by default, `null` for none).
 */
export function travelAreaFixture({
  party = { x: 100, y: 200 },
  lightPhase = "day",
  groundRadius = 4,
  visits = null,
  entities = [],
  sightings = [],
  landmarks = [{ x: 108, y: 207, name: "合成石標" }],
  overview = undefined,
} = {}) {
  const origin = { x: party.x - HALF, y: party.y - HALF };
  const inWindow = (x, y) => x >= origin.x && x < origin.x + SIZE && y >= origin.y && y < origin.y + SIZE;
  const trail = visits ?? [
    [84, 192, 4],
    [88, 195, 4],
    [92, 197, 4],
    [96, 198, 4],
    [100, 200, groundRadius],
    [104, 203, 3],
    [108, 206, 3],
    [111, 210, 2],
    [96, 205, 3],
    [93, 209, 2],
  ];
  const current = wildId(party.x, party.y);
  const node = (x, y, fields) => ({
    id: wildId(x, y), label: "合成荒原", x: x + 0.5, y: y + 0.5,
    visibility: "visited", visited: true, gateway: null, action: null, landmark: null, ...fields,
  });
  const nodes = new Map();
  nodes.set(`${party.x}:${party.y}`, node(party.x, party.y, { visibility: "current" }));
  for (const [vx, vy] of trail) {
    const key = `${vx}:${vy}`;
    if (inWindow(vx, vy) && !nodes.has(key)) nodes.set(key, node(vx, vy, {}));
  }
  const edges = [];
  for (const [, dir, dx, dy] of NEIGHBOURS) {
    const x = party.x + dx;
    const y = party.y + dy;
    if (BLOCKED.has(terrainOf(x, y)) || !revealed(trail, x, y)) continue;
    const key = `${x}:${y}`;
    const id = wildId(x, y);
    const existing = nodes.get(key) ?? node(x, y, { visibility: "seen", visited: false });
    nodes.set(key, { ...existing, action: { kind: "move", exit_ref: `e_story_${dir}`, destination: id } });
    edges.push({ source: current, destination: id });
  }
  for (const mark of landmarks) {
    if (!inWindow(mark.x, mark.y) || !revealed(trail, mark.x, mark.y)) continue;
    const key = `${mark.x}:${mark.y}`;
    nodes.set(key, { ...(nodes.get(key) ?? node(mark.x, mark.y, {})), landmark: { name: mark.name } });
  }
  const rows = [];
  for (let row = 0; row < SIZE; row += 1) {
    const runs = [];
    for (let col = 0; col < SIZE; col += 1) {
      const x = origin.x + col;
      const y = origin.y + row;
      const run = revealed(trail, x, y) ? { length: 1, ...runFacts(x, y) } : { length: 1, kind: "unknown" };
      const last = runs[runs.length - 1];
      if (last && sameFacts(last, run)) last.length += 1;
      else runs.push(run);
    }
    rows.push(runs);
  }
  const sorted = [...nodes.values()].sort((a, b) => a.y - b.y || a.x - b.x);
  return {
    schema_version: 4,
    available: true,
    layer: "wilderness",
    map_id: "elosern",
    frame: { key: "elosern", unit: "km" },
    current_node: current,
    title: "合成荒原",
    nodes: sorted,
    edges,
    quest_markers: [],
    district_name: displayOf(party.x, party.y, terrainOf(party.x, party.y)).district_name,
    district: overview === undefined ? overviewFor(party) : overview,
    cell_km: 1,
    window: { min_x: origin.x, min_y: origin.y, width: SIZE, height: SIZE },
    rows,
    light_phase: lightPhase,
    ground_radius: groundRadius,
    entities,
    sightings,
  };
}

/** The validated, decoded travel grid of one {@link travelAreaFixture} body. */
export function travelGridFixture(options = {}) {
  return decodeTravelGrid(Protocol.validateAreaMapPanel(travelAreaFixture(options)));
}

// Two wolves of a pack and a boar whose threat the server could not state.
const WOLVES = [
  { id: "a0b1c2d3e4f50617", cell: { x: 102, y: 202 }, kind: "hostile", hostile: true, label: "荒原狼", count: 1, threat: "中階 D 級" },
  { id: "b1c2d3e4f5061728", cell: { x: 103, y: 201 }, kind: "hostile", hostile: true, label: "荒原狼", count: 1, threat: "中階 D 級" },
  { id: "c2d3e4f506172839", cell: { x: 98, y: 198 }, kind: "hostile", hostile: true, label: "野豬", count: 1, threat: null },
];
const DAY_SIGHTINGS = [
  { bearing: "北北東", distance_km: 25, silhouette_zh: "一座石塔", name: null },
  { bearing: "西", distance_km: 15, silhouette_zh: "孤立的瞭望台", name: "風鳴丘" },
  { bearing: "東南", distance_km: 40, silhouette_zh: "地平線上的城牆與高塔", name: null },
];

/** Morning on the road: wide day sight, a wolf pack in view, three sightings. */
export const MORNING_GRID = travelGridFixture({ entities: WOLVES, sightings: DAY_SIGHTINGS });
/** The morning window's exact schema-3 body, for stories that adopt it through the store. */
export const MORNING_AREA = travelAreaFixture({ entities: WOLVES, sightings: DAY_SIGHTINGS });
/** Dusk: the amber wash, a narrower sight. */
export const DUSK_GRID = travelGridFixture({
  lightPhase: "dusk",
  groundRadius: 3,
  entities: WOLVES,
  sightings: DAY_SIGHTINGS.slice(0, 2),
});
/** Night: deep blue wash, the moonlit disc, only lights carry. */
export const NIGHT_GRID = travelGridFixture({
  lightPhase: "night",
  groundRadius: 1,
  sightings: [{ bearing: "東南", distance_km: 40, silhouette_zh: "地平線上連成一片的城鎮燈火", name: null }],
});
/** Woodland: the party under canopy, sight of one cell, no horizon. */
export const WOODLAND_GRID = travelGridFixture({
  party: { x: 106, y: 203 },
  groundRadius: 1,
  visits: [
    [84, 192, 4],
    [88, 195, 4],
    [92, 197, 4],
    [96, 198, 4],
    [100, 200, 4],
    [103, 201, 2],
    [106, 203, 1],
  ],
});
