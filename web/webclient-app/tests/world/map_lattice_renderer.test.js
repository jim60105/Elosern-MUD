import { mount } from "@vue/test-utils";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";
import MapLattice from "../../components/MapLattice.vue";
import LocalMapModel from "../../lib/local_map.js";
import { CELL_EM, textCells } from "../../lib/mono_cells.js";
import {
  LOCAL_MAP_INSTANCE_SAMPLE,
  LOCAL_MAP_INTERIOR_SAMPLE,
  LOCAL_MAP_SAMPLE,
  LOCAL_MAP_WILDERNESS_SAMPLE,
  LOCAL_MAP_ALTORIA_PLAZA_SAMPLE,
  LOCAL_MAP_ALTORIA_SOUTH_GATE_SAMPLE,
  LOCAL_MAP_CIARAN_PLAZA_SAMPLE,
  LOCAL_MAP_EXTREME_RATIO_SAMPLE,
  LOCAL_MAP_WILDERNESS_METRIC_SAMPLE,
  LOCAL_MAP_CROWDED_LABELS_SAMPLE,
  localMapModelFor,
} from "../../stories/fixtures.js";
import { HALO_R, gatePath } from "@elosern/map-view";
import { ISLAND_GLYPH_SCALE } from "../../lib/map_glyphs.js";
import { spreadExits } from "../../lib/minimap_projection.js";
import { MARKER_CURRENT_RING_R } from "../../composables/use-map-lattice-geometry.js";
import {
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
    // A bare mount is the island's fixed 240-unit square; the remembered
    // fixture node (5, 5) outside the in-view extent stands on its rim.
    const svg = w.find("svg.local-map__lattice");
    expect(Number(svg.attributes("width"))).toBe(240);
    expect(Number(svg.attributes("height"))).toBe(240);
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

});

