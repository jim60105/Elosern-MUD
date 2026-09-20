import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import MapLattice from "../../components/MapLattice.vue";
import {
  LOCAL_MAP_INTERIOR_SAMPLE,
  LOCAL_MAP_SAMPLE,
  LOCAL_MAP_SINGLE_NODE_SAMPLE,
  LOCAL_MAP_TALL_LATTICE_SAMPLE,
  localMapModelFor,
} from "../../stories/fixtures.js";
import {
  REPORTED_WILDERNESS_PAYLOAD,
  UNIFORM_WILDERNESS_PAYLOAD,
  mountLattice as mountLatticeShared,
} from "./map_lattice_support.js";

describe("MapLattice draft lattice fidelity (webclient-minimap-06-draft-lattice-fidelity)", () => {
  let wrapper;
  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
  });

  function mountLattice(props = {}) {
    wrapper = mountLatticeShared((w) => {
      wrapper = w;
    }, props);
    return wrapper;
  }

  const ISLAND_PROPS = {
    colPitch: 40,
    rowPitch: 40,
    labelFont: 9,
    fieldFill: true,
    showAxis: true,
    fogVignette: true,
    markerNames: true,
  };

  describe("Wave 1: Coordinate-Field Layers", () => {
    it("Task 1.1: renders coordinate dot field registered to node centers with pitch tile", () => {
      const w = mountLattice({
        localMap: localMapModelFor(UNIFORM_WILDERNESS_PAYLOAD),
        ...ISLAND_PROPS,
      });
      const dotField = w.find('[data-testid="local-map__dot-field"]');
      expect(dotField.exists()).toBe(true);
      expect(dotField.attributes("aria-hidden")).toBe("true");
      expect(dotField.classes()).not.toContain("local-map__marker");
      expect(dotField.classes()).not.toContain("local-map__node-label");

      const pattern = w.find("defs pattern");
      expect(pattern.exists()).toBe(true);
      const pitchW = Number(pattern.attributes("width"));
      const pitchH = Number(pattern.attributes("height"));
      expect(pitchW).toBe(40);
      expect(pitchH).toBe(40);

      const circle = pattern.find("circle");
      expect(circle.exists()).toBe(true);
      expect(circle.attributes("r")).toBe("1.15");
      expect(circle.attributes("fill")).toBe("var(--ink-edge)");
      expect(circle.attributes("fill-opacity")).toBe("0.85");

      const cx = Number(circle.attributes("cx"));
      const cy = Number(circle.attributes("cy"));

      const nodeEls = w.findAll('[data-testid^="local-map__node--"]');
      expect(nodeEls.length).toBeGreaterThan(0);
      for (const nodeEl of nodeEls) {
        const transform = nodeEl.attributes("transform");
        const match = transform.match(/translate\(([-\d.]+),\s*([-\d.]+)\)/);
        expect(match).not.toBeNull();
        const nx = Number(match[1]);
        const ny = Number(match[2]);
        const remX = ((nx - cx) % pitchW + pitchW) % pitchW;
        const remY = ((ny - cy) % pitchH + pitchH) % pitchH;
        expect(Math.min(remX, pitchW - remX)).toBeCloseTo(0, 4);
        expect(Math.min(remY, pitchH - remY)).toBeCloseTo(0, 4);
      }
    });

    it("Task 1.1: renders dot field on overlay scale as well", () => {
      const w = mountLattice({
        localMap: localMapModelFor(REPORTED_WILDERNESS_PAYLOAD),
        colPitch: 280,
        rowPitch: 212,
        markerScale: 4.83,
        labelFont: 11,
        labelMax: 10,
        maxWidth: 848,
        fillWidth: true,
        overlayChrome: true,
      });
      const dotField = w.find('[data-testid="local-map__dot-field"]');
      expect(dotField.exists()).toBe(true);
      const pattern = w.find("defs pattern");
      expect(Number(pattern.attributes("width"))).toBe(280);
      expect(Number(pattern.attributes("height"))).toBe(212);
      const circle = pattern.find("circle");
      expect(Number(circle.attributes("r"))).toBeCloseTo(1.15 * 4.83, 4);
    });

    it("Task 1.1 & 1.4: omits dot field, vignette, and axis on graph variant", () => {
      const w = mountLattice({
        localMap: localMapModelFor(LOCAL_MAP_INTERIOR_SAMPLE),
        variant: "graph",
        ...ISLAND_PROPS,
      });
      expect(w.find('[data-testid="local-map__dot-field"]').exists()).toBe(false);
      expect(w.find('[data-testid="local-map__vignette"]').exists()).toBe(false);
      expect(w.find('[data-testid="local-map__axis"]').exists()).toBe(false);
    });

    it("Task 1.2: renders fog vignette with outer stop <= 0.50 only when prop set", () => {
      const wOff = mountLattice({
        localMap: localMapModelFor(LOCAL_MAP_SAMPLE),
        fogVignette: false,
      });
      expect(wOff.find('[data-testid="local-map__vignette"]').exists()).toBe(false);

      const wOn = mountLattice({
        localMap: localMapModelFor(LOCAL_MAP_SAMPLE),
        fogVignette: true,
      });
      const vignette = wOn.find('[data-testid="local-map__vignette"]');
      expect(vignette.exists()).toBe(true);
      expect(vignette.attributes("aria-hidden")).toBe("true");
      expect(vignette.classes()).not.toContain("local-map__marker");
      expect(vignette.classes()).not.toContain("local-map__node-label");

      const gradient = wOn.find("defs radialGradient");
      expect(gradient.exists()).toBe(true);
      const stops = gradient.findAll("stop");
      expect(stops).toHaveLength(3);
      expect(stops[0].attributes("offset")).toBe("0.5");
      expect(Number(stops[0].attributes("stop-opacity"))).toBe(0);
      expect(stops[1].attributes("offset")).toBe("0.78");
      expect(Number(stops[1].attributes("stop-opacity"))).toBe(0.26);
      expect(stops[2].attributes("offset")).toBe("1");
      expect(Number(stops[2].attributes("stop-opacity"))).toBeLessThanOrEqual(0.50);
      expect(Number(stops[2].attributes("stop-opacity"))).toBe(0.50);
    });

    it("Task 1.3: renders axis cross through current node only when prop set", () => {
      const wOff = mountLattice({
        localMap: localMapModelFor(LOCAL_MAP_SAMPLE),
        showAxis: false,
      });
      expect(wOff.find('[data-testid="local-map__axis"]').exists()).toBe(false);

      const wOn = mountLattice({
        localMap: localMapModelFor(LOCAL_MAP_SAMPLE),
        showAxis: true,
        colPitch: 40,
        rowPitch: 40,
      });
      const axis = wOn.find('[data-testid="local-map__axis"]');
      expect(axis.exists()).toBe(true);
      expect(axis.attributes("aria-hidden")).toBe("true");
      expect(axis.attributes("stroke")).toBe("var(--ink-edge)");
      expect(axis.attributes("stroke-width")).toBe("1.5");
      expect(axis.attributes("opacity")).toBe("0.8");
      expect(axis.classes()).not.toContain("local-map__marker");
      expect(axis.classes()).not.toContain("local-map__node-label");

      const lines = axis.findAll("line");
      expect(lines).toHaveLength(2);

      const currentNodeEl = wOn.get('[data-testid="local-map__node--grid:altoria:1:2"]');
      const match = currentNodeEl.attributes("transform").match(/translate\(([-\d.]+),\s*([-\d.]+)\)/);
      const curX = Number(match[1]);
      const curY = Number(match[2]);

      const svg = wOn.get("svg.local-map__lattice");
      const canvasW = Number(svg.attributes("width"));
      const canvasH = Number(svg.attributes("height"));

      expect(Number(lines[0].attributes("x1"))).toBe(0);
      expect(Number(lines[0].attributes("y1"))).toBe(curY);
      expect(Number(lines[0].attributes("x2"))).toBe(canvasW);
      expect(Number(lines[0].attributes("y2"))).toBe(curY);

      expect(Number(lines[1].attributes("x1"))).toBe(curX);
      expect(Number(lines[1].attributes("y1"))).toBe(0);
      expect(Number(lines[1].attributes("x2"))).toBe(curX);
      expect(Number(lines[1].attributes("y2"))).toBe(canvasH);
    });

    it("Task 1.3: draws no axis when no on-canvas current node exists", () => {
      const model = localMapModelFor(LOCAL_MAP_SAMPLE);
      const noCurrentModel = {
        ...model,
        nodes: model.nodes.map((n) => ({ ...n, visibility: "visible_visited", current: false })),
        currentNode: null,
      };
      const w = mountLattice({
        localMap: noCurrentModel,
        showAxis: true,
      });
      expect(w.find('[data-testid="local-map__axis"]').exists()).toBe(false);
    });

    it("Task 1.4: layers have pointer-events none and preserve relative paint order", () => {
      const w = mountLattice({
        localMap: localMapModelFor(LOCAL_MAP_SAMPLE),
        ...ISLAND_PROPS,
      });
      const svg = w.get("svg.local-map__lattice");
      const html = svg.html();

      const defsIdx = html.indexOf("<defs");
      const dotIdx = html.indexOf("local-map__dot-field");
      const vigIdx = html.indexOf("local-map__vignette");
      const edgeIdx = html.indexOf("local-map__edge");
      const axisIdx = html.indexOf("local-map__axis");
      const edgeMarkerIdx = html.indexOf("local-map__edge-marker");
      const nodeIdx = html.indexOf("local-map__node");

      expect(defsIdx).toBeLessThan(dotIdx);
      expect(dotIdx).toBeLessThan(vigIdx);
      expect(vigIdx).toBeLessThan(edgeIdx);
      expect(edgeIdx).toBeLessThan(axisIdx);
      expect(axisIdx).toBeLessThan(edgeMarkerIdx);
      expect(edgeMarkerIdx).toBeLessThan(nodeIdx);
    });

    it("Rubber Duck Issue 1: distinct instances receive unique pattern and fog IDs", () => {
      const MultiMount = {
        components: { MapLattice },
        props: ["p1", "p2"],
        template: `<div><MapLattice v-bind="p1" /><MapLattice v-bind="p2" /></div>`,
      };
      const w = mount(MultiMount, {
        props: {
          p1: { localMap: localMapModelFor(UNIFORM_WILDERNESS_PAYLOAD), ...ISLAND_PROPS },
          p2: { localMap: localMapModelFor(UNIFORM_WILDERNESS_PAYLOAD), colPitch: 280, rowPitch: 212, fogVignette: true },
        },
      });
      const patterns = w.findAll("defs pattern");
      expect(patterns).toHaveLength(2);
      const id1 = patterns[0].attributes("id");
      const id2 = patterns[1].attributes("id");
      expect(id1).toBeDefined();
      expect(id2).toBeDefined();
      expect(id1).not.toBe(id2);

      const fogs = w.findAll("defs radialGradient");
      expect(fogs).toHaveLength(2);
      const fog1 = fogs[0].attributes("id");
      const fog2 = fogs[1].attributes("id");
      expect(fog1).toBeDefined();
      expect(fog2).toBeDefined();
      expect(fog1).not.toBe(fog2);
    });
  });

  describe("Wave 2: Derived Pitch and Proportions", () => {
    it("Task 2.1: labelFont drives font size and baseline derivation", () => {
      const wIsland = mountLattice({
        localMap: localMapModelFor(LOCAL_MAP_SAMPLE),
        ...ISLAND_PROPS,
      });
      const islandLabel = wIsland.get(".local-map__node-label");
      expect(islandLabel.attributes("style")).toContain("font-size: 9px");
      expect(islandLabel.attributes("y")).toBe("22");

      const wOverlay = mountLattice({
        localMap: localMapModelFor(LOCAL_MAP_SAMPLE),
        colPitch: 280,
        rowPitch: 212,
        markerScale: 4.83,
        labelFont: 11,
        labelMax: 10,
      });
      const overlayLabel = wOverlay.get(".local-map__node-label");
      expect(overlayLabel.attributes("style")).toContain("font-size: 11px");
      expect(Number(overlayLabel.attributes("y"))).toBeCloseTo(13 * 4.83 + 13, 2);
    });

    it("Task 2.2: derives square pitch 40 on uniform wilderness (repetition suppressed) and 48 on adjacent labelled pair", () => {
      const uniformWildernessPayload = {
        schema_version: 1,
        available: true,
        layer: "wilderness",
        title: "西部丘陵",
        current_node: "w:1:1",
        nodes: [
          { id: "w:0:0", label: "西部丘陵", x: 0, y: 0, visibility: "visible_visited" },
          { id: "w:1:0", label: "西部丘陵", x: 1, y: 0, visibility: "visible_visited" },
          { id: "w:0:1", label: "西部丘陵", x: 0, y: 1, visibility: "visible_visited" },
          { id: "w:1:1", label: "西部丘陵", x: 1, y: 1, visibility: "current" },
        ],
        edges: [],
      };
      const wUniform = mountLattice({
        localMap: localMapModelFor(uniformWildernessPayload),
        colPitch: 40,
        rowPitch: 40,
        labelFont: 9,
      });
      const visibleLabels = wUniform.findAll(".local-map__node-label").filter((l) => (l.element.lastChild?.textContent || "").trim() !== "");
      expect(visibleLabels).toHaveLength(1);
      const patternUniform = wUniform.find("defs pattern");
      expect(Number(patternUniform.attributes("width"))).toBe(40);
      expect(Number(patternUniform.attributes("height"))).toBe(40);

      const distinctAdjacentPayload = {
        schema_version: 1,
        available: true,
        layer: "grid",
        title: "市街區",
        current_node: "g:0:0",
        nodes: [
          { id: "g:0:0", label: "中央大街", x: 0, y: 0, visibility: "current" },
          { id: "g:1:0", label: "東側巷道", x: 1, y: 0, visibility: "visible_unvisited" },
        ],
        edges: [],
      };
      const wDistinct = mountLattice({
        localMap: localMapModelFor(distinctAdjacentPayload),
        colPitch: 40,
        rowPitch: 40,
        labelFont: 9,
      });
      const patternDistinct = wDistinct.find("defs pattern");
      expect(Number(patternDistinct.attributes("width"))).toBe(48);
      expect(Number(patternDistinct.attributes("height"))).toBe(48);

      const wOverlayDistinct = mountLattice({
        localMap: localMapModelFor(distinctAdjacentPayload),
        colPitch: 280,
        rowPitch: 212,
        labelFont: 11,
        labelMax: 10,
      });
      const patternOverlay = wOverlayDistinct.find("defs pattern");
      expect(Number(patternOverlay.attributes("width"))).toBe(280);
      expect(Number(patternOverlay.attributes("height"))).toBe(212);
    });

    it("Task 2.3: verifies all 6 rows of Design D5 Table and scale <= 1 invariant", () => {
      // Row 1: 3x3, remembered present (UNIFORM_WILDERNESS_PAYLOAD)
      const wRow1 = mountLattice({
        localMap: localMapModelFor(UNIFORM_WILDERNESS_PAYLOAD),
        ...ISLAND_PROPS,
      });
      const svg1 = wRow1.get("svg.local-map__lattice");
      expect(Number(svg1.attributes("width"))).toBeCloseTo(208.91, 1);
      expect(Number(svg1.attributes("height"))).toBeCloseTo(222.91, 1);
      const style1 = svg1.attributes("style");
      expect(style1).toContain("max-width: 206px");
      const scale1 = 206 / 208.911688;
      expect(scale1).toBeLessThanOrEqual(1.0);
      expect(scale1).toBeCloseTo(0.986, 3);
      expect(scale1 * 9).toBeCloseTo(8.87, 2);

      // Row 2: 3x3, no remembered
      const row2Payload = {
        ...UNIFORM_WILDERNESS_PAYLOAD,
        nodes: UNIFORM_WILDERNESS_PAYLOAD.nodes.filter((n) => n.visibility !== "remembered"),
      };
      const wRow2 = mountLattice({
        localMap: localMapModelFor(row2Payload),
        ...ISLAND_PROPS,
      });
      const svg2 = wRow2.get("svg.local-map__lattice");
      expect(Number(svg2.attributes("width"))).toBe(206);
      expect(Number(svg2.attributes("height"))).toBe(220);
      const style2 = svg2.attributes("style");
      expect(style2).toContain("max-width: 206px");
      expect(206 / 206).toBeLessThanOrEqual(1.0);

      // Row 3: 1 node, no remembered
      const wRow3 = mountLattice({
        localMap: localMapModelFor(LOCAL_MAP_SINGLE_NODE_SAMPLE),
        ...ISLAND_PROPS,
      });
      const svg3 = wRow3.get("svg.local-map__lattice");
      expect(Number(svg3.attributes("width"))).toBe(206);
      expect(Number(svg3.attributes("height"))).toBe(220);
      const style3 = svg3.attributes("style");
      expect(style3).toContain("max-width: 206px");

      // Row 4: 1 node, remembered present
      const row4Payload = {
        schema_version: 1,
        available: true,
        layer: "wilderness",
        title: "孤單節點",
        current_node: "w:0:0",
        nodes: [{ id: "w:0:0", label: "起點", x: 0, y: 0, visibility: "current" }],
        remembered: [{ id: "r:rem", label: "遠方城池", x: 10, y: 10, visibility: "remembered" }],
        edges: [],
      };
      const wRow4 = mountLattice({
        localMap: localMapModelFor(row4Payload),
        ...ISLAND_PROPS,
      });
      const svg4 = wRow4.get("svg.local-map__lattice");
      expect(Number(svg4.attributes("width"))).toBeCloseTo(206, 1);
      expect(Number(svg4.attributes("height"))).toBeCloseTo(220, 1);
      const style4 = svg4.attributes("style");
      expect(style4).toContain("max-width: 206px");

      // Row 5: adjacent labelled pair (pitch 48, cols 3, rows 3, remembered present)
      const row5Payload = {
        schema_version: 1,
        available: true,
        layer: "grid",
        title: "繁華市區",
        current_node: "g:1:1",
        nodes: [
          { id: "g:0:0", label: "西巷", x: 0, y: 0, visibility: "visible_visited" },
          { id: "g:1:0", label: "東巷", x: 1, y: 0, visibility: "visible_visited" },
          { id: "g:2:0", label: "南路", x: 2, y: 0, visibility: "visible_visited" },
          { id: "g:0:1", label: "北路", x: 0, y: 1, visibility: "visible_visited" },
          { id: "g:1:1", label: "廣場", x: 1, y: 1, visibility: "current" },
          { id: "g:2:1", label: "市集", x: 2, y: 1, visibility: "visible_visited" },
          { id: "g:0:2", label: "橋頭", x: 0, y: 2, visibility: "visible_visited" },
          { id: "g:1:2", label: "碼頭", x: 1, y: 2, visibility: "visible_visited" },
          { id: "g:2:2", label: "城門", x: 2, y: 2, visibility: "visible_visited" },
          { id: "r:gate", label: "關口", x: 15, y: 15, visibility: "remembered", landmark: true },
        ],
        edges: [],
      };
      const wRow5 = mountLattice({
        localMap: localMapModelFor(row5Payload),
        ...ISLAND_PROPS,
      });
      const svg5 = wRow5.get("svg.local-map__lattice");
      expect(Number(svg5.attributes("width"))).toBeCloseTo(232.91, 1);
      expect(Number(svg5.attributes("height"))).toBeCloseTo(246.91, 1);
      const scale5 = 206 / 232.911688;
      expect(scale5).toBeCloseTo(0.885, 2);
      expect(scale5 * 9).toBeCloseTo(7.96, 2);

      // Row 6: 2x64 tall lattice
      const wRow6 = mountLattice({
        localMap: localMapModelFor(LOCAL_MAP_TALL_LATTICE_SAMPLE),
        ...ISLAND_PROPS,
      });
      const svg6 = wRow6.get("svg.local-map__lattice");
      expect(Number(svg6.attributes("width"))).toBe(206);
      expect(Number(svg6.attributes("height"))).toBe(2574);
      const style6 = svg6.attributes("style");
      expect(style6).toContain("max-width: 23.68px");
      const scale6 = 23.68 / 206;
      expect(scale6).toBeCloseTo(0.115, 3);
      expect(scale6 * 9).toBeCloseTo(1.04, 1);
    });

    it("Task 2.4: deletes maxUpscale prop and bounds scale <= 1 on all fixtures", () => {
      const w = mountLattice({
        localMap: localMapModelFor(LOCAL_MAP_SINGLE_NODE_SAMPLE),
        colPitch: 40,
        rowPitch: 40,
        fieldFill: true,
        maxWidth: 206,
        maxHeight: 296,
      });
      expect(w.props("maxUpscale")).toBeUndefined();
      const style = w.get("svg.local-map__lattice").attributes("style");
      expect(style).toContain("max-width: 206px");
      expect(style).not.toContain("116px");
    });

    it("Task 2.6: overlay geometry is identical to pre-change baseline and gains dot field", () => {
      const wOverlay = mountLattice({
        localMap: localMapModelFor(LOCAL_MAP_SAMPLE),
        colPitch: 280,
        rowPitch: 212,
        markerScale: 4.83,
        labelMax: 10,
        labelFont: 11,
        markerNameFont: 11,
        maxWidth: 848,
        fillWidth: true,
        overlayChrome: true,
        markerNames: true,
      });
      const expectedGutter = 2 * Math.SQRT2 * (9 * 4.83) + 1 + (11 * 11 + 2);
      expect(Number(wOverlay.get("svg.local-map__lattice").attributes("width"))).toBeCloseTo(
        3 * 280 + 2 * expectedGutter,
        4,
      );
      expect(Number(wOverlay.get("svg.local-map__lattice").attributes("height"))).toBeCloseTo(
        1 * 212 + 14 + 2 * expectedGutter,
        4,
      );
      expect(wOverlay.find('[data-testid="local-map__dot-field"]').exists()).toBe(true);
      expect(wOverlay.find('[data-testid="local-map__vignette"]').exists()).toBe(false);
      expect(wOverlay.find('[data-testid="local-map__axis"]').exists()).toBe(false);
    });
  });
});
