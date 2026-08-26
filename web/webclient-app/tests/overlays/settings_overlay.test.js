import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import SettingsOverlay from "../../components/SettingsOverlay.vue";

// SettingsOverlay (H5, webclient-hud-05-overlays-and-command-line): the
// body content of the shared full-screen overlay. The modal chrome (header,
// close control, focus trap) belongs to the OverlayHost, so the body itself
// carries no dialog role, close button, `open` prop or `close` emit. Every
// control is client-local presentation state — no settings control dispatches
// a `ui_action`; each change emits a plain preference-change event that the
// store persists through the versioned layout store (tasks 7.1–7.8).
describe("SettingsOverlay (H5 body, webclient-hud-05-overlays-and-command-line)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  it("renders the settings body without modal chrome (task 6.1)", () => {
    wrapper = mount(SettingsOverlay);
    const overlay = wrapper.get('[data-testid="settings-overlay"]');
    // The body is a plain block, not a dialog: no role, no aria-modal, no
    // close control (those live on the OverlayHost now).
    expect(overlay.attributes("role")).toBeUndefined();
    expect(overlay.attributes("aria-modal")).toBeUndefined();
    expect(wrapper.find('[data-testid="settings-overlay-close"]').exists()).toBe(false);
  });

  it("renders the A−/A/A+ scale segment, the 3-state reduced-motion control and the two toggles", () => {
    wrapper = mount(SettingsOverlay);
    for (const testid of [
      "settings-overlay-scale-A−",
      "settings-overlay-scale-A",
      "settings-overlay-scale-A+",
      "settings-overlay-reduced-motion-default",
      "settings-overlay-reduced-motion-on",
      "settings-overlay-reduced-motion-off",
      "settings-overlay-text-to-html",
      "settings-overlay-colorblind",
    ]) {
      expect(wrapper.find(`[data-testid="${testid}"]`).exists()).toBe(true, `${testid} present`);
    }
    // The invented font-family select is removed (task 7.3).
    expect(wrapper.find('[data-testid="settings-overlay-fonts"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="settings-overlay-type-scale"]').exists()).toBe(false);
  });

  it("marks the current scale step with a non-colour indicator (task 7.2)", () => {
    wrapper = mount(SettingsOverlay, { props: { fontScale: 0.92 } });
    const aMinus = wrapper.get('[data-testid="settings-overlay-scale-A−"]');
    expect(aMinus.classes()).toContain("on");
    expect(aMinus.attributes("aria-pressed")).toBe("true");
  });

  it("emits scale-change with the selected step value", async () => {
    wrapper = mount(SettingsOverlay);
    wrapper.get('[data-testid="settings-overlay-scale-A+"]').trigger("click");
    await wrapper.vm.$nextTick();
    expect(wrapper.emitted("scale-change")).toEqual([[1.12]]);
  });

  it("emits reduced-motion-change across the three states", async () => {
    wrapper = mount(SettingsOverlay);
    wrapper.get('[data-testid="settings-overlay-reduced-motion-on"]').trigger("click");
    await wrapper.vm.$nextTick();
    expect(wrapper.emitted("reduced-motion-change")).toEqual([["on"]]);
    wrapper.get('[data-testid="settings-overlay-reduced-motion-off"]').trigger("click");
    await wrapper.vm.$nextTick();
    expect(wrapper.emitted("reduced-motion-change")).toEqual([["on"], ["off"]]);
    wrapper.get('[data-testid="settings-overlay-reduced-motion-default"]').trigger("click");
    await wrapper.vm.$nextTick();
    expect(wrapper.emitted("reduced-motion-change")).toEqual([["on"], ["off"], [null]]);
  });

  it("marks the active reduced-motion state with a non-colour indicator", () => {
    wrapper = mount(SettingsOverlay, { props: { reducedMotion: "on" } });
    expect(wrapper.get('[data-testid="settings-overlay-reduced-motion-on"]').attributes("aria-pressed")).toBe("true");
    expect(wrapper.get('[data-testid="settings-overlay-reduced-motion-default"]').attributes("aria-pressed")).toBe("false");
  });

  it("emits text-html-change from the HTML narrative toggle", async () => {
    wrapper = mount(SettingsOverlay);
    const toggle = wrapper.get('[data-testid="settings-overlay-text-to-html"]');
    toggle.element.checked = true;
    toggle.trigger("change");
    await wrapper.vm.$nextTick();
    expect(wrapper.emitted("text-html-change")).toEqual([[true]]);
  });

  it("emits colorblind-change from the colorblind toggle", async () => {
    wrapper = mount(SettingsOverlay);
    const toggle = wrapper.get('[data-testid="settings-overlay-colorblind"]');
    toggle.element.checked = true;
    toggle.trigger("change");
    await wrapper.vm.$nextTick();
    expect(wrapper.emitted("colorblind-change")).toEqual([[true]]);
  });
});
