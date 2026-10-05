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

  it("clears an upper label above an unlabeled wilderness node without shrinking text", () => {
    const payload = {
      layer: "wilderness", available: true, current_node: "c", edges: [],
      nodes: [
        { id: "c", x: 0, y: 0, label: "共用地區", visibility: "current" },
        { id: "below", x: 0, y: 1, label: "共用地區", visibility: "visible_visited" },
        { id: "above", x: 0, y: 2, label: "北岸鐘樓", visibility: "visible_visited" },
        ...Array.from({ length: 5 }, (_, i) => ({
          id: `north${i}`, x: 0, y: i + 3, label: "共用地區", visibility: "visible_visited",
        })),
      ],
    };
    wrapper = mount(MapLattice, { props: {
      localMap: localMapModelFor(payload), canvasSize: 240, colPitch: 40, rowPitch: 40,
    } });
    const pitch = Number(wrapper.get("defs pattern").attributes("height"));
    expect(pitch).toBeGreaterThanOrEqual(47);
    expect(wrapper.get("defs pattern").attributes("width")).toBe(String(pitch));
    const below = wrapper.get('[data-node="below"] text');
    expect([...below.element.childNodes].filter((node) => node.nodeType === 3)
      .map((node) => node.textContent).join("").trim()).toBe("");
    const viewBox = wrapper.get("svg").attributes("viewBox").split(" ").map(Number);
    expect(viewBox[2]).toBe(240);
    expect(viewBox[3]).toBe(240);
    expect(wrapper.findAll(".local-map__node")).toHaveLength(8);
  });
});

