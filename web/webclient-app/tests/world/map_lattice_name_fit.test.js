import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import MapLattice from "../../components/MapLattice.vue";
import { localMapModelFor } from "../../stories/fixtures.js";
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
    markerNameFont: 11,
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
    // Model gutterMin for overlay: 2 * reach + 1 + namePad
    const expectedOverlayGutter = 2 * Math.SQRT2 * (9 * 4.83) + 1 + 123;
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
        canvasSize: 208,
        overlayChrome: false,
        markerNames: true,
      },
    });
    const svg = wrapper.get("svg.local-map__lattice");
    const svgWidth = Number(svg.attributes("width"));
    const svgHeight = Number(svg.attributes("height"));

    // Core lattice with adjacent labels: effective pitch is (4 + 1) * 11 + 3 = 58.
    // 3 cols × 58 = 174; 3 rows × 58 = 174 + 14 = 188.
    // Gutter for island with nameHeight: 16 -> namePad: 18 -> gutter: 2 * sqrt(2) * 9 + 1 + 18 ≈ 44.4558
    const expectedGutter = 2 * Math.SQRT2 * 9 + 1 + 18;
    expect(svgWidth).toBe(208);
    expect(svgHeight).toBe(208);
    const vb = svg.attributes("viewBox").split(" ").map(Number);
    expect(vb[2]).toBeCloseTo(188 + 2 * expectedGutter, 5);
    expect(vb[3]).toBeCloseTo(188 + 2 * expectedGutter, 5);

    const westMarker = wrapper.get('[data-testid="local-map__edge-marker--r:west"]');
    const westText = westMarker.get("text.local-map__edge-marker-name--island");
    // Span on left edge: 188. budget = floor(188 / 10) = 18. Label is 11 chars -> fits whole!
    expect(westText.text()).toBe("西部丘陵與谷地（南門）");
    const tspans = westText.findAll("tspan");
    expect(tspans).toHaveLength(11);
    const reach = Math.SQRT2 * 9;
    const expectedX = -(reach + 9);
    tspans.forEach((tspan, i) => {
      expect(Number(tspan.attributes("x"))).toBeCloseTo(expectedX, 3);
      expect(tspan.attributes("dy")).toBe(i === 0 ? "0" : "10");
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
    expect(textEl.attributes("style")).toContain("font-size: 11px");

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
    // Default overlay markerNameFont is 11, labelMax is 10: outwardBox = (10 + 1) * 11 = 121
    const svg11 = wOverlay.get("svg.local-map__lattice");
    const width11 = Number(svg11.attributes("width"));

    // Re-render with markerNameFont = 12: outwardBox = (10 + 1) * 12 = 132 (+11 user units)
    // namePad increases by 11, so gutter increases by 11, and svgWidth increases by 2 * 11 = 22
    const wOverlay12 = mount(MapLattice, {
      props: {
        localMap: localMapModelFor(REPORTED_WILDERNESS_PAYLOAD),
        ...OVERLAY_CONFIG,
        markerNameFont: 12,
      },
    });
    const svg12 = wOverlay12.get("svg.local-map__lattice");
    const width12 = Number(svg12.attributes("width"));
    expect(width12 - width11).toBeCloseTo(22, 5);
  });

  it("Task 4.3: fits 14-glyph label to 11 on lone overlay left and draws whole on lone overlay top", () => {
    // 14-glyph label on lone overlay left marker:
    // span is 650, but outwardBox (121) binds: budget = min(floor(650 / 11), 11) = 11.
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
    // 14 chars fitted to budget 11: tail 9 ('一南關隘道前哨站營'), head 1 ('灰'), with '…'
    expect(leftText.text()).toBe("灰…一南關隘道前哨站營");
    expect(Array.from(leftText.text())).toHaveLength(11);

    // 14-glyph label on lone overlay top marker:
    // span is 840. Not drawsOutward (top edge draws along): budget = floor(840 / 11) = 76.
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

    // Island budget for both orientations is unchanged from wave 1
    const wIslandLeft = mount(MapLattice, {
      props: {
        localMap: localMapModelFor(leftPayload),
        colPitch: 40,
        rowPitch: 40,
        labelMax: 4,
        markerScale: 1,
        canvasSize: 208,
        overlayChrome: false,
        markerNames: true,
      },
    });
    const islandLeftText = wIslandLeft.get('[data-testid="local-map__edge-marker--r:west_long"] text');
    // Span 188, budget 18: fits 14 chars whole
    expect(islandLeftText.text()).toBe("灰鬮荒原第一南關隘道前哨站營");
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

    // Compare per-marker budgets
    const islandBudgets = new Map();
    for (const m of wIsland.vm.fittedEdgeMarkers) {
      islandBudgets.set(m.id, Math.floor(m.span / 10));
    }
    const overlayBudgets = new Map();
    for (const m of wOverlay.vm.fittedEdgeMarkers) {
      const drawsOutward = (121 > 0) && (m.side === "left" || m.side === "right");
      const maxBox = drawsOutward ? Math.floor(121 / 11) : Infinity;
      overlayBudgets.set(m.id, Math.min(Math.floor(m.span / 11), maxBox));
    }

    // Top markers: island span = 174 / 3 = 58 -> budget = 5. Overlay span = 840 / 3 = 280 -> budget = 25.
    expect(islandBudgets.get("r:top_1")).toBe(5);
    expect(overlayBudgets.get("r:top_1")).toBe(25);
    expect(overlayBudgets.get("r:top_1")).toBeGreaterThan(islandBudgets.get("r:top_1"));

    // Left markers: island span = 188 / 2 = 94 -> budget = 9. Overlay outwardBox bound = 11.
    expect(islandBudgets.get("r:left_1")).toBe(9);
    expect(overlayBudgets.get("r:left_1")).toBe(11);
    expect(overlayBudgets.get("r:left_1")).toBeGreaterThan(islandBudgets.get("r:left_1"));

    for (const id of ["r:top_1", "r:top_2", "r:top_3", "r:left_1", "r:left_2"]) {
      expect(overlayBudgets.get(id)).toBeGreaterThan(islandBudgets.get(id));
    }
  });
});
