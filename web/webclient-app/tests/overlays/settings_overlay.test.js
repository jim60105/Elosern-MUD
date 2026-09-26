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

  it("renders the A−/A/A+ scale segment, the three motion-level buttons and the two toggles", () => {
    wrapper = mount(SettingsOverlay);
    for (const testid of [
      "settings-overlay-scale-A−",
      "settings-overlay-scale-A",
      "settings-overlay-scale-A+",
      "settings-overlay-motion-full",
      "settings-overlay-motion-reduced",
      "settings-overlay-motion-off",
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

  it("emits motion-level-change across the three levels", async () => {
    wrapper = mount(SettingsOverlay);
    wrapper.get('[data-testid="settings-overlay-motion-reduced"]').trigger("click");
    await wrapper.vm.$nextTick();
    expect(wrapper.emitted("motion-level-change")).toEqual([["reduced"]]);
    wrapper.get('[data-testid="settings-overlay-motion-off"]').trigger("click");
    await wrapper.vm.$nextTick();
    expect(wrapper.emitted("motion-level-change")).toEqual([["reduced"], ["off"]]);
    wrapper.get('[data-testid="settings-overlay-motion-full"]').trigger("click");
    await wrapper.vm.$nextTick();
    expect(wrapper.emitted("motion-level-change")).toEqual([["reduced"], ["off"], ["full"]]);
  });

  it("marks the effective motion level with a non-colour indicator", () => {
    wrapper = mount(SettingsOverlay, { props: { motionLevel: "reduced" } });
    const pressed = wrapper.get('[data-testid="settings-overlay-motion-reduced"]');
    expect(pressed.attributes("aria-pressed")).toBe("true");
    expect(pressed.classes()).toContain("on");
    for (const other of ["full", "off"]) {
      const button = wrapper.get(`[data-testid="settings-overlay-motion-${other}"]`);
      expect(button.attributes("aria-pressed")).toBe("false");
      expect(button.classes()).not.toContain("on");
    }
  });

  it("names the motion level in the text-speed description", () => {
    wrapper = mount(SettingsOverlay);
    expect(wrapper.text()).toContain("動態效果為「減少」或「關閉」時一律立即顯示");
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

  // webclient-typewriter-reading-prefs (task 5.4): the reading section's
  // text-speed segment and auto-advance toggle.
  it("renders the four text-speed steps and the auto-advance toggle in the reading section", () => {
    wrapper = mount(SettingsOverlay);
    const reading = wrapper.get('section[aria-label="閱讀設定"]');
    const labels = ["slow", "normal", "fast", "instant"].map((value) =>
      reading.get(`[data-testid="settings-overlay-text-speed-${value}"]`).text(),
    );
    expect(labels).toEqual(["慢", "標準", "快", "瞬間"]);
    expect(reading.find('[data-testid="settings-overlay-auto-advance"]').exists()).toBe(true);
    expect(reading.text()).toContain("動態效果為「減少」或「關閉」時一律立即顯示");
  });

  it("marks the current text speed with a non-colour indicator and the pressed state", () => {
    wrapper = mount(SettingsOverlay, { props: { textSpeed: "fast", autoAdvance: true } });
    const fast = wrapper.get('[data-testid="settings-overlay-text-speed-fast"]');
    expect(fast.classes()).toContain("on");
    expect(fast.attributes("aria-pressed")).toBe("true");
    const normal = wrapper.get('[data-testid="settings-overlay-text-speed-normal"]');
    expect(normal.classes()).not.toContain("on");
    expect(normal.attributes("aria-pressed")).toBe("false");
    expect(wrapper.get('[data-testid="settings-overlay-auto-advance"]').element.checked).toBe(true);
  });

  it("emits text-speed-change and auto-advance-change", async () => {
    wrapper = mount(SettingsOverlay);
    wrapper.get('[data-testid="settings-overlay-text-speed-instant"]').trigger("click");
    await wrapper.vm.$nextTick();
    expect(wrapper.emitted("text-speed-change")).toEqual([["instant"]]);
    const toggle = wrapper.get('[data-testid="settings-overlay-auto-advance"]');
    toggle.element.checked = true;
    toggle.trigger("change");
    await wrapper.vm.$nextTick();
    expect(wrapper.emitted("auto-advance-change")).toEqual([[true]]);
  });
});
