import { afterEach, describe, expect, it } from "vitest";
import { localMapModelFor } from "../../stories/fixtures.js";
import {
  OVERLAY_PROPS,
  REPORTED_WILDERNESS_PAYLOAD,
  mountLattice as mountLatticeShared,
} from "./map_lattice_support.js";

// Wave 0 & 1 edge-marker names on the island and the overlay
// (webclient-minimap-05-edge-markers-replace-list). Split sibling of the
// original map_lattice.test.js; shared fixtures live in
// ./map_lattice_support.js.

describe("MapLattice (B4 world family, shared renderer)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountLattice(props = {}) {
    wrapper = mountLatticeShared((w) => {
      wrapper = w;
    }, props);
    return wrapper;
  }

  it("anti-ambiguity rule enforces across distinct edges", () => {
    // Marker on top and marker on bottom, different original labels, fitting to same string.
    // On a 1-col lattice (cols=1) the horizontal span is 58, so the budget is
    // floor(58 / (CELL_EM × 10)) = 9 monospace cells. These two labels
    // differ in their MIDDLE (北關 / 南關), which the head-and-tail ellipsis
    // allocates away first — head 灰 (2) + … (1) + tail 關隘道 (6) — so both fit to
    // 灰…關隘道 while their payload labels differ. That is exactly the case the
    // invariant exists for, and no tail-distinguished pair can reach it.
    const crossEdgePayload = {
      schema_version: 1,
      available: true,
      layer: "wilderness",
      title: "狹窄通道",
      current_node: "w:0:0",
      nodes: [
        { id: "w:0:0", label: "0,0", x: 0, y: 0, visibility: "current", current: true },
        { id: "w:0:1", label: "0,1", x: 0, y: 1, visibility: "visible_visited", current: false },
        { id: "w:0:2", label: "0,2", x: 0, y: 2, visibility: "visible_visited", current: false },
        { id: "r:top", label: "灰鬮荒原北關隘道", x: 0, y: 10, visibility: "remembered", landmark: true },
        { id: "r:bot", label: "灰鬮荒原南關隘道", x: 0, y: -10, visibility: "remembered", landmark: true },
      ],
    };
    const w = mountLattice({ localMap: localMapModelFor(crossEdgePayload), markerNames: true });
    const topMarker = w.get('[data-testid="local-map__edge-marker--r:top"]');
    const botMarker = w.get('[data-testid="local-map__edge-marker--r:bot"]');
    expect(topMarker.find("text").exists()).toBe(false);
    expect(botMarker.find("text").exists()).toBe(false);
  });



  it("Task 1.2: reserves band depth only on island, producing 44.46 gutter", () => {
    const w = mountLattice({
      localMap: localMapModelFor(REPORTED_WILDERNESS_PAYLOAD),
      markerNames: true,
    });
    const svg = w.find("svg.local-map__lattice");
    // The vertical footprint raises rows to 47; name gutter is unchanged.
    const expectedGutter = 2 * Math.SQRT2 * 9 + 1 + 18;
    expect(Number(svg.attributes("width"))).toBeCloseTo(174 + 2 * expectedGutter, 5);
    expect(Number(svg.attributes("height"))).toBeCloseTo(155 + 2 * expectedGutter, 5);
  });

  it("Task 1.3 & 1.4: renders left-edge island marker name as stacked glyph column with token styling", () => {
    const w = mountLattice({
      localMap: localMapModelFor(REPORTED_WILDERNESS_PAYLOAD),
      markerNames: true,
    });
    const westMarker = w.get('[data-testid="local-map__edge-marker--r:west"]');
    const textEl = westMarker.find("text.local-map__edge-marker-name--island");
    expect(textEl.exists()).toBe(true);
    // The type size is the surface's declared `markerNameFont` step (16 units
    // — the shared floor), bound inline so the drawn size and the fit budget
    // cannot drift apart; the rule itself declares only the shared font token
    // and tier.
    expect(textEl.attributes("style")).toContain("font-size: 16px");
    const tspans = textEl.findAll("tspan");
    expect(tspans.length).toBeGreaterThan(0);
    // Every tspan has the same x coordinate within band's depth, and the line
    // step is one type step per stacked glyph, whatever its cell width.
    const reach = Math.SQRT2 * 9;
    const expectedX = -(reach + 9);
    tspans.forEach((tspan, i) => {
      expect(Number(tspan.attributes("x"))).toBeCloseTo(expectedX, 5);
      if (i === 0) {
        expect(tspan.attributes("dy")).toBe("0");
      } else {
        expect(tspan.attributes("dy")).toBe("16");
      }
    });
    // The stacked column stays inside the free span its own marker holds, so
    // the fit budget and the drawn column height agree.
    expect(tspans.length * 16).toBeLessThanOrEqual(
      Number(w.find("svg.local-map__lattice").attributes("height")),
    );

    // Overlay left-edge marker still renders one horizontal outward text
    const wOverlay = mountLattice({
      localMap: localMapModelFor(REPORTED_WILDERNESS_PAYLOAD),
      ...OVERLAY_PROPS,
    });
    const overlayWest = wOverlay.get('[data-testid="local-map__edge-marker--r:west"]');
    const overlayText = overlayWest.find("text.local-map__edge-marker-name");
    expect(overlayText.exists()).toBe(true);
    expect(overlayText.findAll("tspan")).toHaveLength(0);
    expect(overlayText.attributes("text-anchor")).toBe("end");
  });

  it("Task 2.1: fits lone marker whole and truncates two markers to their span allocating tail first", () => {
    // Lone marker on top edge: span = 174, budget = floor(174 / (CELL_EM × 16))
    // = 18 cells. The label is 11 wide glyphs = 22 cells, so the kept
    // （南門） qualifier (8 cells) plus "…" leaves 9 cells of head: 西部丘陵.
    const lonePayload = {
      schema_version: 1,
      available: true,
      layer: "wilderness",
      title: "西部荒野",
      current_node: "w:1:1",
      nodes: [
        ...REPORTED_WILDERNESS_PAYLOAD.nodes.slice(0, 9),
        { id: "r:north", label: "西部丘陵與谷地（南門）", x: 1, y: 10, visibility: "remembered", landmark: true },
      ],
    };
    const wLone = mountLattice({ localMap: localMapModelFor(lonePayload), markerNames: true });
    const northMarker = wLone.get('[data-testid="local-map__edge-marker--r:north"]');
    expect(northMarker.find("text").text()).toBe("西部丘陵…（南門）");

    // Two markers on top edge: span = 174/2 = 87, budget = floor(87 / (CELL_EM
    // × 16)) = 9 cells. The qualifier （南門） (8 cells) plus "…" (1) fills the
    // budget, so the fit falls through to the head-and-tail form: 西 (2) + …
    // (1) + the 3-glyph tail 南門） (6) = 9 cells. Fitted: 西…南門）.
    const twoPayload = {
      schema_version: 1,
      available: true,
      layer: "wilderness",
      title: "西部荒野",
      current_node: "w:1:1",
      nodes: [
        ...REPORTED_WILDERNESS_PAYLOAD.nodes.slice(0, 9),
        { id: "r:north1", label: "西部丘陵與谷地（南門）", x: 0, y: 10, visibility: "remembered", landmark: true },
        { id: "r:north2", label: "聖潔王都", x: 2, y: 10, visibility: "remembered", landmark: true },
      ],
    };
    const wTwo = mountLattice({ localMap: localMapModelFor(twoPayload), markerNames: true });
    const n1 = wTwo.get('[data-testid="local-map__edge-marker--r:north1"]');
    const n2 = wTwo.get('[data-testid="local-map__edge-marker--r:north2"]');
    expect(n1.find("text").text()).toBe("西…南門）");
    expect(n2.find("text").text()).toBe("聖潔王都");
  });

  it("Task 2.2 & 2.3: anti-ambiguity drops names when differing labels truncate identically; preserves title", () => {
    // Three markers on top edge: span = 174/3 = 58, budget = floor(58 /
    // (CELL_EM × 16)) = 6 cells.
    // The two gate labels differ only in their middle (北關 / 南關), which the
    // head-and-tail fit allocates away first: head 灰 (2) + … (1) + tail 道
    // (2), so both would be drawn as 灰…道 while their payload labels differ.
    // Anti-ambiguity rule MUST omit both visible names while keeping diamonds and titles.
    const crowdedPayload = {
      schema_version: 1,
      available: true,
      layer: "wilderness",
      title: "西部荒野",
      current_node: "w:1:1",
      nodes: [
        ...REPORTED_WILDERNESS_PAYLOAD.nodes.slice(0, 9),
        { id: "r:gate_s", label: "灰鬮荒原南關隘道", x: 0, y: 10, visibility: "remembered", landmark: true },
        { id: "r:gate_n", label: "灰鬮荒原北關隘道", x: 1, y: 10, visibility: "remembered", landmark: true },
        { id: "r:king", label: "聖潔王都", x: 2, y: 10, visibility: "remembered", landmark: true },
      ],
    };
    const w = mountLattice({ localMap: localMapModelFor(crowdedPayload), markerNames: true });
    const gateS = w.get('[data-testid="local-map__edge-marker--r:gate_s"]');
    const gateN = w.get('[data-testid="local-map__edge-marker--r:gate_n"]');
    const king = w.get('[data-testid="local-map__edge-marker--r:king"]');

    // Diamonds and titles exist
    expect(gateS.find(".local-map__edge-marker-diamond").exists()).toBe(true);
    expect(gateN.find(".local-map__edge-marker-diamond").exists()).toBe(true);
    expect(gateS.find("title").text()).toBe("灰鬮荒原南關隘道");
    expect(gateN.find("title").text()).toBe("灰鬮荒原北關隘道");

    // Visible name omitted on the two colliding gates
    expect(gateS.find("text").exists()).toBe(false);
    expect(gateN.find("text").exists()).toBe(false);

    // The non-colliding marker draws its own fitted name (聖潔王都 is 8 cells,
    // so the 6-cell budget truncates it to 聖…都) — only the two colliding
    // names are dropped entirely.
    expect(king.find("text").text()).toBe("聖…都");
  });

  it("Task 2.4: overlay disclosure path draws full names for crowded island payload", () => {
    const crowdedPayload = {
      schema_version: 1,
      available: true,
      layer: "wilderness",
      title: "西部荒野",
      current_node: "w:1:1",
      nodes: [
        ...REPORTED_WILDERNESS_PAYLOAD.nodes.slice(0, 9),
        { id: "r:gate_s", label: "灰鬮荒原南關隘道", x: 0, y: 10, visibility: "remembered", landmark: true },
        { id: "r:gate_n", label: "灰鬮荒原北關隘道", x: 1, y: 10, visibility: "remembered", landmark: true },
      ],
    };
    const wOverlay = mountLattice({ localMap: localMapModelFor(crowdedPayload), ...OVERLAY_PROPS });
    const s = wOverlay.get('[data-testid="local-map__edge-marker--r:gate_s"]');
    const n = wOverlay.get('[data-testid="local-map__edge-marker--r:gate_n"]');
    expect(s.find("text").exists()).toBe(true);
    expect(n.find("text").exists()).toBe(true);
    expect(s.find("text").text()).toBe("灰鬮荒原南關隘道");
    expect(n.find("text").text()).toBe("灰鬮荒原北關隘道");
    expect(s.attributes("aria-label")).toBe("灰鬮荒原南關隘道");
    expect(n.attributes("aria-label")).toBe("灰鬮荒原北關隘道");
  });

  it("handles Unicode code points and low budget boundaries correctly", () => {
    const unicodePayload = {
      schema_version: 1,
      available: true,
      layer: "wilderness",
      title: "西部荒野",
      current_node: "w:1:1",
      nodes: [
        ...REPORTED_WILDERNESS_PAYLOAD.nodes.slice(0, 9),
        { id: "r:astral", label: "𠮷野市（新門）", x: 1, y: 10, visibility: "remembered", landmark: true },
      ],
    };
    const w = mountLattice({ localMap: localMapModelFor(unicodePayload), markerNames: true });
    const marker = w.get('[data-testid="local-map__edge-marker--r:astral"]');
    expect(marker.find("text").text()).toBe("𠮷野市（新門）");

    // Budget < 3 drops the visible name safely (drops name, keeps diamond/title)
    // 1-col lattice with 3 markers on top edge: span = 58/3 = 19.33 -> budget = 3 cells, too few for
    // a wide head, "…" and a wide tail (5 cells)
    const lowBudgetPayload = {
      schema_version: 1,
      available: true,
      layer: "wilderness",
      title: "狹窄通道",
      current_node: "w:0:0",
      nodes: [
        { id: "w:0:0", label: "0,0", x: 0, y: 0, visibility: "current", current: true },
        { id: "w:0:1", label: "0,1", x: 0, y: 1, visibility: "visible_visited", current: false },
        { id: "w:0:2", label: "0,2", x: 0, y: 2, visibility: "visible_visited", current: false },
        { id: "r:m1", label: "地圖甲", x: 0, y: 10, visibility: "remembered", landmark: true },
        { id: "r:m2", label: "地圖乙", x: 0, y: 11, visibility: "remembered", landmark: true },
        { id: "r:m3", label: "地圖丙", x: 0, y: 12, visibility: "remembered", landmark: true },
      ],
    };
    const wLow = mountLattice({ localMap: localMapModelFor(lowBudgetPayload), markerNames: true });
    const m1 = wLow.get('[data-testid="local-map__edge-marker--r:m1"]');
    expect(m1.find("text").exists()).toBe(false);
    expect(m1.find("title").text()).toBe("地圖甲");
  });
});
