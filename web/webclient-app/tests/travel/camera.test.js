// The travel camera and its shared glyph states (wilderness-travel-map-ui,
// design "Camera and measurements" and "Overlay and shared glyph
// ownership"). Pure functions over synthetic rectangles, plus the glyph
// consumers mounted in jsdom.

import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import {
  FIT_MIN_CELL,
  ZOOM,
  bearingAngle,
  cellCentre,
  cellSize,
  clampZoom,
  fitRouteCamera,
  followCamera,
  openStage,
  projectSightings,
  safeScale,
  stepZoom,
} from "../../lib/travel-camera.js";
import { SIGHTING_BEARINGS } from "../../lib/area_map_view.js";
import { PARTY_GLYPH, TRAVEL_GLYPHS } from "../../lib/map_glyphs.js";
import MapNodeGlyph from "../../components/MapNodeGlyph.vue";
import TravelGlyph from "../../components/travel/TravelGlyph.vue";
import TravelMapView from "../../components/travel/TravelMap.vue";

const rect = (left, top, width, height) => ({ left, top, width, height, right: left + width, bottom: top + height });

describe("zoom", () => {
  it("steps by 4 between 18 and 46 and scales once by the UI scale", () => {
    expect(ZOOM).toMatchObject({ min: 18, max: 46, step: 4, initial: 30 });
    expect(stepZoom(30, 1)).toBe(34);
    expect(stepZoom(30, -1)).toBe(26);
    expect(stepZoom(46, 1)).toBe(46);
    expect(stepZoom(18, -1)).toBe(18);
    expect(clampZoom(31)).toBe(30);
    expect(clampZoom(500)).toBe(46);
    expect(cellSize(30, 1.4)).toBeCloseTo(42);
    expect(cellSize(30, Number.NaN)).toBe(30);
    expect(safeScale(0)).toBe(1);
  });
});

describe("openStage", () => {
  it("is the strip between the header and the band, narrowed past both side columns", () => {
    const { stage, safe } = openStage({
      root: rect(0, 0, 1451, 790),
      headerBottom: 48,
      bandTop: 570,
      left: rect(16, 400, 360, 170),
      right: rect(1145, 106, 290, 90),
      gap: 16,
    });
    expect(stage).toEqual({ left: 0, top: 48, right: 1451, bottom: 570 });
    expect(safe).toEqual({ left: 392, top: 48, right: 1129, bottom: 570 });
  });

  it("falls back to the root's own edges when the frame is absent", () => {
    const { stage, safe } = openStage({ root: rect(10, 20, 800, 600), gap: 16 });
    expect(stage).toEqual({ left: 0, top: 0, right: 800, bottom: 600 });
    expect(safe).toEqual({ left: 16, top: 0, right: 784, bottom: 600 });
  });

  it("drops the side exclusions when they leave no room", () => {
    const { safe } = openStage({ root: rect(0, 0, 400, 300), left: rect(0, 0, 250, 10), right: rect(150, 0, 100, 10) });
    expect([safe.left, safe.right]).toEqual([0, 400]);
  });
});

describe("followCamera", () => {
  it("centres the party cell between the header and the band", () => {
    const stage = { left: 0, top: 48, right: 1451, bottom: 570 };
    for (const party of [{ x: 100, y: 200 }, { x: -3, y: 7 }]) {
      const cam = followCamera({ party, cellPx: 30, stage });
      const centre = cellCentre(party.x, party.y, 30);
      expect(centre.x + cam.tx).toBeCloseTo(725.5);
      expect(centre.y + cam.ty).toBeCloseTo(309);
    }
  });

  it("puts north up: a cell north of the party sits above it on screen", () => {
    const stage = { left: 0, top: 0, right: 600, bottom: 400 };
    const cam = followCamera({ party: { x: 5, y: 5 }, cellPx: 20, stage });
    expect(cellCentre(5, 6, 20).y + cam.ty).toBeLessThan(cellCentre(5, 5, 20).y + cam.ty);
    expect(cellCentre(6, 5, 20).x + cam.tx).toBeGreaterThan(cellCentre(5, 5, 20).x + cam.tx);
  });
});