// render-auto-scaled-minimap-island: the fixed-canvas lattice island draws
// the automatic projection; the graph variant never projects.
describe("MapLattice island projection (render-auto-scaled-minimap-island)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  const ISLAND = { canvasSize: 240, showAxis: true, fogVignette: true, markerNames: true };

  function centreOf(w, id) {
    const [x, y] = w
      .get(`[data-node="${id}"]`)
      .attributes("transform")
      .match(/-?[\d.]+/g)
      .map(Number);
    return { x, y };
  }

  it("fallback projection clears the actual gate feet and stroke", () => {
    const payload = structuredClone(LOCAL_MAP_SAMPLE);
    payload.layer = "grid";
    payload.current_node = "grid:t_gate:0:0";
    payload.nodes = [[0, 0], [-120, 800], [120, 800]].map(([x, y], i) => ({
      id: `grid:t_gate:${x}:${y}`, x, y, label: `Gate ${i}`, visibility: i ? "visible_unvisited" : "current",
      current: i === 0, anchor: false, landmark: false,
      gateway: i ? { leads_to: "Synthetic gate" } : null,
      action: i ? { kind: "move", exit_ref: `${i}`, destination: `grid:t_gate:${x}:${y}` } : null,
    }));
    payload.edges = payload.nodes.slice(1).map((n) => ({ source: payload.current_node, destination: n.id, label: "n", known: true, traversable: true }));
    wrapper = mount(MapLattice, { props: { localMap: localMapModelFor(payload), ...ISLAND } });
    const a = centreOf(wrapper, payload.nodes[1].id);
    const b = centreOf(wrapper, payload.nodes[2].id);
    // Each actionable gate reserves its travel halo (wider than the arch),
    // at the 0.75 island glyph scale.
    expect(Math.hypot(a.x - b.x, a.y - b.y)).toBeGreaterThanOrEqual(2 * 16 * 0.75 - 0.002);
    expect(wrapper.findAll(".local-map__gate-glyph")).toHaveLength(2);
    // The full map's filled gate arch, unchanged.
    expect(wrapper.get(".local-map__gate-glyph").attributes("d")).toBe("M-8 8 V-2 A8 8 0 0 1 8 -2 V8 Z");
  });

  it("draws the retained unit-distance background as a labelled 1 m ring", () => {
    wrapper = mount(MapLattice, { props: { localMap: localMapModelFor(LOCAL_MAP_SAMPLE), ...ISLAND } });
    const ring = wrapper.get('.local-map__ring[data-distance="1"]');
    expect(Number(ring.attributes("r"))).toBe(66);
    expect(wrapper.findAll(".local-map__ring-label").some((el) => el.text() === "1 m")).toBe(true);
  });

  it("draws current at the centre, every same-layer exit inside the exit ring and only exit routes", () => {
    const payload = LOCAL_MAP_ALTORIA_PLAZA_SAMPLE;
    wrapper = mount(MapLattice, { props: { localMap: localMapModelFor(payload), ...ISLAND } });
    const current = payload.current_node;
    expect(centreOf(wrapper, current)).toEqual({ x: 120, y: 120 });
    const exits = payload.edges.filter((edge) => edge.label).map((edge) => edge.destination);
    expect(exits).toHaveLength(4);
    for (const id of exits) {
      const { x, y } = centreOf(wrapper, id);
      const radius = Math.hypot(x - 120, y - 120);
      expect(radius).toBeGreaterThanOrEqual(36 - 1e-6);
      expect(radius).toBeLessThanOrEqual(88 + 1e-6);
      expect(wrapper.get(`[data-node="${id}"]`).find(".local-map__marker").exists()).toBe(true);
    }
    // Exactly one drawn route per exit, each from the current node's centre.
    const lines = wrapper.findAll(".local-map__edge");
    expect(lines).toHaveLength(exits.length);
    for (const line of lines) {
      expect([line.attributes("x1"), line.attributes("y1")]).toEqual(["120", "120"]);
    }
    // Two-hop context: a dot inside the square or no group at all.
    const context = payload.nodes.filter(
      (node) => node.id !== current && !exits.includes(node.id) && node.visibility !== "remembered",
    );
    let drawnContext = 0;
    for (const node of context) {
      const group = wrapper.find(`[data-node="${node.id}"]`);
      if (!group.exists()) continue;
      drawnContext += 1;
      const { x, y } = centreOf(wrapper, node.id);
      expect(x >= 0 && x <= 240 && y >= 0 && y <= 240).toBe(true);
      expect(group.find(".local-map__context-dot").exists()).toBe(true);
      expect(group.find(".local-map__marker").exists()).toBe(false);
      // Its name only where a free spot remains, in the quiet context tier.
      const label = group.find(".local-map__node-label");
      if (label.exists()) expect(label.classes()).toContain("local-map__node-label--context");
    }
    expect(drawnContext).toBeGreaterThan(0);
    expect(drawnContext).toBeLessThan(context.length);
  });

  it("never draws a cross-layer gate target as a node", () => {
    wrapper = mount(MapLattice, {
      props: { localMap: localMapModelFor(LOCAL_MAP_ALTORIA_SOUTH_GATE_SAMPLE), ...ISLAND },
    });
    expect(wrapper.find('[data-node^="wild:"]').exists()).toBe(false);
    // The street exit keeps its route; the gate's far side is one exit stub
    // on the exit ring (label-minimap-exits-and-gateways), whose own route
    // lives inside the stub group, never in the node layer.
    expect(wrapper.findAll(".local-map__edge").filter((line) => !line.element.closest(".local-map__stub"))).toHaveLength(1);
    expect(wrapper.findAll(".local-map__stub")).toHaveLength(1);
  });

  it("a context dot carries no activation", async () => {
    wrapper = mount(MapLattice, { props: { localMap: localMapModelFor(LOCAL_MAP_ALTORIA_PLAZA_SAMPLE), ...ISLAND } });
    const dot = wrapper.find(".local-map__node--context");
    expect(dot.exists()).toBe(true);
    expect(dot.attributes("tabindex")).toBeUndefined();
    expect(dot.attributes("role")).toBeUndefined();
    await dot.trigger("click");
    await dot.trigger("keydown", { key: "Enter" });
    expect(wrapper.emitted("select")).toBeUndefined();
    expect(wrapper.emitted("move")).toBeUndefined();
  });

  it("compressed mode replaces the dot field with labelled distance rings", () => {
    wrapper = mount(MapLattice, { props: { localMap: localMapModelFor(LOCAL_MAP_EXTREME_RATIO_SAMPLE), ...ISLAND } });
    expect(wrapper.find('[data-testid="local-map__dot-field"]').exists()).toBe(false);
    const rings = wrapper.get('[data-testid="local-map__rings"]');
    expect(rings.attributes("aria-hidden")).toBe("true");
    expect(rings.classes()).not.toContain("local-map__marker");
    const circles = rings.findAll("circle.local-map__ring");
    const labels = rings.findAll("text.local-map__ring-label");
    expect(circles.length).toBeGreaterThan(0);
    expect(labels).toHaveLength(circles.length);
    for (const label of labels) {
      expect(label.text()).toMatch(/^\d+ (?:m|km)$/);
      expect(label.attributes("style")).toContain("font-size: 16px");
    }
    // Radii ascend with the stated distance (the mapping is monotonic).
    const radii = circles.map((c) => Number(c.attributes("r")));
    expect([...radii].sort((a, b) => a - b)).toEqual(radii);
    // Each figure stays on its own ring, never on an exit's own bearing: the
    // exits stand east, north-west and south. A figure whose preferred
    // diagonal is taken by a navigation label moves along its ring
    // (label-minimap-exits-and-gateways), so the figures no longer stack.
    labels.forEach((label, i) => {
      const dx = Number(label.attributes("x")) - 120;
      const dy = Number(label.attributes("y")) - 120;
      expect(Math.hypot(dx, dy)).toBeCloseTo(radii[i], 6);
      const bearing = ((Math.atan2(dx, -dy) * 180) / Math.PI + 360) % 360;
      for (const exit of [90, 315, 180]) {
        const gap = Math.abs(((bearing - exit + 540) % 360) - 180);
        expect(gap).toBeGreaterThanOrEqual(20);
      }
    });
  });

  it("uniform mode draws the dot field inside a pan group and no rings", () => {
    wrapper = mount(MapLattice, {
      props: { localMap: localMapModelFor(LOCAL_MAP_CIARAN_PLAZA_SAMPLE), ...ISLAND, panOnMove: true },
    });
    expect(wrapper.find('[data-testid="local-map__rings"]').exists()).toBe(false);
    const field = wrapper.get('[data-testid="map-lattice__pan--field"]');
    expect(field.classes()).toContain("map-lattice__pan");
    expect(field.find('[data-testid="local-map__dot-field"]').exists()).toBe(true);
  });

  it("holds the graph variant off the projection", () => {
    const model = localMapModelFor(LOCAL_MAP_INTERIOR_SAMPLE);
    const graph = mount(MapLattice, { props: { localMap: model, variant: "graph" } });
    // The radial graph draws every placed room at its radial position: no
    // context tier, no world-anchored dot field and no distance rings.
    expect(graph.findAll(".local-map__node")).toHaveLength(model.radial.nodes.length);
    expect(graph.find(".local-map__node--context").exists()).toBe(false);
    expect(graph.find('[data-testid="local-map__dot-field"]').exists()).toBe(false);
    expect(graph.find('[data-testid="local-map__rings"]').exists()).toBe(false);
    graph.unmount();
  });

  it("keeps every island label inside the square", () => {
    for (const payload of [LOCAL_MAP_WILDERNESS_METRIC_SAMPLE, LOCAL_MAP_ALTORIA_PLAZA_SAMPLE, LOCAL_MAP_EXTREME_RATIO_SAMPLE]) {
      const w = mount(MapLattice, { props: { localMap: localMapModelFor(payload), ...ISLAND } });
      for (const group of w.findAll(".local-map__node")) {
        const [cx, cy] = group.attributes("transform").match(/-?[\d.]+/g).map(Number);
        for (const line of group.findAll(".local-map__node-label tspan")) {
          const width = textCells(line.text().trim()) * CELL_EM * 16;
          const x = cx + Number(line.attributes("x") ?? 0);
          const y = cy + Number(line.attributes("y"));
          expect(x - width / 2).toBeGreaterThanOrEqual(-1e-6);
          expect(x + width / 2).toBeLessThanOrEqual(240 + 1e-6);
          expect(y + 4).toBeLessThanOrEqual(240);
          expect(y - 13).toBeGreaterThanOrEqual(0);
        }
      }
      w.unmount();
    }
  });
});

