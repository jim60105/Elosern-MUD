import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import LocalMap from "../../components/LocalMap.vue";
import MapLattice from "../../components/MapLattice.vue";
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
  };

  it("renders identical node/edge/legend content at the island's default scale", () => {
    const w = mountLattice();
    // The grid fixture's in-view lattice: 3 cols × 1 row.
    const svg = w.find("svg.local-map__lattice");
    expect(svg.attributes("width")).toBe("174");
    expect(svg.attributes("height")).toBe("58");
    expect(w.findAll('[data-testid^="local-map__node--"]').length).toBe(3);
    // The payload lists 3 edges, but the third one ends at the remembered
    // node (grid:altoria:5:5), whose endpoint is not on the canvas — the
    // renderer omits it per the spec's edge-omission rule, so 2 edges draw.
    expect(w.findAll('[data-testid^="local-map__edge--"]').length).toBe(2);
    expect(w.findAll('[data-testid^="local-map__legend-item--"]').length).toBe(4);
    expect(w.get('[data-testid="local-map__marker--current"]').exists()).toBe(true);
  });

  it("renders identical node/edge/legend content at the overlay's larger scale", () => {
    const w = mountLattice(OVERLAY_PROPS);
    const svg = w.find("svg.local-map__lattice");
    // 3 × 280px column pitch wide, 1 × 212px row pitch + 14px label band.
    expect(svg.attributes("width")).toBe("840");
    expect(svg.attributes("height")).toBe("226");
    expect(w.findAll('[data-testid^="local-map__node--"]').length).toBe(3);
    expect(w.findAll('[data-testid^="local-map__edge--"]').length).toBe(2);
    expect(w.findAll('[data-testid^="local-map__legend-item--"]').length).toBe(4);
    // The fill-width variant renders the canvas at the body's available
    // width (848px content box) with no height cap.
    const style = svg.element.style;
    expect(style.width).toBe("100%");
    expect(style.maxWidth).toBe("848px");
    expect(style.maxHeight).toBe("");
  });

  it("keeps node markers and labels non-intersecting at the overlay's scale", () => {
    const w = mountLattice(OVERLAY_PROPS);

    // Node centers from the model's col/row + the overlay's pitch
    // (colPitch 280, rowPitch 212, rows=1): centers are col*280+140 and
    // (1-1-row)*212+106.
    const centers = {
      "grid:altoria:1:2": { x: 420, y: 106 },
      "grid:altoria:2:2": { x: 700, y: 106 },
      "grid:altoria:0:2": { x: 140, y: 106 },
    };
    for (const [id, center] of Object.entries(centers)) {
      const node = w.get(`[data-testid="local-map__node--${id}"]`);
      expect(node.attributes("transform")).toBe(`translate(${center.x}, ${center.y})`);
    }

    // Marker footprints in pre-scale units at markerScale 4.83: the current
    // 26×26 rect scales to a ±62.8px half-extent; the stroked circles (r=12
    // + 2px stroke) scale to a ±59px visual half-extent.
    const CURRENT_HALF = 13 * 4.83;
    const CIRCLE_VISUAL_HALF = 12 * 4.83 + 1;
    const markerBoxes = {
      "grid:altoria:1:2": { x1: 420 - CURRENT_HALF, y1: 106 - CURRENT_HALF, x2: 420 + CURRENT_HALF, y2: 106 + CURRENT_HALF },
      "grid:altoria:2:2": { x1: 700 - CIRCLE_VISUAL_HALF, y1: 106 - CIRCLE_VISUAL_HALF, x2: 700 + CIRCLE_VISUAL_HALF, y2: 106 + CIRCLE_VISUAL_HALF },
      "grid:altoria:0:2": { x1: 140 - CIRCLE_VISUAL_HALF, y1: 106 - CIRCLE_VISUAL_HALF, x2: 140 + CIRCLE_VISUAL_HALF, y2: 106 + CIRCLE_VISUAL_HALF },
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
    // horizontal / 212px vertical) minus the two 26px-marker-scaled
    // footprints leaves a positive visible segment.
    const e0 = w.get('[data-testid="local-map__edge--0"]');
    expect(e0.attributes("x1")).toBe("420");
    expect(e0.attributes("y1")).toBe("106");
    expect(e0.attributes("x2")).toBe("700");
    expect(e0.attributes("y2")).toBe("106");
    expect(280 - 26 * 4.83).toBeGreaterThan(0);
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

  it("clicking a lattice node updates the shared detail line through the select event", async () => {
    const w = mountIsland();
    expect(w.get('[data-testid="local-map-detail"]').text()).toContain("霧骨渡口");
    // Activating the unvisited node (the lattice's select event drives the
    // island's selection state).
    await w.get('[data-testid="local-map__node--grid:altoria:2:2"]').trigger("click");
    const detail = w.get('[data-testid="local-map-detail"]');
    expect(detail.text()).toContain("南門");
    expect(detail.text()).toContain("未探索");
    // The actionable node also emits move.
    const moved = w.emitted("move");
    expect(moved).toHaveLength(1);
    expect(moved[0][0]).toEqual({
      exit_ref: "e_altoria_1_2_e",
      destination: "grid:altoria:2:2",
    });
  });

  it("clicking a non-actionable node updates the detail line without a move emit", async () => {
    const w = mountIsland();
    await w.get('[data-testid="local-map__node--grid:altoria:0:2"]').trigger("click");
    const detail = w.get('[data-testid="local-map-detail"]');
    expect(detail.text()).toContain("碼頭");
    expect(detail.text()).toContain("已探索");
    expect(w.emitted("move")).toBeUndefined();
  });

  it("clicking or focusing a remembered-list node updates the detail line", async () => {
    const w = mountIsland();
    const rememberedItem = w.get('[data-testid="local-map-remembered"] li');
    await rememberedItem.trigger("click");
    const detail = w.get('[data-testid="local-map-detail"]');
    expect(detail.text()).toContain("舊街區");
    expect(detail.text()).toContain("已探索");
    expect(w.emitted("move")).toBeUndefined();
  });
});
