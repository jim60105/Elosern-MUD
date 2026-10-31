// The travel stage's ink painter (OpenSpec change wilderness-travel-map-ui;
// interface design §4.2). Dependency-light ES module: no Vue. It paints one
// decoded travel grid (lib/travel-grid.js) onto a 2D canvas context whose
// backing is exactly `grid.width * samplesPerCell` by
// `grid.height * samplesPerCell` pixels; the stage scales that canvas with a
// CSS transform, so camera moves and zoom never repaint.
//
// Every pixel comes from supplied grid facts plus cosmetic texture:
//
//   1. terrain field: bilinear elevation from each known cell's band (flat
//      neutral shading as soon as any known cell has no band), north-west
//      hillshade, contours at band changes with every third band darker, and
//      a warped terrain lookup in the umber/ochre/moss/slate palette;
//   2. reveal mask: bilinear `known` coverage with a brushed jitter and a
//      darker pooled edge; unknown ground stays fully transparent, so the
//      stage's one hatched fog shows through inside and outside the window;
//   3. ink strokes on their own layer, clipped to the mask (destination-in):
//      summit rings on strict prominence maxima, conifer dabs on woodland,
//      the river along canonical `water` cells, roads along `road` cells,
//      ford stones, dotted district edges and settlement walls only where
//      display facts exist, and a faint grid only inside supplied live sight;
//   4. light (source-atop, so the fog stays clear): memory dimming outside
//      the supplied ground radius, the supplied phase's wash and, at night, a
//      moonlit disc of the supplied radius.
//
// A missing fact suppresses its decoration: no band means no relief, no
// radius means no memory/live distinction or grid, no phase means no wash.
// Nothing here decides reveal, passability, sight or light.
//
// The texture (grain, warp, brush jitter, dab placement) hashes WORLD
// sample coordinates, so the same ground looks the same after the 41 x 41
// window recentres on a step. Texture never feeds a fact.
//
// Coordinates: grid rows run south to north (row 0 is the southern edge);
// the canvas runs north to south, so screen cell row `sr` is grid row
// `height - 1 - sr`.

/** Field samples per cell; the canvas backing follows it exactly. */
export const SAMPLES_PER_CELL = 12;

/**
 * The light look per supplied phase (interface design §4.2 starting values;
 * cosmetic, open to human tuning). `memory` is the dim outside live sight,
 * `desat` its colour drain, `wash` the phase tint.
 */
export const PHASE_LOOK = Object.freeze({
  day: Object.freeze({ wash: null, memory: 0.2, desat: 0.4 }),
  dawn: Object.freeze({ wash: "rgba(120, 110, 170, 0.16)", memory: 0.32, desat: 0.5 }),
  dusk: Object.freeze({ wash: "rgba(196, 112, 48, 0.18)", memory: 0.36, desat: 0.5 }),
  night: Object.freeze({ wash: "rgba(20, 34, 78, 0.36)", memory: 0.42, desat: 0.75 }),
});

// A lamplit parchment wash under ink, per canonical terrain class: umber
// ground, ochre hills, moss woods, slate water. Mid-tones, so the fog reads
// as the dark. An unlisted class reads as open ground.
const TERRAIN_RGB = Object.freeze({
  open_ground: [96, 85, 66],
  hills: [110, 96, 70],
  mountain: [104, 94, 80],
  ridge: [118, 106, 86],
  woodland: [56, 72, 56],
  water: [52, 70, 80],
  sea: [38, 54, 68],
  settlement: [92, 84, 72],
});
const OPEN_RGB = TERRAIN_RGB.open_ground;
const INK = [36, 30, 24];
const RIM = [26, 21, 16];

// ── texture ───────────────────────────────────────────────────────────────

/** A 32-bit avalanche hash of two integers, as a number in [0, 1). */
export function textureHash(x, y, salt = 0) {
  let h = Math.imul(x | 0, 0x27d4eb2d) ^ Math.imul(y | 0, 0x165667b1) ^ Math.imul(salt | 0, 0x9e3779b9);
  h = Math.imul(h ^ (h >>> 15), 0x85ebca6b);
  h = Math.imul(h ^ (h >>> 13), 0xc2b2ae35);
  h ^= h >>> 16;
  return (h >>> 0) / 4294967296;
}

function smoothstep(a, b, t) {
  const x = Math.max(0, Math.min(1, (t - a) / (b - a)));
  return x * x * (3 - 2 * x);
}

function mix(a, b, t) {
  return a + (b - a) * t;
}

/**
 * Smooth value noise in [-0.5, 0.5) on a world lattice of `period` samples,
 * over a block of world samples, with each lattice hash computed once:
 * entry `b * nw + a` is the noise at world sample `(wi0 + a, wj0 - b)` (world
 * rows grow northward, the block runs south).
 */