describe("fitRouteCamera", () => {
  const safe = { left: 392, top: 48, right: 1129, bottom: 570 };
  const bounds = (cam, points) => {
    const xs = points.flatMap((p) => [p.x * cam.cellPx + cam.tx, (p.x + 1) * cam.cellPx + cam.tx]);
    const ys = points.flatMap((p) => [-(p.y + 1) * cam.cellPx + cam.ty, -p.y * cam.cellPx + cam.ty]);
    return { left: Math.min(...xs), right: Math.max(...xs), top: Math.min(...ys), bottom: Math.max(...ys) };
  };

  it("frames the party, route and destination inside the safe rectangle", () => {
    const points = [{ x: 100, y: 200 }, { x: 101, y: 201 }, { x: 108, y: 196 }, { x: 112, y: 193 }];
    const cam = fitRouteCamera({ points, cellPx: 30, minCellPx: FIT_MIN_CELL, safe });
    const box = bounds(cam, points);
    expect(box.left).toBeGreaterThanOrEqual(safe.left - 1e-6);
    expect(box.right).toBeLessThanOrEqual(safe.right + 1e-6);
    expect(box.top).toBeGreaterThanOrEqual(safe.top - 1e-6);
    expect(box.bottom).toBeLessThanOrEqual(safe.bottom + 1e-6);
    expect(cam.cellPx).toBeLessThanOrEqual(30);
  });

  it("never grows past the zoom cell and never shrinks below the scaled minimum", () => {
    const short = fitRouteCamera({ points: [{ x: 0, y: 0 }, { x: 1, y: 0 }], cellPx: 30, minCellPx: 14, safe });
    expect(short.cellPx).toBe(30);
    const long = [{ x: 0, y: 0 }, { x: 80, y: 0 }];
    const cam = fitRouteCamera({ points: long, cellPx: 42, minCellPx: 14 * 1.4, safe });
    expect(cam.cellPx).toBeCloseTo(19.6);
    // Too long even at the minimum: centred and clipped by the stage.
    const box = bounds(cam, long);
    expect((box.left + box.right) / 2).toBeCloseTo((safe.left + safe.right) / 2);
  });

  it("refits when the side columns change, at the same zoom", () => {
    const points = [{ x: 0, y: 0 }, { x: 30, y: 0 }];
    const wide = fitRouteCamera({ points, cellPx: 30, minCellPx: 14, safe: { left: 0, top: 0, right: 1400, bottom: 500 } });
    const narrow = fitRouteCamera({ points, cellPx: 30, minCellPx: 14, safe: { left: 400, top: 0, right: 1000, bottom: 500 } });
    expect(narrow.cellPx).toBeLessThan(wide.cellPx);
  });
});

describe("projectSightings", () => {
  const safe = { left: 392, top: 48, right: 1129, bottom: 570 };
  const inset = { x: 120, y: 38 };

  it("places every bearing on the inset edge along its own direction", () => {
    const sightings = SIGHTING_BEARINGS.map((bearing) => ({ bearing, distance_km: 10, silhouette_zh: "某物", name: null }));
    const cards = projectSightings(sightings, { safe, inset });
    expect(cards).toHaveLength(16);
    const cx = (safe.left + safe.right) / 2;
    const cy = (safe.top + safe.bottom) / 2;
    for (const card of cards) {
      const onEdge =
        Math.abs(card.x - (safe.left + inset.x)) < 1e-6 ||
        Math.abs(card.x - (safe.right - inset.x)) < 1e-6 ||
        Math.abs(card.y - (safe.top + inset.y)) < 1e-6 ||
        Math.abs(card.y - (safe.bottom - inset.y)) < 1e-6;
      expect(onEdge).toBe(true);
      expect(card.x).toBeGreaterThanOrEqual(safe.left + inset.x - 1e-6);
      expect(card.x).toBeLessThanOrEqual(safe.right - inset.x + 1e-6);
      expect(card.y).toBeGreaterThanOrEqual(safe.top + inset.y - 1e-6);
      expect(card.y).toBeLessThanOrEqual(safe.bottom - inset.y + 1e-6);
      // Clockwise from north: the card lies along (sin a, -cos a).
      const angle = Math.atan2(card.x - cx, -(card.y - cy));
      const expected = bearingAngle(card.sighting.bearing);
      expect(Math.abs(Math.atan2(Math.sin(angle - expected), Math.cos(angle - expected)))).toBeLessThan(1e-6);
    }
    expect(cards.find((c) => c.sighting.bearing === "北").y).toBeCloseTo(safe.top + inset.y);
    expect(cards.find((c) => c.sighting.bearing === "東").x).toBeCloseTo(safe.right - inset.x);
  });

  it("moves with the exclusions and never invents a coordinate", () => {
    const sighting = { bearing: "西", distance_km: 15, silhouette_zh: "瞭望台", name: null };
    const [wide] = projectSightings([sighting], { safe: { ...safe, left: 0 }, inset });
    const [narrow] = projectSightings([sighting], { safe, inset });
    expect(narrow.x).toBeGreaterThan(wide.x);
    expect(Object.keys(narrow).sort()).toEqual(["angle", "sighting", "ux", "uy", "x", "y"]);
    expect(narrow.sighting).toBe(sighting);
    expect(projectSightings([{ bearing: "上方" }], { safe, inset })).toEqual([]);
  });
});

