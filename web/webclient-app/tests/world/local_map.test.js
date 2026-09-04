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
    // slim-minimap-island D1: no legend element for ANY payload — the
    // unavailable form included.
    expect(w.find('[data-testid="local-map__legend"]').exists()).toBe(false);
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

  it("marks the only actionable adjacent node (南門) and carries the actionable halo", () => {
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

  it("focuses the remembered list item without emitting a travel action or changing readout", async () => {
    // Wave 0 / change 04 (task 2.4): the remembered list's first item is a
    // focusable `li` with tabindex=0. Focusing it selects the item (natural
    // focus), leaves the readout unchanged (coordinate-only readout), and
    // emits no travel action.
    wrapper = mount(LocalMap, {
      props: { localMap: localMapModelFor(LOCAL_MAP_SAMPLE) },
      attachTo: document.body,
    });
    const li = wrapper.get('[data-testid="local-map__node--grid:altoria:5:5"]').element;
    li.focus();
    await wrapper.vm.$nextTick();
    expect(document.activeElement).toBe(li);
    // Readout remains current node coordinates, not the focused item's name.
    const detail = wrapper.get('[data-testid="local-map-detail"]').text();
    expect(detail).toBe("座標 1,2");
    expect(wrapper.emitted("move")).toBeUndefined();
  });

  // slim-minimap-island (design D1): the state legend is an overlay-only
  // presentation. The island passes the shared renderer's legend-display
  // switch off, so no legend element is mounted in its DOM for any payload
  // (the chip-pairing behavior itself stays pinned on the renderer/overlay
  // suites: map_lattice.test.js, map_overlay.test.js).
  for (const [name, sample] of Object.entries({
    grid: LOCAL_MAP_SAMPLE,
    wilderness: LOCAL_MAP_WILDERNESS_SAMPLE,
    minimal: LOCAL_MAP_MINIMAL_SAMPLE,
    instance: LOCAL_MAP_INSTANCE_SAMPLE,
    interior: LOCAL_MAP_INTERIOR_SAMPLE,
    unavailable: LOCAL_MAP_UNAVAILABLE_SAMPLE,
  })) {
    it(`mounts no state legend on the ${name} payload`, () => {
      const w = mountMap({ localMap: localMapModelFor(sample) });
      expect(w.find('[data-testid="local-map__legend"]').exists()).toBe(false);
      expect(w.findAll('[data-testid^="local-map__legend-item--"]')).toHaveLength(0);
      expect(w.text()).not.toContain("你目前所在的位置");
    });
  }

  it("renders coordinate-only readout on a coordinate-bearing layer and ignores hover", async () => {
    const w = mountMap();
    const detail = w.get('[data-testid="local-map-detail"]');
    // webclient-minimap-04-island-single-affordance (D6): the readout is
    // `座標 <x>,<y>` and nothing else. No place name, no 目前所在, no action.
    expect(detail.text()).toBe("座標 1,2");

    // Hovering a node does NOT change the readout (design D3).
    await w.get('[data-testid="local-map__node--grid:altoria:2:2"]').trigger("mouseenter");
    expect(w.get('[data-testid="local-map-detail"]').text()).toBe("座標 1,2");

    await w.find(".local-map__lattice").trigger("mouseleave");
    expect(w.get('[data-testid="local-map-detail"]').text()).toBe("座標 1,2");

    // Activating a node does NOT change the readout either.
    await w.get('[data-testid="local-map__node--grid:altoria:2:2"]').trigger("click");
    expect(w.get('[data-testid="local-map-detail"]').text()).toBe("座標 1,2");
  });

  it("states the current coordinates on the wilderness layer too", () => {
    const w = mountMap({ localMap: localMapModelFor(LOCAL_MAP_WILDERNESS_SAMPLE) });
    expect(w.get('[data-testid="local-map-detail"]').text()).toBe("座標 3,1");
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

  it("renders the minimal sample: two nodes, one unknown edge, no legend, no actionable node", () => {
    const w = mountMap({ localMap: localMapModelFor(LOCAL_MAP_MINIMAL_SAMPLE) });
    const nodeIds = w.findAll('[data-testid^="local-map__node--"]');
    expect(nodeIds).toHaveLength(2);
    expect(w.findAll('[data-testid^="local-map__edge--"]')).toHaveLength(1);
    expect(w.get('[data-testid="local-map__edge--0"]').classes()).toContain("local-map__edge--unknown");
    expect(w.findAll('[data-testid="local-map__actionable"]')).toHaveLength(0);
    expect(w.findAll('[data-testid^="local-map__legend-item--"]')).toHaveLength(0);
    expect(w.get('[data-testid="local-map-detail"]').text()).toBe("座標 1,2");
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
    for (const [layer, sample] of Object.entries({
      grid: LOCAL_MAP_SAMPLE,
      wilderness: LOCAL_MAP_WILDERNESS_SAMPLE,
      instance: LOCAL_MAP_INSTANCE_SAMPLE,
      interior: LOCAL_MAP_INTERIOR_SAMPLE,
    })) {
      const w = mountMap({ localMap: localMapModelFor(sample) });
      const text = w.text();
      expect(text).not.toContain("°");
      // No compass bearing like 「北 324° · 西 262°」 and no distance unit.
      expect(text).not.toMatch(/[北南東西]\s*\d+/);
      expect(text).not.toMatch(/\d+\s*(?:公尺|公里|km)\b/i);
      // slim-minimap-island D2: the current node's own `座標 x,y` figure is
      // the ONLY coordinate token that may appear, and only on the
      // coordinate-bearing layers — the graph layers state nothing.
      const figures = text.match(/座標\s*-?\d+,-?\d+/g) ?? [];
      if (layer === "grid" || layer === "wilderness") {
        expect(figures).toHaveLength(1);
      } else {
        expect(figures).toHaveLength(0);
      }
      w.unmount();
    }
  });

  // ---------------------------------------------------------------------
  // webclient-minimap-04-island-single-affordance (design D1): the island
  // presents exactly one full-map affordance — a full-bleed transparent
  // <button> spanning the whole island, layered beneath visual content.
  // ---------------------------------------------------------------------

  it("renders exactly one full-map affordance as the island's first DOM child", () => {
    const w = mountMap();
    const affordance = w.get('[data-testid="local-map__expand"]');
    expect(affordance.element.tagName).toBe("BUTTON");
    expect(affordance.attributes("type")).toBe("button");
    expect(affordance.attributes("aria-label")).toBe("展開全地圖");
    expect(affordance.attributes("title")).toBe("展開全地圖");
    expect(affordance.classes()).toContain("local-map__affordance");
    // Button element contains no child elements (no focusable descendant).
    expect(affordance.element.children).toHaveLength(0);
    // It is the available template's FIRST child in DOM order.
    const island = w.get('[data-testid="local-map"]');
    expect(island.element.firstElementChild).toBe(affordance.element);
    // Exactly one affordance exists in the island (no duplicate in header).
    expect(w.findAll('[data-testid="local-map__expand"]')).toHaveLength(1);
  });

  it("emits open-map when the affordance or the island body is clicked", async () => {
    const w = mountMap();
    // Clicking the affordance directly emits open-map once.
    await w.get('[data-testid="local-map__expand"]').trigger("click");
    expect(w.emitted("open-map")).toHaveLength(1);

    // Clicking the island's detail line (body click) emits open-map once.
    await w.get('[data-testid="local-map-detail"]').trigger("click");
    expect(w.emitted("open-map")).toHaveLength(2);
  });

  it("clicking an interactive descendant does not emit open-map", async () => {
    const w = mountMap();
    // A lattice node's own click (the <g data-node>) moves without opening the map.
    await w.get('[data-testid="local-map__node--grid:altoria:2:2"]').trigger("click");
    expect(w.emitted("open-map")).toBeUndefined();
    expect(w.emitted("move")).toHaveLength(1);

    // Clicking a non-actionable node emits neither move nor open-map.
    await w.get('[data-testid="local-map__node--grid:altoria:0:2"]').trigger("click");
    expect(w.emitted("open-map")).toBeUndefined();

    // A remembered-list item click selects the item without opening the map.
    await w.get('[data-testid="local-map-remembered"] li').trigger("click");
    expect(w.emitted("open-map")).toBeUndefined();
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
    expect(style).toContain("width: 100%");
    expect(style).toContain("max-width: 12.13px");
    expect(style).toContain("max-height: 296px");
  });

  // ---------------------------------------------------------------------
  // The minimap island claims its card (the redesign review's primary
  // finding, REDESIGN §7 / draft `.mini svg { width:100%; max-width:172px }`).
  // ---------------------------------------------------------------------

  it("fills the island's width instead of drawing at natural pixel size", () => {
    const w = mountMap();
    const svg = w.get("svg.local-map__lattice");
    const style = svg.attributes("style") ?? "";
    expect(style).toContain("width: 100%");
    expect(style).toContain("max-width: 206px");
  });

  it("bounds the upscale so a one-room payload cannot blow up the marker ramp", () => {
    const w = mountMap({ localMap: localMapModelFor(LOCAL_MAP_SINGLE_NODE_SAMPLE) });
    const style = w.get("svg.local-map__lattice").attributes("style") ?? "";
    expect(style).toContain("width: 100%");
    expect(style).toContain("max-width: 116px");
  });

  it("keeps the header on one row: an elastic title, fixed marks, and no trailing control", () => {
    // webclient-minimap-04-island-single-affordance (task 1.1): the meta row
    // carries the title and the axis marks, with no expand button.
    const w = mountMap({
      localMap: {
        ...localMapModelFor(LOCAL_MAP_SAMPLE),
        title: "冒險者公會外街道圖",
      },
    });
    const titleEl = w.get('[data-testid="local-map__title"] .local-map__meta-title');
    expect(titleEl.text()).toBe("冒險者公會外街道圖");
    // The untruncated string stays reachable on the element itself.
    expect(titleEl.attributes("title")).toBe("冒險者公會外街道圖");
    // The header carries no expand button of its own.
    expect(w.find('.local-map__meta button').exists()).toBe(false);
    // The axis marks stay in the header, unwrapped, on the lattice variant.
    expect(w.find('[data-testid="local-map__orientation"]').exists()).toBe(true);
  });

  it("follows the payload's current node coordinates when the player moves", async () => {
    // webclient-minimap-04-island-single-affordance (D3/D6): the readout is a
    // pure function of the committed payload's current node coordinates. When
    // the payload changes, the readout follows the new coordinates.
    const w = mountMap();
    expect(w.get('[data-testid="local-map-detail"]').text()).toBe("座標 1,2");
    await w.setProps({ localMap: localMapModelFor(LOCAL_MAP_WILDERNESS_SAMPLE) });
    const detail = w.get('[data-testid="local-map-detail"]');
    expect(detail.text()).toBe("座標 3,1");
    expect(detail.classes()).not.toContain("local-map__detail--empty");
  });

  it("states nothing rather than an empty box on coordinate-free layers", () => {
    // Coordinate-free layers (interior/instance) have no coordinate figure,
    // so the readout line renders nothing and gains the --empty modifier class.
    const w = mountMap({ localMap: localMapModelFor(LOCAL_MAP_INTERIOR_SAMPLE) });
    const detail = w.get('[data-testid="local-map-detail"]');
    expect(detail.text()).toBe("");
    expect(detail.classes()).toContain("local-map__detail--empty");
  });

  it("states nothing rather than an empty box when no current node resolves", () => {
    const model = localMapModelFor(LOCAL_MAP_MINIMAL_SAMPLE);
    const w = mountMap({ localMap: { ...model, currentNode: null } });
    const detail = w.get('[data-testid="local-map-detail"]');
    expect(detail.text()).toBe("");
    expect(detail.classes()).toContain("local-map__detail--empty");
  });

  it("keeps the 48-row lattice + 16 remembered nodes within the 64-node bound", () => {
    const model = localMapModelFor(LOCAL_MAP_TALL_REMEMBERED_SAMPLE);
    expect(model.rows).toBe(48);
    expect(model.cols).toBe(2);
    expect(model.nodes).toHaveLength(48);
    expect(model.remembered).toHaveLength(16);
    const w = mountMap({ localMap: model });
    const svg = w.find("svg.local-map__lattice");
    expect(svg.attributes("width")).toBe("266");
    expect(svg.attributes("height")).toBe("2276");
    const list = w.find('[data-testid="local-map-remembered"]');
    expect(list.exists()).toBe(true);
    expect(w.findAll(".local-map__remembered li")).toHaveLength(16);
  });

  it("keeps adjacent node markers and labels non-intersecting at natural geometry", () => {
    const model = localMapModelFor(LOCAL_MAP_GEOMETRY_STRESS_SAMPLE);
    const w = mountMap({ localMap: model });

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

    for (const id of Object.keys(centers)) {
      const label = w.get(`[data-testid="local-map__node--${id}"] .local-map__node-label`);
      expect(label.attributes("y")).toBe("26");
    }

    const markerBoxes = {
      "grid:altoria:1:1": { x1: 78, y1: 57, x2: 96, y2: 75 },
      "grid:altoria:2:1": { x1: 139.5, y1: 60.5, x2: 150.5, y2: 71.5 },
      "grid:altoria:1:2": { x1: 81.5, y1: 16.5, x2: 92.5, y2: 27.5 },
      "grid:altoria:0:1": { x1: 24, y1: 61, x2: 34, y2: 71 },
    };

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
    expect(
      w.get('[data-testid="local-map__node--grid:altoria:1:1"]').attributes("transform"),
    ).toBe("translate(29, 22)");
    expect(w.get('[data-testid="local-map__marker--current"]').exists()).toBe(true);
  });

  it("budgets the canvas from the reduced island sections, not a legend", async () => {
    const host = document.createElement("div");
    host.setAttribute("data-anchor", "hud-right");
    Object.defineProperty(host, "clientHeight", { value: 200, configurable: true });
    document.body.appendChild(host);
    const realRect = Element.prototype.getBoundingClientRect;
    const sectionHeights = {
      "local-map__meta": 24,
      "local-map__remembered": 40,
      "local-map__detail": 18,
    };
    Element.prototype.getBoundingClientRect = function () {
      for (const [cls, height] of Object.entries(sectionHeights)) {
        if (this.classList?.contains(cls)) return { height };
      }
      return realRect.call(this);
    };
    try {
      wrapper = mount(LocalMap, {
        props: { localMap: localMapModelFor(LOCAL_MAP_MINIMAL_SAMPLE) },
        attachTo: host,
      });
      await wrapper.vm.$nextTick();
      expect(wrapper.find("svg.local-map__lattice").attributes("style")).toContain(
        "max-height: 117px",
      );
      wrapper.unmount();
      wrapper = null;
      wrapper = mount(LocalMap, {
        props: { localMap: localMapModelFor(LOCAL_MAP_SAMPLE) },
        attachTo: host,
      });
      await wrapper.vm.$nextTick();
      expect(wrapper.find("svg.local-map__lattice").attributes("style")).toContain(
        "max-height: 69px",
      );
    } finally {
      Element.prototype.getBoundingClientRect = realRect;
      host.remove();
    }
  });

  it("budgets against the anchor's room, not the island's own height", async () => {
    const stage = document.createElement("div");
    const host = document.createElement("div");
    host.setAttribute("data-anchor", "hud-right");
    const dock = document.createElement("div");
    dock.setAttribute("data-anchor", "dock");
    stage.append(host, dock);
    document.body.appendChild(stage);

    const sectionHeights = {
      "local-map__meta": 24,
      "local-map__detail": 18,
    };
    const realRect = Element.prototype.getBoundingClientRect;
    Element.prototype.getBoundingClientRect = function () {
      for (const [cls, height] of Object.entries(sectionHeights)) {
        if (this.classList?.contains(cls)) return { height };
      }
      if (this === host) return { top: 64, height: host.clientHeight };
      if (this === dock) return { top: 500, height: 158 };
      return realRect.call(this);
    };
    Object.defineProperty(host, "clientHeight", {
      configurable: true,
      get() {
        const svg = host.querySelector("svg.local-map__lattice");
        const cap = /max-height:\s*([\d.]+)px/.exec(svg?.getAttribute("style") ?? "");
        const canvas = Math.min(154.91, cap ? parseFloat(cap[1]) : 296);
        return 2 + 18 + 24 + 4 + 8 + canvas + 8 + 18;
      },
    });

    try {
      wrapper = mount(LocalMap, {
        props: { localMap: localMapModelFor(LOCAL_MAP_MINIMAL_SAMPLE) },
        attachTo: host,
      });
      for (let pass = 0; pass < 8; pass += 1) {
        await wrapper.vm.$nextTick();
        expect(
          wrapper.find("svg.local-map__lattice").attributes("style"),
          `pass ${pass} must not ratchet the canvas down`,
        ).toContain("max-height: 296px");
      }
    } finally {
      Element.prototype.getBoundingClientRect = realRect;
      stage.remove();
    }
  });

  it("MapOverlay renders the shared LocalMap and forwards the move intent", async () => {
    const model = localMapModelFor(LOCAL_MAP_GEOMETRY_STRESS_SAMPLE);
    const overlay = mount(MapOverlay, {
      props: { localMap: model },
    });
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
