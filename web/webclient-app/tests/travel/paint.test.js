// The travel painter (wilderness-travel-map-ui, design "Drawing contract").
// Synthetic grids only: each case builds the facts it needs and checks the
// painter's pixels, stroke models and compositing order against independent
// expectations. jsdom has no 2D canvas, so the canvas calls run on a
// recording context; real pixels in a real browser are the managed
// TravelMapTests' job.

import { describe, expect, it } from "vitest";
import {
  PHASE_LOOK,
  SAMPLES_PER_CELL,
  buildField,
  districtEdges,
  paintSignature,
  paintTravelMap,
  strokeChains,
  summitCells,
  textureHash,
  travelPaintStats,
  wallEdges,
} from "../../lib/travel-paint.js";

const S = SAMPLES_PER_CELL;

/**
 * A synthetic grid of `w` x `h` cells at `origin`; `fact(x, y)` returns a
 * cell's facts (`null` for unknown). Rows run south to north like the
 * adapter's.
 */
function makeGrid({ w = 9, h = 9, origin = { x: 0, y: 0 }, party = null, fact, lightPhase = null, groundRadius = null } = {}) {
  const cells = [];
  for (let row = 0; row < h; row += 1) {
    for (let col = 0; col < w; col += 1) {
      const x = origin.x + col;
      const y = origin.y + row;
      const f = fact(x, y);
      cells.push({
        x,
        y,
        known: f !== null,
        terrain: f?.terrain ?? null,
        band: f ? (f.band ?? null) : null,
        tier: f ? (f.tier ?? 0) : null,
        road: !!f?.road,
        ford: !!f?.ford,
        node: null,
        display: f?.display ?? null,
      });
    }
  }
  return {
    mapId: "synthetic",
    origin,
    width: w,
    height: h,
    cells,
    party: party ?? { x: origin.x + Math.floor(w / 2), y: origin.y + Math.floor(h / 2) },
    lightPhase,
    groundRadius,
    entities: [],
    sightings: [],
  };
}

const open = () => ({ terrain: "open_ground", band: 4 });

/** RGBA of the field sample at the centre of world cell (x, y). */
function centrePixel(grid, rgba, x, y) {
  const col = x - grid.origin.x;
  const srow = grid.height - 1 - (y - grid.origin.y);
  const i = col * S + S / 2;
  const j = srow * S + S / 2;
  const o = (j * grid.width * S + i) * 4;
  return [...rgba.slice(o, o + 4)];
}

function saturation([r, g, b]) {
  return Math.max(r, g, b) - Math.min(r, g, b);
}

// A recording 2D context: every property write and call in order.
function recorder(width, height) {
  const log = [];
  const ctx = new Proxy(
    { canvas: { width, height } },
    {
      get(target, key) {
        if (key in target) return target[key];
        if (key === "createImageData") return (w, h) => ({ width: w, height: h, data: new Uint8ClampedArray(w * h * 4) });
        if (key === "createRadialGradient") return (...args) => ({ args, addColorStop: () => {} });
        return (...args) => log.push({ call: key, args });
      },
      set(target, key, value) {
        log.push({ set: key, value });
        target[key] = value;
        return true;
      },
    },
  );
  return { ctx, log };
}

function fakeCanvasFactory() {
  const made = [];
  return {
    made,
    createCanvas(width, height) {
      const rec = recorder(width, height);
      const el = { width, height, rec, getContext: () => rec.ctx };
      made.push(el);
      return el;
    },
  };
}