describe("MapLattice island rim markers (render-auto-scaled-minimap-island)", () => {
  it("keeps two remembered diamonds either side of a diagonal apart at the corner", () => {
    const node = (id, x, y, visibility) => ({
      id, label: id, x, y, visibility, current: visibility === "current", anchor: false, landmark: false, gateway: null, action: null,
    });
    const payload = {
      schema_version: 1, available: true, layer: "grid", current_node: "grid:rim:0:0", title: "rim",
      nodes: [
        node("grid:rim:0:0", 0, 0, "current"),
        node("grid:rim:100:0", 100, 0, "visible_unvisited"),
        // Bearings about 44° and 46°: one leaves through the top, one
        // through the right side, both next to the north-east corner.
        node("grid:rim:9657:10000", 9657, 10000, "remembered"),
        node("grid:rim:10000:9657", 10000, 9657, "remembered"),
      ],
      edges: [{ source: "grid:rim:0:0", destination: "grid:rim:100:0", label: "e", known: true, traversable: true }],
      legend: [],
    };
    const w = mount(MapLattice, { props: { localMap: localMapModelFor(payload), canvasSize: 240, markerNames: true } });
    const markers = w.vm.fittedEdgeMarkers;
    expect(markers).toHaveLength(2);
    expect(new Set(markers.map((m) => m.side)).size).toBe(2);
    const [a, b] = markers;
    // Rotated diamonds (half 7) clear once their L1 distance exceeds 2·reach.
    expect(Math.abs(a.x - b.x) + Math.abs(a.y - b.y)).toBeGreaterThanOrEqual(2 * Math.SQRT2 * 7);
    for (const m of markers) {
      expect(m.x).toBeGreaterThanOrEqual(0);
      expect(m.x).toBeLessThanOrEqual(240);
      expect(m.y).toBeGreaterThanOrEqual(0);
      expect(m.y).toBeLessThanOrEqual(240);
    }
    w.unmount();
  });

  it("draws no distance background for a coordinate-free payload forced onto the lattice island", () => {
    const w = mount(MapLattice, {
      props: { localMap: localMapModelFor(LOCAL_MAP_INSTANCE_SAMPLE), variant: "lattice", canvasSize: 240 },
    });
    expect(w.find('[data-testid="local-map__rings"]').exists()).toBe(false);
    expect(w.find('[data-testid="local-map__dot-field"]').exists()).toBe(false);
    w.unmount();
  });
});

