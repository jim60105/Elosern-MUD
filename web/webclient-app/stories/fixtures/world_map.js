// Story fixture slice: synthetic, schema-valid `world_map` v1 bodies for the
// real WorldMapView stories and tests (OpenSpec change render-world-map-view).
// Every body passes web/static/webclient/js/elosern/protocol/panels/
// map_panels.js `validateWorldMapPanel` (pinned in
// tests/world/world_map_view.test.js).
//
// Everything here is an invented mechanism fixture generated from a few
// deterministic functions: a wobbly continent, a ridge and a border river
// that split three nominal nations, a northern forest held as one district
// claimed by two of them, and a jittered set of landmarks partitioned on a
// 10 km raster. No production lore, registry, or design-prototype geometry
// is imported, and every display name is invented; only the three nation
// ids follow the wire vocabulary the spec scenario names (grandia and
// valhalla share the forest).

const FRAME_KM = 2700;
const CELL_KM = 10;
const GRID = FRAME_KM / CELL_KM;

// ── deterministic helpers ─────────────────────────────────────────────────

function mulberry32(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function hashId(prefix, key) {
  // FNV-1a over the key, stretched to 24 hex characters: a stable
  // nonsemantic wire id.
  let h = 0x811c9dc5;
  for (const ch of key) {
    h ^= ch.codePointAt(0);
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  let out = "";
  while (out.length < 24) {
    h = Math.imul(h ^ (h >>> 13), 0x5bd1e995) >>> 0;
    h = (h ^ (h >>> 15)) >>> 0;
    out += h.toString(16).padStart(8, "0");
  }
  return `${prefix}${out.slice(0, 24)}`;
}

const round1 = (v) => Math.round(v * 10) / 10;

// ── the continent ─────────────────────────────────────────────────────────

const CENTRE = { x: 1350, y: 1380 };
const Y_SQUASH = 1.05;

function coastRadius(theta) {
  return 1060 + 110 * Math.sin(3 * theta + 0.4) + 60 * Math.sin(5 * theta + 1.3) + 32 * Math.sin(11 * theta + 2.1);
}

function polar(x, y) {
  const dx = x - CENTRE.x;
  const dy = (y - CENTRE.y) / Y_SQUASH;
  return { theta: Math.atan2(dy, dx), r: Math.hypot(dx, dy) };
}

/** Inland depth in km (negative at sea). */
function inland(x, y) {
  const { theta, r } = polar(x, y);
  return coastRadius(theta) - r;
}

function buildCoastline() {
  const points = [];
  const n = 180;
  for (let i = 0; i < n; i += 1) {
    const theta = -Math.PI + (2 * Math.PI * i) / n;
    const r = coastRadius(theta);
    points.push([round1(CENTRE.x + r * Math.cos(theta)), round1(CENTRE.y + r * Math.sin(theta) * Y_SQUASH)]);
  }
  points.push([...points[0]]);
  return points;
}

// ── nominal claims: a ridge, a border river and the northern forest ──────

const ridgeX = (y) => 1400 + 46 * Math.sin(y / 170) + 18 * Math.sin(y / 61);
const riverY = (x) => 1350 + 48 * Math.sin(x / 140 + 0.6) + 16 * Math.sin(x / 47);
const forestY = (x) => 2030 + 46 * Math.sin(x / 210 + 1.1) + 14 * Math.sin(x / 53);

function zoneAt(x, y) {
  if (y >= forestY(x)) return "forest";
  if (x > ridgeX(y)) return "grandia";
  return y <= riverY(x) ? "altoria" : "valhalla";
}

/** The two nominal claims the northern forest district lists. */
export const FOREST_NATION_IDS = Object.freeze(["grandia", "valhalla"]);

const ZONE_NATIONS = { altoria: ["altoria"], grandia: ["grandia"], valhalla: ["valhalla"], forest: [...FOREST_NATION_IDS] };

function regionAt(x, y, zone) {
  if (zone === "forest") return "north_deep_forest";
  if (Math.abs(x - ridgeX(y)) <= 80) return "central_mountains";
  if (inland(x, y) < 110) return x > ridgeX(y) ? "southeast_coast" : "southwest_coast";
  return { altoria: "western_hills_valleys", grandia: "eastern_plains", valhalla: "northwest_highland_forest" }[zone];
}

export const NATIONS = [
  { id: "altoria", name: "銀冠王國", x: 820.5, y: 1050.5 },
  { id: "grandia", name: "金穗帝國", x: 1950.5, y: 1250.5 },
  { id: "valhalla", name: "霜牙獸王國", x: 760.5, y: 1800.5 },
];

// ── landmarks (district seeds) ────────────────────────────────────────────

const DISTRICT_NAMES = [
  ["王都河岸", "白塔鐘樓"], ["銀溪谷地", "谷口烽台"], ["灰岩丘陵", "灰岩瞭望石"], ["風車原", "老風車"],
  ["古橋渡", "斷橋碑"], ["南麓牧野", "牧野哨站"], ["石冠台地", "石冠"], ["鹿鳴林", "鹿角古樹"],
  ["霧川上游", "霧川泉眼"], ["白堊坡", "白堊路標"], ["琥珀灣", "琥珀燈塔"], ["麥浪平原", "穀倉遺址"],
  ["赤楓嶺", "楓下祠"], ["藍鈴原", "藍鈴石圈"], ["寒鐵坡", "廢礦井"], ["月影湖畔", "湖心亭"],
];

const FOREST_KEY = "forest";
export const FOREST_NAME = "北境深林";
export const FOREST_LANDMARK = { name: "千年古樹", x: 1300.5, y: 2340.5 };

function buildSeeds() {
  const rand = mulberry32(20261023);
  const seeds = [];
  const spacing = 250;
  for (let gy = 0; gy * spacing < FRAME_KM; gy += 1) {
    for (let gx = 0; gx * spacing < FRAME_KM; gx += 1) {
      const x = gx * spacing + spacing / 2 + (rand() - 0.5) * 140;
      const y = gy * spacing + spacing / 2 + (rand() - 0.5) * 140;
      if (inland(x, y) < 25) continue;
      const zone = zoneAt(x, y);
      if (zone === "forest") continue;
      seeds.push({ x: Math.floor(x) + 0.5, y: Math.floor(y) + 0.5, zone });
    }
  }
  // Each capital is its own district's landmark.
  for (const nation of NATIONS) {
    let best = null;
    for (const seed of seeds) {
      if (seed.zone !== nation.id) continue;
      if (!best || Math.hypot(seed.x - nation.x, seed.y - nation.y) < Math.hypot(best.x - nation.x, best.y - nation.y)) best = seed;
    }
    best.x = nation.x;
    best.y = nation.y;
  }
  seeds.forEach((seed, i) => {
    seed.key = `seed_${i}`;
  });
  seeds.push({ key: FOREST_KEY, zone: "forest", x: FOREST_LANDMARK.x, y: FOREST_LANDMARK.y });
  return seeds;
}

// ── raster ownership and outline tracing ──────────────────────────────────

const SEA = -1;

function buildOwners(seeds) {
  const owner = new Int32Array(GRID * GRID).fill(SEA);
  const region = new Int32Array(GRID * GRID).fill(SEA);
  const byZone = {};
  seeds.forEach((seed, i) => (byZone[seed.zone] ??= []).push(i));
  const regions = [];
  for (let j = 0; j < GRID; j += 1) {
    for (let i = 0; i < GRID; i += 1) {
      const x = i * CELL_KM + CELL_KM / 2;
      const y = j * CELL_KM + CELL_KM / 2;
      // Inflated past the coastline so the render-time coast clip leaves no
      // land sliver uncovered.
      if (inland(x, y) < -12) continue;
      const zone = zoneAt(x, y);
      let best = -1;
      let bestD = Infinity;
      for (const s of byZone[zone]) {
        const d = (seeds[s].x - x) ** 2 + (seeds[s].y - y) ** 2;
        if (d < bestD) {
          bestD = d;
          best = s;
        }
      }
      owner[j * GRID + i] = best;
      const key = regionAt(x, y, zone);
      let index = regions.indexOf(key);
      if (index < 0) index = regions.push(key) - 1;
      region[j * GRID + i] = best * 16 + index;
    }
  }
  return { owner, region, regions };
}

function at(raster, i, j) {
  return i < 0 || j < 0 || i >= GRID || j >= GRID ? SEA : raster[j * GRID + i];
}

function signedArea(points) {
  let total = 0;
  for (let i = 0; i + 1 < points.length; i += 1) total += points[i][0] * points[i + 1][1] - points[i + 1][0] * points[i][1];
  return total / 2;
}

/**
 * Rings per raster value: directed boundary edges with the owner on the
 * left (outer rings counter-clockwise, holes clockwise), chained, then
 * smoothed by keeping each unit edge's midpoint plus every junction corner
 * (three or more values meet), so two neighbours share an identical border.
 */
function traceRings(raster) {
  const edges = new Map();
  const add = (value, ax, ay, bx, by) => {
    if (!edges.has(value)) edges.set(value, new Map());
    const from = `${ax},${ay}`;
    const list = edges.get(value);
    if (!list.has(from)) list.set(from, []);
    list.get(from).push([ax, ay, bx, by]);
  };
  for (let j = 0; j < GRID; j += 1) {
    for (let i = 0; i < GRID; i += 1) {
      const v = raster[j * GRID + i];
      if (v === SEA) continue;
      if (at(raster, i, j - 1) !== v) add(v, i, j, i + 1, j);
      if (at(raster, i + 1, j) !== v) add(v, i + 1, j, i + 1, j + 1);
      if (at(raster, i, j + 1) !== v) add(v, i + 1, j + 1, i, j + 1);
      if (at(raster, i - 1, j) !== v) add(v, i, j + 1, i, j);
    }
  }
  const junction = (x, y) => new Set([at(raster, x - 1, y - 1), at(raster, x, y - 1), at(raster, x - 1, y), at(raster, x, y)]).size >= 3;
  const out = new Map();
  for (const [value, list] of edges) {
    const rings = [];
    for (const [, starts] of list) {
      while (starts.length) {
        const ring = [];
        let edge = starts.pop();
        const origin = `${edge[0]},${edge[1]}`;
        for (;;) {
          ring.push(edge);
          const end = `${edge[2]},${edge[3]}`;
          if (end === origin) break;
          const next = list.get(end);
          if (!next || !next.length) break;
          edge = next.pop();
        }
        // Points with a junction flag: shared borders run junction to
        // junction, so smoothing each such stretch with fixed ends keeps two
        // neighbours' borders identical (Chaikin is symmetric).
        const points = [];
        for (const [ax, ay, bx, by] of ring) {
          if (junction(ax, ay)) points.push({ p: [ax * CELL_KM, ay * CELL_KM], fixed: true });
          points.push({ p: [((ax + bx) / 2) * CELL_KM, ((ay + by) / 2) * CELL_KM], fixed: false });
        }
        const simple = smoothRing(points);
        if (simple.length < 3) continue;
        simple.push([...simple[0]]);
        if (signedArea(simple) !== 0) rings.push(simple);
      }
    }
    out.set(value, rings);
  }
  return out;
}

function chaikinOpen(points, rounds) {
  let pts = points;
  for (let round = 0; round < rounds && pts.length > 2; round += 1) {
    const next = [pts[0]];
    for (let i = 0; i + 1 < pts.length; i += 1) {
      const [ax, ay] = pts[i];
      const [bx, by] = pts[i + 1];
      next.push([0.75 * ax + 0.25 * bx, 0.75 * ay + 0.25 * by], [0.25 * ax + 0.75 * bx, 0.25 * ay + 0.75 * by]);
    }
    next.push(pts[pts.length - 1]);
    pts = next;
  }
  return pts;
}

// Interior points on a straight stretch carry nothing; ends always stay.
function dropCollinear(points) {
  return points.filter((p, k) => {
    if (k === 0 || k === points.length - 1) return true;
    const a = points[k - 1];
    const b = points[k + 1];
    return Math.abs((p[0] - a[0]) * (b[1] - a[1]) - (p[1] - a[1]) * (b[0] - a[0])) > 1e-6;
  });
}

function smoothRing(points) {
  const first = points.findIndex((pt) => pt.fixed);
  const round2 = (pt) => [Math.round(pt[0] * 100) / 100, Math.round(pt[1] * 100) / 100];
  if (first < 0) {
    // No junction: a closed ring smoothed as a loop.
    const loop = [...points.map((pt) => pt.p), points[0].p];
    return chaikinOpen(loop, 2).slice(0, -1).map(round2);
  }
  const rotated = [...points.slice(first), ...points.slice(0, first), points[first]];
  const out = [];
  let stretch = [rotated[0].p];
  for (let i = 1; i < rotated.length; i += 1) {
    stretch.push(rotated[i].p);
    if (rotated[i].fixed) {
      out.push(...dropCollinear(chaikinOpen(stretch, 2)).slice(0, -1));
      stretch = [rotated[i].p];
    }
  }
  return out.map(round2);
}

// ── lines clipped to district ownership ───────────────────────────────────

function sampleLine(points, stepKm = 5) {
  const out = [];
  for (let k = 0; k + 1 < points.length; k += 1) {
    const [ax, ay] = points[k];
    const [bx, by] = points[k + 1];
    const n = Math.max(1, Math.ceil(Math.hypot(bx - ax, by - ay) / stepKm));
    for (let s = 0; s < n; s += 1) out.push([ax + ((bx - ax) * s) / n, ay + ((by - ay) * s) / n]);
  }
  out.push(points[points.length - 1]);
  return out;
}

function ownerAtKm(owner, x, y) {
  return at(owner, Math.floor(x / CELL_KM), Math.floor(y / CELL_KM));
}

function splitByOwner(owner, points, bias = [0, 0]) {
  const pieces = new Map();
  let current = null;
  let run = [];
  for (const [x, y] of sampleLine(points)) {
    const o = inland(x, y) < 0 ? SEA : ownerAtKm(owner, x + bias[0], y + bias[1]);
    if (o !== current) {
      if (current !== null && current !== SEA && run.length >= 2) (pieces.get(current) ?? pieces.set(current, []).get(current)).push(run);
      run = run.length ? [run[run.length - 1]] : [];
      current = o;
    }
    run.push([round1(x), round1(y)]);
  }
  if (current !== null && current !== SEA && run.length >= 2) (pieces.get(current) ?? pieces.set(current, []).get(current)).push(run);
  return pieces;
}

const BORDER_RIVER = Array.from({ length: 140 }, (_, k) => 230 + k * 9).map((x) => [x, riverY(x)]).filter(([x]) => x < ridgeX(1350) - 6);
const EAST_RIVER = [[1720, 1500], [1800, 1360], [1880, 1180], [2010, 1000], [2120, 820], [2230, 640], [2290, 520]];
const RIDGE = Array.from({ length: 200 }, (_, k) => 360 + k * 9).filter((y) => y < forestY(1400)).map((y) => [ridgeX(y), y]);

function borderLines() {
  const forestEdge = forestY(ridgeX(1350));
  const ridgeBorder = Array.from({ length: 220 }, (_, k) => 300 + k * 8)
    .filter((y) => y <= forestEdge && inland(ridgeX(y), y) > 0)
    .map((y) => [round1(ridgeX(y)), round1(y)]);
  const riverBorder = BORDER_RIVER.filter(([x, y]) => inland(x, y) > 0).map(([x, y]) => [round1(x), round1(y)]);
  return [ridgeBorder, riverBorder];
}

// ── places, roads and the walked trail ────────────────────────────────────

export const PLACE_IDS = {
  capital: "place_white_capital",
  mill: "place_mill_town",
  harbour: "place_amber_harbour",
  ford: "place_old_ford",
  hiddenVale: "place_moon_vale",
  eastCapital: "place_east_capital",
  forestVillage: "place_forest_village",
};

const PLACES = [
  { id: PLACE_IDS.capital, name: "白塔王都", kind: "capital", x: 820.5, y: 1050.5 },
  { id: PLACE_IDS.mill, name: "風車鎮", kind: "settlement", x: 1010.5, y: 1170.5 },
  { id: PLACE_IDS.harbour, name: "琥珀港", kind: "harbour", x: 560.5, y: 930.5 },
  { id: PLACE_IDS.ford, name: "古渡口", kind: "settlement", x: 1160.5, y: 1290.5 },
  { id: PLACE_IDS.hiddenVale, name: "月隱谷", kind: "hidden", x: 905.5, y: 1250.5 },
  { id: PLACE_IDS.eastCapital, name: "金穗帝都", kind: "capital", x: 1950.5, y: 1250.5 },
  { id: PLACE_IDS.forestVillage, name: "樹蔭聚落", kind: "settlement", x: 1240.5, y: 2290.5 },
];

const ROADS = [
  [[820.5, 1050.5], [880, 1090], [950, 1140], [1010.5, 1170.5]],
  [[820.5, 1050.5], [740, 1010], [650, 960], [560.5, 930.5]],
  [[1010.5, 1170.5], [1080, 1230], [1160.5, 1290.5]],
];

// The walk from the capital eastward along the road, a loop south, then out
// towards the border river: sampled densely and rasterised at 1 km.
const WALK = [
  [820.5, 1050.5], [880, 1090], [950, 1140], [1010.5, 1170.5], [1030, 1120], [1000, 1060], [960, 1030],
  [1000, 1010], [1060, 1050], [1100, 1120], [1120, 1200], [1160.5, 1290.5], [1190, 1310], [1214.5, 1320.5],
];
export const PLAYER = { x: 1214.5, y: 1320.5 };

function walkCells() {
  const cells = new Set();
  for (const [x, y] of sampleLine(WALK, 0.25)) cells.add(`${Math.floor(x)}:${Math.floor(y)}`);
  return [...cells].map((key) => key.split(":").map(Number));
}

function encodeTrail(cells, resolution) {
  const byRow = new Map();
  for (const [x, y] of cells) {
    const cx = Math.floor(x / resolution);
    const cy = Math.floor(y / resolution);
    if (!byRow.has(cy)) byRow.set(cy, new Set());
    byRow.get(cy).add(cx);
  }
  return {
    resolution_km: resolution,
    rows: [...byRow.keys()].sort((a, b) => a - b).map((row) => {
      const runs = [];
      for (const x of [...byRow.get(row)].sort((a, b) => a - b)) {
        const last = runs[runs.length - 1];
        if (last && last[0] + last[1] === x) last[1] += 1;
        else runs.push([x, 1]);
      }
      return [row, runs];
    }),
  };
}

// ── static geometry (computed once) ───────────────────────────────────────

let STATIC = null;

function staticGeometry() {
  if (STATIC) return STATIC;
  const seeds = buildSeeds();
  const { owner, region, regions } = buildOwners(seeds);
  const outlines = traceRings(owner);
  const regionRings = traceRings(region);
  const rivers = [splitByOwner(owner, BORDER_RIVER), splitByOwner(owner, EAST_RIVER)];
  const ridge = splitByOwner(owner, RIDGE, [-3, 0]);
  const roads = ROADS.map((line) => splitByOwner(owner, line));
  const districts = [];
  let named = 0;
  const altoriaCapital = NATIONS[0];
  const byDistance = seeds
    .map((seed, index) => ({ seed, index }))
    .filter(({ index }) => outlines.has(index))
    .sort((a, b) => Math.hypot(a.seed.x - altoriaCapital.x, a.seed.y - altoriaCapital.y) - Math.hypot(b.seed.x - altoriaCapital.x, b.seed.y - altoriaCapital.y));
  for (const { seed, index } of byDistance) {
    const isForest = seed.key === FOREST_KEY;
    const names = isForest ? [FOREST_NAME, FOREST_LANDMARK.name] : DISTRICT_NAMES[named % DISTRICT_NAMES.length];
    if (!isForest) named += 1;
    const terrain = [];
    for (const [value, rings] of regionRings) {
      if (Math.floor(value / 16) !== index) continue;
      terrain.push({ region: regions[value % 16], polygons: rings });
    }
    const lines = (maps) => maps.flatMap((map) => map.get(index) ?? []);
    districts.push({
      key: seed.key,
      id: hashId("d_", seed.key),
      zone: seed.zone,
      distance: Math.hypot(seed.x - altoriaCapital.x, seed.y - altoriaCapital.y),
      body: {
        name: names[0],
        outline: outlines.get(index),
        landmark: { name: names[1], x: seed.x, y: seed.y },
        nations: ZONE_NATIONS[seed.zone],
        terrain: terrain.sort((a, b) => a.region.localeCompare(b.region)),
        rivers: lines(rivers),
        ridge: lines([ridge]),
        roads: lines(roads),
      },
      ownerIndex: index,
    });
  }
  const placeOwner = new Map(PLACES.map((place) => [place.id, ownerAtKm(owner, place.x, place.y)]));
  STATIC = {
    coastline: buildCoastline(),
    borders: borderLines(),
    districts,
    placeOwner,
    walk: walkCells(),
    ownerAtKm: (x, y) => ownerAtKm(owner, x, y),
  };
  return STATIC;
}

const clone = (value) => JSON.parse(JSON.stringify(value));

// ── lit sets and bodies ───────────────────────────────────────────────────

/** Altoria districts within this radius of the capital start lit. */
const BASE_LIT_RADIUS_KM = 450;

function baseLitKeys() {
  const geo = staticGeometry();
  return new Set(geo.districts.filter((d) => d.zone === "altoria" && d.distance <= BASE_LIT_RADIUS_KM).map((d) => d.key));
}

function districtAtKm(x, y) {
  const geo = staticGeometry();
  const index = geo.ownerAtKm(x, y);
  return geo.districts.find((d) => d.ownerIndex === index) ?? null;
}

/** The unlit district the player stands nearest to (lights in the reveal story). */
function newLightDistrict() {
  const geo = staticGeometry();
  const lit = baseLitKeys();
  return geo.districts
    .filter((d) => !lit.has(d.key) && d.zone !== "forest")
    .map((d) => ({ d, dist: Math.hypot(d.body.landmark.x - PLAYER.x, d.body.landmark.y - PLAYER.y) }))
    .sort((a, b) => a.dist - b.dist)[0].d;
}

const QUESTS = [
  { id: "q_herb_escort", title: "護送藥草商人", tracked: true, x: 1060.5, y: 1240.5 },
  { id: "q_east_archive", title: "調查帝都古文書", tracked: false, x: 1890.5, y: 1330.5 },
  { id: "q_river_wolves", title: "討伐河畔狼群", tracked: false, x: 1380.5, y: 1460.5 },
];

/**
 * A world_map body. `lit` is a set of district keys; `visited` lists the
 * visited place ids; `trail` is 1 or 5; `current` overrides the position.
 */
export function worldMap({ lit = baseLitKeys(), visited = [PLACE_IDS.capital, PLACE_IDS.mill, PLACE_IDS.hiddenVale], trail = 1, current = PLAYER, quests = QUESTS } = {}) {
  const geo = staticGeometry();
  const visitedSet = new Set(visited);
  const districts = geo.districts.map((d) => {
    if (!lit.has(d.key)) return { id: d.id, lit: false, outline: clone(d.body.outline) };
    const places = PLACES.filter(
      (place) => geo.placeOwner.get(place.id) === d.ownerIndex && (visitedSet.has(place.id) || place.kind !== "hidden"),
    );
    return { id: d.id, lit: true, ...clone(d.body), places: clone(places) };
  });
  const markers = quests.map((quest) => {
    const owner = districtAtKm(quest.x, quest.y);
    const approximate = !owner || !lit.has(owner.key);
    const x = approximate ? 50 * Math.floor((quest.x + 25) / 50) : quest.x;
    const y = approximate ? 50 * Math.floor((quest.y + 25) / 50) : quest.y;
    return { id: quest.id, title: quest.title, tracked: quest.tracked, x, y, approximate };
  });
  return {
    schema_version: 1,
    available: true,
    common: { coastline: clone(geo.coastline), borders: clone(geo.borders), nations: clone(NATIONS) },
    districts,
    trail: encodeTrail(geo.walk, trail),
    visited_places: clone(PLACES.filter((place) => visitedSet.has(place.id))),
    current: { x: current.x, y: current.y },
    quest_markers: markers,
  };
}

/** The base exploration: the capital's neighbourhood lit, the rest hatched. */
export const worldBase = () => worldMap();

/** The same history with the downsampled 5 km trail. */
export const worldCoarseTrail = () => worldMap({ trail: 5 });

/** The northern forest lit after reaching its landmark (two nations). */
export function worldForestLit() {
  const lit = baseLitKeys();
  lit.add(FOREST_KEY);
  return worldMap({ lit, visited: [PLACE_IDS.capital, PLACE_IDS.mill, PLACE_IDS.hiddenVale, PLACE_IDS.forestVillage] });
}

/** The base plus the player's nearest unlit district, just lit. */
export function worldNewLight() {
  const lit = baseLitKeys();
  lit.add(newLightDistrict().key);
  return worldMap({ lit });
}

/** A history where only the coarse frame is known: nothing lit at all. */
export const worldUnexplored = () => worldMap({ lit: new Set(), visited: [], quests: QUESTS.slice(1) });

export const FOREST_ID = hashId("d_", FOREST_KEY);
export const QUEST_IDS = { exact: "q_herb_escort", approximate: "q_east_archive", nearApproximate: "q_river_wolves" };
export const newLight = () => {
  const d = newLightDistrict();
  return { id: d.id, name: d.body.name, landmark: { ...d.body.landmark } };
};
export const litDistrictNames = () => {
  const lit = baseLitKeys();
  return staticGeometry().districts.filter((d) => lit.has(d.key)).map((d) => d.body.name);
};
