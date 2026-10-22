// Precomputed world geometry for the prototype: the district ownership raster
// (hit-testing), the lit set, and smoothed district / national outlines
// traced offline from the same walking-distance Voronoi raster.
import { DISTRICT_RASTER, LIT_RADIUS_KM, ALTORIA_KM, ridgeCentreX } from "./prototype-data.js";
import OUTLINES from "./prototype-outlines.json";

const R = DISTRICT_RASTER.resKm;
const N = DISTRICT_RASTER.size;
export const LANDMARKS = DISTRICT_RASTER.landmarks;

const OWNER = Array.from({ length: N }, () => new Int16Array(N).fill(-1));
DISTRICT_RASTER.rows.forEach((runs, y) => {
  for (const [s, l, o] of runs) for (let x = s; x < s + l; x++) OWNER[y][x] = o;
});

// The lit set: districts whose landmark lies near the capital and on the
// capital's (western) side of the summit ridge.
export const LIT = new Set(
  LANDMARKS.map(([x, y], i) => ({ i, x, y }))
    .filter(({ x, y }) => Math.hypot(x - ALTORIA_KM[0], y - ALTORIA_KM[1]) <= LIT_RADIUS_KM && x < ridgeCentreX(y))
    .map(({ i }) => i),
);

export function districtAt(xKm, yKm) {
  const cx = Math.floor(xKm / R);
  const cy = Math.floor(yKm / R);
  if (cx < 0 || cy < 0 || cx >= N || cy >= N) return -1;
  return OWNER[cy][cx];
}

export const DISTRICT_PATHS = Object.entries(OUTLINES.districts).map(([id, d]) => ({
  id: Number(id),
  d,
  lit: LIT.has(Number(id)),
}));
export const LIT_PATHS = DISTRICT_PATHS.filter((p) => p.lit);
export const UNLIT_PATHS = DISTRICT_PATHS.filter((p) => !p.lit);
export const NATION_BORDER_PATH = OUTLINES.nationBorder;

// Terrain tint shapes (the region classifier's bands), clipped to lit land.
const corridor = [];
for (let y = 0; y <= 2200; y += 20) corridor.push([ridgeCentreX(y) - 100, y]);
for (let y = 2200; y >= 0; y -= 20) corridor.push([ridgeCentreX(y) + 100, y]);
export const TERRAIN_SHAPES = [
  { key: "coast", points: "0,0 2700,0 2700,500 0,500", fill: "#5d5946" },
  { key: "highland", points: "0,1700 1300,1700 1300,2200 0,2200", fill: "#3f4b3a" },
  { key: "forest", points: "0,2200 2700,2200 2700,2700 0,2700", fill: "#2f3d31" },
  { key: "mountain", points: corridor.map((p) => p.join(",")).join(" "), fill: "#55504a" },
];

// The summit ridge as a polyline broken at the passes.
export const RIDGE_SEGMENTS = (() => {
  const segs = [];
  let cur = [];
  for (let y = 0; y <= 2200; y += 10) {
    const open = [[410, 425], [970, 990], [1770, 1785]].some(([a, b]) => y >= a - 5 && y <= b + 5);
    if (open) {
      if (cur.length > 1) segs.push(cur);
      cur = [];
      continue;
    }
    cur.push([ridgeCentreX(y), y]);
  }
  if (cur.length > 1) segs.push(cur);
  return segs.map((pts) => pts.map((p) => p.join(",")).join(" "));
})();

const LIT_NAMES = ["王都近郊", "銀河谷地", "灰岩丘陵", "風車原", "古橋渡", "南麓牧野", "石冠台地", "鹿鳴林", "霧川上游", "白堊坡"];
const LIT_LANDMARKS = ["聖潔王都鐘樓", "谷口烽台", "灰岩瞭望石", "風車丘", "古橋碑", "牧野哨站", "石冠", "鹿鳴古樹", "霧川源泉", "白堊路標"];
const ordered = [...LIT].sort((a, b) => a - b);
export function districtName(i) {
  const n = ordered.indexOf(i);
  return n >= 0 ? LIT_NAMES[n % LIT_NAMES.length] : "未探明";
}
export function landmarkName(i) {
  const n = ordered.indexOf(i);
  return n >= 0 ? LIT_LANDMARKS[n % LIT_LANDMARKS.length] : null;
}