function noiseGrid(wi0, wj0, nw, nh, period, salt, out = new Float32Array(nw * nh)) {
  const xs = new Int32Array(nw);
  const txs = new Float32Array(nw);
  for (let a = 0; a < nw; a += 1) {
    const fx = (wi0 + a) / period;
    xs[a] = Math.floor(fx);
    txs[a] = smoothstep(0, 1, fx - xs[a]);
  }
  const ys = new Int32Array(nh);
  const tys = new Float32Array(nh);
  for (let b = 0; b < nh; b += 1) {
    const fy = (wj0 - b) / period;
    ys[b] = Math.floor(fy);
    tys[b] = smoothstep(0, 1, fy - ys[b]);
  }
  const xMin = Math.min(xs[0], xs[nw - 1]);
  const xMax = Math.max(xs[0], xs[nw - 1]) + 1;
  const yMin = Math.min(ys[0], ys[nh - 1]);
  const yMax = Math.max(ys[0], ys[nh - 1]) + 1;
  const lw = xMax - xMin + 1;
  const lattice = new Float32Array(lw * (yMax - yMin + 1));
  for (let y = yMin; y <= yMax; y += 1) {
    for (let x = xMin; x <= xMax; x += 1) lattice[(y - yMin) * lw + (x - xMin)] = textureHash(x, y, salt);
  }
  for (let b = 0; b < nh; b += 1) {
    const row0 = (ys[b] - yMin) * lw;
    const row1 = row0 + lw;
    const ty = tys[b];
    for (let a = 0; a < nw; a += 1) {
      const x = xs[a] - xMin;
      const tx = txs[a];
      const top = lattice[row0 + x] + (lattice[row0 + x + 1] - lattice[row0 + x]) * tx;
      const bottom = lattice[row1 + x] + (lattice[row1 + x + 1] - lattice[row1 + x]) * tx;
      out[b * nw + a] = top + (bottom - top) * ty - 0.5;
    }
  }
  return out;
}

// ── grid helpers ──────────────────────────────────────────────────────────

/** The grid cell at screen cell `(col, srow)` (north-up), or null. */
function screenCell(grid, col, srow) {
  if (col < 0 || srow < 0 || col >= grid.width || srow >= grid.height) return null;
  return grid.cells[(grid.height - 1 - srow) * grid.width + col];
}

/** Screen cell coordinates `{ col, srow }` of a world cell. */
export function screenOf(grid, x, y) {
  return { col: x - grid.origin.x, srow: grid.height - 1 - (y - grid.origin.y) };
}

function displayKey(display) {
  if (!display) return "";
  return [display.terrain_label, display.district_key, display.district_name, display.settlement, display.ford_label].join("~");
}

/**
 * The content signature that decides a repaint: every grid fact the painter
 * reads. Two grid objects with identical facts share it, so a republish of
 * the same window never repaints; camera, zoom, aim, hover and status are not
 * part of it.
 */
export function paintSignature(grid) {
  if (!grid) return "";
  const parts = [
    grid.mapId,
    grid.origin.x,
    grid.origin.y,
    grid.width,
    grid.height,
    grid.party.x,
    grid.party.y,
    grid.lightPhase ?? "-",
    grid.groundRadius ?? "-",
  ];
  for (const cell of grid.cells) {
    parts.push(
      cell.known
        ? `${cell.terrain}/${cell.band ?? "-"}/${cell.tier ?? "-"}/${cell.road ? 1 : 0}${cell.ford ? 1 : 0}/${displayKey(cell.display)}`
        : "?",
    );
  }
  return parts.join("|");
}

function terrainSignature(grid, samples) {
  const parts = [samples, grid.origin.x, grid.origin.y, grid.width, grid.height];
  for (const cell of grid.cells) parts.push(cell.known ? `${cell.terrain}/${cell.band ?? "-"}` : "?");
  return parts.join("|");
}

// ── stroke models (pure) ──────────────────────────────────────────────────

const ORTHOGONAL = [[1, 0], [0, 1], [-1, 0], [0, -1]];
const DIAGONAL = [[1, 1], [1, -1], [-1, 1], [-1, -1]];

function chaikin(points, closed) {
  let pts = points;
  for (let pass = 0; pass < 2; pass += 1) {
    const out = closed ? [] : [pts[0]];
    const n = pts.length;
    const segments = closed ? n : n - 1;
    for (let k = 0; k < segments; k += 1) {
      const a = pts[k];
      const b = pts[(k + 1) % n];
      out.push([a[0] * 0.75 + b[0] * 0.25, a[1] * 0.75 + b[1] * 0.25]);
      out.push([a[0] * 0.25 + b[0] * 0.75, a[1] * 0.25 + b[1] * 0.75]);
    }
    if (!closed) out.push(pts[n - 1]);
    pts = out;
  }
  return pts;
}