describe("buildField: disclosure", () => {
  it("keeps unknown ground fully transparent and known ground opaque", () => {
    // Known cells form the west half; everything east of x = 4 is unknown.
    const grid = makeGrid({ fact: (x) => (x <= 4 ? open() : null) });
    const rgba = buildField(grid);
    expect(rgba.length).toBe(grid.width * S * grid.height * S * 4);
    for (let y = 0; y < 9; y += 1) {
      expect(centrePixel(grid, rgba, 2, y)[3]).toBe(255);
      for (let x = 5; x < 9; x += 1) expect(centrePixel(grid, rgba, x, y)[3]).toBe(0);
    }
    // No pixel deeper than half a cell into the unknown side is painted.
    const fw = grid.width * S;
    for (let j = 0; j < grid.height * S; j += 1) {
      for (let i = Math.ceil(5.5 * S); i < fw; i += 1) expect(rgba[(j * fw + i) * 4 + 3]).toBe(0);
    }
  });

  it("paints identical facts identically and the same world ground the same after the window moves", () => {
    const fact = (x, y) => ((x + y) % 5 === 0 ? null : { terrain: x > 5 ? "woodland" : "hills", band: (x + 2 * y) % 9 });
    const a = makeGrid({ origin: { x: 10, y: 20 }, fact });
    const again = buildField(a, {}, {});
    expect(buildField(a, {}, {})).toEqual(again);
    // One cell east: the overlapping world cells carry the same pixels.
    const b = makeGrid({ origin: { x: 11, y: 20 }, fact });
    const fa = buildField(a, {}, {});
    const fb = buildField(b, {}, {});
    for (let y = 22; y <= 26; y += 1) {
      for (let x = 13; x <= 16; x += 1) expect(centrePixel(b, fb, x, y)).toEqual(centrePixel(a, fa, x, y));
    }
  });

  it("shades flat and neutral while any known cell lacks a band", () => {
    const banded = makeGrid({ fact: (x, y) => ({ terrain: "open_ground", band: x + y }) });
    const partly = makeGrid({ fact: (x, y) => ({ terrain: "open_ground", band: x === 0 && y === 0 ? null : x + y }) });
    const lum = (p) => p[0] + p[1] + p[2];
    const spread = (grid) => {
      const rgba = buildField(grid, {}, {});
      const values = [];
      for (let y = 2; y < 7; y += 1) for (let x = 2; x < 7; x += 1) values.push(lum(centrePixel(grid, rgba, x, y)));
      return Math.max(...values) - Math.min(...values);
    };
    // Relief lifts the higher, north-west-facing ground; flat ground keeps
    // only the texture grain.
    expect(spread(banded)).toBeGreaterThan(spread(partly));
    expect(spread(partly)).toBeLessThan(40);
  });

  it("drains colour outside the supplied ground radius only", () => {
    const fact = () => ({ terrain: "woodland", band: 3 });
    const party = { x: 4, y: 4 };
    const lit = makeGrid({ fact, party, groundRadius: 1, lightPhase: "day" });
    const blind = makeGrid({ fact, party, groundRadius: null, lightPhase: "day" });
    const near = (g) => centrePixel(g, buildField(g, {}, {}), 4, 4);
    const far = (g) => centrePixel(g, buildField(g, {}, {}), 8, 8);
    expect(saturation(far(lit))).toBeLessThan(saturation(far(blind)) * 0.8);
    expect(near(lit)).toEqual(near(blind));
  });

  it("reuses its buffers while the dimensions agree", () => {
    const cache = {};
    const grid = makeGrid({ fact: open });
    const first = buildField(grid, {}, cache);
    const moved = makeGrid({ fact: open, party: { x: 2, y: 2 } });
    expect(buildField(moved, {}, cache)).toBe(first);
    const bigger = makeGrid({ w: 11, fact: open });
    expect(buildField(bigger, {}, cache)).not.toBe(first);
  });
});

describe("stroke models", () => {
  it("joins adjacent flagged cells into smoothed chains and skips lone cells", () => {
    // A road running east along y = 2 from x = 1..5, a lone road cell at
    // (7, 7) and a diagonal step (5,2) -> (6,3).
    const road = new Set(["1:2", "2:2", "3:2", "4:2", "5:2", "6:3", "7:7"]);
    const grid = makeGrid({ fact: (x, y) => ({ terrain: "open_ground", band: 3, road: road.has(`${x}:${y}`) }) });
    const chains = strokeChains(grid, (cell) => cell.road);
    expect(chains).toHaveLength(1);
    const [chain] = chains;
    expect(chain.closed).toBe(false);
    const ends = [chain.points[0], chain.points[chain.points.length - 1]];
    // Screen space: x = col + 0.5, y = (height - 1 - row) + 0.5.
    const centre = (x, y) => [x + 0.5, 8 - y + 0.5];
    expect(ends).toContainEqual(centre(1, 2));
    expect(ends).toContainEqual(centre(6, 3));
    // Chaikin keeps the ends and adds corner-cutting points.
    expect(chain.points.length).toBeGreaterThan(6);
  });

  it("closes a ring of flagged cells and draws no unflagged or unknown cell", () => {
    const ring = new Set(["2:2", "3:2", "4:2", "4:3", "4:4", "3:4", "2:4", "2:3"]);
    const grid = makeGrid({ fact: (x, y) => (x === 8 ? null : { terrain: ring.has(`${x}:${y}`) ? "water" : "open_ground" }) });
    const chains = strokeChains(grid, (cell) => cell.terrain === "water");
    expect(chains).toEqual([expect.objectContaining({ closed: true })]);
    expect(strokeChains(grid, (cell) => cell.road)).toEqual([]);
  });

  it("rings strict prominence maxima with one stable winner per plateau", () => {
    const tiers = { "2:2": 2, "3:2": 2, "6:6": 1, "6:7": 3 };
    const grid = makeGrid({ fact: (x, y) => ({ terrain: "hills", band: 5, tier: tiers[`${x}:${y}`] ?? 0 }) });
    const summits = summitCells(grid).map((c) => `${c.x}:${c.y}`);
    // The 2-2 plateau keeps its western cell (same y, smaller x); (6, 6) sits
    // under the tier-3 neighbour and does not ring.
    expect(summits.sort()).toEqual(["2:2", "6:7"]);
  });

  it("draws district edges and walls only between disclosed facts", () => {
    const fact = (x, y) => {
      if (y === 8) return null;
      return {
        terrain: x < 2 ? "settlement" : "open_ground",
        display: {
          district_key: x < 5 ? "west" : x === 5 ? null : "east",
          settlement: x < 2,
        },
      };
    };
    const grid = makeGrid({ fact });
    const district = districtEdges(grid);
    // x = 5 carries no key, so no edge is drawn on either side of it.
    expect(district).toEqual([]);
    const keyed = makeGrid({ fact: (x, y) => ({ terrain: "open_ground", display: { district_key: x < 4 ? "west" : "east", settlement: false } }) });
    expect(districtEdges(keyed)).toHaveLength(9);
    expect(districtEdges(keyed).every((edge) => edge.x1 === 4 && edge.x2 === 4)).toBe(true);
    // Walls run along x = 2 between known rows only: the unknown top row
    // carries none.
    const walls = wallEdges(grid);
    expect(walls).toHaveLength(8);
    expect(walls.every((edge) => edge.x1 === 2 && edge.x2 === 2 && edge.y1 >= 1)).toBe(true);
  });
});

