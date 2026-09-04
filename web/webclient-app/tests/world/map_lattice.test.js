import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import LocalMap from "../../components/LocalMap.vue";
import MapLattice from "../../components/MapLattice.vue";
import LocalMapModel from "../../lib/local_map.js";
import {
  LOCAL_MAP_SAMPLE,
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

describe("MapLattice (B4 world family, shared renderer)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
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

  it("clicking or focusing a remembered-list node leaves detail line unchanged", async () => {
    const w = mountIsland();
    const rememberedItem = w.get('[data-testid="local-map-remembered"] li');
    await rememberedItem.trigger("click");
    expect(w.get('[data-testid="local-map-detail"]').text()).toBe("座標 1,2");
    expect(w.emitted("move")).toBeUndefined();
  });
});