/**
 * Smoothed polylines through the known cells `flagged(cell)` selects, in
 * screen cell space (a cell centre is `(col + 0.5, srow + 0.5)`).
 *
 * Adjacent flagged cells connect orthogonally, and diagonally only where
 * neither shared orthogonal cell is flagged (so a bend draws no triangle).
 * Chains split where a cell has other than two links; a ring with no such
 * cell is one closed chain. A lone cell has no link and draws no line.
 * Each chain is Chaikin-smoothed twice with its open ends kept. Returns
 * `[{ points: [[x, y], ...], closed }]`.
 */
export function strokeChains(grid, flagged) {
  if (!grid) return [];
  const { width, height } = grid;
  const on = (col, srow) => {
    const cell = screenCell(grid, col, srow);
    return !!cell && cell.known && flagged(cell);
  };
  const id = (col, srow) => srow * width + col;
  const links = new Map();
  const link = (a, b) => {
    if (!links.has(a)) links.set(a, []);
    links.get(a).push(b);
  };
  for (let srow = 0; srow < height; srow += 1) {
    for (let col = 0; col < width; col += 1) {
      if (!on(col, srow)) continue;
      const here = id(col, srow);
      if (!links.has(here)) links.set(here, []);
      for (const [dx, dy] of ORTHOGONAL) {
        if (on(col + dx, srow + dy)) link(here, id(col + dx, srow + dy));
      }
      for (const [dx, dy] of DIAGONAL) {
        if (on(col + dx, srow + dy) && !on(col + dx, srow) && !on(col, srow + dy)) link(here, id(col + dx, srow + dy));
      }
    }
  }
  const centre = (node) => [(node % width) + 0.5, Math.floor(node / width) + 0.5];
  const edgeKey = (a, b) => (a < b ? `${a}-${b}` : `${b}-${a}`);
  const used = new Set();
  const chains = [];
  const walk = (start, next) => {
    const path = [start];
    let prev = start;
    let cur = next;
    used.add(edgeKey(start, next));
    for (;;) {
      path.push(cur);
      const out = links.get(cur);
      if (out.length !== 2) break;
      const step = out[0] === prev ? out[1] : out[0];
      if (used.has(edgeKey(cur, step))) break;
      used.add(edgeKey(cur, step));
      prev = cur;
      cur = step;
    }
    return path;
  };
  const nodes = [...links.keys()].sort((a, b) => a - b);
  for (const node of nodes) {
    const out = links.get(node);
    if (out.length === 2) continue;
    for (const next of out) {
      if (used.has(edgeKey(node, next))) continue;
      chains.push({ points: chaikin(walk(node, next).map(centre), false), closed: false });
    }
  }
  // Rings: every link of every cell is two, so no end started a chain.
  for (const node of nodes) {
    const out = links.get(node);
    if (out.length !== 2 || used.has(edgeKey(node, out[0]))) continue;
    const path = walk(node, out[0]);
    if (path[path.length - 1] === node) path.pop();
    chains.push({ points: chaikin(path.map(centre), true), closed: true });
  }
  return chains;
}

/**
 * The summit cells: known cells with a positive prominence tier that no
 * known 8-neighbour exceeds. A tie goes to the cell with the smaller world
 * y, then the smaller world x, so exactly one cell of a level plateau rings.
 */
export function summitCells(grid) {
  if (!grid) return [];
  const out = [];
  for (const cell of grid.cells) {
    if (!cell.known || !(cell.tier > 0)) continue;
    const { col, srow } = screenOf(grid, cell.x, cell.y);
    let summit = true;
    for (let dy = -1; dy <= 1 && summit; dy += 1) {
      for (let dx = -1; dx <= 1; dx += 1) {
        if (!dx && !dy) continue;
        const n = screenCell(grid, col + dx, srow + dy);
        if (!n || !n.known || typeof n.tier !== "number") continue;
        if (n.tier > cell.tier || (n.tier === cell.tier && (n.y < cell.y || (n.y === cell.y && n.x < cell.x)))) {
          summit = false;
          break;
        }
      }
    }
    if (summit) out.push(cell);
  }
  return out;
}

