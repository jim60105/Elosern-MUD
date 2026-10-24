import { mount } from "@vue/test-utils";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import LocalMap from "../../components/LocalMap.vue";
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
  LOCAL_MAP_ALTORIA_SOUTH_GATE_SAMPLE,
  LOCAL_MAP_ALTORIA_SOUTH_GATE_LOCKED_SAMPLE,
  LOCAL_MAP_CROWDED_LABELS_SAMPLE,
  LOCAL_MAP_WILDERNESS_METRIC_SAMPLE,
  LOCAL_MAP_WILDERNESS_RETURN_SAMPLE,
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

  it("draws a 2-wide × 64-tall street on the island's fixed square", () => {
    // The shared helper mirrors the store's localMapModel construction
    // (stores/elosern.js): the reduced model plus the payload's `available`
    // flag and reason.
    const model = localMapModelFor(LOCAL_MAP_TALL_LATTICE_SAMPLE);
    expect(model.nodes).toHaveLength(64);
    const w = mountMap({ localMap: model });
    const svg = w.find("svg.local-map__lattice");
    expect(svg.exists()).toBe(true);
    expect(svg.attributes("width")).toBe("240");
    expect(svg.attributes("height")).toBe("240");
    // No window over a minimum-pitch lattice (render-auto-scaled-minimap-
    // island): the island is the projection's own 240-unit square with the
    // current node at its centre.
    expect(svg.attributes("viewBox")).toBe("0 0 240 240");
    const current = w.get('[data-visibility="current"]');
    expect(current.attributes("transform")).toBe("translate(120, 120)");
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
    // A lone room has no distance to scale by: the default level (100 m per
    // 100 units) draws world-anchored dots 20 units apart, never a pattern.
    expect(w.find("defs pattern").exists()).toBe(false);
    const dots = w.findAll('[data-testid="local-map__dot-field"] circle');
    expect(dots.length).toBeGreaterThan(0);
    const xs = [...new Set(dots.map((dot) => Number(dot.attributes("cx"))))].sort((a, b) => a - b);
    expect(xs[1] - xs[0]).toBeCloseTo(20, 6);
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

  it("keeps a 48-node street + 16 remembered nodes within the 64-node bound", () => {
    const model = localMapModelFor(LOCAL_MAP_TALL_REMEMBERED_SAMPLE);
    expect(model.nodes).toHaveLength(48);
    expect(model.remembered).toHaveLength(16);
    const w = mountMap({ localMap: model });
    const svg = w.find("svg.local-map__lattice");
    expect(Number(svg.attributes("width"))).toBe(240);
    expect(Number(svg.attributes("height"))).toBe(240);
    // The fixed square holds every remembered marker on its rim band.
    expect(svg.attributes("viewBox")).toBe("0 0 240 240");
    for (const marker of w.findAll('[data-testid^="local-map__edge-marker--"]')) {
      const [mx, my] = marker.attributes("transform").match(/-?[\d.]+/g).map(Number);
      expect(mx).toBeGreaterThanOrEqual(0);
      expect(mx).toBeLessThanOrEqual(240);
      expect(my).toBeGreaterThanOrEqual(0);
      expect(my).toBeLessThanOrEqual(240);
    }
    expect(w.find('[data-testid="local-map-remembered"]').exists()).toBe(false);
    expect(w.findAll('[data-testid^="local-map__edge-marker--"]')).toHaveLength(16);
  });

  it("projects the geometry-stress room onto the island's exit ring", () => {
    // render-auto-scaled-minimap-island: the unit-coordinate stress room's
    // two labelled exits stand one metre away — closer than the exit ring
    // allows at the finest level — so the island compresses them to the
    // shared radius 66 at their exact bearings; the unlinked neighbour is
    // context, a dot without a marker or a route whose name is drawn in the
    // quiet context tier only because a free position remains for it
    // (label-minimap-exits-and-gateways: fits-or-omitted).
    const model = localMapModelFor(LOCAL_MAP_GEOMETRY_STRESS_SAMPLE);
    const w = mountMap({ localMap: model });
    const centre = (id) =>
      w.get(`[data-testid="local-map__node--${id}"]`).attributes("transform");
    expect(centre("grid:altoria:1:1")).toBe("translate(120, 120)");
    expect(centre("grid:altoria:2:1")).toBe("translate(186, 120)");
    expect(centre("grid:altoria:1:2")).toBe("translate(120, 54)");
    expect(centre("grid:altoria:0:1")).toBe("translate(54, 120)");
    const context = w.get('[data-testid="local-map__node--grid:altoria:0:1"]');
    expect(context.classes()).toContain("local-map__node--context");
    expect(context.find(".local-map__marker").exists()).toBe(false);
    expect(context.get(".local-map__node-label").classes()).toContain("local-map__node-label--context");
    expect(context.find("title").text()).toBe("旅館公會");
    // Only the two labelled routes from the current node are drawn.
    expect(w.findAll(".local-map__edge")).toHaveLength(2);
    expect(w.get('[data-testid="local-map__edge--0"]').attributes("x2")).toBe("186");
    expect(w.get('[data-testid="local-map__edge--1"]').attributes("y2")).toBe("54");
    expect(w.get('[data-testid="local-map__scale"]').text()).toBe("距離壓縮");

    // Every drawn label stays inside the square (its box at the 16-unit step
    // in monospace cells, shifted by its own x offset).
    for (const id of ["grid:altoria:1:1", "grid:altoria:2:1", "grid:altoria:1:2"]) {
      const [cx, cy] = centre(id).match(/-?[\d.]+/g).map(Number);
      const line = w.get(`[data-testid="local-map__node--${id}"] .local-map__node-label tspan`).element;
      const text = line.textContent.trim();
      const width = textCells(text) * CELL_EM * 16;
      const x = cx + Number(line.getAttribute("x") ?? 0);
      const y = cy + Number(line.getAttribute("y"));
      expect(x - width / 2).toBeGreaterThanOrEqual(0);
      expect(x + width / 2).toBeLessThanOrEqual(240);
      expect(y + 4).toBeLessThanOrEqual(240);
      expect(y - 16).toBeGreaterThanOrEqual(0);
    }
  });

  it("renders a single-node room with no collision risk (no regression)", () => {
    const model = localMapModelFor(LOCAL_MAP_SINGLE_NODE_SAMPLE);
    const w = mountMap({ localMap: model });
    const svg = w.find("svg.local-map__lattice");
    expect(svg.attributes("width")).toBe("240");
    expect(svg.attributes("height")).toBe("240");
    expect(
      w.get('[data-testid="local-map__node--grid:altoria:1:1"]').attributes("transform"),
    ).toBe("translate(120, 120)");
    expect(w.get('[data-testid="local-map__marker--current"]').exists()).toBe(true);
  });

  it("Task 2.5: declares island geometry on MapLattice mount and renders node labels at its 16-unit step", () => {
    const w = mountMap({ localMap: localMapModelFor(LOCAL_MAP_WILDERNESS_SAMPLE) });
    const lattice = w.findComponent({ name: "MapLattice" });
    expect(lattice.exists()).toBe(true);
    // The overlay pitch props were removed with the full-map overlay.
    expect(lattice.props("colPitch")).toBeUndefined();
    expect(lattice.props("rowPitch")).toBeUndefined();
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

describe("LocalMap metric projection (project-metric-local-maps)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

// project-metric-local-maps: a real metric frame — (0,0), (100,0), (1000,0)
// and (1000,6500) plus a (100,100) diagonal control — with 100 m as the
// smallest in-view coordinate delta.
const METRIC_PAYLOAD = {
  schema_version: 1,
  available: true,
  layer: "grid",
  current_node: "grid:metric:0:0",
  title: "度量城區",
  nodes: [
    { id: "grid:metric:0:0", label: "原點", x: 0, y: 0, visibility: "current", current: true, anchor: false, landmark: false, gateway: null, action: null },
    { id: "grid:metric:100:0", label: "東街", x: 100, y: 0, visibility: "visible_unvisited", current: false, anchor: false, landmark: false, gateway: null, action: { kind: "move", exit_ref: "e", destination: "grid:metric:100:0" } },
    { id: "grid:metric:1000:0", label: "遠東", x: 1000, y: 0, visibility: "visible_unvisited", current: false, anchor: false, landmark: false, gateway: null, action: null },
    { id: "grid:metric:1000:6500", label: "北關", x: 1000, y: 6500, visibility: "visible_unvisited", current: false, anchor: false, landmark: false, gateway: null, action: null },
    { id: "grid:metric:100:100", label: "東北", x: 100, y: 100, visibility: "visible_visited", current: false, anchor: false, landmark: false, gateway: null, action: null },
  ],
  edges: [
    { source: "grid:metric:0:0", destination: "grid:metric:100:0", label: "e", known: true, traversable: true },
    { source: "grid:metric:100:0", destination: "grid:metric:1000:0", label: "e", known: true, traversable: true },
    { source: "grid:metric:1000:0", destination: "grid:metric:1000:6500", label: "n", known: true, traversable: true },
    { source: "grid:metric:0:0", destination: "grid:metric:100:100", label: "ne", known: true, traversable: false },
  ],
  legend: ["你目前所在的位置", "尚未探索的相鄰位置", "曾經到過的位置", "記憶中的邊界"],
};

function nodeCenter(wrapper, id) {
  const match = wrapper
    .get(`[data-testid="local-map__node--${id}"]`)
    .attributes("transform")
    .match(/-?[\d.]+/g)
    .map(Number);
  return { x: match[0], y: match[1] };
}

  it("projects the island at the exit-driven uniform level and keeps the wire coordinates", () => {
    // render-auto-scaled-minimap-island: the island scales by its one-hop
    // exits (100 m east, 141 m north-east → level 200, radii 50 and 70.7),
    // keeps exact bearings, omits the far context that would land off the
    // square, and draws only the two labelled routes from the current node.
    const model = localMapModelFor(METRIC_PAYLOAD);
    wrapper = mount(LocalMap, { props: { localMap: model } });

    const origin = nodeCenter(wrapper, "grid:metric:0:0");
    const near = nodeCenter(wrapper, "grid:metric:100:0");
    const diagonal = nodeCenter(wrapper, "grid:metric:100:100");
    expect(origin).toEqual({ x: 120, y: 120 });
    expect(near.x - origin.x).toBeCloseTo(50, 6);
    expect(near.y).toBeCloseTo(120, 6);
    expect(diagonal.x - origin.x).toBeCloseTo(50, 6);
    expect(origin.y - diagonal.y).toBeCloseTo(50, 6);
    expect(wrapper.find('[data-testid="local-map__node--grid:metric:1000:0"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="local-map__node--grid:metric:1000:6500"]').exists()).toBe(false);
    expect(wrapper.findAll(".local-map__edge").map((edge) => edge.attributes("data-testid"))).toEqual([
      "local-map__edge--0",
      "local-map__edge--3",
    ]);
    expect(wrapper.get('[data-testid="local-map__scale"]').text()).toBe("格距 40 m");
    // The projection never rewrites the payload's metric coordinates.
    const placed = model.nodes.find((node) => node.id === "grid:metric:1000:6500");
    expect([placed.x, placed.y]).toEqual([1000, 6500]);
  });

  it("keeps exact bearings and distance order when context alone sets a compressed scale", () => {
    // No labelled exit: the context places choose the scale. 100 m beside
    // 430 m puts the nearest inside the exit ring's floor, so the island
    // compresses — still monotonic, still on the true bearings.
    const fractional = {
      ...METRIC_PAYLOAD,
      current_node: "grid:metric:0:0",
      nodes: [
        METRIC_PAYLOAD.nodes[0],
        METRIC_PAYLOAD.nodes[1],
        { id: "grid:metric:0:100", label: "北街", x: 0, y: 100, visibility: "visible_visited", current: false, anchor: false, landmark: false, gateway: null, action: null },
        { id: "grid:metric:250:350", label: "西北", x: 250, y: 350, visibility: "visible_unvisited", current: false, anchor: false, landmark: false, gateway: null, action: null },
      ],
      edges: [],
    };
    wrapper = mount(LocalMap, { props: { localMap: localMapModelFor(fractional) } });
    const origin = nodeCenter(wrapper, "grid:metric:0:0");
    const east = nodeCenter(wrapper, "grid:metric:100:0");
    const north = nodeCenter(wrapper, "grid:metric:0:100");
    const far = nodeCenter(wrapper, "grid:metric:250:350");
    expect(east.y).toBeCloseTo(origin.y, 6);
    expect(north.x).toBeCloseTo(origin.x, 6);
    expect(east.x - origin.x).toBeCloseTo(origin.y - north.y, 6);
    const farRadius = Math.hypot(far.x - origin.x, far.y - origin.y);
    expect(farRadius).toBeGreaterThan(east.x - origin.x);
    expect((far.x - origin.x) / (origin.y - far.y)).toBeCloseTo(250 / 350, 3);
    expect(wrapper.find('[data-testid="local-map__rings"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="local-map__dot-field"]').exists()).toBe(false);
  });

  it("keeps adjacent-node action identity while projecting metric geometry", async () => {
    wrapper = mount(LocalMap, { props: { localMap: localMapModelFor(METRIC_PAYLOAD) } });
    const adjacent = wrapper.get('[data-testid="local-map__node--grid:metric:100:0"]');
    // The projection moves only geometry: the node keeps its canonical id and
    // the exact move descriptor the server committed.
    expect(adjacent.attributes("data-node")).toBe("grid:metric:100:0");
    await adjacent.trigger("click");
    expect(wrapper.emitted("move")).toEqual([
      [{ exit_ref: "e", destination: "grid:metric:100:0" }],
    ]);
  });
});

// render-auto-scaled-minimap-island: LocalMap holds the projection level as
// presentation state keyed by the current node's map, and states the scale
// beside (never inside) the coordinate readout.
describe("LocalMap island scale state (render-auto-scaled-minimap-island)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function street(map, [cx, cy], exits) {
    const currentId = `grid:${map}:${cx}:${cy}`;
    return localMapModelFor({
      schema_version: 1,
      available: true,
      layer: "grid",
      current_node: currentId,
      title: "測試街道圖",
      nodes: [
        { id: currentId, label: "此處", x: cx, y: cy, visibility: "current", current: true, anchor: false, landmark: false, gateway: null, action: null },
        ...exits.map(([x, y], i) => ({
          id: `grid:${map}:${x}:${y}`, label: `出口${i}`, x, y, visibility: "visible_unvisited", current: false, anchor: false, landmark: false, gateway: null,
          action: { kind: "move", exit_ref: `e${i}`, destination: `grid:${map}:${x}:${y}` },
        })),
      ],
      edges: exits.map(([x, y]) => ({ source: currentId, destination: `grid:${map}:${x}:${y}`, label: "n", known: false, traversable: true })),
      legend: [],
    });
  }

  const caption = (w) => w.get('[data-testid="local-map__scale"]').text();

  it.each([true, false])("clears painted gateway feet in the real island (mixed %s)", (mixed) => {
    const model = street("t_gate", [0, 0], [[-120, 800], [120, 800], [800, 0]]);
    model.nodes[1].gateway = { leads_to: "Test gate" };
    if (!mixed) model.nodes[2].gateway = { leads_to: "Other gate" };
    wrapper = mount(LocalMap, { props: { localMap: model } });
    const nodeCenter = (w, id) => {
      const [x, y] = w.get(`[data-node="${id}"]`).attributes("transform").match(/-?[\d.]+/g).map(Number);
      return { x, y };
    };
    const a = nodeCenter(wrapper, "grid:t_gate:-120:800");
    const b = nodeCenter(wrapper, "grid:t_gate:120:800");
    // Both exits carry a move action, so each reserves its travel halo
    // (r 15 plus 1, at the 0.75 island glyph scale), wider than the arch.
    expect(Math.hypot(a.x - b.x, a.y - b.y)).toBeGreaterThanOrEqual(2 * 16 * 0.75 - 0.002);
    expect(nodeCenter(wrapper, "grid:t_gate:0:0")).toEqual({ x: 120, y: 120 });
    expect(nodeCenter(wrapper, "grid:t_gate:800:0")).toEqual({ x: 200, y: 120 });
    expect(wrapper.findAll(".local-map__gate-glyph")).toHaveLength(mixed ? 1 : 2);
  });

  it("keeps the previous level on one map and resets it on another map or layer", async () => {
    // 1100 m selects level 1500 (格距 300 m).
    wrapper = mount(LocalMap, { props: { localMap: street("hyst", [0, 0], [[0, 1100]]) } });
    expect(caption(wrapper)).toBe("格距 300 m");
    // An 850 m exit alone would select 1000 (格距 200 m); one step coarser
    // still fits, so a move on the same map keeps 1500.
    await wrapper.setProps({ localMap: street("hyst", [0, 1100], [[0, 1950]]) });
    expect(caption(wrapper)).toBe("格距 300 m");
    // The same geometry on another map selects afresh.
    await wrapper.setProps({ localMap: street("other", [0, 1100], [[0, 1950]]) });
    expect(caption(wrapper)).toBe("格距 200 m");
    // Leaving the coordinate-bearing lattice drops the memory and the caption.
    await wrapper.setProps({ localMap: street("hyst", [0, 0], [[0, 1100]]) });
    await wrapper.setProps({ localMap: localMapModelFor(LOCAL_MAP_INTERIOR_SAMPLE) });
    expect(wrapper.find('[data-testid="local-map__scale"]').exists()).toBe(false);
    await wrapper.setProps({ localMap: street("hyst", [0, 1100], [[0, 1950]]) });
    expect(caption(wrapper)).toBe("格距 200 m");
  });

  it("states the scale as its own element beside the unchanged readout", () => {
    wrapper = mount(LocalMap, { props: { localMap: street("hyst", [3500, 2850], [[3500, 3700]]) } });
    const scale = wrapper.get('[data-testid="local-map__scale"]');
    const readout = wrapper.get('[data-testid="local-map-detail"]');
    expect(readout.text()).toBe("座標 3500,2850");
    expect(scale.element.contains(readout.element)).toBe(false);
    expect(readout.element.contains(scale.element)).toBe(false);
    expect(scale.text()).toMatch(/^格距 \d+ (?:m|km)$/);
    // The island's only distance figure is that caption.
    const text = wrapper.text().replace(scale.text(), "");
    expect(text).not.toMatch(/\d+\s*(?:m|km)\b/);
  });

  it("states compression by text and no caption on coordinate-free layers", () => {
    wrapper = mount(LocalMap, { props: { localMap: localMapModelFor(LOCAL_MAP_SAMPLE) } });
    expect(caption(wrapper)).toBe("距離壓縮");
    wrapper.unmount();
    wrapper = mount(LocalMap, { props: { localMap: localMapModelFor(LOCAL_MAP_INSTANCE_SAMPLE) } });
    expect(wrapper.find('[data-testid="local-map__scale"]').exists()).toBe(false);
  });
});

describe("LocalMap gateways and island labels (label-minimap-exits-and-gateways)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountPayload(payload) {
    wrapper = mount(LocalMap, { props: { localMap: localMapModelFor(payload) }, attachTo: document.body });
    return wrapper;
  }

  const translateOf = (el) => {
    const match = el.closest("[transform]")?.getAttribute("transform")?.match(/translate\(\s*([-\d.e]+)[\s,]+([-\d.e]+)/);
    return match ? { x: Number(match[1]), y: Number(match[2]) } : { x: 0, y: 0 };
  };

  // Every drawn island label line as a box in user units (centred text, 16 px
  // step, monospace cells), joined to the label element it belongs to.
  function labelBoxes(w) {
    const boxes = [];
    for (const text of w.findAll(".local-map__node-label")) {
      const group = text.element.closest(".local-map__node");
      const origin = group ? translateOf(group) : { x: 0, y: 0 };
      for (const tspan of text.findAll("tspan")) {
        const width = textCells(tspan.text()) * CELL_EM * 16;
        const x = origin.x + Number(tspan.attributes("x"));
        const y = origin.y + Number(tspan.attributes("y"));
        boxes.push({ owner: text.element, x0: x - width / 2, x1: x + width / 2, y0: y - 0.8 * 16, y1: y + 0.25 * 16 });
      }
    }
    return boxes;
  }

  it("draws the current gate room's here seal, room name and 通往 line on the city side", () => {
    const w = mountPayload(LOCAL_MAP_ALTORIA_SOUTH_GATE_SAMPLE);
    const current = w.get('[data-node="grid:capital_altoria:3050:150"]');
    // As on the area map, the current glyph wins over the gate arch.
    expect(current.find('[data-testid="local-map__gate-glyph"]').exists()).toBe(false);
    expect(current.find(".local-map__marker--current").exists()).toBe(true);
    const lines = current.findAll(".local-map__node-label tspan").map((t) => t.text());
    expect(lines).toEqual(["南門", "通往 西部丘陵與谷地"]);
    expect(current.findAll(".local-map__node-label tspan")[1].classes()).toContain("local-map__via");
  });

  it("draws the far side as a labelled exit-ring stub, never as a node", () => {
    const w = mountPayload(LOCAL_MAP_ALTORIA_SOUTH_GATE_SAMPLE);
    expect(w.find('[data-node^="wild:"]').exists()).toBe(false);
    const stubs = w.findAll(".local-map__stub");
    expect(stubs).toHaveLength(1);
    const arrow = stubs[0].get(".local-map__stub-arrow");
    // South of the gate: bearing 180 on the exit ring (radius 88).
    expect(arrow.attributes("transform")).toBe("translate(120, 208) rotate(180)");
    expect(stubs[0].get(".local-map__stub-label").text()).toBe("通往 西部丘陵與谷地");
    expect(stubs[0].classes()).not.toContain("local-map__stub--locked");
  });

  it("makes an actionable stub a named native button that moves exactly once", async () => {
    const w = mountPayload(LOCAL_MAP_ALTORIA_SOUTH_GATE_SAMPLE);
    const buttons = w.findAll(".local-map__stub-button");
    expect(buttons).toHaveLength(1);
    const button = buttons[0];
    expect(button.element.tagName).toBe("BUTTON");
    expect(button.attributes("type")).toBe("button");
    expect(button.attributes("aria-label")).toBe("往 西部丘陵與谷地 移動");
    button.element.focus();
    expect(document.activeElement).toBe(button.element);
    // The platform turns Enter/Space into the click; no key handler of its
    // own can add a second submission.
    await button.trigger("keydown", { key: "Enter" });
    await button.trigger("keydown", { key: " " });
    expect(w.emitted("move")).toBeUndefined();
    await button.trigger("click");
    expect(w.emitted("move")).toEqual([[{ exit_ref: "e_south_gate_wild", destination: "wild:elosern:860:1076" }]]);
    expect(w.emitted("open-map")).toBeUndefined();
    // The island's tab order: the full-map affordance first, then the stub.
    const stops = w.findAll("button").map((b) => b.attributes("data-testid"));
    expect(stops).toEqual(["local-map__expand", "local-map__stub-button--0"]);
  });

  it("keeps Space on the stub button away from the shell's document key routing", async () => {
    const w = mountPayload(LOCAL_MAP_ALTORIA_SOUTH_GATE_SAMPLE);
    const seen = [];
    const listener = (event) => seen.push(event.key);
    document.addEventListener("keydown", listener);
    try {
      const button = w.get(".local-map__stub-button");
      await button.trigger("keydown", { key: " " });
      await button.trigger("keydown", { key: "Enter" });
      // Space stops at the button (the platform activates it on keyup);
      // Enter still bubbles, where the bridge already leaves buttons alone.
      expect(seen).toEqual(["Enter"]);
    } finally {
      document.removeEventListener("keydown", listener);
    }
  });

  it("ignores a held Enter's repeated activations on the stub button", () => {
    const w = mountPayload(LOCAL_MAP_ALTORIA_SOUTH_GATE_SAMPLE);
    const button = w.get(".local-map__stub-button").element;
    const first = new KeyboardEvent("keydown", { key: "Enter", bubbles: true, cancelable: true });
    const held = new KeyboardEvent("keydown", { key: "Enter", repeat: true, bubbles: true, cancelable: true });
    button.dispatchEvent(first);
    button.dispatchEvent(held);
    expect(first.defaultPrevented).toBe(false);
    expect(held.defaultPrevented).toBe(true);
  });

  it("keeps unleadered stub labels separate from the compact arrow button", () => {
    const w = mountPayload(LOCAL_MAP_ALTORIA_SOUTH_GATE_SAMPLE);
    const style = w.get(".local-map__stub-button").attributes("style");
    const pct = (key) => Number(style.match(new RegExp(`${key}: ([\\d.]+)%`))[1]) * 2.4;
    expect(pct("width")).toBeCloseTo(22, 6);
    expect(pct("height")).toBeCloseTo(22, 6);
    expect(w.find(".local-map__stub-hit").exists()).toBe(true);
  });

  it("gives a leadered stub label its own hit area instead of a spanning button", () => {
    // The east gate as the shipped capital presents it: the street exit
    // west, the gate's far side east on the rim, and the remembered south
    // gate's name whole on the right edge, and two street exits flanking the
    // stub's bearing north-east and south-east, so the stub's label is
    // pushed out onto a leader line (at the island glyph scale the plain
    // east-gate neighbourhood alone leaves its label a free position).
    const node = (id, label, x, y, visibility, extra = {}) => ({
      id, label, x, y, visibility, current: visibility === "current", anchor: false, landmark: false,
      gateway: null, action: null, ...extra,
    });
    const payload = {
      schema_version: 1, available: true, layer: "grid", current_node: "grid:cap:6500:3010", title: "東門街道圖",
      nodes: [
        node("grid:cap:6500:3010", "東門", 6500, 3010, "current", { gateway: { leads_to: "荊棘荒林" } }),
        node("grid:cap:5380:2850", "東市", 5380, 2850, "visible_unvisited", {
          action: { kind: "move", exit_ref: "76", destination: "grid:cap:5380:2850" },
        }),
        node("grid:cap:4380:3000", "公會前", 4380, 3000, "visible_unvisited"),
        node("grid:cap:4560:3920", "大神殿前", 4560, 3920, "visible_unvisited"),
        node("wild:elosern:503:501", "荊棘荒林", 6510, 3010, "visible_visited", {
          action: { kind: "move", exit_ref: "105", destination: "wild:elosern:503:501" },
        }),
        node("grid:cap:3050:150", "荊棘荒林", 3050, 150, "remembered", { landmark: true, gateway: { leads_to: "荊棘荒林" } }),
        node("grid:cap:7100:3310", "東巷", 7100, 3310, "visible_unvisited", {
          action: { kind: "move", exit_ref: "78", destination: "grid:cap:7100:3310" },
        }),
        node("grid:cap:7100:2710", "南巷", 7100, 2710, "visible_unvisited", {
          action: { kind: "move", exit_ref: "79", destination: "grid:cap:7100:2710" },
        }),
      ],
      edges: [
        { source: "grid:cap:6500:3010", destination: "grid:cap:7100:3310", label: "ne", known: false, traversable: true },
        { source: "grid:cap:6500:3010", destination: "grid:cap:7100:2710", label: "se", known: false, traversable: true },
        { source: "grid:cap:6500:3010", destination: "grid:cap:5380:2850", label: "w", known: false, traversable: true },
        { source: "grid:cap:6500:3010", destination: "grid:cap:4380:3000", label: "", known: false, traversable: false },
        { source: "grid:cap:6500:3010", destination: "grid:cap:4560:3920", label: "", known: false, traversable: false },
        { source: "grid:cap:6500:3010", destination: "wild:elosern:503:501", label: "e", known: true, traversable: true },
      ],
      legend: [],
    };
    const w = mountPayload(payload);
    const stub = w.get(".local-map__stub");
    expect(stub.find(".local-map__leader").exists()).toBe(true);
    const style = w.get(".local-map__stub-button").attributes("style");
    const pct = (key) => Number(style.match(new RegExp(`${key}: ([\\d.]+)%`))[1]) * 2.4;
    // The button is the arrow's own box (2 × 9 plus padding), and the far
    // label carries its own hit area inside it.
    expect(pct("width")).toBeCloseTo(2 * 9 + 4, 6);
    expect(pct("height")).toBeCloseTo(2 * 9 + 4, 6);
    expect(w.find(".local-map__stub-button .local-map__stub-hit").exists()).toBe(true);
  });

  it("keeps a locked gateway visible and inert", async () => {
    const w = mountPayload(LOCAL_MAP_ALTORIA_SOUTH_GATE_LOCKED_SAMPLE);
    const stub = w.get(".local-map__stub");
    expect(stub.classes()).toContain("local-map__stub--locked");
    expect(stub.get(".local-map__stub-label").text()).toBe("通往 西部丘陵與谷地");
    expect(w.find(".local-map__stub-button").exists()).toBe(false);
    expect(stub.attributes("tabindex")).toBeUndefined();
    await stub.trigger("click");
    expect(w.emitted("move")).toBeUndefined();
    // Its route reads blocked by shape (dashed), not colour.
    expect(stub.get(".local-map__edge").classes()).toContain("local-map__edge--blocked");
  });

  it("offers the city return from the wilderness without drawing city streets", async () => {
    const w = mountPayload(LOCAL_MAP_WILDERNESS_RETURN_SAMPLE);
    expect(w.find('[data-node^="grid:"]').exists()).toBe(false);
    const button = w.get(".local-map__stub-button");
    expect(button.attributes("aria-label")).toBe("往 聖潔王都 移動");
    expect(w.get(".local-map__stub-label").text()).toBe("通往 聖潔王都");
    await button.trigger("click");
    expect(w.emitted("move")).toEqual([[{ exit_ref: "e_return_n", destination: "grid:capital_altoria:3050:150" }]]);
    // The neighbours repeating the current region's name stay unlabelled;
    // each keeps its full name as the label's title-free accessible name
    // through its node group and its move action.
    const repeated = LOCAL_MAP_WILDERNESS_RETURN_SAMPLE.nodes.filter(
      (n) => n.visibility !== "current" && n.id.startsWith("wild:"),
    );
    expect(repeated.length).toBe(7);
    for (const node of repeated) {
      const group = w.get(`[data-node="${node.id}"]`);
      expect(group.find(".local-map__node-label").exists()).toBe(false);
      expect(group.find(".local-map__actionable").exists()).toBe(true);
    }
  });

  it("labels a differing wilderness region but suppresses only the repeated one", () => {
    const w = mountPayload(LOCAL_MAP_WILDERNESS_METRIC_SAMPLE);
    const labelled = LOCAL_MAP_WILDERNESS_METRIC_SAMPLE.nodes.filter(
      (n) => n.visibility !== "current" && n.label !== LOCAL_MAP_WILDERNESS_METRIC_SAMPLE.title,
    );
    expect(labelled).toHaveLength(3);
    for (const node of labelled) {
      expect(w.get(`[data-node="${node.id}"] .local-map__node-label tspan`).text()).toBe(node.label.slice(0, 4));
    }
  });

  it("keeps every crowded exit labelled, clear of markers, with remembered names whole", () => {
    const w = mountPayload(LOCAL_MAP_CROWDED_LABELS_SAMPLE);
    const payload = LOCAL_MAP_CROWDED_LABELS_SAMPLE;
    const exits = payload.edges.filter((e) => e.label).map((e) => e.destination);
    for (const id of exits) {
      expect(w.get(`[data-node="${id}"] .local-map__node-label tspan`).text().length).toBeGreaterThan(0);
    }
    // The current label found none of its eight spots free: it keeps its
    // classic truncated place below the marker (design.md), painted last so
    // no neighbour covers it.
    const current = w.get(`[data-node="${payload.current_node}"]`);
    expect(current.get(".local-map__node-label tspan").text()).toBe("交易十字…");
    expect(Number(current.get(".local-map__node-label tspan").attributes("y"))).toBeCloseTo(14 * 0.75 + 3 + 0.8 * 16, 6);
    expect(w.findAll(".local-map__node").at(-1).attributes("data-node")).toBe(payload.current_node);
    // Every other label line stays in the square, clear of every drawn
    // exit and current marker's footprint; a label pushed out to a leader
    // line in this deliberately overfull square may at worst cover a quiet
    // context dot (the least-overlap last resort weighs markers heaviest).
    const currentLabel = current.get(".local-map__node-label").element;
    const markers = w.findAll(".local-map__node").map((g) => ({ ...translateOf(g.element), r: g.find(".local-map__gate-glyph").exists() ? 14 : g.classes().includes("local-map__node--context") ? 3 : 9 }));
    for (const box of labelBoxes(w).filter((b) => b.owner !== currentLabel)) {
      expect(box.x0).toBeGreaterThanOrEqual(0);
      expect(box.x1).toBeLessThanOrEqual(240);
      expect(box.y0).toBeGreaterThanOrEqual(0);
      expect(box.y1).toBeLessThanOrEqual(240);
      const leadered = !!box.owner.parentNode.querySelector(":scope > .local-map__leader");
      for (const m of markers) {
        if (leadered && m.r === 3) continue;
        const nx = Math.min(Math.max(m.x, box.x0), box.x1);
        const ny = Math.min(Math.max(m.y, box.y0), box.y1);
        expect(Math.hypot(m.x - nx, m.y - ny), `${box.owner.textContent} vs marker ${m.x},${m.y}`).toBeGreaterThanOrEqual(m.r);
      }
    }
    // The east gate is a same-layer gateway: arch plus 通往 line.
    const east = w.get('[data-node="grid:trade_crossroads:1900:1010"]');
    expect(east.find('[data-testid="local-map__gate-glyph"]').exists()).toBe(true);
    expect(east.findAll(".local-map__node-label tspan").map((t) => t.text())[1]).toMatch(/^通往 東部大平/);
    // Remembered names are drawn whole on the rim, never shortened.
    for (const node of payload.nodes.filter((n) => n.visibility === "remembered")) {
      const text = w.get(`[data-testid="local-map__edge-marker--${node.id}"] .local-map__edge-marker-name--island`);
      expect(text.text().replace(/\s+/g, "")).toBe(node.label);
    }
  });
});
