// Mock rules for the wilderness travel-mode prototype (reference only).
// Everything the real server owns per the sight-and-fog spec — elevation,
// reveal, routing, reserve prediction, interrupt flags — is imitated here on
// one fixed 41 x 41 window so the presentation can be judged. Nothing here is
// the production algorithm; the numbers follow the approved rulebook values.

export const WINDOW = 41;
export const HOME = Object.freeze({ x: 20, y: 22 });
export const RESERVE_FULL = 360000;
export const WALK_COST_PER_SECOND = 8;
export const SLEEP_RESTORE_PER_SECOND = 12;

const SECONDS_PER_CELL = Object.freeze({ road: 800, open: 1200, hills: 1200, woodland: 1800, ford: 1200 });
const STAGES = Object.freeze([
  { key: "normal", label: "精神充沛", min: 252000, scale: 1 },
  { key: "light", label: "輕度疲勞", min: 144000, scale: 0.9 },
  { key: "moderate", label: "中度疲勞", min: 72000, scale: 0.75 },
  { key: "severe", label: "重度疲勞", min: 1, scale: 0.5 },
  { key: "asleep", label: "強制睡眠", min: 0, scale: 0 },
]);
export const STAGE_INDEX = Object.freeze({ normal: 0, light: 1, moderate: 2, severe: 3, asleep: 4 });

export const PACES = Object.freeze([
  { key: "cautious", label: "保守", hint: "走到輕度疲勞就停", stopStage: "light" },
  { key: "standard", label: "標準", hint: "走到中度疲勞就停", stopStage: "moderate" },
  { key: "forced", label: "強行", hint: "直到精力不足以再走一步", stopStage: null },
]);

// Sight rulebook (spec section 3.2).
const TERRAIN_RADIUS = Object.freeze({
  open: [4, 3, 1],
  road: [4, 3, 1],
  ford: [4, 3, 1],
  hills: [3, 2, 1],
  woodland: [1, 1, 0],
});
const PROMINENCE_BONUS = Object.freeze([[0, 0, 0], [1, 0, 0], [2, 1, 0], [3, 2, 0]]);
const VANTAGE_RADIUS = Object.freeze([8, 5, 2]);

// ------------------------------------------------------------------ noise

function hash2(ix, iy, seed) {
  let v = Math.imul(ix, 374761393) ^ Math.imul(iy, 668265263) ^ Math.imul(seed, 1442695041);
  v = Math.imul(v ^ (v >>> 13), 1274126177);
  v ^= v >>> 16;
  return (v >>> 0) / 4294967295;
}

function smooth(t) {
  return t * t * (3 - 2 * t);
}

function valueNoise(px, py, seed) {
  const ix = Math.floor(px);
  const iy = Math.floor(py);
  const sx = smooth(px - ix);
  const sy = smooth(py - iy);
  const a = hash2(ix, iy, seed);
  const b = hash2(ix + 1, iy, seed);
  const c = hash2(ix, iy + 1, seed);
  const d = hash2(ix + 1, iy + 1, seed);
  return (a * (1 - sx) + b * sx) * (1 - sy) + (c * (1 - sx) + d * sx) * sy;
}

function fbm(px, py, seed, octaves = 5) {
  let sum = 0;
  let amp = 1;
  let total = 0;
  let freq = 1;
  for (let o = 0; o < octaves; o += 1) {
    sum += amp * valueNoise(px * freq, py * freq, seed + o * 31);
    total += amp;
    amp *= 0.5;
    freq *= 2;
  }
  return sum / total;
}

// ------------------------------------------------------------- geography

export const RIVER = Object.freeze([
  [27.2, -2], [25.6, 6], [28.4, 12], [26.4, 19], [26.1, 23], [23.4, 29], [25.2, 35], [21.5, 43],
]);
export const ROAD = Object.freeze([
  [-2, 39], [4, 35.5], [9, 33], [14, 28.5], [18.5, 25], [22.5, 23.4], [26.2, 22.9], [30, 18], [34.5, 12.5], [43, 7],
]);
export const FORD = Object.freeze({ x: 26, y: 23 });