// Shared cell edges between two known cells `test` accepts, as screen
// cell-space segments `{ x1, y1, x2, y2, a, b }`.
function sharedEdges(grid, test) {
  const out = [];
  for (let srow = 0; srow < grid.height; srow += 1) {
    for (let col = 0; col < grid.width; col += 1) {
      const a = screenCell(grid, col, srow);
      if (!a?.known) continue;
      const east = screenCell(grid, col + 1, srow);
      if (east?.known && test(a, east)) out.push({ x1: col + 1, y1: srow, x2: col + 1, y2: srow + 1, a, b: east });
      const south = screenCell(grid, col, srow + 1);
      if (south?.known && test(a, south)) out.push({ x1: col, y1: srow + 1, x2: col + 1, y2: srow + 1, a, b: south });
    }
  }
  return out;
}

/** District edges: between two known cells whose supplied district keys differ. */
export function districtEdges(grid) {
  if (!grid) return [];
  return sharedEdges(grid, (a, b) => {
    const ka = a.display?.district_key ?? null;
    const kb = b.display?.district_key ?? null;
    return ka !== null && kb !== null && ka !== kb;
  });
}

/** Settlement walls: where a known disclosed footprint meets known open land. */
export function wallEdges(grid) {
  if (!grid) return [];
  return sharedEdges(grid, (a, b) => (a.display?.settlement === true) !== (b.display?.settlement === true));
}

// ── the field ─────────────────────────────────────────────────────────────

function cellElevations(grid) {
  const { width, height, cells } = grid;
  const known = cells.filter((cell) => cell.known);
  const flat = known.length === 0 || known.some((cell) => typeof cell.band !== "number");
  if (flat) return { flat: true, elev: null };
  const elev = new Float32Array(width * height);
  const have = new Uint8Array(width * height);
  let sum = 0;
  for (let srow = 0; srow < height; srow += 1) {
    for (let col = 0; col < width; col += 1) {
      const cell = screenCell(grid, col, srow);
      if (cell.known) {
        elev[srow * width + col] = cell.band;
        have[srow * width + col] = 1;
        sum += cell.band;
      }
    }
  }
  // Unknown cells take their known neighbours' mean (the fog hides them;
  // this only keeps relief continuous up to the brushed edge).
  const mean = sum / known.length;
  for (let pass = 0; pass < 2; pass += 1) {
    const next = Uint8Array.from(have);
    for (let srow = 0; srow < height; srow += 1) {
      for (let col = 0; col < width; col += 1) {
        const k = srow * width + col;
        if (have[k]) continue;
        let total = 0;
        let count = 0;
        for (let dy = -1; dy <= 1; dy += 1) {
          for (let dx = -1; dx <= 1; dx += 1) {
            const c = col + dx;
            const r = srow + dy;
            if (c < 0 || r < 0 || c >= width || r >= height || !have[r * width + c]) continue;
            total += elev[r * width + c];
            count += 1;
          }
        }
        if (count) {
          elev[k] = total / count;
          next[k] = 1;
        }
      }
    }
    have.set(next);
  }
  for (let k = 0; k < elev.length; k += 1) if (!have[k]) elev[k] = mean;
  return { flat: false, elev };
}

function bilinear(values, width, height, u, v) {
  const x = Math.min(width - 1, Math.max(0, u - 0.5));
  const y = Math.min(height - 1, Math.max(0, v - 0.5));
  const x0 = Math.floor(x);
  const y0 = Math.floor(y);
  const x1 = Math.min(width - 1, x0 + 1);
  const y1 = Math.min(height - 1, y0 + 1);
  const fx = x - x0;
  const fy = y - y0;
  return mix(
    mix(values[y0 * width + x0], values[y0 * width + x1], fx),
    mix(values[y1 * width + x0], values[y1 * width + x1], fx),
    fy,
  );
}