describe("shared travel glyph states", () => {
  const wrap = (component, props) => mount(component, { props });

  it("draws the party seal from MapNodeGlyph and leaves the existing states unchanged", () => {
    const party = wrap(MapNodeGlyph, { state: "party", size: 1.4, testIds: { marker: "seal" } });
    expect(party.find('[data-testid="seal"]').attributes("r")).toBe(String(PARTY_GLYPH.bodyR));
    expect(party.find(".map-glyph").attributes("transform")).toBe("scale(1.4)");
    expect(party.findAll("circle")).toHaveLength(3);
    expect(party.find(".map-glyph__here-ring").exists()).toBe(false);
    const current = wrap(MapNodeGlyph, { state: "current" });
    expect(current.find(".map-glyph__party-body").exists()).toBe(false);
    expect(current.findAll("circle").map((c) => c.classes()[0])).toEqual([
      "map-glyph__here-glow",
      "map-glyph__here-ring",
      "map-glyph__here-dot",
    ]);
    const visited = wrap(MapNodeGlyph, { state: "visited", gate: true });
    expect(visited.find(".map-glyph__gate").exists()).toBe(true);
  });

  it("differs between surfaces only by its whole-group scale", () => {
    for (const [kind, state] of [["landmark", null], ["neighbour", "aimed"], ["hostile", null], ["route", "severe"]]) {
      const a = wrap(TravelGlyph, { kind, state, size: 1 });
      const b = wrap(TravelGlyph, { kind, state, size: 2.2 });
      expect(b.find("g").attributes("transform")).toBe("scale(2.2)");
      expect(b.find("g").html().replace(/ transform="[^"]*"/, "")).toBe(a.find("g").html());
    }
  });

  it("separates every state by shape, not colour alone", () => {
    const shape = (kind, state) => wrap(TravelGlyph, { kind, state }).find("g").html();
    const neighbours = ["open", "aimed", "blocked", "unknown"].map((state) => wrap(TravelGlyph, { kind: "neighbour", state }));
    const radii = neighbours.map((w) => w.find("circle").attributes("r"));
    expect(radii[1]).not.toBe(radii[0]);
    expect(radii[3]).not.toBe(radii[0]);
    expect(neighbours.map((w) => w.find("g").attributes("data-state"))).toEqual(["open", "aimed", "blocked", "unknown"]);
    const routes = ["normal", "light", "moderate", "severe"].map((state) => shape("route", state));
    expect(new Set(routes).size).toBe(4);
    expect(routes[0]).toMatch(/<circle/);
    expect(routes[1]).toMatch(/<path/);
    // Severe is the ring with its core (each mark also sits on one ink seat).
    expect((routes[3].match(/travel-glyph__(ring|core)/g) || []).length).toBe(2);
    expect(routes.every((html) => (html.match(/travel-glyph__halo-ink/g) || []).length === 1)).toBe(true);
  });

  it("draws the landmark as the band ornament's diamond", () => {
    const tokens = readFileSync(resolve(process.cwd(), "web/webclient-app/styles/tokens.css"), "utf8");
    const ornament = decodeURIComponent(tokens.match(/--band-ornament: url\("data:image\/svg\+xml,([^"]+)"\)/)[1]);
    // The ornament's diamond spans 10.3..19.7 around x = 15 and its dot r = 1.3.
    const diamond = ornament.match(/M15 ([\d.]+) ([\d.]+) 5\.5 15 ([\d.]+) ([\d.]+) 5\.5Z/);
    expect(15 - Number(diamond[4])).toBeCloseTo(TRAVEL_GLYPHS.landmark.half);
    expect(Number(ornament.match(/r='([\d.]+)'/)[1])).toBe(TRAVEL_GLYPHS.landmark.dotR);
    const glyph = wrap(TravelGlyph, { kind: "landmark" });
    const h = TRAVEL_GLYPHS.landmark.half;
    expect(glyph.find("path").attributes("d")).toBe(`M0 ${-h} L${h} 0 L0 ${h} L${-h} 0 Z`);
  });
});

describe("TravelMap overlay consumers", () => {
  // A 7 x 7 window around (3, 3): the east neighbour has a committed move,
  // the west one is known without one, the north row is undisclosed.
  function grid(extra = {}) {
    const cells = [];
    for (let y = 0; y < 7; y += 1) {
      for (let x = 0; x < 7; x += 1) {
        const known = y <= 3;
        const node =
          x === 4 && y === 3
            ? { id: "e", action: { kind: "move", exit_ref: "e_e", destination: "e" }, landmark: null }
            : x === 1 && y === 1
              ? { id: "lm", action: null, landmark: { name: "合成石標" } }
              : null;
        cells.push({ x, y, known, terrain: known ? "open_ground" : null, band: null, tier: null, road: false, ford: false, node, display: null });
      }
    }
    return {
      mapId: "m", title: "合成", cellKm: 1, origin: { x: 0, y: 0 }, width: 7, height: 7, cells,
      party: { x: 3, y: 3 }, lightPhase: null, groundRadius: null, entities: [], sightings: [], ...extra,
    };
  }

  it("marks neighbours from committed facts only and suppresses absent decorations", () => {
    const w = mount(TravelMapView, { props: { grid: grid(), status: "ready" } });
    const all = w.findAll('[data-testid="travel-map__neighbour"]').map((g) => g.attributes("data-state"));
    expect(all.filter((s) => s === "open")).toHaveLength(1);
    expect(all.filter((s) => s === "unknown")).toHaveLength(3);
    expect(all.filter((s) => s === "blocked")).toHaveLength(4);
    expect(all).not.toContain("aimed");
    expect(w.find('[data-testid="travel-map__party"]').exists()).toBe(true);
    // No radius: no sight ring; no hostiles; the landmark carries its name.
    expect(w.find('[data-testid="travel-map__sight"]').exists()).toBe(false);
    expect(w.findAll('[data-testid="travel-map__hostile"]')).toHaveLength(0);
    expect(w.findAll('[data-testid="travel-map__landmark"]')).toHaveLength(1);
    expect(w.text()).toContain("合成石標");
  });

  it("aims only an open neighbour and hides the targets while walking", async () => {
    const w = mount(TravelMapView, { props: { grid: grid(), status: "ready", aim: "east" } });
    expect(w.findAll('[data-testid="travel-map__neighbour"]').filter((g) => g.attributes("data-state") === "aimed")).toHaveLength(1);
    expect(w.get('[data-testid="travel-map__aim-chip"]').classes()).not.toContain("is-blocked");
    await w.setProps({ aim: "west" });
    expect(w.findAll('[data-testid="travel-map__neighbour"]').filter((g) => g.attributes("data-state") === "aimed")).toHaveLength(0);
    expect(w.get('[data-testid="travel-map__aim-chip"]').classes()).toContain("is-blocked");
    await w.setProps({ walking: { kind: "direction" } });
    expect(w.findAll('[data-testid="travel-map__neighbour"]')).toHaveLength(0);
    expect(w.find('[data-testid="travel-map__party"]').exists()).toBe(true);
  });

  it("zooms one step per wheel notch and takes no pick from a map that is not current", async () => {
    const w = mount(TravelMapView, { props: { grid: grid(), status: "ready" } });
    const stage = w.get('[data-testid="travel-map"]');
    // A trackpad's stream of small deltas adds up to one notch.
    for (let k = 0; k < 9; k += 1) await stage.trigger("wheel", { deltaY: -10 });
    expect(stage.attributes("data-zoom")).toBe("30");
    await stage.trigger("wheel", { deltaY: -10 });
    expect(stage.attributes("data-zoom")).toBe("34");
    await stage.trigger("wheel", { deltaY: 300 });
    expect(stage.attributes("data-zoom")).toBe("22");
    await w.setProps({ status: "unavailable" });
    await stage.trigger("click", { clientX: 5, clientY: 5 });
    expect(w.emitted("pick")).toBeUndefined();
  });

  it("draws supplied hostiles, the sight ring and sighting cards without coordinates", () => {
    const w = mount(TravelMapView, {
      props: {
        grid: grid({
          groundRadius: 2,
          entities: [
            { id: "h1", cell: { x: 2, y: 2 }, kind: "hostile", hostile: true, label: "合成狼", count: 2, threat: null },
            { id: "n1", cell: { x: 2, y: 1 }, kind: "npc", hostile: false, label: "合成商人" },
          ],
          sightings: [{ bearing: "北北東", distance_km: 25, silhouette_zh: "合成石塔", name: null }],
        }),
        status: "ready",
      },
    });
    expect(w.findAll('[data-testid="travel-map__hostile"]')).toHaveLength(1);
    const chip = w.findAll(".tm-chip--seal");
    expect(chip).toHaveLength(1);
    expect(chip[0].text()).toContain("合成狼");
    expect(chip[0].text()).toMatch(/\b2\b/);
    expect(w.text()).not.toContain("合成商人");
    expect(w.find('[data-testid="travel-map__sight"]').exists()).toBe(true);
    const card = w.get('[data-testid="travel-map__sighting"]');
    expect(card.text()).toContain("北北東");
    expect(card.text()).toMatch(/\b25\b/);
    expect(card.text()).toContain("合成石塔");
  });
});