function segmentDistance(px, py, ax, ay, bx, by) {
  const dx = bx - ax;
  const dy = by - ay;
  const t = Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)));
  return Math.hypot(px - (ax + t * dx), py - (ay + t * dy));
}

export function polylineDistance(px, py, line) {
  let best = Infinity;
  for (let i = 0; i < line.length - 1; i += 1) {
    best = Math.min(best, segmentDistance(px, py, line[i][0], line[i][1], line[i + 1][0], line[i + 1][1]));
  }
  return best;
}

// Continuous elevation in [0, 1] at a window coordinate (cell centres sit on
// integer + 0.5). Domain-warped fBm, lifted toward the north-east, carved
// down along the river: a stand-in for the offline elevation model.
export function elevationAt(px, py) {
  const wx = fbm(px / 11 + 5.2, py / 11 + 1.3, 7, 3);
  const wy = fbm(px / 11 + 1.7, py / 11 + 9.2, 11, 3);
  const relief = fbm(px / 13 + 1.8 * wx, py / 13 + 1.8 * wy, 3, 5);
  const lift = 0.18 * Math.max(0, (px - py + 10) / 50);
  const river = polylineDistance(px, py, RIVER);
  const carve = 0.22 * Math.exp(-(river * river) / 10);
  return Math.max(0, Math.min(1, relief * 0.85 + lift - carve));
}

function woodlandAt(cx, cy) {
  const n = fbm(cx / 7 + 3.1, cy / 7 + 7.7, 19, 4);
  const bias = 0.012 * (16 - cx) + 0.01 * (18 - cy);
  return n + bias > 0.6;
}

function rasterRoad() {
  const cells = new Set();
  for (let i = 0; i < ROAD.length - 1; i += 1) {
    const [ax, ay] = ROAD[i];
    const [bx, by] = ROAD[i + 1];
    const n = Math.ceil(Math.hypot(bx - ax, by - ay) * 4);
    for (let s = 0; s <= n; s += 1) {
      const x = Math.floor(ax + ((bx - ax) * s) / n);
      const y = Math.floor(ay + ((by - ay) * s) / n);
      if (x >= 0 && y >= 0 && x < WINDOW && y < WINDOW) cells.add(`${x},${y}`);
    }
  }
  return cells;
}

function buildGrid() {
  const road = rasterRoad();
  const cells = [];
  const elev = [];
  for (let y = 0; y < WINDOW; y += 1) {
    const row = [];
    const erow = [];
    for (let x = 0; x < WINDOW; x += 1) {
      const e = elevationAt(x + 0.5, y + 0.5);
      erow.push(e);
      const key = `${x},${y}`;
      const onRiver = polylineDistance(x + 0.5, y + 0.5, RIVER) < 0.62;
      let terrain;
      const bank = y === FORD.y && Math.abs(x - FORD.x) === 1;
      if (x === FORD.x && y === FORD.y) terrain = "ford";
      else if (onRiver && !bank) terrain = "river";
      else if (road.has(key)) terrain = "road";
      else if (woodlandAt(x, y)) terrain = "woodland";
      else if (e > 0.56) terrain = "hills";
      else terrain = "open";
      row.push({ x, y, terrain, band: Math.min(15, Math.floor(e * 16)), prominence: 0 });
    }
    cells.push(row);
    elev.push(erow);
  }
  // Prominence: elevation above the mean of the ring at distance 2..3.
  const proms = [];
  for (let y = 0; y < WINDOW; y += 1) {
    for (let x = 0; x < WINDOW; x += 1) {
      let sum = 0;
      let n = 0;
      for (let dy = -3; dy <= 3; dy += 1) {
        for (let dx = -3; dx <= 3; dx += 1) {
          const d = Math.max(Math.abs(dx), Math.abs(dy));
          if (d < 2) continue;
          const xx = Math.min(WINDOW - 1, Math.max(0, x + dx));
          const yy = Math.min(WINDOW - 1, Math.max(0, y + dy));
          sum += elev[yy][xx];
          n += 1;
        }
      }
      proms.push({ x, y, p: elev[y][x] - sum / n });
    }
  }
  for (const { x, y, p } of proms) {
    const cell = cells[y][x];
    if (cell.terrain === "woodland" || cell.terrain === "river") continue;
    cell.prominence = p > 0.11 ? 3 : p > 0.08 ? 2 : p > 0.055 ? 1 : 0;
  }
  return cells;
}

