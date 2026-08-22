import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import HelpOverlay from "../../components/HelpOverlay.vue";
import { ONBOARDING_GUIDE_SAMPLE } from "../../stories/fixtures.js";

describe("HelpOverlay (B5 full-overlays family)", () => {
  const guide = ONBOARDING_GUIDE_SAMPLE;
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
  });

  it("renders the onboarding guide: arrival prose + prompt, guard guidance, and every Q&A row", () => {
    wrapper = mount(HelpOverlay, { props: { guide } });
    const overlay = wrapper.get('[data-testid="help-overlay"]');
    expect(overlay.attributes("role")).toBe("dialog");
    expect(overlay.attributes("aria-modal")).toBe("true");
    expect(
      wrapper.get('[data-testid="help-arrival"]').text(),
    ).toContain(guide.arrival.prose);
    expect(
      wrapper.get('[data-testid="help-arrival-prompt"]').text(),
    ).toContain(guide.arrival.prompt);
    const guardText = wrapper.get('[data-testid="help-guard"]').text();
    expect(guardText).toContain(guide.guard.name);
    expect(guardText).toContain(guide.guard.guidance);
    const rows = wrapper
      .get('[data-testid="help-qa"]')
      .findAll('[data-testid="help-qa-row"]');
    expect(rows).toHaveLength(guide.qna.length);
    guide.qna.forEach((entry, index) => {
      const text = rows[index].text();
      expect(text).toContain(entry.question);
      expect(text).toContain(entry.answer);
    });
  });

  it("renders only the arrival section for a bare guide (truthful-data rule)", () => {
    wrapper = mount(HelpOverlay, {
      props: { guide: { arrival: guide.arrival } },
    });
    const arrivalText = wrapper.get('[data-testid="help-arrival"]').text();
    expect(arrivalText).toContain(guide.arrival.prose);
    expect(
      wrapper.get('[data-testid="help-arrival-prompt"]').text(),
    ).toContain(guide.arrival.prompt);
    expect(wrapper.find('[data-testid="help-guard"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="help-qa"]').exists()).toBe(false);
    expect(wrapper.findAll('[data-testid="help-qa-row"]').length).toBe(0);
  });

  it("shows just the dialog frame when the guide is missing", () => {
    wrapper = mount(HelpOverlay, {});
    expect(wrapper.find('[data-testid="help-overlay"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="help-arrival"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="help-guard"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="help-qa"]').exists()).toBe(false);
  });

  it("emits \"close\" from the close button", () => {
    wrapper = mount(HelpOverlay, { props: { guide } });
    wrapper.get('[data-testid="help-overlay-close"]').trigger("click");
    expect(wrapper.emitted("close")).toBeTruthy();
    expect(wrapper.emitted("close").length).toBe(1);
  });

  it("is hidden when open is false", () => {
    wrapper = mount(HelpOverlay, { props: { guide, open: false } });
    expect(wrapper.find('[data-testid="help-overlay"]').exists()).toBe(false);
  });
});
