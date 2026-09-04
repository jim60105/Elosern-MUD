import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import LocalMap from "../../components/LocalMap.vue";
import MapLattice from "../../components/MapLattice.vue";
import LocalMapModel from "../../lib/local_map.js";
import {
  LOCAL_MAP_INTERIOR_SAMPLE,
  LOCAL_MAP_SAMPLE,
  LOCAL_MAP_SINGLE_NODE_SAMPLE,
  LOCAL_MAP_TALL_LATTICE_SAMPLE,
  LOCAL_MAP_WILDERNESS_SAMPLE,
  localMapModelFor,
} from "../../stories/fixtures.js";

// The shared lattice renderer (improve-webclient-map-overlay-scale):
// the minimap island and the full-map overlay both render through
// MapLattice, parameterized by scale. These tests guard the extraction
// itself (identical content at both scales) and the non-intersection
// invariant at the overlay's larger scale.

// The server's four fixed visibility-state legend labels, in wire order
// (web/webclient/presentation/local_map.py LEGEND_LABELS).
const LEGEND_LABELS_FOR_TEST = [
  "你目前所在的位置",
  "尚未探索的相鄰位置",
  "已經探索過的相鄰位置",
  "曾經到過、但不在附近的遠方位置",
];

// Wave 0 & 1 (webclient-minimap-05-edge-markers-replace-list):
  // Named edge markers on the island and overlay.
  const REPORTED_WILDERNESS_PAYLOAD = {
    schema_version: 1,
    available: true,
    layer: "wilderness",
    title: "西部荒野",
    current_node: "w:1:1",
    nodes: [
      { id: "w:0:0", label: "0,0", x: 0, y: 0, visibility: "visible_visited", current: false },
      { id: "w:1:0", label: "1,0", x: 1, y: 0, visibility: "visible_visited", current: false },
      { id: "w:2:0", label: "2,0", x: 2, y: 0, visibility: "visible_visited", current: false },
      { id: "w:0:1", label: "0,1", x: 0, y: 1, visibility: "visible_visited", current: false },
      { id: "w:1:1", label: "1,1", x: 1, y: 1, visibility: "current", current: true },
      { id: "w:2:1", label: "2,1", x: 2, y: 1, visibility: "visible_visited", current: false },
      { id: "w:0:2", label: "0,2", x: 0, y: 2, visibility: "visible_visited", current: false },
      { id: "w:1:2", label: "1,2", x: 1, y: 2, visibility: "visible_visited", current: false },
      { id: "w:2:2", label: "2,2", x: 2, y: 2, visibility: "visible_visited", current: false },
      { id: "r:west", label: "西部丘陵與谷地（南門）", x: -10, y: 1, visibility: "remembered", landmark: true },
      { id: "r:east", label: "聖潔王都", x: 10, y: 1, visibility: "remembered", landmark: true },
    ],
    edges: [],
  };

  const UNIFORM_WILDERNESS_PAYLOAD = {
    schema_version: 1,
    available: true,
    layer: "wilderness",
    title: "西部荒野",
    current_node: "w:1:1",
    nodes: [
      { id: "w:0:0", label: "西部荒野", x: 0, y: 0, visibility: "visible_visited" },
      { id: "w:1:0", label: "西部荒野", x: 1, y: 0, visibility: "visible_visited" },
      { id: "w:2:0", label: "西部荒野", x: 2, y: 0, visibility: "visible_visited" },
      { id: "w:0:1", label: "西部荒野", x: 0, y: 1, visibility: "visible_visited" },
      { id: "w:1:1", label: "西部荒野", x: 1, y: 1, visibility: "current", current: true },
      { id: "w:2:1", label: "西部荒野", x: 2, y: 1, visibility: "visible_visited" },
      { id: "w:0:2", label: "西部荒野", x: 0, y: 2, visibility: "visible_visited" },
      { id: "w:1:2", label: "西部荒野", x: 1, y: 2, visibility: "visible_visited" },
      { id: "w:2:2", label: "西部荒野", x: 2, y: 2, visibility: "visible_visited" },
      { id: "r:west", label: "西部丘陵與谷地（南門）", x: -10, y: 1, visibility: "remembered", landmark: true },
      { id: "r:east", label: "聖潔王都", x: 10, y: 1, visibility: "remembered", landmark: true },
    ],
    edges: [],
  };

