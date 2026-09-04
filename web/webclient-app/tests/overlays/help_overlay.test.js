import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import HelpOverlay from "../../components/HelpOverlay.vue";

describe("HelpOverlay (H5 body, webclient-hud-05-overlays-and-command-line)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  it("renders the client's own control reference", () => {
    // The body is a plain block (task 6.1): no dialog role / aria-modal /
    // close control — those belong to the OverlayHost.
    wrapper = mount(HelpOverlay);
    const overlay = wrapper.get('[data-testid="help-overlay"]');
    expect(overlay.attributes("role")).toBeUndefined();
    expect(overlay.attributes("aria-modal")).toBeUndefined();
    const controls = wrapper.get('[data-testid="help-controls"]');
    expect(controls.exists()).toBe(true);
    const rows = controls.findAll('[data-testid^="help-controls-row-"]');
    expect(rows.length).toBeGreaterThan(0);
    const gameHelp = wrapper.get('[data-testid="help-controls-gamehelp"]').text();
    expect(gameHelp).toMatch(/help/i);
  });

  it("renders no authored game-help sections", () => {
    // The guide payload is gone with the onboarding subsystem: the overlay
    // carries only the client-owned control reference.
    wrapper = mount(HelpOverlay);
    expect(wrapper.emitted().update).toBeUndefined();
    expect(wrapper.html()).not.toContain("guide");
  });
});