export const GRID = buildGrid();

export function cellAt(x, y) {
  if (x < 0 || y < 0 || x >= WINDOW || y >= WINDOW) return null;
  return GRID[y][x];
}

export function passable(x, y) {
  const cell = cellAt(x, y);
  return !!cell && cell.terrain !== "river";
}

export const TERRAIN_LABEL = Object.freeze({
  open: "開闊地",
  road: "官道",
  hills: "丘陵",
  woodland: "林地",
  river: "界河",
  ford: "主渡口",
});

// ------------------------------------------------------------ landmarks

export const LANDMARKS = Object.freeze([
  {
    id: "watchtower",
    x: 34,
    y: 6,
    name: "古哨塔遺址",
    silhouette: "一座殘破石塔",
    vantage: true,
    district: "石楠丘陵",
    art: "/art/scenes/ruin_interior.webp",
    prose: "傾頹的石塔立在丘頂，外牆爬滿地衣。從殘存的箭窗望出去，整片石楠丘陵在腳下展開，北方的林線一直延伸到天際。",
  },
]);

export const DISTANT_SOURCES = Object.freeze([
  { id: "watchtower", bearingFrom: (p) => ({ dx: 34 - p.x, dy: 6 - p.y }), silhouette: "一座殘破石塔", dayKm: 22, nightKm: 0 },
  { id: "hamlet", bearingFrom: (p) => ({ dx: 58 - p.x, dy: 30 - p.y }), silhouette: "村落炊煙", nightSilhouette: "村落燈火", dayKm: 45, nightKm: 45 },
]);

export const CITY = Object.freeze({ x: 1, y: 38, name: "聖潔王都・東門" });

export const HOSTILES = Object.freeze([
  { id: "wolves", x: 31, y: 15, name: "灰狼", count: 2, threat: "危險" },
  { id: "rabbits", x: 15, y: 27, name: "穴兔", count: 3, threat: "輕微" },
]);

// ---------------------------------------------------------------- clock

export function lightPhase(minutes) {
  const h = (((minutes / 60) % 24) + 24) % 24;
  if (h >= 7 && h < 17) return "day";
  if (h >= 17 && h < 19) return "dusk";
  if (h >= 5 && h < 7) return "dawn";
  return "night";
}

export const PHASE_LABEL = Object.freeze({ day: "白晝", dusk: "黃昏", night: "夜晚", dawn: "黎明" });

function phaseColumn(phase) {
  return phase === "day" ? 0 : phase === "night" ? 2 : 1;
}

export function formatClock(minutes) {
  const day = Math.floor(minutes / 1440) + 1;
  const m = Math.floor(minutes % 1440);
  const hh = String(Math.floor(m / 60)).padStart(2, "0");
  const mm = String(m % 60).padStart(2, "0");
  return { day, text: `${hh}:${mm}`, label: `第 ${day} 日 ${hh}:${mm}` };
}

// ---------------------------------------------------------------- sight

export function sightRadius(x, y, phase) {
  const cell = cellAt(x, y);
  if (!cell) return 0;
  const col = phaseColumn(phase);
  const base = (TERRAIN_RADIUS[cell.terrain] ?? TERRAIN_RADIUS.open)[col];
  const bonus = cell.terrain === "woodland" ? 0 : PROMINENCE_BONUS[cell.prominence][col];
  const vantage = LANDMARKS.some((l) => l.vantage && l.x === x && l.y === y) ? VANTAGE_RADIUS[col] : 0;
  return Math.max(base + bonus, vantage);
}

export function inDisc(x, y, ox, oy, r) {
  return (x - ox) ** 2 + (y - oy) ** 2 <= (r + 0.5) ** 2;
}

