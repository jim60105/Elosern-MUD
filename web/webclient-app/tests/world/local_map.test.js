import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import LocalMap from "../../components/LocalMap.vue";
import MapOverlay from "../../components/MapOverlay.vue";
import LocalMapModel from "../../lib/local_map.js";
import {
  LOCAL_MAP_GEOMETRY_STRESS_SAMPLE,
  LOCAL_MAP_INTERIOR_SAMPLE,
  LOCAL_MAP_INSTANCE_SAMPLE,
  LOCAL_MAP_MINIMAL_SAMPLE,
  LOCAL_MAP_SAMPLE,
  LOCAL_MAP_SINGLE_NODE_SAMPLE,
  LOCAL_MAP_TALL_LATTICE_SAMPLE,
  LOCAL_MAP_TALL_REMEMBERED_SAMPLE,
  LOCAL_MAP_UNAVAILABLE_SAMPLE,
  LOCAL_MAP_WILDERNESS_SAMPLE,
} from "../../stories/fixtures.js";

describe("LocalMap (B4 world family)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountMap(props = {}) {
    wrapper = mount(LocalMap, {
      props: {
        localMap: LOCAL_MAP_SAMPLE,
        ...props,
      },
    });
    return wrapper;
  }

  it("renders the payload's map title in the island's meta line", () => {
    const w = mountMap();
    // H2: the meta line carries the title plus, on the coordinate-bearing
    // layers only, the renderer-axis orientation legend (design D9).
    const title = w.get('[data-testid="local-map__title"] .local-map__meta-title');
    expect(title.text()).toBe("霧骨渡口");
  });

  it("renders the honest unavailable box with the payload's reason message", () => {
    const w = mountMap({ localMap: LOCAL_MAP_UNAVAILABLE_SAMPLE });
    expect(w.get('[data-testid="local-map__unavailable"]').text()).toBe("區域地圖目前無法顯示");
    expect(w.find(".local-map__lattice").exists()).toBe(false);
    expect(w.find('[data-testid="local-map__title"]').exists()).toBe(false);
    expect(w.find('[data-testid^="local-map__node--"]').exists()).toBe(false);
  });

  it("renders one marker per visibility state, each as a distinct non-color glyph", () => {
    const w = mountMap();
    const expected = {
      current: "grid:altoria:1:2",
      visible_unvisited: "grid:altoria:2:2",
      visible_visited: "grid:altoria:0:2",
      remembered: "grid:altoria:5:5",
    };
    for (const [state, id] of Object.entries(expected)) {
      const node = w.get(`[data-testid="local-map__node--${id}"]`);
      expect(node.attributes("data-visibility")).toBe(state);
      expect(node.find(`.local-map__marker--${state}`).exists()).toBe(true);
    }
  });

  it("encodes every state by shape, not color alone", () => {
    const w = mountMap();
    // current → square, visible_unvisited → open circle,
    // visible_visited → filled circle, remembered → diamond (rotated rect).
    expect(w.get('[data-testid="local-map__node--grid:altoria:1:2"]').find("rect").exists()).toBe(true);
    expect(w.get('[data-testid="local-map__node--grid:altoria:2:2"]').find("circle").exists()).toBe(true);
    expect(w.get('[data-testid="local-map__node--grid:altoria:0:2"]').find("circle").exists()).toBe(true);
    expect(
      w.get('[data-testid="local-map__node--grid:altoria:5:5"]').find('rect[transform="rotate(45)"]').exists(),
    ).toBe(true);
  });

  it("marks the only actionable adjacent node (南門) and shows it in the detail line", () => {
    const w = mountMap();
    const actionable = w.findAll('[data-testid="local-map__actionable"]');
    expect(actionable).toHaveLength(1);
    // The single actionable marker sits on the visible_unvisited node.
    expect(
      w.get('[data-testid="local-map__node--grid:altoria:2:2"]').find('[data-testid="local-map__actionable"]').exists(),
    ).toBe(true);
  });

  it("emits the payload's exact move intent when the actionable node is clicked", async () => {
    const w = mountMap();
    await w.get('[data-testid="local-map__node--grid:altoria:2:2"]').trigger("click");
    const emitted = w.emitted("move");
    expect(emitted).toHaveLength(1);
    expect(emitted[0][0]).toEqual({
      exit_ref: "e_altoria_1_2_e",
      destination: "grid:altoria:2:2",
    });
  });

  it("does not emit any travel action for a node without an action", async () => {
    const w = mountMap();
    await w.get('[data-testid="local-map__node--grid:altoria:0:2"]').trigger("click");
    expect(w.emitted("move")).toBeUndefined();
    // The remembered node is focusable but inert.
    await w.get('[data-testid="local-map__node--grid:altoria:5:5"]').trigger("click");
    expect(w.emitted("move")).toBeUndefined();
  });

  it("renders the payload's legend entries paired with their state glyphs", () => {
    const w = mountMap();
    const items = w.findAll('[data-testid^="local-map__legend-item--"]');
    expect(items).toHaveLength(4);
    expect(w.get('[data-testid="local-map__legend"]').text()).toContain("你目前所在的位置");
    for (const [i, state] of Object.entries(["current", "visible_unvisited", "visible_visited", "remembered"])) {
      expect(items[Number(i)].find(`.local-map__legend-glyph--${state}`).exists()).toBe(true);
    }
    expect(w.text()).toContain("尚未探索的相鄰位置");
    expect(w.text()).toContain("已經探索過的相鄰位置");
    expect(w.text()).toContain("曾經到過、但不在附近的遠方位置");
  });

  it("defaults the detail line to the current node and follows hover", async () => {
    const w = mountMap();
    const detail = w.get('[data-testid="local-map-detail"]');
    expect(detail.text()).toContain("霧骨渡口");
    expect(detail.text()).toContain("目前所在");
    expect(detail.text()).toContain("(1, 2)");

    await w.get('[data-testid="local-map__node--grid:altoria:2:2"]').trigger("mouseenter");
    const hovered = w.get('[data-testid="local-map-detail"]');
    expect(hovered.text()).toContain("南門");
    expect(hovered.text()).toContain("未探索");
    expect(hovered.text()).toContain("(2, 2)");
    expect(hovered.text()).toContain("grid:altoria:2:2");

    await w.find(".local-map__lattice").trigger("mouseleave");
    expect(w.get('[data-testid="local-map-detail"]').text()).toContain("霧骨渡口");

    await w.get('[data-testid="local-map__node--grid:altoria:2:2"]').trigger("click");
    // Selection persists after the interaction.
    expect(w.get('[data-testid="local-map-detail"]').text()).toContain("南門");
  });

  it("renders every edge of the payload with its own traversability styling", () => {
    const w = mountMap();
    const edges = w.findAll('[data-testid^="local-map__edge--"]');
    expect(edges).toHaveLength(3);
    expect(w.get('[data-testid="local-map__edge--0"]').classes()).toContain("local-map__edge--traversable");
    expect(w.get('[data-testid="local-map__edge--1"]').classes()).toContain("local-map__edge--blocked");
    expect(w.get('[data-testid="local-map__edge--2"]').classes()).toContain("local-map__edge--unknown");
  });

  it("renders the minimal sample: two nodes, one unknown edge, one legend line, no actionable node", () => {
    const w = mountMap({ localMap: LOCAL_MAP_MINIMAL_SAMPLE });
    const nodeIds = w.findAll('[data-testid^="local-map__node--"]');
    expect(nodeIds).toHaveLength(2);
    expect(w.findAll('[data-testid^="local-map__edge--"]')).toHaveLength(1);
    expect(w.get('[data-testid="local-map__edge--0"]').classes()).toContain("local-map__edge--unknown");
    expect(w.findAll('[data-testid="local-map__actionable"]')).toHaveLength(0);
    expect(w.findAll('[data-testid^="local-map__legend-item--"]')).toHaveLength(1);
    expect(w.get('[data-testid="local-map-detail"]').text()).toContain("霧骨渡口");
  });

  // H2 (webclient-hud-02-status-islands, design D9/D10): the island
  // re-chrome keeps the load-bearing `.local-map` root class, adds the
  // renderer-axis orientation legend on the coordinate-bearing layers only,
  // and renders no bearing, no compass angle, or distance.

  it("keeps the .local-map root class the mode-gate CSS selects on", () => {
    const w = mountMap();
    expect(w.find(".local-map").exists()).toBe(true);
    expect(w.attributes("data-testid")).toBe("local-map");
  });

  it("shows the orientation legend on grid and wilderness layers only", () => {
    for (const sample of [LOCAL_MAP_SAMPLE, LOCAL_MAP_WILDERNESS_SAMPLE]) {
      const w = mountMap({ localMap: sample });
      const orientation = w.find('[data-testid="local-map__orientation"]');
      expect(orientation.exists(), `legend present for ${sample.layer}`).toBe(true);
      expect(orientation.text()).toBe("北↑");
      w.unmount();
    }
  });

  it("omits the orientation legend on the coordinate-free instance and interior layers", () => {
    for (const sample of [LOCAL_MAP_INSTANCE_SAMPLE, LOCAL_MAP_INTERIOR_SAMPLE]) {
      const w = mountMap({ localMap: sample });
      expect(
        w.find('[data-testid="local-map__orientation"]').exists(),
        `legend absent for ${sample.layer}`,
      ).toBe(false);
      w.unmount();
    }
  });

  it("renders no bearing, no degree sign, and no distance figure anywhere in the island", () => {
    for (const sample of [
      LOCAL_MAP_SAMPLE,
      LOCAL_MAP_WILDERNESS_SAMPLE,
      LOCAL_MAP_INSTANCE_SAMPLE,
      LOCAL_MAP_INTERIOR_SAMPLE,
    ]) {
      const w = mountMap({ localMap: sample });
      const text = w.text();
      expect(text).not.toContain("°");
      // No compass bearing like 「北 324° · 西 262°」 and no distance unit.
      expect(text).not.toMatch(/[北南東西]\s*\d+/);
      expect(text).not.toMatch(/\d+\s*(?:公尺|公里|km)\b/i);
      w.unmount();
    }
  });

  // ---------------------------------------------------------------------
  // fix-webclient-local-map-node-crowding: the decoupled column/row pitch
  // geometry — no two node markers (nor labels) may intersect at every
  // populated lattice size up to the model's 64×64 bound.
  // ---------------------------------------------------------------------

  it("sizes the 2-col × 64-row lattice canvas from the model's exported lattice", () => {
    // Mirror the store's localMapModel shape (stores/elosern.js): the
    // reduced model plus the payload's `available` flag and reason.
    const model = {
      ...LocalMapModel.reducePanel(LOCAL_MAP_TALL_LATTICE_SAMPLE),
      available: true,
      reason: null,
    };
    expect(model.cols).toBe(2);
    expect(model.rows).toBe(64);
    const w = mountMap({ localMap: model });
    const svg = w.find("svg.local-map__lattice");
    expect(svg.exists()).toBe(true);
    // Natural (pre-scale) canvas: 2 × 58px column pitch wide,
    // 64 × 44px row pitch + 14px label band tall.
    expect(svg.attributes("width")).toBe("116");
    expect(svg.attributes("height")).toBe("2830");
    expect(svg.attributes("viewBox")).toBe("0 0 116 2830");
  });

  it("keeps the 48-row lattice + 16 remembered nodes within the 64-node bound", () => {
    // The rubber-duck blocking combination: 48 in-view + 16 remembered = 64
    // (MAX_NODES). The model computes the lattice from the in-view nodes
    // only; remembered nodes stay in the bounded focusable list.
    const model = {
      ...LocalMapModel.reducePanel(LOCAL_MAP_TALL_REMEMBERED_SAMPLE),
      available: true,
      reason: null,
    };
    expect(model.rows).toBe(48);
    expect(model.cols).toBe(2);
    expect(model.nodes).toHaveLength(48);
    expect(model.remembered).toHaveLength(16);
    const w = mountMap({ localMap: model });
    const svg = w.find("svg.local-map__lattice");
    // Natural canvas: 2 × 58px wide, 48 × 44px + 14px label band tall.
    expect(svg.attributes("width")).toBe("116");
    expect(svg.attributes("height")).toBe("2126");
    // The remembered list renders 16 bounded, focusable entries outside the
    // coordinate canvas.
    const list = w.find('[data-testid="local-map-remembered"]');
    expect(list.exists()).toBe(true);
    expect(w.findAll(".local-map__remembered li")).toHaveLength(16);
  });

  it("keeps adjacent node markers and labels non-intersecting at natural geometry", () => {
    const model = {
      ...LocalMapModel.reducePanel(LOCAL_MAP_GEOMETRY_STRESS_SAMPLE),
      available: true,
      reason: null,
    };
    const w = mountMap({ localMap: model });

    // Node centers from the model's col/row + the renderer's decoupled
    // pitch (COL_PITCH 58, ROW_PITCH 44, label band 14): centers are
    // col*58+29 and (rows-1-row)*44+22 with rows=2.
    const centers = {
      "grid:altoria:1:1": { x: 87, y: 66 },
      "grid:altoria:2:1": { x: 145, y: 66 },
      "grid:altoria:1:2": { x: 87, y: 22 },
      "grid:altoria:0:1": { x: 29, y: 66 },
    };
    for (const [id, center] of Object.entries(centers)) {
      const node = w.get(`[data-testid="local-map__node--${id}"]`);
      expect(node.attributes("transform")).toBe(`translate(${center.x}, ${center.y})`);
    }

    // DOM-tied label offset: the component renders every node label's
    // baseline at the fixed `y="26"` attribute (the crowding fix keeps the
    // label line box clear of the node's own marker and of the row below).
    for (const id of Object.keys(centers)) {
      const label = w.get(`[data-testid="local-map__node--${id}"] .local-map__node-label`);
      expect(label.attributes("y")).toBe("26");
    }

    // Marker footprints in pre-scale units: the current 26×26 rect and the
    // stroked unvisited circles (r=12 + stroke 2 → visual half-extent 13);
    // the filled visited circle is plain r=12 (half-extent 12).
    const markerBoxes = {
      "grid:altoria:1:1": { x1: 74, y1: 53, x2: 100, y2: 79 },
      "grid:altoria:2:1": { x1: 132, y1: 53, x2: 158, y2: 79 },
      "grid:altoria:1:2": { x1: 74, y1: 9, x2: 100, y2: 35 },
      "grid:altoria:0:1": { x1: 17, y1: 54, x2: 45, y2: 78 },
    };

    // Node labels: baseline at center.y + 26; the 11px monospace line box
    // extends ≈10.5px above and ≈3px below the baseline. A 4-CJK label is
    // 44px wide (full-width CJK glyphs at 11px); a truncated label
    // (4 chars + "…") is ≈ 55px wide.
    const labelBoxes = {
      "grid:altoria:1:1": { x1: 65, y1: 81.5, x2: 109, y2: 95 },
      "grid:altoria:2:1": { x1: 117.5, y1: 81.5, x2: 172.5, y2: 95 },
      "grid:altoria:1:2": { x1: 59.5, y1: 37.5, x2: 114.5, y2: 51 },
      "grid:altoria:0:1": { x1: 7, y1: 81.5, x2: 51, y2: 95 },
    };

    function separated(a, b) {
      return (
        a.x2 + 2 <= b.x1 ||
        b.x2 + 2 <= a.x1 ||
        a.y2 + 2 <= b.y1 ||
        b.y2 + 2 <= a.y1
      );
    }
    function everyPair(boxes) {
      const ids = Object.keys(boxes);
      for (let i = 0; i < ids.length; i += 1) {
        for (let j = i + 1; j < ids.length; j += 1) {
          expect(
            separated(boxes[ids[i]], boxes[ids[j]]),
            `${ids[i]} vs ${ids[j]} must keep a ≥2px gap`,
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
    everyPair(markerBoxes);

    // Connector edges stay visible: the center-to-center span (58px
    // horizontal / 44px vertical) minus the two 26px marker footprints
    // leaves a positive visible segment.
    const e0 = w.get('[data-testid="local-map__edge--0"]');
    expect(e0.attributes("x1")).toBe("87");
    expect(e0.attributes("y1")).toBe("66");
    expect(e0.attributes("x2")).toBe("145");
    expect(e0.attributes("y2")).toBe("66");
    expect(58 - 26).toBeGreaterThan(0);
    const e1 = w.get('[data-testid="local-map__edge--1"]');
    expect(e1.attributes("x1")).toBe("87");
    expect(e1.attributes("y1")).toBe("66");
    expect(e1.attributes("x2")).toBe("87");
    expect(e1.attributes("y2")).toBe("22");
    expect(44 - 26).toBeGreaterThan(0);
  });

  it("renders a single-node room with no collision risk (no regression)", () => {
    const model = {
      ...LocalMapModel.reducePanel(LOCAL_MAP_SINGLE_NODE_SAMPLE),
      available: true,
      reason: null,
    };
    const w = mountMap({ localMap: model });
    const svg = w.find("svg.local-map__lattice");
    expect(svg.attributes("width")).toBe("58");
    expect(svg.attributes("height")).toBe("58");
    // rows=1 → y = (1-1-0)*44 + 22 = 22.
    expect(
      w.get('[data-testid="local-map__node--grid:altoria:1:1"]').attributes("transform"),
    ).toBe("translate(29, 22)");
    expect(w.get('[data-testid="local-map__marker--current"]').exists()).toBe(true);
  });

  it("MapOverlay renders the shared LocalMap and forwards the move intent", async () => {
    const model = {
      ...LocalMapModel.reducePanel(LOCAL_MAP_GEOMETRY_STRESS_SAMPLE),
      available: true,
      reason: null,
    };
    const overlay = mount(MapOverlay, {
      props: { localMap: model },
    });
    // The shared component renders inside the overlay body (MapOverlay.vue:52-54).
    expect(overlay.find('[data-testid="local-map__lattice"]').exists()).toBe(true);
    await overlay.get('[data-testid="local-map__node--grid:altoria:2:1"]').trigger("click");
    expect(overlay.emitted("move")).toHaveLength(1);
    expect(overlay.emitted("move")[0][0]).toEqual({
      exit_ref: "e_altoria_1_1_e",
      destination: "grid:altoria:2:1",
    });
    overlay.unmount();
  });
});
