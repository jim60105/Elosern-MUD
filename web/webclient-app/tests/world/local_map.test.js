import { mount } from "@vue/test-utils";
import { readFileSync } from "node:fs";
import { join } from "node:path";
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
    };
    for (const [state, id] of Object.entries(expected)) {
      const node = w.get(`[data-testid="local-map__node--${id}"]`);
      expect(node.attributes("data-visibility")).toBe(state);
      expect(node.find(`.local-map__marker--${state}`).exists()).toBe(true);
    }
    const edgeMarker = w.get('[data-testid="local-map__edge-marker--grid:altoria:5:5"]');
    expect(edgeMarker.find(".local-map__edge-marker-diamond").exists()).toBe(true);
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
      w.get('[data-testid="local-map__edge-marker--grid:altoria:5:5"]').find('rect[transform="rotate(45)"]').exists(),
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
    // Edge marker click emits no move (falls through to open-map).
    await w.get('[data-testid="local-map__edge-marker--grid:altoria:5:5"]').trigger("click");
    expect(w.emitted("move")).toBeUndefined();
  });

  it("Task 3.1 & 3.2: scopes remembered list to graph variant and provides text mirror for edge markers", async () => {
    // Wilderness/grid payload: no remembered list in DOM, mirror is present
    const wLattice = mountMap({ localMap: localMapModelFor(LOCAL_MAP_WILDERNESS_SAMPLE) });
    expect(wLattice.find('[data-testid="local-map-remembered"]').exists()).toBe(false);
    const mirror = wLattice.find('[data-testid="local-map-edge-markers-mirror"]');
    expect(mirror.exists()).toBe(true);
    expect(mirror.attributes("aria-label")).toBe("已知的地圖出入口");
    const mirrorItems = mirror.findAll("li");
    expect(mirrorItems).toHaveLength(1);
    expect(mirrorItems[0].text()).toContain("遠處山徑");
    expect(mirrorItems[0].attributes("tabindex")).toBeUndefined();

    // Interior payload with remembered: remembered list present, non-focusable items, no mirror
    const interiorPayload = {
      ...LOCAL_MAP_INTERIOR_SAMPLE,
      nodes: [
        ...LOCAL_MAP_INTERIOR_SAMPLE.nodes,
        { id: "room:rem", label: "公會倉庫", x: 0, y: 5, visibility: "remembered", landmark: false },
      ],
    };
    const wInterior = mountMap({ localMap: localMapModelFor(interiorPayload) });
    const remList = wInterior.find('[data-testid="local-map-remembered"]');
    expect(remList.exists()).toBe(true);
    const remItems = remList.findAll("li");
    expect(remItems).toHaveLength(1);
    expect(remItems[0].text()).toContain("公會倉庫");
    expect(remItems[0].attributes("tabindex")).toBeUndefined();
    expect(remItems[0].attributes("data-node")).toBeUndefined();
    expect(wInterior.find('[data-testid="local-map-edge-markers-mirror"]').exists()).toBe(false);
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

    // An edge marker click falls through and emits open-map.
    await w.get('[data-testid="local-map__edge-marker--grid:altoria:5:5"]').trigger("click");
    expect(w.emitted("open-map")).toHaveLength(1);

    // On a graph payload, clicking a remembered list item falls through and emits open-map.
    const interiorPayload = {
      ...LOCAL_MAP_INTERIOR_SAMPLE,
      nodes: [
        ...LOCAL_MAP_INTERIOR_SAMPLE.nodes,
        { id: "room:rem", label: "公會倉庫", x: 0, y: 5, visibility: "remembered", landmark: false },
      ],
    };
    const wInterior = mountMap({ localMap: localMapModelFor(interiorPayload) });
    await wInterior.get('[data-testid="local-map-remembered"] li').trigger("click");
    expect(wInterior.emitted("open-map")).toHaveLength(1);
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
    // Design D5 row 6: 2 × 40px column core padded symmetrically to 206px width cap,
    // 64 × 40px row pitch + 14px label band = 2574px tall, zero vertical margin.
    expect(svg.attributes("width")).toBe("206");
    expect(svg.attributes("height")).toBe("2574");
    expect(svg.attributes("viewBox")).toBe("0 0 206 2574");
    // Single width bound: 296 * 206 / 2574 = 23.68px
    const style = svg.attributes("style") ?? "";
    expect(style).toContain("width: 100%");
    expect(style).toContain("max-width: 23.68px");
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

  it("spends width fill as coordinate margin rather than magnification (maxUpscale retired)", () => {
    const w = mountMap({ localMap: localMapModelFor(LOCAL_MAP_SINGLE_NODE_SAMPLE) });
    const style = w.get("svg.local-map__lattice").attributes("style") ?? "";
    expect(style).toContain("width: 100%");
    // Design D5 row 3: single node canvas is padded to 206px with scale 1.0
    expect(style).toContain("max-width: 206px");
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
    expect(Number(svg.attributes("width"))).toBeCloseTo(206, 5);
    expect(Number(svg.attributes("height"))).toBeCloseTo(2022.911688, 4);
    expect(w.find('[data-testid="local-map-remembered"]').exists()).toBe(false);
    expect(w.findAll('[data-testid^="local-map__edge-marker--"]')).toHaveLength(16);
  });

  it("keeps adjacent node markers and labels non-intersecting at natural geometry", () => {
    const model = localMapModelFor(LOCAL_MAP_GEOMETRY_STRESS_SAMPLE);
    const w = mountMap({ localMap: model });

    // Distinct adjacent labels trigger pitch 48 on both axes. Margin = 31 on both axes.
    const centers = {
      "grid:altoria:1:1": { x: 103, y: 103 },
      "grid:altoria:2:1": { x: 151, y: 103 },
      "grid:altoria:1:2": { x: 103, y: 55 },
      "grid:altoria:0:1": { x: 55, y: 103 },
    };
    for (const [id, center] of Object.entries(centers)) {
      const node = w.get(`[data-testid="local-map__node--${id}"]`);
      expect(node.attributes("transform")).toBe(`translate(${center.x}, ${center.y})`);
    }

    // Label baseline at labelFont 9: 22 units
    for (const id of Object.keys(centers)) {
      const label = w.get(`[data-testid="local-map__node--${id}"] .local-map__node-label`);
      expect(label.attributes("y")).toBe("22");
    }

    const markerBoxes = {
      "grid:altoria:1:1": { x1: 94, y1: 94, x2: 112, y2: 112 },
      "grid:altoria:2:1": { x1: 145.5, y1: 97.5, x2: 156.5, y2: 108.5 },
      "grid:altoria:1:2": { x1: 97.5, y1: 49.5, x2: 108.5, y2: 60.5 },
      "grid:altoria:0:1": { x1: 49.5, y1: 97.5, x2: 60.5, y2: 108.5 },
    };

    // Label boxes: font 9, 5 full-width glyphs (45 wide), ascent 8.55, descent 4.05 around y=22
    const labelBoxes = {
      "grid:altoria:1:1": { x1: 80.5, y1: 116.45, x2: 125.5, y2: 129.05 },
      "grid:altoria:2:1": { x1: 128.5, y1: 116.45, x2: 173.5, y2: 129.05 },
      "grid:altoria:1:2": { x1: 80.5, y1: 68.45, x2: 125.5, y2: 81.05 },
      "grid:altoria:0:1": { x1: 32.5, y1: 116.45, x2: 77.5, y2: 129.05 },
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
    expect(e0.attributes("x1")).toBe("103");
    expect(e0.attributes("y1")).toBe("103");
    expect(e0.attributes("x2")).toBe("151");
    expect(e0.attributes("y2")).toBe("103");
    expect(48 - 9 - 5.5).toBeGreaterThan(0);
    const e1 = w.get('[data-testid="local-map__edge--1"]');
    expect(e1.attributes("x1")).toBe("103");
    expect(e1.attributes("y1")).toBe("103");
    expect(e1.attributes("x2")).toBe("103");
    expect(e1.attributes("y2")).toBe("55");
    expect(48 - 9 - 5.5).toBeGreaterThan(0);
  });

  it("renders a single-node room with no collision risk (no regression)", () => {
    const model = localMapModelFor(LOCAL_MAP_SINGLE_NODE_SAMPLE);
    const w = mountMap({ localMap: model });
    const svg = w.find("svg.local-map__lattice");
    // Design D5 row 3: canvas fills maxWidth 206px as coordinate margin, height 220px
    expect(svg.attributes("width")).toBe("206");
    expect(svg.attributes("height")).toBe("220");
    expect(
      w.get('[data-testid="local-map__node--grid:altoria:1:1"]').attributes("transform"),
    ).toBe("translate(103, 103)");
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
        "max-height: 117px",
      );
    } finally {
      Element.prototype.getBoundingClientRect = realRect;
      host.remove();
    }
  });

  it("Task 4.1: derives canvas height budget from laid out sections on 1280x720 fixture", async () => {
    const stage = document.createElement("div");
    const hudRight = document.createElement("div");
    hudRight.setAttribute("data-anchor", "hud-right");
    const dock = document.createElement("div");
    dock.setAttribute("data-anchor", "dock");
    stage.appendChild(hudRight);
    stage.appendChild(dock);
    document.body.appendChild(stage);

    const realRect = Element.prototype.getBoundingClientRect;
    Element.prototype.getBoundingClientRect = function () {
      if (this === hudRight) return { top: 64 };
      if (this === dock) return { top: 500 };
      if (this.classList?.contains("local-map__meta")) return { height: 15 };
      if (this.classList?.contains("local-map__detail")) {
        return { height: this.classList?.contains("local-map__detail--empty") ? 0 : 16 };
      }
      if (this.classList?.contains("local-map__remembered")) return { height: 224 };
      return realRect.call(this);
    };

    try {
      // 1. Lattice variant: meta (15) + detail (16) = 31, 2 gaps = 16. 424 - 31 - 16 - 25 = 352 -> clamped 296
      wrapper = mount(LocalMap, {
        props: { localMap: localMapModelFor(LOCAL_MAP_SAMPLE) },
        attachTo: hudRight,
      });
      await wrapper.vm.$nextTick();
      expect(wrapper.find("svg.local-map__lattice").attributes("style")).toContain(
        "max-height: 296px",
      );
      wrapper.unmount();
      wrapper = null;

      // 2. Graph variant with no remembered: meta (15), no detail (0), 1 gap = 8. 424 - 15 - 8 - 25 = 376 -> clamped 296
      wrapper = mount(LocalMap, {
        props: { localMap: localMapModelFor(LOCAL_MAP_INTERIOR_SAMPLE) },
        attachTo: hudRight,
      });
      await wrapper.vm.$nextTick();
      expect(wrapper.find("svg.local-map__lattice").attributes("style")).toContain(
        "max-height: 296px",
      );
      wrapper.unmount();
      wrapper = null;

      // 3. Graph variant with 16 remembered: meta (15) + remembered (224) = 239, 2 gaps = 16. 424 - 239 - 16 - 25 = 144
      const graphWith16 = {
        ...LOCAL_MAP_INTERIOR_SAMPLE,
        nodes: [
          ...LOCAL_MAP_INTERIOR_SAMPLE.nodes,
          ...Array.from({ length: 16 }, (_, i) => ({
            id: `room:rem:${i}`,
            label: `倉庫${i}`,
            x: 0,
            y: i + 2,
            visibility: "remembered",
          })),
        ],
      };
      wrapper = mount(LocalMap, {
        props: { localMap: localMapModelFor(graphWith16) },
        attachTo: hudRight,
      });
      await wrapper.vm.$nextTick();
      expect(wrapper.find("svg.local-map__lattice").attributes("style")).toContain(
        "max-height: 144px",
      );
    } finally {
      Element.prototype.getBoundingClientRect = realRect;
      stage.remove();
    }
  });

  it("Task 4.2: gutter enlargement cannot breach canvas height cap and re-measures to same cap", async () => {
    const stage = document.createElement("div");
    const hudRight = document.createElement("div");
    hudRight.setAttribute("data-anchor", "hud-right");
    const dock = document.createElement("div");
    dock.setAttribute("data-anchor", "dock");
    stage.appendChild(hudRight);
    stage.appendChild(dock);
    document.body.appendChild(stage);

    const realRect = Element.prototype.getBoundingClientRect;
    Element.prototype.getBoundingClientRect = function () {
      if (this === hudRight) return { top: 64 };
      if (this === dock) return { top: 500 };
      if (this.classList?.contains("local-map__meta")) return { height: 15 };
      if (this.classList?.contains("local-map__detail")) return { height: 16 };
      return realRect.call(this);
    };

    const crowdedModel = localMapModelFor(LOCAL_MAP_TALL_REMEMBERED_SAMPLE);
    try {
      wrapper = mount(LocalMap, {
        props: { localMap: crowdedModel },
        attachTo: hudRight,
      });
      await wrapper.vm.$nextTick();
      const svg = wrapper.find("svg.local-map__lattice");
      expect(svg.attributes("style")).toContain("max-height: 296px");
      // Width bound spends the height budget proportionally: 296 * (206 / 2022.91) = 30.14px
      expect(svg.attributes("style")).toContain("max-width: 30.14px");
    } finally {
      Element.prototype.getBoundingClientRect = realRect;
      stage.remove();
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

  it("Task 2.5: declares island geometry on MapLattice mount and renders node label at <= 9 CSS px", () => {
    const w = mountMap({ localMap: localMapModelFor(LOCAL_MAP_WILDERNESS_SAMPLE) });
    const lattice = w.findComponent({ name: "MapLattice" });
    expect(lattice.exists()).toBe(true);
    expect(lattice.props("colPitch")).toBe(40);
    expect(lattice.props("rowPitch")).toBe(40);
    expect(lattice.props("labelFont")).toBe(9);
    expect(lattice.props("fieldFill")).toBe(true);
    expect(lattice.props("showAxis")).toBe(true);
    expect(lattice.props("fogVignette")).toBe(true);
    expect(lattice.props("maxUpscale")).toBeUndefined();
    const label = lattice.find(".local-map__node-label");
    expect(label.attributes("style")).toContain("font-size: 9px");
  });

  // ---------------------------------------------------------------------
  // The island's own type ladder and its layered-content contract. Both are
  // expressed in the SFC's scoped CSS, which a jsdom mount does not apply, so
  // they are asserted against the authored rule text — the same technique the
  // layout-variant and z-index suites already use for style contracts.
  // ---------------------------------------------------------------------

  const ISLAND_SOURCE = readFileSync(
    join(import.meta.dirname, "../../components/LocalMap.vue"),
    "utf-8",
  );

  function ruleBody(source, selector) {
    const start = source.indexOf(`${selector} {`);
    expect(start, `rule not found: ${selector}`).toBeGreaterThan(-1);
    return source.slice(start, source.indexOf("}", start));
  }

  it("keeps the readout at the island's smallest type step, never above its own header", () => {
    // webclient-local-map: the readout "SHALL render at the island's smallest
    // type step". The island's smallest chrome step is the meta row's 10px, so
    // the readout states its one secondary figure at exactly that step — it
    // shipped at 11px, which made a coordinate pair the LARGEST text on the
    // card, above the card's own title.
    const header = ruleBody(ISLAND_SOURCE, ".local-map__meta");
    const readout = ruleBody(ISLAND_SOURCE, ".local-map__detail");
    const step = (body) => body.match(/font-size:\s*([0-9.]+)px/)?.[1];
    expect(step(header)).toBe("10");
    expect(step(readout)).toBe(step(header));
    // ...and the treatment stays box-free and token-driven (design D7).
    expect(readout).toContain("var(--f-mono)");
    expect(readout).toContain("var(--paper-500)");
    expect(readout).not.toMatch(/\bborder\s*:/);
    expect(readout).not.toMatch(/\bbackground\s*:/);
    expect(readout).not.toMatch(/#[0-9a-fA-F]{3,6}/);
  });

  it("declares the marker-name step so no island text outweighs the island's chrome", () => {
    const w = mountMap({ localMap: localMapModelFor(LOCAL_MAP_WILDERNESS_SAMPLE) });
    const lattice = w.findComponent({ name: "MapLattice" });
    expect(lattice.props("markerNameFont")).toBe(10);
    // Declared by the surface, not inherited from the renderer's default —
    // the island owns every type size it draws (the `labelFont` precedent).
    expect(ISLAND_SOURCE).toContain(':marker-name-font="10"');
    // Every type size the island declares is at or below its 10px chrome step:
    // the node label (9), the marker name (10), the readout and the header
    // (10). A marker name drawn at --text-sm (13) used to out-shout both.
    const chromeStep = 10;
    expect(lattice.props("labelFont")).toBeLessThanOrEqual(chromeStep);
    expect(lattice.props("markerNameFont")).toBeLessThanOrEqual(chromeStep);
  });

  it("keeps the assistive-technology mirror out of the island's flex flow", () => {
    // The z-index raising rule outranks `.visually-hidden` on specificity, so
    // without an explicit exclusion it re-positions the mirror to `relative`:
    // `clip` then stops applying (it only affects absolutely positioned boxes)
    // and the mirror becomes an in-flow flex item worth its own box plus a full
    // gap — height that `measureCanvasBudget()` never reserves, because it
    // counts only the meta row, the canvas, and at most one of the graph list
    // and the readout.
    const raising = ISLAND_SOURCE.match(
      /\.local-map > \*:not\(\.local-map__affordance\)([^{]*)\{/,
    );
    expect(raising, "the raising rule must stay a :not() rule").not.toBeNull();
    expect(raising[1]).toContain(":not(.visually-hidden)");
    expect(ruleBody(ISLAND_SOURCE, ".visually-hidden")).toContain("position: absolute");

    // The mirror is still rendered, still unfocusable, and still the only
    // island section the budget does not count.
    const w = mountMap({ localMap: localMapModelFor(LOCAL_MAP_WILDERNESS_SAMPLE) });
    const mirror = w.find('[data-testid="local-map-edge-markers-mirror"]');
    expect(mirror.exists()).toBe(true);
    expect(mirror.classes()).toContain("visually-hidden");
    expect(mirror.attributes("tabindex")).toBeUndefined();
  });
});
