import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import LocalMap from "../../components/LocalMap.vue";
import MapOverlay from "../../components/MapOverlay.vue";
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
  localMapModelFor,
} from "../../stories/fixtures.js";

describe("LocalMap (B4 world family)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountMap(props = {}) {
    // Wave 0 (webclient-map-00-story-fidelity): mounts use the shared
    // derived-shape helper so they exercise the EXACT prop shape the store
    // passes in production, not the raw payload.
    wrapper = mount(LocalMap, {
      props: {
        localMap: localMapModelFor(LOCAL_MAP_SAMPLE),
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
    const w = mountMap({ localMap: localMapModelFor(LOCAL_MAP_UNAVAILABLE_SAMPLE) });
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
    // Draft marker ladder (webclient-map-01-draft-chrome design D2):
    // current → filled seal circle (with the seal-light ring),
    // visible_unvisited → open circle, visible_visited → filled ink circle,
    // remembered → diamond (rotated rect).
    expect(
      w.get('[data-testid="local-map__node--grid:altoria:1:2"]').find("circle.local-map__marker--current").exists(),
    ).toBe(true);
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

  it("selects the focused remembered list item without emitting a travel action", async () => {
    // Wave 0 (task 3.2 contract, pinned in jsdom): the FocusedRemembered
    // story's named state is real keyboard focus — a genuine focus() only
    // lands because the `li` is tabindex=0, and its @focus handler selects
    // the node. A click-triggered test cannot mask a broken tabindex/@focus
    // wiring here.
    wrapper = mount(LocalMap, {
      props: { localMap: localMapModelFor(LOCAL_MAP_SAMPLE) },
      attachTo: document.body,
    });
    const li = wrapper.get('[data-testid="local-map__node--grid:altoria:5:5"]').element;
    li.focus();
    await wrapper.vm.$nextTick();
    expect(document.activeElement).toBe(li);
    const detail = wrapper.get('[data-testid="local-map-detail"]').text();
    expect(detail).toContain("舊街區");
    expect(detail).toContain("已探索");
    expect(detail).not.toContain("→");
    expect(wrapper.emitted("move")).toBeUndefined();
  });

  it("renders the payload's legend entries paired with their state chips", () => {
    const w = mountMap();
    const items = w.findAll('[data-testid^="local-map__legend-item--"]');
    expect(items).toHaveLength(4);
    expect(w.get('[data-testid="local-map__legend"]').text()).toContain("你目前所在的位置");
    // Draft dot-chips (design D2): every entry carries its state chip, and
    // visited vs remembered are distinguished by the chip's border style
    // (solid gold frame vs dashed gold frame) — not by the label text.
    for (const [i, state] of Object.entries(["current", "visible_unvisited", "visible_visited", "remembered"])) {
      expect(items[Number(i)].find(`.local-map__legend-chip--${state}`).exists()).toBe(true);
    }
    expect(
      items[2].find(".local-map__legend-chip--visible_visited").classes(),
    ).not.toContain("local-map__legend-chip--remembered");
    expect(w.text()).toContain("尚未探索的相鄰位置");
    expect(w.text()).toContain("已經探索過的相鄰位置");
    expect(w.text()).toContain("曾經到過、但不在附近的遠方位置");
  });

  it("defaults the detail line to the current node and follows hover", async () => {
    const w = mountMap();
    const detail = w.get('[data-testid="local-map-detail"]');
    expect(detail.text()).toContain("霧骨渡口");
    expect(detail.text()).toContain("目前所在");
    // map-02 design D3: the detail line never shows raw world-coordinate
    // numbers — the radial variant makes them meaningless, and they were
    // never a reading path on either variant.
    expect(detail.text()).not.toContain("(1, 2)");

    await w.get('[data-testid="local-map__node--grid:altoria:2:2"]').trigger("mouseenter");
    const hovered = w.get('[data-testid="local-map-detail"]');
    expect(hovered.text()).toContain("南門");
    expect(hovered.text()).toContain("未探索");
    expect(hovered.text()).not.toContain("(2, 2)");
    expect(hovered.text()).toContain("grid:altoria:2:2");

    await w.find(".local-map__lattice").trigger("mouseleave");
    expect(w.get('[data-testid="local-map-detail"]').text()).toContain("霧骨渡口");

    await w.get('[data-testid="local-map__node--grid:altoria:2:2"]').trigger("click");
    // Selection persists after the interaction.
    expect(w.get('[data-testid="local-map-detail"]').text()).toContain("南門");
  });

  it("renders the on-canvas edges with their traversability styling and omits the off-canvas one", () => {
    const w = mountMap();
    // The derived model splits `remembered` off the canvas, so the payload's
    // third edge (current → the remembered 舊街區) has an off-canvas endpoint
    // and is omitted from the drawn layer (the local-map spec's edge rule).
    const edges = w.findAll('[data-testid^="local-map__edge--"]');
    expect(edges).toHaveLength(2);
    expect(w.get('[data-testid="local-map__edge--0"]').classes()).toContain("local-map__edge--traversable");
    expect(w.get('[data-testid="local-map__edge--1"]').classes()).toContain("local-map__edge--blocked");
    expect(w.find('[data-testid="local-map__edge--2"]').exists()).toBe(false);
  });

  it("renders the minimal sample: two nodes, one unknown edge, one legend line, no actionable node", () => {
    const w = mountMap({ localMap: localMapModelFor(LOCAL_MAP_MINIMAL_SAMPLE) });
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
      const w = mountMap({ localMap: localMapModelFor(sample) });
      const orientation = w.find('[data-testid="local-map__orientation"]');
      expect(orientation.exists(), `legend present for ${sample.layer}`).toBe(true);
      // The draft header pair (webclient-map-01-draft-chrome D5): the axis
      // marks name both readable directions; it carries no bearing or
      // distance (the no-bearing assertions below still bind).
      expect(orientation.text()).toBe("北↑ 東→");
      w.unmount();
    }
  });

  it("omits the orientation legend on the coordinate-free instance and interior layers", () => {
    for (const sample of [LOCAL_MAP_INSTANCE_SAMPLE, LOCAL_MAP_INTERIOR_SAMPLE]) {
      const w = mountMap({ localMap: localMapModelFor(sample) });
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
      const w = mountMap({ localMap: localMapModelFor(sample) });
      const text = w.text();
      expect(text).not.toContain("°");
      // No compass bearing like 「北 324° · 西 262°」 and no distance unit.
      expect(text).not.toMatch(/[北南東西]\s*\d+/);
      expect(text).not.toMatch(/\d+\s*(?:公尺|公里|km)\b/i);
      w.unmount();
    }
  });

  // ---------------------------------------------------------------------
  // webclient-map-01-draft-chrome (design D5): the draft's whole-island
  // click-to-open affordance, scoped to the island body — the meta-row
  // trigger, the lattice nodes, and the remembered list keep their own
  // behaviour and must never also emit `open-map`.
  // ---------------------------------------------------------------------

  it("emits open-map when the island body (a non-interactive spot) is clicked", async () => {
    const w = mountMap();
    // The island's detail line is plain text — a body click target.
    await w.get('[data-testid="local-map-detail"]').trigger("click");
    const emitted = w.emitted("open-map");
    expect(emitted).toHaveLength(1);
  });

  it("clicking an interactive descendant does not also emit open-map", async () => {
    const w = mountMap();
    // The meta-row trigger itself (a <button>) — the click guard skips it.
    await w.get('[data-testid="local-map__expand"]').trigger("click");
    expect(w.emitted("open-map")).toHaveLength(1); // only the button's own emit
    // A lattice node's own click (the <g data-node>) never bubbles into the
    // island-wide open.
    await w.get('[data-testid="local-map__node--grid:altoria:0:2"]').trigger("click");
    expect(w.emitted("open-map")).toHaveLength(1);
    // Clicking a node's interior descendant (the marker circle — the actual
    // DOM click target) must behave identically to clicking the group.
    await w
      .get('[data-testid="local-map__node--grid:altoria:0:2"] circle.local-map__marker--visible_visited')
      .trigger("click");
    expect(w.emitted("open-map")).toHaveLength(1);
    // A remembered-list item click selects the node without opening.
    await w.get('[data-testid="local-map-remembered"] li').trigger("click");
    expect(w.emitted("open-map")).toHaveLength(1);
    expect(w.emitted("move")).toBeUndefined();
  });

  it("keeps the island root non-interactive (no role, no tabindex)", () => {
    const w = mountMap();
    expect(w.attributes("role")).toBeUndefined();
    expect(w.attributes("tabindex")).toBeUndefined();
  });

  it("does not emit open-map from the unavailable island", async () => {
    const w = mountMap({ localMap: localMapModelFor(LOCAL_MAP_UNAVAILABLE_SAMPLE) });
    await w.get('[data-testid="local-map__unavailable"]').trigger("click");
    expect(w.emitted("open-map")).toBeUndefined();
  });

  // ---------------------------------------------------------------------
  // fix-webclient-local-map-node-crowding: the decoupled column/row pitch
  // geometry — no two node markers (nor labels) may intersect at every
  // populated lattice size up to the model's 64×64 bound.
  // ---------------------------------------------------------------------

  it("sizes the 2-col × 64-row lattice canvas from the model's exported lattice", () => {
    // The shared helper mirrors the store's localMapModel construction
    // (stores/elosern.js): the reduced model plus the payload's `available`
    // flag and reason.
    const model = localMapModelFor(LOCAL_MAP_TALL_LATTICE_SAMPLE);
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
    // Wave 0 (task 3.3): the scale-down CONTRACT jsdom can prove — the
    // island's caps bind as inline styles so a real browser scales the
    // canvas (2830px natural height cannot overflow the island). The
    // rendered proportional size is verified in the running Storybook
    // (World/LocalMap — TallLatticeScaled), not here.
    const style = svg.attributes("style") ?? "";
    expect(style).toContain("max-width: 206px");
    expect(style).toContain("max-height: 296px");
  });

  it("keeps the 48-row lattice + 16 remembered nodes within the 64-node bound", () => {
    // The rubber-duck blocking combination: 48 in-view + 16 remembered = 64
    // (MAX_NODES). The model computes the lattice from the in-view nodes
    // only; remembered nodes stay in the bounded focusable list.
    const model = localMapModelFor(LOCAL_MAP_TALL_REMEMBERED_SAMPLE);
    expect(model.rows).toBe(48);
    expect(model.cols).toBe(2);
    expect(model.nodes).toHaveLength(48);
    expect(model.remembered).toHaveLength(16);
    const w = mountMap({ localMap: model });
    const svg = w.find("svg.local-map__lattice");
    // Natural canvas: 2 × 58px wide, 48 × 44px + 14px label band tall,
    // grown by the edge-marker gutter (model value 75: the 16 remembered
    // remotes fan out along the top and right edges, and the right edge's
    // slot packing drives the need beyond the 26.46 minimum) — map-02 D3b.
    expect(svg.attributes("width")).toBe("266");
    expect(svg.attributes("height")).toBe("2276");
    // The remembered list renders 16 bounded, focusable entries outside the
    // coordinate canvas.
    const list = w.find('[data-testid="local-map-remembered"]');
    expect(list.exists()).toBe(true);
    expect(w.findAll(".local-map__remembered li")).toHaveLength(16);
  });

  it("keeps adjacent node markers and labels non-intersecting at natural geometry", () => {
    const model = localMapModelFor(LOCAL_MAP_GEOMETRY_STRESS_SAMPLE);
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

    // Marker footprints in pre-scale units (draft ladder,
    // webclient-map-01-draft-chrome D2): the current seal circle is r=8 with
    // stroke 2 → half-extent 9; the stroked unvisited hollow dot is r=4.5 +
    // stroke 2 → half-extent 5.5; the filled visited ink dot is r=4.5 +
    // stroke 1 → half-extent 5. The gold landmark ring on the current node
    // (r=5) is a same-node decoration inside the seal circle's footprint.
    const markerBoxes = {
      "grid:altoria:1:1": { x1: 78, y1: 57, x2: 96, y2: 75 },
      "grid:altoria:2:1": { x1: 139.5, y1: 60.5, x2: 150.5, y2: 71.5 },
      "grid:altoria:1:2": { x1: 81.5, y1: 16.5, x2: 92.5, y2: 27.5 },
      "grid:altoria:0:1": { x1: 24, y1: 61, x2: 34, y2: 71 },
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
    // horizontal / 44px vertical) minus the two scaled marker footprints
    // (current half 9, unvisited half 5.5) leaves a positive visible
    // segment.
    const e0 = w.get('[data-testid="local-map__edge--0"]');
    expect(e0.attributes("x1")).toBe("87");
    expect(e0.attributes("y1")).toBe("66");
    expect(e0.attributes("x2")).toBe("145");
    expect(e0.attributes("y2")).toBe("66");
    expect(58 - 9 - 5.5).toBeGreaterThan(0);
    const e1 = w.get('[data-testid="local-map__edge--1"]');
    expect(e1.attributes("x1")).toBe("87");
    expect(e1.attributes("y1")).toBe("66");
    expect(e1.attributes("x2")).toBe("87");
    expect(e1.attributes("y2")).toBe("22");
    expect(44 - 9 - 5.5).toBeGreaterThan(0);
  });

  it("renders a single-node room with no collision risk (no regression)", () => {
    const model = localMapModelFor(LOCAL_MAP_SINGLE_NODE_SAMPLE);
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
    const model = localMapModelFor(LOCAL_MAP_GEOMETRY_STRESS_SAMPLE);
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