describe("paintTravelMap", () => {
  function paintWith(grid) {
    const factory = fakeCanvasFactory();
    const { ctx, log } = recorder(grid.width * S, grid.height * S);
    paintTravelMap(ctx, grid, { cache: {}, createCanvas: factory.createCanvas });
    return { log, factory };
  }

  it("clips the ink to the reveal mask before any light reaches painted pixels", () => {
    const grid = makeGrid({ fact: () => ({ terrain: "woodland", band: 3 }), lightPhase: "dusk", groundRadius: 2 });
    const { log, factory } = paintWith(grid);
    const [field, ink] = factory.made;
    expect([field.width, field.height]).toEqual([grid.width * S, grid.height * S]);
    // The ink layer is masked by the field's own alpha (destination-in).
    const inkLog = ink.rec.log;
    const masking = inkLog.findIndex((entry) => entry.set === "globalCompositeOperation" && entry.value === "destination-in");
    expect(masking).toBeGreaterThan(0);
    // Every stroke precedes the mask; the mask is the field itself.
    expect(inkLog.slice(0, masking).some((entry) => entry.call === "stroke" || entry.call === "fill")).toBe(true);
    expect(inkLog.slice(masking).filter((entry) => entry.call === "stroke" || entry.call === "fill")).toEqual([]);
    expect(inkLog.slice(masking).find((entry) => entry.call === "drawImage").args[0]).toBe(field);
    const ops = log.filter((entry) => entry.set === "globalCompositeOperation").map((entry) => entry.value);
    expect(ops).toEqual(["source-over", "source-atop", "source-over"]);
    const draws = log.filter((entry) => entry.call === "drawImage").map((entry) => entry.args[0]);
    expect(draws).toEqual([field, ink]);
    const atop = log.findIndex((entry) => entry.value === "source-atop");
    const washes = log.slice(atop).filter((entry) => entry.set === "fillStyle").map((entry) => entry.value);
    expect(washes).toContain(PHASE_LOOK.dusk.wash);
  });

  it("adds no wash, memory dim or moon without a supplied phase and radius", () => {
    const { log } = paintWith(makeGrid({ fact: open }));
    expect(log.some((entry) => entry.value === "source-atop" && entry.set)).toBe(true);
    expect(log.filter((entry) => entry.call === "fillRect")).toEqual([]);
    const day = paintWith(makeGrid({ fact: open, lightPhase: "day", groundRadius: 3 }));
    // Day: the memory dim only.
    expect(day.log.filter((entry) => entry.call === "fillRect")).toHaveLength(1);
    const night = paintWith(makeGrid({ fact: open, lightPhase: "night", groundRadius: 1 }));
    // Night: the dim, the deep blue wash and the moonlit disc.
    expect(night.log.filter((entry) => entry.call === "fillRect")).toHaveLength(3);
    expect(night.log.some((entry) => entry.value === PHASE_LOOK.night.wash)).toBe(true);
  });

  it("counts every paint call", () => {
    const before = travelPaintStats().count;
    paintWith(makeGrid({ fact: open }));
    paintWith(makeGrid({ fact: open }));
    expect(travelPaintStats().count).toBe(before + 2);
  });
});

