import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import LocalMap from "../../components/LocalMap.vue";
import MapLattice from "../../components/MapLattice.vue";
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

  it("keeps the shared-region label suppression on the projected wilderness island", () => {
    // render-auto-scaled-minimap-island: one-kilometre wilderness cells are
    // projected (one exit north at 1 km → level 1500, radius 66.667), the exit
    // sharing the current cell's region name draws no label text, and the
    // two-hop cells that would land off the square are omitted.
    const payload = {
      layer: "wilderness", available: true, current_node: "wild:t:0:0",
      edges: [{ source: "wild:t:0:0", destination: "wild:t:0:1", label: "n", known: true, traversable: true }],
      nodes: [
        { id: "wild:t:0:0", x: 0, y: 0, label: "共用地區", visibility: "current" },
        { id: "wild:t:0:1", x: 0, y: 1, label: "共用地區", visibility: "visible_visited" },
        { id: "wild:t:0:2", x: 0, y: 2, label: "北岸鐘樓", visibility: "visible_visited" },
        ...Array.from({ length: 5 }, (_, i) => ({
          id: `wild:t:0:${i + 3}`, x: 0, y: i + 3, label: "共用地區", visibility: "visible_visited",
        })),
      ],
    };
    wrapper = mount(MapLattice, { props: {
      localMap: localMapModelFor(payload), canvasSize: 240,
    } });
    expect(wrapper.get("svg").attributes("viewBox")).toBe("0 0 240 240");
    const exit = wrapper.get('[data-node="wild:t:0:1"]');
    expect(exit.attributes("transform")).toBe("translate(120, 53.333)");
    // label-minimap-exits-and-gateways: the information-free repeat draws
    // no label block at all, and the node keeps its full name as its title.
    expect(exit.find(".local-map__node-label").exists()).toBe(false);
    expect(exit.get("title").text()).toBe("共用地區");
    expect(exit.find(".local-map__marker").exists()).toBe(true);
    // 2 km north and beyond would land above the square: omitted context.
    expect(wrapper.find('[data-node="wild:t:0:2"]').exists()).toBe(false);
    expect(wrapper.findAll(".local-map__node")).toHaveLength(2);
  });
});