// The terrain part of the field: elevation-shaded colour per sample. It
// depends on terrain and bands only, so a reveal-, party- or light-only
// change reuses it.
function buildTerrain(grid, samples, cache) {
  const { width, height } = grid;
  const fw = width * samples;
  const fh = height * samples;
  const n = fw * fh;
  const rgb = cache.rgb?.length === n * 3 ? cache.rgb : new Float32Array(n * 3);
  const aw = fw + 2;
  const ah = fh + 2;
  const elevSamples = cache.elevSamples?.length === aw * ah ? cache.elevSamples : new Float32Array(aw * ah);
  const { flat, elev } = cellElevations(grid);
  const baseI = grid.origin.x * samples;
  const baseJ = (grid.origin.y + height) * samples - 1;
  // World-anchored noise fields for this window (the apron grids carry one
  // extra sample on every side for the gradients).
  const relief = flat ? null : noiseGrid(baseI - 1, baseJ + 1, aw, ah, samples * 1.6, 11);
  const detail = flat ? null : noiseGrid(baseI - 1, baseJ + 1, aw, ah, samples * 0.5, 23);
  const warpU = noiseGrid(baseI, baseJ, fw, fh, samples * 1.3, 37);
  const warpV = noiseGrid(baseI, baseJ, fw, fh, samples * 1.3, 41);
  const grainField = noiseGrid(baseI, baseJ, fw, fh, 5, 7);
  cache.jitter = noiseGrid(baseI, baseJ, fw, fh, samples * 0.55, 3, cache.jitter?.length === n ? cache.jitter : undefined);
  const fine = noiseGrid(baseI, baseJ, fw, fh, 3, 9);
  for (let k = 0; k < n; k += 1) cache.jitter[k] = cache.jitter[k] * 0.3 + fine[k] * 0.12;
  // Elevation per sample, with a one-sample apron for the gradients.
  for (let j = -1; j <= fh; j += 1) {
    for (let i = -1; i <= fw; i += 1) {
      const k = (j + 1) * aw + (i + 1);
      elevSamples[k] = flat
        ? 0
        : bilinear(elev, width, height, (i + 0.5) / samples, (j + 0.5) / samples) + relief[k] * 0.7 + detail[k] * 0.18;
    }
  }
  for (let j = 0; j < fh; j += 1) {
    const ownRow = Math.floor((j + 0.5) / samples);
    for (let i = 0; i < fw; i += 1) {
      const p = j * fw + i;
      // A warped lookup, so region borders wander off the cell grid.
      const wu = (i + 0.5) / samples + warpU[p] * 1.1;
      const wv = (j + 0.5) / samples + warpV[p] * 1.1;
      const warped = screenCell(grid, Math.floor(wu), Math.floor(wv));
      const terrain = warped?.known ? warped.terrain : screenCell(grid, Math.floor((i + 0.5) / samples), ownRow)?.terrain;
      const base = TERRAIN_RGB[terrain] ?? OPEN_RGB;
      const grain = (textureHash(baseI + i, baseJ - j, 5) - 0.5) * 7 + grainField[p] * 6;
      let lift = 0.9;
      let contour = 0;
      if (!flat) {
        const k = (j + 1) * aw + (i + 1);
        const e = elevSamples[k];
        const gx = elevSamples[k + 1] - elevSamples[k - 1];
        const gy = elevSamples[k + aw] - elevSamples[k - aw];
        // Light from the north-west: a slope rising to the south-east faces it.
        const shade = Math.max(-1, Math.min(1, (gx + gy) * 2.6));
        lift = 0.66 + 0.46 * (shade * 0.5 + 0.5) + Math.min(1, e / 15) * 0.1;
        const band = Math.floor(e);
        const east = Math.floor(elevSamples[k + 1]);
        const south = Math.floor(elevSamples[k + aw]);
        if (east !== band || south !== band) {
          const line = Math.max(band, east, south);
          contour = line % 3 === 0 ? 0.32 : 0.15;
        }
      }
      const o = p * 3;
      for (let c = 0; c < 3; c += 1) {
        let value = base[c] * lift + grain;
        if (contour) value = mix(value, INK[c], contour);
        rgb[o + c] = value;
      }
    }
  }
  cache.rgb = rgb;
  cache.elevSamples = elevSamples;
}

/**
 * The painted field of one grid as RGBA (row-major, north-up), sized
 * `width * samplesPerCell` by `height * samplesPerCell`. Alpha is the brushed
 * reveal mask: exactly 0 wherever the cover falls off, so unknown ground is
 * transparent. Buffers live on `cache` and are reused while sizes agree.
 */
