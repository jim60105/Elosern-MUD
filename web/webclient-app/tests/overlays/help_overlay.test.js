import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import HelpOverlay from "../../components/HelpOverlay.vue";
import { ONBOARDING_GUIDE_SAMPLE } from "../../stories/fixtures.js";

describe("HelpOverlay (H5 body, webclient-hud-05-overlays-and-command-line)", () => {
  const guide = ONBOARDING_GUIDE_SAMPLE;
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  it("renders the onboarding guide: arrival prose + prompt, guard guidance, and every Q&A row", () => {
    wrapper = mount(HelpOverlay, { props: { guide } });
    // The body is a plain block (task 6.1): no dialog role / aria-modal /
    // close control — those belong to the OverlayHost.
    const overlay = wrapper.get('[data-testid="help-overlay"]');
    expect(overlay.attributes("role")).toBeUndefined();
    expect(overlay.attributes("aria-modal")).toBeUndefined();
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

  it("always renders the client's own control reference (task 6.6)", () => {
    // Mounted with no guide payload: the control reference section is present
    // with its rows and the one-line `help` path (the client's own reference,
    // never authored game-help content).
    wrapper = mount(HelpOverlay);
    const controls = wrapper.get('[data-testid="help-controls"]');
    expect(controls.exists()).toBe(true);
    const rows = controls.findAll('[data-testid^="help-controls-row-"]');
    expect(rows.length).toBeGreaterThan(0);
    const gameHelp = wrapper.get('[data-testid="help-controls-gamehelp"]').text();
    expect(gameHelp).toMatch(/help/i);
    // No guide sections when the payload is absent (task 6.7).
    expect(wrapper.find('[data-testid="help-arrival"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="help-guard"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="help-qa"]').exists()).toBe(false);
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
});
