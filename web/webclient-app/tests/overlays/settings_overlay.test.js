import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import SettingsOverlay from "../../components/SettingsOverlay.vue";

// SettingsOverlay (B5 overlay family): full-viewport settings dialog with
// client-local options (fonts, type scale, reduced motion, text-to-HTML
// narrative, colorblind palette). Each control change emits the matching
// `options.*` OOB action envelope (the C-wave store persists/dispatches it).
describe("SettingsOverlay (B5 overlay family)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.documentElement.removeAttribute("data-reduced-motion");
  });

  it("renders the full-viewport settings dialog as a dialog with a close button", () => {
    wrapper = mount(SettingsOverlay);
    const overlay = wrapper.get('[data-testid="settings-overlay"]');
    expect(overlay.attributes("role")).toBe("dialog");
    expect(wrapper.find('[data-testid="settings-overlay-close"]').exists()).toBe(true);
  });

  it("emits close from the close button", () => {
    wrapper = mount(SettingsOverlay);
    wrapper.get('[data-testid="settings-overlay-close"]').trigger("click");
    expect(wrapper.emitted("close")).toBeTruthy();
  });

  it("hides the overlay when open is false", () => {
    wrapper = mount(SettingsOverlay, { props: { open: false } });
    expect(wrapper.find('[data-testid="settings-overlay"]').exists()).toBe(false);
  });

  it("emits options.fonts when the font select changes", () => {
    wrapper = mount(SettingsOverlay);
    const select = wrapper.get('[data-testid="settings-overlay-fonts"]');
    select.element.value = "f-serif";
    select.trigger("change");
    expect(wrapper.emitted("action")[0][0]).toEqual({
      action_id: "options.fonts",
      payload: { font: "f-serif" },
    });
  });

  it("emits options.type_scale when the type scale select changes", () => {
    wrapper = mount(SettingsOverlay);
    const select = wrapper.get('[data-testid="settings-overlay-type-scale"]');
    select.element.value = "1.25";
    select.trigger("change");
    expect(wrapper.emitted("action")[0][0]).toEqual({
      action_id: "options.type_scale",
      payload: { value: 1.25 },
    });
  });

  it("emits options.reduced_motion from the reduced-motion toggle", () => {
    wrapper = mount(SettingsOverlay);
    const toggle = wrapper.get('[data-testid="settings-overlay-reduced-motion"]');
    toggle.element.checked = true;
    toggle.trigger("change");
    expect(wrapper.emitted("action")[0][0]).toEqual({
      action_id: "options.reduced_motion",
      payload: { value: "on" },
    });
  });

  it("emits options.text_to_html from the HTML narrative toggle", () => {
    wrapper = mount(SettingsOverlay);
    const toggle = wrapper.get('[data-testid="settings-overlay-text-to-html"]');
    toggle.element.checked = true;
    toggle.trigger("change");
    expect(wrapper.emitted("action")[0][0]).toEqual({
      action_id: "options.text_to_html",
      payload: { enabled: true },
    });
  });

  it("emits options.colorblind from the colorblind toggle", () => {
    wrapper = mount(SettingsOverlay);
    const toggle = wrapper.get('[data-testid="settings-overlay-colorblind"]');
    toggle.element.checked = true;
    toggle.trigger("change");
    expect(wrapper.emitted("action")[0][0]).toEqual({
      action_id: "options.colorblind",
      payload: { enabled: true },
    });
  });

  it("reflects the reduced-motion option as a root data attribute", () => {
    wrapper = mount(SettingsOverlay, { props: { options: { reduced_motion: "on" } } });
    expect(
      wrapper.get('[data-testid="settings-overlay"]').attributes("data-reduced-motion"),
    ).toBe("on");
    wrapper.unmount();

    wrapper = mount(SettingsOverlay);
    expect(
      wrapper.get('[data-testid="settings-overlay"]').attributes("data-reduced-motion"),
    ).toBe("off");
  });

  it("reflects reduced motion app-wide via the document root (app-wide motion tokens)", () => {
    document.documentElement.removeAttribute("data-reduced-motion");
    wrapper = mount(SettingsOverlay, { props: { options: { reduced_motion: "on" } } });
    // The option's state is applied to <html>, so the whole app (shell,
    // panels, narrative feed) inherits the 1ms motion tokens — not just
    // the settings dialog.
    expect(document.documentElement.getAttribute("data-reduced-motion")).toBe("on");
    // Toggling the control off keeps the app-wide state in sync.
    const toggle = wrapper.get('[data-testid="settings-overlay-reduced-motion"]');
    toggle.element.checked = false;
    toggle.trigger("change");
    expect(document.documentElement.getAttribute("data-reduced-motion")).toBe("off");
    expect(wrapper.emitted("action").at(-1)[0]).toEqual({
      action_id: "options.reduced_motion",
      payload: { value: "off" },
    });
  });

  it("reflects the colorblind option as a root data attribute", () => {
    wrapper = mount(SettingsOverlay, { props: { options: { colorblind: true } } });
    expect(
      wrapper.get('[data-testid="settings-overlay"]').attributes("data-colorblind"),
    ).toBe("on");
    wrapper.unmount();

    wrapper = mount(SettingsOverlay);
    expect(
      wrapper.get('[data-testid="settings-overlay"]').attributes("data-colorblind"),
    ).toBe("off");
  });

  it("emits only options.-prefixed action ids for every control", () => {
    wrapper = mount(SettingsOverlay);
    const font = wrapper.get('[data-testid="settings-overlay-fonts"]');
    font.element.value = "f-mono";
    font.trigger("change");
    const scale = wrapper.get('[data-testid="settings-overlay-type-scale"]');
    scale.element.value = "0.9";
    scale.trigger("change");
    const motion = wrapper.get('[data-testid="settings-overlay-reduced-motion"]');
    motion.element.checked = true;
    motion.trigger("change");
    const html = wrapper.get('[data-testid="settings-overlay-text-to-html"]');
    html.element.checked = true;
    html.trigger("change");
    const blind = wrapper.get('[data-testid="settings-overlay-colorblind"]');
    blind.element.checked = true;
    blind.trigger("change");
    const actions = wrapper.emitted("action");
    expect(actions).toHaveLength(5);
    for (const [envelope] of actions) {
      expect(envelope.action_id.startsWith("options.")).toBe(true);
    }
  });
});
