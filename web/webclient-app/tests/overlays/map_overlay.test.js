import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import MapOverlay from "../../components/MapOverlay.vue";
import {
  LOCAL_MAP_MINIMAL_SAMPLE,
  LOCAL_MAP_SAMPLE,
  LOCAL_MAP_UNAVAILABLE_SAMPLE,
  localMapModelFor,
} from "../../stories/fixtures.js";

describe("MapOverlay (H5 body, webclient-hud-05-overlays-and-command-line)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  it("renders the shared lattice in the overlay body, without the island chrome", () => {
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
    expect(wrapper.find('[data-testid="local-map__legend"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="local-map"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="local-map__expand"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="local-map-remembered"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="local-map-detail"]').exists()).toBe(false);
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

  it("keeps the island's full-map trigger out of the overlay body (task 6.2)", () => {
    wrapper = mount(MapOverlay, { props: { localMap: localMapModelFor(LOCAL_MAP_SAMPLE) } });
    // The `open-map` emit contract is retained on the overlay, but the
    // trigger button now lives in the island chrome (`LocalMap.vue`), so
    // the overlay body itself no longer hosts the expand control.
    expect(wrapper.find('[data-testid="local-map__expand"]').exists()).toBe(false);
    expect(MapOverlay.emits).toContain("open-map");
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
});
