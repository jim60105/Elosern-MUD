import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import LocalMap from "../../components/LocalMap.vue";
import { LOCAL_MAP_SAMPLE, localMapModelFor } from "../../stories/fixtures.js";

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

  it("clicking a lattice node forwards the move intent while leaving readout unchanged", async () => {
    const w = mountIsland();
    expect(w.get('[data-testid="local-map-detail"]').text()).toBe("座標 1,2");
    // Activating the unvisited node forwards the move intent.
    await w.get('[data-testid="local-map__node--grid:altoria:2:2"]').trigger("click");
    // Readout remains coordinate-only (webclient-minimap-04-island-single-affordance D3/D6).
    expect(w.get('[data-testid="local-map-detail"]').text()).toBe("座標 1,2");
    // The actionable node also emits move.
    const moved = w.emitted("move");
    expect(moved).toHaveLength(1);
    expect(moved[0][0]).toEqual({
      exit_ref: "e_altoria_1_2_e",
      destination: "grid:altoria:2:2",
    });
  });

  it("clicking a non-actionable node leaves detail line unchanged without a move emit", async () => {
    const w = mountIsland();
    await w.get('[data-testid="local-map__node--grid:altoria:0:2"]').trigger("click");
    expect(w.get('[data-testid="local-map-detail"]').text()).toBe("座標 1,2");
    expect(w.emitted("move")).toBeUndefined();
  });

  it("clicking an edge marker leaves detail line unchanged", async () => {
    const w = mountIsland();
    const edgeMarker = w.get('[data-testid^="local-map__edge-marker--"]');
    await edgeMarker.trigger("click");
    expect(w.get('[data-testid="local-map-detail"]').text()).toBe("座標 1,2");
    expect(w.emitted("move")).toBeUndefined();
  });
});