// The island draws the area map's node glyphs (MapNodeGlyph) inside one
// group scaled by the single island glyph scale; footprints, label
// clearance, the stub start and the aim ring follow the same scale.
describe("the minimap island draws the area map's node glyphs", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  const glyphScales = (w) => w.findAll(".local-map__glyph > g.map-glyph").map((g) => g.attributes("transform"));
  const actionableId = (payload) => String(payload.nodes.find((n) => n.action && n.visibility !== "current").id);

  it("draws the lattice glyph group at the island scale, whatever markerScale", () => {
    expect(ISLAND_GLYPH_SCALE).toBe(0.75);
    for (const markerScale of [1, 2]) {
      wrapper = mount(MapLattice, { props: { localMap: localMapModelFor(LOCAL_MAP_SAMPLE), markerScale } });
      const scales = glyphScales(wrapper);
      expect(scales.length).toBeGreaterThan(0);
      for (const t of scales) expect(t).toBe("scale(0.75)");
      wrapper.unmount();
      wrapper = null;
    }
  });

  it("draws the graph glyph group at the island scale times markerScale, with the label below the scaled footprint", () => {
    for (const markerScale of [1, 2]) {
      const model = localMapModelFor(LOCAL_MAP_INTERIOR_SAMPLE);
      wrapper = mount(MapLattice, { props: { localMap: model, variant: model.layoutVariant, markerScale } });
      expect(model.layoutVariant).toBe("graph");
      for (const t of glyphScales(wrapper)) expect(t).toBe(`scale(${0.75 * markerScale})`);
      // The graph label baseline: the largest base footprint (16) at the
      // glyph scale, a 2-unit margin, then the 16-unit type step.
      const label = wrapper.get(".local-map__node-label");
      expect(Number(label.attributes("y"))).toBeCloseTo(16 * 0.75 * markerScale + 2 + 16, 9);
      wrapper.unmount();
      wrapper = null;
    }
  });

  it("keeps base shapes inside the scaled group, identical to the area map's", () => {
    wrapper = mount(MapLattice, { props: { localMap: localMapModelFor(LOCAL_MAP_ALTORIA_SOUTH_GATE_SAMPLE) } });
    const here = wrapper.get(".local-map__here > g.map-glyph");
    expect(here.attributes("transform")).toBe("scale(0.75)");
    expect(here.findAll(".map-glyph__here-glow, .map-glyph__here-ring, .map-glyph__here-dot").map((c) => c.attributes("r"))).toEqual(["14", "10", "6"]);
    for (const halo of wrapper.findAll(".local-map__actionable")) expect(halo.attributes("r")).toBe("15");
    expect(gatePath()).toBe("M-8 8 V-2 A8 8 0 0 1 8 -2 V8 Z");
  });

  it("starts a gateway stub at the scaled travel halo's edge", () => {
    wrapper = mount(MapLattice, { props: { localMap: localMapModelFor(LOCAL_MAP_ALTORIA_SOUTH_GATE_SAMPLE) } });
    const line = wrapper.get(".local-map__stub .local-map__edge");
    const r = Math.hypot(Number(line.attributes("x1")) - 120, Number(line.attributes("y1")) - 120);
    expect(r).toBeCloseTo((HALO_R + 1) * 0.75, 9);
    expect(r).toBeCloseTo(12, 9);
  });

  it("keeps the aim ring's inner stroke edge outside the scaled travel halo", () => {
    expect(MARKER_CURRENT_RING_R).toBeCloseTo(HALO_R * 0.75 + 2, 12);
    // The ring's 1.6 px stroke against the halo's 1.2 stroke at the scale.
    expect(MARKER_CURRENT_RING_R - 0.8).toBeGreaterThan((15 + 0.6) * 0.75);
    const id = actionableId(LOCAL_MAP_SAMPLE);
    wrapper = mount(MapLattice, { props: { localMap: localMapModelFor(LOCAL_MAP_SAMPLE), aimedNode: id } });
    const node = wrapper.get(`[data-testid="local-map__node--${id}"]`);
    expect(Number(node.get('[data-testid="local-map__aim-ring"]').attributes("r"))).toBeCloseTo(13.25, 9);
    expect(node.find(".local-map__actionable").exists()).toBe(true);
  });

  it("spreads exits by footprints at the island scale", () => {
    // Two actionable exits at r 80 whose centres are 20 units apart: inside
    // the scaled clearance 2 × 16 × 0.75 = 24, so they spread.
    const theta = (2 * Math.asin(10 / 80) * 180) / Math.PI;
    const exits = [
      { bearing: 0, radius: 80, order: 0, node: { action: { kind: "move" } } },
      { bearing: theta, radius: 80, order: 1, node: { action: { kind: "move" } } },
    ];
    spreadExits(exits);
    const gap = ((((exits[1].bearing - exits[0].bearing) % 360) + 540) % 360) - 180;
    expect(gap).toBeGreaterThan(theta + 1e-6);
    // Spread to the scaled clearance: a chord of 24 at r 80.
    expect(gap).toBeCloseTo((2 * Math.asin(12 / 80) * 180) / Math.PI, 6);
  });

  it("holds no island marker-ladder paint of its own", () => {
    const css = readFileSync(resolve(process.cwd(), "web/webclient-app/components/map-lattice.css"), "utf-8");
    expect(css).not.toMatch(/\.local-map__marker[\w-]*\s*[{,]/);
    expect(css).not.toMatch(/\.local-map__actionable\s*[{,]/);
    expect(css).not.toMatch(/\.local-map__gate-glyph\s*[{,]/);
    expect(css).not.toMatch(/\.local-map__landmark\s*[{,]/);
  });

  it("rescales glyph, footprint, label clearance, stub start and aim ring from the one constant", async () => {
    vi.resetModules();
    vi.doMock("../../lib/map_glyphs.js", async (importOriginal) => ({
      ...(await importOriginal()),
      ISLAND_GLYPH_SCALE: 0.5,
    }));
    try {
      const { default: Lattice } = await import("../../components/MapLattice.vue");
      const { default: Island } = await import("../../components/LocalMap.vue");
      const { spreadExits: spread } = await import("../../lib/minimap_projection.js");
      const { MARKER_CURRENT_RING_R: ringR } = await import("../../composables/use-map-lattice-geometry.js");
      const id = actionableId(LOCAL_MAP_SAMPLE);
      wrapper = mount(Lattice, { props: { localMap: localMapModelFor(LOCAL_MAP_SAMPLE), aimedNode: id } });
      for (const t of glyphScales(wrapper)) expect(t).toBe("scale(0.5)");
      // Aim ring: HALO_R × 0.5 + 2.
      expect(ringR).toBeCloseTo(9.5, 12);
      expect(Number(wrapper.get('[data-testid="local-map__aim-ring"]').attributes("r"))).toBeCloseTo(9.5, 9);
      wrapper.unmount();
      // Stub start: (HALO_R + 1) × 0.5.
      wrapper = mount(Lattice, { props: { localMap: localMapModelFor(LOCAL_MAP_ALTORIA_SOUTH_GATE_SAMPLE) } });
      const line = wrapper.get(".local-map__stub .local-map__edge");
      expect(Math.hypot(Number(line.attributes("x1")) - 120, Number(line.attributes("y1")) - 120)).toBeCloseTo(8, 9);
      wrapper.unmount();
      // Label clearance: the crowded current label's classic spot sits the
      // current footprint (14 × 0.5) plus the gap below the marker.
      wrapper = mount(Island, { props: { localMap: localMapModelFor(LOCAL_MAP_CROWDED_LABELS_SAMPLE) }, attachTo: document.body });
      const current = wrapper.get(`[data-node="${LOCAL_MAP_CROWDED_LABELS_SAMPLE.current_node}"]`);
      expect(Number(current.get(".local-map__node-label tspan").attributes("y"))).toBeCloseTo(14 * 0.5 + 3 + 0.8 * 16, 6);
      // Footprints: the 20-unit pair that spreads at 0.75 clears 2 × 16 × 0.5.
      const theta = (2 * Math.asin(10 / 80) * 180) / Math.PI;
      const exits = [
        { bearing: 0, radius: 80, order: 0, node: { action: { kind: "move" } } },
        { bearing: theta, radius: 80, order: 1, node: { action: { kind: "move" } } },
      ];
      spread(exits);
      expect(exits[0].bearing).toBe(0);
      expect(exits[1].bearing).toBe(theta);
    } finally {
      vi.doUnmock("../../lib/map_glyphs.js");
      vi.resetModules();
    }
  });
});
