import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import LocalMap from "../../components/LocalMap.vue";
import {
  LOCAL_MAP_MINIMAL_SAMPLE,
  LOCAL_MAP_SAMPLE,
  LOCAL_MAP_UNAVAILABLE_SAMPLE,
} from "../../stories/fixtures.js";

describe("LocalMap (B4 world family)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountMap(props = {}) {
    wrapper = mount(LocalMap, {
      props: {
        localMap: LOCAL_MAP_SAMPLE,
        ...props,
      },
    });
    return wrapper;
  }

  it("renders the payload's map title", () => {
    expect(mountMap().get('[data-testid="local-map__title"]').text()).toBe("霧骨渡口");
  });

  it("renders the honest unavailable box with the payload's reason message", () => {
    const w = mountMap({ localMap: LOCAL_MAP_UNAVAILABLE_SAMPLE });
    expect(w.get('[data-testid="local-map__unavailable"]').text()).toBe("區域地圖目前無法顯示");
    expect(w.find(".local-map__lattice").exists()).toBe(false);
    expect(w.find('[data-testid="local-map__title"]').exists()).toBe(false);
    expect(w.find('[data-testid^="local-map__node--"]').exists()).toBe(false);
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
    // current → square, visible_unvisited → open circle,
    // visible_visited → filled circle, remembered → diamond (rotated rect).
    expect(w.get('[data-testid="local-map__node--grid:altoria:1:2"]').find("rect").exists()).toBe(true);
    expect(w.get('[data-testid="local-map__node--grid:altoria:2:2"]').find("circle").exists()).toBe(true);
    expect(w.get('[data-testid="local-map__node--grid:altoria:0:2"]').find("circle").exists()).toBe(true);
    expect(
      w.get('[data-testid="local-map__node--grid:altoria:5:5"]').find('rect[transform="rotate(45)"]').exists(),
    ).toBe(true);
  });

  it("marks the only actionable adjacent node (南門) and shows it in the detail line", () => {
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

  it("renders the payload's legend entries paired with their state glyphs", () => {
    const w = mountMap();
    const items = w.findAll('[data-testid^="local-map__legend-item--"]');
    expect(items).toHaveLength(4);
    expect(w.get('[data-testid="local-map__legend"]').text()).toContain("你目前所在的位置");
    for (const [i, state] of Object.entries(["current", "visible_unvisited", "visible_visited", "remembered"])) {
      expect(items[Number(i)].find(`.local-map__legend-glyph--${state}`).exists()).toBe(true);
    }
    expect(w.text()).toContain("尚未探索的相鄰位置");
    expect(w.text()).toContain("已經探索過的相鄰位置");
    expect(w.text()).toContain("曾經到過、但不在附近的遠方位置");
  });

  it("defaults the detail line to the current node and follows hover", async () => {
    const w = mountMap();
    const detail = w.get('[data-testid="local-map__detail"]');
    expect(detail.text()).toContain("霧骨渡口");
    expect(detail.text()).toContain("current");
    expect(detail.text()).toContain("(1, 2)");

    await w.get('[data-testid="local-map__node--grid:altoria:2:2"]').trigger("mouseenter");
    const hovered = w.get('[data-testid="local-map__detail"]');
    expect(hovered.text()).toContain("南門");
    expect(hovered.text()).toContain("visible_unvisited");
    expect(hovered.text()).toContain("(2, 2)");
    expect(hovered.text()).toContain("grid:altoria:2:2");

    await w.find(".local-map__lattice").trigger("mouseleave");
    expect(w.get('[data-testid="local-map__detail"]').text()).toContain("霧骨渡口");

    await w.get('[data-testid="local-map__node--grid:altoria:2:2"]').trigger("click");
    // Selection persists after the interaction.
    expect(w.get('[data-testid="local-map__detail"]').text()).toContain("南門");
  });

  it("renders every edge of the payload with its own traversability styling", () => {
    const w = mountMap();
    const edges = w.findAll('[data-testid^="local-map__edge--"]');
    expect(edges).toHaveLength(3);
    expect(w.get('[data-testid="local-map__edge--0"]').classes()).toContain("local-map__edge--traversable");
    expect(w.get('[data-testid="local-map__edge--1"]').classes()).toContain("local-map__edge--blocked");
    expect(w.get('[data-testid="local-map__edge--2"]').classes()).toContain("local-map__edge--unknown");
  });

  it("renders the minimal sample: two nodes, one unknown edge, one legend line, no actionable node", () => {
    const w = mountMap({ localMap: LOCAL_MAP_MINIMAL_SAMPLE });
    const nodeIds = w.findAll('[data-testid^="local-map__node--"]');
    expect(nodeIds).toHaveLength(2);
    expect(w.findAll('[data-testid^="local-map__edge--"]')).toHaveLength(1);
    expect(w.get('[data-testid="local-map__edge--0"]').classes()).toContain("local-map__edge--unknown");
    expect(w.findAll('[data-testid="local-map__actionable"]')).toHaveLength(0);
    expect(w.findAll('[data-testid^="local-map__legend-item--"]')).toHaveLength(1);
    expect(w.get('[data-testid="local-map__detail"]').text()).toContain("霧骨渡口");
  });
});