// The revealed mask (spec section 5.3): lit-district cells, then the union
// of every visit's sight disc.
export function revealedMask(visits, litDistricts) {
  const mask = new Uint8Array(WINDOW * WINDOW);
  for (let y = 0; y < WINDOW; y += 1) {
    for (let x = 0; x < WINDOW; x += 1) {
      if (litDistricts.has("石楠丘陵") && districtOf(x, y) === "石楠丘陵") mask[y * WINDOW + x] = 1;
    }
  }
  for (const v of visits) {
    const r = v.sight;
    for (let y = v.y - r; y <= v.y + r; y += 1) {
      for (let x = v.x - r; x <= v.x + r; x += 1) {
        if (x < 0 || y < 0 || x >= WINDOW || y >= WINDOW) continue;
        if (inDisc(x, y, v.x, v.y, r)) mask[y * WINDOW + x] = 1;
      }
    }
  }
  return mask;
}

export function districtOf(x, y) {
  // A mock district edge: the north-eastern third beyond a wandering line.
  return x - y * 0.7 + 4 * Math.sin(y / 5) > 16 ? "石楠丘陵" : "王都東郊";
}

// The trail the party has already walked from the city gate, with the
// largest sight it had on each cell (a daytime walk).
export function initialVisits() {
  const trail = [];
  const path = [
    [2, 37], [3, 36], [4, 35], [5, 35], [6, 34], [7, 34], [8, 33], [9, 33], [10, 32], [11, 31],
    [12, 30], [13, 29], [14, 28], [15, 27], [16, 26], [17, 25], [18, 24], [19, 23], [20, 22],
  ];
  for (const [x, y] of path) trail.push({ x, y, sight: sightRadius(x, y, "day") });
  return trail;
}

// --------------------------------------------------------------- reserve

export function stageOf(reserve) {
  if (reserve <= 0) return STAGES[4];
  return STAGES.find((s) => reserve >= s.min) ?? STAGES[3];
}

export function stepSeconds(ax, ay, bx, by, reserve) {
  const a = cellAt(ax, ay);
  const b = cellAt(bx, by);
  const slow = Math.max(SECONDS_PER_CELL[a.terrain] ?? 1200, SECONDS_PER_CELL[b.terrain] ?? 1200);
  const diag = ax !== bx && ay !== by ? Math.SQRT2 : 1;
  const scale = stageOf(reserve).scale || 1;
  return Math.ceil((slow * diag) / scale);
}

// ----------------------------------------------------------------- route

export const DIRECTIONS = Object.freeze([
  { key: "n", label: "北", dx: 0, dy: -1 },
  { key: "ne", label: "東北", dx: 1, dy: -1 },
  { key: "e", label: "東", dx: 1, dy: 0 },
  { key: "se", label: "東南", dx: 1, dy: 1 },
  { key: "s", label: "南", dx: 0, dy: 1 },
  { key: "sw", label: "西南", dx: -1, dy: 1 },
  { key: "w", label: "西", dx: -1, dy: 0 },
  { key: "nw", label: "西北", dx: -1, dy: -1 },
]);

export function canStep(x, y, dx, dy) {
  if (!passable(x + dx, y + dy)) return false;
  if (dx !== 0 && dy !== 0) return passable(x + dx, y) && passable(x, y + dy);
  return true;
}

export function blockReason(x, y, dx, dy) {
  const target = cellAt(x + dx, y + dy);
  if (!target) return "超出視窗";
  if (target.terrain === "river") return "界河，無法涉水";
  if (dx !== 0 && dy !== 0 && !(passable(x + dx, y) && passable(x, y + dy))) return "斜向會穿過界河";
  return null;
}