describe("MapLattice (B4 world family, shared renderer)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  it("anti-ambiguity rule enforces across distinct edges", () => {
    // Marker on top and marker on bottom, different original labels, fitting to same string.
    // On a 1-col lattice (cols=1) the horizontal span is 58, so the budget is
    // floor(58 / markerNameFont) = floor(58 / 10) = 5 glyphs. These two labels
    // differ in their MIDDLE (北關 / 南關), which the head-and-tail ellipsis
    // allocates away first — tail 3 = 關隘道, head 1 = 灰 — so both fit to
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
    // Core lattice: 3*58=174 by 3*44+14=146. Gutter: 2*sqrt(2)*9 + 1 + 18 ≈ 44.455844.
    const expectedGutter = 2 * Math.SQRT2 * 9 + 1 + 18;
    expect(Number(svg.attributes("width"))).toBeCloseTo(174 + 2 * expectedGutter, 5);
    expect(Number(svg.attributes("height"))).toBeCloseTo(146 + 2 * expectedGutter, 5);
  });

  it("Task 1.3 & 1.4: renders left-edge island marker name as stacked glyph column with token styling", () => {
    const w = mountLattice({
      localMap: localMapModelFor(REPORTED_WILDERNESS_PAYLOAD),
      markerNames: true,
    });
    const westMarker = w.get('[data-testid="local-map__edge-marker--r:west"]');
    const textEl = westMarker.find("text.local-map__edge-marker-name--island");
    expect(textEl.exists()).toBe(true);
    // The type size is the surface's declared `markerNameFont` step (default
    // 10), bound inline so the drawn size and the fit budget cannot drift
    // apart; the rule itself declares only the shared font token and tier.
    expect(textEl.attributes("style")).toContain("font-size: 10px");
    const tspans = textEl.findAll("tspan");
    expect(tspans.length).toBeGreaterThan(0);
    // Every tspan has the same x coordinate within band's depth, and the line
    // step is one type step (full-width CJK in a monospace token).
    const reach = Math.SQRT2 * 9;
    const expectedX = -(reach + 9);
    tspans.forEach((tspan, i) => {
      expect(Number(tspan.attributes("x"))).toBeCloseTo(expectedX, 5);
      if (i === 0) {
        expect(tspan.attributes("dy")).toBe("0");
      } else {
        expect(tspan.attributes("dy")).toBe("10");
      }
    });
    // The stacked column stays inside the free span its own marker holds, so
    // the fit budget and the drawn column height agree.
    expect(tspans.length * 10).toBeLessThanOrEqual(
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
    // Lone marker on top edge: span = 174, budget = floor(174 / 10) = 17.
    // Label length 11 <= 17 -> draws whole.
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
    expect(northMarker.find("text").text()).toBe("西部丘陵與谷地（南門）");

    // Two markers on top edge: span = 174/2 = 87, budget = floor(87 / 10) = 8.
    // Tail is （南門） (4 chars). Head budget = 8 - 1 - 4 = 3 ('西部丘').
    // Fitted: 西部丘…（南門）.
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
    expect(n1.find("text").text()).toBe("西部丘…（南門）");
    expect(n2.find("text").text()).toBe("聖潔王都");
  });

  it("Task 2.2 & 2.3: anti-ambiguity drops names when differing labels truncate identically; preserves title", () => {
    // Three markers on top edge: span = 174/3 = 58, budget = floor(58 / 10) = 5.
    // The two gate labels differ only in their middle (北關 / 南關), which the
    // head-and-tail fit allocates away first: tail 3 = 關隘道, head 1 = 灰, so
    // both would be drawn as 灰…關隘道 while their payload labels differ.
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

    // Non-colliding marker draws its name
    expect(king.find("text").text()).toBe("聖潔王都");
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
    // 1-col lattice with 3 markers on top edge: span = 58/3 = 19.33 -> budget = floor(19.33/10) = 1 (< 3)
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

  // Wave 0 binds every mount through the shared derived-shape helper (the
  // exact store model shape); the old local copy shimmed the raw
  // `current_node` field around the detail-line seeding bug design D1 fixed.
  function mountLattice(props = {}) {
    wrapper = mount(MapLattice, {
      props: {
        localMap: localMapModelFor(LOCAL_MAP_SAMPLE),
        ...props,
      },
    });
    return wrapper;
  }

  const OVERLAY_PROPS = {
    colPitch: 280,
    rowPitch: 212,
    labelMax: 10,
    markerScale: 4.83,
    maxWidth: 848,
    maxHeight: null,
    fillWidth: true,
    overlayChrome: true,
    markerNames: true,
    markerNameFont: 11,
  };
  it("renders identical node/edge/legend content at the island's default scale", () => {
    const w = mountLattice();
    // The grid fixture's in-view lattice: 3 cols × 1 row. The remembered
    // fixture node (5, 5) sits outside the in-view extent, so the island
    // grows an edge-marker gutter around the natural 174×58 canvas
    // (map-02 D3b; the model's gutter for this fixture is 26.4558…).
    const svg = w.find("svg.local-map__lattice");
    expect(Number(svg.attributes("width"))).toBeCloseTo(226.91168824543144, 6);
    expect(Number(svg.attributes("height"))).toBeCloseTo(110.91168824543144, 6);
    expect(w.findAll('[data-testid^="local-map__node--"]').length).toBe(3);
    // The payload lists 3 edges, but the third one ends at the remembered
    // node (grid:altoria:5:5), whose endpoint is not on the canvas — the
    // renderer omits it per the spec's edge-omission rule, so 2 edges draw.
    expect(w.findAll('[data-testid^="local-map__edge--"]').length).toBe(2);
    expect(w.findAll('[data-testid^="local-map__legend-item--"]').length).toBe(4);
    expect(w.get('[data-testid="local-map__marker--current"]').exists()).toBe(true);
    // The edge-marker decoration layer: one diamond for the remembered
    // place, in the island's name-free presentation (aria-hidden, no text).
    const edgeMarker = w.get('[data-testid="local-map__edge-marker--grid:altoria:5:5"]');
    expect(edgeMarker.attributes("aria-hidden")).toBe("true");
    expect(edgeMarker.find("text").exists()).toBe(false);
  });

  it("renders identical node/edge/legend content at the overlay's larger scale", () => {
    const w = mountLattice(OVERLAY_PROPS);
    const svg = w.find("svg.local-map__lattice");
    // The natural canvas is 3 × 280px wide, 1 × 212px row pitch + 14px
    // label band; the edge-marker gutter (model value 246.9517… at the
    // overlay's name-bearing geometry) grows it on every side (map-02 D3b).
    expect(Number(svg.attributes("width"))).toBeCloseTo(1333.9034542254337, 6);
    expect(Number(svg.attributes("height"))).toBeCloseTo(719.9034542254337, 6);
    expect(w.findAll('[data-testid^="local-map__node--"]').length).toBe(3);
    expect(w.findAll('[data-testid^="local-map__edge--"]').length).toBe(2);
    expect(w.findAll('[data-testid^="local-map__legend-item--"]').length).toBe(4);
    // The fill-width variant renders the canvas at the body's available
    // width (848px content box) with no height cap.
    const style = svg.element.style;
    expect(style.width).toBe("100%");
    expect(style.maxWidth).toBe("848px");
    expect(style.maxHeight).toBe("");
    // At the overlay's scale the marker carries its place name and an
    // accessible name (the overlay has no remembered list).
    const edgeMarker = w.get('[data-testid="local-map__edge-marker--grid:altoria:5:5"]');
    expect(edgeMarker.attributes("aria-hidden")).toBeUndefined();
    expect(edgeMarker.attributes("aria-label")).toBe("舊街區");
    expect(edgeMarker.find("text").text()).toBe("舊街區");
  });

  // slim-minimap-island D1: the legend-display switch. Default-on keeps
  // every bare mount (and the overlay) rendering the legend; off mounts no
  // legend element at all while the canvas content is untouched.
  it("mounts no legend element when the legend switch is off", () => {
    const w = mountLattice({ showLegend: false });
    expect(w.find('[data-testid="local-map__legend"]').exists()).toBe(false);
    expect(w.findAll('[data-testid^="local-map__legend-item--"]')).toHaveLength(0);
    // The rest of the shared render is unchanged by the switch.
    expect(w.findAll('[data-testid^="local-map__node--"]').length).toBe(3);
    expect(w.findAll('[data-testid^="local-map__edge--"]').length).toBe(2);
    expect(w.get('[data-testid="local-map__marker--current"]').exists()).toBe(true);
  });

  it("keeps node markers and labels non-intersecting at the overlay's scale", () => {
    const w = mountLattice(OVERLAY_PROPS);

    // Node centers from the model's col/row + the overlay's pitch
    // (colPitch 280, rowPitch 212, rows=1): centers are col*280+140 and
    // (1-1-row)*212+106, shifted by the edge-marker gutter the model
    // computes for this exact geometry (map-02 D3b — the renderer and the
    // test derive the gutter from the same model call, pinning their
    // composition; relative node geometry is gutter-invariant).
    const gutter = LocalMapModel.edgeMarkersFor(
      LOCAL_MAP_SAMPLE.nodes.filter((n) => n.visibility !== "remembered"),
      LOCAL_MAP_SAMPLE.nodes.filter((n) => n.visibility === "remembered"),
      {
        canvasWidth: 3 * 280,
        canvasHeight: 212 + 14,
        current: { x: 420, y: 106 },
        markerHalf: 9 * 4.83,
        nameWidth: 11 * 11,
        nameHeight: 16,
      },
    ).gutter;
    const centers = {
      "grid:altoria:1:2": { x: 420 + gutter, y: 106 + gutter },
      "grid:altoria:2:2": { x: 700 + gutter, y: 106 + gutter },
      "grid:altoria:0:2": { x: 140 + gutter, y: 106 + gutter },
    };
    for (const [id, center] of Object.entries(centers)) {
      const node = w.get(`[data-testid="local-map__node--${id}"]`);
      expect(node.attributes("transform")).toBe(
        `translate(${String(center.x)}, ${String(center.y)})`,
      );
    }

    // Marker footprints in pre-scale units at markerScale 4.83 (draft
    // ladder, webclient-map-01-draft-chrome D2): the current seal circle
    // r=8 with a 2px stroke → half-extent 8×4.83+1; the unvisited hollow
    // dot r=4.5 + stroke 2 → 4.5×4.83+1; the visited ink dot r=4.5 +
    // stroke 1 → 4.5×4.83+0.5. The gold landmark ring and the actionable
    // halo are same-node decorations, not markers — excluded here (they sit
    // within the same footprint as their node's marker).
    const CURRENT_HALF = 8 * 4.83 + 1;
    const UNVISITED_HALF = 4.5 * 4.83 + 1;
    const VISITED_HALF = 4.5 * 4.83 + 0.5;
    const markerBoxes = {
      "grid:altoria:1:2": { x1: centers["grid:altoria:1:2"].x - CURRENT_HALF, y1: centers["grid:altoria:1:2"].y - CURRENT_HALF, x2: centers["grid:altoria:1:2"].x + CURRENT_HALF, y2: centers["grid:altoria:1:2"].y + CURRENT_HALF },
      "grid:altoria:2:2": { x1: centers["grid:altoria:2:2"].x - UNVISITED_HALF, y1: centers["grid:altoria:2:2"].y - UNVISITED_HALF, x2: centers["grid:altoria:2:2"].x + UNVISITED_HALF, y2: centers["grid:altoria:2:2"].y + UNVISITED_HALF },
      "grid:altoria:0:2": { x1: centers["grid:altoria:0:2"].x - VISITED_HALF, y1: centers["grid:altoria:0:2"].y - VISITED_HALF, x2: centers["grid:altoria:0:2"].x + VISITED_HALF, y2: centers["grid:altoria:0:2"].y + VISITED_HALF },
    };
    // Node labels: baseline at the scaled offset (13×4.83 + 13 ≈ 75.8px
    // below the node origin); the 11px monospace line box extends 10.5px
    // above and 3px below the baseline. CJK glyphs are full-width (11px);
    // a truncated label appends "…" (labelMax + 1 glyphs worst case).
    const LABEL_ASCENT = 10.5;
    const LABEL_DESCENT = 3;
    const GLYPH_W = 11;
    const labelY = 13 * 4.83 + 13;
    function labelBox(id) {
      const center = centers[id];
      const node = w.get(`[data-testid="local-map__node--${id}"]`);
      const textEl = node.find(".local-map__node-label");
      const label = textEl.text();
      const width = label.length * GLYPH_W;
      return {
        x1: center.x - width / 2,
        y1: center.y + labelY - LABEL_ASCENT,
        x2: center.x + width / 2,
        y2: center.y + labelY + LABEL_DESCENT,
      };
    }
    const labelBoxes = {
      "grid:altoria:1:2": labelBox("grid:altoria:1:2"),
      "grid:altoria:2:2": labelBox("grid:altoria:2:2"),
      "grid:altoria:0:2": labelBox("grid:altoria:0:2"),
    };

    function separated(a, b) {
      return (
        a.x2 + 2 <= b.x1 ||
        b.x2 + 2 <= a.x1 ||
        a.y2 + 2 <= b.y1 ||
        b.y2 + 2 <= a.y1
      );
    }
    function checkAll(boxes) {
      const ids = Object.keys(boxes);
      for (let i = 0; i < ids.length; i += 1) {
        for (let j = i + 1; j < ids.length; j += 1) {
          expect(
            separated(boxes[ids[i]], boxes[ids[j]]),
            `${ids[i]} vs ${ids[j]} must keep a ≥2px gap at the overlay's scale`,
          ).toBe(true);
        }
      }
      for (const id of Object.keys(boxes)) {
        for (const labelId of Object.keys(labelBoxes)) {
          expect(
            separated(markerBoxes[id], labelBoxes[labelId]),
            `marker ${id} vs label ${labelId} must keep a ≥2px gap`,
          ).toBe(true);
        }
      }
    }
    checkAll(markerBoxes);

    // Connector edges stay visible: the center-to-center span (280px
    // horizontal) minus the two scaled marker footprints (current 9×4.83,
    // unvisited 5.5×4.83) leaves a positive visible segment.
    const e0 = w.get('[data-testid="local-map__edge--0"]');
    expect(Number(e0.attributes("x1"))).toBeCloseTo(420 + gutter, 6);
    expect(Number(e0.attributes("y1"))).toBeCloseTo(106 + gutter, 6);
    expect(Number(e0.attributes("x2"))).toBeCloseTo(700 + gutter, 6);
    expect(Number(e0.attributes("y2"))).toBeCloseTo(106 + gutter, 6);
    expect(280 - (8 + 1) * 4.83 - (4.5 + 1) * 4.83).toBeGreaterThan(0);
  });

  it("emits select on every node activation and move only for an exact move action", async () => {
    const w = mountLattice();
    // The unvisited node carries the exact `move` action.
    await w.get('[data-testid="local-map__node--grid:altoria:2:2"]').trigger("click");
    const selected = w.emitted("select");
    const moved = w.emitted("move");
    expect(selected).toHaveLength(1);
    expect(selected[0][0].id).toBe("grid:altoria:2:2");
    expect(moved).toHaveLength(1);
    expect(moved[0][0]).toEqual({
      exit_ref: "e_altoria_1_2_e",
      destination: "grid:altoria:2:2",
    });
    // A node without an action emits select only.
    await w.get('[data-testid="local-map__node--grid:altoria:0:2"]').trigger("click");
    expect(w.emitted("select")).toHaveLength(2);
    expect(w.emitted("move")).toHaveLength(1);
  });

  it("emits hover and leave for node pointer events", async () => {
    const w = mountLattice();
    await w.get('[data-testid="local-map__node--grid:altoria:1:2"]').trigger("mouseenter");
    expect(w.emitted("hover")).toHaveLength(1);
    expect(w.emitted("hover")[0][0].id).toBe("grid:altoria:1:2");
    await w.find("svg.local-map__lattice").trigger("mouseleave");
    expect(w.emitted("leave")).toHaveLength(1);
  });

  it("renders the wilderness fixture content at both scales", () => {
    const island = mount(MapLattice, {
      props: { localMap: localMapModelFor(LOCAL_MAP_WILDERNESS_SAMPLE) },
    });
    const overlay = mount(MapLattice, {
      props: { localMap: localMapModelFor(LOCAL_MAP_WILDERNESS_SAMPLE), ...OVERLAY_PROPS },
    });
    const islandNodes = island.findAll('[data-testid^="local-map__node--"]');
    const overlayNodes = overlay.findAll('[data-testid^="local-map__node--"]');
    expect(islandNodes.length).toBe(overlayNodes.length);
    expect(island.findAll('[data-testid^="local-map__edge--"]').length).toBe(
      overlay.findAll('[data-testid^="local-map__edge--"]').length,
    );
  });

  // ---------------------------------------------------------------------
  // webclient-map-01-draft-chrome: the overlay chrome (design D4) — the
  // mapcanvas framing class and the teardrop pin — plus the shared draft
  // adornments (gold landmark ring, dot-chip legend).
  // ---------------------------------------------------------------------

  it("paints the mapcanvas framing only under overlayChrome", () => {
    const island = mountLattice();
    expect(island.get("svg.local-map__lattice").classes()).not.toContain("local-map__lattice--canvas");
    island.unmount();
    const overlay = mountLattice({ ...OVERLAY_PROPS, overlayChrome: true });
    expect(overlay.get("svg.local-map__lattice").classes()).toContain("local-map__lattice--canvas");
  });

  it("renders the pin only under overlayChrome, anchored to the current node", () => {
    const island = mountLattice();
    expect(island.findAll('[data-testid="local-map__pin"]')).toHaveLength(0);
    island.unmount();

    const overlay = mountLattice({ ...OVERLAY_PROPS, overlayChrome: true });
    const pins = overlay.findAll('[data-testid="local-map__pin"]');
    expect(pins).toHaveLength(1);
    // The pin shares the current node group's coordinate system: same
    // translate pair, then the marker scale so it tracks the marker ladder.
    const currentTransform = overlay
      .get('[data-testid="local-map__node--grid:altoria:1:2"]')
      .attributes("transform");
    const pinTransform = pins[0].attributes("transform");
    expect(pinTransform.startsWith(`${currentTransform} scale(`)).toBe(true);
    expect(pinTransform).toContain("scale(4.83)");
    // Pure adornment: it must never intercept node clicks or announce.
    // The fixed teardrop path: apex 16 pre-scale units directly above the
    // current node's y, x-aligned (the draft's pin geometry).
    expect(pins[0].attributes("d").startsWith("M0 -16")).toBe(true);
    expect(pins[0].attributes("aria-hidden")).toBe("true");
  });

  it("keeps the pin's stroke hairline at any marker scale", () => {
    // The pin path geometry scales with the ladder via its element
    // transform; without a non-scaling stroke the overlay's scale(4.83)
    // would thicken the draft's 1.4px outline to ~6.8px (rubber-duck W1).
    const w = mountLattice({ ...OVERLAY_PROPS, overlayChrome: true });
    let rule = null;
    for (const sheet of document.styleSheets) {
      for (const candidate of sheet.cssRules) {
        if (candidate.selectorText?.includes(".local-map__pin")) rule = candidate.cssText;
      }
    }
    expect(rule, "the pin rule is in the component's injected style sheet").toContain(
      "vector-effect: non-scaling-stroke",
    );
    w.unmount();
  });

  it("renders no pin when the payload carries no current node", () => {
    const model = localMapModelFor(LOCAL_MAP_SAMPLE);
    const noCurrent = {
      ...model,
      nodes: model.nodes.map((n) => (n.visibility === "current" ? { ...n, visibility: "visible_visited" } : n)),
    };
    const w = mountLattice({ ...OVERLAY_PROPS, overlayChrome: true, localMap: noCurrent });
    expect(w.findAll('[data-testid="local-map__pin"]')).toHaveLength(0);
  });

  it("draws the gold landmark ring over (not instead of) the visibility marker", () => {
    // The wilderness fixture's non-current landmark: 舊營地 (visited) at
    // island scale — ring r=5 coexists with the visited dot r=4.5.
    const w = mountLattice({ localMap: localMapModelFor(LOCAL_MAP_WILDERNESS_SAMPLE) });
    const node = w.get('[data-testid="local-map__node--wild:plains:2:2"]');
    const rings = node.findAll(".local-map__landmark");
    expect(rings).toHaveLength(1);
    expect(rings[0].attributes("r")).toBe("5");
    expect(node.find(".local-map__marker--visible_visited").exists()).toBe(true);
    // The ring is deliberately outside the `local-map__marker` class (the
    // browser geometry audit pairs marker boxes; decorations must not
    // self-overlap).
    expect(rings[0].classes()).not.toContain("local-map__marker");
    // The current landmark keeps exactly one ring; the remembered landmark
    // (遠處山徑) stays in the list with no ring on the canvas.
    expect(w.findAll('[data-testid="local-map__node--wild:plains:3:1"] .local-map__landmark')).toHaveLength(1);
    expect(w.findAll('[data-testid="local-map__node--wild:plains:7:5"]').length).toBe(0);
    expect(w.findAll(".local-map__landmark")).toHaveLength(2);
  });

  it("scales the landmark ring with the marker ladder at the overlay scale", () => {
    const w = mountLattice({
      ...OVERLAY_PROPS,
      localMap: localMapModelFor(LOCAL_MAP_WILDERNESS_SAMPLE),
    });
    expect(
      w.get('[data-testid="local-map__node--wild:plains:2:2"] .local-map__landmark').attributes("r"),
    ).toBe(String(5 * 4.83));
  });

  it("labels nodes by draft tier: here, gold, seen, far", () => {
    const w = mountLattice({ localMap: localMapModelFor(LOCAL_MAP_WILDERNESS_SAMPLE) });
    expect(
      w.get('[data-testid="local-map__node--wild:plains:3:1"] .local-map__node-label').classes(),
    ).toContain("local-map__node-label--here");
    // 舊營地: a visited landmark reads gold, not seen.
    expect(
      w.get('[data-testid="local-map__node--wild:plains:2:2"] .local-map__node-label').classes(),
    ).toContain("local-map__node-label--gold");
    expect(
      w.get('[data-testid="local-map__node--wild:plains:4:1"] .local-map__node-label').classes(),
    ).toContain("local-map__node-label--far");
  });

  // ---------------------------------------------------------------------
  // local-map-remembered-are-map-gateways wave 6 (FLAGGED/STRIKEABLE, design
  // D8b): the wilderness in-view neighbourhood must not repeat one region
  // name across every drawn cell.
  // ---------------------------------------------------------------------

  it("suppresses a duplicate in-view label on the wilderness layer, keeping the accessible name", () => {
    const model = localMapModelFor(LOCAL_MAP_WILDERNESS_SAMPLE);
    const current = model.nodes.find((n) => n.visibility === "current");
    const inViewVisibilities = new Set(["visible_unvisited", "visible_visited"]);
    const duped = {
      ...model,
      nodes: model.nodes.map((n) =>
        inViewVisibilities.has(n.visibility) ? { ...n, label: current.label } : n,
      ),
    };
    const inViewIds = duped.nodes.filter((n) => inViewVisibilities.has(n.visibility)).map((n) => n.id);
    expect(inViewIds.length).toBeGreaterThan(0);
    const w = mountLattice({ localMap: duped });
    for (const id of inViewIds) {
      const label = w.get(`[data-testid="local-map__node--${id}"] .local-map__node-label`);
      // The <title> element's text is part of the label's own textContent in
      // jsdom, so isolate the visible run by reading its own direct text.
      expect(label.element.childNodes[label.element.childNodes.length - 1].textContent).toBe("");
      expect(label.get("title").text()).toBe(current.label);
    }
    // The current node always draws its own label.
    const currentLabel = w.get(`[data-testid="local-map__node--${current.id}"] .local-map__node-label`);
    expect(
      currentLabel.element.childNodes[currentLabel.element.childNodes.length - 1].textContent,
    ).toBe(current.label);
  });

  it("does not suppress a duplicate in-view label outside the wilderness layer", () => {
    const model = localMapModelFor(LOCAL_MAP_SAMPLE);
    const current = model.nodes.find((n) => n.visibility === "current");
    const inViewVisibilities = new Set(["visible_unvisited", "visible_visited"]);
    const duped = {
      ...model,
      nodes: model.nodes.map((n) =>
        inViewVisibilities.has(n.visibility) ? { ...n, label: current.label } : n,
      ),
    };
    const inViewIds = duped.nodes.filter((n) => inViewVisibilities.has(n.visibility)).map((n) => n.id);
    expect(inViewIds.length).toBeGreaterThan(0);
    const w = mountLattice({ localMap: duped });
    for (const id of inViewIds) {
      const label = w.get(`[data-testid="local-map__node--${id}"] .local-map__node-label`);
      expect(label.element.childNodes[label.element.childNodes.length - 1].textContent).toBe(
        current.label,
      );
    }
  });

  it("pairs every legend entry with a dot chip at both scales", () => {
    for (const props of [{}, OVERLAY_PROPS]) {
      const w = mountLattice(props);
      const items = w.findAll('[data-testid^="local-map__legend-item--"]');
      expect(items).toHaveLength(4);
      for (const [i, state] of Object.entries(["current", "visible_unvisited", "visible_visited", "remembered"])) {
        expect(items[Number(i)].find(`.local-map__legend-chip--${state}`).exists()).toBe(true);
      }
      // Non-colour redundancy lives in the chip class pair: visited (solid
      // frame) and remembered (dashed frame) are distinct states.
      expect(items[2].find(".local-map__legend-chip--remembered").exists()).toBe(false);
      expect(items[3].find(".local-map__legend-chip--visible_visited").exists()).toBe(false);
      w.unmount();
    }
  });

  // webclient-map-scale-legend D3: entries beyond the four states are
  // explanatory notes. They render with the neutral info-chip treatment —
  // never a cycled state chip — and their full text label is the primary
  // carrier. A deliberately distinctive note guards against truncation.
  it("renders a fifth beyond-state entry as a neutral info chip, text intact", () => {
    const note = "每格約 10 公里（荒野坐標網格）";
    const w = mountLattice({
      localMap: { ...localMapModelFor(LOCAL_MAP_SAMPLE), legend: [...LEGEND_LABELS_FOR_TEST, note] },
    });
    const items = w.findAll('[data-testid^="local-map__legend-item--"]');
    expect(items).toHaveLength(5);
    // The first four keep their state chip treatments in the fixed order.
    for (const [i, state] of Object.entries(["current", "visible_unvisited", "visible_visited", "remembered"])) {
      expect(items[Number(i)].find(`.local-map__legend-chip--${state}`).exists()).toBe(true);
    }
    const info = items[4];
    expect(info.find(".local-map__legend-chip--info").exists()).toBe(true);
    // The info entry carries no state class at all (never a fifth state).
    for (const state of ["current", "visible_unvisited", "visible_visited", "remembered"]) {
      expect(info.find(`.local-map__legend-chip--${state}`).exists()).toBe(false);
    }
    // The text label renders in full (no truncation of beyond-state notes).
    expect(info.text()).toBe(note);
  });

  it("styles every entry beyond the fourth as info, for any payload", () => {
    const extra = ["附註甲", "附註乙", "附註丙"];
    const w = mountLattice({
      localMap: { ...localMapModelFor(LOCAL_MAP_SAMPLE), legend: [...LEGEND_LABELS_FOR_TEST, ...extra] },
    });
    const items = w.findAll('[data-testid^="local-map__legend-item--"]');
    expect(items).toHaveLength(7);
    extra.forEach((label, offset) => {
      const item = items[4 + offset];
      expect(item.find(".local-map__legend-chip--info").exists()).toBe(true);
      expect(item.text()).toBe(label);
    });
  });
});

describe("LocalMap island chrome (regression for the MapLattice extraction)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountIsland(props = {}) {
    wrapper = mount(LocalMap, {
      props: {
        localMap: localMapModelFor(LOCAL_MAP_SAMPLE),
        ...props,
      },
    });
    return wrapper;
  }

  it("clicking a lattice node forwards the move intent while leaving readout unchanged", async () => {
    const w = mountIsland();
    expect(w.get('[data-testid="local-map-detail"]').text()).toBe("座標 1,2");
    // Activating the unvisited node forwards the move intent.
    await w.get('[data-testid="local-map__node--grid:altoria:2:2"]').trigger("click");
    // Readout remains coordinate-only (webclient-minimap-04-island-single-affordance D3/D6).
    expect(w.get('[data-testid="local-map-detail"]').text()).toBe("座標 1,2");
    // The actionable node also emits move.
    const moved = w.emitted("move");
    expect(moved).toHaveLength(1);
    expect(moved[0][0]).toEqual({
      exit_ref: "e_altoria_1_2_e",
      destination: "grid:altoria:2:2",
    });
  });

  it("clicking a non-actionable node leaves detail line unchanged without a move emit", async () => {
    const w = mountIsland();
    await w.get('[data-testid="local-map__node--grid:altoria:0:2"]').trigger("click");
    expect(w.get('[data-testid="local-map-detail"]').text()).toBe("座標 1,2");
    expect(w.emitted("move")).toBeUndefined();
  });

  it("clicking an edge marker leaves detail line unchanged", async () => {
    const w = mountIsland();
    const edgeMarker = w.get('[data-testid^="local-map__edge-marker--"]');
    await edgeMarker.trigger("click");
    expect(w.get('[data-testid="local-map-detail"]').text()).toBe("座標 1,2");
    expect(w.emitted("move")).toBeUndefined();
  });
});

describe("MapLattice draft lattice fidelity (webclient-minimap-06-draft-lattice-fidelity)", () => {
  let wrapper;
  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
  });

  function mountLattice(props = {}) {
    wrapper = mount(MapLattice, {
      props: {
        localMap: localMapModelFor(LOCAL_MAP_SAMPLE),
        ...props,
      },
    });
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
    maxWidth: 848,
    maxHeight: null,
    fillWidth: true,
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
        maxWidth: 206,
        maxHeight: 296,
        fillWidth: false,
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
    expect(svgWidth).toBeCloseTo(174 + 2 * expectedGutter, 5);
    expect(svgHeight).toBeCloseTo(188 + 2 * expectedGutter, 5);

    const westMarker = wrapper.get('[data-testid="local-map__edge-marker--r:west"]');
    const westText = westMarker.get("text.local-map__edge-marker-name--island");
    // Span on left edge: (188 + 2 * 44.4558) - 2 * 44.4558 = 188.
    // budget = floor(188 / 10) = 18. Label is 11 chars -> fits whole!
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
        maxWidth: 206,
        maxHeight: 296,
        fillWidth: false,
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
        maxWidth: 206,
        maxHeight: 296,
        fillWidth: false,
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
