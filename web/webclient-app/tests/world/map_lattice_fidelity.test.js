import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import MapLattice from "../../components/MapLattice.vue";
import { CELL_EM } from "../../lib/mono_cells.js";
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
    labelFont: 16,
    canvasSize: 240,
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
      // The reported wilderness shape's 240px square grows the drawn pitch to
      // 45 (its gutter reserves 44.456 units a side), and the dot field is
      // registered to that drawn pitch, not to the declared 40 units.
      expect(pitchW).toBeGreaterThanOrEqual(47);
      expect(pitchH).toBe(pitchW);

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
      const vb = svg.attributes("viewBox").split(" ").map(Number);
      const canvasW = vb[2];
      const canvasH = vb[3];

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
      expect(islandLabel.attributes("style")).toContain("font-size: 16px");
      expect(islandLabel.attributes("y")).toBe("29");

      const wOverlay = mountLattice({
        localMap: localMapModelFor(LOCAL_MAP_SAMPLE),
        colPitch: 280,
        rowPitch: 212,
        markerScale: 4.83,
        labelFont: 16,
        labelMax: 10,
      });
      const overlayLabel = wOverlay.get(".local-map__node-label");
      expect(overlayLabel.attributes("style")).toContain("font-size: 16px");
      expect(Number(overlayLabel.attributes("y"))).toBeCloseTo(11 * 4.83 + 2 + 16, 2);
    });

    it("Task 2.2: derives square pitch 40 on uniform wilderness (repetition suppressed) and clears the drawn adjacent labels", () => {
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
        labelFont: 16,
      });
      const visibleLabels = wUniform.findAll(".local-map__node-label").filter((l) => (l.element.lastChild?.textContent || "").trim() !== "");
      expect(visibleLabels).toHaveLength(1);
      const patternUniform = wUniform.find("defs pattern");
      expect(Number(patternUniform.attributes("width"))).toBeGreaterThanOrEqual(47);
      expect(patternUniform.attributes("height")).toBe(patternUniform.attributes("width"));

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
        labelFont: 16,
      });
      // webclient-map-legibility: the label term clears the labels actually
      // drawn, measured in monospace cells — two 4-glyph CJK names (8 cells
      // each) need ceil(((8 + 8) / 2 × CELL_EM + 0.5) × 16) = 83.
      const patternDistinct = wDistinct.find("defs pattern");
      expect(Number(patternDistinct.attributes("width"))).toBe(83);
      expect(Number(patternDistinct.attributes("height"))).toBe(83);

      // A short name beside a long one needs less:
      // ceil(((4 + 8) / 2 × CELL_EM + 0.5) × 16) = 65.
      const shortLong = {
        ...distinctAdjacentPayload,
        nodes: [
          { id: "g:0:0", label: "碼頭", x: 0, y: 0, visibility: "current" },
          { id: "g:1:0", label: "霧骨渡口", x: 1, y: 0, visibility: "visible_unvisited" },
        ],
      };
      const wShortLong = mountLattice({ localMap: localMapModelFor(shortLong), colPitch: 40, rowPitch: 40, labelFont: 16 });
      expect(Number(wShortLong.find("defs pattern").attributes("width"))).toBe(65);

      // Two truncated names (labelMax 4 wide glyphs + the narrow "…" = 9
      // cells) are the worst case, never looser than the old
      // (labelMax + 1) * labelFont + 3 = 83: ceil((9 × CELL_EM + 0.5) × 16) = 93.
      const longLong = {
        ...distinctAdjacentPayload,
        nodes: [
          { id: "g:0:0", label: "北岸大道東段", x: 0, y: 0, visibility: "current" },
          { id: "g:1:0", label: "南岸大道西段", x: 1, y: 0, visibility: "visible_unvisited" },
        ],
      };
      const wLongLong = mountLattice({ localMap: localMapModelFor(longLong), colPitch: 40, rowPitch: 40, labelFont: 16 });
      expect(Number(wLongLong.find("defs pattern").attributes("width"))).toBe(93);
      expect(93).toBeGreaterThanOrEqual((4 + 1) * 16 + 3);

      const wOverlayDistinct = mountLattice({
        localMap: localMapModelFor(distinctAdjacentPayload),
        colPitch: 280,
        rowPitch: 212,
        labelFont: 16,
        labelMax: 10,
      });
      const patternOverlay = wOverlayDistinct.find("defs pattern");
      expect(Number(patternOverlay.attributes("width"))).toBe(280);
      expect(Number(patternOverlay.attributes("height"))).toBe(212);
    });

    it("Task 2.3: verifies all 6 rows of Design D5 Table and scale <= 1 invariant", () => {
      // 1. 3x3 core with no gateways: pitch 60 (the 1.5x cap) and scale 1
      const noGatewaysPayload = {
        ...UNIFORM_WILDERNESS_PAYLOAD,
        nodes: UNIFORM_WILDERNESS_PAYLOAD.nodes.filter((n) => n.visibility !== "remembered"),
      };
      const wNoGateways = mountLattice({
        localMap: localMapModelFor(noGatewaysPayload),
        ...ISLAND_PROPS,
      });
      const svg1 = wNoGateways.get("svg.local-map__lattice");
      expect(Number(svg1.attributes("width"))).toBe(240);
      expect(Number(svg1.attributes("height"))).toBe(240);
      expect(svg1.attributes("viewBox")).toBe("0 0 240 240");
      expect(svg1.attributes("style")).toContain("width: calc(240px * var(--ui-scale, 1))");
      expect(svg1.attributes("style")).toContain("height: calc(240px * var(--ui-scale, 1))");
      const pattern1 = wNoGateways.find("defs pattern");
      expect(Number(pattern1.attributes("width"))).toBe(60);
      expect(Number(pattern1.attributes("height"))).toBe(60);

      // 2. Single node: pitch 60 (1.5x cap) and scale 1
      const wSingle = mountLattice({
        localMap: localMapModelFor(LOCAL_MAP_SINGLE_NODE_SAMPLE),
        ...ISLAND_PROPS,
      });
      const svg2 = wSingle.get("svg.local-map__lattice");
      expect(Number(svg2.attributes("width"))).toBe(240);
      expect(Number(svg2.attributes("height"))).toBe(240);
      expect(svg2.attributes("viewBox")).toBe("0 0 240 240");
      expect(svg2.attributes("style")).toContain("width: calc(240px * var(--ui-scale, 1))");
      expect(svg2.attributes("style")).toContain("height: calc(240px * var(--ui-scale, 1))");
      const pattern2 = wSingle.find("defs pattern");
      expect(Number(pattern2.attributes("width"))).toBe(60);
      expect(Number(pattern2.attributes("height"))).toBe(60);

      // 3. Reported wilderness shape with gateways: the 240px square's roomier
      // inset box grows the pitch to 45 (the gutter reserves 44.456 units a
      // side), so the drawing needs 237.91 units, fits the 240px square at
      // scale 1, and every drawn node label reads at exactly 16.00 CSS px.
      const wWild = mountLattice({
        localMap: localMapModelFor(UNIFORM_WILDERNESS_PAYLOAD),
        ...ISLAND_PROPS,
      });
      const svg3 = wWild.get("svg.local-map__lattice");
      expect(Number(svg3.attributes("width"))).toBe(240);
      expect(Number(svg3.attributes("height"))).toBe(240);
      const pattern3 = wWild.find("defs pattern");
      expect(Number(pattern3.attributes("width"))).toBeGreaterThanOrEqual(47);
      expect(pattern3.attributes("height")).toBe(pattern3.attributes("width"));
      const vbParts = svg3.attributes("viewBox").split(" ").map(Number);
      expect(vbParts[2]).toBeCloseTo(240, 1);
      expect(vbParts[3]).toBeCloseTo(240, 1);
      const scale3 = 240 / vbParts[2];
      expect(scale3).toBeCloseTo(1, 3);
      expect(scale3 * 16).toBeCloseTo(16, 1);
      expect(scale3 * 16).toBeGreaterThanOrEqual(16);

      // 4. 2x64 lattice: the 2574-unit square would draw at 0.0808, below
      // the island's legibility floor, so it is windowed at scale 1
      // around the current node instead (design §11).
      const wTall = mountLattice({
        localMap: localMapModelFor(LOCAL_MAP_TALL_LATTICE_SAMPLE),
        ...ISLAND_PROPS,
      });
      const svg4 = wTall.get("svg.local-map__lattice");
      expect(Number(svg4.attributes("width"))).toBe(240);
      expect(Number(svg4.attributes("height"))).toBe(240);
      const vbTall = svg4.attributes("viewBox").split(" ").map(Number);
      expect(vbTall[2]).toBeCloseTo(240, 6);
      expect(vbTall[3]).toBeCloseTo(240, 6);
      const scale4 = 240 / vbTall[2];
      expect(scale4).toBeCloseTo(1, 6);

      // 5. Graph cases:
      // a. One-ring interior: a 260-unit radial canvas (R0 80 + label bottom 26
      // + padding 24 per side), cropped to its footprint plus the 8px inset:
      // the 228-unit footprint fits the 240px square at scale 1
      const wInterior = mountLattice({
        localMap: localMapModelFor(LOCAL_MAP_INTERIOR_SAMPLE),
        variant: "graph",
        ...ISLAND_PROPS,
      });
      const svg5 = wInterior.get("svg.local-map__lattice");
      expect(Number(svg5.attributes("width"))).toBe(240);
      expect(Number(svg5.attributes("height"))).toBe(240);
      const vb5 = svg5.attributes("viewBox").split(" ").map(Number);
      expect(vb5[0]).toBe(10);
      expect(vb5[1]).toBe(10);
      expect(vb5[2]).toBe(240);
      expect(vb5[3]).toBe(240);
      const scale5 = 240 / 240;
      expect(scale5).toBe(1);

      // b. Current-only interior: side 240 with scale 1 and current node at centre
      const singleInteriorPayload = {
        schema_version: 1,
        available: true,
        layer: "interior",
        title: "公會密室",
        current_node: "room:current",
        nodes: [
          { id: "room:current", label: "密室", x: 0, y: 0, visibility: "current" },
        ],
        edges: [],
      };
      const wSingleInterior = mountLattice({
        localMap: localMapModelFor(singleInteriorPayload),
        variant: "graph",
        ...ISLAND_PROPS,
      });
      const svg6 = wSingleInterior.get("svg.local-map__lattice");
      expect(Number(svg6.attributes("width"))).toBe(240);
      expect(Number(svg6.attributes("height"))).toBe(240);
      const vb6 = svg6.attributes("viewBox").split(" ").map(Number);
      expect(vb6[0]).toBe(-70);
      expect(vb6[1]).toBe(-70);
      expect(vb6[2]).toBe(240);
      expect(vb6[3]).toBe(240);
      const scale6 = 240 / 240;
      expect(scale6).toBe(1.0);
      const currentNodeEl = wSingleInterior.get('[data-testid="local-map__node--room:current"]');
      expect(currentNodeEl.attributes("transform")).toBe("translate(50, 50)");
      expect(vb6[0] + vb6[2] / 2).toBe(50);
      expect(vb6[1] + vb6[3] / 2).toBe(50);
    });

    it("Task 2.4: deletes maxUpscale and fieldFill props, bounds scale <= 1 on all fixtures", () => {
      const w = mountLattice({
        localMap: localMapModelFor(LOCAL_MAP_SINGLE_NODE_SAMPLE),
        colPitch: 40,
        rowPitch: 40,
      });
      expect(w.props("maxUpscale")).toBeUndefined();
      expect(w.props("fieldFill")).toBeUndefined();
      // webclient-full-map-fit-view D6: a bare mount declares neither the
      // island's square canvas nor the overlay's fitted view, so it draws
      // at the canvas's natural size — no inline size and no max-width.
      const style = w.get("svg.local-map__lattice").attributes("style");
      expect(style).toBeUndefined();
    });

    it("Task 2.6: overlay geometry is identical to pre-change baseline and gains dot field", () => {
      const wOverlay = mountLattice({
        localMap: localMapModelFor(LOCAL_MAP_SAMPLE),
        colPitch: 280,
        rowPitch: 212,
        markerScale: 4.83,
        labelMax: 10,
        labelFont: 16,
        markerNameFont: 16,
        overlayChrome: true,
        markerNames: true,
      });
      // namePad: the outward box of (10 + 1) × 2 monospace cells at the
      // overlay's 16-unit marker-name step, plus 2.
      const expectedGutter = 2 * Math.SQRT2 * (9 * 4.83) + 1 + (22 * CELL_EM * 16 + 2);
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

    it("retarget: the island draws its node labels and marker names at the 16px floor", () => {
      // webclient-local-map "Map chrome and ordinary node labels are legible
      // without dropping topology" (amended by
      // retarget-desktop-viewport-contract D7): on the reported wilderness
      // shape with its named edge markers the island's drawing resolves to
      // scale 1, so every drawn node label and every drawn marker name renders
      // at its declared 16-unit step — exactly 16 CSS px at the 1451x790
      // reference viewport.
      const w = mountLattice({
        localMap: localMapModelFor(UNIFORM_WILDERNESS_PAYLOAD),
        ...ISLAND_PROPS,
      });
      const svg = w.get("svg.local-map__lattice");
      // The canvas renders at its reference 240 CSS px; the viewBox side is the
      // drawing's own square, so the ratio is the uniform scale.
      const canvas = Number(svg.attributes("width"));
      expect(canvas).toBe(240);
      const scale = canvas / Number(svg.attributes("viewBox").split(" ")[2]);
      expect(scale).toBe(1);

      const stepOf = (el) => Number(el.attributes("style").match(/font-size:\s*([\d.]+)px/)[1]);
      const labels = w.findAll(".local-map__node-label");
      expect(labels.length).toBeGreaterThan(0);
      for (const label of labels) {
        expect(stepOf(label)).toBe(16);
        expect(stepOf(label) * scale).toBeGreaterThanOrEqual(16);
      }
      const names = w.findAll(".local-map__edge-marker-name--island");
      expect(names.length).toBeGreaterThan(0);
      for (const name of names) {
        expect(stepOf(name)).toBe(16);
        expect(stepOf(name) * scale).toBeGreaterThanOrEqual(16);
      }
    });
  });
});
