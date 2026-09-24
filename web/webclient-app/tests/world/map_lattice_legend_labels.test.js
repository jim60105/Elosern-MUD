import { afterEach, describe, expect, it } from "vitest";
import {
  LOCAL_MAP_SAMPLE,
  LOCAL_MAP_WILDERNESS_SAMPLE,
  localMapModelFor,
} from "../../stories/fixtures.js";
import {
  OVERLAY_PROPS,
  mountLattice as mountLatticeShared,
} from "./map_lattice_support.js";

// Split sibling of the original map_lattice.test.js (describe "MapLattice
// (B4 world family, shared renderer)"): landmark ring, draft-tier labels,
// (webclient-full-map-fit-view D5: the legend chip-pairing cases moved to
// tests/overlays/map_overlay.test.js, where the legend now renders inside
// the overlay's popover.) Shared fixtures live in ./map_lattice_support.js.

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

  it("draws the gold landmark ring over (not instead of) the visibility marker", () => {
    // The wilderness fixture's non-current landmark: 舊營地 (visited) at
    // island scale — ring r=5 coexists with the visited dot r=4.5.
    const w = mountLattice({ localMap: localMapModelFor(LOCAL_MAP_WILDERNESS_SAMPLE) });
    const node = w.get('[data-testid="local-map__node--wild:plains:2:2"]');
    const rings = node.findAll(".local-map__landmark");
    expect(rings).toHaveLength(1);
    expect(rings[0].attributes("r")).toBe("5");
    expect(node.find(".local-map__marker--visible_visited").exists()).toBe(true);
    // The ring is deliberately outside the `local-map__marker` class (the
    // browser geometry audit pairs marker boxes; decorations must not
    // self-overlap).
    expect(rings[0].classes()).not.toContain("local-map__marker");
    // The current landmark keeps exactly one ring; the remembered landmark
    // (遠處山徑) stays in the mirror/edge marker presentation with no ring on the canvas.
    expect(w.findAll('[data-testid="local-map__node--wild:plains:3:1"] .local-map__landmark')).toHaveLength(1);
    expect(w.findAll('[data-testid="local-map__node--wild:plains:7:5"]').length).toBe(0);
    expect(w.findAll(".local-map__landmark")).toHaveLength(2);
  });

  it("scales the landmark ring with the marker ladder at the overlay scale", () => {
    const w = mountLattice({
      ...OVERLAY_PROPS,
      localMap: localMapModelFor(LOCAL_MAP_WILDERNESS_SAMPLE),
    });
    expect(
      w.get('[data-testid="local-map__node--wild:plains:2:2"] .local-map__landmark').attributes("r"),
    ).toBe(String(5 * 4.83));
  });

  it("labels nodes by draft tier: here, gold, seen, far", () => {
    const w = mountLattice({ localMap: localMapModelFor(LOCAL_MAP_WILDERNESS_SAMPLE) });
    expect(
      w.get('[data-testid="local-map__node--wild:plains:3:1"] .local-map__node-label').classes(),
    ).toContain("local-map__node-label--here");
    // 舊營地: a visited landmark reads gold, not seen.
    expect(
      w.get('[data-testid="local-map__node--wild:plains:2:2"] .local-map__node-label').classes(),
    ).toContain("local-map__node-label--gold");
    expect(
      w.get('[data-testid="local-map__node--wild:plains:4:1"] .local-map__node-label').classes(),
    ).toContain("local-map__node-label--far");
  });

  // ---------------------------------------------------------------------
  // local-map-remembered-are-map-gateways wave 6 (FLAGGED/STRIKEABLE, design
  // D8b): the wilderness in-view neighbourhood must not repeat one region
  // name across every drawn cell.
  // ---------------------------------------------------------------------

  it("suppresses a duplicate in-view label on the wilderness layer, keeping the accessible name", () => {
    const model = localMapModelFor(LOCAL_MAP_WILDERNESS_SAMPLE);
    const current = model.nodes.find((n) => n.visibility === "current");
    const inViewVisibilities = new Set(["visible_unvisited", "visible_visited"]);
    const duped = {
      ...model,
      nodes: model.nodes.map((n) =>
        inViewVisibilities.has(n.visibility) ? { ...n, label: current.label } : n,
      ),
    };
    const inViewIds = duped.nodes.filter((n) => inViewVisibilities.has(n.visibility)).map((n) => n.id);
    expect(inViewIds.length).toBeGreaterThan(0);
    const w = mountLattice({ localMap: duped });
    for (const id of inViewIds) {
      const label = w.get(`[data-testid="local-map__node--${id}"] .local-map__node-label`);
      // The <title> element's text is part of the label's own textContent in
      // jsdom, so isolate the visible run by reading its own direct text.
      expect(label.element.childNodes[label.element.childNodes.length - 1].textContent).toBe("");
      expect(label.get("title").text()).toBe(current.label);
    }
    // The current node always draws its own label.
    const currentLabel = w.get(`[data-testid="local-map__node--${current.id}"] .local-map__node-label`);
    expect(
      currentLabel.element.childNodes[currentLabel.element.childNodes.length - 1].textContent,
    ).toBe(current.label);
  });

  it("does not suppress a duplicate in-view label outside the wilderness layer", () => {
    const model = localMapModelFor(LOCAL_MAP_SAMPLE);
    const current = model.nodes.find((n) => n.visibility === "current");
    const inViewVisibilities = new Set(["visible_unvisited", "visible_visited"]);
    const duped = {
      ...model,
      nodes: model.nodes.map((n) =>
        inViewVisibilities.has(n.visibility) ? { ...n, label: current.label } : n,
      ),
    };
    const inViewIds = duped.nodes.filter((n) => inViewVisibilities.has(n.visibility)).map((n) => n.id);
    expect(inViewIds.length).toBeGreaterThan(0);
    const w = mountLattice({ localMap: duped });
    for (const id of inViewIds) {
      const label = w.get(`[data-testid="local-map__node--${id}"] .local-map__node-label`);
      expect(label.element.childNodes[label.element.childNodes.length - 1].textContent).toBe(
        current.label,
      );
    }
  });
});
