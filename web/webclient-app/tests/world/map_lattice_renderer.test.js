import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import MapLattice from "../../components/MapLattice.vue";
import LocalMapModel from "../../lib/local_map.js";
import {
  LOCAL_MAP_SAMPLE,
  LOCAL_MAP_WILDERNESS_SAMPLE,
  localMapModelFor,
} from "../../stories/fixtures.js";
import {
  OVERLAY_PROPS,
  mountLattice as mountLatticeShared,
} from "./map_lattice_support.js";

// The shared lattice renderer (improve-webclient-map-overlay-scale):
// scale parity, non-intersection geometry, node events, overlay chrome,
// and the pin. Split sibling of the original map_lattice.test.js; shared
// fixtures live in ./map_lattice_support.js.

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
    // webclient-full-map-fit-view D6: an overlay-scale mount without
    // fitView draws at the canvas's natural size — no inline style at all
    // (the legend moved to the overlay's popover, so none renders here).
    expect(svg.element.style.cssText).toBe("");
    // At the overlay's scale the marker carries its place name and an
    // accessible name (the overlay has no remembered list).
    const edgeMarker = w.get('[data-testid="local-map__edge-marker--grid:altoria:5:5"]');
    expect(edgeMarker.attributes("aria-hidden")).toBeUndefined();
    expect(edgeMarker.attributes("aria-label")).toBe("舊街區");
    expect(edgeMarker.find("text").text()).toBe("舊街區");
  });

  // webclient-full-map-fit-view D1/D4: with fitView the SVG fills its
  // clipped viewport and its viewBox is the view window. Before any layout
  // (jsdom measures no viewport box) the view is null and the window is the
  // whole canvas, which under `meet` is also a fitted rendering.
  it("fitView fills its viewport and windows the whole canvas before layout", () => {
    const w = mountLattice({ ...OVERLAY_PROPS, fitView: true });
    const svg = w.get("svg.local-map__lattice");
    expect(svg.element.style.width).toBe("100%");
    expect(svg.element.style.height).toBe("100%");
    const W = Number(svg.attributes("width"));
    const H = Number(svg.attributes("height"));
    expect(svg.attributes("viewBox")).toBe(`0 0 ${W} ${H}`);
    expect(w.get(".local-map__viewport").classes()).toContain("local-map__viewport--fit");
  });

  // webclient-full-map-fit-view D3: a primary-button drag past the
  // threshold pans the view and its trailing click is suppressed, so a
  // drag that ends on a node never submits that node's move. A press that
  // stays within the threshold is an ordinary click and still moves.
  it("a drag past the threshold never emits move", async () => {
    const w = mountLattice({ ...OVERLAY_PROPS, fitView: true });
    const node = w.get('[data-testid="local-map__node--grid:altoria:2:2"]');
    await node.trigger("pointerdown", { button: 0, pointerId: 1, clientX: 100, clientY: 100 });
    await node.trigger("pointermove", { pointerId: 1, clientX: 112, clientY: 100 });
    await node.trigger("pointerup", { pointerId: 1, clientX: 112, clientY: 100 });
    await node.trigger("click");
    expect(w.emitted("move")).toBeUndefined();

    await node.trigger("pointerdown", { button: 0, pointerId: 2, clientX: 100, clientY: 100 });
    await node.trigger("pointermove", { pointerId: 2, clientX: 102, clientY: 100 });
    await node.trigger("pointerup", { pointerId: 2, clientX: 102, clientY: 100 });
    await node.trigger("click");
    expect(w.emitted("move")).toHaveLength(1);
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
});