// A* over revealed, passable cells with full-speed durations as the cost.
export function findRoute(from, to, mask) {
  const idx = (x, y) => y * WINDOW + x;
  if (!mask[idx(to.x, to.y)] || !passable(to.x, to.y)) return null;
  const open = new Map([[idx(from.x, from.y), { x: from.x, y: from.y, g: 0, f: 0, prev: null }]]);
  const closed = new Map();
  const h = (x, y) => Math.hypot(to.x - x, to.y - y) * 800;
  while (open.size) {
    let bestKey = null;
    let best = null;
    for (const [k, n] of open) {
      if (!best || n.f < best.f) {
        best = n;
        bestKey = k;
      }
    }
    open.delete(bestKey);
    closed.set(bestKey, best);
    if (best.x === to.x && best.y === to.y) {
      const steps = [];
      for (let n = best; n.prev; n = n.prev) steps.unshift({ x: n.x, y: n.y });
      return steps.length <= 60 ? steps : null;
    }
    for (const d of DIRECTIONS) {
      const nx = best.x + d.dx;
      const ny = best.y + d.dy;
      if (nx < 0 || ny < 0 || nx >= WINDOW || ny >= WINDOW) continue;
      const k = idx(nx, ny);
      if (closed.has(k) || !mask[k] || !canStep(best.x, best.y, d.dx, d.dy)) continue;
      const g = best.g + stepSeconds(best.x, best.y, nx, ny, RESERVE_FULL);
      const known = open.get(k);
      if (!known || g < known.g) open.set(k, { x: nx, y: ny, g, f: g + h(nx, ny), prev: best });
    }
  }
  return null;
}

// The travel.plan imitation: per-step duration and predicted worst stage
// for the slowest traveller, nightfall, and the pace stop (spec 7.2).
export function planRoute({ from, steps, reserve, minutes, pace, stopAtNight }) {
  let r = reserve;
  let t = minutes;
  let px = from.x;
  let py = from.y;
  let nightfallIndex = null;
  let stopIndex = null;
  let stopReason = null;
  const stopStage = PACES.find((p) => p.key === pace)?.stopStage ?? null;
  const out = [];
  for (let i = 0; i < steps.length; i += 1) {
    const s = steps[i];
    const sec = stepSeconds(px, py, s.x, s.y, r);
    if (r - sec * WALK_COST_PER_SECOND < 0) {
      stopIndex ??= i - 1;
      stopReason ??= "depletion";
      break;
    }
    const before = stageOf(r).key;
    const phaseBefore = lightPhase(t);
    r -= sec * WALK_COST_PER_SECOND;
    t += sec / 60;
    const after = stageOf(r).key;
    const phase = lightPhase(t);
    out.push({ ...s, sec, stage: after, minutes: t, reserve: r });
    if (nightfallIndex === null && phase === "night" && phaseBefore !== "night") nightfallIndex = i;
    if (stopIndex === null && stopStage && before !== after && STAGE_INDEX[after] >= STAGE_INDEX[stopStage]) {
      stopIndex = i;
      stopReason = "pace";
    }
    if (stopIndex === null && stopAtNight && nightfallIndex === i) {
      stopIndex = i;
      stopReason = "nightfall";
    }
    px = s.x;
    py = s.y;
  }
  if (stopIndex === null) {
    stopIndex = out.length - 1;
    stopReason = "arrival";
  }
  return { steps: out, nightfallIndex, stopIndex, stopReason };
}

// The party's remaining walking capacity by stage on the current terrain's
// pace (the leg gauge when no route is chosen).
export function capacityByStage(reserve, secondsPerCell = 1200) {
  const counts = { normal: 0, light: 0, moderate: 0, severe: 0 };
  let r = reserve;
  for (let guard = 0; guard < 200; guard += 1) {
    const stage = stageOf(r);
    if (stage.key === "asleep") break;
    const sec = Math.ceil(secondsPerCell / stage.scale);
    if (r - sec * WALK_COST_PER_SECOND < 0) break;
    counts[stage.key] += 1;
    r -= sec * WALK_COST_PER_SECOND;
  }
  return counts;
}

export function compassBearing(dx, dy) {
  const names = ["北", "北北東", "東北", "東北東", "東", "東南東", "東南", "南南東", "南", "南南西", "西南", "西南西", "西", "西北西", "西北", "北北西"];
  const angle = (Math.atan2(dx, -dy) * 180) / Math.PI;
  return names[Math.round(((angle + 360) % 360) / 22.5) % 16];
}
