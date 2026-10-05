import { mount } from "@vue/test-utils";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import LocalMap from "../../components/LocalMap.vue";
import MapOverlay from "../../components/MapOverlay.vue";
import { CELL_EM, textCells } from "../../lib/mono_cells.js";
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
    // Wilderness/grid payload: no remembered list in DOM, edge markers mirror is present
    const wLattice = mountMap({ localMap: localMapModelFor(LOCAL_MAP_WILDERNESS_SAMPLE) });
    expect(wLattice.find('[data-testid="local-map-remembered"]').exists()).toBe(false);
    const mirror = wLattice.find('[data-testid="local-map-edge-markers-mirror"]');
    expect(mirror.exists()).toBe(true);
    expect(mirror.attributes("aria-label")).toBe("已知的地圖出入口");
    const mirrorItems = mirror.findAll("li");
    expect(mirrorItems).toHaveLength(1);
    expect(mirrorItems[0].text()).toContain("遠處山徑");
    expect(mirrorItems[0].attributes("tabindex")).toBeUndefined();

    // Interior payload with remembered: no local-map-remembered, local-map-remembered-mirror present
    const interiorPayload = {
      ...LOCAL_MAP_INTERIOR_SAMPLE,
      nodes: [
        ...LOCAL_MAP_INTERIOR_SAMPLE.nodes,
        { id: "room:rem", label: "公會倉庫", x: 0, y: 5, visibility: "remembered", landmark: false },
      ],
    };
    const wInterior = mountMap({ localMap: localMapModelFor(interiorPayload) });
    expect(wInterior.find('[data-testid="local-map-remembered"]').exists()).toBe(false);
    const remMirror = wInterior.find('[data-testid="local-map-remembered-mirror"]');
    expect(remMirror.exists()).toBe(true);
    expect(remMirror.attributes("aria-label")).toBe("記得的地點");
    const remItems = remMirror.findAll("li");
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
  // suites: map_lattice_renderer.test.js, map_overlay.test.js).
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
      // No compass bearing like 「北 324° ‧ 西 262°」 and no distance unit.
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

    // An edge marker click on a wilderness sample also emits open-map without move.
    const wWild = mountMap({ localMap: localMapModelFor(LOCAL_MAP_WILDERNESS_SAMPLE) });
    await wWild.get('[data-testid^="local-map__edge-marker--"]').trigger("click");
    expect(wWild.emitted("open-map")).toHaveLength(1);
    expect(wWild.emitted("move")).toBeUndefined();
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
    expect(svg.attributes("width")).toBe("240");
    expect(svg.attributes("height")).toBe("240");
    // Below the island's legibility floor the 2574-unit square is shown
    // through a 240 window centred on the current node, not shrunk to
    // a hairline (design §11).
    const vb = svg.attributes("viewBox").split(" ").map(Number);
    expect(vb[2]).toBeCloseTo(240, 6);
    expect(vb[3]).toBeCloseTo(240, 6);
    const current = w.get('[data-visibility="current"]');
    const [cx, cy] = current.attributes("transform").match(/-?[\d.]+/g).map(Number);
    expect(cx).toBeCloseTo(vb[0] + vb[2] / 2, 6);
    expect(cy).toBeCloseTo(vb[1] + vb[3] / 2, 6);
    const style = svg.attributes("style") ?? "";
    expect(style).toContain("width: calc(240px * var(--ui-scale, 1))");
    expect(style).toContain("height: calc(240px * var(--ui-scale, 1))");
  });

  // ---------------------------------------------------------------------
  // The minimap island claims its card (the redesign review's primary
  // finding, REDESIGN §7 / draft `.mini svg { width:100%; max-width:172px }`).
  // ---------------------------------------------------------------------

  it("fills the island's width instead of drawing at natural pixel size", () => {
    const w = mountMap();
    const svg = w.get("svg.local-map__lattice");
    const style = svg.attributes("style") ?? "";
    expect(style).toContain("width: calc(240px * var(--ui-scale, 1))");
    expect(style).toContain("height: calc(240px * var(--ui-scale, 1))");
    expect(Number(svg.attributes("width"))).toBe(240);
    expect(Number(svg.attributes("height"))).toBe(240);
  });

  it("spends width fill as coordinate margin rather than magnification (maxUpscale retired)", () => {
    const w = mountMap({ localMap: localMapModelFor(LOCAL_MAP_SINGLE_NODE_SAMPLE) });
    const svg = w.get("svg.local-map__lattice");
    const style = w.get("svg.local-map__lattice").attributes("style") ?? "";
    expect(style).toContain("width: calc(240px * var(--ui-scale, 1))");
    expect(style).toContain("height: calc(240px * var(--ui-scale, 1))");
    expect(Number(svg.attributes("width"))).toBe(240);
    expect(Number(svg.attributes("height"))).toBe(240);
    const pattern = w.find("defs pattern");
    expect(Number(pattern.attributes("width"))).toBe(60);
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
    expect(Number(svg.attributes("width"))).toBe(240);
    expect(Number(svg.attributes("height"))).toBe(240);
    const vb = svg.attributes("viewBox").split(" ").map(Number);
    // The 2022.91-unit square exceeds the legibility floor, so the island
    // shows a 240 window clamped inside the drawing.
    expect(vb[2]).toBeCloseTo(240, 6);
    expect(vb[0]).toBeGreaterThanOrEqual(0);
    expect(vb[1]).toBeGreaterThanOrEqual(0);
    expect(vb[0] + vb[2]).toBeLessThanOrEqual(2022.911688 + 1e-6);
    expect(vb[1] + vb[3]).toBeLessThanOrEqual(2022.911688 + 1e-6);
    expect(w.find('[data-testid="local-map-remembered"]').exists()).toBe(false);
    expect(w.findAll('[data-testid^="local-map__edge-marker--"]')).toHaveLength(16);
  });

  it("keeps adjacent node markers and labels non-intersecting at natural geometry", () => {
    const model = localMapModelFor(LOCAL_MAP_GEOMETRY_STRESS_SAMPLE);
    const w = mountMap({ localMap: model });

    // With canvasSize 240 the label term binds: the adjacent 霧骨渡口 (8 cells)
    // and 南門街道… (9 cells) need ((8 + 9) / 2 × CELL_EM + 0.5) × 16 → 88,
    // above the 60-unit fill cap. Three columns and two rows of 88 need a
    // 264-unit square — wider than the island's 240px canvas, so the drawing
    // is scaled to 240/264 — at margins 0 (x) and 37 (y, with the 14-unit
    // label band).
    const P = 88;
    const col = (c) => c * P + P / 2;
    const row = (r) => (1 - r) * P + P / 2 + 37;
    const centers = {
      "grid:altoria:1:1": { x: col(1), y: row(0) },
      "grid:altoria:2:1": { x: col(2), y: row(0) },
      "grid:altoria:1:2": { x: col(1), y: row(1) },
      "grid:altoria:0:1": { x: col(0), y: row(0) },
    };
    expect(centers["grid:altoria:1:1"]).toEqual({ x: 132, y: 169 });
    for (const [id, center] of Object.entries(centers)) {
      const node = w.get(`[data-testid="local-map__node--${id}"]`);
      expect(node.attributes("transform")).toBe(`translate(${center.x}, ${center.y})`);
    }

    // Label baseline at labelFont 16: 11 + 2 + 16 = 29 units
    for (const id of Object.keys(centers)) {
      const label = w.get(`[data-testid="local-map__node--${id}"] .local-map__node-label`);
      expect(label.attributes("y")).toBe("29");
    }

    // Current seal half-extent 9; visited/unvisited dots 5.5.
    const half = { "grid:altoria:1:1": 9, "grid:altoria:2:1": 5.5, "grid:altoria:1:2": 5.5, "grid:altoria:0:1": 5.5 };
    const markerBoxes = {};
    for (const [id, c] of Object.entries(centers)) {
      markerBoxes[id] = { x1: c.x - half[id], y1: c.y - half[id], x2: c.x + half[id], y2: c.y + half[id] };
    }

    // Label boxes: the drawn (truncated) label measured in monospace cells at
    // font 16, ascent 15.2 and descent 7.2 around the baseline y = 29.
    const labelBoxes = {};
    for (const [id, c] of Object.entries(centers)) {
      // The drawn text only: the element also holds the full name's <title>.
      const el = w.get(`[data-testid="local-map__node--${id}"] .local-map__node-label`).element;
      const text = Array.from(el.childNodes)
        .filter((n) => n.nodeType === Node.TEXT_NODE)
        .map((n) => n.textContent)
        .join("")
        .trim();
      const width = textCells(text) * CELL_EM * 16;
      labelBoxes[id] = { x1: c.x - width / 2, y1: c.y + 13.8, x2: c.x + width / 2, y2: c.y + 36.2 };
    }

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
    everyPair(labelBoxes);

    const e0 = w.get('[data-testid="local-map__edge--0"]');
    expect(e0.attributes("x1")).toBe("132");
    expect(e0.attributes("y1")).toBe("169");
    expect(e0.attributes("x2")).toBe("220");
    expect(e0.attributes("y2")).toBe("169");
    expect(P - 9 - 5.5).toBeGreaterThan(0);
    const e1 = w.get('[data-testid="local-map__edge--1"]');
    expect(e1.attributes("x1")).toBe("132");
    expect(e1.attributes("y1")).toBe("169");
    expect(e1.attributes("x2")).toBe("132");
    expect(e1.attributes("y2")).toBe("81");
    expect(P - 9 - 5.5).toBeGreaterThan(0);
  });

  it("renders a single-node room with no collision risk (no regression)", () => {
    const model = localMapModelFor(LOCAL_MAP_SINGLE_NODE_SAMPLE);
    const w = mountMap({ localMap: model });
    const svg = w.find("svg.local-map__lattice");
    expect(svg.attributes("width")).toBe("240");
    expect(svg.attributes("height")).toBe("240");
    expect(
      w.get('[data-testid="local-map__node--grid:altoria:1:1"]').attributes("transform"),
    ).toBe("translate(120, 113)");
    expect(w.get('[data-testid="local-map__marker--current"]').exists()).toBe(true);
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

  it("Task 2.5: declares island geometry on MapLattice mount and renders node labels at its 16-unit step", () => {
    const w = mountMap({ localMap: localMapModelFor(LOCAL_MAP_WILDERNESS_SAMPLE) });
    const lattice = w.findComponent({ name: "MapLattice" });
    expect(lattice.exists()).toBe(true);
    expect(lattice.props("colPitch")).toBe(40);
    expect(lattice.props("rowPitch")).toBe(40);
    expect(lattice.props("labelFont")).toBe(16);
    expect(lattice.props("canvasSize")).toBe(240);
    expect(lattice.props("showAxis")).toBe(true);
    expect(lattice.props("fogVignette")).toBe(true);
    expect(lattice.props("maxUpscale")).toBeUndefined();
    const label = lattice.find(".local-map__node-label");
    expect(label.attributes("style")).toContain("font-size: 16px");
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


  it("declares the marker-name step so no island text outweighs the island's chrome", () => {
    const w = mountMap({ localMap: localMapModelFor(LOCAL_MAP_WILDERNESS_SAMPLE) });
    const lattice = w.findComponent({ name: "MapLattice" });
    expect(lattice.props("markerNameFont")).toBe(16);
    // Declared by the surface, not inherited from the renderer's default —
    // the island owns every type size it draws (the `labelFont` precedent).
    expect(ISLAND_SOURCE).toContain(':marker-name-font="16"');
    // Every type size the island declares is at or below its own chrome step
    // (retarget-desktop-viewport-contract D7): the node label (16), the marker
    // name (16), and the title, orientation marks and readout at `--text-xs`
    // (16px at the reference) — one 16px floor for the whole island, no drawn
    // label or name below it.
    const chromeStep = 16;
    for (const selector of [".local-map__meta", ".local-map__orientation", ".local-map__detail"]) {
      expect(ruleBody(ISLAND_SOURCE, selector)).toContain("font-size: var(--text-xs)");
    }
    expect(lattice.props("labelFont")).toBeLessThanOrEqual(chromeStep);
    expect(lattice.props("markerNameFont")).toBeLessThanOrEqual(chromeStep);
  });
});
