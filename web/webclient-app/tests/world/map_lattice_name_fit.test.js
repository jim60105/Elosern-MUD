import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import MapLattice from "../../components/MapLattice.vue";
import { localMapModelFor } from "../../stories/fixtures.js";
import { CELL_EM } from "../../lib/mono_cells.js";
import { REPORTED_WILDERNESS_PAYLOAD } from "./map_lattice_support.js";

describe("The Overlay's Marker Names Obey the Geometry That Reserves Them (webclient-minimap-07-overlay-marker-name-fit)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
  });

  const OVERLAY_CONFIG = {
    colPitch: 280,
    rowPitch: 212,
    labelMax: 10,
    markerScale: 4.83,
    overlayChrome: true,
    markerNames: true,
    labelFont: 16,
    markerNameFont: 16,
  };

  it("Task 1.1: pins pre-change overlay baseline for names within capacity", () => {
    wrapper = mount(MapLattice, {
      props: {
        localMap: localMapModelFor(REPORTED_WILDERNESS_PAYLOAD),
        ...OVERLAY_CONFIG,
      },
    });
    const svg = wrapper.get("svg.local-map__lattice");
    const svgWidth = Number(svg.attributes("width"));
    const svgHeight = Number(svg.attributes("height"));
    const viewBox = svg.attributes("viewBox");

    // Core lattice: 3 cols × 280 = 840; 3 rows × 212 = 636 + 14 = 650.
    // Model gutterMin for overlay: 2 * reach + 1 + namePad, where namePad is
    // the outward name box, (labelMax + 1) × 2 = 22 monospace cells at 16,
    // plus 2.
    const expectedOverlayGutter = 2 * Math.SQRT2 * (9 * 4.83) + 1 + 22 * CELL_EM * 16 + 2;
    // Pinned literal, so a drift in the cell measure itself is caught here too.
    expect(22 * CELL_EM * 16).toBeCloseTo(206.25, 3);
    expect(svgWidth).toBeCloseTo(840 + 2 * expectedOverlayGutter, 5);
    expect(svgHeight).toBeCloseTo(650 + 2 * expectedOverlayGutter, 5);
    expect(viewBox).toBe(`0 0 ${svgWidth} ${svgHeight}`);

    const westMarker = wrapper.get('[data-testid="local-map__edge-marker--r:west"]');
    const westText = westMarker.get("text.local-map__edge-marker-name");
    expect(westText.text()).toBe("西部丘陵與谷地（南門）");
    const expectedOutset = Math.SQRT2 * (9 * 4.83) + 2;
    expect(Number(westText.attributes("x"))).toBeCloseTo(-expectedOutset, 3);
    expect(Number(westText.attributes("y"))).toBe(4);
    expect(westText.attributes("text-anchor")).toBe("end");

    const eastMarker = wrapper.get('[data-testid="local-map__edge-marker--r:east"]');
    const eastText = eastMarker.get("text.local-map__edge-marker-name");
    expect(eastText.text()).toBe("聖潔王都");
    expect(Number(eastText.attributes("x"))).toBeCloseTo(expectedOutset, 3);
    expect(Number(eastText.attributes("y"))).toBe(4);
    expect(eastText.attributes("text-anchor")).toBe("start");
  });

  it("Task 1.2: pins pre-change island baseline for drawn names, stacked tspans, and gutter", () => {
    wrapper = mount(MapLattice, {
      props: {
        localMap: localMapModelFor(REPORTED_WILDERNESS_PAYLOAD),
        colPitch: 40,
        rowPitch: 40,
        labelMax: 4,
        markerScale: 1,
        canvasSize: 240,
        overlayChrome: false,
        markerNames: true,
      },
    });
    const svg = wrapper.get("svg.local-map__lattice");
    const svgWidth = Number(svg.attributes("width"));
    const svgHeight = Number(svg.attributes("height"));

    // Core lattice: the label term clears the drawn 3-glyph labels ("0,0") —
    // ((3 + 3) / 2 × CELL_EM + 0.5) × 16 = 37 < 40 — so the declared 40-unit
    // pitch is the floor and the 240px square's roomier inset box grows the
    // drawn pitch to 45.
    // Gutter for the island with nameHeight 16 -> namePad 18 -> gutter:
    // 2 * sqrt(2) * 9 + 1 + 18 ≈ 44.4558, so the drawn field is
    // 240 − 2 × 44.4558 = 151.088 units a side.
    const expectedGutter = 2 * Math.SQRT2 * 9 + 1 + 18;
    expect(svgWidth).toBe(240);
    expect(svgHeight).toBe(240);
    const vb = svg.attributes("viewBox").split(" ").map(Number);
    expect(vb[2]).toBeCloseTo(240, 5);
    expect(vb[3]).toBeCloseTo(240, 5);
    const westSpan = wrapper.vm.fittedEdgeMarkers.find((m) => m.id === "r:west").span;
    expect(westSpan).toBeCloseTo(240 - 2 * expectedGutter, 5);

    const westMarker = wrapper.get('[data-testid="local-map__edge-marker--r:west"]');
    const westText = westMarker.get("text.local-map__edge-marker-name--island");
    // Span on the left edge: 151.088. The island stacks left names one glyph
    // per line, so budget = floor(151.088 / 16) = 9 steps; the kept （南門）
    // qualifier (4 steps) plus "…" leaves 4 steps of head: 西部丘陵.
    expect(westText.text()).toBe("西部丘陵…（南門）");
    const tspans = westText.findAll("tspan");
    expect(tspans).toHaveLength(9);
    const reach = Math.SQRT2 * 9;
    const expectedX = -(reach + 9);
    tspans.forEach((tspan, i) => {
      expect(Number(tspan.attributes("x"))).toBeCloseTo(expectedX, 3);
      expect(tspan.attributes("dy")).toBe(i === 0 ? "0" : "16");
    });

    const eastMarker = wrapper.get('[data-testid="local-map__edge-marker--r:east"]');
    const eastText = eastMarker.get("text.local-map__edge-marker-name--island");
    expect(eastText.text()).toBe("聖潔王都");
    const eastTspans = eastText.findAll("tspan");
    expect(eastTspans).toHaveLength(4);
  });

  it("Task 3.2: binds markerNameFont inline on overlay marker name and rule declares no font-size", () => {
    wrapper = mount(MapLattice, {
      props: {
        localMap: localMapModelFor(REPORTED_WILDERNESS_PAYLOAD),
        ...OVERLAY_CONFIG,
      },
    });
    const westMarker = wrapper.get('[data-testid="local-map__edge-marker--r:west"]');
    const textEl = westMarker.get("text.local-map__edge-marker-name");
    expect(textEl.attributes("style")).toContain("font-size: 16px");

    let checkedRule = false;
    for (const sheet of document.styleSheets) {
      try {
        for (const rule of sheet.cssRules) {
          if (rule.selectorText && rule.selectorText.includes(".local-map__edge-marker-name") && !rule.selectorText.includes("--island")) {
            checkedRule = true;
            expect(rule.style.fontSize).toBe("");
          }
        }
      } catch {
        // ignore
      }
    }
    expect(checkedRule).toBe(true);
  });

  it("Task 4.1: outwardBox derives from markerNameFont and moves reserved gutter", () => {
    const wOverlay = mount(MapLattice, {
      props: {
        localMap: localMapModelFor(REPORTED_WILDERNESS_PAYLOAD),
        ...OVERLAY_CONFIG,
      },
    });
    // The overlay's markerNameFont is 16, labelMax is 10: the outward box is
    // (10 + 1) × 2 = 22 monospace cells, 22 × CELL_EM × 16 = 206.25 units.
    const svg16 = wOverlay.get("svg.local-map__lattice");
    const width16 = Number(svg16.attributes("width"));

    // Re-render with markerNameFont = 20 (a step above the floor): the box
    // grows by 22 × CELL_EM × 4 = 51.5625 units, so namePad and each gutter
    // grow by that and svgWidth by twice it.
    const wOverlay20 = mount(MapLattice, {
      props: {
        localMap: localMapModelFor(REPORTED_WILDERNESS_PAYLOAD),
        ...OVERLAY_CONFIG,
        markerNameFont: 20,
      },
    });
    const svg20 = wOverlay20.get("svg.local-map__lattice");
    const width20 = Number(svg20.attributes("width"));
    expect(width20 - width16).toBeCloseTo(2 * 22 * CELL_EM * 4, 5);
  });

  it("Task 4.3: fits 14-glyph label to 11 on lone overlay left and draws whole on lone overlay top", () => {
    // 14-glyph label on lone overlay left marker:
    // span is 650, but the outward box binds: budget = min(floor(650 / (CELL_EM × 11)), 22) = 22 cells.
    const leftPayload = {
      schema_version: 1,
      available: true,
      layer: "wilderness",
      title: "西部荒野",
      current_node: "w:1:1",
      nodes: [
        ...REPORTED_WILDERNESS_PAYLOAD.nodes.slice(0, 9),
        { id: "r:west_long", label: "灰鬮荒原第一南關隘道前哨站營", x: -10, y: 1, visibility: "remembered", landmark: true },
      ],
    };
    const wLeft = mount(MapLattice, {
      props: {
        localMap: localMapModelFor(leftPayload),
        ...OVERLAY_CONFIG,
      },
    });
    const leftMarker = wLeft.get('[data-testid="local-map__edge-marker--r:west_long"]');
    const leftText = leftMarker.get("text.local-map__edge-marker-name");
    // 14 wide glyphs fitted to 22 cells: head '灰' (2) + '…' (1) + tail 9 wide
    // glyphs ('一南關隘道前哨站營', 18) = 21; one more wide glyph would not fit.
    expect(leftText.text()).toBe("灰…一南關隘道前哨站營");
    expect(Array.from(leftText.text())).toHaveLength(11);

    // 14-glyph label on lone overlay top marker:
    // span is 840. Not drawsOutward (top edge draws along): budget = floor(840 / (CELL_EM × 11)) = 126 cells.
    // Label fits whole!
    const topPayload = {
      schema_version: 1,
      available: true,
      layer: "wilderness",
      title: "西部荒野",
      current_node: "w:1:1",
      nodes: [
        ...REPORTED_WILDERNESS_PAYLOAD.nodes.slice(0, 9),
        { id: "r:top_long", label: "灰鬮荒原第一南關隘道前哨站營", x: 1, y: 10, visibility: "remembered", landmark: true },
      ],
    };
    const wTop = mount(MapLattice, {
      props: {
        localMap: localMapModelFor(topPayload),
        ...OVERLAY_CONFIG,
      },
    });
    const topMarker = wTop.get('[data-testid="local-map__edge-marker--r:top_long"]');
    const topText = topMarker.get("text.local-map__edge-marker-name");
    expect(topText.text()).toBe("灰鬮荒原第一南關隘道前哨站營");

    // The island's own declared step (16 units) truncates the same long label
    // harder than the overlay's outward_name capacity does.
    const wIslandLeft = mount(MapLattice, {
      props: {
        localMap: localMapModelFor(leftPayload),
        colPitch: 40,
        rowPitch: 40,
        labelMax: 4,
        markerScale: 1,
        canvasSize: 240,
        overlayChrome: false,
        markerNames: true,
      },
    });
    const islandLeftText = wIslandLeft.get('[data-testid="local-map__edge-marker--r:west_long"] text');
    // Span 151.088, budget 9 steps: the 14-glyph name keeps its head and tail
    expect(islandLeftText.text()).toBe("灰…關隘道前哨站營");
    expect(Array.from(islandLeftText.text())).toHaveLength(9);
  });

  it("Task 4.4: anti-ambiguity pass covers overlay when differing 14-glyph labels collide on budget 11", () => {
    // Two overlay left markers whose 14-glyph labels differ only in the middle (indices 1..4):
    // Head 1: '灰', Tail 9: '遠方神秘未知隘道營'
    // label 1: '灰' + '南關驛站' + '遠方神秘未知隘道營'
    // label 2: '灰' + '北關驛站' + '遠方神秘未知隘道營'
    // Both truncate to '灰…遠方神秘未知隘道營' (11 glyphs).
    // Anti-ambiguity rule MUST omit both visible names, preserving diamonds and accessible aria-labels.
    const l1 = "灰南關驛站遠方神秘未知隘道營";
    const l2 = "灰北關驛站遠方神秘未知隘道營";
    const collidingPayload = {
      schema_version: 1,
      available: true,
      layer: "wilderness",
      title: "西部荒野",
      current_node: "w:1:1",
      nodes: [
        ...REPORTED_WILDERNESS_PAYLOAD.nodes.slice(0, 9),
        { id: "r:coll_1", label: l1, x: -10, y: 0, visibility: "remembered", landmark: true },
        { id: "r:coll_2", label: l2, x: -10, y: 2, visibility: "remembered", landmark: true },
      ],
    };
    const w = mount(MapLattice, {
      props: {
        localMap: localMapModelFor(collidingPayload),
        ...OVERLAY_CONFIG,
      },
    });
    const m1 = w.get('[data-testid="local-map__edge-marker--r:coll_1"]');
    const m2 = w.get('[data-testid="local-map__edge-marker--r:coll_2"]');

    // Diamonds, landmark rings, aria-label and titles exist
    expect(m1.find(".local-map__edge-marker-diamond").exists()).toBe(true);
    expect(m1.find(".local-map__edge-marker-landmark").exists()).toBe(true);
    expect(m1.attributes("aria-label")).toBe(l1);
    expect(m1.find("title").text()).toBe(l1);

    expect(m2.find(".local-map__edge-marker-diamond").exists()).toBe(true);
    expect(m2.find(".local-map__edge-marker-landmark").exists()).toBe(true);
    expect(m2.attributes("aria-label")).toBe(l2);
    expect(m2.find("title").text()).toBe(l2);

    // Neither draws a visible name
    expect(m1.find("text").exists()).toBe(false);
    expect(m2.find("text").exists()).toBe(false);
  });

  it("Task 4.5: design D5 monotonicity: overlay per-marker budget > island on edges where island truncates", () => {
    // Crowded edge payload: 3 markers on top edge, 2 markers on left edge
    const crowdedPayload = {
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
      ],
    };
    const wIsland = mount(MapLattice, {
      props: {
        localMap: localMapModelFor(crowdedPayload),
        colPitch: 40,
        rowPitch: 40,
        labelMax: 4,
        markerScale: 1,
        overlayChrome: false,
        markerNames: true,
      },
    });
    const wOverlay = mount(MapLattice, {
      props: {
        localMap: localMapModelFor(crowdedPayload),
        ...OVERLAY_CONFIG,
      },
    });

    // Compare per-marker budgets against the renderer's own rule
    // (use-map-lattice-render.js): a sideways name on the island stacks one
    // glyph per line, so its budget is in type steps; every horizontal name is
    // budgeted in whole monospace cells of CELL_EM × the declared 16-unit
    // step; and the overlay caps a sideways name at its declared outward box,
    // (labelMax + 1) × 2 = 22 cells.
    const STEP = 16;
    const OUTWARD_CELLS = 22;
    function budgetFor(marker, overlay) {
      const sideways = marker.side === "left" || marker.side === "right";
      const stacked = sideways && !overlay;
      if (stacked) {
        return Math.floor(marker.span / STEP);
      }
      return Math.min(
        Math.floor(marker.span / (CELL_EM * STEP)),
        overlay && sideways ? OUTWARD_CELLS : Infinity,
      );
    }
    const islandBudgets = new Map(
      wIsland.vm.fittedEdgeMarkers.map((m) => [m.id, budgetFor(m, false)]),
    );
    const overlayBudgets = new Map(
      wOverlay.vm.fittedEdgeMarkers.map((m) => [m.id, budgetFor(m, true)]),
    );

    // Top markers: island span = 120 / 3 = 40 -> budget 4. Overlay span =
    // 840 / 3 = 280 -> budget floor(280 / (CELL_EM × 16)) = 29.
    expect(islandBudgets.get("r:top_1")).toBe(4);
    expect(overlayBudgets.get("r:top_1")).toBe(29);
    expect(overlayBudgets.get("r:top_1")).toBeGreaterThan(islandBudgets.get("r:top_1"));

    // Left markers: island span = 134 / 2 = 67 -> budget floor(67 / 16) = 4.
    // Overlay span = 650 / 2 = 325, capped by the 22-cell outward box.
    expect(islandBudgets.get("r:left_1")).toBe(4);
    expect(overlayBudgets.get("r:left_1")).toBe(22);
    expect(overlayBudgets.get("r:left_1")).toBeGreaterThan(islandBudgets.get("r:left_1"));

    for (const id of ["r:top_1", "r:top_2", "r:top_3", "r:left_1", "r:left_2"]) {
      expect(overlayBudgets.get(id)).toBeGreaterThan(islandBudgets.get(id));
    }
  });
});
