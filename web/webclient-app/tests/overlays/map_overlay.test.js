import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import { h } from "vue";
import MapOverlay from "../../components/MapOverlay.vue";
import MapLattice from "../../components/MapLattice.vue";
import {
  LOCAL_MAP_SAMPLE,
  LOCAL_MAP_INTERIOR_SAMPLE,
  LOCAL_MAP_UNAVAILABLE_SAMPLE,
  localMapModelFor,
} from "../../stories/fixtures.js";

// The server's four fixed visibility-state legend labels, in wire order
// (web/webclient/presentation/local_map.py LEGEND_LABELS).
const LEGEND_LABELS_FOR_TEST = [
  "你目前所在的位置",
  "尚未探索的相鄰位置",
  "已經探索過的相鄰位置",
  "曾經到過、但不在附近的遠方位置",
];

describe("MapOverlay (H5 body, webclient-hud-05-overlays-and-command-line)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  it("renders the shared lattice in the overlay body, without the island chrome", async () => {
    // Wave 0: the overlay's live prop is the store's derived model, so the
    // contract mounts bind through the shared helper.
    wrapper = mount(MapOverlay, { props: { localMap: localMapModelFor(LOCAL_MAP_SAMPLE) } });
    // The body is a plain block (task 6.1): no dialog role / aria-modal /
    // close control — those belong to the OverlayHost.
    const overlay = wrapper.get('[data-testid="map-overlay"]');
    expect(overlay.attributes("role")).toBeUndefined();
    expect(wrapper.find('[data-testid="map-overlay-close"]').exists()).toBe(false);
    // The available branch renders the shared lattice renderer at the
    // overlay's own larger scale — not the island's chrome (the `local-map`
    // root, the remembered list, the detail line, and the expand trigger
    // all stay in the island's `LocalMap.vue`).
    expect(wrapper.find('[data-testid="map-overlay-content"]').exists()).toBe(true);
    expect(wrapper.find(".local-map__lattice").exists()).toBe(true);
    expect(wrapper.find('[data-testid="local-map__node--grid:altoria:1:2"]').exists()).toBe(true);
    // webclient-full-map-fit-view D5: the legend renders only inside the
    // popover, which opens closed — nothing exists until the toggle fires.
    expect(wrapper.find('[data-testid="local-map__legend"]').exists()).toBe(false);
    await wrapper.get('[data-testid="map-overlay-legend-toggle"]').trigger("click");
    expect(wrapper.find('[data-testid="local-map__legend"]').exists()).toBe(true);
    await wrapper.get('[data-testid="map-overlay-legend-toggle"]').trigger("click");
    expect(wrapper.find('[data-testid="local-map__legend"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="local-map"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="local-map__expand"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="map-overlay-remembered"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="local-map-detail"]').exists()).toBe(false);

    // D5 contract: map-overlay-remembered is present on graph payload with remembered nodes
    const graphPayloadWithRem = {
      ...LOCAL_MAP_INTERIOR_SAMPLE,
      nodes: [
        ...LOCAL_MAP_INTERIOR_SAMPLE.nodes,
        { id: "room:rem1", label: "公會倉庫", x: 0, y: 5, visibility: "remembered", landmark: false },
      ],
    };
    const wGraph = mount(MapOverlay, { props: { localMap: localMapModelFor(graphPayloadWithRem) } });
    const remList = wGraph.find('[data-testid="map-overlay-remembered"]');
    expect(remList.exists()).toBe(true);
    const remEntries = remList.findAll("li");
    expect(remEntries).toHaveLength(1);
    expect(remEntries[0].text()).toContain("公會倉庫");
    expect(remEntries[0].attributes("tabindex")).toBeUndefined();
    expect(remEntries[0].attributes("role")).toBeUndefined();
  });

  it("forwards the move event when an actionable adjacent node is clicked", async () => {
    wrapper = mount(MapOverlay, { props: { localMap: localMapModelFor(LOCAL_MAP_SAMPLE) } });
    await wrapper
      .get('[data-testid="local-map__node--grid:altoria:2:2"]')
      .trigger("click");
    const emitted = wrapper.emitted("move");
    expect(emitted).toHaveLength(1);
    expect(emitted[0][0]).toEqual({
      exit_ref: "e_altoria_1_2_e",
      destination: "grid:altoria:2:2",
    });
  });

  it("exposes only traversable nodes as keyboard actions and moves with Enter or Space", async () => {
    wrapper = mount(MapOverlay, { props: { localMap: localMapModelFor(LOCAL_MAP_SAMPLE) } });
    const destination = wrapper.get('[data-testid="local-map__node--grid:altoria:2:2"]');
    expect(destination.attributes("role")).toBe("button");
    expect(destination.attributes("tabindex")).toBe("0");
    expect(wrapper.get('[data-testid="local-map__node--grid:altoria:1:2"]').attributes("tabindex")).toBeUndefined();
    await destination.trigger("keydown", { key: "Enter" });
    await destination.trigger("keydown", { key: " " });
    expect(wrapper.emitted("move")).toEqual([
      [{ exit_ref: "e_altoria_1_2_e", destination: "grid:altoria:2:2" }],
      [{ exit_ref: "e_altoria_1_2_e", destination: "grid:altoria:2:2" }],
    ]);
  });

  it("keeps the island's full-map trigger out of the overlay body (task 6.2)", () => {
    wrapper = mount(MapOverlay, { props: { localMap: localMapModelFor(LOCAL_MAP_SAMPLE) } });
    // The `open-map` emit contract is retained on the overlay, but the
    // trigger button now lives in the island chrome (`LocalMap.vue`), so
    // the overlay body itself no longer hosts the expand control.
    expect(wrapper.find('[data-testid="local-map__expand"]').exists()).toBe(false);
    expect(MapOverlay.emits).toContain("open-map");
  });

  it("renders the draft overlay chrome: mapcanvas framing and the location pin", async () => {
    wrapper = mount(MapOverlay, { props: { localMap: localMapModelFor(LOCAL_MAP_SAMPLE) } });
    // webclient-map-01-draft-chrome design D4: the full-map surface is the
    // only caller with the canvas treatment and the pin.
    expect(wrapper.get("svg.local-map__lattice").classes()).toContain("local-map__lattice--canvas");
    expect(wrapper.findAll('[data-testid="local-map__pin"]')).toHaveLength(1);
    // The dot-chip legend renders at the overlay's scale too — once its
    // popover is open (webclient-full-map-fit-view D5).
    await wrapper.get('[data-testid="map-overlay-legend-toggle"]').trigger("click");
    expect(wrapper.find(".local-map__legend-chip--current").exists()).toBe(true);
  });

  it("withholds the overlay chrome from the unavailable branch", () => {
    wrapper = mount(MapOverlay, { props: { localMap: localMapModelFor(LOCAL_MAP_UNAVAILABLE_SAMPLE) } });
    expect(wrapper.find(".local-map__lattice--canvas").exists()).toBe(false);
    expect(wrapper.findAll('[data-testid="local-map__pin"]')).toHaveLength(0);
  });

  it("renders only the registry-owned reason for the unavailable payload", () => {
    wrapper = mount(MapOverlay, { props: { localMap: localMapModelFor(LOCAL_MAP_UNAVAILABLE_SAMPLE) } });
    expect(
      wrapper.get('[data-testid="map-overlay-unavailable"]').text(),
    ).toBe("區域地圖目前無法顯示");
    // The unavailable form never invents a lattice: no LocalMap panel.
    expect(wrapper.find('[data-testid="local-map"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="map-overlay-content"]').exists()).toBe(false);
  });

  it("re-renders the available/unavailable branch when the local_map payload is replaced", async () => {
    wrapper = mount(MapOverlay, { props: { localMap: localMapModelFor(LOCAL_MAP_SAMPLE) } });
    expect(wrapper.find(".local-map__lattice").exists()).toBe(true);
    // An OOB read-model update replaces the payload: the body must track the
    // new state, never show a stale branch (the delta's read-model-update
    // requirement, first observable here outside Storybook).
    await wrapper.setProps({ localMap: localMapModelFor(LOCAL_MAP_UNAVAILABLE_SAMPLE) });
    expect(
      wrapper.get('[data-testid="map-overlay-unavailable"]').text(),
    ).toBe("區域地圖目前無法顯示");
    expect(wrapper.find(".local-map__lattice").exists()).toBe(false);
    await wrapper.setProps({ localMap: localMapModelFor(LOCAL_MAP_SAMPLE) });
    expect(wrapper.find(".local-map__lattice").exists()).toBe(true);
  });

  // ---------------------------------------------------------------------
  // webclient-full-map-fit-view D3/D5: the fitted-view toolbar and the
  // legend popover's disclosure contract.
  // ---------------------------------------------------------------------

  it("offers the four view controls with their accessible names", () => {
    wrapper = mount(MapOverlay, { props: { localMap: localMapModelFor(LOCAL_MAP_SAMPLE) } });
    expect(wrapper.get('[data-testid="map-overlay-zoom-out"]').attributes("aria-label")).toBe("縮小");
    expect(wrapper.get('[data-testid="map-overlay-zoom-out"]').text()).toBe("−");
    expect(wrapper.get('[data-testid="map-overlay-zoom-in"]').attributes("aria-label")).toBe("放大");
    expect(wrapper.get('[data-testid="map-overlay-zoom-in"]').text()).toBe("+");
    expect(wrapper.get('[data-testid="map-overlay-recentre"]').text()).toBe("置中");
    const toggle = wrapper.get('[data-testid="map-overlay-legend-toggle"]');
    expect(toggle.attributes("aria-label")).toBe("圖例");
    expect(toggle.text()).toBe("?");
    // A bound control carries aria-disabled, never `disabled` (D3): a
    // focused button must never drop focus out of the trap.
    for (const id of ["map-overlay-zoom-out", "map-overlay-zoom-in", "map-overlay-recentre", "map-overlay-legend-toggle"]) {
      expect(wrapper.get(`[data-testid="${id}"]`).attributes("disabled")).toBeUndefined();
    }
  });

  it("toggles the legend popover's aria-expanded and aria-controls wiring", async () => {
    wrapper = mount(MapOverlay, { props: { localMap: localMapModelFor(LOCAL_MAP_SAMPLE) } });
    const toggle = wrapper.get('[data-testid="map-overlay-legend-toggle"]');
    expect(toggle.attributes("aria-expanded")).toBe("false");
    expect(wrapper.find('[data-testid="map-overlay-legend-popover"]').exists()).toBe(false);
    await toggle.trigger("click");
    expect(toggle.attributes("aria-expanded")).toBe("true");
    expect(toggle.attributes("aria-controls")).toBe(
      wrapper.get('[data-testid="map-overlay-legend-popover"]').attributes("id"),
    );
    expect(wrapper.get('[data-testid="map-overlay-legend-popover"]').attributes("role")).toBe("group");
    expect(wrapper.get('[data-testid="map-overlay-legend-popover"]').attributes("aria-label")).toBe("圖例");
  });

  // Escape precedence (D5, the modified contextual-hud overlay requirement):
  // while the popover is open it is the topmost Escape level and the key
  // never reaches the OverlayHost section handler above.
  it("closes only the popover on Escape and stops the event while it is open", async () => {
    const seen = [];
    const Parent = {
      render() {
        return h(
          "div",
          { onKeydown: (e) => seen.push(e.key) },
          [h(MapOverlay, { localMap: localMapModelFor(LOCAL_MAP_SAMPLE) })],
        );
      },
    };
    const parent = mount(Parent, { attachTo: document.body });
    wrapper = parent;
    const overlay = parent.findComponent(MapOverlay);
    await overlay.get('[data-testid="map-overlay-legend-toggle"]').trigger("click");
    expect(overlay.find('[data-testid="map-overlay-legend-popover"]').exists()).toBe(true);
    await overlay.get('[data-testid="map-overlay"]').trigger("keydown", { key: "Escape" });
    expect(overlay.find('[data-testid="map-overlay-legend-popover"]').exists()).toBe(false);
    // The parent listener never saw the Escape (stopPropagation on the
    // overlay root, which runs before the parent's in bubble order).
    expect(seen).toEqual([]);
    parent.unmount();
    wrapper = null;
  });

  it("lets Escape propagate while the popover is closed", async () => {
    const seen = [];
    const Parent = {
      render() {
        return h(
          "div",
          { onKeydown: (e) => seen.push(e.key) },
          [h(MapOverlay, { localMap: localMapModelFor(LOCAL_MAP_SAMPLE) })],
        );
      },
    };
    const parent = mount(Parent, { attachTo: document.body });
    wrapper = parent;
    const overlay = parent.findComponent(MapOverlay);
    await overlay.get('[data-testid="map-overlay"]').trigger("keydown", { key: "Escape" });
    expect(seen).toContain("Escape");
    parent.unmount();
    wrapper = null;
  });

  it("closes the popover on a pointer press outside it, without consuming the press", async () => {
    wrapper = mount(MapOverlay, { props: { localMap: localMapModelFor(LOCAL_MAP_SAMPLE) } });
    await wrapper.get('[data-testid="map-overlay-legend-toggle"]').trigger("click");
    expect(wrapper.find('[data-testid="map-overlay-legend-popover"]').exists()).toBe(true);
    const node = wrapper.get('[data-testid="local-map__node--grid:altoria:2:2"]');
    await node.trigger("pointerdown", { button: 0, pointerId: 3, clientX: 50, clientY: 50 });
    expect(wrapper.find('[data-testid="map-overlay-legend-popover"]').exists()).toBe(false);
    // The press was not consumed: the node click path stays intact.
    await node.trigger("click");
    expect(wrapper.emitted("move")).toHaveLength(1);
  });

  it("zooms with the + and - keys through the exposed lattice controls", async () => {
    wrapper = mount(MapOverlay, { props: { localMap: localMapModelFor(LOCAL_MAP_SAMPLE) } });
    // Spy through the MapLattice instance's raw defineExpose object —
    // that is the exact object the overlay's latticeRef calls on.
    const lattice = wrapper.findComponent(MapLattice);
    const exposed = lattice.vm.$.exposed;
    const zoomIn = vi.spyOn(exposed, "zoomIn");
    const zoomOut = vi.spyOn(exposed, "zoomOut");
    const root = wrapper.get('[data-testid="map-overlay"]');
    await root.trigger("keydown", { key: "+" });
    await root.trigger("keydown", { key: "=" });
    await root.trigger("keydown", { key: "Add" });
    expect(zoomIn).toHaveBeenCalledTimes(3);
    await root.trigger("keydown", { key: "-" });
    await root.trigger("keydown", { key: "_" });
    await root.trigger("keydown", { key: "Subtract" });
    expect(zoomOut).toHaveBeenCalledTimes(3);
    // A held modifier means browser page zoom — the key passes through.
    await root.trigger("keydown", { key: "+", ctrlKey: true });
    expect(zoomIn).toHaveBeenCalledTimes(3);
  });

  it("passes the fitted view to the shared lattice and no cap props", () => {
    wrapper = mount(MapOverlay, { props: { localMap: localMapModelFor(LOCAL_MAP_SAMPLE) } });
    const lattice = wrapper.findComponent(MapLattice);
    expect(lattice.props("fitView")).toBe(true);
    // The deleted cap props can only reappear as fallthrough attrs on the
    // lattice root or as an inline width bound on the canvas — neither
    // exists (kebab form checked, the attr spelling a fallthrough takes).
    expect(lattice.attributes("max-width")).toBeUndefined();
    expect(lattice.find("svg.local-map__lattice").element.style.cssText).not.toContain("max-width");
  });

  // Moved from tests/world/map_lattice_legend_labels.test.js (webclient-
  // full-map-fit-view D5): the legend is the overlay popover's presentation
  // now, so its pairing cases mount MapOverlay and open the popover.
  it("pairs every legend entry with a dot chip at the overlay scale", async () => {
    wrapper = mount(MapOverlay, { props: { localMap: localMapModelFor(LOCAL_MAP_SAMPLE) } });
    await wrapper.get('[data-testid="map-overlay-legend-toggle"]').trigger("click");
    const items = wrapper.findAll('[data-testid^="local-map__legend-item--"]');
    expect(items).toHaveLength(4);
    for (const [i, state] of Object.entries(["current", "visible_unvisited", "visible_visited", "remembered"])) {
      expect(items[Number(i)].find(`.local-map__legend-chip--${state}`).exists()).toBe(true);
    }
    // Non-colour redundancy lives in the chip class pair: visited (solid
    // frame) and remembered (dashed frame) are distinct states.
    expect(items[2].find(".local-map__legend-chip--remembered").exists()).toBe(false);
    expect(items[3].find(".local-map__legend-chip--visible_visited").exists()).toBe(false);
  });

  // webclient-map-scale-legend D3: entries beyond the four states are
  // explanatory notes. They render with the neutral info-chip treatment —
  // never a cycled state chip — and their full text label is the primary
  // carrier. A deliberately distinctive note guards against truncation.
  it("renders a fifth beyond-state entry as a neutral info chip, text intact", async () => {
    const note = "每格約 10 公里（荒野坐標網格）";
    wrapper = mount(MapOverlay, {
      props: {
        localMap: {
          ...localMapModelFor(LOCAL_MAP_SAMPLE),
          legend: [...LEGEND_LABELS_FOR_TEST, note],
        },
      },
    });
    await wrapper.get('[data-testid="map-overlay-legend-toggle"]').trigger("click");
    const items = wrapper.findAll('[data-testid^="local-map__legend-item--"]');
    expect(items).toHaveLength(5);
    // The first four keep their state chip treatments in the fixed order.
    for (const [i, state] of Object.entries(["current", "visible_unvisited", "visible_visited", "remembered"])) {
      expect(items[Number(i)].find(`.local-map__legend-chip--${state}`).exists()).toBe(true);
    }
    const info = items[4];
    expect(info.find(".local-map__legend-chip--info").exists()).toBe(true);
    // The info entry carries no state class at all (never a fifth state).
    for (const state of ["current", "visible_unvisited", "visible_visited", "remembered"]) {
      expect(info.find(`.local-map__legend-chip--${state}`).exists()).toBe(false);
    }
    // The text label renders in full (no truncation of beyond-state notes).
    expect(info.text()).toBe(note);
  });

  it("styles every entry beyond the fourth as info, for any payload", async () => {
    const extra = ["附註甲", "附註乙", "附註丙"];
    wrapper = mount(MapOverlay, {
      props: {
        localMap: {
          ...localMapModelFor(LOCAL_MAP_SAMPLE),
          legend: [...LEGEND_LABELS_FOR_TEST, ...extra],
        },
      },
    });
    await wrapper.get('[data-testid="map-overlay-legend-toggle"]').trigger("click");
    const items = wrapper.findAll('[data-testid^="local-map__legend-item--"]');
    expect(items).toHaveLength(7);
    extra.forEach((label, offset) => {
      const item = items[4 + offset];
      expect(item.find(".local-map__legend-chip--info").exists()).toBe(true);
      expect(item.text()).toBe(label);
    });
  });
});
