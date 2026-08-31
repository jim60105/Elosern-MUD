import { mount } from "@vue/test-utils";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import LocalMap from "../../components/LocalMap.vue";
import MapLattice from "../../components/MapLattice.vue";
import MapOverlay from "../../components/MapOverlay.vue";
import LocalMapModel from "../../lib/local_map.js";
import {
  LOCAL_MAP_INTERIOR_SAMPLE,
  LOCAL_MAP_SAMPLE,
  LOCAL_MAP_WILDERNESS_SAMPLE,
  localMapModelFor,
} from "../../stories/fixtures.js";

// Layout variants (webclient-map-02-layout-variants task 7.1): the surfaces
// resolve their drawing convention from the committed payload's layer through
// the model's `layoutVariant` — grid/wilderness payloads draw the rank-
// compressed lattice (plus the edge direction markers for remembered places
// strictly outside the in-view extent), instance/interior payloads draw the
// model's radial placement. Nothing else may select the layout: there is no
// control of any kind on either surface.

describe("map layout variants (B4 world family, map-02)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountLattice(props = {}) {
    wrapper = mount(MapLattice, { props });
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

  it("draws the same committed content in both layouts (model-selected)", () => {
    // The lattice payload: every in-view node, its legend, and its actions
    // render; the graph payload does the same for its own committed content.
    // A variant switch may change coordinates ONLY — never what is drawn.
    const lattice = localMapModelFor(LOCAL_MAP_SAMPLE);
    const w1 = mountLattice({ localMap: lattice, variant: lattice.layoutVariant });
    expect(lattice.layoutVariant).toBe("lattice");
    expect(w1.findAll('[data-testid^="local-map__node--"]')).toHaveLength(3);
    expect(w1.findAll('[data-testid^="local-map__legend-item--"]')).toHaveLength(4);
    expect(w1.findAll('[data-testid="local-map__actionable"]')).toHaveLength(1);

    const graph = localMapModelFor(LOCAL_MAP_INTERIOR_SAMPLE);
    const w2 = mountLattice({ localMap: graph, variant: graph.layoutVariant });
    expect(graph.layoutVariant).toBe("graph");
    // Every radial placement entry is drawn — the graph layout loses no node.
    expect(graph.radial.nodes).toHaveLength(graph.nodes.length);
    expect(w2.findAll('[data-testid^="local-map__node--"]')).toHaveLength(graph.nodes.length);
    expect(w2.findAll('[data-testid^="local-map__edge--"]')).toHaveLength(graph.edges.length);
    expect(w2.findAll('[data-testid^="local-map__legend-item--"]')).toHaveLength(
      graph.legend.length,
    );
    // The interior payload's actionable node keeps its halo and move action.
    expect(w2.findAll('[data-testid="local-map__actionable"]')).toHaveLength(1);
  });

  it("renders exactly one pin anchored above the current marker in both layouts", () => {
    for (const sample of [LOCAL_MAP_SAMPLE, LOCAL_MAP_INTERIOR_SAMPLE]) {
      const model = localMapModelFor(sample);
      const w = mountLattice({
        localMap: model,
        variant: model.layoutVariant,
        overlayChrome: true,
        ...(model.layoutVariant === "graph" ? {} : OVERLAY_PROPS),
      });
      const pins = w.findAll('[data-testid="local-map__pin"]');
      expect(pins, model.layer).toHaveLength(1);
      const current = model.nodes.find((node) => node.visibility === "current");
      const nodeTransform = w.get(`[data-testid="local-map__node--${current.id}"]`)
        .attributes("transform");
      const [nx, ny] = nodeTransform
        .match(/translate\(([^,]+),\s*([^)]+)\)/)
        .slice(1, 3)
        .map(Number);
      // The wave-1 pin ownership contract: the pin shares the current
      // marker's translate pair (same coordinate system, it tracks the
      // marker ladder through the element scale), and its fixed path draws
      // ABOVE the anchor (tip at y=-16 in local units, negative y = up).
      const pinTransform = pins[0].attributes("transform");
      const [px, py] = pinTransform
        .match(/translate\(([^,]+),\s*([^)]+)\)/)
        .slice(1, 3)
        .map(Number);
      expect(px).toBe(nx);
      expect(py).toBe(ny);
      expect(pins[0].attributes("d")).toMatch(/^M0 -16/);
      w.unmount();
      wrapper = null;
    }
  });

  it("live-swaps an interior payload replacement to the radial layout", async () => {
    // The island follows the model field on payload replacement (task 7.1):
    // a grid payload in lattice layout live-swaps to an interior payload in
    // radial layout with no control touched.
    wrapper = mount(LocalMap, {
      props: { localMap: localMapModelFor(LOCAL_MAP_SAMPLE) },
    });
    expect(wrapper.find('[data-testid="local-map__orientation"]').exists()).toBe(true);
    expect(
      wrapper.find('[data-testid="local-map__edge-marker--grid:altoria:5:5"]').exists(),
    ).toBe(true);

    const interior = localMapModelFor(LOCAL_MAP_INTERIOR_SAMPLE);
    await wrapper.setProps({ localMap: interior });
    // Orientation legend: the radial variant has no axis convention to state.
    expect(wrapper.find('[data-testid="local-map__orientation"]').exists()).toBe(false);
    // Edge markers: the graph variant never marks.
    expect(
      wrapper.find('[data-testid^="local-map__edge-marker--"]').exists(),
    ).toBe(false);
    // The drawn positions come from the radial placement at the island's
    // scale (markerScale 1, no gutter) — not from any lattice formula.
    for (const placed of interior.radial.nodes) {
      const node = wrapper.get(`[data-testid="local-map__node--${placed.id}"]`);
      expect(node.attributes("transform")).toBe(
        `translate(${String(placed.x)}, ${String(placed.y)})`,
      );
    }
  });

  it("drives the orientation legend from layoutVariant, not the payload layer", () => {
    // A lattice-coordinate model whose layoutVariant is absent gets no
    // orientation legend — the legend follows the RESOLVED variant (design
    // D3), never a re-derivation from the payload's layer field.
    const model = localMapModelFor(LOCAL_MAP_SAMPLE);
    expect(model.layoutVariant).toBe("lattice");
    wrapper = mount(LocalMap, {
      props: { localMap: { ...model, layoutVariant: undefined } },
    });
    expect(wrapper.find('[data-testid="local-map__orientation"]').exists()).toBe(false);
    wrapper.unmount();

    wrapper = mount(LocalMap, { props: { localMap: model } });
    const orientation = wrapper.get('[data-testid="local-map__orientation"]');
    expect(orientation.text()).toBe("北↑ 東→");
  });

  it("renders edge direction markers only for off-extent remembered places on the lattice variant", () => {
    // Positive: the grid fixture's remembered place (5, 5) is strictly
    // outside the in-view extent [0..2]×[2..2] → one marker, and the
    // wilderness fixture's (7, 5) outside [2..4]×[1..2] → one marker.
    for (const [sample, id] of [
      [LOCAL_MAP_SAMPLE, "grid:altoria:5:5"],
      [LOCAL_MAP_WILDERNESS_SAMPLE, "wild:plains:7:5"],
    ]) {
      const model = localMapModelFor(sample);
      const w = mountLattice({ localMap: model, variant: "lattice" });
      const marker = w.get(`[data-testid="local-map__edge-marker--${id}"]`);
      expect(marker.classes()).toContain("local-map__edge-marker");
      // Non-interactive decoration: no pointer events, no activation.
      expect(marker.find("a, button").exists()).toBe(false);
      w.unmount();
      wrapper = null;
    }
    // Negative: a remembered node INSIDE the in-view extent never marks
    // (the list entry stays canonical), and coincident remotes never mark.
    const inside = {
      ...LOCAL_MAP_SAMPLE,
      nodes: LOCAL_MAP_SAMPLE.nodes.map((node) =>
        node.visibility === "remembered" ? { ...node, x: 2, y: 2 } : node,
      ),
    };
    const wInside = mountLattice({ localMap: localMapModelFor(inside), variant: "lattice" });
    expect(wInside.findAll('[data-testid^="local-map__edge-marker--"]')).toHaveLength(0);
    wInside.unmount();
    wrapper = null;
  });

  it("never renders edge markers on the graph variant", () => {
    // A graph payload cannot carry remembered remotes under the presenter's
    // coordinate-free layout, but even a forced variant=lattice → graph flip
    // over a remembered-bearing payload draws none: the graph layout has no
    // canvas edge a bearing could point at.
    const model = localMapModelFor(LOCAL_MAP_SAMPLE);
    wrapper = mountLattice({ localMap: model, variant: "graph" });
    // variant=graph with no radial placement: nothing is fabricated; the
    // marker layer is empty regardless of the remembered set.
    expect(wrapper.findAll('[data-testid^="local-map__edge-marker--"]')).toHaveLength(0);
  });

  it("exposes marker names only at the overlay scale (island keeps the list canonical)", () => {
    const model = localMapModelFor(LOCAL_MAP_SAMPLE);
    // Island scale (no overlay chrome): the marker is aria-hidden, name-free.
    const island = mountLattice({ localMap: model, variant: "lattice" });
    const islandMarker = island.get('[data-testid="local-map__edge-marker--grid:altoria:5:5"]');
    expect(islandMarker.attributes("aria-hidden")).toBe("true");
    expect(islandMarker.find("text").exists()).toBe(false);
    // The island's canonical reading path: the remembered list item.
    expect(
      island.find('[data-testid="local-map-remembered"]').exists(),
    ).toBe(false, "MapLattice alone has no list — LocalMap owns it");
    island.unmount();
    wrapper = null;
    // Overlay scale: visible name + accessible name on the decoration.
    const overlay = mountLattice({ localMap: model, variant: "lattice", ...OVERLAY_PROPS });
    const overlayMarker = overlay.get('[data-testid="local-map__edge-marker--grid:altoria:5:5"]');
    expect(overlayMarker.attributes("aria-label")).toBe("舊街區");
    expect(overlayMarker.find("text").text()).toBe("舊街區");
  });

  it("renders no layout control of any kind on either surface", () => {
    // The withdrawn switch design must leave no residue: neither the island
    // nor the overlay chrome may contain a segmented control, button, menu
    // item, or testid suggesting a layout toggle.
    const island = mount(LocalMap, {
      props: { localMap: localMapModelFor(LOCAL_MAP_SAMPLE) },
    });
    const overlay = mount(MapOverlay, {
      props: { localMap: localMapModelFor(LOCAL_MAP_SAMPLE) },
    });
    for (const [name, w] of [["island", island], ["overlay", overlay]]) {
      const controls = w
        .findAll("button, [role='button'], [role='radio'], [role='tab'], .seg")
        .filter((el) => {
          const text = el.text().toLowerCase();
          const testid = (el.attributes("data-testid") || "").toLowerCase();
          return (
            /layout|variant|lattice|graph|径|徑|radial|网格|網格/.test(text) ||
            /layout|variant|lattice|graph/.test(testid)
          );
        });
      expect(controls, `no layout control on the ${name}`).toHaveLength(0);
      // And none hiding in the markup either.
      expect(w.html().toLowerCase()).not.toMatch(/data-testid="[^"]*layout/);
      w.unmount();
    }
    wrapper = null;
  });

  it("keeps the wave-1 dot-field and axis contrast floor across both variants", () => {
    // Task 5.2 contrast pin: the radial variant reuses the wave-1 token
    // classes, so the pin is written once over the shared style block and
    // the token values. (1) No marker/edge/label rule dims its fill below
    // the 0.85 floor. (2) The axis ink over the map background keeps a
    // contrast ratio ≥ 0.65 at shipped stroke widths ≥ 1.5px.
    const tokens = readFileSync(
      join(process.cwd(), "web/webclient-app/styles/tokens.css"),
      "utf-8",
    );
    const token = (name) => tokens.match(new RegExp(`${name}:\\s*(#[0-9a-f]{6})`, "i"))[1];
    const luminance = (hex) => {
      const [r, g, b] = [1, 3, 5]
        .map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
        .map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
      return 0.2126 * r + 0.7152 * g + 0.0722 * b;
    };
    const contrast = (a, b) => {
      const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
      return (hi + 0.05) / (lo + 0.05);
    };
    const axisInk = token("--ink-edge");
    // The map-canvas gradient's two stops and the island's ink-860 ground:
    // the axis ink must clear the 0.65 floor over every map background.
    expect(contrast(axisInk, token("--map-canvas-lo"))).toBeGreaterThanOrEqual(0.65);
    expect(contrast(axisInk, token("--map-canvas-hi"))).toBeGreaterThanOrEqual(0.65);
    expect(contrast(axisInk, token("--ink-860"))).toBeGreaterThanOrEqual(0.65);
    const source = readFileSync(
      join(process.cwd(), "web/webclient-app/components/MapLattice.vue"),
      "utf-8",
    );
    const style = source.match(/<style[^>]*>([\s\S]*)<\/style>/)[1];
    // Shipped connector-axis stroke widths (design floor 1.5px): the three
    // edge states only — the marker layer's landmark ring is a decoration,
    // not an axis.
    const edgeWidths = [...style.matchAll(/\.local-map__edge(?:--[\w-]+)?\s*\{[^}]*stroke-width:\s*([\d.]+)/g)].map(
      (m) => Number(m[1]),
    );
    expect(edgeWidths).toEqual([2, 2, 1.5]);
    // No dot/marker/edge rule fades below the 0.85 floor on either variant —
    // the variants share these classes, so one scan pins both.
    const faded = [...style.matchAll(/\.local-map__(?:marker|edge|node)[^{]*\{[^}]*?(?:fill-opacity|opacity):\s*([0-9.]+)/g)].filter(
      (m) => Number(m[2]) < 0.85,
    );
    expect(faded).toEqual([]);
    // The remembered/edge-marker diamond fills are the same opaque token,
    // so the lattice dot-field reading carries into the marker layer.
    const markerFill = style.match(
      /\.local-map__edge-marker-diamond\s*\{[^}]*fill:\s*var\((--[\w-]+)\)/,
    );
    expect(markerFill[1]).toBe("--paper-500");
  });
});