export function buildField(grid, { samplesPerCell = SAMPLES_PER_CELL } = {}, cache = {}) {
  const samples = samplesPerCell;
  const { width, height } = grid;
  const fw = width * samples;
  const fh = height * samples;
  const tsig = terrainSignature(grid, samples);
  if (cache.terrainSig !== tsig) {
    buildTerrain(grid, samples, cache);
    cache.terrainSig = tsig;
  }
  const n = fw * fh;
  const rgba = cache.rgba?.length === n * 4 ? cache.rgba : new Uint8ClampedArray(n * 4);
  const cover = cache.cover?.length === width * height ? cache.cover : new Float32Array(width * height);
  for (let srow = 0; srow < height; srow += 1) {
    for (let col = 0; col < width; col += 1) cover[srow * width + col] = screenCell(grid, col, srow).known ? 1 : 0;
  }
  const look = PHASE_LOOK[grid.lightPhase] ?? PHASE_LOOK.day;
  const radius = typeof grid.groundRadius === "number" ? grid.groundRadius : null;
  const party = screenOf(grid, grid.party.x, grid.party.y);
  const pu = party.col + 0.5;
  const pv = party.srow + 0.5;
  const { rgb, jitter } = cache;
  for (let j = 0; j < fh; j += 1) {
    const v = (j + 0.5) / samples;
    for (let i = 0; i < fw; i += 1) {
      const u = (i + 0.5) / samples;
      const p = j * fw + i;
      const o = p * 4;
      // Outside the window everything is fog; inside, bilinear cover.
      const x = u - 0.5;
      const y = v - 0.5;
      const x0 = Math.floor(x);
      const y0 = Math.floor(y);
      const at = (c, r) => (c < 0 || r < 0 || c >= width || r >= height ? 0 : cover[r * width + c]);
      const fx = x - x0;
      const fy = y - y0;
      const base = mix(mix(at(x0, y0), at(x0 + 1, y0), fx), mix(at(x0, y0 + 1), at(x0 + 1, y0 + 1), fx), fy);
      if (base <= 0) {
        rgba[o + 3] = 0;
        continue;
      }
      const a = smoothstep(0.38, 0.62, base + jitter[p]);
      if (a <= 0) {
        rgba[o + 3] = 0;
        continue;
      }
      // The wash's edge pools darker, like ink drying at a brushed border.
      const rim = Math.min(1, a * (1 - a) * 4.2);
      let r = mix(rgb[p * 3], RIM[0], rim * 0.65);
      let g = mix(rgb[p * 3 + 1], RIM[1], rim * 0.65);
      let b = mix(rgb[p * 3 + 2], RIM[2], rim * 0.65);
      if (radius !== null) {
        // Outside live sight the wash loses colour: memory, not sight.
        const away = smoothstep(radius + 0.1, radius + 1.1, Math.hypot(u - pu, v - pv)) * look.desat;
        if (away > 0) {
          const lum = r * 0.3 + g * 0.59 + b * 0.11;
          r = mix(r, lum, away);
          g = mix(g, lum, away);
          b = mix(b, lum, away);
        }
      }
      rgba[o] = r;
      rgba[o + 1] = g;
      rgba[o + 2] = b;
      rgba[o + 3] = Math.round(a * 255);
    }
  }
  cache.rgba = rgba;
  cache.cover = cover;
  return rgba;
}

// ── ink ───────────────────────────────────────────────────────────────────

function tracePath(ctx, chain, s) {
  const pts = chain.points;
  ctx.beginPath();
  ctx.moveTo(pts[0][0] * s, pts[0][1] * s);
  for (let k = 1; k < pts.length; k += 1) ctx.lineTo(pts[k][0] * s, pts[k][1] * s);
  if (chain.closed) ctx.closePath();
}

function strokeChainSet(ctx, chains, s, passes) {
  for (const pass of passes) {
    ctx.strokeStyle = pass.color;
    ctx.lineWidth = pass.width;
    ctx.setLineDash(pass.dash ?? []);
    for (const chain of chains) {
      tracePath(ctx, chain, s);
      ctx.stroke();
    }
  }
  ctx.setLineDash([]);
}

function centreOf(grid, cell, s) {
  const { col, srow } = screenOf(grid, cell.x, cell.y);
  return [(col + 0.5) * s, (srow + 0.5) * s];
}

