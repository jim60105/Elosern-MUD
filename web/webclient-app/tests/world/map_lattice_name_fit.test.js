import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import MapLattice from "../../components/MapLattice.vue";
import { localMapModelFor } from "../../stories/fixtures.js";
import { CELL_EM, textCells } from "../../lib/mono_cells.js";
import { REPORTED_WILDERNESS_PAYLOAD } from "./map_lattice_support.js";

describe("The island's marker names obey the geometry that reserves them (webclient-minimap-07-overlay-marker-name-fit)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
  });

  it("Task 1.2: pins pre-change island baseline for drawn names, stacked tspans, and gutter", () => {
    wrapper = mount(MapLattice, {
      props: {
        localMap: localMapModelFor(REPORTED_WILDERNESS_PAYLOAD),
        labelMax: 4,
        markerScale: 1,
        canvasSize: 240,
        markerNames: true,
      },
    });
    // render-auto-scaled-minimap-island: the island is the projection's
    // fixed 240-unit square, so its lone side markers stand on the rim band
    // (inset by the 7-unit diamond's reach plus 1.5) and every name is drawn
    // whole inside the square: 聖潔王都 fits the band below its diamond; the
    // 11-glyph 西部丘陵與谷地（南門） does not fit on one side of its diamond,
    // so it reads through it down the band column — its head above the
    // diamond, its tail below.
    const svg = wrapper.get("svg.local-map__lattice");
    expect(Number(svg.attributes("width"))).toBe(240);
    expect(svg.attributes("viewBox")).toBe("0 0 240 240");
    const reach = Math.SQRT2 * 7;
    const inset = reach + 1.5;
    const west = wrapper.vm.fittedEdgeMarkers.find((m) => m.id === "r:west");
    expect(west.x).toBeCloseTo(inset, 6);
    expect(west.y).toBeCloseTo(120, 6);

    const glyphsOf = (marker) =>
      marker.get("text.local-map__edge-marker-name--island").findAll("tspan");
    const westGlyphs = glyphsOf(wrapper.get('[data-testid="local-map__edge-marker--r:west"]'));
    expect(westGlyphs.map((g) => g.text()).join("")).toBe("西部丘陵與谷地（南門）");
    const ys = westGlyphs.map((g) => Number(g.attributes("y")) + west.y);
    for (const glyph of westGlyphs) {
      expect(Number(glyph.attributes("x")) + west.x).toBeCloseTo(3 + 8, 6);
    }
    // Reading order runs top to bottom, skipping the diamond's own span.
    expect([...ys].sort((a, b) => a - b)).toEqual(ys);
    expect(ys.some((y) => y < west.y)).toBe(true);
    expect(ys.some((y) => y > west.y)).toBe(true);
    for (const y of ys) {
      expect(y - 12.8 >= west.y + reach || y + 3.2 <= west.y - reach).toBe(true);
      expect(y - 12.8).toBeGreaterThanOrEqual(0);
      expect(y + 3.2).toBeLessThanOrEqual(240);
    }

    const east = wrapper.vm.fittedEdgeMarkers.find((m) => m.id === "r:east");
    const eastGlyphs = glyphsOf(wrapper.get('[data-testid="local-map__edge-marker--r:east"]'));
    expect(eastGlyphs.map((g) => g.text()).join("")).toBe("聖潔王都");
    // The band column itself, directly below the diamond.
    for (const glyph of eastGlyphs) {
      expect(Number(glyph.attributes("x")) + east.x).toBeCloseTo(240 - 3 - 8, 6);
      expect(Number(glyph.attributes("y")) + east.y).toBeGreaterThan(east.y + reach);
    }
  });

  it("island rim names stay whole, inside the square and apart from one another", () => {
    const crowded = {
      schema_version: 1,
      available: true,
      layer: "wilderness",
      title: "西部荒野",
      current_node: "w:1:1",
      nodes: [
        ...REPORTED_WILDERNESS_PAYLOAD.nodes.slice(0, 9),
        { id: "r:top_1", label: "灰鬮荒原第一要塞", x: 0, y: 10, visibility: "remembered", landmark: true },
        { id: "r:top_2", label: "灰鬮荒原第二要塞", x: 1, y: 10, visibility: "remembered", landmark: true },
        { id: "r:top_3", label: "灰鬮荒原第三要塞", x: 2, y: 10, visibility: "remembered", landmark: true },
        { id: "r:left_1", label: "西部丘陵與谷地（南門）", x: -10, y: 0, visibility: "remembered", landmark: true },
        { id: "r:left_2", label: "西部丘陵與谷地（北門）", x: -10, y: 2, visibility: "remembered", landmark: true },
        { id: "r:long", label: "灰鬮荒原第一南關隘道前哨站營", x: 10, y: 1, visibility: "remembered", landmark: true },
      ],
    };
    const w = mount(MapLattice, {
      props: { localMap: localMapModelFor(crowded), canvasSize: 240, markerNames: true },
    });
    const boxes = [];
    for (const marker of w.vm.fittedEdgeMarkers) {
      const lines = marker.rimName.lines;
      expect(lines.map((line) => line.text).join("")).toBe(marker.name);
      for (const line of lines) {
        const width = marker.rimName.horizontal ? textCells(line.text) * CELL_EM * 16 : 16;
        const left = marker.rimName.horizontal ? marker.x + line.x : marker.x + line.x - 8;
        const top = marker.y + line.y - 12.8;
        const box = { id: marker.id, left, right: left + width, top, bottom: top + 16 };
        expect(box.left).toBeGreaterThanOrEqual(0);
        expect(box.right).toBeLessThanOrEqual(240);
        expect(box.top).toBeGreaterThanOrEqual(0);
        expect(box.bottom).toBeLessThanOrEqual(240);
        boxes.push(box);
      }
    }
    for (let i = 0; i < boxes.length; i += 1) {
      for (let j = i + 1; j < boxes.length; j += 1) {
        if (boxes[i].id === boxes[j].id) continue;
        const a = boxes[i];
        const b = boxes[j];
        const apart = a.right <= b.left + 1e-6 || b.right <= a.left + 1e-6 || a.bottom <= b.top + 1e-6 || b.bottom <= a.top + 1e-6;
        expect(apart, `${a.id} vs ${b.id}`).toBe(true);
      }
    }
    w.unmount();
  });

});
