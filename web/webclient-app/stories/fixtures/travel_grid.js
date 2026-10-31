// Synthetic full-fact travel grids for the wilderness travel stories
// (wilderness-travel-map-ui). They are in the decoded TravelGrid shape that
// lib/travel-grid.js produces (base design's shape), but carry every fact the
// later window-ui slice supplies — elevation band, prominence tier, road and
// ford flags, display metadata, landmarks, live hostiles, distant sightings,
// the light phase and the ground radius — so the painter and overlays can be
// reviewed against the approved prototype. Every value is a deterministic
// function of world coordinates; nothing here is shipped geography or a
// production rule (reveal is a fixed list of synthetic visit discs).

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

const MOVE = (dir, id) => ({ kind: "move", exit_ref: `e_story_${dir}`, destination: id });
const NEIGHBOURS = [
  ["north", 0, 1],
  ["northeast", 1, 1],
  ["east", 1, 0],
  ["southeast", 1, -1],
  ["south", 0, -1],
  ["southwest", -1, -1],
  ["west", -1, 0],
  ["northwest", -1, 1],
];
const PASSABLE = new Set(["open_ground", "hills", "woodland", "settlement"]);

/**
 * One synthetic grid centred on the party at `party` (default the morning
 * camp on the road), at `lightPhase` with `groundRadius`, carrying
 * `entities` and `sightings` as given.
 */
export function travelGridFixture({
  party = { x: 100, y: 200 },
  lightPhase = "day",
  groundRadius = 4,
  visits = null,
  entities = [],
  sightings = [],
  landmarks = [{ x: 108, y: 207, name: "合成石標" }],
} = {}) {
  const origin = { x: party.x - HALF, y: party.y - HALF };
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
  const nodes = new Map();
  const current = { id: `wild:story:${party.x}:${party.y}`, label: "合成荒原", visibility: "current", visited: true, gateway: null, action: null, landmark: null };
  nodes.set(`${party.x}:${party.y}`, current);
  for (const [dir, dx, dy] of NEIGHBOURS) {
    const x = party.x + dx;
    const y = party.y + dy;
    if (!PASSABLE.has(terrainOf(x, y))) continue;
    const id = `wild:story:${x}:${y}`;
    nodes.set(`${x}:${y}`, { id, label: "合成荒原", visibility: "seen", visited: false, gateway: null, action: MOVE(dir, id), landmark: null });
  }
  for (const mark of landmarks) {
    const key = `${mark.x}:${mark.y}`;
    const existing = nodes.get(key);
    const id = `wild:story:${mark.x}:${mark.y}`;
    nodes.set(key, { ...(existing ?? { id, label: mark.name, visibility: "seen", visited: false, gateway: null, action: null }), landmark: { name: mark.name } });
  }
  const cells = [];
  for (let row = 0; row < SIZE; row += 1) {
    for (let col = 0; col < SIZE; col += 1) {
      const x = origin.x + col;
      const y = origin.y + row;
      const known = revealed(trail, x, y);
      const terrain = terrainOf(x, y);
      cells.push(
        Object.freeze({
          x,
          y,
          known,
          terrain: known ? terrain : null,
          band: known ? band(x, y) : null,
          tier: known ? tierOf(x, y, terrain) : null,
          road: known && isRoad(x, y),
          ford: known && isRiver(x, y) && isRoad(x, y),
          node: nodes.get(`${x}:${y}`) ?? null,
          display: known ? displayOf(x, y, terrain) : null,
        }),
      );
    }
  }
  return Object.freeze({
    mapId: "story",
    title: "合成荒原",
    frame: Object.freeze({ key: "story", unit: "km" }),
    cellKm: 1,
    currentNode: current.id,
    origin: Object.freeze(origin),
    width: SIZE,
    height: SIZE,
    cells: Object.freeze(cells),
    party: Object.freeze({ ...party }),
    lightPhase,
    groundRadius,
    entities: Object.freeze(entities),
    sightings: Object.freeze(sightings),
  });
}

const WOLVES = [
  { id: "story-wolf-a", cell: { x: 103, y: 202 }, kind: "hostile", hostile: true, label: "荒原狼", count: 3, threat: "危險" },
];
const DAY_SIGHTINGS = [
  { bearing: "北北東", distance_km: 25, silhouette_zh: "一座石塔", name: null },
  { bearing: "西", distance_km: 15, silhouette_zh: "孤立的瞭望台", name: "風鳴丘" },
  { bearing: "東南", distance_km: 40, silhouette_zh: "地平線上的城牆與高塔", name: null },
];

/** Morning on the road: wide day sight, a wolf pack in view, three sightings. */
export const MORNING_GRID = travelGridFixture({ entities: WOLVES, sightings: DAY_SIGHTINGS });
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
