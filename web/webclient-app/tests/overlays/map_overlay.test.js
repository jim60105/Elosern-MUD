import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import MapOverlay from "../../components/MapOverlay.vue";
import {
  LOCAL_MAP_MINIMAL_SAMPLE,
  LOCAL_MAP_SAMPLE,
  LOCAL_MAP_UNAVAILABLE_SAMPLE,
} from "../../stories/fixtures.js";

describe("MapOverlay (H5 body, webclient-hud-05-overlays-and-command-line)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  it("renders the full lattice in the overlay body, reusing the LocalMap panel", () => {
    wrapper = mount(MapOverlay, { props: { localMap: LOCAL_MAP_SAMPLE } });
    // The body is a plain block (task 6.1): no dialog role / aria-modal /
    // close control — those belong to the OverlayHost.
    const overlay = wrapper.get('[data-testid="map-overlay"]');
    expect(overlay.attributes("role")).toBeUndefined();
    expect(wrapper.find('[data-testid="map-overlay-close"]').exists()).toBe(false);
    // The available branch renders the LocalMap lattice.
    expect(wrapper.find('[data-testid="map-overlay-content"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="local-map"]').exists()).toBe(true);
    expect(wrapper.find(".local-map__lattice").exists()).toBe(true);
    expect(wrapper.find('[data-testid="local-map__node--grid:altoria:1:2"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="local-map__legend"]').exists()).toBe(true);
  });

  it("forwards the move event when an actionable adjacent node is clicked", async () => {
    wrapper = mount(MapOverlay, { props: { localMap: LOCAL_MAP_SAMPLE } });
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

  it("forwards the open-map event from the island's full-map trigger (task 6.2)", async () => {
    wrapper = mount(MapOverlay, { props: { localMap: LOCAL_MAP_SAMPLE } });
    await wrapper.get('[data-testid="local-map__expand"]').trigger("click");
    expect(wrapper.emitted("open-map")).toBeTruthy();
  });

  it("renders only the registry-owned reason for the unavailable payload", () => {
    wrapper = mount(MapOverlay, { props: { localMap: LOCAL_MAP_UNAVAILABLE_SAMPLE } });
    expect(
      wrapper.get('[data-testid="map-overlay-unavailable"]').text(),
    ).toBe("區域地圖目前無法顯示");
    // The unavailable form never invents a lattice: no LocalMap panel.
    expect(wrapper.find('[data-testid="local-map"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="map-overlay-content"]').exists()).toBe(false);
  });

  it("re-renders the available/unavailable branch when the local_map payload is replaced", async () => {
    wrapper = mount(MapOverlay, { props: { localMap: LOCAL_MAP_SAMPLE } });
    expect(wrapper.find('[data-testid="local-map"]').exists()).toBe(true);
    // An OOB read-model update replaces the payload: the body must track the
    // new state, never show a stale branch (the delta's read-model-update
    // requirement, first observable here outside Storybook).
    await wrapper.setProps({ localMap: LOCAL_MAP_UNAVAILABLE_SAMPLE });
    expect(
      wrapper.get('[data-testid="map-overlay-unavailable"]').text(),
    ).toBe("區域地圖目前無法顯示");
    expect(wrapper.find('[data-testid="local-map"]').exists()).toBe(false);
    await wrapper.setProps({ localMap: LOCAL_MAP_SAMPLE });
    expect(wrapper.find('[data-testid="local-map"]').exists()).toBe(true);
  });
});