describe("paintSignature", () => {
  it("is equal for equal facts and changes with any painted fact", () => {
    const base = makeGrid({ fact: open, lightPhase: "day", groundRadius: 3 });
    const copy = makeGrid({ fact: open, lightPhase: "day", groundRadius: 3 });
    expect(copy).not.toBe(base);
    expect(paintSignature(copy)).toBe(paintSignature(base));
    const variants = [
      makeGrid({ fact: open, lightPhase: "dusk", groundRadius: 3 }),
      makeGrid({ fact: open, lightPhase: "day", groundRadius: 2 }),
      makeGrid({ fact: open, lightPhase: "day", groundRadius: 3, party: { x: 1, y: 1 } }),
      makeGrid({ fact: (x, y) => (x === 0 && y === 0 ? null : open()), lightPhase: "day", groundRadius: 3 }),
      makeGrid({ fact: (x) => ({ ...open(), road: x === 3 }), lightPhase: "day", groundRadius: 3 }),
      makeGrid({ origin: { x: 1, y: 0 }, fact: open, lightPhase: "day", groundRadius: 3 }),
    ];
    for (const grid of variants) expect(paintSignature(grid)).not.toBe(paintSignature(base));
  });

  it("texture hashing is a pure function of world coordinates", () => {
    expect(textureHash(12, -7, 3)).toBe(textureHash(12, -7, 3));
    expect(textureHash(12, -7, 3)).not.toBe(textureHash(13, -7, 3));
    expect(textureHash(0, 0)).toBeGreaterThanOrEqual(0);
    expect(textureHash(0, 0)).toBeLessThan(1);
  });
});

describe("TravelMap repaint keys", () => {
  // Manual animation frames and a no-op 2D context, so the component's own
  // scheduling decides when the real painter runs.
  async function harness() {
    const { mount } = await import("@vue/test-utils");
    const { nextTick } = await import("vue");
    const TravelMap = (await import("../../components/travel/TravelMap.vue")).default;
    const frames = [];
    const raf = globalThis.requestAnimationFrame;
    const caf = globalThis.cancelAnimationFrame;
    globalThis.requestAnimationFrame = (fn) => frames.push(fn);
    globalThis.cancelAnimationFrame = () => {};
    const getContext = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function fake() {
      return recorder(this.width, this.height).ctx;
    };
    const restore = () => {
      globalThis.requestAnimationFrame = raf;
      globalThis.cancelAnimationFrame = caf;
      HTMLCanvasElement.prototype.getContext = getContext;
    };
    const flush = async () => {
      await nextTick();
      while (frames.length) frames.shift()();
      await nextTick();
    };
    return { mount, TravelMap, flush, restore };
  }

  const gridAt = (party, extra = {}) =>
    makeGrid({ w: 11, h: 11, fact: (x, y) => (Math.abs(x - 5) + Math.abs(y - 5) > 7 ? null : open()), party, lightPhase: "day", groundRadius: 2, ...extra });

  it("repaints once per content change and never for camera, zoom, aim, hover or status", async () => {
    const h = await harness();
    try {
      const w = h.mount(h.TravelMap, { props: { grid: gridAt({ x: 5, y: 5 }), status: "ready" }, attachTo: document.body });
      await h.flush();
      const count = () => travelPaintStats().count;
      const start = count();
      expect(start).toBeGreaterThan(0);
      // An identical window republished as a new object.
      await w.setProps({ grid: gridAt({ x: 5, y: 5 }) });
      await h.flush();
      expect(count()).toBe(start);
      // Zoom, aim, hover, walking, UI scale and status.
      await w.get('[data-testid="travel-map"]').trigger("wheel", { deltaY: -100 });
      await w.setProps({ aim: "east", uiScale: 1.4, status: "refreshing" });
      await w.get('[data-testid="travel-map"]').trigger("pointermove", { clientX: 40, clientY: 40 });
      await h.flush();
      expect(w.get('[data-testid="travel-map"]').attributes("data-zoom")).toBe("34");
      expect(count()).toBe(start);
      // Two content changes inside one frame paint once; a change that
      // returns to the painted content paints nothing.
      await w.setProps({ grid: gridAt({ x: 6, y: 5 }) });
      await w.setProps({ grid: gridAt({ x: 6, y: 6 }) });
      await h.flush();
      expect(count()).toBe(start + 1);
      await w.setProps({ grid: gridAt({ x: 5, y: 5 }) });
      await w.setProps({ grid: gridAt({ x: 6, y: 6 }) });
      await h.flush();
      expect(count()).toBe(start + 1);
      const canvas = w.get('[data-testid="travel-map__canvas"]').element;
      expect([canvas.width, canvas.height]).toEqual([11 * S, 11 * S]);
      w.unmount();
    } finally {
      h.restore();
    }
  });
});