/** Inks every stroke layer of `grid` onto `ctx` at `s` pixels per cell. */
export function drawInk(ctx, grid, s = SAMPLES_PER_CELL) {
  ctx.lineCap = "round";
  ctx.lineJoin = "round";

  // Summits: concentric rings, one per prominence tier, on strict maxima.
  for (const cell of summitCells(grid)) {
    const [cx, cy] = centreOf(grid, cell, s);
    ctx.lineWidth = Math.max(0.8, s * 0.07);
    for (let k = 0; k < cell.tier; k += 1) {
      ctx.strokeStyle = `rgba(40, 30, 20, ${0.62 - k * 0.14})`;
      ctx.beginPath();
      ctx.ellipse(cx, cy, s * (0.16 + k * 0.12), s * (0.11 + k * 0.085), -0.3, 0, Math.PI * 2);
      ctx.stroke();
    }
    ctx.fillStyle = "rgba(40, 30, 20, 0.75)";
    ctx.beginPath();
    ctx.arc(cx, cy, Math.max(0.8, s * 0.06), 0, Math.PI * 2);
    ctx.fill();
  }

  // Woods: three deterministic conifer dabs per cell.
  for (const cell of grid.cells) {
    if (!cell.known || cell.terrain !== "woodland") continue;
    const { col, srow } = screenOf(grid, cell.x, cell.y);
    for (let k = 0; k < 3; k += 1) {
      const tx = (col + 0.2 + textureHash(cell.x, cell.y, 100 + k) * 0.6) * s;
      const ty = (srow + 0.3 + textureHash(cell.x, cell.y, 200 + k) * 0.5) * s;
      const size = s * (0.16 + textureHash(cell.x, cell.y, 300 + k) * 0.08);
      ctx.fillStyle = "rgba(22, 34, 25, 0.92)";
      ctx.beginPath();
      ctx.moveTo(tx, ty - size * 1.55);
      ctx.lineTo(tx + size, ty + size * 0.62);
      ctx.lineTo(tx - size, ty + size * 0.62);
      ctx.closePath();
      ctx.fill();
      ctx.strokeStyle = "rgba(150, 178, 140, 0.42)";
      ctx.lineWidth = Math.max(0.6, s * 0.05);
      ctx.beginPath();
      ctx.moveTo(tx - size * 0.65, ty + size * 0.2);
      ctx.lineTo(tx, ty - size * 1.4);
      ctx.stroke();
    }
  }

  // The river: a dark bank wash, the water body, a pale current line.
  strokeChainSet(ctx, strokeChains(grid, (cell) => cell.terrain === "water"), s, [
    { color: "rgba(28, 36, 38, 0.42)", width: s * 1.05 },
    { color: "#4a6a7c", width: s * 0.6 },
    { color: "rgba(156, 186, 202, 0.5)", width: Math.max(0.8, s * 0.07), dash: [s * 0.5, s * 0.36] },
  ]);

  // Roads: an ink underlay and a gold dash.
  strokeChainSet(ctx, strokeChains(grid, (cell) => cell.road === true), s, [
    { color: "rgba(26, 20, 14, 0.6)", width: Math.max(2, s * 0.2) },
    { color: "rgba(214, 184, 122, 0.92)", width: Math.max(1, s * 0.085), dash: [s * 0.32, s * 0.2] },
  ]);

  // The ford: stepping stones across the water, drawn over road and river.
  for (const cell of grid.cells) {
    if (!cell.known || !cell.ford) continue;
    const { col, srow } = screenOf(grid, cell.x, cell.y);
    for (let k = 0; k < 4; k += 1) {
      const sx = (col + 0.17 + k * 0.22) * s;
      const sy = (srow + 0.42 + (k % 2) * 0.16) * s;
      ctx.fillStyle = "rgba(20, 18, 16, 0.5)";
      ctx.beginPath();
      ctx.ellipse(sx + s * 0.02, sy + s * 0.03, s * 0.1, s * 0.07, 0.3, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = "#d3cab6";
      ctx.beginPath();
      ctx.ellipse(sx, sy, s * 0.09, s * 0.062, 0.3, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  // Settlement footprints: a shaded plate and a pale wall at the edge.
  for (const cell of grid.cells) {
    if (!cell.known || cell.display?.settlement !== true) continue;
    const { col, srow } = screenOf(grid, cell.x, cell.y);
    ctx.fillStyle = "rgba(34, 30, 26, 0.32)";
    ctx.fillRect(col * s, srow * s, s, s);
  }
  ctx.strokeStyle = "rgba(230, 204, 148, 0.86)";
  ctx.lineWidth = Math.max(1, s * 0.1);
  ctx.beginPath();
  for (const edge of wallEdges(grid)) {
    ctx.moveTo(edge.x1 * s, edge.y1 * s);
    ctx.lineTo(edge.x2 * s, edge.y2 * s);
  }
  ctx.stroke();

  // District edges: a dotted ink line along the shared edge.
  ctx.fillStyle = "rgba(38, 30, 22, 0.62)";
  for (const edge of districtEdges(grid)) {
    for (let k = 0; k < 3; k += 1) {
      const t = (k + 0.5) / 3;
      ctx.beginPath();
      ctx.arc(mix(edge.x1, edge.x2, t) * s, mix(edge.y1, edge.y2, t) * s, Math.max(0.7, s * 0.055), 0, Math.PI * 2);
      ctx.fill();
    }
  }

  // A faint cell grid, only inside the supplied live sight.
  if (typeof grid.groundRadius === "number") {
    const { col, srow } = screenOf(grid, grid.party.x, grid.party.y);
    const cx = (col + 0.5) * s;
    const cy = (srow + 0.5) * s;
    const reach = (grid.groundRadius + 0.5) * s;
    const r = grid.groundRadius + 1;
    ctx.save();
    ctx.beginPath();
    ctx.arc(cx, cy, reach, 0, Math.PI * 2);
    ctx.clip();
    ctx.strokeStyle = "rgba(28, 22, 16, 0.2)";
    ctx.lineWidth = Math.max(0.5, s * 0.04);
    ctx.beginPath();
    for (let k = -r; k <= r + 1; k += 1) {
      ctx.moveTo((col + k) * s, (srow - r) * s);
      ctx.lineTo((col + k) * s, (srow + r + 1) * s);
      ctx.moveTo((col - r) * s, (srow + k) * s);
      ctx.lineTo((col + r + 1) * s, (srow + k) * s);
    }
    ctx.stroke();
    ctx.restore();
  }
}

// ── paint ─────────────────────────────────────────────────────────────────

const stats = { count: 0, lastMs: 0 };

/** The painter's own call record: how many paints ran and the last one's ms. */
export function travelPaintStats() {
  return { count: stats.count, lastMs: stats.lastMs };
}

function defaultCanvas(width, height) {
  const el = document.createElement("canvas");
  el.width = width;
  el.height = height;
  return el;
}

function sized(cache, key, width, height, createCanvas) {
  const current = cache[key];
  if (current && current.width === width && current.height === height) return current;
  const el = createCanvas(width, height);
  cache[key] = el;
  return el;
}

/**
 * Paints `grid` onto `ctx`, whose canvas is `width * samplesPerCell` by
 * `height * samplesPerCell`. `cache` keeps the typed fields and the two
 * offscreen layers between calls (reused while the dimensions agree);
 * `createCanvas(w, h)` makes an offscreen layer (injectable for tests).
 * Returns the paint's duration in milliseconds.
 */
export function paintTravelMap(ctx, grid, { samplesPerCell = SAMPLES_PER_CELL, cache = {}, createCanvas = defaultCanvas } = {}) {
  const started = typeof performance !== "undefined" ? performance.now() : Date.now();
  const s = samplesPerCell;
  const fw = grid.width * s;
  const fh = grid.height * s;
  const rgba = buildField(grid, { samplesPerCell: s }, cache);

  // 1–2. The masked terrain field.
  const field = sized(cache, "fieldCanvas", fw, fh, createCanvas);
  const fctx = field.getContext("2d");
  const image = cache.image?.width === fw && cache.image?.height === fh ? cache.image : fctx.createImageData(fw, fh);
  image.data.set(rgba);
  cache.image = image;
  fctx.putImageData(image, 0, 0);
  ctx.globalCompositeOperation = "source-over";
  ctx.clearRect(0, 0, fw, fh);
  ctx.drawImage(field, 0, 0);

  // 3. Ink on its own layer, clipped to the reveal mask (the field's alpha).
  const ink = sized(cache, "inkCanvas", fw, fh, createCanvas);
  const ictx = ink.getContext("2d");
  ictx.globalCompositeOperation = "source-over";
  ictx.clearRect(0, 0, fw, fh);
  drawInk(ictx, grid, s);
  ictx.globalCompositeOperation = "destination-in";
  ictx.drawImage(field, 0, 0);
  ictx.globalCompositeOperation = "source-over";
  ctx.drawImage(ink, 0, 0);

  // 4. Light on painted pixels only.
  const look = PHASE_LOOK[grid.lightPhase] ?? null;
  const radius = typeof grid.groundRadius === "number" ? grid.groundRadius : null;
  const { col, srow } = screenOf(grid, grid.party.x, grid.party.y);
  const lx = (col + 0.5) * s;
  const ly = (srow + 0.5) * s;
  ctx.globalCompositeOperation = "source-atop";
  if (radius !== null) {
    const memory = (look ?? PHASE_LOOK.day).memory;
    const dim = ctx.createRadialGradient(lx, ly, Math.max(0.4, radius + 0.1) * s, lx, ly, (radius + 1.1) * s);
    dim.addColorStop(0, "rgba(8, 9, 12, 0)");
    dim.addColorStop(1, `rgba(8, 9, 12, ${memory})`);
    ctx.fillStyle = dim;
    ctx.fillRect(0, 0, fw, fh);
  }
  if (look?.wash) {
    ctx.fillStyle = look.wash;
    ctx.fillRect(0, 0, fw, fh);
  }
  if (grid.lightPhase === "night" && radius !== null) {
    const moon = ctx.createRadialGradient(lx, ly, 0, lx, ly, (radius + 1.1) * s);
    moon.addColorStop(0, "rgba(170, 190, 230, 0.18)");
    moon.addColorStop(1, "rgba(170, 190, 230, 0)");
    ctx.fillStyle = moon;
    ctx.fillRect(0, 0, fw, fh);
  }
  ctx.globalCompositeOperation = "source-over";
  const ended = typeof performance !== "undefined" ? performance.now() : Date.now();
  stats.count += 1;
  stats.lastMs = ended - started;
  return stats.lastMs;
}
